#!/usr/bin/env python

from time import ctime
import string
import os
import fcntl
from random import randint
import pickle
from copy import copy
from functools import total_ordering

from sys import path
path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_utils as db


class AccessLevelList(object):
	def __init__(self, levels, default_default_delay):
		for power, level in enumerate(reversed(levels)): # reverse so root gets highest index
			level.set_power(power)
		self.levels_list = levels
		self.levels_dict = { level.name : level for level in levels }
		self.names = [level.name for level in levels]
		self.default_default_delay = default_default_delay
	def __getitem__(self, name):
		return self.levels_dict[name]
	def delay(self, from_level, to_level):
		if to_level in from_level.default_delays:
			return from_level.default_delays[to_level]
		else:
			return self.default_default_delay
	def each_higher_than(self, level):
		for higher_level in self.levels_list:
			if higher_level.power > level.power:
				yield higher_level.name

@total_ordering
class AccessLevel(object):
	def __init__	( self
			, name = None
			, default_delays = {}
			, iptables_file = None
			, hosts_file = None
			, allow_inandout_from = True
			, allow_inandout_to = True
			, is_admin = False
			, allow_timeset_from_nonroot=False
			):
		self.name = name
		self.default_delays = default_delays
		self.iptables_file = iptables_file
		self.hosts_file = hosts_file
		self.allow_inandout_from = allow_inandout_from
		self.allow_inandout_to = allow_inandout_to
		self.is_admin = is_admin
		self.allow_timeset_from_nonroot = allow_timeset_from_nonroot
	def set_power(self, power):
		self.power = power
	def __ge__(self, other):
		return self.power >= other.power

	def __repr__(self):
		return "AccessLevel('%s')" % self.name

	def activate_restriction_systems(self):
		execute("sudo iptables-restore <" + configuration.CONTROLLER_DIRECTORY + "iptables-files/" + self.iptables_file)
		execute("sudo cp -f " + configuration.CONTROLLER_DIRECTORY + "hosts-files/" + self.hosts_file + " /etc/hosts")
		# Force-reload the DNS cache
		execute("sudo service dnsmasq force-reload")
		# Create file to signal to Ulysses that state has changed.
		execute("echo " + self.name + " >" + configuration.CONTROLLER_DIRECTORY + "has_changed")

def remove_root_access():
	"""Removes root access from the decommed user, by changing root's password to a randomly-generated string. Stores this password in a file called precompass.txt."""
	newpass = None
	if configuration.TESTING_BUT_RETAIN_ROOT:
		newpass = configuration.ROOT_PASS_WITH_ACCESS + "-testing"
	else:
		newpass = (configuration.ROOT_PASS_WITH_ACCESS if configuration.JUST_TESTING else generate_random_digits(configuration.ROOT_PASSWORD_WITHOUT_ACCESS_LENGTH))
	execute("echo " + str(newpass) + " >>" + configuration.CONTROLLER_DIRECTORY + "precompass.txt", hidden=True) #store it just in case something goes wrong
	execute("sudo chmod go-r " + configuration.CONTROLLER_DIRECTORY + "precompass.txt") #prevent user from reading it
	execute("echo \"" + configuration.ROOT_USERNAME + ":" + str(newpass) + "\" | sudo chpasswd", hidden=True)
	execute("chmod ugo-x /usr/games/steam") # TODO
	print "REMOVED ROOT ACCESS"

def restore_root_access():
	"""Gives root access back to the decommed user, by changing root's password to configuration.ROOT_PASS_WITH_ACCESS."""
	execute("echo \"" + configuration.ROOT_USERNAME + ":" + configuration.ROOT_PASS_WITH_ACCESS + "\" | sudo chpasswd")
	print "GAVE BACK ROOT ACCESS"
	execute("chmod ugo+x /usr/games/steam") # TODO
	# note that we still keep the old precompass around


