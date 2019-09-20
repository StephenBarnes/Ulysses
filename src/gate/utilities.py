
from sys import path
import os
path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_utils as db


def parse_category_selector(selector):

	if selector == "ALL":
		return lambda handler, curr_categories : True

	# Make list of lists of conjucts that are our conditions to be satisfied.
	requisite_category_strings = selector.split(',') # eg ['alpha&beta', 'gamma']
	requisite_category_conjunctions = [s.split('&') for s in requisite_category_strings] # eg [ ['alpha','beta'], ['gamma'] ]
	# this is in disjunctive normal form, except without "not"s


	# Build up match function

	matches_conjunct = lambda conjunct, categories : ((conjunct[0] == "!") and (conjunct[1:] not in categories)) or ((conjunct[0] != "!") and (conjunct in categories))
		# read: "curr_categories matches a conjunct iff (conjunct is NOT in categories and conjunct IS negated ) OR ( conjunct is in categories and conjunct is NOT negated )"

	matches_conjunction = lambda curr_categories, conjunction : all([matches_conjunct(rq, curr_categories) for rq in conjunction])
	    # read: "curr_categories matches conjunction iff every conjunct in the conjunction matches curr_categories"

	match_fn = lambda handler, curr_categories : any([matches_conjunction(curr_categories, rqc) for rqc in requisite_category_conjunctions])
	    # read: "curr_categories matches rule iff curr_categories matches any conjunction"

	return match_fn


