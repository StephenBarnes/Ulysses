
from os import path

from utilities import parse_category_selector

class Judge():
	"""
	Judges whether or not a request should be forwarded, given its
	classification.
	"""
	def __init__(self, access_level=None):
		ulysses_dir = path.dirname(path.dirname(path.dirname(path.realpath(__file__))))
			# We have to go up from judge.py to gate to src to ulysses, to find the access_rules folder
		self.dirname = path.join(ulysses_dir, 'access_rules')
		if access_level is None:
			access_level = "none"
		self.load_access_rules(access_level)
	def load_access_rules(self, access_level=None):
		self.rules = []
		if access_level is None:
			access_level = self.read_access_level()
		filename = "%s_access.txt" % access_level
		full_name = path.join(self.dirname, filename)
		if not path.exists(full_name):
			raise Exception("Access rules file does not exist: %s" % full_name)
		print "Reading access rules from file '%s'..." % full_name
		with open(full_name, "r") as f:
			for line in f.readlines():
				line = line.strip() # remove trailing newlines (and other trailing/leading whitespace)
				if len(line) == 0:
					continue
				if line[0] == "#":
					continue
				line_elems = line.split('\t')
				self.rules.append(make_access_rule(line_elems))
	def render_judgment(self, categories):
		"""
		Given categories, judge request. Returns (judgment, info) where
		judgment is one of BLOCK, DELAY, ALLOW, and info is either a number of
		seconds (in the case of a DELAY) or None (otherwise).
		"""
		for match_fn, action in self.rules:
			if match_fn(None, categories):
				return action
		print "Error: reached end of access rules file without finding a matching rule. End your access rules files with 'ALLOW\tALL' or 'BLOCK\tALL' or 'DELAY\tALL'. For now, I'll assume you meant to block."
		return ("BLOCK", None)

def make_access_rule(line_elems):
	"""
	Given the elements of an access line, make a tuple (match_fn,
	action), where match_fn is a function from sets of categories to
	(True, False), and action is True (for ALLOW) or False (BLOCK).
	"""
	match_fn = parse_category_selector(line_elems[1])
		# note: this creates a function (handler,categories)->bool BUT handler's don't make sense for judges' match_fns, so we just ignore the handler and pass in None
	action = None
	if line_elems[0] in ("BLOCK", "ALLOW"):
		assert len(line_elems) == 2, "%s lines in access-rules files must have exactly one tab, separating action from category selector. Erroneous line: %s" % (line_elems[0], "<tab>".join(line_elems))
		action = (line_elems[0], None)
	elif line_elems[0] == "DELAY":
		assert len(line_elems) == 3, "DELAY lines in access-rules files must have exactly one tab, separating action from category selector. Erroneous line: %s" % "<tab>".join(line_elems)
		action = ("DELAY", line_elems[2])
	else:
		raise Exception("Error: first word in non-comment access rule must be either ALLOW or BLOCK or DELAY, not %s." % line_elems[0])
	return (match_fn, action)

# Possible later modification: have several judges, and an AggregateJudge, like for classifiers

