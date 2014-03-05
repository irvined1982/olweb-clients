.. program:: bqueues.py

Provides similar functionality and syntax to the OpenLava bqueues command.  Displays information about queues.

This is not meant to be a like for like replacement for bqueues, but an example of how to use the API.

.. option:: -w

Displays queue information in a wide format. Fields are displayed without truncation.

.. option:: -l

Displays  queue  information in a long multi-line format. The -l option displays the following additional information: queue description, queue characteristics and statistics, scheduling parameters, resource limits, scheduling policies, users, hosts, user shares, windows, associated commands, and job controls.

.. option:: -m host_name | -m host_group | -m all

Displays the queues that can run jobs on the specified host or host group. If the keyword all is specified, displays the queues that can  run  jobs  on  all hosts . For a list of host groups see bmgroup(1).

.. option:: -u user_name | -u user_group | -u all

Displays  the  queues  that can accept jobs from the specified user or user group (For a list of user groups see bugroup(1).) If the keyword `all' is specified, displays the queues that can accept jobs from all users.

.. option:: queue_name ...

Displays information about the specified queues.