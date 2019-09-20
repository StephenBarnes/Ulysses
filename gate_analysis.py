#!/usr/bin/env python

# this script should NOT be setuid, since it relies on files in malkuth version of Ulysses, which can be modified without root-access

from src.gate.classifiers import AggregateClassifier
from src.gate.judge import Judge
import sys
import src.precommitment.utilities as utilities

def strip_initial(S, start):
	if S.startswith(start):
		return S[len(start):]
	return S

def split_host_path(url):
	url = strip_initial(url, "http://")
	url = strip_initial(url, "https://")
	if "/" not in url:
		return url, ''
	url, slash, path = url.partition("/")
	assert slash == "/", (url, slash, path)
	return url, slash + path


url = sys.argv[1]


class DummyHandler:
	pass
dummy_handler = DummyHandler()
host, path = split_host_path(url)
dummy_handler.headers = {'host' : host, 'path' : path, 'full_url' : host + path}
	# assumes path is already deobfuscated, no "%.."
dummy_handler.path = path
dummy_handler.deobfuscated_path = path
print
print
print "inferred structure:", dummy_handler.headers
classifier = AggregateClassifier()
categories = classifier.classify(dummy_handler, '', verbose=True)
	# assumes there's no data, so no filtering based on text of response
print "categories:", categories
print


if len(sys.argv) == 3:
	access_level_str = sys.argv[2]
else:
	sys.path.append("/home/malkuth/proj/ulysses/src/precommitment")
	precom_state = utilities.SystemState()
	access_level_str = precom_state.access.name
	print "NOTE: this assumes access level is:", precom_state.access


judge = Judge(access_level_str)
judgment, info = judge.render_judgment(categories)
print "judgment:", judgment
print "info:", info