@total_ordering
class Time(object):
	denominations = (("m", 1), ("h", 60), ("d", 24))
		# the units in which time is denominated, together with the number each is of the previous denomination (i.e. days are 24 hours, hours are 60 minutes)
	def __init__(self, repr=None, minutes=None):
		if repr is None and minutes is None:
			raise Exception('Time object initialized without arguments.')
		if minutes is not None:
			self.minutes = minutes
		else:
			self.minutes = self.from_repr(repr)
	def from_repr(self, repr):
		if repr.isdigit():
			return int(repr)
		else:
			numofeachdenom = {}
			r = 0 # starting value
			for denomsymbol, denommult in reversed(self.denominations + (("D", 1),)): # allow D to also be read as days
				loc = repr.find(denomsymbol)
				if loc != -1:
					try:
						r += int(repr[:loc])
					except:
						raise Exception("Could not convert time to integer number of "\
							"minutes. Times should be specified e.g. '2h', or '1h30m'"\
							", or '15m'.")
					repr = repr[loc+1:]
				r *= denommult
			return r
	def __sub__(self, other):
		return Time(minutes = self.minutes - other.minutes)
	def __str__(self):
		assert type(self.minutes) == type(1)
		numofeachdenom = {"m" : self.minutes}
		for i in xrange(len(self.denominations)-1): # while we're able to: group together smaller units into bigger clumps, e.g. group 130 minutes into 2 hours and 10 minutes
			numofeachdenom[self.denominations[i+1][0]], numofeachdenom[self.denominations[i][0]] = divmod(numofeachdenom[self.denominations[i][0]], self.denominations[i+1][1])
		# now we string together the number of each denomination with its symbol; we're allowed to drop large units (eg hours) if there are no larger units (eg days) that are present
		R = ""
		forceshow = False
		for denom in reversed(self.denominations):
			if forceshow:
				R += str(numofeachdenom[denom[0]]).rjust(2,"0") + denom[0]
			elif numofeachdenom[denom[0]]:
				forceshow = True
				R += str(numofeachdenom[denom[0]]) + denom[0]
		return ("0m" if (R == "") else R)
	def __repr__(self):
		return "Time('%s')" % str(self)
	def increment(self):
		self.minutes += 1

	# We define only __eq__ and __gt__; the other comparison operators are
	# automatically given by the @total_ordering decorator above
	def __eq__(self, other):
		return type(self) == type(other) \
			and self.minutes == other.minutes
	def __gt__(self, other):
		return self.minutes > other.minutes

	# Define __hash__, so we can put Times in sets
	def __hash__(self):
		return self.minutes


def execute(command, hidden=False):
	"""executes the command through os.system, except if we're JUST_TESTING, in which case just print it."""
	if not configuration.JUST_TESTING:
		print "executing:", ("(hidden)" if hidden else command)
		os.system(command)
	else:
		print "would have executed:", command


def generate_random_digits(L):
	"""Generates a string of L random decimal digits."""
	R = ""
	for i in xrange(L):
	        R += str(randint(0,9))
	return R


def describe_delay(elapsed, required):
	if elapsed == 0:
		return "%s (none elapsed)" % required
	else:
		to_go = required - elapsed
		return "%s (%s of %s)" % \
				( to_go
				, elapsed
				, required
				)

