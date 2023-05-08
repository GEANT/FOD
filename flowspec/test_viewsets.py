import sys
from os import environ
import pytest
from viewsets import *
from flowspec.models import *
from accounts.models import *
from rest_framework.authtoken.models import Token

import requests
#import list

#if DEBUG:
#        warnings.simplefilter('ignore', category=RemovedInDjango40Warning)

#

assert settings.ROUTES_DUPLICATES_CHECKING == False

#dirname1 = os.path.dirname(__file__)
dirname1 = os.path.dirname(os.path.dirname(__file__)) # 2 dir components up as we are located in sub dir "flowspec"

@pytest.fixture
def test_settings(settings):
    settings.DEBUG = True
    #settings.LOG_FILE_LOCATION = "/srv/flowspy/log/testing"
    settings.LOG_FILE_LOCATION = dirname1+"/log/testing"

pytestmark = pytest.mark.django_db

@pytest.fixture(scope='session')
def api_client(django_db_blocker):
  with django_db_blocker.unblock():
    settings.DEBUG = True
    #settings.LOG_FILE_LOCATION = "/srv/flowspy/log/testing"
    settings.LOG_FILE_LOCATION = dirname1+"/log/testing"

    from rest_framework.test import APIClient

    #token = Token.objects.get(user__username='admin').key
    username='admin'
    try:
      #print("adminuser list="+str(User.objects), file=sys.stderr)
      print("adminuser list="+str([x.username for x in User.objects.filter()]), file=sys.stderr)
      adminuser = User.objects.get(username=username)
      print("adminuser existing used", file=sys.stderr)
    except Exception as e:
      print("adminuser exception "+str(e), file=sys.stderr)
      adminuser = User.objects.create(username=username)
      print("adminuser created", file=sys.stderr)
    print("adminuser="+str(adminuser), file=sys.stderr)

    try:
      ap = UserProfile.objects.get(user=adminuser)
      print("ap existing used", file=sys.stderr)
    except Exception as e:
      print("ap exception "+str(e), file=sys.stderr)
      ap = UserProfile(user=adminuser)
      ap.save()
      print("ap created", file=sys.stderr)
    print("ap="+str(ap), file=sys.stderr)

    try:
      an = PeerRange.objects.get(network="0.0.0.0/0")
      print("an existing used", file=sys.stderr)
    except Exception as e:
      print("an exception "+str(e), file=sys.stderr)
      an = PeerRange.objects.create(network="0.0.0.0/0")
      print("an created", file=sys.stderr)
      #an = PeerRange(network="0.0.0.0/0")
      #an.save() 
    print("an="+str(an), file=sys.stderr)

    try:
      aPeer = Peer.objects.get(peer_name="allnet")
      print("aPeer existing used", file=sys.stderr)
    except Exception as e:
      print("aPeer exception "+str(e), file=sys.stderr)
      aPeer = Peer(peer_id=100, peer_name="allnet")
      aPeer.save()
      aPeer.networks.set([an])
      ap.peers.set([aPeer])
      print("aPeer created", file=sys.stderr)
    print("aPeer="+str(aPeer), file=sys.stderr)

    try:
      token = Token.objects.get(user__username=username).key
      print("token existing used", file=sys.stderr)
    except Token.DoesNotExist:
      token = Token.objects.create(user=adminuser).key
      print("token created", file=sys.stderr)
    print("token="+str(token), file=sys.stderr)

    api_client = APIClient()
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    return api_client


@pytest.fixture(scope='session')
def django_db_setup():
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example-data',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
    #django_setup2()

pytestmark = pytest.mark.django_db


##@pytest.fixture(scope='session')
#def django_setup2():
#  print("django_setup2", file=sys.stderr)
#  pytestmark = pytest.mark.django_db
#  #Author.objects.create(name="Joe")
#  #an_author = Author(name="Joe") 
#  #an_author.save() 
#  an = PeerRange.objects.create(network="0.0.0.0/0")
#  #an = PeerRange(network="0.0.0.0/0")
#  #an.save() 
#  print("an="+str(an), file=sys.stderr)
#  aPeer = Peer(peer_id=100, peer_name="allnet")
#  aPeer.save()
#  aPeer.networks.set([an])
#  print("aPeer="+str(aPeer), file=sys.stderr)
#  #adminuser = User.objects.get(username='admin')
#  adminuser = User.objects.create(username='testadmin')
#  try:
#      token = adminuser.auth_token
#  except Token.DoesNotExist:
#      token = Token.objects.create(user=adminuser)
#  ap = UserProfile(user=adminuser)
#  ap.save()
#  ap.peers.set([aPeer])
#  print("ap="+str(ap), file=sys.stderr)

#django_setup2()

