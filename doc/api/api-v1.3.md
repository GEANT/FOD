# REST API v1.3

# Description

Current version of {{ product_name_short }} officially has a REST API.
The API needs authentication. Out of the box the supported authentication
type is Token Authentication.

## Generating Tokens

A user can generate an API token using the {{ product_name_short }} UI. Select "My Profile" from the
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

* `/api/routes/`
* `/api/thenactions/`
* `/api/matchprotocol/`
* `/api/matchdscp/`
* `/api/fragmenttypes/`
* `/api/stats/routes/`


# Usage Examples

Some basic usage examples will be provided including available
actions. Examples will be provided in `cURL` form.

An example will be provided for `ThenAction`. This example applies to most other
models (`MatchPort`, `FragmentType`, `MatchProtocol`, `MatchDscp`) except
`Route` which is more complex and will be treated separately.

## ThenAction

### GET

#### All items

URL: `/api/thenactions/`

Example:
```
curl -X GET https://fod.example.com/api/thenactions/ -H "Authorization: Token <your-token>"

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

Required fields:

* `name`: a name for the route
* `source`: a source subnet in CIDR formation
* `destination`: a destination subnet in CIDR formation
* `comments`: a small comment on what this route is about

The response will contain all the additional fields

URL: `/api/routes/`

Example input data file `newroute.json`:

```
{
    "comments": "test comment",
    "destination": "1.0.0.4/32",
    "destinationport": "124",
    "name": "test",
    "protocol": [
        "udp"
    ],
    "source": "0.0.0.0/0",
    "sourceport": "123",
    "then": ["discard"]
}
```

```
curl -X POST --data-binary @newroute.json  -H "Content-Type: application/json" -H "Authorization: Token <your-token>" https://fod.example.com/api/routes/

RESPONSE:
{
    "name": "test_OLLFTU",
    "id": 63,
    "comments": "test comment",
    "applier": "admin",
    "source": "0.0.0.0/0",
    "sourceport": "123",
    "destination": "1.0.0.4/32",
    "destinationport": "124",
    "port": null,
    "dscp": [],
    "fragmenttype": [],
    "icmpcode": null,
    "packetlength": null,
    "protocol": [
        "udp"
    ],
    "tcpflag": null,
    "then": [
        "discard"
    ],
    "filed": "2021-04-14T12:11:58.352094Z",
    "last_updated": "2021-04-14T12:11:58.352141Z",
    "status": "PENDING",
    "expires": "2021-05-13",
    "response": null,
    "requesters_address": null
}
```

Notice that the `Route` has a `PENDING` status. This happens because the `Route`
is applied asynchronously to the Flowspec device (the API does not wait for the
operation). After a while the `Route` application will be finished and the 
`status` field will contain the updated status (`ACTIVE`, `ERROR` etc).
You can check this `Route`s status by issuing a `GET` request with the `id`
the API returned.

This `Route`, however, is totally useless, since it applies no action for the
matched traffic. Let's add one with a `then` action which will discard it.

To do that, we must first add a `ThenAction` (or pick one of the already
existing) since we need it's `id`. Let's assume a `ThenAction` with an `id` of
`4` exists. To create a new `Route` with this `ThenAction`:

```
curl -X POST https://fod.example.com/api/routes/ -F "source=62.217.45.75/32" -F "destination=62.217.45.91/32" -F "name=testroute" -F "comments=Route for testing" -F "then=https://fod.example.com/api/thenactions/4" -H "Authorization: Token <your-token>"

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

With the same process one can associate a `Route` with the `MatchPort`,
`FragmentType`, `MatchProtocol` & `MatchDscp` models.

NOTE:

When adding multiple `ForeignKey` related fields (such as multiple
`MatchPort` or `ThenAction` items) it is best to use a `json` file on the
request instead of specifying each field as a form argument.

Example:

```
curl -X POST https://fod.example.com/api/routes/ -d@data.json -H "Authorization: Token <your-token>"

data.json:
{
    "name": "testroute",
    "comments": "Route for testing",
    "then": [
        "https://fod.example.com/api/thenactions/4",
        "https://fod.example.com/api/thenactions/5",
    ],
    "source": "62.217.45.75/32",
    "destination": "62.217.45.91/32"
}

RESPONSE:
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

### PUT, PATCH

`Route` objects can be modified using the `PUT` / `PATCH` HTTP methods.

When using `PUT` all fields should be specified (see `POST` section).
However, when using `PATCH` one can specify single fields too. This is useful
for changing the `status` of an `INACTIVE` `Route` to `ACTIVE`.

The process is the same as described above with `POST`. Don't forget to use
the correct method.

### DELETE

See `ThenAction`s.

### General notes on `Route` models:

* When `POST`ing a new `Route`, {{ product_name_short }} will automatically commit it to the flowspec
device. Thus, `POST`ing a new `Route` with a status of `INACTIVE` has no effect,
since the `Route` will be activated and the status will be restored to `ACTIVE`.
* When `DELETE`ing a `Route`, the actual `Route` object will remain. {{ product_name_short }} will
only delete the rule from the flowspec device and change the `Route`'s status to
'INACTIVE'
* When changing (`PUT`/`PATCH`) a `Route`, {{ product_name_short }} will sync the changes to the
flowspec device. Changing the status of the `Route` will activate / delete the
rule respectively.
