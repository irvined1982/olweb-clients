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
import logging
import tempfile


class RemoteServerError(Exception):
    """
    Raised when the remote server is not found, fails, or otherwise does not behave in a standard way
    for example when giving err 500

    """


class AuthenticationError(RemoteServerError):
    """
    Raised when the client is unable to authenticate to the server

    """
    pass


class NoSuchHostError(RemoteServerError):
    """
    Raised when the requested host does not exist in the job scheduling environment, or it is not visible/accessible
    by the current user.
    """
    pass


class NoSuchJobError(RemoteServerError):
    """
    Raised when the requested job does not exist in the job scheduling environment.  This can happen when the
    job has been completed, and the scheduler has purged the job from the active jobs.
    """
    pass


class NoSuchQueueError(RemoteServerError):
    """
    Raised when the requested queue does not exist in the job scheduling environment, or it is not visible/accessible
    by the current user.
    """
    pass


class NoSuchUserError(RemoteServerError):
    """
    Raised when the requested user does not exist in the job scheduling environment.
    """
    pass


class ResourceDoesntExistError(RemoteServerError):
    """
    Raised when the requested resource does not exist in the job scheduling environment.
    """
    pass


class ClusterInterfaceError(RemoteServerError):
    """
    Raised when the underlying API call fails, for example due to a network fault, or the job scheduler
    being unavailable.
    """
    pass


class PermissionDeniedError(RemoteServerError):
    """
    Raised when the current user does not have sufficiant privilages to perform for requested operation
    """
    pass


class JobSubmitError(RemoteServerError):
    """
    Raised when a job cannot be submitted
    """
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
        """
        True if the connection is currently authenticated

        :returns: True if the connection is currently authenticated
        :rtype: Boolean

        """
        for c in self._cookies:
            if c.name == 'sessionid':
                return True
        return False

    def login(self):
        """
        Logs the user into the server.

        :raise: AuthenticationError if the user cannot be authenticated
        """
        data = {
            'username': self.username,
            'password': self.password,
        }
        data = json.dumps(data, sort_keys=True, indent=4)
        url = self.url + "/accounts/ajax_login"
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        self._open(req)

        if not self.authenticated:
            raise AuthenticationError(data['description'])

        url = self.url + "/get_token"
        req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        data = self._open(req)
        self._csrf_token = data['cookie']
        found = False
        for h in self._opener.addheaders:
            if h[0] == 'X-CSRFToken':
                found = True
        if not found:
            self._opener.addheaders.append(('X-CSRFToken', self._csrf_token))

    def _open(self, request):
        """
        Open a connection to the server, get and parse the response.

        :param request: urllib request object
        :return: deserialized response from server.
        :raises: RemoteServerError
        :raises: AuthenticationError

        """

        if self._referer:
            headers = []
            for h in self._opener.addheaders:
                if h[0] == 'Referer':
                    continue
                else:
                    headers.append(h)
            headers.append(('Referer', self._referer))
            self._opener.addheaders = headers

        self._referer = request.get_full_url()
        try:
            response = self._opener.open(request)

            # Check the content type is correct
            for header in response.info().headers:
                if header.startswith("Content-Type") and not header.startswith("Content-Type: application/json"):
                    raise RemoteServerError(
                        "Expected a content_type of application/json however the header was: %s" % header)

            data = json.load(response)

            # Close connection, no longer required.
            response.close()

            if not "status" in data:
                raise RemoteServerError("Response did not contain status attribute")

            if not "message" in data:
                raise RemoteServerError("Response did not contain message attribute")

            if not "data" in data:
                raise RemoteServerError("Response did not contain data attribute")

            if data['status'] != "OK":
                exception_data = data['data']
                for sc in RemoteServerError.__subclasses__():
                    if sc.__name__ == exception_data['exception_class']:
                        raise sc(exception_data['message'])
                raise RemoteServerError("The operation failed: %s" % data['message'])
            return data['data']

        except urllib2.HTTPError as e:
            if e.code in [400, 401, 403, 404, 500]:
                # noinspection PyBroadException
                try:
                    exception_data = json.load(e)
                    exception_data = exception_data['data']
                    for sc in RemoteServerError.__subclasses__():
                        if sc.__name__ == exception_data['exception_class']:
                            raise sc(exception_data['message'])
                    raise RemoteServerError("The operation failed: %s" % exception_data['message'])
                except Exception:
                    if e.code == 403 and self.authenticated:
                        raise PermissionDeniedError("Unknown authentication/authorization failure, check server logs")
                    elif e.code == 500:
                        f = tempfile.NamedTemporaryFile(delete=False)
                        f.write(e.read())
                        f.close()
                        raise RemoteServerError("Server returned error 500, output stored in: %s" % f.name)
                    else:
                        raise RemoteServerError("Invalid server URL, or misconfigured web server")
            raise

    def open(self, request):
        """
        Authenticates if required using login, then calls _open to make the connection and get the data.

        :param urllib2.Request request: Request object with appropriate URL configured
        :returns: deserialized data returned from server
        :rtype: object

        """

        if not self.authenticated:
            self.login()
        return self._open(request)


class StatusType(object):
    def __unicode__(self):
        return u'%s' % self.friendly

    def __repr__(self):
        return u'%s' % self.name

    def __str__(self):
        return '%s' % self.friendly


class OpenLavaObject(object):
    """
    Base class for OpenLava objects, automatically populates attributes based on values returned from
    the server.

    """

    def __init__(self, connection, data=None):
        """
        Create a new instance.

        :param OpenLavaConnection connection:

            Connection object that will be used to connect to the server and retrieve data.

        :param dict data:

            Optional dictionary containing pre-retrieved data from the server, this will be populated into
            the objects data structure

        """
        self._connection = connection
        if data is not None:
            if not isinstance(data, dict):
                raise ValueError("Must be a dict")
            for k, v in data.iteritems():
                setattr(self, k, v)

    def _exec_remote(self, url):
        """
        Open a url on the server, and get the result

        :param url: URL to open
        :return: Deserialized JSON response from server as object
        """
        url = self._connection.url + url
        req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        return self._connection.open(req)


