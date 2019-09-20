
from os import path, walk
import re

from utilities import parse_category_selector

DEBUG = False


class Classifier():
	"""
	Classifies data into categories (which are strings); returns a list
	of categories, or set([]) if no classification could be made.
	"""
	def classify(self, handler, data):
		return []
class UrlClassifier(Classifier):
	"""Classifies URLs."""
	pass
class HTTPClassifier(Classifier):
	"""Classifies HTTP responses and requests, using content, URL, etc."""
	pass


class SubstringClassifier(HTTPClassifier):
	proxy_classes = {"circumvention", "proxy", "found_by_substringclassifier"}
	RULES = {	re.compile(r"glype", re.IGNORECASE) : proxy_classes
		,	re.compile(r"Encrypts the URL of the page you are viewing so that it does not contain the target site in plaintext") : proxy_classes
		,	re.compile(r"free( online)? proxy", re.IGNORECASE) : proxy_classes
		,	re.compile(r"Encrypt URL<.{1,500}Encrypt Page<.{1,500}Allow Cookies<.{1,500}Remove Scripts<.{1,500}Remove Objects<", re.IGNORECASE) : proxy_classes
				# yes, this rule is necessary, because those other 2 rules really do let a lot of proxy sites slip through
		,	re.compile(r'Powered by <a href="http://www.glype.com/">Glype</a>', re.IGNORECASE) : proxy_classes
		,	re.compile(r'mini URL-form') : proxy_classes
		,	re.compile(r"edit-browser.php") : proxy_classes
		,	re.compile(r"surrogafier") : proxy_classes
		}
	# TODO rather read the rules from a text file,
	# and allow adding blocks to that text-file from outside of root-access
	def __init__(self):
		pass
	def reload(self):
		pass
	def classify(self, handler, data, verbose=False):
		R = set()
		for regex, classifications in self.RULES.items():
			if classifications <= R: # if we're already got all those classifications, don't bother trying to match
				continue
			if regex.search(data):
				R.update(classifications)
				if verbose:
					print("apply substring classifier:", regex, classifications)
					print("current classes:", R)
		return R


