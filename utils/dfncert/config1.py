[main]
debug = false
one_shot = true
raw = false
silent = false
host = localhost
port = 12345

# List of routers
#routers = router.1, router.2
routers = router.1

# Configuration for router.1
[router.1]
netconf_port = 830
ip_address = 192.168.50.1
username = admin
password = admin

## Configuration for router.2
#[router.2]
#netconf_port = 830
#ip_address = Y
#username = user
#password = pass

