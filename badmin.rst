.. program:: badmin.py

Provides similar functionality and syntax to the OpenLava badmin command.  Queue and host maintenance.

This is not meant to be a like for like replacement for badmin, but an example of how to use the API.

.. option:: hopen [host_name ... | host_group ... | all]

Opens  batch server hosts. Specify the names of any server hosts or host groups (see bmgroup(1)). All batch server hosts will be opened if the reserved word all is specified. If no host or host group is specified, the local host is assumed. A host accepts batch jobs if it is open.

.. option:: hclose [host_name ... | host_group ... | all]

Closes batch server hosts. Specify the names of any server hosts or host groups (see bmgroup(1)). All batch server hosts will be closed if the reserved word all is specified. If no argument is specified, the local host is assumed. A closed host will not accept any new job, but jobs already dispatched to the host will not be affected. Note that this is different from a host closed by a window - all jobs on it are suspended in that case.

.. option:: qopen [queue_name ... | all]

Opens specified queues, or all queues if the reserved word all is  specified

.. option:: qclose [queue_name ... | all]

Closes  specified  queues,  or all queues if the reserved word all is specified. If no queue is specified, the system default queue is assumed.

.. option:: qact [queue_name ... | all]

Activates specified queues, or all queues if the reserved word all is specified.

.. option:: qinact [queue_name ... | all]

Inactivates  specified queues, or all queues if the reserved word all is specified.
