#!/usr/bin/env python

import sys

import utilities

import requests

SHOW_ERRORS = True
	# show exception traceback, instead of describing the exception and printing usage
	# set to True when debugging; set to False when thoroughly bug-tested and shipping to end users

def usage():
	s = "Usage: req COMMAND [ARGUMENTS...]\n\n"
	s += "Available commands are:\n\n"
	for ri in requests.request_infos:
		s += "\n" + ri.req_class.name
		if ri.req_class.abbrev is not None:
			s += " (%s)" % ri.req_class.abbrev
		s += ri.req_class.__doc__
	return s


def create_request(request_keyword, arguments, state, show_errors=SHOW_ERRORS):
	"""
	Uses words (eg "wait 30m") to create a request with the given currstate
	and command queue.
	Returns False if something went wrong, else True.
	"""
	try:
		this_request_type = requests.get_request_info(request_keyword)
	except Exception, e:
		print "Error: %s" % e
		print usage()
		return False

	if show_errors:
		request = this_request_type.req_class(arguments, state)
		return True
	else:
		try:
			request = this_request_type.req_class(arguments, state)
				# note that `request` here might not be the request that was added to comq
				# eg "force wait 10m" will return the force request, not the wait request
			return True
		except Exception, e:
			print "Error: %s\n" % e
			print "Usage for request type \"%s\":%s" % \
				(this_request_type.req_class.name, this_request_type.req_class.__doc__)
			return False


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print usage()
		exit(1)

	state = utilities.SystemState()

	if not create_request(sys.argv[1], sys.argv[2:], state):
		exit(1)

	state.pickle()

