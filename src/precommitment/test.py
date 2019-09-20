#!/usr/bin/env python

import unittest
import sys

from configuration import *
from utilities import *

import req
import step


# define a "standard state", which is used for several test
std_comq = []
std_parallel = []
std_delay = {
	'none': Time("5m"),
	'few': Time("5m"),
	'some': Time("5m"),
	'delayed_most': Time("200m"),
	'most': Time("210m"),
	'all': Time("240m"),
	'root': Time("240m"),
	'wget': Time("60m"),
	}
std_wait_access = None
std_time_access = None
std_switched_access = ACCESS_LEVELS['some']
std_state = SystemState(std_comq, std_parallel, std_delay, std_wait_access, std_time_access, std_switched_access, 0)


class PrintMonitor():
	"""
	Replacement for sys.stdout. Logs all lines written to it.
	"""
	def __init__(self):
		self.lines = []
	def write(self, s):
		self.lines.append(s)
	def get(self):
		"Get strings written, formatted correctly into lines, and clear."
		R = ''.join(self.lines).split('\n')[:-1]
			# this contortion is needed because eg "print 'alpha', 'beta'"
			# calls write("alpha"), write(" "), write("gamma"), write("\n"),
			# and appends "", apparently
		self.clear()
		return R
	def clear(self):
		self.lines = []
old_stdout = sys.stdout
printed = PrintMonitor()
sys.stdout = printed


class TestWait(unittest.TestCase):
	def setUp(self):
		self.state = std_state.copy()
	def test_creation(self):
		req.create_request('wait', ['1h'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 1)
	def test_execution(self):
		req.create_request('wait', ['1h'], self.state, show_errors=False)
		wait_req = self.state.comq[0]
		for istep in xrange(60-1):
			step.step_all(self.state)
			self.assertEqual(self.state.comq, CommandQueue([wait_req]))
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([]))
	def test_multiple_waits(self):
		req.create_request('wait', ['1h'], self.state, show_errors=False)
		req.create_request('wait', ['1h'], self.state, show_errors=False)
		wait_reqs = [self.state.comq[0], self.state.comq[1]]
		# let the first wait request run its course
		for istep in xrange(60-1):
			step.step_all(self.state)
			self.assertEqual(self.state.comq, CommandQueue(wait_reqs))
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([wait_reqs[1]]))
		# let the second wait request run its course
		for istep in xrange(60-1):
			step.step_all(self.state)
			self.assertEqual(self.state.comq, CommandQueue([wait_reqs[1]]))
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([]))
	def test_incorrect_arguments(self):
		self.assertFalse(
				req.create_request('wait', [], self.state, show_errors=False))
		self.assertFalse(
				req.create_request('wait', ['1h', '1h'], self.state, show_errors=False))
		self.assertFalse(
				req.create_request('wait', ['notatimedelta'], self.state, show_errors=False))

class TestSwitchTo(unittest.TestCase):
	def setUp(self):
		self.state = std_state.copy()
	def test_creation(self):
		req.create_request('switchto', ['all'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 1)
	def test_execution(self):
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		req.create_request('switchto', ['all'], self.state, show_errors=False)
		for istep in xrange(240-1):
			step.step_all(self.state)
			self.assertEqual(len(self.state.comq), 1)
			self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([]))
		self.assertEqual(self.state.access, ACCESS_LEVELS['all'])
	def test_multiple_switchtos(self):
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		# create two switchtos
		req.create_request('switchto', ['all'], self.state, show_errors=False)
		req.create_request('switchto', ['some'], self.state, show_errors=False)
		switchto_reqs = [self.state.comq[0], self.state.comq[1]]
		# let the first request run its course
		for istep in xrange(240-1):
			step.step_all(self.state)
			self.assertEqual(len(self.state.comq), 2)
			self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([switchto_reqs[1]]))
		self.assertEqual(self.state.access, ACCESS_LEVELS['all'])
		# let the second request run its course
		for istep in xrange(ACCESS_LEVELS.default_default_delay.minutes - 1):
			step.step_all(self.state)
			self.assertEqual(len(self.state.comq), 1)
			self.assertEqual(self.state.access, ACCESS_LEVELS['all'])
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([]))
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
	def test_incorrect_argument(self):
		self.assertFalse(
				req.create_request('switchto', [], self.state, show_errors=False))
		self.assertFalse(
				req.create_request('switchto', ['not_an_access_level'], self.state, show_errors=False))
		self.assertFalse(
				req.create_request('switchto', ['some', 'what=what'], self.state, show_errors=False))
	def test_shortcuts(self):
		# Switch from 'some all=4h some=5m etc' to 'some all=1h etc', which SHOULD take 3h
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		req.create_request('switchto', ['some', 'all=1h'], self.state, show_errors=False)
		# should take 3h, so we run for just less than that and see if anything happens
		for istep in xrange(180-1):
			step.step_all(self.state)
			assert len(self.state.comq) == 1, "%s" % istep
			self.assertEqual(len(self.state.comq), 1)
		# run once more and check that it's executed correctly
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([]))
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		self.assertEqual(self.state.delay['all'].minutes, 60)
	def test_set_delays(self):
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		req.create_request('switchto',
				['some', 'all=1h', 'most=5h', 'none=1m', 'some=2h'], self.state, show_errors=False)
		# should take 3h, since we're switching to all=1h
		for istep in xrange(180-1):
			step.step_all(self.state)
			assert len(self.state.comq) == 1, "%s" % istep
			self.assertEqual(len(self.state.comq), 1)
		# run once more and check that it's executed correctly
		step.step_all(self.state)
		self.assertEqual(self.state.comq, CommandQueue([]))
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		self.assertEqual(self.state.delay['all'].minutes, 60)
		self.assertEqual(self.state.delay['most'].minutes, 5*60)
		self.assertEqual(self.state.delay['some'].minutes, 120)
		self.assertEqual(self.state.delay['none'].minutes, 1)

