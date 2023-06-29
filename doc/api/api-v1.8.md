# REST API v1.8

(same as v1.7)

# Description

Current version of FoD officially has a REST API.
The API needs authentication. Out of the box the supported authentication
type is Token Authentication.

TO UPDATE

## Generating Tokens

A user can generate an API token using the FoD UI. Select "My Profile" from the
top right menu and on the "Api Token" section click "Generate One".

## Accessing the API

The API is available at `/api/`. One can see the available API endpoints for 
each model by making a GET request there. An authentication token must be added
in the request:

* Using `cURL`, add the `-H "Authorization: Token <your-token>"`
parameter
* Using Postman, under the "Headers" add a header with name
"Authorization" and value "Token <your-token>".

# Endpoints

REST API provides the following endpoints that will be described in more detail in the next sections:

* `/api/matchprotocol/` 
* `/api/fragmenttypes/`
* `/api/matchdscp/` not supported yet
* `/api/thenactions/`
* `/api/routes/`
* `/api/stats/routes/`

# Usage Examples

Some basic usage examples will be provided including available
actions. Examples will be provided in `cURL` form.

An example will be provided for `ThenAction`. This example applies to most other
models (`FragmentType`, `MatchProtocol`, `MatchDscp`) except
`Route` which is more complex and will be treated separately.

## ThenAction

### GET

#### All items

URL: `/api/thenactions/`

Example:
```
curl -X GET https://fod.example.com/api/thenactions/ -H "Authorization: Token <your-token>"
# or on the FoD host locally:
curl -X GET http://localhost:8000/api/thenactions/ -H "Authorization: Token <your-token>"

RESPONSE:
[
    "discard",
    "rate-limit:10000k",
    "rate-limit:1000k",
    "rate-limit:100k"
]
```

## Route

### GET

#### All items

URL: `/api/routes/`

Example:
```
curl -X GET https://fod.example.com/api/routes/ -H "Authorization: Token <your-token>"

RESPONSE:
[
  {
        "applier": "admin",
        "comments": "test comment",
        "destination": "1.0.0.4/32",
        "destinationport": "124",
        "dscp": [],
        "expires": "2021-04-15",
        "filed": "2021-03-17T13:39:04.244120Z",
        "fragmenttype": [],
        "icmpcode": null,
        "id": 62,
        "last_updated": "2021-03-17T13:39:04.244151Z",
        "name": "test_66ML9G",
        "packetlength": null,
        "port": null,
        "protocol": [
            "udp"
        ],
        "requesters_address": null,
        "response": null,
        "source": "0.0.0.0/0",
        "sourceport": "123",
        "status": "PENDING",
        "tcpflag": null,
        "then": [
            "discard"
        ]
    }
   ...
]
```

#### A specific item

One can also GET a specific `Route`, by using the `id` in the GET url

URL: `/api/routes/<route-id>/`

Example:
```
curl -X GET https://fod.example.com/api/routes/1/ -H "Authorization: Token <your-token>"

RESPONSE:
{
    "applier": "admin",
    "comments": "test comment",
    "destination": "1.0.0.4/32",
    "destinationport": "124",
    "dscp": [],
    "expires": "2021-04-15",
    "filed": "2021-03-17T13:39:04.244120Z",
    "fragmenttype": [],
    "icmpcode": null,
    "id": 62,
    "last_updated": "2021-03-17T13:39:04.244151Z",
    "name": "test_66ML9G",
    "packetlength": null,
    "port": null,
    "protocol": [
        "udp"
    ],
    "requesters_address": null,
    "response": null,
    "source": "0.0.0.0/0",
    "sourceport": "123",
    "status": "PENDING",
    "tcpflag": null,
    "then": [
        "discard"
    ]
}
```

### POST

Starting from FoD v1.7 the REST API accepts parameters for POST, PUT and PATCH only via JSON documents,
old method used in REST API of FoD v1.3 to specify parameters as single form values is not supported any more.

Required fields (to be specified via JSON document):

* `name`: a name for the route
* `source`: a source subnet in CIDR formation
* `destination`: a destination subnet in CIDR formation
* `comments`: a small comment on what this route is about

The response will contain all the additional fields

URL: `/api/routes/`

Example input data file `newroute.json`:

```
{
    "name": "test1",
    "comments": "test1 comment",
    "source": "0.0.0.0/0",
    "destination": "1.0.0.4/32",
    "protocol": [
        "udp", "tcp"
    ],
    "sourceport": "123,126,250-270",
    "destinationport": "27,124,300-400,500-600",
    "then": ["discard"],
    "expires": "2022-10-20"
}
```

```
# protocol: "icmp" | "udp" | "tcp" # actually choices returned by 'curl -X GET https://fod.example.com/api/matchprotocol/ ...)
# fragmenttype: "is-fragment" | "dont-fragment" | "first-fragment" | "last-fragment" | "not-a-fragment" # actually choices returned by 'curl -X GET https://fod.example.com/api/fragmenttype/ ...)
# dscp: not supported yet
# packetlength: not supported yet
# tcpflag: not supported yet
# icmptype: not supported yet
# icmpcode: not supported yet
# port, sourceport, destinationport
# then: "discard" | "rate-limit:10000k" | "rate-limit:1000k" | "rate-limit:100k" # actually choices returned by 'curl -X GET https://fod.example.com/api/thenactions/ ...)
```

