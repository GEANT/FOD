# Configuration v1.8

Time to configure flowspy.

First of all you have to copy the dist files to their proper position:

	# cd /srv/flowspy/flowspy
	# cp settings.py.dist settings.py
	# cp urls.py.dist urls.py

Then, you have to edit the settings.py file to correspond to your needs. The settings one has to focus on are:

## Settings.py
Its time to configure `settings.py` in order to connect flowspy with a database, a network device and a broker.

So lets edit settings.py file.

It is strongly advised that you do not change the following to False
values unless, you want to integrate FoD with you CRM or members
database. This implies that you are able/have the rights to create
database views between the two databases:

    PEER_MANAGED_TABLE = True
    PEER_RANGE_MANAGED_TABLE = True
    PEER_TECHC_MANAGED_TABLE = True

By doing that the corresponding tables as defined in peers/models will
not be created. As noted above, you have to create the views that the
tables will rely on.

### Administrators

	ADMINS: set your admin name and email (assuming that your server can send notifications)

### Secret Key
Please put a random string in `SECRET_KEY` setting.
Make this *unique*, and don't share it with anybody. It's the unique identifier of this instance of the application.

### Allowed hosts
A list of strings representing the host/domain names that this Django site can serve. This is a security measure to prevent an attacker from poisoning caches and password reset emails with links to malicious hosts by submitting requests with a fake HTTP Host header, which is possible even under many seemingly-safe webserver configurations.

For example:

	ALLOWED_HOSTS = ['*']

### Protected subnets
Subnets for which source or destination address will prevent rule creation and notify the `NOTIFY_ADMIN_MAILS`.

	PROTECTED_SUBNETS = ['10.10.0.0/16']

### Minimum Prefix Length for submitted FlowSpec rules

IPv4 rules:

	PREFIX_LENGTH = 29

IPv6 rules:

	PREFIX_LENGTH_IPV6 = 64 - (32 - 29)

### Database
`DATABASES` should contain the database credentials:

	DATABASES = {
	    'default': {
	        'ENGINE': 'django.db.backends.mysql',
	        'NAME': 'flowspy',
	        'USER': '<db user>',
	        'PASSWORD': '<db password>',
	        'HOST': '<db host>',
	        'PORT': '',
	    }
	}

