
from accounts.models import *
from peers.models import *

def init_admin_user(admin_username, admin_pwd, admin_email_addr, admin_peer_name, admin_peer_ip_prefix):
    u = User.objects.create_user(username=admin_username, email=admin_email_addr, password=admin_pwd)
    u.is_superuser = True
    u.is_staff = True
    u.save()
    pr = PeerRange(network = admin_peer_ip_prefix)
    pr.save()
    p = Peer(peer_name = admin_peer_name, peer_tag = admin_peer_name)
    p.save()
    p.networks.add(pr)
    ua = UserProfile()
    ua.user = u
    ua.save()
    ua.peers.add(p)


