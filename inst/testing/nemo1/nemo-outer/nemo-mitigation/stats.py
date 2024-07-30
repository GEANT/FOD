
import os
import ipaddress

from paramiko import SSHClient, AutoAddPolicy


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

client = SSHClient()

client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

client.connect('192.168.50.2', username='freerouter', key_filename='/home/freerouter/.ssh/id_rsa')

command = "show policy-map flowspec v1 ipv4"

transport = client.get_transport()
channel = transport.open_session()
channel.exec_command(command)

output_list = []

while True:
    rl, wl, xl = select.select([channel],[],[],5.0)
    if len(rl) > 0:
        temp = channel.recv(1024)

        output_list.append(temp)
    templist = temp.decode("utf-8").split("\r")
    if "freerouter2#" in templist[-1]:
        break

client.close()

to_parse = output_list[1].decode("utf-8")

split_on_newline = to_parse.split("\r\n")

while("" in split_on_newline):
    split_on_newline.remove("")

for item in split_on_newline:
    if item[0:3] != "seq":
        line = item.split(" ")
        while ("" in line):
            line.remove("")
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
            with open(destination_filename, mode = "w") as message:
                message.write(content)
            command = "chown freerouter:freerouter /home/freerouter/template_result.txt"
            os.system(command)
            command = "cat /home/freerouter/template_result.txt"
            os.system(command)
