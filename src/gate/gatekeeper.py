
from os import path, system

from ..proxy.proxy_server import AsyncMitmProxy, ProxyHandler
from classifiers import AggregateClassifier
from judge import Judge
from safe_print import s_print, s_log
from time import sleep

from utilities import db

#Some notes of things I'm discovering, as I discover them:
#in GatekeeperHandler:
#	'data' is the plain text of the entire request
#	'self' is of course a subclass of ProxyHandler, which is a subclass of BaseHTTPRequestHandler, thus:
#		self has all of the useful stuff listed at https://docs.python.org/3.3/library/http.server.html#http.server.BaseHTTPRequestHandler
#		self.path contains request path
#		self.headers contains all headers
#			eg self.headers['Host'] is the host
#			self.headers is of type HTTPMessage
#				which has structure defined at https://docs.python.org/3/library/email.message.html#email.message.Message
#					(yes, really, it's based on an email class - horrible design)
#					look at that page, it lists all the methods
#			you can add a header by doing self.headers['foo']='bar', etc.
#		self.server gives access to the AsyncMitmProxy, though that probably won't be useful


CLASSIFIER = AggregateClassifier()
class GatekeeperHandler(ProxyHandler):
	"""
	Uses classifiers and judges to modify HTTP requests before they are
	passed on (to the browser or to the web).
	"""
	judge = Judge()
	update_filename = path.join(path.dirname(path.dirname(path.realpath(__file__))), 'precommitment', 'has_changed')
	print "\nReady to start processing requests.\n"

	def mitm_request(self, data):
		"""Modifies requests."""

		# NOTE we always allow requests through -- we only categorize and judge responses
		# this could be changed

		url = self.headers['Host'] + self.path
		trimmed_url = trim_to(url, 40)

		log_request(url, self.command)

		s_print('>> to: %s' % trimmed_url)

		# check for updates
		if path.isfile(self.update_filename):
			new_access_level = open(self.update_filename, "r").read().strip()
			system("rm -f " + self.update_filename)
			s_print("\n\nUPDATING ACCESS LEVEL: %s\n" % new_access_level)
			self.judge.load_access_rules(new_access_level)
			global CLASSIFIER
			CLASSIFIER.reload() # throw away old classifier, create a new one (because e.g. maybe we added a temporarily_blocked entry)

		return data

	def mitm_response(self, data):
		"""Modifies responses."""

		url = self.headers['Host'] + self.path
		trimmed_url = trim_to(url, 40)

		s_print('<< judging: %s' % trimmed_url)

		global CLASSIFIER
		categories = CLASSIFIER.classify(self, data)
		judgment, info = self.judge.render_judgment(categories)

		log_response(url, categories, judgment, info, self.command)

		s_print("<< %s\nJudged:\t%s => %s (%s)\n" % (trimmed_url, categories, judgment, info))

		if judgment == "BLOCK":
			return refuse(categories, info)
		elif judgment == "DELAY":
			sleep(float(info))
			return data
		elif judgment == "ALLOW":
			return data
		else:
			raise Exception("Unrecognized judgment: %s (%s)" % (judgment, info))

def refuse(categories, info):
	return """HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8

Blocked: %s %s""" % (tuple(categories), info if info else '')

def log_request(url, command):
	sql =	( "INSERT INTO UlyssesRequests "
		+ "(date, url, command) "
		+ "values (%r, %r, %r);"
		)
	args =	( db.curr_time_str()
		, url
		, command
		)
	s_log(sql % args)

def log_response(url, categories, judgment, info, command):
	sql =	( "INSERT INTO UlyssesResponses "
		+ "(date, url, categories, judgment, info, command) "
		+ "values (%r, %r, %r, %r, %s, %r);"
		)
	args =	( db.curr_time_str()
		, url
		, ','.join(categories)
		, judgment
		, repr(info) if info is not None else 'NULL'
		, command
		)
	s_log(sql % args)

def trim_to(s, width):
	"""
	Trims given string `s` to maximum width of `width`, by either
	leaving as-is or cutting and appending "...".
	"""
	if len(s) > width:
		return s[:width-3] + "..."
	return s
