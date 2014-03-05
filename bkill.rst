.. program:: bkill.py

Provides similar functionality and syntax to the OpenLava bkill command.  Sends signals to kill, suspend, or resume unfinished jobs.

This is not meant to be a like for like replacement for bkill, but an example of how to use the API.

.. option:: -J job_name

Operates only on jobs with the specified job_name. The -J option is ignored if a job ID other than 0 is specified in the job_ID option.

.. option:: -m host_name | -m host_group

Operates only on jobs dispatched to the specified host or host group.

.. option:: -q queue_name

Operates only on jobs in the specified queue.

.. option:: -u user_name | -u user_group | -u all

Operates only on jobs submitted by the specified user or user group (see bugroup(1)), or by all users if the reserved user name all is specified.

.. option::  job_ID ... | 0 | "job_ID[index]" ...

Operates only on jobs that are specified by job_ID or "job_ID[index]", where "job_ID[index]" specifies selected job array elements (see bjobs(1)). For job arrays, quotation marks must enclose the job ID and index, and index must be enclosed in square brackets.

Jobs submitted by any user can be specified here without using the -u option. If you use the reserved job ID 0, all the  jobs  that  satisfy  other  options (that is, -m, -q, -u and -J) are operated on; all other job IDs are ignored.

The  options  -u,  -q,  -m and -J have no effect if a job ID other than 0 is specified. Job IDs are returned at job submission time (see bsub(1)) and may be obtained with the bjobs command (see bjobs(1)).