class Host(OpenLavaObject):
    """
    Retrieve Host information and perform administrative actions on hosts on the cluster.  Hosts are any kind
    of host associated with the cluster, they may be submit hosts, execution hosts, clients, etc.

    .. py:attribute:: cluster_type

        The type of cluster this host object is associated with.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.cluster_type
            u'openlava'

    .. py:attribute:: name

        The host name of the host.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.name
            u'...'

        :return: hostname
        :rtype: str

    .. py:attribute:: host_name

        The host name of the host.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.name
            u'...'

        :return: hostname
        :rtype: str

    .. py:attribute:: description

        The description given to the host by the cluster administrators.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.description
            u''

        :return: Host description
        :rtype: str

    .. py:attribute:: load_information

        Return load information on the host.  Load information is a collection of available metrics that describe
        the current load of the host.  Such as the CPU usage, memory consumption, and available disk space.  These
        vary based on the host type, operating system and scheduler.

        The dict has three fields, names, short_names, and values, each a list of the same length.  Names
        contains a list of field names, short_names contains a shorter version of the name, and values contains
        the corresponding value of the field.  A value of -1 is unlimited.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> info=host.load_information
            >>> for i in range(len(info['names'])):
            ...     values = ""
            ...     for v in info['values']:
            ...         values += "%s(%s) " % (v['values'][i], v['name'])
            ...     print "%s(%s): %s" % (info['names'][i], info['short_names'][i], values)
            ...
            15s Load(r15s): 0.0599999427795(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            1m Load(r1m): 0.039999961853(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            15m Load(r15m): 0.0499999523163(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Avg CPU Utilization(ut): 0.0759999975562(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Paging Rate (Pages/Sec)(pg): 0.0(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Disk IO Rate (MB/Sec)(io): 0.0(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Num Users(ls): 3.0(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Idle Time(it): 1.0(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Tmp Space (MB)(tmp): 54141.0(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Free Swap (MB)(swp): 507.03125(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)
            Free Memory (MB)(mem): 625.3515625(Actual Load) -1(Stop Dispatching Load) -1(Stop Executing Load)

        :returns: dictionary of load index dictionaries
        :rtype: dictionary

    .. py:attribute:: admins

        Gets the host administrators.  Host administrators can perform any action on the host.
        This does not imply they are actual superusers on the physical systems.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.admins
            [u'openlava']

        :returns: Array of usernames
        :rtype: array
        :raise: OpenLavaError on failure

    .. py:attribute:: is_busy

        Returns True if the host is busy.  Busy is defined as a host that is running jobs.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.is_busy
            False

        :return: True if the host is busy.
        :rtype: bool

    .. py:attribute:: is_down

        Returns True if the host is down. Down is defined as not being available to the scheduler.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.is_down
            False

        :return: True if the host is down.
        :rtype: bool

    .. py:attribute:: is_closed

        Returns True if the host is closed for new jobs.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.is_closed
            False

        :return: True if the host is closed.
        :rtype: bool

    .. py:attribute:: has_checkpoint_support

        Returns True if the host supports checkpointing.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.has_checkpoint_support
            True

        :return: True if checkpoint support is enabled
        :rtype: bool

    .. py:attribute:: host_model

        String containing host model information

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.host_model
            u'IntelI5'

        :return: Host model name
        :rtype: str

    .. py:attribute:: host_type

        String containing host type information.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.host_type
            u'linux'

        :return: Host Type
        :rtype: str

    .. py:attribute:: resources

        Gets a list of resources that are available on this host.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.resources
            [foo]

        :return: List of :py:class:`cluster.openlavacluster.Resource` objects
        :rtype: :py:class:`cluster.openlavacluster.Resource`

    .. py:attribute:: max_jobs

        Returns the maximum number of jobs that may execute on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.max_jobs
            2

        :return: Maximum number of jobs
        :rtype: int

    .. py:attribute:: max_processors

        Returns the maximum number of processors (Job Slots) available on the host for all jobs.

        .. note::
            If max_slots is greater than max_processors, then there will be contention for physical cores.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.max_processors
            1

        :return: Max processors (Slots)
        :rtype: int

    .. py:attribute:: max_ram

        Max Ram that can be consumed by jobs, in Kb

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.max_ram
            992

        :return: Max Ram (Mb)
        :rtype: int

    .. py:attribute:: max_slots

        Returns the maximum number of scheduling slots that may be consumed on this host

        .. note::
            If max_slots is greater than max_processors, then there will be contention for physical cores.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.max_slots
            2

        :return: Max slots
        :rtype: int

    .. py:attribute:: max_swap

        Max swap space that may be consumed by jobs on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.max_swap
            509

        :return: Max Swap Space (Mb)
        :rtype: int

    .. py:attribute:: max_tmp

        Max swap space that may be consumed by jobs on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.max_tmp
            64002

        :return: Max Swap (Mb)
        :rtype: int

    .. py:attribute:: num_reserved_slots

        Returns the number of scheduling slots that are reserved

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_reserved_slots
            0

        :return: Number of reserved slots
        :rtype: int

    .. py:attribute:: num_running_jobs

        Returns the number of concurent jobs that are executing on the host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_running_jobs
            0

        :return: Job count
        :rtype: int

    .. py:attribute:: num_running_slots

        Returns the total number of scheduling slots that are consumed on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_running_slots
            0

        :return: slot count
        :rtype: int

    .. py:attribute:: num_suspended_jobs

        Returns the number of jobs that are suspended on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_suspended_jobs
            0

        :return: Suspended job count
        :rtype: int

    .. py:attribute:: num_suspended_slots

        Returns the number of scheduling slots that are suspended on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_suspended_slots
            0

        :return: suspended slot count
        :rtype: int

    .. py:attribute:: run_windows

        Openlava run windows that are defined in the hosts configuration

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.run_windows
            u'-'

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: Run Windows
        :rtype: str

    .. py:attribute:: statuses

        Hosts can have one or more statuses that apply.  Statuses indicate the condition of the host, such as its
        availability, and health.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.statuses
            [HOST_STAT_OK]

        :return: List of statuses that apply to hist host
        :rtype: list of :py:class:`cluster.openlavacluster.JobStatus` objects

    .. py:attribute:: total_jobs

        Returns the total number of jobs that are running on this host, including suspended jobs.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.total_jobs
            0

        :return: running job count
        :rtype: int

    .. py:attribute:: total_slots

        Returns the total number of slots that are consumed on this host, including those from  suspended jobs.

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.total_slots
            0

        :return: consumed slot count
        :rtype: int

        .. py:attribute:: cpu_factor

        Returns the CPU factor of the host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.cpu_factor
            100.0

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: CPU Factor of the host
        :rtype: float

    .. py:attribute:: is_server

        True if host is an openlava server (as opposed to submission host)

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.is_server
            True

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: True if host can run jobs
        :rtype: bool

    .. py:attribute:: num_disks

        Openlava specific: Returns the number of physical disks installed in the machine

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_disks
            0

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: Num physical disks
        :rtype: int
        
    .. py:attribute:: num_user_suspended_jobs

        Returns the number of jobs that have been suspended by the user on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_user_suspended_jobs
            0

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: user suspended job count
        :rtype: int

    .. py:attribute:: num_user_suspended_jobs

        Returns the number of scheduling slots that have been suspended by the user on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_user_suspended_slots
            0

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: user suspened slot count
        :rtype: int

    .. py:attribute:: num_system_suspended_jobs

        Returns the number of jobs that have been suspended by the system on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]            
            >>> host.num_system_suspended_jobs
            0

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: system suspended job count
        :rtype: int

    .. py:attribute:: num_system_suspended_slots

        Returns the number of scheduling slots that have been suspended by the system on this host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]
            >>> host.num_system_suspended_slots
            0

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: system suspended slot count
        :rtype: int

    .. py:attribute:: has_kernel_checkpoint_copy

        Returns true if the host supports kernel checkpointing

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]            
            >>> host.has_kernel_checkpoint_copy
            False

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: True if kernel can checkpoint
        :rtype: bool

    .. py:attribute:: max_slots_per_user

        Returns the maximum slots that a user can occupy on the host

        Example::

            >>> from olwclient import OpenLavaConnection, Host
            >>> class ConnectionArgs:
            ...  username="testuser"
            ...  password="password"
            ...  url="http://example.com/olweb/"
            ...
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> host=Host.get_host_list(c)[0]            
            >>> host.max_slots_per_user
            2147483647

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: Max slots per user
        :rtype: int

"""

    def __str__(self):
        return self.host_name

    def __unicode__(self):
        return u"%s" % self.host_name

    def __repr__(self):
        return self.__str__()

    @classmethod
    def get_hosts_by_names(cls, connection, host_names):
        """
        Return a list of Host objects that are in host_names

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
        """
        Get all hosts that are part of the cluster.

        Example::

            >>> from openlavacluster import Host
            >>> host=Host.get_host_list()[0]
            >>> Host.get_host_list()
            [master, comp00, comp01, comp02, comp03, comp04]

        :return: List of :py:class:`cluster.openlavacluster.Host` Objects, one for each host on the cluster.
        :rtype: list

        """
        url = connection.url + "/hosts"
        request = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        try:
            data = connection.open(request)
            return [Host(connection, data=i) for i in data]
        except:
            raise

    def __init__(self, connection, host_name=None, data=None):
        """
        Retrieve Host information and perform administrative actions on hosts on the cluster.  Hosts are any kind
        of host associated with the cluster, they may be submit hosts, execution hosts, clients, etc.

        :param connection:
        :param host_name:
        :param data:
        :return:
        """

        if host_name:
            url = connection.url + "/hosts/%s?json=1" % host_name
            req = urllib2.Request(url, None, {'Content-Type': 'application/json'})

            data = connection.open(req)

        if not isinstance(data, dict):
            raise ValueError("Data must be a dict")
        if data['type'] not in ["Host", "ExecutionHost"]:
            raise ValueError("data is not of type Host")
        if 'jobs' in data:
            del(data['jobs'])  # jobs is a method, not a property.

        OpenLavaObject.__init__(self, connection, data=data)
        self.resources = [Resource(self._connection, data=res) for res in self.resources]
        self.statuses = [Status(self._connection, data=status) for status in self.statuses]

    def jobs(self, **kwargs):
        """
        Returns matching jobs on the host.  By default, returns all jobs that are executing on the host.

        .. note::

            This performs a request to the server to get the current jobs executing. It does not use
            the short job list returned by the initial host call.  This mirrors the behavior
            of the local class.

        Example::

            >>> from openlavacluster import Host
            >>> host=Host.get_host_list()[0]
            >>> host.jobs()
            [9790]

        :param job_id: Only return jobs matching the specified job id.
        :param job_name: Only return jobs matching the specified job name.
        :param user: Only return jobs belonging to the specified user.
        :param queue: Only return jobs belonging to the specified queue.
        :param options: Unused.
        :return: List of :py:class:`cluster.openlavacluster.Job` objects
        """

        return Job.get_job_list(self._connection, host_name=self.name, **kwargs)

    def close(self):
        """
        Closes the host, when a host is closed, it will no longer accept new jobs.

        Example::

            >>> from openlavacluster import Host
            >>> host=Host.get_host_list()[0]
            >>> host.close()
            Traceback (most recent call last):
              ...
            cluster.PermissionDeniedError: Unable to close host: master: User permission denied

        :return: 0 on success
        :raises: :py:exc:`cluster.openlavacluster.RemoteServerError` when host cannot be closed.
        """
        self._exec_remote("/hosts/%s/close" % self.host_name)

    def open(self):
        """
                Opens the host, when a host is closed, it will no longer accept new jobs.

        Example::

            >>> from openlavacluster import Host
            >>> host=Host.get_host_list()[0]
            >>> host.open()
            Traceback (most recent call last):
              ...
            cluster.PermissionDeniedError: Unable to open host: master: User permission denied

        :return: 0 on success
        :raises: :py:exc:`cluster.openlavacluster.RemoteServerError` when host cannot be opened.

    """
        self._exec_remote("/hosts/%s/open" % self.host_name)


class Status(OpenLavaObject, StatusType):
    """
    Status of an object.

    .. py:attribute:: description

        Description of the status

    .. py:attribute:: friendly

        Friendly name for the status

    .. py:attribute:: name

        Full name of the status

    .. py:attribute:: status

        Numeric code of the status

    """


class User(OpenLavaObject):
    """


    """

    @classmethod
    def get_user_list(cls, connection):
        """
        Returns a list of User objects that are available.

        :returns: List of User objects
        :rtype: list
        :raise: RemoteServerError

        """
        url = connection.url + "/users/"
        request = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        try:
            data = connection.open(request)
            if not isinstance(data, list):
                raise RemoteServerError("Invalid data returned from server")
            return [cls(connection, data=i) for i in data]
        except:
            raise

    def __init__(self, connection, user_name=None, data=None):
        """
        :param OpenLavaConnection connection: The connection instance to use
        :param str user_name: name of user to load from remote server
        :param dict data: pre-populated dictionary of user data
        """
        if user_name:
            url = connection.url + "/users/%s" % user_name
            req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
            data = connection.open(req)

        if not isinstance(data, dict):
            raise ValueError("Data must be a dict")

        if data['type'] != "User":
            raise ValueError("data is not of type User")

        del data['jobs']  # Handled by method, not returned data.
        OpenLavaObject.__init__(self, connection, data=data)

    def __str__(self):
        return "%s" % self.name

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __repr__(self):
        return self.__str__()

    def jobs(self, **kwargs):
        """
        Returns matching jobs for this user.  By default, returns all jobs that are submitted by this user.

        Example::

            >>> from openlavacluster import User
            >>> user = User.get_queue_list()[0]
            >>> user.jobs()
            [9790]

        :param job_id: Only return jobs matching the specified job id.
        :param job_name: Only return jobs matching the specified job name.
        :param host_name: Only return jobs executing on the specified host.
        :param queue_name: Only return jobs executing on the specified host.
        :param options: Unused.
        :return: List of :py:class:`.Job` objects

        """
        return Job.get_job_list(user_name=self.name, **kwargs)


class Queue(OpenLavaObject):
    """


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
        else:
            queues = [cls(connection, queue_name=queue_name) for queue_name in queue_names]
        return queues

    @classmethod
    def get_queue_list(cls, connection):
        """Returns a list of Queue objects that are available.

        :returns: List of Queue objects
        :rtype: list
        :raise: RemoteServerError

        """
        url = connection.url + "/queues/"
        request = urllib2.Request(url, None, {'Content-Type': 'application/json'})
        try:
            data = connection.open(request)
            if not isinstance(data, list):
                raise RemoteServerError("Invalid data returned from server")
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
            data = connection.open(req)

        if not isinstance(data, dict):
            raise ValueError("Data must be a dict")

        if data['type'] != "Queue":
            raise ValueError("data is not of type Queue")

        del data['jobs']  # Handled by method, not returned data.
        OpenLavaObject.__init__(self, connection, data=data)
        self.attributes = [Status(self._connection, data=attr) for attr in self.attributes]
        self.statuses = [Status(self._connection, data=status) for status in self.statuses]
        self.runtime_limits = [ResourceLimit(self._connection, data=d) for d in self.runtime_limits]

    def __str__(self):
        return "%s" % self.name

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __repr__(self):
        return self.__str__()

    def jobs(self, **kwargs):
        """
        Returns matching jobs on the queue.  By default, returns all jobs that are executing on the queue.

        Example::

            >>> from openlavacluster import Queue
            >>> queue = Queue.get_queue_list()[0]
            >>> queue.jobs()
            [9790]

        :param job_id: Only return jobs matching the specified job id.
        :param job_name: Only return jobs matching the specified job name.
        :param user: Only return jobs belonging to the specified user.
        :param _name: Only return jobs executing on the specified host.
        :param options: Unused.
        :return: List of :py:class:`cluster.openlavacluster.Job` objects

        """
        return Job.get_job_list(queue_name=self.name, **kwargs)

    def close(self):
        """
        Closes the queue, once closed no new jobs will be accepted.

        The user must be a queue administrator for this operation to succeed.

        :raises :py:exc:`olwclient.PermissionDeniedError`: The user does not have permission to perform this operation.

        """
        self._exec_remote("/queues/%s/close" % self.name)

    def open(self):
        """
        Opens the queue, once open new jobs will be accepted.

        The user must be a queue administrator for this operation to succeed.

        :raises :py:exc:`olwclient.PermissionDeniedError`: The user does not have permission to perform this operation.

        """
        self._exec_remote("/queues/%s/open" % self.name)

    def inactivate(self):
        """
        Inactivates the queue, when inactive jobs will no longer be dispatched.

        The user must be a queue administrator for this operation to succeed.

        :raises :py:exc:`olwclient.PermissionDeniedError`: The user does not have permission to perform this operation.

        """
        self._exec_remote("/queues/%s/inactivate" % self.name)

    def activate(self):
        """
        Activates the queue, when active, jobs will be dispatched to hosts for execution.

        The user must be a queue administrator for this operation to succeed.

        :raises :py:exc:`olwclient.PermissionDeniedError`: The user does not have permission to perform this operation.

        """
        self._exec_remote("/queues/%s/activate" % self.name)


