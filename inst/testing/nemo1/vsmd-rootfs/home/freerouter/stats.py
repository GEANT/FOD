
import os
import sys
import ipaddress

from paramiko import SSHClient, AutoAddPolicy

#import logging
#logging.basicConfig(level=logging.DEBUG)
#logger = logging.getLogger("paramiko.transport")
#logger.info('message')

import paramiko
import select

import time
from time import time

from jinja2 import Environment, FileSystemLoader

environment = Environment(loader = FileSystemLoader("/home/freerouter/templates/"))
template = environment.get_template("template.txt")

destination_filename = "/home/freerouter/template_result.txt"
command = "chown freerouter:freerouter /home/freerouter/template_result.txt"
os.system(command)

#client = SSHClient()
#
#client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#
##print ("ok0")
#
##client.connect('10.197.36.3', username='admin', key_filename='/home/freerouter/.ssh/id_rsa')
#client.connect('10.197.36.3', username='admin', password='netconf', key_filename=None)
#
##print("ok1")
#
#command = "show policy-map flowspec v1 ipv4"
#
#transport = client.get_transport()
#channel = transport.open_session()
#channel.exec_command(command)
#
#output_list = []
#
#while True:
#    rl, wl, xl = select.select([channel],[],[],5.0)
#    if len(rl) > 0:
#        temp = channel.recv(1024)
#
#        output_list.append(temp)
#    print ("output_list="+(str(output_list)))
#    print ("temp="+str(temp))
#    templist = temp.decode("utf-8", errors='ignore').split("\r")
#    print ("templist="+(str(templist)))
#    #if "freerouter2#" in templist[-1]:
#    if "311ba8eb5ac2#" in templist[-1]:
#        break
#
#channel.exec_command(command)
#
#client.close()

import fileinput

#

#to_parse = output_list[1].decode("utf-8")
#
#split_on_newline = to_parse.split("\r\n")
#
#while("" in split_on_newline):
#    split_on_newline.remove("")

#for item in split_on_newline:

for item in fileinput.input():
    item.rstrip()
    #print("item="+str(item))

    if item[0:3] != "seq":
        #print("item2="+str(item))

        line = item.split(" ")
        while ("" in line):
            line.remove("")
        #print("line="+str(line))

        if len(line) > 11:
            afi = "IPv4"
            dest_net = line[14]
            source_net = line[11]
            proto = line[10].split("-")[0]
            sport = line[13].split("-")[0]
            dport = line[16].split("-")[0]
            match = line[7].split("=")[1].replace(")", "")
            match_left = match.split("(")[0]
            match_right = match.split("(")[1]
            drop = line[9].split("=")[1].replace(")", "")
            drop_left = drop.split("(")[0]
            drop_right = drop.split("(")[1]
            source_mask = ipaddress.ip_address(line[12]).exploded
            source_mask = 32 - 4 * str(source_mask).count("0")
            dest_mask = ipaddress.ip_address(line[15]).exploded

            dest_mask = 32 - 4 * str(dest_mask).count("0")
            content = template.render(
                    afi = afi,
                    dest_net = dest_net,
                    dest_mask = dest_mask,
                    source_net = source_net,
                    source_mask = source_mask,
                    proto = proto,
                    dport = dport,
                    sport = sport,
                    match_left = match_left,
                    match_right = match_right,
                    drop_left = drop_left,
                    drop_right = drop_right
                    )
            #print("content="+str(content))

            with open(destination_filename, mode = "w") as message:
                message.write(content)
            command = "chown freerouter:freerouter /home/freerouter/template_result.txt"
            os.system(command)
            command = "cat /home/freerouter/template_result.txt"
            os.system(command)
