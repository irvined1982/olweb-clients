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


def print_long():
    for host in Host.get_hosts_by_names(connection, args.hostnames):
        print "HOST  %s" % host.host_name
        print "\n"
        print "STATUS           CPUF  JL/U    MAX  NJOBS    RUN  SSUSP  USUSP    RSV DISPATCH_WINDOW"
        print "%-16.16s %-5.5s %-7.7s %-4.4s %-8.8s %-4.4s %-6.6s %-8.8s %-3.3s %-18.18s" %\
              (",".join([s.friendly for s in host.statuses]),
               host.cpu_factor,
               "-" if host.max_slots_per_user == 2147483647 else host.max_slots_per_user,
               host.max_slots, host.total_slots,
               host.num_running_slots,
               host.num_system_suspended_slots,
               host.num_user_suspended_slots,
               host.num_reserved_slots, host.run_windows)
        print "\nLOAD THRESHOLD USED FOR SCHEDULING:"
        template=[]

        row = "%-20.20s " % " "

        for name in host.load_information.short_names:
            l=len(name)
            if l<5:
                l=5
            template.append("%%%d.%ds " % (l, l))
            f = "%%%d.%ds " % (l, l)
            row += f % name

        print row

        for index in host.load_information.values:
            row="%-20.20s " % index.name
            for i in range(len(index.values)):
                value=index.values[i]
                if value == -1 or value == 2147483648.0:
                    value = "-"
                row += template[i] % value
            print row


def print_short():
    print "HOST_NAME          STATUS       JL/U    MAX  NJOBS    RUN  SSUSP  USUSP    RSV"
    for host in Host.get_hosts_by_names(connection, args.hostnames):
        print "%-18.18s %-12.12s %-7.7s %-4.4s %-8.8s %-4.4s %-6.6s %-8.8s %-4.4s" % (host.host_name, ",".join([s.friendly for s in host.statuses]), "-" if host.max_slots_per_user == 2147483647 else host.max_slots_per_user, host.max_slots, host.total_slots, host.num_running_slots, host.num_system_suspended_slots, host.num_user_suspended_slots, host.num_reserved_slots)


def print_wide():
    print "HOST_NAME          STATUS       JL/U    MAX  NJOBS    RUN  SSUSP  USUSP    RSV"
    for host in Host.get_hosts_by_names(connection, args.hostnames):
        print "%-18s %-12s %-7s %-4s %-8s %-4s %-6s %-8s %-4s" % (host.host_name, ",".join([s.friendly for s in host.statuses]), "-" if host.max_slots_per_user == 2147483647 else host.max_slots_per_user, host.max_slots, host.total_slots, host.num_running_slots, host.num_system_suspended_slots, host.num_user_suspended_slots, host.num_reserved_slots)


parser = argparse.ArgumentParser(description='Displays information about hosts')
OpenLavaConnection.configure_argument_list(parser)

parser.add_argument("-w", action='store_true', dest="wide", help="Displays host information in wide format. Fields are displayed without truncation.")
parser.add_argument("-l", action='store_true', dest="long", help="Displays  host  information in a (long) multi-line format. In addition to the default fields, displays information about the CPU factor, the dispatch windows, the current load, and the load thresholds.")
parser.add_argument("hostnames", default=None, nargs="*", help="Only  displays  information  about the specified hosts or host groups. For host groups")

args = parser.parse_args()
if len(args.hostnames) == 0:
        args.hostnames = ["all"]

connection=OpenLavaConnection(args)

if args.long:
    print_long()
elif args.wide:
    print_wide()
else:
    print_short()


