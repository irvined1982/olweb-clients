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
import socket
import json
import urllib2
import cookielib
import urllib
import datetime
import re


class AuthenticationError(Exception):
    """Raised when the client is unable to authenticate to the server"""
    pass


class OpenLavaConnection(object):
    """
    Connection and authentication handler for dealing with the server.  Subclass this when you
need a different method of authentication
    """

    @classmethod
    def configure_argument_list(cls, parser):
        """Configures an argument parser with the arguments that are required to connect to the server and authenticate.

        :param argparse.ArgumentParser parser: Argument parser that will be used to parse command line arguments
        :returns: None
        :rtype: None

        """

        parser.add_argument("url", help="URL of server")
        parser.add_argument("--username", help="Username to use when authenticating")
        parser.add_argument("--password", help="Password to use when authenticating")

    def __init__(self, args):
        """Creates a new instance of the connection.

        :param argparse.Namespace args: Arguments required to initialize the connection
        :returns: None
        :rtype:None

        """
        self.username = args.username
        self.password = args.password
        self.url = args.url
        self.url = self.url.rstrip("/")
        self._csrf_token = None
        self._referer = None
        self._cookies = cookielib.LWPCookieJar()
        handlers = [
            urllib2.HTTPHandler(),
            urllib2.HTTPSHandler(),
            urllib2.HTTPCookieProcessor(self._cookies)
        ]
        self._opener = urllib2.build_opener(*handlers)
        self._opener.addheaders = [('HTTP_X_REQUESTED_WITH', 'XMLHttpRequest'), ('X-Requested-With', 'XMLHttpRequest')]

    @property
    def authenticated(self):
        """True if the connection is currently authenticated

        :returns: True if the connection is currently authenticated
        :rtype: Boolean
        """
        for c in self._cookies:
            if c.name == 'sessionid':
                return True
        return False

    def login(self):
        """Logs the user into the server.

        :raise: AuthenticationError if the user cannot be authenticated
        """
        data = {
            'username': self.username,
            'password': self.password,
        }
        data = json.dumps(data)
        url = self.url + "/accounts/ajax_login"
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        f = self._open(req)
        data = json.loads(f.read())
        f.close()

        if not self.authenticated:
            raise AuthenticationError(data['description'])

        url = self.url + "/get_token"
        req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        f = self._open(req)
        data = json.loads(f.read())
        self._csrf_token = data['cookie']
        found=False
        for h in self._opener.addheaders:
            if h[0] == 'X-CSRFToken':
                found = True
        if not found:
            self._opener.addheaders.append( ('X-CSRFToken', self._csrf_token) )
        f.close()

    def _open(self, request):

        if self._referer:
            headers=[]
            for h in self._opener.addheaders:
                if h[0] == 'Referer':
                    continue
                else:
                    headers.append(h)
            headers.append(('Referer', self._referer))
            self._opener.addheaders = headers

        self._referer = request.get_full_url()
        return self._opener.open(request)

    def open(self, request):
        """Opens a request to the server.

        :param urllib2.Request request: Request object with appropriate URL configured
        :returns: HTtp Response object
        :rtype: HTTPResponse
        :raise: URLError on exception
        """

        if not self.authenticated:
            self.login()
        return self._open(request)


class OpenLavaObject(object):
    """Base class for OpenLava objects, automatically populates attributes based on values returned from the server."""

    def __init__(self, connection, data=None):
        """Create a new instance of the class.

        :param OpenLavaConnection connection: Connection object that will be used to connect to the server and retrieve data.
        :param dict data: Optional dictionary containing pre-retrieved data from the server, this will be populated into the objects data structure

        """
        self._connection = connection
        if json:
            if not isinstance(data, dict):
                raise ValueError("Must be a dict")
            for k, v in data.iteritems():
                setattr(self, k, v)

    def _exec_remote(self, url):
        url = self._connection.url + url
        req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        try:
            data = self._connection.open(req).read()
            data = json.loads(data)
            if not isinstance(data, dict):
                raise ValueError("Invalid data returned")
            if data['status'] == "Fail":
                raise RemoteException(data)
            else:
                return data
        except urllib2.HTTPError as e:
            if e.code == 404:
                raise NoSuchObjectError(url)
            else:
                raise


