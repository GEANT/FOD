#!/usr/bin/env python
# Copyright 2011 Leonidas Poulopoulos (GRNET S.A - NOC)
# Copyright 2019 Tomas Cejka (CESNET): fixed namespace
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re as re_
import os
from lxml import etree as etree_

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_netconf_xml.log", False)

new_ele = lambda tag, attrs={}, **extra: etree_.Element(tag, attrs, **extra)
sub_ele = lambda parent, tag, attrs={}, **extra: etree_.SubElement(parent, tag, attrs, **extra)

NETCONFOPERATION = '{urn:ietf:params:xml:ns:netconf:base:1.0}operation'

# Globals
Tag_pattern_ = re_.compile(r'({.*})?(.*)')
STRING_CLEANUP_PAT = re_.compile(r"[\n\r\s]+")

class Device(object):

    def __init__(self):
        self.name = ''
        self.domain_name = ''
        self.interfaces = []
        self.vlans = []
        self.routing_options = []
        self.protocols = {}


    def export(self, netconf_config=False):
        config = new_ele("configuration", nsmap={None: "http://xml.juniper.net/xnm/1.1/xnm"})
        device = new_ele('system')
        if self.name:
            sub_ele(device, "host-name").text = self.name
        if self.domain_name:
            sub_ele(device, "domain-name").text = self.domain_name
        if len(device.getchildren()):
            config.append(device)
        interfaces = new_ele('interfaces')
        if len(self.interfaces):
            for interface in self.interfaces:
                if (interface):
                    interfaces.append(interface.export())
            config.append(interfaces)
        vlans = new_ele('vlans')
        if len(self.vlans):
            for vlan in self.vlans:
                if (vlan):
                    vlans.append(vlan.export())
            config.append(vlans)
        routing_options = new_ele('routing-options')
        if len(self.routing_options):
            for ro in self.routing_options:
                if (ro):
                    routing_options.append(ro.export())
            config.append(routing_options)
        protocols = new_ele('protocols')
        if len(self.protocols.keys()):
            for pro in self.protocols.keys():
                protocols.append(self.protocols[pro].export())
            config.append(protocols)
        if netconf_config:
            conf = new_ele("config", nsmap={None: "urn:ietf:params:xml:ns:netconf:base:1.0"})
            conf.append(config)
            config = conf
        if len(config.getchildren()):
            return config
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'interfaces':
            for node in child_:
                obj_ = Interface()
                obj_.build(node)
                self.interfaces.append(obj_)
        if nodeName_ == 'vlans':
            for node in child_:
                obj_ = Vlan()
                obj_.build(node)
                self.vlans.append(obj_) 
        if nodeName_ == 'routing-options':
            for node in child_:
                childName_ = Tag_pattern_.match(node.tag).groups()[-1]
                logger.info("jncdevice::Device::build(): routing-options childName_="+str(childName_))

                flow_node = None
                if childName_ == 'flow':
                   flow_node = node
                elif childName_ == 'rib': # IPv6 rule support
                   for node2 in node:
                     childName_ = Tag_pattern_.match(node2.tag).groups()[-1]
                     if childName_ == 'flow':
                       flow_node = node2
                       break

                # *************** FLOW ****************
                if flow_node != None:
                    obj_ = Flow()
                    obj_.build(flow_node)
                    logger.info("jncdevice::Device::build(): => flow_node="+str(flow_node)+" => obj_="+str(obj_))
                    self.routing_options.append(obj_)

        if nodeName_ == 'protocols':
            for node in child_:
                childName_ = Tag_pattern_.match(node.tag).groups()[-1]
                if childName_ == 'l2circuit':
                    obj_ = L2Circuit()
                    obj_.build(node)
                    self.protocols['l2circuit'] = obj_
                if childName_ == 'oam':
                    obj_ = OAM()
                    obj_.build(node)
                    self.protocols['oam']=obj_

class DeviceDiff(Device):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DeviceDiff, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance

devdiff = DeviceDiff()

