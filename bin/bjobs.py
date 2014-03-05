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

def print_long():
    for job in jobs:
        print
        status = job.status.name
        if status == "JOB_STAT_RUN":
            status = "RUN"
        elif status == "JOB_STAT_PEND":
            status = "PEND"
        elif status == "JOB_STAT_DONE":
            status = "DONE"
        elif status == "JOB_STAT_EXIT":
            status = "EXIT"
        elif status == "JOB_STAT_USUSP":
            status = "USUSP"
        elif status == "JOB_STAT_SSUSP":
            status = "SSUSP"
        else:
            status = "UNKNOWN"
        job_id = job.job_id
        if job.array_index != 0:
            job_id = "%s[%s]" % (job.job_id, job.array_index)

        row = "Job <%s>, User <%s>, Project <%s>, Status <%s>, Queue <%s>, Command <%s>" % (
        job_id, job.user_name, job.project_names[0], status, job.queue.name, job.command)

        if len(row) > 80:
            print row[:80]
            row = row[80:]
            if len(row) > 0:
                if len(row) > 80:
                    print "            %s" % row[:70]
                else:
                    print "            %s" % row

        else:
            print row
        print "%s: submitted from host: <%s>, CWD <%s>" % (job.submit_time_datetime, job.submission_host.name, job.cwd)
        if job.status.name == "JOB_STAT_PEND":
            print "PENDING REASONS:"
            print job.pending_reasons

        print


def print_short():
    print "%-7.7s %-7.7s %-5.5s %-10.10s %-11.11s %-11.11s %-10.10s %12.12s" % (
        "JOBID",
        "USER",
        "STAT",
        "QUEUE",
        "FROM_HOST",
        "EXEC_HOST",
        "JOB_NAME",
        "SUBMIT_TIME",
    )

    for job in jobs:
        status = job.status.name
        if status == "JOB_STAT_RUN":
            status = "RUN"
        elif status == "JOB_STAT_PEND":
            status = "PEND"
        elif status == "JOB_STAT_DONE":
            status = "DONE"
        elif status == "JOB_STAT_EXIT":
            status = "EXIT"
        elif status == "JOB_STAT_USUSP":
            status = "USUSP"
        elif status == "JOB_STAT_SSUSP":
            status = "SSUSP"
        else:
            status = "UNKNOWN"

        job_id = job.job_id
        if job.array_index != 0:
            job_id = "%s[%s]" % (job.job_id, job.array_index)

        print "%-7.7s %-7.7s %-5.5s %-10.10s %-11.11s %-11.11s %-11.11s %-12s" % (
            job_id,
            job.user_name,
            status,
            job.queue.name,
            job.submission_host.name,
            " ".join([x.name for x in job.execution_hosts]),
            job.name,
            job.submit_time_datetime,
        )


def print_wide():
    print "%-7.7s %-7.7s %-5.5s %-10.10s %-11.11s %-11.11s %-10.10s %12.12s" % (
        "JOBID",
        "USER",
        "STAT",
        "QUEUE",
        "FROM_HOST",
        "EXEC_HOST",
        "JOB_NAME",
        "SUBMIT_TIME",
    )

    for job in jobs:
        status = job.status.name
        if status == "JOB_STAT_RUN":
            status = "RUN"
        elif status == "JOB_STAT_PEND":
            status = "PEND"
        elif status == "JOB_STAT_DONE":
            status = "DONE"
        elif status == "JOB_STAT_EXIT":
            status = "EXIT"
        elif status == "JOB_STAT_USUSP":
            status = "USUSP"
        elif status == "JOB_STAT_SSUSP":
            status = "SSUSP"
        else:
            status = "UNKNOWN"

        job_id = job.job_id
        if job.array_index != 0:
            job_id = "%s[%s]" % (job.job_id, job.array_index)

        print "%-7s %-7s %-5s %-10s %-11s %-11s %-11s %-12s" % (
            job_id,
            job.user_name,
            status,
            job.queue.name,
            job.submission_host.name,
            " ".join([x.name for x in job.execution_hosts]),
            job.name,
            job.submit_time_datetime,
        )


parser = argparse.ArgumentParser(description='Displays information about hosts')
OpenLavaConnection.configure_argument_list(parser)

parser.add_argument("-a", action='store_const', const="ALL", dest="job_state",
                    help="Displays  information  about  jobs in all states, including finished jobs that finished recently, within an interval specified by CLEAN_PERIOD in lsb.params")
parser.add_argument("-d", action='store_const', const="EXIT", dest="job_state",
                    help="Displays information about jobs that finished recently, within an interval specified by CLEAN_PERIOD in lsb.params")
parser.add_argument("-p", action='store_const', const="PEND", dest="job_state",
                    help="Displays  pending  jobs, together with the pending reasons that caused each job not to be dispatched during the last dispatch turn. The pending reason shows the number of hosts for that reason, or names the hosts if -l is also specified.")
parser.add_argument("-r", action='store_const', const="RUN", dest="job_state", help="Displays running jobs.")
parser.add_argument("-s", action='store_const', const="SUSP", dest="job_state",
                    help="Displays suspended jobs, together with the suspending reason that caused each job to become suspended.")
parser.add_argument("-w", action='store_true', dest="wide",
                    help="Displays queue information in wide format. Fields are displayed without truncation.")
parser.add_argument("-l", action='store_true', dest="long",
                    help="Displays queue information in a (long) multi-line format. ")
parser.add_argument("-u", dest="user_name", default=getpass.getuser(),
                    help="Only displays jobs that have been submitted by the specified users. The keyword all specifies all users")
parser.add_argument("job_ids", nargs='*', type=str, default=None,
                    help="Displays information about the specified jobs or job arrays")
parser.add_argument("-m", dest="host_name", default=None,
                    help="Only displays jobs dispatched to the specified hosts.")
parser.add_argument("-q", dest="queue_name", default=None,
                    help="Only displays jobs in the specified queue.")
parser.add_argument("-J", dest="job_name", default=None,
                    help="Displays information about the specified jobs or job arrays.")

args = parser.parse_args()

connection = OpenLavaConnection(args)

if len(args.job_ids) > 0:
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
else:
    jobs = Job.get_job_list(connection,
                            user_name=args.user_name,
                            job_state=args.job_state,
                            host_name=args.host_name,
                            queue_name=args.queue_name,
                            job_name=args.job_name,
    )


if args.long:
    print_long()
elif args.wide:
    print_wide()
else:
    print_short()


