#!/usr/bin/env python
# Copyright 2014 David Irvine
#
# This file is part of olwclients
#
# olwclients is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or (at
# your option) any later version.
#
# olwclients is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with olwclients. If not, see <http://www.gnu.org/licenses/>.

import argparse
from olwclient import *
import socket


def hclose(args):
    for host in Host.get_hosts_by_names(connection, args.host_names):
        try:
            host.close()
            print "Olosed host: %s" % host.host_name
        except RemoteException as e:
            print "Unable to close host: %s: %s" % (host.host_name, e.message)


def hopen(args):
    for host in Host.get_hosts_by_names(connection, args.host_names):
        try:
            host.open()
            print "Opened host: %s" % host.host_name
        except RemoteException as e:
            print "Unable to open host: %s: %s" % (host.host_name, e.message)


def qopen(args):
    for queue in Queue.get_queues_by_names(connection, args.queue_names):
        try:
            queue.open()
            print "Opened queue: %s" % queue.name
        except RemoteException as e:
            print "Unable to open queue: %s: %s" % (queue.name, e.message)


def qclose(args):
    for queue in Queue.get_queues_by_names(connection, args.queue_names):
        try:
            queue.close()
            print "Closed queue: %s" % queue.name
        except RemoteException as e:
            print "Unable to close queue: %s: %s" % (queue.name, e.message)


def qact(args):
    for queue in Queue.get_queues_by_names(connection, args.queue_names):
        try:
            queue.activate()
            print "Activated queue: %s" % queue.name
        except RemoteException as e:
            print "Unable to activate queue: %s: %s" % (queue.name, e.message)

def qinact(args):
    for queue in Queue.get_queues_by_names(connection, args.queue_names):
        try:
            queue.inactivate()
            print "Inactivated queue: %s" % queue.name
        except RemoteException as e:
            print "Unable to inactivate queue: %s: %s" % (queue.name, e.message)




parser = argparse.ArgumentParser(description='Badmin provides a set of commands to control and monitor Openlava.')
OpenLavaConnection.configure_argument_list(parser)
subparsers = parser.add_subparsers(help='sub-command help')

phclose = subparsers.add_parser('hclose', help='Closes  batch  server hosts.')
phclose.add_argument("host_names", nargs='*', type=str, default=None,
                     help='Specify the names of any server hosts or host groups.  All batch server hosts will be closed if the reserved word all is specified.')
phclose.set_defaults(func=hclose)

phopen = subparsers.add_parser('hopen', help='Opens batch server hosts.')
phopen.add_argument("host_names", nargs='*', type=str, default=None,
                    help='Specify the names of any server hosts or host groups.  All batch server hosts will be closed if the reserved word all is specified.')
phopen.set_defaults(func=hopen)

pqopen = subparsers.add_parser('qopen', help='Opens batch  queues.')
pqopen.add_argument("queue_names", nargs='*', type=str, default=None,
                    help='Opens specified queues, or all queues if the reserved word all is specified. If no queue is specified, the system default queue is assumed.')
pqopen.set_defaults(func=qopen)

pqclose = subparsers.add_parser('qclose', help='Closes batch queues.')
pqclose.add_argument("queue_names", nargs='*', type=str, default=None,
                     help='Closes specified queues, or all queues if the reserved word all is specified. If no queue is specified, the system default queue is assumed.')
pqclose.set_defaults(func=qclose)

pqinact = subparsers.add_parser('qinact', help='Inactivates batch queues.')
pqinact.add_argument("queue_names", nargs='*', type=str, default=None,
                     help='Inactivates specified queues, or all queues if the reserved word all is specified. If no queue is specified, the system default queue is assumed.')
pqinact.set_defaults(func=qinact)

pqact = subparsers.add_parser('qact', help='Activates batch queues.')
pqact.add_argument("queue_names", nargs='*', type=str, default=None,
                   help='Activates specified queues, or all queues if the reserved word all is specified. If no queue is specified, the system default queue is assumed.')
pqact.set_defaults(func=qact)

args = parser.parse_args()
connection = OpenLavaConnection(args)
args.func(args)