class Interface(object):
    def __repr__(self):
        return "Name %s, Description: %s" % (self.name, self.description)

    def __init__(self,name=None,description=None):
        self.name = name
        self.bundle = ''
        self.description = description
        self.vlantagging = ''
        self.tunneldict = []
        # Unit dict is a list of dictionaries containing units to
        # interfaces, should be index like {'unit': 'name',
        # 'description': 'foo', 'vlanid': 'bar', 'addresses': ['IPv4addresses', 'IPv6addresses']}
        self.unitdict = []

    def get_descr(self): return self.description
    def set_descr(self,x):
        global devdiff
        self.description = x
        intdiff = Interface(name=self.name, description=self.description)
        if len(devdiff.interfaces) > 0:
            deviffIntNames = [x.name for x in devdiff.interfaces]
            if self.name in deviffIntNames:
                for interface in devdiff.interfaces:
                    if interface.name == self.name:
                        devdiff.interfaces.remove(interface)
        devdiff.interfaces.append(intdiff)
    # The new_description attribute initiates the DeviceDiff class
    new_description = property(get_descr,set_descr)
        
    def export(self):
        ifce = new_ele('interface')
        if self.name:
            sub_ele(ifce, "name").text = self.name
        if self.description:
            sub_ele(ifce, "description").text = self.description
        if len(self.unitdict):
            for unit in self.unitdict:
                if unit:
                    ifce.append(unit.export())
        if len(ifce.getchildren()):
            return ifce
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        elif nodeName_ == 'description':
            description_ = child_.text
            description_ = re_.sub(STRING_CLEANUP_PAT, " ", description_).strip()
            self.description = description_
        elif nodeName_ == 'unit':
            obj_ = Unit()
            obj_.build(child_)
            self.unitdict.append(obj_)
        
class Vlan:
    def __repr__(self):
        return "Name %s, Vlan-Id: %s" % (self.name, self.vlan_id)
    def __init__(self):
        self.name = ''
        self.vlan_id = ''
        self.operation = None
                
    
    def export(self):
        if self.operation:
            vlan = new_ele('vlan', {NETCONFOPERATION: self.operation})
        else:
            vlan = new_ele('vlan')
        if self.name:
            sub_ele(vlan, "name").text = self.name
        if self.vlan_id:
            sub_ele(vlan, "vlan-id").text = self.vlan_id
        if self.name and self.vlan_id:
            return vlan
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        elif nodeName_ == 'vlan-id':
            vlanid_ = child_.text
            vlanid_ = re_.sub(STRING_CLEANUP_PAT, " ", vlanid_).strip()
            self.vlan_id = vlanid_

