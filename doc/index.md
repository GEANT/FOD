# Description

Firewall on Demand applies, via Netconf, flow rules to a network device.
These rules are then propagated via e-bgp to peering routers. Each user
is authenticated against shibboleth. Authorization is performed via a
combination of a Shibboleth attribute and the peer network address range
that the user originates from. FoD is meant to operate over this
architecture:

```
    +-----------+          +------------+        +------------+  
    |   FoD     | NETCONF  | flowspec   | ebgp   |   router   |  
    | web app   +----------> device     +-------->            |  
    +-----------+          +------+-----+        +------------+  
                                  | ebgp  
                                  |  
                           +------v-----+  
                           |   router   |  
                           |            |  
                           +------------+  
```

NETCONF is chosen as the mgmt protocol to apply rules to a single
flowspec capable device. Rules are then propagated via igbp to all
flowspec capable routers. Of course FoD could apply rules directly (via
NETCONF always) to a router and then ibgp would do the rest. In GRNET’s
case the flowspec capable device is an EX4200.

> ** Attention **
>
> Make sure your FoD server has SSH access to your flowspec device.

# Index

* [Prerequisites/Generic](./prerequisites/generic.md)

* [Installation/v1.7/Generic](./installation/v1.7/generic.md)
* [Installation/v1.7/DebianAndUbuntu](./installation/v1.7/debian_ubuntu.md)
* [Installation/v1.7/CentOS](./installation/v1.7/centos.md)
* [Installation/v1.7/Docker](./installation/v1.7/docker.md)
* [Installation/v1.7/Extra Docker Container for Testing FoD without Router Hardware](./installation/v1.7/docker_extra.md)

* [Configuration/v1.7](./configuration/configuration-v1.7.md)

* [Basic Administration and Usage/v1.7](./administration_and_usage/basic_administration_and_usage-v1.7.md)

* [REST API/v1.7](./api/api-v1.7.md)

* [Design Overview](./development/design-overview.md)

# Contact 

You can find more about FoD or raise your issues at [Github FoD
repository].

You can contact us directly at fod{at}lists[dot]geant(.)org

# GRNET Contact 

You can find more about FoD or raise your issues at [Github FoD
repository].

You can contact GRNET at dev{at}noc[dot]grnet(.)gr

# Repositories

  - [GEANT Github FoD repository](https://github.com/GEANT/FOD)

  - [GRNET Github FoD repository](https://github.com/grnet/flowspy)


## Copyright and license

Copyright © 2017-2023 GÈANT GN4-2/GN4-3/GN5-1 Project

Copyright © 2010-2017 Greek Research and Technology Network (GRNET S.A.)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
