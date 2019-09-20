#!/usr/bin/env python

from utilities import *
import configuration


std_comq = CommandQueue()
std_parallel = []
std_delay = \
	{ 'none': Time("1m")
	, 'few': Time("1m")
	, 'some': Time("1m")
	, 'delayed_most': Time("1m")
	, 'most': Time("1m")
	, 'all': Time("1m")
	, 'root': Time("1m")
	, 'wget': Time("1m")
	}
std_wait_access = None
std_time_access = None
std_switched_access = configuration.ACCESS_LEVELS['root']
std_state = SystemState(std_comq, std_parallel, std_delay, std_wait_access, std_time_access, std_switched_access, 0)


std_state.pickle()