class Unit:
    def __repr__(self):
        return "Name %s, Description: %s" % (self.name, self.description)    
    def __init__(self):
        self.name = ''
        self.description = ''
        self.vlan_id = ''
        self.encapsulation = ''
        self.apply_groups = ''
        self.input_vlan_map = {'swap':False, 'vlan_id':''}
        self.output_vlan_map = {'swap':False, 'vlan_id':''}
        #family: {'name':(one of inet, inet6, mpls, iso...), 'addresses':[], 'mtu':'', 'accounting': {}, 'vlan_members':['',''], 'vlan_members_operation':'delete' or 'replace' or 'merge'(this is the default so omit)}
        self.family = []
        
        
    def export(self):
        unit = new_ele('unit')
        if self.name:
            sub_ele(unit, "name").text = self.name
        if self.description:
            sub_ele(unit, "description").text = self.description
        if self.apply_groups:
            sub_ele(unit, "apply-groups").text = self.apply_groups
        if self.encapsulation:
            sub_ele(unit, "encapsulation").text = self.encapsulation
        if self.vlan_id:
            sub_ele(unit, "vlan-id").text = self.vlan_id
        if self.input_vlan_map['swap'] or self.input_vlan_map['vlan_id']:
            ivm = new_ele('input-vlan-map')
            sub_ele(ivm,"swap")
            if self.input_vlan_map['vlan_id']:
                sub_ele(ivm,"vlan-id").text = self.input_vlan_map['vlan_id']
            unit.append(ivm)
        if self.output_vlan_map['swap'] or self.output_vlan_map['vlan_id']:
            ovm = new_ele('output-vlan-map')
            sub_ele(ovm,"swap")
            if self.output_vlan_map['vlan_id']:
                sub_ele(ovm,"vlan-id").text = self.output_vlan_map['vlan_id']
            unit.append(ovm)
        if len(self.family):
            family = new_ele("family")
            for member in self.family:
                try:
                    if member['name']:
                        mem_name = new_ele(member['name'])
                except:
                    pass
                try:
                    if len(member['addresses']):
                        for address in member['addresses']:
                            addr = new_ele('address')
                            sub_ele(addr,"name").text = address
                            mem_name.append(addr)
                except:
                    pass
                try:
                    if member['mtu']:
                        sub_ele(mem_name, "mtu").text = member['mtu']
                    family.append(mem_name)
                except:
                    pass
                try:
                    if member['vlan_members']:
                        try:
                            if member['vlan_members_operation']:
                                operation = member['vlan_members_operation']
                        except:
                            operation = None
                        ethernet_switching = sub_ele(family,'ethernet-switching')
                        vlan = sub_ele(ethernet_switching, 'vlan')
                        for vlan_item in member['vlan_members']:
                            if operation:
                                vmem = sub_ele(vlan,'members', {NETCONFOPERATION: operation})
                            else:
                                vmem = sub_ele(vlan,'members')
                            vmem.text = vlan_item
                except:
                    pass
            unit.append(family)
        if len(unit.getchildren()):
            return unit
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'encapsulation':
            encapsulation_ = child_.text
            encapsulation_ = re_.sub(STRING_CLEANUP_PAT, " ", encapsulation_).strip()
            self.encapsulation = encapsulation_
        if nodeName_ == 'apply-groups':
            apply_groups_ = child_.text
            apply_groups_ = re_.sub(STRING_CLEANUP_PAT, " ", apply_groups_).strip()
            self.apply_groups = apply_groups_
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        elif nodeName_ == 'vlan-id':
            vlanid_ = child_.text
            vlanid_ = re_.sub(STRING_CLEANUP_PAT, " ", vlanid_).strip()
            self.vlan_id = vlanid_
        elif nodeName_ == 'description':
            description_ = child_.text
            description_ = re_.sub(STRING_CLEANUP_PAT, " ", description_).strip()
            self.description = description_
        elif nodeName_ == 'input-vlan-map':
            for node in child_:
                childName_ = Tag_pattern_.match(node.tag).groups()[-1]
                if childName_ == 'swap':
                     self.input_vlan_map['swap'] = True
                if childName_ == 'vlan-id':
                     vlan_id = node.text
                     vlan_id = re_.sub(STRING_CLEANUP_PAT, " ", vlan_id).strip()
                     self.input_vlan_map['vlan_id'] = vlan_id
        elif nodeName_ == 'output-vlan-map':
            for node in child_:
                childName_ = Tag_pattern_.match(node.tag).groups()[-1]
                if childName_ == 'swap':
                     self.output_vlan_map['swap'] = True
                if childName_ == 'vlan-id':
                     vlan_id = node.text
                     vlan_id = re_.sub(STRING_CLEANUP_PAT, " ", vlan_id).strip()
                     self.output_vlan_map['vlan_id'] = vlan_id
        elif nodeName_ == 'family':
            vlan_unit_list = []
            family_dict = {}
            for node in child_:
                childName_ = Tag_pattern_.match(node.tag).groups()[-1]
                # *************** ETHERNET-SWITCHING ****************
                if childName_ == 'ethernet-switching':
                    for grandChild_ in node:
                        grandchildName_ = Tag_pattern_.match(grandChild_.tag).groups()[-1]
                        if grandchildName_ == 'port-mode':
                            pmode = grandChild_.text
                            pmode = re_.sub(STRING_CLEANUP_PAT, " ", pmode).strip()
                            family_dict['port-mode'] = pmode
                        elif grandchildName_ == 'vlan':
                            for vlan_member in grandChild_:
                                vlanmem = vlan_member.text
                                vlanmem = re_.sub(STRING_CLEANUP_PAT, " ", vlanmem).strip()
                                vlan_unit_list.append(vlanmem)
                            family_dict['vlan_members'] = vlan_unit_list
                    self.family.append(family_dict)

class Flow(object):
    def __init__(self, is_ipv4 = True):
        self.routes = []      
        self.is_ipv4 = is_ipv4
        logger.info("jncdevice::Flow::Flow(): is_ipv4="+str(is_ipv4))
        
    def export(self):
        
        flow = new_ele('flow')

        if self.is_ipv4:
          flow0 = flow
        else:
          flow0 = new_ele('rib')
          sub_ele(flow0, 'name').text = 'inet6.0'
          flow0.append(flow)

        if len(self.routes):
            for route in self.routes:
                flow.append(route.export()) 
            return flow0
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
            if nodeName_ == 'route':
                obj_ = Route()
                obj_.build(child_)
                self.routes.append(obj_)

