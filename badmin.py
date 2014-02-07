#!/usr/bin/env python
import argparse
from olwclient import *
import socket


def _get_hosts(host_names):
    if len(host_names) == 1 and host_names[0] == "all":
        hosts = Host.get_host_list(connection)
    elif len(host_names) == 0:
        hosts = [Host(host_name=socket.gethostname())]
    else:
        hosts = [Host(host_name=host_name) for host_name in host_names]
    return hosts


def hclose(args):
    for host in _get_hosts(args.host_names):
        try:
            host.close()
            print "Olosed host: %s" % host.host_name
        except RemoteException as e:
            print "Unable to close host: %s: %s" % (host.host_name, e.message)

def hopen(args):
    for host in _get_hosts(args.host_names):
        try:
            host.close()
            print "Opened host: %s" % host.host_name
        except RemoteException as e:
            print "Unable to open host: %s: %s" % (host.host_name, e.message)


parser = argparse.ArgumentParser(description='Badmin provides a set of commands to control and monitor Openlava.')
OpenLavaConnection.configure_argument_list(parser)
subparsers = parser.add_subparsers(help='sub-command help')

phclose = subparsers.add_parser('hclose', help='Closes  batch  server hosts.')
phclose.add_argument("host_names", nargs='*', type=str, default=None, help='Specify the names of any server hosts or host groups.  All batch server hosts will be closed if the reserved word all is specified.')
phclose.set_defaults(func=hclose)

phopen = subparsers.add_parser('hclose', help='Opens batch server hosts.')
phopen.add_argument("host_names", nargs='*', type=str, default=None, help='Specify the names of any server hosts or host groups.  All batch server hosts will be closed if the reserved word all is specified.')
phopen.set_defaults(func=hopen)

args = parser.parse_args()
connection=OpenLavaConnection(args)
args.func(args)





