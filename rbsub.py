#!/usr/bin/env python
import json
import urllib2
import cookielib
import argparse
import datetime


class AuthenticationError(Exception):
	pass

class OpenLavaWeb(object):
	def __init__(self, url, username, password):
		self.username=username
		self.password=password
		self.url=url
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
		for c in self._cookies:
			if c.name=='sessionid':
				return True
		return False

	def login(self):
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
		if not self.authenticated:
			self.login()
		return self._open(request)


class OpenLavaObject(object):
	def __init__(self, auth, params=None):
		self._auth=auth
		if params:
			for k,v in params.items():
				setattr(self,k,v)

class OpenLavaNoAuth:
	def __init__(self, **kwargs):
		for k,v in kwargs.items():
			setattr(self,k,v)

class SubmissionHost(OpenLavaNoAuth):
	pass

class Status(OpenLavaNoAuth):
	pass

class Queue(OpenLavaNoAuth):
	pass

class ExecutionHost(OpenLavaNoAuth):
	pass

class Job(OpenLavaObject):
	@classmethod
	def get_jobs(cls,auth, user=None, job_id=None, array_index=None):
		if job_id and array_index:
			return [Job(job_id=job_id, array_index=array_index)]
		elif job_id:
			url=auth.url + "/job/%d?json=1" % job_id
		elif user:
			url=auth.url + "/users/%s/jobs?json=1" % user
		else:
			url=auth.url + '/jobs?json=1'
		req = urllib2.Request(url,None, {'Content-Type': 'application/json'})
		try:
			data=auth.open(req).read()
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


def get_auth(url, username, password):
	return OpenLavaWeb(url=url, username=username, password=password)

def run_bjobs(args):
	auth=get_auth(url=args.url, username=args.username, password=args.password)
	user=args.user
	if user=="all":
		user=None
	jobs=Job.get_jobs(auth, user, args.job_id, args.array_index)
	if len(jobs)>0:
		print "JOBID     USER      STAT     QUEUE      FROM_HOST   EXEC_HOST   JOB_NAME   SUBMIT_TIME"
		for job in jobs:
			print "%d[%d]  %s    %s    %s    %s    %s   %s %s  " % ( job.job_id, job.array_index, job.user_name, job.status.friendly, job.queue.name, job.submission_host.name ," ".join([str(i.name) for i in job.execution_hosts]), job.name, datetime.datetime.fromtimestamp(job.submit_time))
	else:
		print "No Jobs"


parser = argparse.ArgumentParser()

parser.add_argument("url", help="URL of server")
parser.add_argument("--username", help="Username to use when authenticating")
parser.add_argument("--password", help="Password to use when authenticating")
subparsers = parser.add_subparsers(help='sub-command help')
bjobs = subparsers.add_parser('bjobs', help='bjobs help')

bjobs.add_argument("--job_id", type=int, help="Show a specific job")
bjobs.add_argument("--array_index", type=int, help="Show a specific job in an array")
bjobs.add_argument("--user", "-u", type=str, help="Show a specific users jobs")
bjobs.set_defaults(func=run_bjobs)

args = parser.parse_args()
args.func(args)





