
# Utilities for programs that send data to Traxis.

# To import this file:
#from sys import path
#path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) #or whatever
#import db_utils as db



from os import popen, system
import sqlite3 as sq
from datetime import datetime, timedelta
import sys
import time


DB_FILE = "/home/j/Traxis/DATA.db"

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

class WithDBCursor():
	"""
	Opens database, returns cursor for executing SQL, then commits and
	closes database.

	To use this:
	....with WithDBCursor() as cursor:
	........cursor.execute("INSERT INTO etc.")
	"""
	def __enter__(self):
		try:
			self.con = sq.connect(DB_FILE)
			self.cursor = self.con.cursor()
		except Exception as e:
			print("ERROR creating WithDBCursor:", e)
			if self.con:
				self.con.close()
			exit(1)
		return self.cursor # ie after a "with WithDBCursor() as cursor",
				  # "cursor" will be cursor, not a WithDBCursor object

	def __exit__(self, type, value, traceback):
		try:
			if value is None: # if there was no exception
				self.con.commit()
		except Exception as e:
			print("ERROR committing or closing DB connection:", e)
		finally:
			if self.con:
				self.con.close()

def ExecuteOne(command, args):
	with WithDBCursor() as cursor:
		cursor.execute(command, args)

def ExecuteMany(commands_args):
	with WithDBCursor() as cursor:
		for command, args in commands_args:
			cursor.execute(command, args)

def Fetch(command, args=None):
	with WithDBCursor() as cursor:
		if args:
			cursor.execute(command, args)
		else:
			cursor.execute(command)
		fetched_data = cursor.fetchall()
	return fetched_data

def Exists(command, args=()):
	"Check whether there exists a record matching some SELECT statement."
	with WithDBCursor() as cursor:
		cursor.execute(command, args)
		if cursor.fetchone():
			return True
		else:
			return False


class DBWriter():
	"""
	Opens connection to database and provides cursor for executing SQL.
	On close(), commits to database and closes connection.

	Where possible, you should instead use WithDBCursor instead of
	this. DBWriter is only for situations where you need a
	connection that will persist over several functions, and can't
	easily e.g. use a WithDBCursor and just pass the cursor in.
	Motivating example: in my LogEverything plugin for Anki, I only
	have hooks into functions, and I can't do the WithDBCursor thing
	without mangling the source (which would be bad because when
	Anki updates I'd have to update my mangling).

	This must be close()'d after use, though things will *usually*
	go OK even if you don't.
	"""
	def __init__(self):
		try:
			self.con = sq.connect(DB_FILE)
			self.cursor = self.con.cursor()
			self.has_been_closed = False
		except Exception as e:
			print("ERROR creating DBWriter:", e)
			if self.con:
				self.con.close()
			exit(1)
	def close(self):
		if not self.has_been_closed:
			try:
				self.con.commit()
			except Exception as e:
				print("ERROR committing or closing DB connection:", e)
			finally:
				if self.con:
					self.con.close()
				self.has_been_closed = True
	def __del__(self):
		"""
		This is *usually* called as a destructor, though sometimes Python
		doesn't ever call __del__, so you should still close() the object.
		This is not called on "del db_writer".
		"""
		self.close()


def given_time_str(dt):
	return dt.strftime(TIME_FORMAT)

def curr_time_str():
	return given_time_str(datetime.now())

def curr_minute():
	"""
	Useful for e.g. scripts that run every minute to log info to Traxis,
	but only report that data to the user every n minutes.
	"""
	return datetime.now().minute

def parse_time_str(s):
	return time.strptime(s, TIME_FORMAT)

def notify(s):
	print("notifying: %s" % s)
	system("export DISPLAY=:0 && notify-send \"%s\"" % s)

def error_notify(s):
	sys.stderr.write(str(s))
	notify("ERROR: %s" % s)




class DatetimeRun:
	def __init__(self, type, start, end=None, break_length = timedelta(minutes=1, seconds=30)):
		self.type = type
		self.start = start
		self.break_length = break_length
		if end is None:
			end = start
		self.end = end
	def try_add(self, new):
		"""
		Tries to add the new datetime to the end. If it doesn't go on the end,
		implying the end of the run, returns False. Else, if adding works,
		returns True.
		"""
		if (new - self.end) < self.break_length:
			self.end = new
			return True
		else:
			return False
	def split_at_midnight(self):
		"""
		Split the run into a list of runs, none of which span over
		a midnight.
		"""
		if same_day(self.start, self.end):
			return [self]
		else:
			R = []
			R.append(DatetimeRun(self.type, self.start, datetime_ceil(self.start)))
			middle_day = self.start + timedelta(days=1)
			while not same_day(middle_day, self.end):
				R.append(DatetimeRun(self.type, datetime_floor(middle_day), datetime_ceil(middle_day)))
			R.append(DatetimeRun(self.type, datetime_floor(self.end), self.end))
			return R
	def csv_str(self):
		return "%s,%s,%s" % (self.type, self.start.strftime("%Y-%m-%dT%H:%M"), self.end.strftime("%Y-%m-%dT%H:%M"))
	def length(self):
		return self.end - self.start


def same_day(a, b):
	return a.strftime("%Y-%m-%d") == b.strftime("%Y-%m-%d")

def datetime_ceil(d):
	return datetime(d.year, d.month, d.day, 23, 59)

def datetime_floor(d):
	return datetime(d.year, d.month, d.day, 0, 0)

def timedelta_strf(delta, format_str):
	hours = delta.seconds / 3600
	minutes = (delta.seconds % 3600) / 60
	seconds = delta.seconds % 60

	def str_00(x):
		return str(x).rjust(2, '0')
	def rep_time(s, c, x):
		return s.replace("%" + c, str_00(x))

	codes = { 'H' : hours
		, 'M' : minutes
		, 'S' : seconds
		}
	for c, x in codes.items():
		format_str = rep_time(format_str, c, x)
	
	return format_str

