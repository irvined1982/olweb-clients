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
    """Connection and authentication handler for dealing with the server.  Subclass this when you need a different method of authentication"""

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
        f = urllib2.urlopen(req)
        data = json.loads(f.read())
        f.close()
        if not self.authenticated:
            raise AuthenticationError(data['description'])

    def _open(self, request):
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
    @classmethod
    def get_hosts_by_names(cls, connection, host_names):
        if len(host_names) == 1 and host_names[0] == "all":
            hosts = cls.get_host_list(connection)
        elif len(host_names) == 0:
            hosts = [cls(connection, host_name=socket.gethostname())]
        else:
            hosts = [cls(connection, host_name=host_name) for host_name in host_names]
        return hosts


    @classmethod
    def get_host_list(cls, connection):
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
        raise NotImplementedError

    def close(self):
        self._exec_remote("/hosts/%s/close" % self.host_name)

    def open(self):
        self._exec_remote("/hosts/%s/open" % self.host_name)


class NoSuchObjectError(Exception):
    pass


class LoadInformation(OpenLavaObject):
    pass


class LoadValueList(OpenLavaObject):
    pass


class RemoteException(Exception):
    def __init__(self, data):
        Exception.__init__(self, data['message'])
        for k, v in data.iteritems():
            setattr(self, k, v)


class Status(OpenLavaObject):
    pass


class Resource(OpenLavaObject):
    """Resource"""
    pass


class ConsumedResource(OpenLavaObject):
    pass


class ExecutionHost(OpenLavaObject):
    pass


class JobOption(OpenLavaObject):
    pass


class Process(OpenLavaObject):
    pass


class Job(OpenLavaObject):
    @classmethod
    def submit(cls, connection, **kwargs):
        connection.login()
        allowed_keys=[
            'options',
            'options2',
            'command',
            'num_processors',
            'max_num_processors',
        ]

        for k in kwargs.keys():
            if k not in allowed_keys:
                raise ValueError("Argument: %s is not valid" % k)

        data = json.dumps(kwargs)
        url = connection.url + "/job/submit"
        request = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        data=connection.open(request).read()
        data = json.loads(data)


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
        self.execution_hosts = [ExecutionHost(self._connection, data=d) for d in self.execution_hosts]
        self.options = [JobOption(self._connection, data=d) for d in self.options]
        self.processes = [Process(self._connection, data=d) for d in self.processes]
        self.status = Status(self._connection, data=self.status)

    def kill(self):
        self._exec_remote("/job/%s/%s/kill" % (self.job_id, self.array_index))

    def resume(self):
        self._exec_remote("/job/%s/%s/resume" % (self.job_id, self.array_index))

    def requeue(self):
        self._exec_remote("/job/%s/%s/requeue" % (self.job_id, self.array_index))

    def stop(self):
        self._exec_remote("/job/%s/%s/stop" % (self.job_id, self.array_index))


    @property
    def submit_time_datetime(self):
        return datetime.datetime.fromtimestamp(self.submit_time)

    @property
    def queue(self):
        return Queue(self._connection, queue_name=self._queue['name'])

    @property
    def submission_host(self):
        return Host(self._connection, host_name=self._submission_host['name'])


class Queue(OpenLavaObject):
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