class Host(OpenLavaObject):
    """Retrieve queue information and perform administrative actions on queues on the remote cluster.

.. py:attribute:: admins

List of user names that have administrative rights on this host.

:returns: list of user names
:rtype: list of str

.. py:attribute:: cpu_factor

CPU Factor of the host

.. py:attribute:: description

Description of the host

.. py:attribute:: has_checkpoint_support

True if the host supports checkpointing

.. py:attribute:: has_kernel_checkpoint_copy

True if the host has kernel checkpointing support

.. py:attribute:: host_model

Model name of the host

.. py:attribute:: host_name

Hostname of the host

.. py:attribute:: host_type

Host architecture

.. py:attribute:: is_busy

True if the host is currently busy

.. py:attribute:: is_closed

True if the host is currently closed

.. py:attribute:: is_down

True if the host is down for an unknown reason

.. py:attribute:: is_server

True if the host is a job server

.. py:attribute:: load_information

List of LoadIndex objects

.. py:attribute:: max_jobs

The maximum number of jobs that may execute on this host

.. py:attribute:: max_processors

The total number of processors available to jobs on this host

.. py:attribute:: max_ram

The total amount of RAM available to jobs on this host

.. py:attribute:: max_slots

The total number of slots available to jobs on this host

.. py:attribute:: max_slots_per_user

The maximum number of slots that may be consumed per user on this host

.. py:attribute:: max_swap

The maximum amount of swap space that is available to jobs on this host

.. py:attribute:: max_tmp

The maximum amount of temporary space that is available to jobs on this host

.. py:attribute:: name

The name of the host

.. py:attribute:: num_disks

The number of physical disks attached

.. py:attribute:: num_reserved_slots

The number of slots that are reserved

.. py:attribute:: num_running_jobs

The number of jobs that are running

.. py:attribute:: num_running_slots

The number of slots that are running

.. py:attribute:: num_suspended_jobs

The number of jobs that are suspended

.. py:attribute:: num_suspended_slots

The number of slots that are suspended

.. py:attribute:: num_system_suspended_jobs

The number of jobs that have been suspended by the system

.. py:attribute:: num_system_suspended_slots

The number of slots that have been suspended by the system

.. py:attribute:: num_user_suspended_jobs

The number of jobs that have been suspended by the user

.. py:attribute:: num_user_suspended_slots

The number of slots that have been suspended by the user

.. py:attribute:: resources

List of resources that are available on the system

.. py:attribute:: run_windows

The run windows that the host is open for. If empty indicates that the host is always open.

.. py:attribute:: statuses

List of statuses that apply to the host

.. py:attribute:: total_jobs

Total jobs on the host

.. py:attribute:: total_slots

Total slots consumed on the host

"""

    @classmethod
    def get_hosts_by_names(cls, connection, host_names):
        """Return a list of Host objects that are in host_names

        :param list host_names: List of hostnames to get
        :returns: List of Host objects
        :rtype: list

     """
        if len(host_names) == 1 and host_names[0] == "all":
            hosts = cls.get_host_list(connection)
        elif len(host_names) == 0:
            hosts = [cls(connection, host_name=socket.gethostname())]
        else:
            hosts = [cls(connection, host_name=host_name) for host_name in host_names]
        return hosts


    @classmethod
    def get_host_list(cls, connection):
        """Returns all hosts on the remote cluster"""
        url = connection.url + "/hosts"
        request = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        try:
            data = connection.open(request).read()
            data = json.loads(data)
            if not isinstance(data, list):
                print "Got strange data back"
                data = []
            return [Host(connection, data=i) for i in data]
        except:
            raise

    def __init__(self, connection, host_name=None, data=None):
        if host_name:
            url = connection.url + "/hosts/%s?json=1" % host_name
            req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
            try:
                data = connection.open(req).read()
                data = json.loads(data)
            except urllib2.HTTPError as e:
                if e.code == 404:
                    raise NoSuchObjectError("No such host: %s" % host_name)
                else:
                    raise
        if not isinstance(data, dict):
            raise ValueError("Data must be a dict")
        if data['type'] != "Host":
            raise ValueError("data is not of type Host")
        OpenLavaObject.__init__(self, connection, data=data)
        self.resources = [Resource(self._connection, data=res) for res in self.resources]
        self.statuses = [Status(self._connection, data=status) for status in self.statuses]
        self.load_information = LoadInformation(self._connection, data=self.load_information)
        self.load_information.values = [LoadValueList(self._connection, data=l) for l in self.load_information.values]


    def jobs(self):
        """Return a list of Jobs that are executing on the Host.
        """
        raise NotImplementedError

    def close(self):
        """Close the host, no new jobs will be scheduled"""
        self._exec_remote("/hosts/%s/close" % self.host_name)

    def open(self):
        """Open the host for scheduling"""
        self._exec_remote("/hosts/%s/open" % self.host_name)


