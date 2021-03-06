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
import sys

parser = argparse.ArgumentParser(description='Displays information about hosts')
OpenLavaConnection.configure_argument_list(parser)

parser.add_argument("-B", action='append_const', const=0x100, dest="options",
                    help="Sends mail to you when the job is dispatched and begins execution.")

parser.add_argument("-H", action='append_const', const=0x01, dest="options2",
                    help="Holds the job in the PSUSP state when the job is submitted. The job will not be scheduled \
                    until you tell the system to resume the job.")

parser.add_argument("-N", action='append_const', const=0x80, dest="options",
                    help="Sends the job report to you by mail when the job finishes. When used without any other \
                    options, behaves the same as the default.")

parser.add_argument("-r", action='append_const', const=0x4000, dest="options",
                    help="If  the  execution host becomes unavailable while a job is running, specifies that the \
                    job will rerun on another host.")

parser.add_argument("-x", action='append_const', const=0x40, dest="options",
                    help="Puts the host running your job into exclusive execution mode.")

parser.add_argument("-n", dest="procs", default="1",
                    help="Submits a parallel job and specifies the minimum and maximum numbers of processors required \
                    to run the job")

parser.add_argument("-J", dest="job_name", default=None,
                    help="Assigns the specified name to the job, and, for job arrays, specifies the indices of the job \
                    array and optionally the maximum number of jobs that can run at any given time.")

parser.add_argument("-q", dest="queue_name", default=None, help="Submits the job to the specified queues.")

parser.add_argument("commands", nargs='+', type=str, default=None,
                    help='Command to execute on the remote host')

args = parser.parse_args()

connection = OpenLavaConnection(args)

command = " ".join(args.commands)
min_processors, sep, max_processors = args.procs.partition(",")
min_processors = int(min_processors)

try:
    max_processors = int(max_processors)
except ValueError:
    max_processors = min_processors
options = 0
options2 = 0
if args.options:
    for o in args.options:
        options = options | o
if args.options2:
    for o in args.options2:
        options2 = options2 | o

payload = {
    "options": options,
    "options2": options2,
    "requested_slots": min_processors,
    "max_requested_slots": max_processors,
    "command": command,
}

if args.queue_name:
    payload['queue_name'] = args.queue_name

if args.job_name:
    payload['job_name'] = args.job_name

connection.login()

try:
    jobs = Job.submit(connection, **payload)
    for j in jobs:
        print "Job: %s[%s] was submitted." % (j.job_id, j.array_index)

except RemoteServerError, e:
    print "Unable to submit job: %s" % e.message
    sys.exit(1)