class ListUrlClassifier(UrlClassifier):
	"""
	Classifies URLs by searching through (given) text file containing
	known classifications.
	Text file should consist of lines with a category, then a tab, then
	a regex. (Not using csv module because .split ALWAYS works here.)
	"""
	def __init__(self):
		self.load_all_url_classifications()
	def reload(self):
		self.load_all_url_classifications()
	def classify(self, handler, data, verbose=False):
		categories = set()
		matchee = handler.headers['host'].lower()
		matchee_after_dot = matchee[matchee.find('.')+1:]
		for match_string, new_categories in self.host_exact_match_rules:
			if (match_string == matchee) \
					or ("www." + match_string == matchee) \
					or (match_string == matchee_after_dot):
						categories.update(new_categories)
						if verbose:
							print("host exact match with string", match_string, "gives new categories:", new_categories)
		for match_fn, new_categories, details in self.match_rules:
			if match_fn(handler, categories):
				categories.update(new_categories)
				if verbose:
					print("match rule", details, "gives new categories:", new_categories)
		for match_fn, new_categories, details in self.classify_rules:
			if match_fn(handler, categories):
				categories.update(new_categories)
				if verbose:
					print("match rule", details, "gives new categories:", new_categories)
		return categories
	def load_all_url_classifications(self):
		ulysses_dir_name = path.dirname(path.dirname(path.dirname(path.realpath(__file__))))
			# We have to go up from classifiers.py into gate into src into ulysses, to find the url_classifications directory
		dirname = path.join(ulysses_dir_name, 'url_classifications')
		if not path.exists(dirname):
			raise Exception('ListUrl\'s directory does not exist: %s' % dirname)
		self.match_rules = []
		self.host_exact_match_rules = []
		self.classify_rules = []
		for root, dirs, files in walk(dirname):
			for filename in files:
				fullname = path.join(root, filename)
				self.load_url_classification_file(fullname)
		print "Loaded %s exact rules for matching hosts to categories." % len(self.host_exact_match_rules)
		print "Loaded %s more rules for matching URLs to categories." % len(self.match_rules)
		print "Loaded %s rules for classifying into categories based on pre-existing categories." % len(self.classify_rules)
	def load_url_classification_file(self, fullname):
		"""
		Reads each line from the given URL classification file, processes it
		into a classification rule, and appends the rule to self.match_rules
		as a tuple (match_fn, action).
		"""
		print "Loading URL classification file '%s'..." % fullname
		with open(fullname, "r") as f:
			for line in f.readlines():
				line = line.strip() # remove trailing and leading whitespace, including trailing newlines
				# Ignore comments and blank lines
				if len(line) == 0:
					continue
				if line[0] == "#":
					continue
				# Process the line into a (match_fn, action) tuple for our match_rules list
				# We ignore errors here, so that eg if user tries a 'block whatever nonexistent_option' he won't shut down the entire system.
				try:
					self.process_url_match(line)
				except Exception as e:
					print("Error processing url match line %r : %r" % (line, e))
	def process_url_match(self, line):
		"""
		Given a line from a URL classification file, produce a tuple
		(match_fn, categories), containing the function that checks whether
		the condition is satisfied, and the list of categories that will be
		given to a message when the condition is satisfied.

		E.g., given the line "stories\t/r/askreddit\tpath", this function
		returns (match_fn,['stories']), where match_fn will test whether
		"/r/askreddit" occurs in its argument's path string.
		"""
		# Get line elements
		line_elems = line.split('\t')
		# call either process_regex_rule or process_CLASSIFY
		if line_elems[0] == "CLASSIFY":
			self.process_CLASSIFY(line_elems)
		else:
			self.process_regex_rule(line_elems)
	def process_CLASSIFY(self, line_elems):
		"""
		Processes a classify statement into a (match_fn, action) tuple.
		"""
		assert len(line_elems) == 3, "Error: line is of incorrect format:\n%s\nA CLASSIFY statement must have exactly two tabs, eg CLASSIFY<tab>fanfiction<tab>fiction." % "<tab>".join(line_elems)
		# Make all categories lowercase
		line_elems = [le.lower() for le in line_elems]
		# Get list of new categories
		new_categories = set(line_elems[2].split(','))
		# Get match_fn by parsing the category selector
		match_fn = parse_category_selector(line_elems[1])
		# Make action function
		self.classify_rules.append((match_fn, new_categories, line_elems))
	def process_regex_rule(self, line_elems):
		if len(line_elems) not in (2, 3):
			raise Exception('Each line in URL regex classification file'\
				+ 'must have at least one tab, separating class from'\
				+ 'regex, and at most 2 tabs (if it uses regex options).'\
				+ 'Given line has elements: %s' % line_elems)
		category_str = ''
		matchstring = ''
		options = ''
		if len(line_elems) == 2:
			category_str, matchstring = line_elems
		elif len(line_elems) == 3:
			category_str, matchstring, options = line_elems[:3]
		else:
			raise Exception
		# Make action to apply to categories list
		category_str = category_str.lower() # we always convert all categories to lowercase before using them
		categories = set(category_str.split(','))
		# Make match function and category list to return
		self.make_match_function(matchstring, options, categories)
	def make_match_function(self, matchstring, option_str_list, categories):
		"""
		Given the match string and the option list (respectively, the second
		and third items on a line in url classifications), construct a
		function that will take in a handler, then return whether the
		condition has been satisfied.

		E.g. given ("/r/askreddit","path"), this function returns a function
		that tests whether "/r/askreddit" is in its argument's path string.
		"""
		regex_matchee = "host"
			# where we'll try to match the regex; can be "host", "full_url", or "path"
		match_method = "simple"
			# how we'll try to match
			# "simple": we're to just check whether it's a substring, no regexes required
			# "exact": we check that it's == the matchee, or that "www" + match_string == matchee
				# TODO: make it also match if we can find the first '.' then match after that
			# "regex": we compile it as a regex
		ignore_case = True
			# note that case-insensitivity is default; option "case-sensitive" removes it
		# We process the options string.
		if option_str_list != '':
			options_list = option_str_list.split(',')
			# If it has the "subreddit" option, change the match-string to match that subreddit and add "regex" and "full_url" options
			if options_list == ["subreddit"]:
				matchstring = "^(www.)?reddit.com/r/" + matchstring + "(/.*)?$"
				options_list = ["full_url", "regex"]
			# Process each option
			for option in options_list:
				if option == "case-sensitive":
					assert "regex" in options_list, ("Error: only regex matchstrings can be case-sensitive. "\
							"In other cases, case-sensitivity makes no sense. Offending line has matchstring %s" % matchstring)
					ignore_case = False
				elif option == "full_url":
					not_in(options_list, ["path"])
					regex_matchee = "full_url"
				elif option == "path":
					not_in(options_list, ["full_url"])
					regex_matchee = "path"
				elif option == "regex":
					not_in(options_list, ["exact"])
					match_method = "regex"
				elif option == "exact":
					not_in(options_list, ["regex"])
					match_method = "exact"
				else:
					raise Exception("Unknown option: %s" % option)
		if match_method == "simple":
			assert ignore_case
			matchstring = matchstring.lower()
			self.match_rules.append((
					lambda handler, c: matchee_string(regex_matchee, handler).lower().find(matchstring) != -1,
					categories,
					(matchstring, option_str_list)
					))
		elif match_method == "regex":
			regex_options = set()
			if ignore_case:
				regex_options.add(re.IGNORECASE)
			# Build the regex, using our regex_options
			regex = re.compile(matchstring, *regex_options)
			# Build the function, by searching for the regex in the appropriate string
			self.match_rules.append((
					lambda handler, c: regex.search(matchee_string(regex_matchee, handler)),
					categories,
					(matchstring, option_str_list)))
			# re regexes: .match only tests at the beginning of url; .search tests everywhere
		elif match_method == "exact":
			assert ignore_case
			matchstring = matchstring.lower()
			# if it's an exact host match, add it to our special host_exact_match_rules list, which is faster because we don't pass around functions
			if regex_matchee == "host":
				self.host_exact_match_rules.append((matchstring, categories))
			else:
				self.match_rules.append((
						lambda handler, c: matchee_string(regex_matchee, handler).lower() in (matchstring, "www."+matchstring),
						categories,
						(matchstring, option_str_list)))
		else:
			raise Exception("Unknown match_method %s. This should not be possible." % match_method)