class NoSuchObjectError(Exception):
    """Indicates that the requested object does not exist on the remote server"""
    pass


class LoadInformation(OpenLavaObject):
    pass


class LoadValueList(OpenLavaObject):
    pass


class RemoteException(Exception):
    """Indicates an exception hapenned on the remote server"""

    def __init__(self, data):
        Exception.__init__(self, data['message'])
        for k, v in data.iteritems():
            setattr(self, k, v)


class Status(OpenLavaObject):
    """Status of an object.

.. py:attribute:: description

Description of the status

.. py:attribute:: friendly

Friendly name for the status

.. py:attribute:: name

Full name of the status

.. py:attribute:: status

Numeric code of the status

    """
    pass


class Resource(OpenLavaObject):
    """Available resource on the remote cluster.

.. py:attribute:: description

Description of the resource

.. py:attribute:: flags

Flags set on the resource

.. note:: Openlava scheduler only.

.. py:attribute:: interval

Resource update interval for dynamic resources

.. note:: Openlava scheduler only.

.. py:attribute:: name

Name of the resource

.. py:attribute:: order

Ordering of the resource

.. note:: Openlava scheduler only.

    """
    pass


class ConsumedResource(OpenLavaObject):
    """Resources consumed by a job.

.. py:attribute:: limit

Limit imposed by the scheduler on the resource

.. py:attribute:: name

Name of the resource

.. py:attribute:: unit

The units the resource is measured in

.. py:attribute:: value

The value of the consumed resource

    """
    pass


class JobOption(OpenLavaObject):
    """Option submitted with Job.

.. py:attribute:: description

Description of the option

.. py:attribute:: friendly

Friendly name for the option

.. py:attribute:: name

Full name of the option

.. py:attribute:: status

Numeric code of the option

    """
    pass


class Process(OpenLavaObject):
    """Process started by submitted job.

.. py:attribute:: cray_job_id

Cray job ID of the process

.. py:attribute:: hostname

Hostname process was started on, may be None if unknown

.. py:attribute:: parent_process_id

Process ID of parent process.

.. py:attribute:: process_group_id

Group ID of the process

.. py:attribute:: process_id

Process ID of the process


"""
    pass