#@pytest.fixture
#def user() -> settings.AUTH_USER_MODEL:
#    # return the UserFactory (factoryboy)
#    return UserFactory()

#def test_test1():
#	django_setup2()
 
class TestFragmenttypes:
    def test_list(self, api_client, test_settings):
        endpoint = '/api/matchprotocol/'
        response = api_client.get(endpoint)
        assert response.status_code == 200
        resp_data = json.loads(response.content)
        assert len(resp_data) == 3
        assert resp_data == [ "icmp", "tcp", "udp" ]


class TestRoute:
    def test_add(self, api_client):
        endpoint = '/api/routes/'
        data = {
            "comments": "test route",
            "destination": "1.0.0.2/32",
            "destinationport": "123",
            "name": "test",
            "protocol": [
                "tcp"
            ],
            "source": "0.0.0.0/0",
            "sourceport": "123",
            "then": ["discard"],
            "status": "ACTIVE"
        }

        response = api_client.post(endpoint, json.dumps(data), content_type='application/json')
        assert response.status_code == 201

        resp_data = json.loads(response.content)
        route_id = resp_data["id"]
        response = api_client.delete(f"{endpoint}{route_id}/")
        print(response.content)

    def test_fail_icmpwithport(self, api_client):
        endpoint = '/api/routes/'
        data = {
            "status": "ACTIVE",
            "comments": "test comment",
            "destination": "1.0.0.3/32",
            "destinationport": "80",
            "name": "test",
            "protocol": ["icmp"],
            "fragmenttype": [
                "is-fragment"
            ],
            "source": "0.0.0.0/0",
            "sourceport": "123",
            "then": ["discard"]
        }

        response = api_client.post(endpoint, json.dumps(data), content_type='application/json')
        assert response.status_code == 400
        assert json.loads(response.content) == {"non_field_errors": ["ICMP protocol does not allow to specify ports"]}


    def test_fail_unknownthenaction(self, api_client):
        endpoint = '/api/routes/'
        data = {
            "status": "ACTIVE",
            "comments": "test comment",
            "destination": "1.0.0.3/32",
            "port": "80",
            "name": "test-unknownthen",
            "source": "0.0.0.0/0",
            "then": ["drop"]
        }
 
        response = api_client.post(endpoint, json.dumps(data), content_type='application/json')
        assert response.status_code == 400
        assert json.loads(response.content) == {"then": [["ThenAction does not exist."]]}


    def test_fail_unknownfragmenttype(self, api_client):
        endpoint = '/api/routes/'
        data = {
            "status": "ACTIVE",
            "comments": "test comment",
            "destination": "1.0.0.3/32",
            "destinationport": "80",
            "name": "test",
            "protocol": [],
            "fragmenttype": [
                "unknown-fragment"
            ],
            "source": "0.0.0.0/0",
            "sourceport": "123",
            "then": ["discard"]
        }
 
        response = api_client.post(endpoint, json.dumps(data), content_type='application/json')
        assert response.status_code == 400
        assert json.loads(response.content) == {'fragmenttype': [['FragmentType does not exist.']]}

    def test_list(self, api_client):
        endpoint = '/api/routes/'
        response = api_client.get(endpoint)
        assert response.status_code == 200
        resp_data = json.loads(response.content)
        print(resp_data)

    def test_add_check(self, api_client, settings):
        settings.DEBUG = True
        #settings.LOG_FILE_LOCATION = "/srv/flowspy/log/testing"
        settings.LOG_FILE_LOCATION = dirname1+"/log/testing"

        endpoint = '/api/routes/'

        name = "testcreate"
        comments = "test route"
        destination = "1.0.0.2/32"
        destinationport = "123"
        source = "0.0.0.0/0"
        sourceport = "123"
        protocol = [ "tcp" ]
        then = ["discard"]

        data = {
            "name": name,
            "comments": comments,
            "destination": destination,
            "destinationport": destinationport,
            "protocol": protocol,
            "source": source,
            "sourceport": sourceport,
            "then": then,
            "status": "ACTIVE"
        }

        response = api_client.post(endpoint, json.dumps(data), content_type='application/json')

        assert response.status_code == 201


        resp_data = json.loads(response.content)
        print("myresp_data="+str(resp_data))

        route_id = resp_data["id"]
        print("myroute_id="+str(route_id))

        #assert "comments" in resp_data and resp_data.comments == comments
        assert resp_data["comments"] == comments
        assert resp_data["destination"] == destination
        assert resp_data["destinationport"] == destinationport
        assert resp_data["protocol"] == protocol
        assert resp_data["source"] == source
        assert resp_data["sourceport"] == sourceport
        assert resp_data["then"] == then
        
        # lookup created object
        Route.objects.get(id=route_id)
        print("myroute "+str(route_id)+" added")

        #

        endpoint = '/api/routes/' + str(route_id) + '/'
        response = api_client.get(endpoint)
        print("response="+str(response))
        print("route "+str(route_id)+" verified")

        assert response.status_code == 200
        resp_data = json.loads(response.content)
        print(resp_data)

        #

        #response = api_client.delete(f"{endpoint}{route_id}/")
        response = api_client.delete(f"{endpoint}")
        print("route "+str(route_id)+" deleted")
        
        assert response.status_code == 202

        try:
            Route.objects.get(id=route_id)
        except:
            # should be deleted by now
            pass