class Route(object):    
    def __init__(self):
        self.name = ''
        self.operation = None
        self.match = {
            "destination": [],
            "destination-v6": [],
            "source": [],
            "source-v6": [],
            "protocol": [],
            "port": [],
            "destination-port": [],
            "source-port": [],
            "icmp-code": [],
            "icmp-type": [],
            "tcp-flags": [],
            "packet-length": [],
            "dscp": [],
            "fragment": []
        }
        ''' Match is a dict with list values
        example: self. match = {
            "destination": [<ip-prefix(es)>],
            "source": [<ip-prefix(es)>],
            "protocol": [<numeric-expression(s)>],
            "port": [<numeric-expression(s)>],
            "destination-port": [<numeric-expression(s)>]
            "source-port": [<numeric-expression(s)>],
            "icmp-code": [<numeric-expression(s)>],
            "icmp-type": [<numeric-expression(s)>],
            "tcp-flags": [<bitwise-expression(s)>],
            "packet-length": [<numeric-expression(s)>],
            "dscp": [<numeric-expression(s)>],
            "fragment": [
                "dont-fragment" 
                "not-a-fragment"
                "is-fragment"
                "first-fragment"
                "last-fragment"
            ]
        '''
        self.then = {
            "accept": False,
            "discard": False,
            "community": False,
            "next-term": False,
            "rate-limit": False,
            "sample": False,
            "routing-instance": False
        }
        '''Then is a dict (have to see about this in the future:
        self.then = {
        "accept": True/False,
        "discard": True/False,
        "community": "<name>"/False,
        "next-term": True/False,
        "rate-limit": <rate>/False,
        "sample": True/False,
        "routing-instance": "<RouteTarget extended community>"
        }
        '''
        
    def export(self):
        if self.operation:
           ro = new_ele('route', {NETCONFOPERATION: self.operation})
        else:
            ro = new_ele('route')
        if self.name:
            sub_ele(ro, "name").text = self.name
        match = new_ele("match")
        for key in self.match:
            if self.match[key]:
                if key=="destination-v6":
                    for value in self.match[key]:
                        newsub = sub_ele(match, "destination")
                        sub_ele(newsub, "prefix").text = value
                elif key=="source-v6":
                    for value in self.match[key]:
                        newsub = sub_ele(match, "source")
                        sub_ele(newsub, "prefix").text = value
                else:
                    for value in self.match[key]:
                        sub_ele(match,key).text = value
        if match.getchildren():
            ro.append(match)
        then = new_ele("then")
        for key in self.then:
            if self.then[key]:
                if self.then[key] != True and self.then[key] != False:
                    sub_ele(then,key).text = self.then[key]
                else:
                    sub_ele(then,key)
        if then.getchildren():
            ro.append(then)
        if ro.getchildren():
            return ro
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        elif nodeName_ == 'match':
            for grandChild_ in child_:
                grandChildName_ = Tag_pattern_.match(grandChild_.tag).groups()[-1]
                grandChildText = grandChild_.text
                grandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandChildText).strip()
                self.match[grandChildName_].append(grandChildText)
        elif nodeName_ == 'then':
            for grandChild_ in child_:
                grandChildName_ = Tag_pattern_.match(grandChild_.tag).groups()[-1]
                self.then[grandChildName_] = True

class Parser(object):
    def __init__(self, confile=None):
        self.confile = confile
    
    def export(self):
        if self.confile:
            confile = self.confile
            if os.path.isfile(confile):
                # probably it's a file...
                configuration = self.parse()
            else:
                configuration = self.parseString()
            return configuration
        else:
            return None

    def parsexml_(self, *args, **kwargs):
        if 'parser' not in kwargs:
            kwargs['parser'] = etree_.ETCompatXMLParser()
        doc = etree_.parse(*args, **kwargs)
        return doc
    
    def parse(self):
        '''Normally this would be an rpc_reply in case of netconf invoking or
        a configuration element in case of normal parsing'''
        doc = self.parsexml_(self.confile)
        rootNode = doc.getroot()
        #NetCONF invoked
        rootNodeTag = Tag_pattern_.match(rootNode.tag).groups()[-1]
        if rootNodeTag == 'rpc-reply':
            rootNode = rootNode.xpath("//*[local-name()='configuration']")[0]
        if rootNodeTag == 'data':
            rootNode = rootNode.xpath("//*[local-name()='configuration']")[0]
        rootObj = Device()
        rootObj.build(rootNode)
        return rootObj
    
    def parseString(self):
        '''Normally this would be an rpc_reply in case of netconf invoking or
        a configuration element in case of normal parsing'''
        #from StringIO import StringIO
        from io import StringIO
        from io import BytesIO
        doc = self.parsexml_(BytesIO(self.confile.encode()))
        rootNode = doc.getroot()
        rootNodeTag = Tag_pattern_.match(rootNode.tag).groups()[-1]
        if rootNodeTag == 'rpc-reply':
            rootNode = rootNode.xpath("//*[local-name()='configuration']")[0]
        if rootNodeTag == 'data':
            rootNode = rootNode.xpath("//*[local-name()='configuration']")[0]
        rootObj = Device()
        rootObj.build(rootNode)
        return rootObj