### Localization
By default Flowspy has translations for English and Greek. In case you want to add
another language, or remove one of the existing, you can change the `LANGUAGES`
variable and follow [django's localization documentation](https://docs.djangoproject.com/en/1.4/topics/i18n/translation/#localization-how-to-create-language-files)

You might want to change `TIME_ZONE` setting too. Here is a [list](http://en.wikipedia.org/wiki/List_of_tz_database_time_zones)


### Cache
Flowspy uses cache in order to be fast. We recomend the usage of memcached, but
any cache backend supported by django should work fine.

	CACHES = {
	    'default': {
	        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
	        'LOCATION': '127.0.0.1:11211',
	    }
	}

### Network device access for rule changes (NETCONF)
We have to inform django about the device we set up earlier.

	NETCONF_DEVICE = "device.example.com"
	NETCONF_USER = "<netconf user>"
	NETCONF_PASS = "<netconf password>"
	NETCONF_PORT = 830

### Network device access for mitigation counters (SNMP)
We have to inform django about the device we set up earlier.

	SNMP_COMMUNITY = "abcd"

	SNMP_IP = [
	  {"ip": "192.168.0.1", "port": 1000},
	  {"ip": "192.168.0.2", "port": 1001, "community": "abcdef"},
	  {"ip": "192.168.0.3", "port": 1002},
	  {"ip": "192.168.0.4", "port": 1002}
]

	SNMP_CNTBYTES =     "1.3.6.1.4.1.2636.3.5.2.1.5" # OID of bytes counter (currently unused)
	SNMP_CNTPACKETS =   "1.3.6.1.4.1.2636.3.5.2.1.4" # OID of packet counter
	SNMP_RULESFILTER = ["__flowspec_default_inet__", "__flowspec_IAS_inet__", "__flowspec_default_inet6__", "__flowspec_IAS_inet6__"] # get only statistics of specified tables$
	SNMP_POLL_INTERVAL = 8 #seconds # load new data into cache if it is older that a specified number of seconds
	SNMP_TEMP_FILE = "/srv/flowspy/snmp_temp_data"
	SNMP_POLL_LOCK = "/var/run/fod/snmppoll.lock"
	SNMP_MAX_SAMPLECOUNT = 2016 # one month
	SNMP_REMOVE_RULES_AFTER = 604800 # one month

### statistics calc based on the SNMP counters
	
	GRAPHS_API_URL = 'http://127.0.0.1:8080/api/routes/'

	STATISTICS_PER_RULE = True
	STATISTICS_PER_RULE__ADD_INITIAL_ZERO = True

### redis 
Redis connection configuration (as a broker for celery)

	CELERY_BROKER_URL = "redis://localhost//"
	POLLS_TUBE = 'polls'
	BROKER_VHOST = "/"
	CELERY_CONCURRENCY = 1

### Notifications
Outgoing mail address and prefix.

	DISABLE_EMAIL_NOTIFICATION = False # only disable for testing

	SERVER_EMAIL = "Example FoD Service <noreply@example.com>"
	EMAIL_SUBJECT_PREFIX = "[FoD] "
	NOTIFY_ADMIN_MAILS = ["admin@example.com"]


If you have not installed an outgoing mail server you can always use your own account (either corporate or gmail, hotmail ,etc) by adding the
following lines in settings.py:

    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_USE_TLS = True #(or False)
    EMAIL_HOST = 'smtp.example.com'
    EMAIL_HOST_USER = 'username'
    EMAIL_HOST_PASSWORD = 'yourpassword'
    EMAIL_PORT = 587 #(outgoing)

### Whois servers
Add two whois servers in order to be able to get all the subnets for an AS.

	PRIMARY_WHOIS = 'whois.example.com'
	ALTERNATE_WHOIS = 'whois.example.net'

### Branding
Fill your company's information in order to show it in flowspy.

	BRANDING = {
	    'name': 'Example.com',
	    'url': 'https://example.com',
	    'footer_iframe': 'https://example.com/iframes/footer/',
	    'facebook': '//facebook.com/example.com',
	    'twitter': '//twitter.com/examplecom',
	    'phone': '800-12-12345',
	    'email': 'helpdesk@example.com',
	    'logo': 'logo.png',
	    'favicon': 'favicon.ico',
	}


### Shibboleth
Flowspy supports shibboleth authentication.

	SHIB_ADMIN_DOMAIN = 'example.com'
	SHIB_LOGOUT_URL = 'https://example.com/Shibboleth.sso/Logout'

	SHIB_AUTH_ENTITLEMENT = 'urn:mace' # can also be set to '', if no filtering of users by entitlement is not needed

	SHIB_SLUGIFY_USERNAME = False

attribute configuration:

	SHIB_USERNAME = ['HTTP_EPPN'] # essential attribute, needed for identification of the user
	SHIB_USERNAME_DISPLAY_NAME = "eduPersonPrincipalName" # only needed for displaying the error message of missing attribute
	SHIB_USERNAME_DISPLAY_ADDINFO = "urn:mace:dir:attribute-def:eduPersonPrincipalName or urn:oid:1.3.6.1.4.1.5923.1.1.1.6" # only needed for displaying the error message of missing attribute

	SHIB_MAIL = ['mail', 'HTTP_MAIL', 'HTTP_SHIB_INETORGPERSON_MAIL'] # essential attribute, because mail is needed for registration and notifications
	SHIB_MAIL_DISPLAY_NAME = "MAIL" # only needed for displaying the error message of missing attribute
	SHIB_MAIL_DISPLAY_ADDINFO = "urn:mace:dir:attribute-def:mail or urn:oid:0.9.2342.19200300.100.1.3 or SHIB_INETORGPERSON_MAIL" # only needed for displaying the error message of missing attribute

	SHIB_FIRSTNAME = ['HTTP_SHIB_INETORGPERSON_GIVENNAME'] # not essential attribute
	SHIB_FIRSTNAME_DISPLAY_NAME = "GIVENNAME" # only needed for displaying the error message of missing attribute
	SHIB_FIRSTNAME_DISPLAY_ADDINFO = "urn:mace:dir:attribute-def:givenName or urn:oid:2.5.4.42" # only needed for displaying the error message of missing attribute

	SHIB_LASTNAME = ['HTTP_SHIB_PERSON_SURNAME'] # not essential attribute
	SHIB_LASTNAME_DISPLAY_NAME = "SURNAME" # only needed for displaying the error message of missing attribute
	SHIB_LASTNAME_DISPLAY_ADDINFO = "urn:mace:dir:attribute-def:sn or urn:oid:2.5.4.4" # only needed for displaying the error message of missing attribute

	SHIB_ENTITLEMENT = ['HTTP_SHIB_EP_ENTITLEMENT'] # not essential, if SHIB_AUTH_ENTITLEMENT='', otherwise essential
	SHIB_ENTITLEMENT_DISPLAY_NAME = "eduPersonEntitlement" # only needed for displaying the error message of missing attribute
	SHIB_ENTITLEMENT_DISPLAY_ADDINFO = "urn:oid:1.3.6.1.4.1.5923.1.1.1.7; the value of this attribute also has to include 'urn:mace:example.com:pki:user'" # only needed for displaying the error message of missing attribute

### Various Settings

	TIME_ZONE = 'UTC'
	LANGUAGE_CODE = 'en'
	LANGUAGES = (
		('el', _('Greek')),
		('en', _('English')),
	)


### Syncing the database
To create all the tables and fill with basic data needed by FoD we have to run the following commands:

	cd /srv/flowspy
	./manage.py migrate
	./manage.py initial_data

## Create a superuser
A superuser can be added by using the following command from `/srv/flowspy/`:

	./manage.py createsuperuser


## Propagate the flatpages
Inside the initial\_data/fixtures\_manual.xml file we have placed 4
flatpages (2 for Greek, 2 for English) with Information and Terms of
Service about the service. To import the flatpages, run from root
folder:

    python manage.py loaddata initial_data/fixtures_manual.xml

### Celery
Celery is a distributed task queue, which helps FoD run some async tasks, like applying a flowspec rule to a router.

`Note` In order to check if celery runs or even debug it, you can run:

	./manage.py celeryd --loglevel=debug


### Testing/Debugging
In order to see what went wrong you can check the following things.

#### Django
You can start the server manually by running:

	./manage.py runserver 127.0.0.1:8081

By doing so, you can serve your application like gunicord does just to test that its starting properly. This command should not be used in production!

Of course you have to stop gunicorn and make sure that port 8081 is free.

#### Gunicorn
Just curl from the server http://localhost:8081

#### Celery
In order to check if celery is working properly one can start celery by typing:

	./manage.py celeryd --loglevel=debug

Again this is for debug purposes.


#### Connectivity to flowspec device
Just try to connect with the credentials you entered in settings.py from the host that will be serving flowspy.


#### General Test
Log in to the admin interface via https://<hostname>/admin. Go to Peer ranges and add a new range (part of/or a complete subnet), eg. 10.20.0.0/19 Go to Peers and add a new peer, eg. id: 1, name: Test, AS: 16503, tag: TEST and move the network you have created from Available to Chosen. From the admin front, go to User, and edit your user. From the bottom of the page, select the TEST peer and save. Last but not least, modify as required the existing (example.com) Site instance (admin home->Sites). You are done. As you are logged-in via the admin, there is no need to go through Shibboleth at this time. Go to https://<hostname>/ and create a new rule. Your rule should be applied on the flowspec capable device after aprox. 10 seconds.

## Footer
Under the templates folder (templates), you can alter the footer.html
file to include your own footer messages, badges, etc.

## Welcome Page
Under the templates folder (templates), you can alter the welcome page -
welcome.html with your own images, carousel, videos, etc.

## Usage

### Web interface
FoD comes with a web interface, in which one can edit and apply new routes.

### Rest Api
FoD provides a rest api. It uses token as authentication method.

### Generating Tokens
A user can generate a token for his account on "my profile" page from FoD's
UI. Then by using this token in the header of the request he can list, retrieve,
modify and create rules.

### Example Usage
Here are some examples:

#### GET items
- List all the rules your user has created (admin users can see all the rules)

            curl -X GET https://fod.example.com/api/routes/ -H 'Authorization: Token <Your users token>'

- Retrieve a specific rule:

            curl -X GET https://fod.example.com/api/routes/<rule_id>/ -H 'Authorization: Token <Your users token>'

- In order to create or modify a rule you have to use POST/PUT methods.

#### POST/PUT rules
In order to update or create rules you can follow this example:

##### Foreign Keys
In order to create/modify a rule you have to connect the rule with some foreign keys:

###### Ports, Fragmentypes, protocols, thenactions
When creating a rule, one can specify:

- source port
- destination port
- port (if source = destination)

That can be done by getting the url of the desired port instance from `/api/ports/<port_id>/`

Same with Fragmentypes in `/api/fragmenttypes/<fragmenttype_id>/`, protocols in `/api/matchprotocol/<protocol_id>/` and then actions in `/api/thenactions/<action_id>/`.

Since we have the urls we want to connect with the rule we want to create, we can make a POST request like the following:


      curl -X POST -H 'Authorization: Token <Your users token>' -F "name=Example" -F "comments=Description" -F "source=0.0.0.0/0" -F "sourceport=https://fod.example.com/api/ports/7/" -F "destination=203.0.113.12" https://fod.example.com/api/routes/

And here is a PUT request example:

      curl -X PUT -F "name=Example" -F "comments=Description" -F "source=0.0.0.0/0" -F "sourceport=https://fod.example.com/api/ports/7/" -F "destination=83.212.9.93" https://fod.example.com/api/routes/12/ -H  'Authorization: Token <Your users token>'