class Job(OpenLavaObject):
    """Get information about, and manipulate jobs on remote server.

.. py:attribute:: admins

List of user names that have administrative rights on this host.

:returns: list of user names
:rtype: list of str

.. py:attribute:: array_index

The array index of the job, 0 for non-array jobs.

.. py:attribute:: begin_time

Earliest time (Epoch UTC) that the job may begin

.. py:attribute:: checkpoint_directory

Data where checkpoint data will be written to.

.. py:attribute:: checkpoint_period

Time between checkpointing operations

.. py:attribute:: command

Command to execute

.. py:attribute:: consumed_resources

List of ConsumedResource objects

.. py:attribute:: cpu_factor

.. py:attribute:: cpu_time

.. py:attribute:: cwd

Current Working Directory of the job

.. py:attribute:: dependency_condition

Dependency conditions that must be met before the job will be dispatched

.. py:attribute:: email_user

User to email job notifications to

.. py:attribute:: end_time

Time job ended. (Epoch UTC)

.. py:attribute:: error_file_name

.. py:attribute:: execution_cwd

.. py:attribute:: execution_home_directory

.. py:attribute:: execution_hosts

List of host objects that are executing the job

.. py:attribute:: execution_user_id

User ID under which the job is executing

.. py:attribute:: execution_user_name

User name under which the job is executing

.. py:attribute:: host_specification
.. py:attribute:: input_file_name
.. py:attribute:: is_completed

True if the job completed

.. py:attribute:: is_failed

True if the job failed

.. py:attribute:: is_pending

True if the job is pending

.. py:attribute:: is_running

True if the job is running

.. py:attribute:: is_suspended

True if the job is suspended

.. py:attribute:: job_id

ID of the job

.. py:attribute:: login_shell

.. py:attribute:: max_requested_slots

.. py:attribute:: name

.. py:attribute:: options

List of JobOptions for the job

.. py:attribute:: output_file_name

.. py:attribute:: parent_group

.. py:attribute:: pending_reasons

.. py:attribute:: pre_execution_command

.. py:attribute:: predicted_start_time

.. py:attribute:: priority

.. py:attribute:: process_id

.. py:attribute:: processes

.. py:attribute:: project_names

.. py:attribute:: requested_hosts

.. py:attribute:: requested_resources

.. py:attribute:: requested_slots

.. py:attribute:: reservation_time

.. py:attribute:: resource_usage_last_update_time

Last time resource usage was updated (Epoch UTC)

.. py:attribute:: runtime_limits

List of runtime limits

.. py:attribute:: service_port

NIOS Service port

.. py:attribute:: start_time

Time job started (Epoch UTC)

.. py:attribute:: status

Job Status object

.. py:attribute:: submission_host

Host where job was submitted

.. py:attribute:: submit_home_directory

Home directory on submission host.

.. py:attribute:: submit_time

Job submit time (Epoch UTC)

.. py:attribute:: suspension_reasons

.. py:attribute:: termination_signal

.. py:attribute:: termination_time

Termination deadline in seconds. (Epoch UTC)
.. py:attribute:: user_name

User name of job submitter

.. py:attribute:: user_priority

User given priority for the job


    """

    @classmethod
    def submit(cls, connection, **kwargs):
        connection.login()
        allowed_keys = [
            'options',
            'options2',
            'command',
            'num_processors',
            'max_num_processors',
            'queue_name',
            'project_name'
            'job_name',
        ]

        for k in kwargs.keys():
            if k not in allowed_keys:
                raise ValueError("Argument: %s is not valid" % k)

        data = json.dumps(kwargs)
        url = connection.url + "/job/submit"
        request = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        data = connection.open(request).read()
        data = json.loads(data)
        if 'status' in data and data['status'] == 'Fail':
            raise RemoteException(data)
        return Job(connection, data=data)

    @classmethod
    def get_job_list(cls, connection, user_name=None, job_state="ACT", host_name=None, queue_name=None, job_name=None):
        url = connection.url + "/jobs/"
        if user_name == "all":
            user_name = None

        params = {
            "queue_name": queue_name,
            "job_name": job_name,
            "host_name": host_name,
            "job_state": job_state,
            "user_name": user_name,
        }
        for k, v in params.items():
            if v == None:
                del (params[k])

        url += "?" + urllib.urlencode(params)
        request = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        try:
            data = connection.open(request).read()
            data = json.loads(data)
            if not isinstance(data, list):
                print "Got strange data back"
                data = []
            return [cls(connection, data=i) for i in data]
        except:
            raise

    def __init__(self, connection, job_id=None, array_id=None, data=None):
        if job_id != None:
            if array_id == None:
                array_id = 0
            url = connection.url + "/job/%s/%s" % (job_id, array_id)
            req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
            try:
                data = connection.open(req).read()
                data = json.loads(data)
            except urllib2.HTTPError as e:
                if e.code == 404:
                    raise NoSuchObjectError("No such job: %s" % job_id)
                else:
                    raise

        if not isinstance(data, dict):
            raise ValueError("Data must be a dict")
        if data['type'] != "Job":
            raise ValueError("data is not of type Job")
        self._queue = data['queue']
        del (data['queue'])
        self._submission_host = data['submission_host']
        del (data['submission_host'])

        OpenLavaObject.__init__(self, connection, data=data)
        self.consumed_resources = [ConsumedResource(self._connection, data=d) for d in self.consumed_resources]
        self.execution_hosts = [Host(self._connection, host_name=d['name']) for d in self.execution_hosts]
        self.options = [JobOption(self._connection, data=d) for d in self.options]
        self.processes = [Process(self._connection, data=d) for d in self.processes]
        self.status = Status(self._connection, data=self.status)

    def kill(self):
        """Kills the job.  The user must be a job owner, queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure
        """
        self._exec_remote("/job/%s/%s/kill" % (self.job_id, self.array_index))

    def resume(self):
        """Resumes the job.  The user must be a job owner, queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure
        """
        self._exec_remote("/job/%s/%s/resume" % (self.job_id, self.array_index))

    def requeue(self):
        """Requeues the job.  The user must be a job owner,  queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure
        """
        self._exec_remote("/job/%s/%s/requeue" % (self.job_id, self.array_index))

    def stop(self):
        """Suspends the job.  The user must be a job owner, queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure
        """
        self._exec_remote("/job/%s/%s/stop" % (self.job_id, self.array_index))


    @property
    def submit_time_datetime(self):
        return datetime.datetime.utcfromtimestamp(self.submit_time)

    @property
    def queue(self):
        return Queue(self._connection, queue_name=self._queue['name'])

    @property
    def submission_host(self):
        return Host(self._connection, host_name=self._submission_host['name'])


