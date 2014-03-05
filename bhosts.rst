.. program:: bhosts.py

Provides similar functionality and syntax to the OpenLava bhosts command.  Displays hosts and their static and dynamic resource.

This is not meant to be a like for like replacement for bhosts, but an example of how to use the API.

By default, returns the following information about all hosts: host name, host status, job slot limits, and job state statistics.

.. option:: -w

Displays host information in wide format. Fields are displayed without truncation.

.. option:: -l

Displays host information in a (long) multi-line format. In addition to the default fields, displays information about the CPU factor, the dispatch windows, the current load, and the load thresholds.

.. option:: host_name ... | host_group ...

Only  displays information about the specified hosts or host groups. For host groups, the names of the hosts belonging to the group are displayed instead of the name of the host group. Do not use quotes when specifying multiple hosts or host groups.