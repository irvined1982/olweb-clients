#!/usr/bin/env python
import json
import urllib2
import cookielib
import argparse
import datetime


class AuthenticationError(Exception):
	"""Raised when the client is unable to authenticate to the server"""
	pass






class OpenLavaConnection(object):
	"""Connection and authentication handler for dealing with the server"""

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
		self.username=args.username
		self.password=args.password
		self.url=args.url
		self.url=self.url.rstrip("/")

		self._cookies = cookielib.LWPCookieJar()
		handlers = [
				urllib2.HTTPHandler(),
				urllib2.HTTPSHandler(),
				urllib2.HTTPCookieProcessor(self._cookies)
				]
		self._opener = urllib2.build_opener(*handlers)
		
	@property
	def authenticated(self):
		"""True if the connection is currently authenticated"""
		for c in self._cookies:
			if c.name=='sessionid':
				return True
		return False

	def login(self):
		"""Logs the user into the server"""
		data={
				'username':self.username,
				'password':self.password,
				}
		data=json.dumps(data)
		url=self.url + "/accounts/ajax_login"
		req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
		f=self._open(req)
		f = urllib2.urlopen(req)
		data= json.loads(f.read())
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
	def __init__(self, auth, params=None):
		self._auth=auth
		if params:
			for k,v in params.items():
				setattr(self,k,v)

class Job(OpenLavaObject):
	@classmethod
	def get_jobs(cls, conn, user=None, job_id=None, array_index=None):
		if job_id and array_index:
			return [Job(job_id=job_id, array_index=array_index)]
		elif job_id:
			url=conn.url + "/job/%d?json=1" % job_id
		elif user:
			url=conn.url + "/users/%s/jobs?json=1" % user
		else:
			url=conn.url + '/jobs?json=1'
		req = urllib2.Request(url,None, {'Content-Type': 'application/json'})
		try:
			data=conn.open(req).read()
			data=json.loads(data)
			if isinstance(data, dict):
				data=[data]

		except urllib2.HTTPError as e:
			if e.code==404:
				raise ValueError("No such job ID: %d[%d]" % ( job_id, array_index ))
			else:
				raise
		return [Job(auth=auth, params=i) for i in data]



	def __init__(self,auth, params=None, job_id=None, array_index=None):
		OpenLavaObject.__init__(self, auth, params)
		if params:
			pass
		elif job_id:
			url = self._auth.url + "/job/%d/%d?json=1" % (job_id, array_index)
			req = urllib2.Request(url,None, {'Content-Type': 'application/json'})
			try:
				data=self._auth.open(req).read()
				data=json.loads(data)
				for k,v in data.items():
					setattr(self,k,v)
			except urllib2.HTTPError as e:
				if e.code==404:
					raise ValueError("No such job ID: %d[%d]" % ( job_id, array_index ))
				else:
					raise
		else:
			raise ValueError("No parameters or job id")

		self.execution_hosts=[ExecutionHost(**i) for i in self.execution_hosts]
		self.status=Status(**self.status)
		self.submission_host=SubmissionHost(**self.submission_host)
		self.queue=Queue(**self.queue)