class TestRouteOuter:

    #def test_add_outer(self, api_client):

    def get_token(self):
  
        try:
          if self.token1 != None:
            return self.token1  
        except:
            pass

        if environ.get('FOD_TOKEN') != None:
          token1 = environ.get('FOD_TOKEN')
        else:
          #f = open("/srv/flowspy/.admin_token1", "r")
          f = open(dirname1+"/.admin_token1", "r")
          token1 = f.read().rstrip() 
          f.close()

        print("outer token="+str(type(token1)))
        self.token1 = token1
        return token1

    def get_headers(self):

        fod_api_headers = {
          "Authorization" : "Token " + self.get_token(),
          "Content-Type" : "application/json",
        }
        return fod_api_headers

    def wait_route_nonpending(self, endpoint_base, route_id, response=None):
        
        fod_api_headers = self.get_headers()

        endpoint = endpoint_base + str(route_id)

        if response==None:
          response = requests.get(endpoint, headers=fod_api_headers)
          #print("response.content"+str(response.content))
        
        resp_data = json.loads(response.content)
        while "status" in resp_data and resp_data["status"]=="PENDING":
          print("loop to wait for NON-PENDING status")
          response = requests.get(endpoint, headers=fod_api_headers)
          print("response.content"+str(response.content))
          resp_data = json.loads(response.content)
          if "status" in resp_data and resp_data["status"]=="PENDING":
            wait_time = 1
            print("waiting "+str(wait_time))
            time.sleep(wait_time)

        print("wait_route_nonpending(): before returning")
        if "status" in resp_data:
          return resp_data["status"]
        else:
          return None

    def add_route(self, endpoint_base, name="testcreate", comments="test route", source="0.0.0.0/0", sourceport="123", destination="1.0.0.2/32", destinationport="123", protocol=[ "tcp" ], then=[ "discard" ], status="ACTIVE"):

        fod_api_headers = self.get_headers()

        data = {
            "name": name,
            "comments": comments,
            "destination": destination,
            "destinationport": destinationport,
            "protocol": protocol,
            "source": source,
            "sourceport": sourceport,
            "then": then,
            "status": status,
        }
        print("add_route(): data="+str(data))

        response = requests.post(endpoint_base, headers=fod_api_headers, data=json.dumps(data))
        print("response.content"+str(response.content))
        print("response.status_code"+str(response.status_code))
    
        # Validate response headers and body contents, e.g. status code.
        assert response.status_code == 201 or response.status_code == 202

        resp_data = json.loads(response.content)
        print("myresp_data="+str(resp_data))

        route_id = resp_data["id"]
        print("myroute_id="+str(route_id))

        #assert "comments" in resp_data and resp_data.comments == comments
        assert resp_data["comments"] == comments
        assert resp_data["destination"] == destination
        assert resp_data["destinationport"] == destinationport
        assert resp_data["protocol"] == protocol
        assert resp_data["source"] == source
        assert resp_data["sourceport"] == sourceport
        assert resp_data["then"] == then

        #

        #endpoint = 'http://localhost:8000/api/routes/' + str(route_id)
        #while resp_data["status"]=="PENDING":
        #  print("loop to wait for NON-PENDING status")
        #  response = requests.get(endpoint, headers=fod_api_headers)
        #  print("response.content"+str(response.content))
        #  resp_data = json.loads(response.content)
        #  if resp_data["status"]=="PENDING":
        #    wait_time = 1
        #    print("waiting "+str(wait_time))
        #    time.sleep(wait_time)
        #assert resp_data["status"] == status
        status_ret = self.wait_route_nonpending(endpoint_base, route_id, response)

        assert status_ret == status

        return route_id


    def delete_route(self, endpoint_base, route_id):

        fod_api_headers = self.get_headers()

        endpoint = endpoint_base + str(route_id)
        response = requests.delete(endpoint, headers=fod_api_headers)
        assert response.status_code == 202
        print("rule "+str(route_id)+" deleted")

        status_ret = self.wait_route_nonpending(endpoint_base, route_id, None)

        print("rule "+str(route_id)+" checking whether really deleted")
        response = requests.get(endpoint, headers=fod_api_headers)
        resp_data = json.loads(response.content)
        print("get.response.data="+str(resp_data))
        assert response.status_code == 404
        print("rule "+str(route_id)+" really gone")
 
    def test_add_outer_single(self):

        ip1="10.0.0.1/32"

        #

        endpoint_base = 'http://localhost:8000/api/routes/'
        print("endpoint_base="+str(endpoint_base))

        fod_api_headers = self.get_headers()

        comments = "test route"
        protocol = [ "tcp" ]

        #then = [ "https://fod.example.com/api/thenactions/3/" ]
        #then = [ "discard" ]
        then = [ "rate-limit:10000k" ]

        #

        route_id1 = self.add_route(endpoint_base, name="testrule_1s", comments=comments, source="0.0.0.0/0", sourceport="1000-2000", destination=ip1, destinationport="3000-4000,5000-6000", protocol=["tcp"], then=then, status="INACTIVE")
        print("created route: route_id1="+str(route_id1))
        self.delete_route(endpoint_base, route_id1)


    def test_add_outer_multi(self):

        ip1="10.0.0.1/32"
        ip2="10.0.0.2/32"
        ip3="10.0.0.3/32"

        #

        endpoint_base = 'http://localhost:8000/api/routes/'
        print("endpoint_base="+str(endpoint_base))

        fod_api_headers = self.get_headers()

        comments = "test route"
        protocol = [ "tcp" ]

        #then = [ "https://fod.example.com/api/thenactions/3/" ]
        #then = [ "discard" ]
        then = [ "rate-limit:10000k" ]

        #

        print("\nphase 0")
        response = requests.get(endpoint_base, headers=fod_api_headers)
        assert response.status_code // 100 == 2
        resp_data = json.loads(response.content)
        print("get.response.data="+str(resp_data))

        #

        print("\nphase 0a")
        response = requests.get(endpoint_base+"?scope=applier", headers=fod_api_headers)
        assert response.status_code // 100 == 2
        resp_data = json.loads(response.content)
        print("get.response.data="+str(resp_data))

        #

        print("\nphase 1")
        route_id1 = self.add_route(endpoint_base, name="testrule_1m", comments=comments, source="0.0.0.0/0", sourceport="1000-2000", destination=ip1, destinationport="3000-4000,5000-6000", protocol=["tcp"], then=then, status="INACTIVE")
        print("created route: route_id1="+str(route_id1))

        #

        if True:
          print("\nphase 1a")
          data = {
              "status": "ACTIVE",
          }
          response = requests.patch(endpoint_base+str(route_id1)+"/", headers=fod_api_headers, data=json.dumps(data))
          print("response.content"+str(response.content))
          assert response.status_code // 100 == 2
          resp_data = json.loads(response.content)
          print("get.response.data="+str(resp_data))
          
          status_ret = self.wait_route_nonpending(endpoint_base, route_id1, response)

          ##

          print("\nphase 1b")
          data = {
              "status": "INACTIVE",
          }
          response = requests.patch(endpoint_base+str(route_id1)+"/", headers=fod_api_headers, data=json.dumps(data))
          print("response.content"+str(response.content))
          assert response.status_code // 100 == 2
          resp_data = json.loads(response.content)
          print("get.response.data="+str(resp_data))
          
          status_ret = self.wait_route_nonpending(endpoint_base, route_id1, response)

        #

        self.delete_route(endpoint_base, route_id1)

        #

        print("\nphase 2")
        route_id2 = self.add_route(endpoint_base, name="testrule_2", comments=comments, source="0.0.0.0/0", sourceport="1000-2000,3000-4000", destination=ip2, destinationport="3000-4000,5000-6000", protocol=["udp"], then=then)
        print("created route: route_id2="+str(route_id2))
        self.delete_route(endpoint_base, route_id2)

        #

        print("\nphase 3a")
        route_id3a = self.add_route(endpoint_base, name="testrule_3a", comments=comments, source="::/0", sourceport="1000-2000,3000-4000", destination="::1/128", destinationport="3000-4000,5000-6000", protocol=["udp"], then=then)
        print("created route: route_id3a="+str(route_id3a))
        self.delete_route(endpoint_base, route_id3a)

        #

        route_id_ary = { }
        for i in range(3, 10):
          print("\nphase "+str(i))
          route_id_ary[i] = self.add_route(endpoint_base, name="testrule_"+str(i), comments=comments, source="0.0.0.0/0", sourceport="1000-2000,3000-4000", destination=ip3, destinationport="3000-4000,5000-6000", protocol=["udp"], then=then)
          print("created route: route_id"+str(i)+"="+str(route_id_ary[i]))
  
        #
        
        for i in range(3, 10):
          print("\nphase 10."+str(i))
          self.delete_route(endpoint_base, route_id_ary[i])
 