class L2Circuit(object):
    def __init__(self):
        self.neighbors = []        
        
    def export(self):
        l2circuit = new_ele('l2circuit')
        if len(self.neighbors):
            for neighbor in self.neighbors:
                try:
                    l2circuit.append(neighbor.export())
                except TypeError:
                    pass  
            return l2circuit
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
            if nodeName_ == 'neighbor':
                obj_ = L2CNeighbor()
                obj_.build(child_)
                self.neighbors.append(obj_)

class OAM(object):
    def __init__(self):
        self.ethernet = ''        
        
    def export(self):
        oam = new_ele('oam')
        if (self.ethernet):
            try:
                oam.append(self.ethernet.export())
            except TypeError:
                pass
            return oam
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
            if nodeName_ == 'ethernet':
                obj_ = EthernetOAM()
                obj_.build(child_)
                self.ethernet = obj_


class EthernetOAM(object):
    def __init__(self):
        self.connectivity_fault_management = ''       
        
    def export(self):
        ethoam = new_ele('ethernet')
        if (self.connectivity_fault_management):
            try:
                ethoam.append(self.connectivity_fault_management.export())
            except TypeError:
                pass  
            return ethoam
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
            if nodeName_ == 'connectivity-fault-management':
                obj_ = EthernetOAMCFM()
                obj_.build(child_)
                self.connectivity_fault_management = obj_

class EthernetOAMCFM(object):
    def __init__(self):
        self.maintenance_domains = []        
        
    def export(self):
        ethoamcfm = new_ele('connectivity-fault-management')
        if len(self.maintenance_domains):
            for md in self.maintenance_domains:
                try:
                    ethoamcfm.append(md.export())
                except TypeError:
                    pass  
            return ethoamcfm
        else:
            return False

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
            if nodeName_ == 'maintenance-domain':
                obj_ = CFMMD()
                obj_.build(child_)
                self.maintenance_domains.append(obj_)

class CFMMD(object):
    def __repr__(self):
        return "MD: %s Lvl: %s" % (self.name, self.level)

    def __init__(self):
        self.name = ''
        self.level = ''
        self.operation = None
        self.maintenance_association = ''
    
    def export(self):
        if self.operation:
           md = new_ele('maintenance-domain', {NETCONFOPERATION:self.operation})
        else:
            md = new_ele('maintenance-domain')
        if self.name:
            sub_ele(md, "name").text = self.name
        if self.level:
            sub_ele(md, "level").text = str(self.level)
        if self.maintenance_association:
            md.append(self.maintenance_association.export())    
        return md
    
    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        if nodeName_ == 'level':
            level_ = child_.text
            level_ = re_.sub(STRING_CLEANUP_PAT, " ", level_).strip()
            self.level = level_
        if nodeName_ == 'maintenance-association':
            obj_ = MaintenanceAssoc()
            obj_.build(child_)
            self.maintenance_association = obj_
        #TODO: Implement MA