def matchee_string(regex_matchee, handler):
	if regex_matchee == "host":
		return handler.headers['host']
	elif regex_matchee == "path":
		return handler.deobfuscated_path
	elif regex_matchee == "full_url":
		return handler.headers['host'] + handler.deobfuscated_path
	else:
		raise Exception("Unknown regex_matchee %s. This should not be possible." % regex_matchee)


def not_in(L, not_in_L):
	"""
	Asserts that no element of not_in_L is in L.
	"""
	for niL in not_in_L:
		assert niL not in L, "Error: conflicting items in list: %s contains %s" % (L, niL)


class AggregateClassifier(HTTPClassifier):
	list_url_c = ListUrlClassifier()
	substring_classifier = SubstringClassifier()
	cached_classifications = {}
	def cache_key(self, handler):
		return (handler.headers['host'], handler.path)
	def classify(self, handler, data, verbose=False):
		if self.cache_key(handler) not in self.cached_classifications:
			remove_url_obfuscation(handler)
			c = set()
			c.update(self.list_url_c.classify(handler, data, verbose=True))
			c.update(self.substring_classifier.classify(handler, data, verbose=True))
			# EXTENDHERE to take into account more classifiers
			self.cached_classifications[self.cache_key(handler)] = c
		else:
			if DEBUG or verbose: print "(cache hit)"
		return self.cached_classifications[self.cache_key(handler)]
	def reload(self):
		self.list_url_c.reload()
		self.substring_classifier.reload()
		self.cached_classifications = {}

def remove_url_obfuscation(handler):
	"""
	Modify handler.path to prevent obfuscation of characters by replacing them with %-codes, eg replacing 'e' with '%65'.
	Adds a new member `handler.deobfuscated_path`.
	"""
	def code_to_char(code):
		return chr(int(code[1:], 16)) # convert eg '%65' to hex value of 65 (which is 101), then to 'e'
	path = handler.path
	while True:
		code = re.search("%..", path)
		if code is None:
			handler.deobfuscated_path = path # give it a new member 'deobfuscated_path'
			return
		path = path[: code.start()] + code_to_char(code.group(0)) + path[code.end() :]

