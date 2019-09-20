#!/usr/bin/env python

# FINALLY: add the license, credits, etc., as per original MITMProxy.

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import urlparse, urlunparse, ParseResult
from SocketServer import ThreadingMixIn
from httplib import HTTPResponse
from ssl import wrap_socket
from socket import socket
from os import path

from cert_auth import CertificateAuthority

class ProxyHandler(BaseHTTPRequestHandler):
	def __init__(self, request, client_address, server):
		self.is_connect = False
		BaseHTTPRequestHandler.__init__(self, request, client_address, server)
	def _connect_to_host(self):
		# Get hostname and port to connect to
		if self.is_connect:
			self.hostname, self.port = self.path.split(':')
		else:
			u = urlparse(self.path)
			if u.scheme != 'http':
				raise Exception('Unknown scheme %s' % repr(u.scheme))
			self.hostname = u.hostname
			self.port = u.port or 80
			self.path = urlunparse(
				ParseResult(
					scheme='',
					netloc='',
					params=u.params,
					path=u.path or '/',
					query=u.query,
					fragment=u.fragment
				)
			)
		# Connect to destination
		self._proxy_sock = socket()
		self._proxy_sock.settimeout(10)
		self._proxy_sock.connect((self.hostname, int(self.port)))
		# Wrap socket if SSL is required
		if self.is_connect:
			self._proxy_sock = wrap_socket(self._proxy_sock)
	def _transition_to_ssl(self):
		self.request = wrap_socket(self.request, server_side=True, certfile=self.server.ca[self.path.split(':')[0]])
	def do_CONNECT(self):
		self.is_connect = True
		try:
			# Connect to destination first
			self._connect_to_host()
			# If successful, let's do this!
			self.send_response(200, 'Connection established')
			self.end_headers()
			#self.request.sendall('%s 200 Connection established\r\n\r\n' % self.request_version)
			self._transition_to_ssl()
		except Exception, e:
			self.send_error(500, str(e))
			return
		# Reload!
		self.setup()
		self.ssl_host = 'https://%s' % self.path
		self.handle_one_request()
	def do_COMMAND(self):
		# Is this an SSL tunnel?
		if not self.is_connect:
			try:
				# Connect to destination
				self._connect_to_host()
			except Exception, e:
				self.send_error(500, str(e))
				return
			# Extract path
		# Build request
		req = '%s %s %s\r\n' % (self.command, self.path, self.request_version)
		# Add headers to the request
		req += '%s\r\n' % self.headers
		# Append message body if present to the request
		if 'Content-Length' in self.headers:
			req += self.rfile.read(int(self.headers['Content-Length']))
		# Send it down the pipe!
		req = self.mitm_request(req)
		if req is None:
			# this means that the handler wants to block it entirely
			return
		self._proxy_sock.sendall(req)
		# Parse response
		h = HTTPResponse(self._proxy_sock)
		h.begin()
		# Get rid of the pesky header
		del h.msg['Transfer-Encoding']
		# Time to relay the message across
		res = '%s %s %s\r\n' % (self.request_version, h.status, h.reason)
		res += '%s\r\n' % h.msg
		res += h.read()
		# Let's close off the remote end
		h.close()
		self._proxy_sock.close()
		# Relay the message
		res = self.mitm_response(res)
		if res is None:
			# this means that the handler wants to block it entirely
			return
		self.request.sendall(res)
	def mitm_request(self, data):
		for p in self.server._req_plugins:
			data = p(self.server, self).do_request(data)
		return data
	def mitm_response(self, data):
		for p in self.server._res_plugins:
			data = p(self.server, self).do_response(data)
		return data
	def __getattr__(self, item):
		if item.startswith('do_'):
			if item != 'do_CONNECT': # added by SAB, not sure if necessary
				return self.do_COMMAND

class InterceptorPlugin(object):
	def __init__(self, server, msg):
		self.server = server
		self.message = msg

class RequestInterceptorPlugin(InterceptorPlugin):
	def do_request(self, data):
		return data

class ResponseInterceptorPlugin(InterceptorPlugin):
	def do_response(self, data):
		return data

class MitmProxy(HTTPServer):
	def __init__(self, server_address=('', 8080), RequestHandlerClass=ProxyHandler, bind_and_activate=True, ca_file=None):
		if ca_file is None:
			ca_file = path.join(path.dirname(path.realpath(__file__)), "ca.pem")
		HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
		self.ca = CertificateAuthority(ca_file)
		self._res_plugins = []
		self._req_plugins = []
	def register_interceptor(self, interceptor_class):
		if not issubclass(interceptor_class, RequestInterceptorPlugin)\
			and not issubclass(ResponseInterceptorPlugin):
			raise Exception('Registered interceptor must be subclass of either'\
				+ 'RequestInterceptorPlugin or ResponseInterceptorPlugin, or both.'\
				+ ' Argument\'s type was: %s.' % type(interceptor_class))
		if issubclass(interceptor_class, RequestInterceptorPlugin):
			self._req_plugins.append(interceptor_class)
		if issubclass(interceptor_class, ResponseInterceptorPlugin):
			self._res_plugins.append(interceptor_class)

class AsyncMitmProxy(ThreadingMixIn, MitmProxy):
	pass