class Queue(OpenLavaObject):
    """Retrieve queue information and perform administrative actions on queues on the remote cluster.

.. py:attribute:: accept_interval

Queue accept interval in seconds

.. py:attribute:: admins

List of user names that have administrative rights on this queue.

:returns: list of usernames
:rtype: list of str

.. py:attribute:: allowed_hosts

Hosts that this queue is allowed to submit to.

:returns: List of host names, or None when queue can dispatch to all hosts.
:rtype: list or None

.. py:attribute:: allowed_users

Users that may use this queue.

:returns: List of user names, or None when all users can submit to this queue.
:rtype: list or None

.. py:attribute:: attributes

Attributes of the Queue.

:returns: List of QueueAttributes
:rtype: QueueAttribute

.. py:attribute:: checkpoint_data_directory

Data where checkpoint data will be written to.

.. py:attribute:: checkpoint_period

Time in seconds between checkpointing.  -1 indicates no checkpointing.

.. py:attribute:: default_slots_per_job

The default number of job slots consumed by a job

.. py:attribute:: description

Description of the queue.

.. py:attribute:: dispatch_windows

String of time windows that the queue will dispatch during.  Empty of always open.

.. note:: Openlava scheduler only.

.. py:attribute:: host_specification

.. py:attribute:: is_accepting_jobs

Returns true if the queue is open and accepting new jobs

.. py:attribute:: is_despatching_jobs

Returns true if the queue is actively dispatching new jobs

.. py:attribute:: job_starter_command

Path to the job starter command

.. note:: Openlava scheduler only.

.. py:attribute:: max_jobs

Maximum number of jobs that may execute in the queue

.. py:attribute:: max_jobs_per_host

Maximum number of jobs per host

.. py:attribute:: max_jobs_per_processor

Maximum number of jobs per processor

.. py:attribute:: max_jobs_per_user

Maximum number of jobs per user

.. py:attribute:: max_slots

Maximum number of slots that may execute in the queue

.. py:attribute:: max_slots_per_host

Maximum number of slots that may be consumed per host

.. py:attribute:: max_slots_per_job

Maximum number of slots that can be consumed per job

.. py:attribute:: max_slots_per_processor

Maximum number of slots that can be consumed per processor

.. py:attribute:: max_slots_per_user

Maximum number of slots that can be consumed per user

.. py:attribute:: migration_threshold

.. py:attribute:: min_slots_per_job

Minimum number of slots that may be consumed per job

.. py:attribute:: name

Name of the queue

.. py:attribute:: nice

Nice value of jobs running in the queue

.. py:attribute:: num_pending_jobs

Current number of jobs that are pending

.. py:attribute:: num_pending_slots

Current number of slots that are pending

.. py:attribute:: num_reserved_slots

Current number of slots that are reserved

.. py:attribute:: num_running_jobs

Current number of jobs that are running

.. py:attribute:: num_running_slots

Current number of slots that are running

.. py:attribute:: num_suspended_jobs

Current number of jobs that are suspended

.. py:attribute:: num_suspended_slots

Current number of slots that are suspended

.. py:attribute:: num_system_suspended_jobs

Current number of jobs that are suspended by the system

.. py:attribute:: num_system_suspended_slots

Current number of slots that are suspended by the system

.. py:attribute:: num_user_suspended_jobs

Current number of jobs that are suspended by a user

.. py:attribute:: num_user_suspended_slots

Current number of slots that are suspended by a user

.. py:attribute:: post_execution_command

Command that will execute after the job has completed

.. py:attribute:: pre_execution_command

Command that will execute prior to the job executing

.. py:attribute:: pre_post_user_name

Username of the user who will execute the pre/post commands

.. py:attribute:: priority

Priority of the queue.

.. py:attribute:: requeue_exit_values

Jobs exiting with this value will be requeued

.. py:attribute:: resource_requirements

Default resource requirements of the queue

.. py:attribute:: resume_action_command

.. py:attribute:: resume_condition

.. py:attribute:: run_windows

.. py:attribute:: runtime_limits

.. py:attribute:: scheduling_delay

Delay between receiving a job and performing scheduling operations

.. py:attribute:: slot_hold_time

.. py:attribute:: statuses

.. py:attribute:: stop_condition

.. py:attribute:: suspend_action_command

.. py:attribute:: terminate_action_command

.. py:attribute:: total_jobs

Total number of jobs in the queue.

.. py:attribute:: total_slots

Total number of slots consumed by jobs in the queue.

    """

    @classmethod
    def get_queues_by_names(cls, connection, queue_names):
        """Return a list of Queue objects that match the given queue_names.

        :param list queue_names: List of queue names
        :returns: List of Queue objects that match
        :rtype: list
        """
        if len(queue_names) == 1 and queue_names[0] == "all":
            queues = cls.get_queue_list(connection)
        elif len(queue_names) == 0:
            raise NotImplementedError("Must check cluster for default queue")
            #queues = [cls(connection, queue_name=socket.gethostname())]
        else:
            queues = [cls(connection, queue_name=queue_name) for queue_name in queue_names]
        return queues

    @classmethod
    def get_queue_list(cls, connection):
        """Returns a list of Queue objects that are available.

        :returns: List of Queue objects
        :rtype: list

        """
        url = connection.url + "/queues/"
        request = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        try:
            data = connection.open(request).read()
            data = json.loads(data)
            if not isinstance(data, list):
                print "Got strange data back"
                data = []
            return [cls(connection, data=i) for i in data]
        except:
            raise

    def __init__(self, connection, queue_name=None, data=None):
        """
        :param OpenLavaConnection connection: The connection instance to use
        :param str queue_name: name of queue to load from remote server
        :param dict data: pre-populated dictionary of queue data
        """
        if queue_name:
            url = connection.url + "/queues/%s" % queue_name
            req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
            try:
                data = connection.open(req).read()
                data = json.loads(data)
            except urllib2.HTTPError as e:
                if e.code == 404:
                    raise NoSuchObjectError("No such queue: %s" % queue_name)
                else:
                    raise
        if not isinstance(data, dict):
            raise ValueError("Data must be a dict")
        if data['type'] != "Queue":
            raise ValueError("data is not of type Queue")
        OpenLavaObject.__init__(self, connection, data=data)
        self.attributes = [Status(self._connection, data=attr) for attr in self.attributes]
        self.statuses = [Status(self._connection, data=status) for status in self.statuses]
        # runtime limits

    def jobs(self):
        """Returns a list of SimpleJob objects."""
        raise NotImplementedError

    def close(self):
        """Closes the queue.  The user must be a queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure"""
        self._exec_remote("/queues/%s/close" % self.name)

    def open(self):
        """Opens the queue.  The user must be a queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure"""
        self._exec_remote("/queues/%s/open" % self.name)

    def inactivate(self):
        """Inactivates the queue.  The user must be a queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure"""
        self._exec_remote("/queues/%s/inactivate" % self.name)

    def activate(self):
        """Activates the queue.  The user must be a queue or cluster administrator for this operation to succeed.

        :raise: RemoteException on failure"""
        self._exec_remote("/queues/%s/activate" % self.name)


__ALL__ = [OpenLavaConnection, AuthenticationError, RemoteException, NoSuchObjectError, Host, Job]
