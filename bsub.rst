.. program:: bsub.py

Provides similar functionality and syntax to the OpenLava bsub command.  Submits a batch job using the API.

This is not meant to be a like for like replacement for bsub, but an example of how to use the API.

Submits a job for batch execution and assigns it a unique numerical job ID.

Runs  the  job on a host that satisfies all requirements of the job, when all conditions on the job, host, queue, and cluster are satisfied.  If the scheduler cannot run all jobs immediately, scheduling policies determine the order of dispatch. Jobs are started and suspended according to the current system load.

Sets the user's execution environment for the job, including the current working directory, file creation mask, and all environment variables,  and  sets scheduling system environment variables before starting the job.

.. option:: -B

Sends mail to you when the job is dispatched and begins execution.

.. option:: -H

Holds the job in the PSUSP state when the job is submitted. The job will not be scheduled until you tell the system to resume the job.

.. option:: -N

Sends the job report to you by mail when the job finishes. When used without any other options, behaves the same as the default.

.. option:: -r

If  the  execution host becomes unavailable while a job is running, specifies that the job will rerun on another host. openlava requeues the job in the same job queue with the same job ID. When an available execution host is found, reruns the job as if it were submitted new. You receive a mail message  informing you of the host failure and requeuing of the job.

If the system goes down while a job is running, specifies that the job will be requeued when the system restarts.

Reruns a job if the execution host or the system fails; it does not rerun a job if the job itself fails.

.. option:: -x

Puts the host running your job into exclusive execution mode.

In  exclusive  execution mode, your job runs by itself on a host. It is dispatched only to a host with no other jobs running, and openlava does not send any other jobs to the host until the job completes.

To submit a job in exclusive execution mode, the queue must be configured to allow exclusive jobs.

.. option:: -n min_proc[,max_proc]

Submits a parallel job and specifies the minimum and maximum numbers of processors required to run the job (some of the processors may be on the same multi‐processor host). If you do not specify a maximum, the number you specify represents the exact number of processors to use.

.. option:: -J "job_name[index_list]%job_slot_limit"

Assigns the specified name to the job, and, for job arrays, specifies the indices of the job array and optionally the maximum number of jobs that can run at any given time.

The job name need not be unique.

To specify a job array, enclose the index list in square brackets, as shown, and enclose the entire job array specification in quotation  marks,  as  shown.  The  index  list is a comma-separated list whose elements have the syntax start[-end[:step]] where start, end and step are positive integers. If the step is omitted, a step of one is assumed. The job array index starts at one. By default, the maximum job array index is 2.00.

You may also use a positive integer to specify the system-wide job slot limit (the maximum number of jobs that can run at  any  given  time)  for  this  job array.

All jobs in the array share the same job ID and parameters. Each element of the array is distinguished by its array index.

.. option:: command [argument]

The  job  can  be specified by a command line argument command, or through the standard input if the command is not present on the command line. The command can be anything that is provided to a UNIX Bourne shell (see sh(1)). command is assumed to begin with the first word that is not part of a bsub option.  All arguments that follow command are provided as the arguments to the command.

If  the  batch  job  is not given on the command line, bsub reads the job commands from standard input. If the standard input is a controlling terminal, the user is prompted with "bsub>" for the commands of the job. The input is terminated by entering CTRL-D on a  new  line.  You  can  submit  multiple  commands through standard input. The commands are executed in the order in which they are given. bsub options can also be specified in the standard input if the line begins with #BSUB; e.g., "#BSUB -x". If an option is given on both the bsub command line, and in the standard input, the command line option  overrides  the option  in the standard input. The user can specify the shell to run the commands by specifying the shell path name in the first line of the standard input, such as "#!/bin/csh". If the shell is not given in the first line, the Bourne shell is used. The standard input facility can be used to spool a  user's  job script; such as "bsub < script". See EXAMPLES below for examples of specifying commands through standard input.

