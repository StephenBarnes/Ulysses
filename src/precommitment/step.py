#!/usr/bin/env python

import utilities


def step_all(state):
	for queued_req in state.comq:
		queued_req.step(state)
	for parallel_req in state.parallel:
		parallel_req.step_initialize(state)
	for parallel_req in state.parallel:
		parallel_req.step(state)


if __name__ == "__main__":

	state = utilities.SystemState()

	state.time_in_level.increment()

	step_all(state)

	state.pickle()