class ExecutionHost(Host):
    """
    Execution Hosts are hosts that are executing jobs, a subclass of :py:class:`cluster.openlavacluster.Host`,
    they have the additional num_slots_for_job attribute indicating how many slots (Processors) are allocated
    to the job.

    .. py:attribute:: num_slots_for_job

        The number of slots that are allocated to the job.

        :return: Slots consumed by job
        :rtype: int

    """

    def __init__(self, connection, host_name=None, num_slots_for_job=None, data=None):
        if host_name and num_slots_for_job:
            Host.__init__(self, connection, host_name=host_name)
            self.num_slots_for_job = num_slots_for_job
        else:
            self._connection = connection
            self._url = data['url']
            self._loaded_from_server = False
            self.host_name = data['name']
            self.name = data['name']
            self.num_slots_for_job = data['num_slots']

    def __getattr__(self, name):
        if self._loaded_from_server:
            raise AttributeError
        else:
            Host.__init__(self, self._connection, host_name=self.name)
            if hasattr(self, name):
                return getattr(self, name)
            else:
                raise AttributeError

    def __str__(self):
        return "%s:%s" % (self.host_name, self.num_slots_for_job)

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __repr__(self):
        return self.__str__()


class ResourceLimit(OpenLavaObject):
    """
    Resource limits are limits on the amount of resource usage of a Job, Queue, Host or User.  Resource
    Limits may be specified by the user, or as an administator through the scheduler configuration.

    .. py:attribute:: name

        The name of the resource

    .. py:attribute:: soft_limit

        The soft limit of the resource, when this limit is reached, an action is performed on the job, usually
        this is is in the form of a non-fatal signal being sent to the job.

    .. py:attribute:: hard_limit

        The hard limit of the resource, when this limit is reached, the job is terminated.

    .. py:attribute:: description

        A description of the resource limit

    .. py:attribute:: unit

        The unit of measurement

    """

    def __str__(self):
        return "%s:%s (%s)" % (self.name, self.soft_limit, self.hard_limit)

    def __repr__(self):
        return self.__str__()

    def __unicode__(self):
        return u"%s" % self.__str__()