class SystemState(object):
	def __init__(self
			, comq=None	# Command queue
			, parallel=None	# Parallel command queue
			, delay=None	# Delays to switch into various switched_access levels
			, wait_access=None	# Access-level we should be in, according to the waitset requests.
			, time_access=None	# Access-level we should be in, according to the current time;
						# set by eg parallel "timeset" commands
			, switched_access=None	# Access-level we should be in, according to switchings;
						# set by eg "switchto" commands
			, time_in_level=None	# how long we've been in this state
			):
		args = (comq, parallel, delay, time_access, switched_access, time_in_level)
		if all(arg is None for arg in args):
			self.unpickle()
		elif None in args and time_access is not None and wait_access is not None:
				# we allow time_access and wait_access to be None, eg if no "timeset"/"waitset" command is in effect
			raise Exception('Haven\'t implemented unpickling only some args. Why would you even want that? Args: %s' % str(args))
		else:
			self.comq = CommandQueue()
			self.parallel = parallel
			self.delay = delay
			self.wait_access = wait_access
			self.time_access = time_access
			self.switched_access = switched_access
			self.time_in_level = Time("0m")
	def unpickle(self):
		with open(configuration.CONTROLLER_DIRECTORY + "state.pickle", "r") as f:
			self.comq = pickle.load(f)
			self.parallel = pickle.load(f)
			self.delay = pickle.load(f)
			self.wait_access = pickle.load(f)
			self.time_access = pickle.load(f)
			self.switched_access = pickle.load(f)
			self.time_in_level = pickle.load(f)
	def pickle(self):
		with open(configuration.CONTROLLER_DIRECTORY + "state.pickle", "w") as f:
			pickle.dump(self.comq, f)
			pickle.dump(self.parallel, f)
			pickle.dump(self.delay, f)
			pickle.dump(self.wait_access, f)
			pickle.dump(self.time_access, f)
			pickle.dump(self.switched_access, f)
			pickle.dump(self.time_in_level, f)
	def copy(self):
		return SystemState(self.comq[:], self.parallel[:], copy(self.delay), self.wait_access, self.time_access, self.switched_access, self.time_in_level)

	@property
	def access(self):
		"""Get the 'effective' access-level of this state.
		"""
		time_switched_access = (self.time_access if self.time_access is not None else self.switched_access)

		if (self.wait_access is not None) and (self.wait_access < time_switched_access):
			return self.wait_access
		return time_switched_access

	def log(self):
		"Logs this state in Traxis."

		date_str = db.curr_time_str()

		main =	( "INSERT INTO ComsysStates "
			+ "(date, delays, time_in_level, access_level, wait_access, time_access, switched_access) "
			+ "values (?, ?, ?, ?, ?, ?, ?);"
			,	( date_str
				, ','.join(('%s=%s' % (a, self.delay[a]) for a in sorted(self.delay.keys())))
				, self.time_in_level.minutes
				, self.access.name
				, self.wait_access.name if self.wait_access is not None else None
				, self.time_access.name if self.time_access is not None else None
				, self.switched_access.name
				)
			)

		queued_commands_tuples = [com.sql_in_group(date_str, "comq", self) for com in self.comq]

		parallel_commands_tuples = [com.sql_in_group(date_str, "parallel", self) for com in self.parallel]

		to_log = [main] + queued_commands_tuples + parallel_commands_tuples

		if not configuration.JUST_TESTING:
			db.ExecuteMany(to_log)
			# NOTE: this used to exit even when you run the test.py script, ie when it shouldn't have.
			# Only fixed this around 2015-01-31T18:50:00.
			# Before then, you might occasionally see a bunch of bogus database rows in rapid succession.
			# See this query for an example: select * from ComsysStates where date like '2015-01-31T18:%';

	def enact_access(self):
		"""Checks how much internet access this state allows, then enacts that level
		by notifying Ulysses, restoring/removing root access, etc.
		"""
		if not self.access.is_admin:
			remove_root_access()
		else:
			restore_root_access()
		self.access.activate_restriction_systems()


class CommandQueue(object):
	def __init__(self, list=None):
		if list is None:
			self.list = []
		else:
			self.list = list
	def containsRequestType(self, req_type):
		return any(type(item) == req_type for item in self.list)
	def append(self, item):
		self.list.append(item)
	def __iter__(self):
		for item in self.list:
			yield item
	def remove(self, item):
		self.list.remove(item)
	def __getitem__(self, key):
		return self.list[key]
	def __len__(self):
		return len(self.list)
	def __eq__(self, other):
		return type(self) == type(other) \
			and self.list == other.list
	def __bool__(self):
		return bool(self.list)


class Delay(object):
	def __init__(self, length=None):
		self.elapsed = Time("0m")
		assert (type(length) == type(Time("0m"))) \
			or (length is None)
		self.required = length
	@property
	def is_done(self):
		return self.required <= self.elapsed
	def step(self):
		self.elapsed.increment()
	def set_time_required(self, time_required):
		self.required = time_required
	@property
	def to_go(self):
		return self.required - self.elapsed
	def __str__(self):
		if self.elapsed == Time("0m"):
			return "%s (none elapsed)" % self.required
		else:
			return "%s (%s of %s)" % \
					( self.to_go
					, self.elapsed
					, self.required
					)




import configuration
# TODO: should this be at the bottom?


if __name__ == "__main__":
	print "This file is not intended to be executed."
	exit(1)