```
curl -X POST https://fod.example.com/api/routes/ -H "Content-Type: application/json" -d@newroute.json -H "Authorization: Token <your-token>" 

{
    "name":"testroute_9Q5Y90",
    "id":5,
    "comments":"Route for testing",
    "applier":"admin",
    "source":"62.217.45.75/32",
    "sourceport":[],
    "destination":"62.217.45.94/32",
    "destinationport":[],
    "port":[],
    "dscp":[],
    "fragmenttype":[],
    "icmpcode":null,
    "packetlength":null,
    "protocol":[],
    "tcpflag":null,
    "then":[
       "https://fod.example.com/api/thenactions/4/"
    ],
    "filed":"2017-03-29T14:21:03.261Z",
    "last_updated":"2017-03-29T14:21:03.261Z",
    "status":"PENDING",
    "expires":"2017-04-05",
    "response":null,
    "requesters_address":null
}
```

Notice that the `Route` has a `PENDING` status. This happens because the `Route`
is applied asynchronously to the Flowspec device (the API does not wait for the
operation). After a while the `Route` application will be finished and the 
`status` field will contain the updated status (`ACTIVE`, `ERROR` etc).
You can check this `Route`s status by issuing a `GET` request with the `id`
the API returned.



### PUT, PATCH

Starting from FoD v1.7 the REST API accepts parameters for POST, PUT and PATCH only via JSON documents,
old method used in REST API of FoD v1.3 to specify parameters as single form values is not supported any more.

`Route` objects can be modified using the `PUT` / `PATCH` HTTP methods.

```
# e.g., for rule id '10100'
curl -X PUT https://fod.example.com/api/routes/10100/ -d@data.json -H "Authorization: Token <your-token>"

curl -X PATCH https://fod.example.com/api/routes/10100/ -d@data.json -H "Authorization: Token <your-token>"
``` 

When using `PUT` all fields need to be specified (compare `POST` section).
However, when using `PATCH` one can specify single fields, too. 
This is especially useful for changing the `status` of an `INACTIVE` `Route` to `ACTIVE`
or vice versa.

A PATCH or PUT of an active rule towards status INACTIVE will trigger removal of that active
rule from the configured NETCONF-linked router.
A PATCH or PUT of an inactive rule towards status ACTIVE will trigger commiting of that inactive
rule to the configured NETCONF-linked router.
A PATCH or PUT of an inactive rule with no status change will not trigger any change towards
the configured NETCONF-linked router.

The result of PUT and PATCH are different in the following case:
A PATCH without change of status value and change only of non-FlowSpec-specific
match and action fields will not trigger a recommiting of even an active FlowSpec rule
on the configured NETCONF-linked router.
So, e.g., the comments or the rule expiration period can be changed without interrupting
and active route.

In contrast, a PUT of an active rule will always trigger a recommiting of that route 
on the configured NETCONF-linked router, independent of the attribute values changed.
So, this is useful
for ensuring that a rule is really still actively installed on the configured NETCONF-linked router
with all match and action parameters as is was last deployed by FoD,
and not changed by some other means without FoD's notice, e.g., other tools or directly by the CLI of the router.

### DELETE

```
# e.g., for rule id '10100'
curl -X DELETE https://fod.example.com/api/routes/10100/ -H "Authorization: Token <your-token>"

``` 

A DELETE method applied to a Flowspec rule has now always the semantics of fully removing the rule
also from data base (and so its history), not only deactivating it via NETCONF on the routers.
Furthermore, the application of this method can be restricted depending on the settings.
3 setting variables (ALLOW_DELETE_FULL_FOR_ADMIN, ALLOW_DELETE_FULL_FOR_USER_ALL, ALLOW_DELETE_FULL_FOR_USER_LIST)
control whether admin users, normal users in general, or a specificly selected
set of normal users is allowed to use DELETE method.
The default values of the settings (flowspy/settings.py.dist) by this means 
allow DELETE only for admins, only for a specificly defined set of normal users.

### General notes on `Route` models (differences to REST API of FoD v1.7):

* Starting from FoD v1.7 the REST API accepts parameters for POST, PUT and PATCH only via JSON documents,
old method used in REST API of FoD v1.3 to specify parameters as single form values is not supported any more.

* In contrast to REST API of FoD v1.3, REST API of current version v1.7 will honor the status
value set in POST method calls.
So, it is possible to create a Flowspec rule with status INACTIVE, 
i.e., a rule which will not be automatically commited via NETCONF as result of the POST method call.

* In contrast to REST API of FoD v1.3, REST API of current version v1.7,
the reuslt of PUT and PATCH method differs in some occasions (see above).

* In contrast to REST API of FoD v1.3, REST API of current version v1.7
will behave differently regarding the DELETE method (see above).