class ConsumedResource(OpenLavaObject):
    """
        .. py:attribute:: name

        The name of the consumed resource.

        :return: name of resource
        :rtype: str

    .. py:attribute:: value

        The current value of the consumed resource.

        :return: value of resource
        :rtype: str

    .. py:attribute:: limit

        The limit specified for the resource, may be None, if the resource does not have a limit.

        :return: limit of resource consumption
        :rtype: str

    .. py:attribute:: unit

        The unit of measurement for the resource, may be None, if the unit cannot be determined.

        :return: unit of measurement
        :rtype: str

    """

    def __str__(self):
        s = "%s: %s" % (self.name, self.value)
        if self.unit:
            s += "%s" % self.unit

        if self.limit:
            s += " (%s)" % self.limit

        return s

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __repr__(self):
        return self.__str__()


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
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "%s" % self.name

    def __unicode__(self):
        return u"%s" % self.__str__()


class JobOption(OpenLavaObject, StatusType):
    """
    When a job is submitted, it may be submitted with options that define job behavior.   These may be to
    define the job behavior such as host exclusivity, or to specify that other fields, such as job name have
    been used.

    .. py:attribute:: name

        Gets the name of the status, this is generally the name of the constant defined in the Openlava header
        file.

        :return: Status Name
        :rtype: str

    .. py:attribute:: description

        Gets the description of the status, this is the human readable description of the status, it is generally
        the human readable description defined in the `Openlava <http://www.openlava.org/>`_ header file.

        .. note:

            Descriptions may be empty.

        :return: Description of the status.
        :rtype: str

    .. py:attribute:: status

        Returns the status code, this is the numeric value of the code. This is generally the value of the constant
        defined in the `Openlava <http://www.openlava.org/>`_ header file.

        :return: The status code
        :rtype: int


    .. py:attribute:: friendly

        A friendly name for the status, this is a short, human readable name.

        :return: Human readable status name
        :rtype: str

    .. list-table:: Valid Statuses for Openlava Jobs
        :header-rows: 1

        * - Value
          - Friendly Name
          - Name
          - Description
        * - 0x01
          - SUB_JOB_NAME
          - Job submitted with name
          - Submitted with a job name
        * - 0x02
          - SUB_QUEUE
          - Job submitted with queue
          -
        * - 0x04
          - SUB_HOST
          - SUB_HOST
          -
        * - 0x08
          - SUB_IN_FILE
          - Job Submitted with input file
          -
        * - 0x10
          - SUB_OUT_FILE
          - Job submitted with output file
          -
        * - 0x20
          - SUB_ERR_FILE
          - Job submitted with error file
          -
        * - 0x40
          - SUB_EXCLUSIVE
          - Job submitted to run exclusively
          -
        * - 0x80
          - SUB_NOTIFY_END
          - SUB_NOTIFY_END
          -
        * - 0x100
          - SUB_NOTIFY_BEGIN
          - SUB_NOTIFY_BEGIN
          -
        * - 0x200
          - SUB_USER_GROUP
          - SUB_USER_GROUP
          -
        * - 0x400
          - SUB_CHKPNT_PERIOD
          - Job submitted with checkpoint period
          -
        * - 0x800
          - SUB_CHKPNT_DIR
          - Job submitted with checkpoint directory
          -
        * - 0x1000
          - SUB_RESTART_FORCE
          - SUB_RESTART_FORCE
          -
        * - 0x2000
          - SUB_RESTART
          - SUB_RESTART
          -
        * - 0x4000
          - SUB_RERUNNABLE
          - Job submitted as rerunnable
          -
        * - 0x8000
          - SUB_WINDOW_SIG
          - SUB_WINDOW_SIG
          -
        * - 0x10000
          - SUB_HOST_SPEC
          - Job submitted with host spec
          -
        * - 0x20000
          - SUB_DEPEND_COND
          - Job submitted with depend conditions
          -
        * - 0x40000
          - SUB_RES_REQ
          - Job submitted with resource request
          -
        * - 0x80000
          - SUB_OTHER_FILES
          - SUB_OTHER_FILES
          -
        * - 0x100000
          - SUB_PRE_EXEC
          - Job submitted with pre exec script
          -
        * - 0x200000
          - SUB_LOGIN_SHELL
          - Job submitted with login shell
          -
        * - 0x400000
          - SUB_MAIL_USER
          - Job submitted to email user
          -
        * - 0x800000
          - SUB_MODIFY
          - SUB_MODIFY
          -
        * - 0x1000000
          - SUB_MODIFY_ONCE
          - SUB_MODIFY_ONCE
          -
        * - 0x2000000
          - SUB_PROJECT_NAME
          - Job submitted to project
          -
        * - 0x4000000
          - SUB_INTERACTIVE
          - Job submitted as interactive
          -
        * - 0x8000000
          - SUB_PTY
          - SUB_PTY
          -
        * - 0x10000000
          - SUB_PTY_SHELL
          - SUB_PTY_SHELL
          -
        * - 0x01
          - SUB2_HOLD
          - SUB2_HOLD
          -
        * - 0x02
          - SUB2_MODIFY_CMD
          - SUB2_MODIFY_CMD
          -
        * - 0x04
          - SUB2_BSUB_BLOCK
          - SUB2_BSUB_BLOCK
          -
        * - 0x08
          - SUB2_HOST_NT
          - SUB2_HOST_NT
          -
        * - 0x10
          - SUB2_HOST_UX
          - SUB2_HOST_UX
          -
        * - 0x20
          - SUB2_QUEUE_CHKPNT
          - SUB2_QUEUE_CHKPNT
          -
        * - 0x40
          - SUB2_QUEUE_RERUNNABLE
          - SUB2_QUEUE_RERUNNABLE
          -
        * - 0x80
          - SUB2_IN_FILE_SPOOL
          - SUB2_IN_FILE_SPOOL
          -
        * - 0x100
          - SUB2_JOB_CMD_SPOOL
          - SUB2_JOB_CMD_SPOOL
          -
        * - 0x200
          - SUB2_JOB_PRIORITY
          - SUB2_JOB_PRIORITY
          -
        * - 0x400
          - SUB2_USE_DEF_PROCLIMIT
          - SUB2_USE_DEF_PROCLIMIT
          -
        * - 0x800
          - SUB2_MODIFY_RUN_JOB
          - SUB2_MODIFY_RUN_JOB
          -
        * - 0x1000
          - SUB2_MODIFY_PEND_JOB
          - SUB2_MODIFY_PEND_JOB
          -

    """


