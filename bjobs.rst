.. program:: bjobs.py

Provides similar functionality and syntax to the OpenLava bjobs command.  Displays information about jobs.  By default, displays information about your own pending, running and suspended jobs.

This is not meant to be a like for like replacement for bjobs, but an example of how to use the API.

.. option:: -a

Displays  information  about  jobs in all states, including finished jobs that finished recently, within an interval specified by CLEAN_PERIOD in lsb.params (the default period is 1 hour).

.. option:: -d

Displays information about jobs that finished recently, within an interval specified by CLEAN_PERIOD in lsb.params (the default period is 1 hour).

.. option:: -p

Displays  pending  jobs, together with the pending reasons that caused each job not to be dispatched during the last dispatch turn. The pending reason shows the number of hosts for that reason, or names the hosts if -l is also specified.

Each pending reason is associated with one or more hosts and it states the cause why these hosts are not allocated to run the job.  In situations where the job  requests  specific hosts (using bsub -m), users may see reasons for unrelated hosts also being displayed, together with the reasons associated with the requested hosts. The life cycle of a pending reason ends after a new dispatch turn starts. The reason may not reflect the current load situation because  it could last as long as the interval specified by MBD_SLEEP_TIME in lsb.params.

When the job slot limit is reached for a job array (bsub -J "jobArray[indexList]%job_slot_limit") the following message is displayed:

The job array has reached its job slot limit.

.. option:: -r

Displays running jobs.

.. option:: -s

Displays suspended jobs, together with the suspending reason that caused each job to become suspended.

The  suspending  reason  may not remain the same while the job stays suspended. For example, a job may have been suspended due to the paging rate, but after the paging rate dropped another load index could prevent the job from being resumed. The suspending reason will be updated according to the load index.  The reasons could be as old as the time interval specified by SBD_SLEEP_TIME in lsb.params. So the reasons shown may not reflect the current load situation.

.. option:: -l

Long format. Displays detailed information for each job in a multi-line format.

The  -l  option displays the following additional information: project name, job command, current working directory on the submission host, pending and sus‐pending reasons, job status, resource usage, resource limits information.

.. option:: -u user_name | -u user_group | -u all

Only displays jobs that have been submitted by the specified users. The keyword all specifies all users.

.. option:: job_ID

Displays information about the specified jobs or job arrays.

.. option:: -m

Only displays jobs dispatched to the specified hosts.

.. option:: -q queue_name

Only displays jobs in the specified queue.

The command bqueues.py returns a list of queues configured in the system, and information about the configurations of these queues.

.. option:: -J job_name

Displays information about the specified jobs or job arrays.
