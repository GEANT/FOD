
var xhrlp = '';
$(document).ready(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    $("#message").select();
    {% if user.is_authenticated %}
    updater.start();
    {% endif %}
});


function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

jQuery.postJSON = function(url, args, callback) {
    $.ajax({url: url, dataType: "json", type: "POST", cache: false,
            success: function(response) {
        if (callback) callback(response);
    }, error: function(response) {
        console.log("ERROR:", response);
    }});
};

jQuery.fn.formToDict = function() {
    var fields = this.serializeArray();
    var json = {}
    for (var i = 0; i < fields.length; i++) {
        json[fields[i].name] = fields[i].value;
    }
    if (json.next) delete json.next;
    return json;
};

jQuery.fn.disable = function() {
    this.enable(false);
    return this;
};

jQuery.fn.enable = function(opt_enable) {
    if (arguments.length && !opt_enable) {
        this.attr("disabled", "disabled");
    } else {
        this.removeAttr("disabled");
    }
    return this;
};

var poller_dash_use_reload; 
var dataTableUpdate_lock = false;
function reloadDataTable(cause) {

  console.log("reloadDataTable(): cause="+cause+" dataTableUpdate_lock="+dataTableUpdate_lock);

  if (!dataTableUpdate_lock) {
    dataTableUpdate_lock = true

    try {
      //console.log("DataTable reload triggered after new rule update messages");
      console.log("DataTable reload triggered after new rule update messages (poller_dash_use_reload="+poller_dash_use_reload+")");

    if (poller_dash_use_reload!=undefined && poller_dash_use_reload) {
       window.location.reload(false); 	
    } else if ($('#routes_table').DataTable().ajax!=undefined) {
       console.log("DataTable.ajax defined");
       //oTable.fnReloadAjax(refreshUrl);
       //console.log("oTable="+oTable);
       //console.log("ajax2="+$('#routes_table').DataTable().ajax);
       $('#routes_table').DataTable().ajax.reload();
     } else {
       console.log("DataTable.ajax is undefined");
       if (oTable!=undefined) {
         oTable.fnReloadAjax(refreshUrl);
       }
       window.location.reload(false); 	
     }

      console.log("DataTable reload returned");
    } catch (e) {
      console.log("DataTable reload failed: "+e);
    }

    dataTableUpdate_lock = false
  }
}


var updater = {
    started: false,
    last_ids: new Object(),
    start: function() {
            //console.log("Initial fetching of all notifications.");
            {% for peer in user.userprofile.peers.all %}
            updater.last_ids["{{ peer.pk }}"] = null;
        try {
            $.ajax({url: "{% url 'fetch-existing'  peer.pk %}", type: "POST", dataType: "json", cache:false,
                            success: updater.onFetchExisting,
                            error: updater.onError});
        } catch (e) {
            console.log("Error: " + e);
        }
            {% endfor %}
    },
    poll: function() {
        {% if user.is_authenticated %}
          timeout = {{timeout}};
          {% for peer in user.userprofile.peers.all %}
           //console.log("Polling new notifications from", updater.last_ids["{{ peer.pk }}"], "peerid {{ peer.pk }}");
           $.ajax({url: "{% url 'fetch-updates'  peer.pk 'PLACEHOLDER' %}".replace("PLACEHOLDER", updater.last_ids["{{ peer.pk }}"]), type: "POST", dataType: "json", cache:false,
                success: updater.onSuccess,
                timeout: timeout,
                error: updater.onError});
          {% endfor %}
        {% endif %}
    },
    onSuccess: function(response) {
        try {
            if (response!=undefined) {
              updater.newMessages(response);
              var errdialog = $('#ajaxerror')
              if (errdialog[0]) {
                  errdialog[0].remove();
              }
              /*if ($('#routes_table')) {
                reloadDataTable("on success response="+response);
              }*/
            }
        } catch (e) {
            console.log(e);
            return;
        }
    },

    onFetchExisting: function(response) {
        try {
            updater.existingMessages(response);
            if (updater.started == false) {
                updater.started = true;
                setInterval(updater.poll, 3000);
            }
        } catch (e) {
            console.log(e);
            updater.onError();
            return;
        }
    },

    onError: function(response, text) {
        var errdialog = $('#ajaxerror');
        if (!errdialog[0]) {
           $('#page-wrapper').after("<div id='ajaxerror'>Loading...</div>");
        }
        $('#ajaxerror').css({"position": "fixed", "right": "100px", "bottom": "10px", "padding": "5px", "font-weight": "bold", "color": "#fff", "background-color": "#f00", "z-index": "10"});
    },

    newMessages: function(response) {

        //console.log("newMessages(): response="+response)
        //console.log("newMessages(): response.messages="+response.messages)

        if (!response || !response.messages) {
            //console.log("newMessages(): !response or !messages")
            return;
        }
        if (response.messages.length == 0){
            //console.log("newMessages(): 0 messages")
            return true;
        }
        
        console.log("newMessages: inner");

        var messages = response.messages;
        var peerid = messages[messages.length - 1]["peerid"];
        var msgid = messages[messages.length - 1]["id"];
        updater.last_ids[peerid] = msgid;

        console.log(messages.length, "new messages, last_id:", msgid, "peerid", peerid);

        var reloadContent = false;
        for (var i = 0; i < messages.length; i++) {
            updater.showMessage(messages[i], peerid);
            try {
              body = messages[i].body 
              if (body.match(/Successfully committed$/) || body.match(/Deleting inactive/) || body.match(/NETCONF/) || body.match(/non-flowspec-params updated/) || body.match(/Rule/) || body.match(/Please wait/)) {
                reloadContent = true;
              }
            } catch (e) {
              console.log("message processing: "+e);
            }
        }
        $("#hid_mid").val('UPDATED');
        if (reloadContent) {
            if ($('#routes_table')) {
              reloadDataTable("on messages.length="+messages.length);
            }
        }
    },

    existingMessages: function(response) {
        if (!response || !response.messages) return;
        if (response.messages.length == 0){
            return true;
        }
        $("#inbox").empty();
        var messages = response.messages;
        var peerid = messages[messages.length - 1]["peerid"];
        var msgid = messages[messages.length - 1]["id"];
        updater.last_ids[peerid] = msgid;
        //console.log("got", messages.length, "messages with last_id", msgid);
        for (var i = 0; i < messages.length; i++) {
            updater.showMessage(messages[i], peerid);
        }
    },

    showMessage: function(message, peerid) {
        var existing = $("#m" + message.id);
        if (existing.length > 0) return;

        try {
          var username = message.body.split("]")[0].replace("[","");
          //var mbody = message.body.replace("["+username+"] ","");
          var mbody = message.body.replace("["+username+"] ", "["+peerid+"] ");
          var htmlnode = '<li class="left clearfix">\
                                      <div class="chat-body clearfix" style="margin-left: 0px;"> \
                                          <div class="header"> \
                                              <small class="pull-right text-muted"> \
                                                  <i class="fa fa-clock-o fa-fw"></i> '+ message.time +'  \
                                              </small>\
                                          </div>\
                                          <p><small><strong class="primary-font">'+username+'</strong>:\
                                              '+ mbody+'\
                                          </small></p>\
                                      </div>\
                                  </li>';
          var node = $(htmlnode);
          node.hide();
          $("#inbox").prepend(node);
          node.slideDown();
        } catch (e) {
          console.log("showMessage(): "+e)
        }
    }
};

function blink(selector){
        $(selector).animate({color: "#EE5F5B"}, 500, function(){
                $(this).animate({ color: "white" }, 500, function(){
                        blink(this);
                });
        });
}

