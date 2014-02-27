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
    for queue in Queue.get_queues_by_names(connection, args.queue_names):
        if args.user and args.user == "all" and queue.allowed_users:
            continue # allowed users only True if restricted
        if args.user and queue.allowed_users and args.user not in args.allowed_users:
            continue # User is not in allowed users list
        if args.host and args.host == "all" and queue.allowed_hosts:
            continue # allowed hosts only True if restricted
        if args.host and queue.allowed_hosts and args.host not in args.allowed_hosts:
            continue
        print "QUEUE: %s" % queue.name
        print "  -- %s" % queue.description
        print ""
        print "PARAMETERS/STATISTICS"
        print "PRIO NICE STATUS          MAX JL/U JL/P JL/H NJOBS  PEND   RUN SSUSP USUSP  RSV"
        print "%-4.4s %-4.4s %-15.15s %-3.3s %-4.4s %-4.4s %-4.4s %-6.6s %-6.6s %-3.3s %-5.5s %-6.6s %-3.3s" % (queue.priority,
                                           queue.nice,
                                           ",".join([s.friendly for s in queue.statuses]),
                                           "-" if queue.max_slots == 2147483647 else quee.max_slots,
                                           "-" if queue.max_slots_per_user == 2147483647 else queue.max_slots_per_user,
                                           "-" if queue.max_slots_per_processor == 2147483648.0 else queue.max_slots_per_processor,
                                           "-" if queue.max_slots_per_host == 2147483647 else queue.max_slots_per_host,
                                           queue.total_slots,
                                           queue.num_pending_slots,
                                           queue.num_running_slots,
                                           queue.num_system_suspended_slots,
                                           queue.num_user_suspended_slots,
                                           queue.num_reserved_slots,
        )
        print "Interval for a host to accept two jobs is %s seconds" % queue.accept_interval
        print ""
        print "USERS:  %s" % (", ".join(queue.allowed_users) if queue.allowed_users else "all users")
        print "HOSTS:  %s" % (", ".join(queue.allowed_hosts) if queue.allowed_hosts else "all hosts")



def print_short():
    print "QUEUE_NAME      PRIO STATUS          MAX JL/U JL/P JL/H #NJOBS  PEND   RUN  SUSP"
    for queue in Queue.get_queues_by_names(connection, args.queue_names):
        if args.user and args.user == "all" and queue.allowed_users:
            continue # allowed users only True if restricted
        if args.user and queue.allowed_users and args.user not in args.allowed_users:
            continue # User is not in allowed users list
        if args.host and args.host == "all" and queue.allowed_hosts:
            continue # allowed hosts only True if restricted
        if args.host and queue.allowed_hosts and args.host not in args.allowed_hosts:
            continue
        print "%-15.15s %-4.4s %-15.15s %-3.3s %-4.4s %-4.4s %-4.4s %-7.7s %-6.6s %-4.4s %-4.4s" % (queue.name,
                                                                                       queue.priority,
                                                                                       ",".join([s.friendly for s in queue.statuses]),
                                                                                       "-" if queue.max_slots == 2147483647 else quee.max_slots,
                                                                                       "-" if queue.max_slots_per_user == 2147483647 else queue.max_slots_per_user,
                                                                                       "-" if queue.max_slots_per_processor == 2147483648.0 else queue.max_slots_per_processor,
                                                                                       "-" if queue.max_slots_per_host == 2147483647 else queue.max_slots_per_host,
                                                                                       queue.total_slots,
                                                                                       queue.num_pending_slots,
                                                                                       queue.num_running_slots,
                                                                                       queue.num_suspended_slots,
                                                                                        )


def print_wide():
    print "QUEUE_NAME      PRIO STATUS          MAX JL/U JL/P JL/H #NJOBS  PEND   RUN  SUSP"
    for queue in Queue.get_queues_by_names(connection, args.queue_names):
        if args.user and args.user == "all" and queue.allowed_users:
            continue # allowed users only True if restricted
        if args.user and queue.allowed_users and args.user not in args.allowed_users:
            continue # User is not in allowed users list
        if args.host and args.host == "all" and queue.allowed_hosts:
            continue # allowed hosts only True if restricted
        if args.host and queue.allowed_hosts and args.host not in args.allowed_hosts:
            continue # Host is not in allowed hosts list
        print "%-15s %-4s %-15s %-3s %-4s %-4s %-4s %-7s %-6s %-4s %-4s" % (queue.name,
                                                                                       queue.priority,
                                                                                       ",".join([s.friendly for s in queue.statuses]),
                                                                                       "-" if queue.max_slots == 2147483647 else quee.max_slots,
                                                                                       "-" if queue.max_slots_per_user == 2147483647 else queue.max_slots_per_user,
                                                                                       "-" if queue.max_slots_per_processor == 2147483648.0 else queue.max_slots_per_processor,
                                                                                       "-" if queue.max_slots_per_host == 2147483647 else queue.max_slots_per_host,
                                                                                       queue.total_slots,
                                                                                       queue.num_pending_slots,
                                                                                       queue.num_running_slots,
                                                                                       queue.num_suspended_slots,
                                                                                        )


parser = argparse.ArgumentParser(description='Displays information about hosts')
OpenLavaConnection.configure_argument_list(parser)

parser.add_argument("-w", action='store_true', dest="wide", help="Displays queue information in wide format. Fields are displayed without truncation.")
parser.add_argument("-l", action='store_true', dest="long", help="Displays queue information in a (long) multi-line format. ")
parser.add_argument("queue_names", default=None, nargs="*", help="Only displays information about the specified queue or queueus")
parser.add_argument("-u", default=None, dest="user", type=str, help="Displays the queues that can accept jobs from the specified user or user group.  If the keyword `all' is specified, displays the queues that can accept jobs from all users.")
parser.add_argument("-m", default=None, dest="host", type=str, help="Displays the queues that can run jobs on the specified host or host group.  If the keyword all is specified, displays the queues that can run jobs on all  hosts")
args = parser.parse_args()
if len(args.queue_names) == 0:
        args.queue_names = ["all"]

connection=OpenLavaConnection(args)

if args.long:
    print_long()
elif args.wide:
    print_wide()
else:
    print_short()


