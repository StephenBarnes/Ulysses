

# Threadsafe print function.
# From: http://stackoverflow.com/questions/7877850/python-2-7-print-thread-safe?lq=1

# Cheap hack, not the "right" way to do it but gets the job done.
# Doesn't handle print() keyword arguments. Makes output always unbuffered.

from __future__ import print_function
from sys import stdout
from datetime import datetime

def s_print(x):
	stdout.write("%s\n" % x)
	stdout.flush()


def logfile_name():
	time_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
	return "/home/j/Traxis/temp_storage/ulysses/%s" % time_str

def s_log(sql):
	# NOTE not sure whether this is actually threadsafe, I'll have to check...
	with open(logfile_name(), "a") as filehandle:
		try:
			filehandle.write(sql + '\n')
		except Exception as e:
			filehandle.write('Error: %r' % e)
		finally:
			filehandle.flush()