class TestRm(unittest.TestCase):
	def setUp(self):
		self.state = std_state.copy()
	def test_simple_rm(self):
		req.create_request('switchto', ['some'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 1)
		req.create_request('rm', ['q', '0'], self.state, show_errors=False)
		self.assertEqual(self.state.comq, CommandQueue([]))
	def test_out_of_bounds_rm(self):
		req.create_request('switchto', ['some'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 1)
		self.assertFalse(
				req.create_request('rm', ['1'], self.state, show_errors=False))
	def test_two_part_rm(self):
		# Create two wait requests
		req.create_request('wait', ['1m'], self.state, show_errors=False)
		req.create_request('wait', ['2m'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 2)
		wait_reqs = [self.state.comq[0], self.state.comq[1]]
		# Remove the second wait
		succeeded = req.create_request('rm', ['q', '1'], self.state, show_errors=False)
		self.assertEqual(self.state.comq, CommandQueue([wait_reqs[0]]))
		# Remove the first wait
		req.create_request('rm', ['q', '0'], self.state, show_errors=False)
		self.assertEqual(self.state.comq, CommandQueue([]))

class TestForcing(unittest.TestCase):
	def setUp(self):
		self.state = std_state.copy()
	def test_forced_wait(self):
		req.create_request('force', ['wait', '1m'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 1)
		self.assertFalse(
				req.create_request('rm', [], self.state, show_errors=False))
		self.assertEqual(len(self.state.comq), 1)
	def test_forced_switchto(self):
		req.create_request('force', ['switchto', 'none'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 1)
		self.assertFalse(
				req.create_request('rm', [], self.state, show_errors=False))
		self.assertEqual(len(self.state.comq), 1)

class TestShow(unittest.TestCase):
	def setUp(self):
		self.state = std_state.copy()
	def test_show(self):
		"Add a variety of requests, and check that we can show them without errors."
		req.create_request('force', ['wait', '1m'], self.state, show_errors=False)
		req.create_request('force', ['switchto', 'some', 'all=5m'], self.state, show_errors=False)
		req.create_request('wait', ['5m'], self.state, show_errors=False)
		req.create_request('switchto', ['some', 'all=5m'], self.state, show_errors=False)
		self.assertEqual(len(self.state.comq), 4)
		self.assertTrue(
				req.create_request('show', [], self.state, show_errors=False))

class TestExecute(unittest.TestCase):
	def setUp(self):
		self.state = std_state.copy()
	def test_basic(self):
		self.assertEqual(self.state.access, ACCESS_LEVELS['some'])
		req.create_request('execute', ['echo'], self.state, show_errors=False)
		for istep in xrange(self.state.delay['root'].minutes - 1):
			step.step_all(self.state)
			self.assertEqual(len(self.state.parallel), 1)
		step.step_all(self.state)
		self.assertEqual(len(self.state.parallel), 0)

class TestRefrsh(unittest.TestCase):
	def setUp(self):
		self.state = std_state.copy()
	def test_basic(self):
		self.assertTrue(req.create_request('refresh', [], self.state, show_errors=False))



if __name__ == "__main__":
	unittest.main()