class MaintenanceAssoc(object):
    def __repr__(self):
        return "MA: %s MEP: %s, Ifce: %s, Dir: %s" % (self.name, self.mep['name'], self.mep['ifce'], self.mep['direction'])

    def __init__(self, name=None, cc_interval="1s", cc_lt="3", cc_hi="7", cc_ifce_tlv=True, cc_port_tlv=False, mip_hf=None, mep_name=None, mep_ifce=None, mep_ifce_vlan=None, mep_direction=None, mep_auto_disco=True, mep_rem_name=None, sla_iter_profiles=[]):
        self.name = name
        self.operation = None
        self.continuity_check = {"interval":cc_interval,
                                 "loss_threshold": cc_lt,
                                 "hold_interval": cc_hi,
                                 "interface_status_tlv": cc_ifce_tlv,
                                 "port_status_tlv": cc_port_tlv
                                 }
        self.mip_half_function = mip_hf
        self.mep = {"name": mep_name,
                    "ifce": mep_ifce,
                    "ifce_vlan": mep_ifce_vlan,
                    "direction": mep_direction,
                    "auto_discovery": mep_auto_disco,
                    "remote_mep":{"name":mep_rem_name, "sla_iterator_profiles": sla_iter_profiles}
                    }
    
    def export(self):
        if self.operation:
            ma = new_ele("maintenance-association", {NETCONFOPERATION: self.operation})
        else:
            ma = new_ele("maintenance-association")
        if self.name:
            sub_ele(ma, "name").text = self.name
        if self.mip_half_function:
            sub_ele(ma, "mip-half-function").text = self.mip_half_function
        cc = sub_ele(ma, "continuity-check")
        if self.continuity_check['interval']:
            sub_ele(cc, "interval").text = self.continuity_check['interval']
        if self.continuity_check['loss_threshold']:
            sub_ele(cc, "loss-threshold").text = self.continuity_check['loss_threshold']
        if self.continuity_check['hold_interval']:
            sub_ele(cc, "hold-interval").text = self.continuity_check['hold_interval']
        if self.continuity_check['interface_status_tlv']:
            sub_ele(cc, "interface-status-tlv")
        if self.continuity_check['port_status_tlv']:
            sub_ele(cc, "port-status-tlv")
        mep = sub_ele(ma, "mep")
        if self.mep['name']:
            sub_ele(mep, 'name').text = self.mep['name']
        if self.mep['direction']:
            sub_ele(mep, 'direction').text = self.mep['direction']
        if self.mep['auto_discovery']:
            sub_ele(mep, 'auto-discovery')
        if self.mep['ifce']:
            ifce = sub_ele(mep, 'interface')
            sub_ele(ifce, "interface-name").text = self.mep['ifce']
            if self.mep['ifce_vlan']:
                sub_ele(ifce, "vlan-id").text = self.mep['ifce_vlan']
        if self.mep['remote_mep']['name'] and self.mep['remote_mep']['sla_iterator_profiles']:
            rmep = sub_ele(mep, "remote-mep")
            sub_ele(rmep, 'name').text = self.mep['remote_mep']['name']
            for sip in self.mep['remote_mep']['sla_iterator_profiles']:
                slaip = sub_ele(rmep, 'sla-iterator-profile')
                sub_ele(slaip, 'name').text = sip
        return ma
    
    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        if nodeName_ == 'mip-half-function':
            mhf_ = child_.text
            mhf_ = re_.sub(STRING_CLEANUP_PAT, " ", mhf_).strip()
            self.mip_half_function = mhf_
        if nodeName_ == 'continuity-check':
            for grandChild_ in child_:
                grandChildName_ = Tag_pattern_.match(grandChild_.tag).groups()[-1]
                if grandChildName_ == 'interval':
                    grandChildText = grandChild_.text
                    grandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandChildText).strip()
                    self.continuity_check['interval'] = grandChildText
                if grandChildName_ == 'loss-threshold':
                    grandChildText = grandChild_.text
                    grandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandChildText).strip()
                    self.continuity_check['loss_threshold'] = grandChildText
                if grandChildName_ == 'hold-interval':
                    grandChildText = grandChild_.text
                    grandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandChildText).strip()
                    self.continuity_check['hold_interval'] = grandChildText
                if grandChildName_ == 'interface-status-tlv':
                    self.continuity_check['interface_status_tlv'] = True
                if grandChildName_ == 'port-status-tlv':
                    self.continuity_check['port_status_tlv'] = True
        if nodeName_ == 'mep':
            for grandChild_ in child_:
                grandChildName_ = Tag_pattern_.match(grandChild_.tag).groups()[-1]
                if grandChildName_ == 'name':
                    grandChildText = grandChild_.text
                    grandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandChildText).strip()
                    self.mep['name'] = grandChildText
                if grandChildName_ == 'interface':
                    for grandgrandChild_ in grandChild_:
                        grandgrandChildName_ = Tag_pattern_.match(grandgrandChild_.tag).groups()[-1]
                        if grandgrandChildName_ == 'interface-name':
                            grandgrandChildText = grandgrandChild_.text
                            grandgrandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandgrandChildText).strip()
                            self.mep['ifce'] = grandgrandChildText
                        if grandgrandChildName_ == 'vlan-id':
                            grandgrandChildText = grandgrandChild_.text
                            grandgrandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandgrandChildText).strip()
                            self.mep['ifce_vlan'] = grandgrandChildText
                if grandChildName_ == 'direction':
                    grandChildText = grandChild_.text
                    grandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandChildText).strip()
                    self.mep['direction'] = grandChildText
                if grandChildName_ == 'auto-discovery':
                    self.mep['auto_discovery'] = True
                if grandChildName_ == 'remote-mep':
                    self.mep['remote_mep']['sla_iterator_profiles'] = []
                    for grandgrandChild_ in grandChild_:
                        grandgrandChildName_ = Tag_pattern_.match(grandgrandChild_.tag).groups()[-1]
                        if grandgrandChildName_ == 'name':
                            grandgrandChildText = grandgrandChild_.text
                            grandgrandChildText = re_.sub(STRING_CLEANUP_PAT, " ", grandgrandChildText).strip()
                            self.mep['remote_mep']['name'] = grandgrandChildText
                        if grandgrandChildName_ == 'sla-iterator-profile':
                            for grand3Child_ in grandgrandChild_:
                                grand3ChildName_ = Tag_pattern_.match(grand3Child_.tag).groups()[-1]
                                if grand3ChildName_ == 'name':
                                    grand3ChildText = grand3Child_.text
                                    grand3ChildText = re_.sub(STRING_CLEANUP_PAT, " ", grand3ChildText).strip()
                                    self.mep['remote_mep']['sla_iterator_profiles'].append(grand3ChildText)