class Process(OpenLavaObject):
    """
    Processes represent executing processes that are part of a job.  Where supported the scheduler may
    keep track of processes spawned by the job.  Information about the process is returned in Process
    classes.

    .. py:attribute:: hostname

        The name of the host that the process is running on.  This may not be available if the scheduler does not
        track which hosts start which process.

    .. py:attribute:: process_id

        The numerical ID of the running process.

    .. py:attribute:: extras

        A list of extra field names that are available

    """

    def __str__(self):
        return "%s:%s" % (self.hostname, self.process_id)

    def __unicode__(self):
        return u"%s" % self.__str__()

    def __repr__(self):
        return self.__str__()


class Job(OpenLavaObject):
    """
    Get information about, and manipulate jobs using olwclient to communicate with an openlava-web server.
    There is no requirement for the current host to be part of the underlying cluster, all scheduler interaction
    will be handled by the remote server.

    .. py:attribute:: cluster_type

        The type of cluster, defines the scheduling environment being used under the hood.  This is always
        a short string giving the name of the scheduler, for example for `Openlava <http://www.openlava.org/>`_,
        it will return openlava, for Sun Grid Engine, it will return sge, etc.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.cluster_type
            u'openlava'

        :return: Scheduler type
        :rtype: str

    .. py:attribute:: array_index

        The array index of the job, 0 for non-array jobs.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.array_index
            0

        :return: Array Index
        :rtype: int

    .. py:attribute:: job_id

        Numerical Job ID of the job, not including the array index.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.job_id
            1234

        :return: Job ID
        :rtype: int

    .. py:attribute:: admins

        List of user names that have administrative rights for this job. This is the job Owner and the Queue
        administrators.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.admins
            [u'irvined', u'openlava']
            >>>

        :returns: list of user names
        :rtype: list

    .. py:attribute:: begin_time

        Earliest time (Epoch UTC) that the job may begin.  Job will not start before this time.  If no begin time
        was specified in job submission then the value will be zero.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.begin_time
            0

        :return: Earliest start time of the job as integer since the Epoch (UTC)
        :rtype: int

    .. py:attribute:: command

        Command to execute as specified by the user.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.command
            u'sleep 1000'

        :return: Command as string
        :rtype: str

    .. py:attribute:: consumed_resources

        The scheduler may keep track of various resources that are consumed by the job, these are
        returned as a list of :py:class:`olwclient.ConsumedResource` objects, one for each resource consumed.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.consumed_resources
            [Resident Memory: 0KB (-1), Virtual Memory: 0KB (-1), User Time: 0:00:00None (-1),
            System Time: 0:00:00None (None), Num Active Processes: 0Processes (None)]

        :return: List of :py:class:`olwclient.ConsumedResource` Objects

    .. py:attribute:: cpu_time

        CPU Time in seconds that the job has consumed.  This is the amount of processor time, consumed by the job.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.cpu_time
            0.0

        :return: CPU time in seconds
        :rtype: float

    .. py:attribute:: dependency_condition

        Dependency conditions that must be met before the job will be dispatched.  Returns an empty string if
        no job dependencies have been specified.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.dependency_condition
            u''

        :return: Job dependency information
        :rtype: str


    .. py:attribute:: email_user

        User to email job notifications to if set.  If no email address was supplied, then returns an empty
        string.

        .. note::

            If no email address was specified, `Openlava <http://www.openlava.org/>`_ may still email the
            owner of the job if so configured.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.email_user
            u''

        :return: User email address, may be ""
        :rtype: str

    .. py:attribute:: end_time

        Time the job ended in seconds since epoch UTC.  If the job has not yet finished, then end_time will be 0.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.end_time
            0

        :return: Number of seconds since epoch (UTC) when the job exited.
        :rtype: int

    .. py:attribute:: error_file_name

        Path to the job error file, may be empty if none was specified.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.error_file_name
            u'/dev/null'

        :returns: Path of the job error file.
        :rtype: str

    .. py:attribute:: execution_hosts

        List of hosts that job is running on, if the job is neither finished nor executing then the list will be empty

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.execution_hosts
            [master:1]

        :returns:
            List of :py:class:`olwclient.ExecutionHost` objects, one for each host the job
            is executing on.

        :rtype: list

    .. py:attribute:: input_file_name

        Path to the job input file, may be ""

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.input_file_name
            u'/dev/null'

        :returns: Path of the job input file.
        :rtype: str

    .. py:attribute:: is_completed

        True if the job completed without failure.  For this to be true, the job must have returned exit status zero,
        must not have been killed by the user or an admin.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.is_completed
            True

        :return: True if job has completed without error.
        :rtype: bool

    .. py:attribute:: was_killed

        True if the job was killed by the owner or an admin.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.is_running
            False
            >>> job.is_completed
            False
            >>> job.is_pending
            True
            >>> job.was_killed
            False
            >>> job.is_failed
            False
            >>> job.is_suspended
            False

        :return: True if the job was killed
        :rtype: bool

    .. py:attribute:: is_failed

        True if the exited due to failure.  For this to be true, the job must have returned a non zero exit status, and
        must not have been killed by the user or admin.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.is_running
            False
            >>> job.is_completed
            False
            >>> job.is_pending
            True
            >>> job.was_killed
            False
            >>> job.is_failed
            False
            >>> job.is_suspended
            False

        :return: True if the job failed
        :rtype: bool

    .. py:attribute:: is_pending

        True if the job is pending.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.is_running
            False
            >>> job.is_completed
            False
            >>> job.is_pending
            True
            >>> job.was_killed
            False
            >>> job.is_failed
            False
            >>> job.is_suspended
            False

        :return: True if the job is pending
        :rtype: bool

    .. py:attribute:: is_running

        True if the job is running.  For this to be true, the job must currently be executing on compute nodes and the
        job must not be suspended.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.is_running
            False
            >>> job.is_completed
            False
            >>> job.is_pending
            True
            >>> job.was_killed
            False
            >>> job.is_failed
            False
            >>> job.is_suspended
            False

        :return: True if the job is executing
        :rtype: bool

    .. py:attribute:: is_suspended

        True if the job is suspended.  For this to be true, the job must have been suspended by the system, an
        administrator or the job owner.  The job may have been suspended whilst executing, or whilst in a pending state.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.is_running
            False
            >>> job.is_completed
            False
            >>> job.is_pending
            True
            >>> job.was_killed
            False
            >>> job.is_failed
            False
            >>> job.is_suspended
            False

        :return: True if the job is suspended
        :rtype: bool

    .. py:attribute:: max_requested_slots

        The maximum number of slots that this job will execute on.  If the user requested a range of slots to consume,
        this is set to the upper bound of that range.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.max_requested_slots
            1

        :return: Maximum number of slots requested
        :rtype: int

    .. py:attribute:: name

        The name given to the job by the user or scheduling system. May be "".  If this is an array job, then the
        job name will contain the array information.  Generally if no name was specified, then the name will be set
        to the command that was specified.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.name
            u'sleep 100'

        :return: Name of job
        :rtype: str


    .. py:attribute:: options

        Job options control the behavior of the job and specify additional scheduling criteria being used to
        schedule and execute the job.  They may have been explicitly set by the user, or the scheduler.

        Job options is list containing :py:class:`olwclient.JobOption`

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.options
            [SUB_QUEUE, SUB_PROJECT_NAME, SUB_OUT_FILE]

        :return: List of :py:class:`olwclient.JobOption`
        :rtype: List


    .. py:attribute:: output_file_name

        Path to the job output file, may be "" if the job output is not being directed to a file.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.output_file_name
            u'/dev/null'

        :returns: Path of the job output file.
        :rtype: str

    .. py:attribute:: pending_reasons

        Text string explaining why the job is pending.  These are the human readable reasons that
        the scheduler has for not executing the job at present.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.pending_reasons
            u' The job was suspended by the user while pending: 1 host;'

        :return: Reason why the job is pending.
        :rtype: str

    .. py:attribute:: predicted_start_time

        The time the job is predicted to start, in seconds since EPOCH. (UTC)  If the expected start time is not
        available then returns zero.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.predicted_start_time
            0

        :return: The predicted start time
        :rtype: int

    .. py:attribute:: priority

        The priority given to the job by the user, this may have been modified by the scheduling environment, or an
        administrator.  If no priority was given, then returns -1.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.priority
            -1

        :return: Priority
        :rtype: int

    .. py:attribute:: process_id

        The numeric process ID of the primary process associated with this job.  If the job does not have a process id
        then returns -1.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.is_pending
            True
            >>> job.process_id
            -1
            >>> job.is_running
            True
            >>> job.process_id
            25148

        :return: Process ID
        :rtype: int

    .. py:attribute:: processes

        Array of process objects for each process started by the job.  This only includes processes that Openlava
        is aware of, processes that are started independently of `Openlava <http://www.openlava.org/>`_ will
        not be included. Generally this only includes the primary process on the primary host and any child processes.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.processes
            [None:16422, None:16422, None:16422]

        :return: Array of :py:class:`cluster.Process` objects
        :rtype: list

    .. py:attribute:: project_names

        Array of project names that the job was submitted with.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.project_names
            [u'default']

        :return: Project Names
        :rtype: list of str


    .. py:attribute:: requested_resources

        Resource string requested by the user.  This may be have been modified by the scheduler, or an administrator.
        If no resources were requested, returns an empty string.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.requested_resources
            u''

        :return: Resource Requirements
        :rtype: str

    .. py:attribute:: requested_slots

        The number of job slots requested by the job.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.requested_slots
            1

        :return: Slots requested
        :rtype: int

    .. py:attribute:: reservation_time

        The time when the slots for this job were reserved.  Time is in seconds since Epoch (UTC).  If the slots were
        not reserved, then returns zero.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.reservation_time
            0

        :return: Time when slots were reserved.
        :rtype: int

    .. py:attribute:: runtime_limits

        Array of run time limits imposed on the job.  May have been modified by the scheduler or an administrator.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.runtime_limits
            [CPU Time:-1 (-1), File Size:-1 (-1), Data Segment Size:-1 (-1), Stack Size:-1 (-1),
            Core Size:-1 (-1), RSS Size:-1 (-1), Num Files:-1 (-1), Max Open Files:-1 (-1), Swap Limit:-1 (-1),
            Run Limit:-1 (-1), Process Limit:-1 (-1)]

        :returns: All applicable :py:class:`olwclient.ResourceLimit` objects for the job.
        :rtype: list of :py:class:`olwclient.ResourceLimit` objects


    .. py:attribute:: start_time

        The time time the job started in seconds since Epoch. (UTC)  If the job has not yet started, returns 0.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.start_time
            1414347750

        :returns: Job Start Time
        :rtype: int

    .. py:attribute:: status

        :py:class:`cluster.openlavacluster.JobStatus` object that defines the current status of the job.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.status
            JOB_STAT_RUN

        :return: Job Status
        :rtype: :py:class:`cluster.openlavacluster.JobStatus`

    .. py:attribute:: submit_time

        The time the job was submitted in seconds since Epoch. (UTC)

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.submit_time
            1414347742

        :returns: Job Submit Time
        :rtype: int

    .. py:attribute:: suspension_reasons

    Text string explaining why the job is suspended.  If the job is not suspended, may return invalid information.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.suspension_reasons
            u' Unknown suspending reason code: 0'

        :return: Reason why the job is suspended.
        :rtype: str

    .. py:attribute:: termination_time

        Termination deadline in seconds since the Epoch. (UTC)  The job will be terminated if it is not finished by
        this time.  If no termination deadline was specified, returns zero.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.termination_time
            0

        :return: Job termination time
        :rtype: int

    .. py:attribute:: user_name

        User name of the job owner.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.user_name
            u'irvined'

        :return: Username
        :rtype: str


    .. py:attribute:: user_priority

        User given priority for the job.  This may have been modified by the scheduling system or an administrator.
        If the user did not specify a priority, then returns -1.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.user_priority
            -1

        :return: priority
        :rtype: int


    .. py:attribute:: requested_hosts

        An array of Host objects corresponding the the hosts that the user requested for this job.  If the user did
        not request any hosts, then the list will be empty.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.requested_hosts
            []

        :return: List of requested hosts
        :rtype: list

    .. py:attribute:: checkpoint_directory

        Path to directory where checkpoint data will be written to.  If no checkpoint directory was specified then
        returns an empty string.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.checkpoint_directory
            u''

        :return: path to checkpoint directory
        :rtype: str

    .. py:attribute:: checkpoint_period

        Number of seconds between checkpoint operations.  If no checkpointing period was specified, then returns 0.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.checkpoint_period
            0

        :return: Number of seconds between checkpoints
        :rtype: int

    .. py:attribute:: cpu_factor

        CPU Factor of execution host.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.cpu_factor
            0.0

        :return: CPU Factor
        :rtype: float

    .. py:attribute:: cwd

        Current Working Directory of the job.  This is a relative path, and may consist of only the basename.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.cwd
            u''

        :return: Current Working Directory
        :rtype: str

    .. py:attribute:: execution_cwd

        Current working directory on the execution host

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.execution_cwd
            u'/home/mytestuser'

        :return: CWD on exec host
        :rtype: str

    .. py:attribute:: execution_home_directory

        The home directory of the user on the execution host.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.execution_home_directory
            u'/home/irvined'

        :return Home Directory
        :rtype: str

    .. py:attribute:: execution_user_id

        User ID of the user used to execute the job on the execution host.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.execution_user_id
            1000

        :return: Numerical ID of the user
        :rtype: int

    .. py:attribute:: execution_user_name

        User name of the user used to execute the job on the execution host.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.execution_user_name
            u'irvined'

        :return: name of the user
        :rtype: str

    .. py:attribute:: host_specification

    A hostname or model name that describes the specification of the host being used to execute the job.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.host_specification
            u'master'

        :return: Host Specification
        :rtype: str

    .. py:attribute:: login_shell

        The shell used when running the job.  If not used, or not specified will return an empty string.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.login_shell
            u''

        :return: Login Shell
        :rtype: str

    .. py:attribute:: parent_group

        The parent Job Group, if not used will be ""

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.parent_group
            u'/'

        :return: Parent Job Group
        :rtype: str

    .. py:attribute:: pre_execution_command

        Pre Execution Command specified by the user, if this is not supplied, will return and empty string.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.pre_execution_command
            u''

        :return: Pre Execution Command
        :rtype: str

    .. py:attribute:: resource_usage_last_update_time

        The time the resource usage information was last updated in seconds since Epoch. (UTC)

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.resource_usage_last_update_time
            1414348649

        :return: resource usage update time
        :rtype: int

    .. py:attribute:: service_port

        NIOS Port of the job

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.service_port
            0

        :return: NIOS Port
        :rtype: int

    .. py:attribute:: submit_home_directory

        Home directory on the submit host of the user used to execute the job

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.submit_home_directory
            u'/home/irvined'

        :return: Home Directory

        :rtype: str

    .. py:attribute:: termination_signal

        Signal to send when job exceeds termination deadline.

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.termination_signal
            0

        :return: Termination Signal
        :rtype: int

    """

    def __repr__(self):
        s = "%s" % self.job_id
        if self.array_index > 0:
            s += "[%s]" % self.array_index
        return s

    def __str__(self):
        return self.__repr__()

    def __unicode__(self):
        return u"%s" % self.__str__()

    @property
    def resource_usage_last_update_time_datetime(self):
        """
        A datetime object set to the time the resource usage information was last updated

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> print job.resource_usage_last_update_time_datetime
            2014-10-17 16:18:53

        :return: last update time of resource usage
        :rtype: datetime

        """
        return datetime.datetime.utcfromtimestamp(self.resource_usage_last_update_time)

    @property
    def submit_time_datetime(self):
        """
        The submit time as a datetime object (UTC)

        :return: submit time
        :rtype: datetime

        """
        return datetime.datetime.utcfromtimestamp(self.submit_time)

    @property
    def queue(self):
        """
        The queue object that this job is currently in.  This may have been modified by the scheduling system, or an
        administrator.

        :return: Queue object that the job is in.
        :rtype: Queue

        """
        return self._queue['name']

    @property
    def submission_host(self):
        """
        :py:class:`olwclient.Host` object corresponding to the host that the job was submitted from.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> job.submission_host
            master

        :return: Submit :py:class:`olwclient.Host` object
        :rtype: :py:class:`cluster.Host`

        """
        return Host(self._connection, host_name=self._submission_host['name'])

    def checkpoint_period_timedelta(self):
        """
        Checkpointing period as a timedelta object

        .. note::

            Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        Example::

            >>> class ConnectionArgs:
            ...  username="mytestuser"
            ...  password="topsecret"
            ...  url="http://example.com/"
            >>> from olwclient import Job, OpenLavaConnection
            >>> c=OpenLavaConnection(ConnectionArgs)
            >>> job=Job.get_job_list(c)[0]
            >>> print job.checkpoint_period_timedelta
            0:00:00

        :return: Checkpointing period
        :rtype: timedelta

        """
        return datetime.timedelta(seconds=self.checkpoint_period)

    def __init__(self, connection, job_id=None, array_index=None, data=None):
        """
        Creates a new instance of the job class.

        :param connection: Connection object to user to get data
        :param data:

            If defined, contains the data as a dictionary from the remote server.  Default: Undefined, used only
            internally.

        :param job_id: Numeric Job ID.
        :param array_index: Array index of the job.

        When job is None (Default) then makes a connection to the openlava server using the connection object, and
        requests information about the job with the specified job_id and array index.  If the job exists, then the
        job is created and returned.  If the job doesnt exist, or there is an error with the API call, an exception
        is raised.

        :raises NoSuchJobError: When the job doesnt exist

        """
        if job_id is not None:
            if array_index is None:
                array_index = 0
            url = connection.url + "/job/%s/%s" % (job_id, array_index)
            req = urllib2.Request(url, None, {'Content-Type': 'application/json'})
            data = connection.open(req)
            if not isinstance(data, dict):
                raise RemoteServerError("Expected a dict from: %s but got a: %s" % (url, type(data)))
            if data['type'] != "Job":
                raise RemoteServerError("Expected a Job object but got a : %s from %s" % (data['type'], url))

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
        self.runtime_limits = [ResourceLimit(self._connection, data=d) for d in self.runtime_limits]

    def kill(self):
        """
        Kills the job.  The user must be a job owner, queue or cluster administrator for this operation to succeed.

        :return: None
        :raise: RemoteServerError on failure
        """
        self._exec_remote("/job/%s/%s/kill" % (self.job_id, self.array_index))

    def resume(self):
        """
        Resumes the job.  The user must be a job owner, queue or cluster administrator for this operation to succeed.

        :return: None
        :raise: RemoteServerError on failure
        """
        self._exec_remote("/job/%s/%s/resume" % (self.job_id, self.array_index))

    def requeue(self, **kwargs):
        """
        Requeues the job.  The user must be a job owner,  queue or cluster administrator for this operation to succeed.

        :param bool hold:

            When true, jobs will be held in the suspended pending state.

            .. note::

                Openlava Only! This property is specific to Openlava and is not generic to all cluster interfaces.

        :return: None
        :raise: RemoteServerError on failure
        """

        q = urllib.urlencode(kwargs)
        if len(q) > 0:
            q = "?%s" % q

        self._exec_remote("/job/%s/%s/requeue%s" % (self.job_id, self.array_index, q))

    def suspend(self):
        """
        Suspends the job.  The user must be a job owner, queue or cluster administrator for this operation to succeed.

        :return: None
        :raise: RemoteServerError on failure
        """
        self._exec_remote("/job/%s/%s/suspend" % (self.job_id, self.array_index))

    @classmethod
    def submit(cls, connection, **kwargs):
        """
        Submits a job into the the remote cluster. Returns an array of Job objects.

        :param connection:  Active Connection object.

        :param options:
            Numeric value to pass to the options of the scheduler.

        :param options2:
            Numeric value to pass to the options2 field of the scheduler.

        :param command:
            The command to execute

        :param requested_hosts
            A string containing the list of hosts separated by a space that the user wishes the job to run on.

        :param max_requested_slots
            Max number of slots to use

        :param queue_name:
            The name of the queue to submit the job into, if none, the default queue is used.

        :param project_name
            Name of project to submit to

        :param job_name:
            The name of the job.  If none, then no name is used.

        :return:

            List of Job objects.  If the job was an array job, then the list will contain multiple elements with the
            same job id, but different array_indexes, if the job was not an array job, then the list will contain only
            a single element.

        """
        connection.login()
        allowed_keys = [
            'options',
            'options2',
            'command',
            'requested_slots',
            'max_requested_slots',
            'queue_name',
            'project_name',
            'job_name',
        ]

        for k in kwargs.keys():
            if k not in allowed_keys:
                raise ValueError("Argument: %s is not valid" % k)
        data = json.dumps(kwargs, sort_keys=True, indent=4)

        url = connection.url + "/job/submit"
        request = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        data = connection.open(request)

        if not isinstance(data, list):
            raise RemoteServerError("Server did not return a list: %s" % url)
        return [Job(connection, data=i) for i in data]

    @classmethod
    def get_job_list(cls, connection, job_id=0, array_index=-1, queue_name=None, host_name=None, user_name="all",
                     job_state="ACT", job_name=None):
        """
        Returns a list of jobs that match the specified criteria.

        :param connection:  Connection object to use to get data

        :param job_id:
            The numeric Job ID, if this is specified, then queue_name, host_name, user_name, and job_state are
            ignored.

        :param array_index:
            The array index of the job.  If array_index is -1, then all array tasks from the corresponding job ID are
            returned.  If array_index is not zero, then a job_id must also be specified.

        :param queue_name:
            The name of the queue.  If specified, implies that job_id and array_index are set to default.  Only returns
            jobs that are submitted into the named queue.

        :param host_name:
            The name of the host.  If specified, implies that job_id and array_index are set to default.  Only returns
            jobs that are executing on the specified host.

        :param user_name:
            The name of the user.  If specified, implies that job_id and array_index are set to default.  Only returns
            jobs that are owned by the specified user.

        :param job_state:
            Only return jobs in this state, state can be "ACT" - all active jobs, "ALL" - All jobs, including finished
            jobs, "EXIT" - Jobs that have exited due to an error or have been killed by the user or an administator,
            "PEND" - Jobs that are in a pending state, "RUN" - Jobs that are currently running, "SUSP" Jobs that are
            currently suspended.

        :param job_name:
            Only return jobs that are named job_name.

        :return: Array of Job objects.
        :rtype: list

        """

        if job_id != 0 and array_index == -1:
            logging.debug("Getting info for elements in job.")
            url = connection.url + "/jobs/%d" % job_id
        else:
            logging.debug("Getting info for all jobs")
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
                if v is None:
                    del (params[k])
            url = connection.url + "/jobs?" + urllib.urlencode(params)
        logging.debug("Sending request")
        request = urllib2.Request(url, None, {'Content-Type': 'application/json'})

        data = connection.open(request)
        if not isinstance(data, list):
            raise RemoteServerError("Expected: %s to return a list of jobs, not: %s" % (url, type(data)))
        return [cls(connection, data=i) for i in data]


__ALL__ = [OpenLavaConnection, RemoteServerError, AuthenticationError, Host, Job, ExecutionHost]
