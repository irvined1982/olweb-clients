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
import os
import getpass
import re
import sys

parser = argparse.ArgumentParser(description='Displays information about hosts')
OpenLavaConnection.configure_argument_list(parser)







parser.add_argument("-J", dest="job_name", default=None,
                    help="Operates only on jobs with the specified job_name. The -J option is ignored if a job ID other than 0 is specified in the job_ID option.")
parser.add_argument("-m", dest="host_name", default=None,
                    help="Operates only on jobs dispatched to the specified host or host group.")
parser.add_argument("-q", dest="queue_name", default=None,
                    help="Operates only on jobs in the specified queue.")
parser.add_argument("-u", dest="user_name", default=getpass.getuser(),
                    help="Operates only on jobs submitted by the specified user or user group (see bugroup(1)), or by all users if the reserved user name all is specified.")

parser.add_argument("job_ids", nargs='+', type=str, default=None,
                    help='Operates  only  on jobs that are specified by job_ID or "job_ID[index]", where "job_ID[index]" specifies selected job array elements (see bjobs(1)). For job arrays, quotation marks must enclose the job ID and index, and index must be enclosed in square brackets.')

parser.add_argument("-s", dest="signal", default="kill", choices=["kill", "suspend", "resume", "requeue"], help="Sends the specified signal to specified jobs. Signals can be one of: kill, suspend, resume, requeue," )


args = parser.parse_args()

connection = OpenLavaConnection(args)

if 0 in args.job_ids or "0" in args.job_ids:
    jobs = Job.get_job_list(connection,
                            user_name=args.user_name,
                            host_name=args.host_name,
                            queue_name=args.queue_name,
                            job_name=args.job_name,
    )
else:
    jobs = []
    for job_id in args.job_ids:
        try:
            jid = int(job_id)
            aid = 0
        except ValueError:
            match = re.search('\d+\[\d+\]', job_id)
            if match:
                jid=match.group(0)
                aid=match.group(1)
            else:
                print "Invalid job id: %s" % job_id
                sys.exit(1)

        jobs.append(Job(connection, job_id=jid, array_id=aid))

for job in jobs:
    print "Sending %s signal to job: %s[%s]" % (args.signal, job.job_id, job.array_index)
    getattr(job, args.signal)()