class L2CNeighbor(object):
    def __repr__(self):
        return "Name %s" % (self.name)   
    def __init__(self):
        self.name = ''
        self.interfaces = []
    
    def export(self):
        l2cneighbor = new_ele('neighbor')
        if self.name:
            sub_ele(l2cneighbor, "name").text = self.name
        if len(self.interfaces):
            for ifce in self.interfaces:
                l2cneighbor.append(ifce.export())
            return l2cneighbor
        else:
            return False
    
    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        if nodeName_ == 'interface':
            obj_ = L2CIfce()
            obj_.build(child_)
            self.interfaces.append(obj_)

class L2CIfce(object):
    def __repr__(self):
        return "Name %s, VCID: %s, MTU: %s" % (self.name, self.virtual_circuit_id, self.mtu) 
    def __init__(self):
        self.name = ''
        self.virtual_circuit_id = ''
        self.description = ''
        self.mtu = ''
        self.no_control_word = False
        
        
    def export(self):
        ifce = new_ele('interface')
        if self.name:
            sub_ele(ifce, "name").text = self.name
        if self.virtual_circuit_id:
            sub_ele(ifce, "virtual-circuit-id").text = str(self.virtual_circuit_id)
        if self.description:
            sub_ele(ifce, "description").text = self.description
        if self.mtu:
            sub_ele(ifce, "mtu").text = str(self.mtu)
        if self.no_control_word:
            sub_ele(ifce, "no-control-word")
        return ifce

    def build(self, node):
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, nodeName_)

    def buildChildren(self, child_, nodeName_, from_subclass=False):
        if nodeName_ == 'name':
            name_ = child_.text
            name_ = re_.sub(STRING_CLEANUP_PAT, " ", name_).strip()
            self.name = name_
        if nodeName_ == 'virtual-circuit-id':
            virtual_circuit_id_ = child_.text
            virtual_circuit_id_ = re_.sub(STRING_CLEANUP_PAT, " ", virtual_circuit_id_).strip()
            self.virtual_circuit_id = virtual_circuit_id_
        if nodeName_ == 'description':
            description_ = child_.text
            description_ = re_.sub(STRING_CLEANUP_PAT, " ", description_).strip()
            self.description = description_
        if nodeName_ == 'mtu':
            mtu_ = child_.text
            mtu_ = re_.sub(STRING_CLEANUP_PAT, " ", mtu_).strip()
            self.mtu = mtu_
        if nodeName_ == 'no-control-word':
            self.no_control_word = True

   

