# Prerequistes

Operation of {{ product_name_short }} requires a router which is 

* BGP FlowSpec-capable and 

* supports JUNOS-specific NETCONF YANG models to inject/update the FlowSpec rules :
 
    + for BGP FlowSpec rules with IPv4 addresses: flow.route entries in configuration.routing-options 
   (NETCONF filter ``<configuration><routing-options><flow/></routing-options></configuration>``)
    + for BGP FlowSpec rules with IPv6 addresses: rib.flow entries in configuration.routing-options 
   (NETCONF filter ``<configuration><routing-options><rib><name>inet6.0</name><flow/></rib></routing-options></configuration>``)
    + or combined NETCONF FILTER: ``<configuration><routing-options><rib><name>inet6.0</name><flow/></rib><flow/></routing-options></configuration>``

* a NETCONF/ssh account on the router with appropriate rights to perform NETCONF RPC operations ``get_config`` and ``edit_config`` on the subtree given by NETCONF FILTERa above

example result of a NETCONF ``get_config`` query on a router with one IPv4-based BGP FlowSpec rule and one IPv6-based one:

<?xml version="1.0" encoding="UTF-8"?><data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
    <configuration xmlns="http://xml.juniper.net/xnm/1.1/xnm">

      <routing-options>

        <flow>
          <route>
            <name>{{ product_name_short }}_testrule1_529HMW</name>
            <then>
              <rate-limit>10000k</rate-limit>
            </then>
            <match>
              <protocol>tcp</protocol>
              <protocol>udp</protocol>
              <source-port>1-5</source-port>
              <source-port>10-11</source-port>
              <source-port>12</source-port>
              <destination>10.0.0.2/32</destination>
              <source>10.0.0.1/32</source>
            </match>
          </route>
        </flow>

        <rib>
          <name>inet6.0</name>
          <flow>
            <route>
              <name>{{ product_name_short }}_testipv6_MPSKD8</name>
              <then>
                <discard/>
              </then>
              <match>
                <protocol>icmp</protocol>
                <destination>
                  <prefix>1242:ac11::/127</prefix>
                </destination>
                <source>
                  <prefix>242:ac11:1::/127</prefix>
                </source>
              </match>
            </route>
          </flow>
        </rib>

      </routing-options>
    </configuration>
  </data>

* moreover, currently, for FlowSpec mitigation statisticis, i.e., drop counters in units bytes/s and packets/s per active FlowSpec rule, the router receiving the FlowSpec rules via NETCONF as well as all the involved routers which are receiving and installing FlowSpec rules via BGP, are required to support at least some part of a JUNIPER-specific SNMP enterprise MIB to provide these drop counters:
 
    + The two top-level OIDs for the drop counter tables are entries in the JUNIPER firewall MIB, registered at 1.3.6.1.4.1.2636.3.5 (https://oidref.com/1.3.6.1.4.1.2636.3.5 https://oidref.com/static/circitor/JUNIPER-FIREWALL-MIB.mib) (1.3.6.1.4.1.2636 = Juniper enterprise MIB)
        + 1.3.6.1.4.1.2636.3.5.2.1.4 for packets/s (https://oidref.com/1.3.6.1.4.1.2636.3.5.2.1.4)
        + 1.3.6.1.4.1.2636.3.5.2.1.5 for bytes/s (https://oidref.com/1.3.6.1.4.1.2636.3.5.2.1.5)


 


