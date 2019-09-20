#!/usr/bin/env python
from os import path
import utilities as u

# CONFIGURATION OPTIONS
##################################################

# See further information at brightmakesmight.com/comsys .
# This file isn't intended to be usable if you haven't read that first.




# These are the access-levels; you can add more. There must be one called "root".
# NB: You MUST add these in order from least to most permissive. (Because we need that information to determine some switching-time technicalities, eg to forbid switching from "none root=3h" to "none root=1m" (which takes like 5 minutes) and then to "root" (which would take only 1 minute).)
ACCESS_LEVELS = u.AccessLevelList\
	([	u.AccessLevel\
			(	name = "root"
			,	default_delays = {}
			,	iptables_file = "iptables_allow_all" # we don't force the user to go through the proxy
			,	hosts_file = "hosts_block_destructive"
			#,	hosts_file = "hosts_allow_all"
			,	allow_inandout_from = False
			,	allow_inandout_to = False
			,	is_admin = True
			)
	,	u.AccessLevel\
			(	name = "all"
			,	default_delays = \
					{	"root"	: u.Time("30m")
					}
			,	iptables_file = "iptables_allow_all" # we don't force the user to go through the proxy
			,	hosts_file = "hosts_block_destructive"
			#,	hosts_file = "hosts_allow_all"
				# we don't bother to define the last three fields (allow_inandout_from, allow_inandout_to, is_admin) so they're just set to default values (True, True, False)
			)
	,	u.AccessLevel\
			(	name = "most"
			,	default_delays = \
					{	"root"	: u.Time("1h")
					,	"all"	: u.Time("1h")
					}
			,	iptables_file = "iptables_block_nonproxy"
			,	hosts_file = "hosts_block_destructive"
			#,	hosts_file = "hosts_allow_all"
			)
	#,	u.AccessLevel\
	#		(	name = "delayed_most"
	#		,	default_delays = \
	#				{	"root"	: u.Time("12h")
	#				,	"all"	: u.Time("12h")
	#				,	"most"	: u.Time("1h")
	#				}
	#		,	iptables_file = "iptables_block_nonproxy"
	#		,	hosts_file = "hosts_block_destructive"
	#		)
	,	u.AccessLevel\
			(	name = "some"
			,	default_delays = \
					{	"root"	: u.Time("2h")
					,	"all"	: u.Time("2h")
					,	"most"	: u.Time("1h")
					,	"delayed_most"	: u.Time("1h")
					}
			,	iptables_file = "iptables_block_nonproxy"
			,	hosts_file = "hosts_block_destructive"
			#,	hosts_file = "hosts_allow_all"
			)
	,	u.AccessLevel\
			(	name = "few"
			,	default_delays = \
					{	"root"	: u.Time("3h")
					,	"all"	: u.Time("3h")
					,	"most"	: u.Time("2h")
					,	"delayed_most"	: u.Time("2h")
					,	"some"	: u.Time("1h")
					}
			,	iptables_file = "iptables_block_nonproxy"
			,	hosts_file = "hosts_block_destructive"
			,	allow_timeset_from_nonroot = True
					# NOTE that this allows switching from none-access to few-access in one 
					# minute flat, regardless of none->few delay. I'm okay with that.
			)
	,	u.AccessLevel\
			(	name = "none"
			,	default_delays = \
					{	"root"	: u.Time("4h")
					,	"all"	: u.Time("4h")
					,	"most"	: u.Time("3h")
					,	"delayed_most"	: u.Time("3h")
					,	"some"	: u.Time("2h")
					,	"few"	: u.Time("1h")
					}
			,	iptables_file = "iptables_block_nonproxy"
			,	hosts_file = "hosts_block_destructive"
			,	allow_timeset_from_nonroot = True
			)
	],
	default_default_delay = u.Time("1m")
		# The number of minutes it should take, by default, to switch to another access-level
		# You should override this for switches from lower to higher access-levels, in the DEFAULT_TIMES dict above.
	)
DELAY_KEYS = list(ACCESS_LEVELS.names) + ["wget"]



# Now we specify the default times for switching between access-levels. Anything not specified is assumed to be 5 minutes. (The dictionary maps the current access-level to [a dictionary that maps access-levels you could switch into, to the time it would take to switch to those access-levels. For instance, switching from all to root takes 1 hour.

# I used these defaults over a 3-month break where I had no commitments but wanted to stay productive.
#DEFAULT_TIMES = {
#		"root" : { },
#		"all" : { "root" : "5h" },
#		"some" : { "all" : "1d", "root" : "1d", "wget" : "1h" },
#		"few" : { "all" : "2d", "root" : "2d", "some" : "1d", "wget" : "2h" },
#		"none" : { "few" : "1d", "some" : "2d", "all" : "2d12h", "root" : "2d12h", "wget" : "3h" },
#		}
# these DEFAULT_TIMES are for testing:
#DEFAULT_TIMES = {
#		"root" : { },
#		"all" : { "root" : "1m" },
#		"some" : { "all" : "1m", "root" : "1m", "wget" : "1m" },
#		"few" : { "all" : "1m", "root" : "1m", "some" : "1m", "wget" : "1m" },
#		"none" : { "few" : "1m", "some" : "1m", "all" : "1m", "root" : "1m", "wget" : "1m" },
#		}

JUST_TESTING = True # when this is True, root access will never really be removed from you, and shell commands will not be executed
TESTING_BUT_RETAIN_ROOT = False # When this is True and JUST_TESTING is False, all commands WILL be executed, but root's password will not be randomized, it will just be set to ROOT_PASS_WITH_ACCESS + "-testing", eg "adminpass-testing"

ROOT_PASS_WITH_ACCESS = "adminpass" # the password that the root account will have when you're in the "root" accesslevel. When you're not in the root accesslevel, root has a randomly-generated password that's stored in the read-protected file "precompass.txt".
ROOT_USERNAME = "root" # the name of the user account that has root access; CONTROLLER_DIRECTORY should be somewhere in /home/ROOT_USERNAME

CONTROLLER_DIRECTORY = path.dirname(path.realpath(__file__)) + "/" # The directory this script is being run from. This should belong to root, i.e. you will not have access to it except when you're in root-access.

# We will now specify, for every access-level, the files controlling internet access for that access-level. There are two ways we control this. First, through the "iptables" tool, which can set up packet filter rules in the Linux kernel. Second, through the /etc/hosts file, which is a lookup table for hostnames.
# Which of those two (iptables or /etc/hosts) should you use in which situations?
# Use iptables to:
#	- block websites on a blacklist by blocking their packets
#	- block all packets except those coming from a small whitelist of productive websites
#	- when the website has a specific unchanging IP address. This is the case for most websites, except very large websites like youtube or reddit
# Use /etc/hosts to:
#	- block specific domain names, eg reddit or youtube, by redirecting them to localhost. Iptables is unsuitable for blocking these because they do not have static ip addresses, i.e. you will still be able to access them after you think you've blocked them with iptables.
# In general, I'd say use iptables when you want to use a whitelist, and use /etc/hosts when you want to form a blacklist.
# See my example files for a general sense of how to use them. In my example files, I use only one hosts file for blocking some almost-always-suboptimal websites, eg youtube, and use iptables for whitelisting or blacklisting things according to access-level.
# You could eg make /etc/hosts also do whitelisting by setting up an intercepting proxy like squid.

##IPTABLES_ACCESS_TABLES = {
	#the name of the iptables config file that corresponds to each access-level. These must be stored in CONTROLLER_DIRECTORY/iptables-files. Every access-level must have an entry in this dictionary.
##HOSTS_ACCESS_TABLES = {
	#the name of the /etc/hosts file that corresponds to each access-level. These must be stored in CONTROLLER_DIRECTORY/hosts-files. Every access-level must have an entry in this dictionary.

FORBIDDENLIST = [] #list of strings which, if they appear in a URL, make the "get" command refuse to fetch them
GETEFFECTS = { #dict of strings which, if they appear in a URL, make the "get" command take longer or shorter to fetch them. For instance, an item "reddit.com"->2 means sites containing that string in their URL will take twice as long, or "lesswrong.com"->.5 means lesswrong webpages will take half as long.
	"reddit.com":		2,
	"lesswrong.com":	.2,
	}

ALLOW_INANDOUT = True # Whether to allow "in-and-out" operations. If allowed, you can issue a command like "inandout all", which will switch you to all-access for INANDOUTDURATION and then force you to go back wherever you came from. In exchange for committing to losing all-access after the 30 minutes are up, switching into all-access takes INANDOUTSPEEDUP of what it normally would.
INANDOUTDURATION = 30 # How many minutes you stay in the target state after inandouting into it, before being forced back to where you came from.
INANDOUTSPEEDUP = 2.5 # How much quicker it is to inandout into an access-level, relative to switching into it normally. Eg if it's 2 then you can inandout in half the time it takes to cookswitch normally. You could make this 1.

#############
# ADVANCED CONFIGURATION OPTIONS; you probably won't need to change these

WGET_FLOOR = 5 # the lower limit, in minutes, on wget time. This is to prevent exploits where you can eg switch from "none" to "none wget=0m" (which is bad because it means you can browse any website at only a slight time delay)

ROOT_PASSWORD_WITHOUT_ACCESS_LENGTH = 12 # The length (characters) of the randomly-generated password your root account gets when you lose root access. Generally this should be longer if your precoms are "harder", eg if you go to a remote house where you have no other internet-enabled devices and so are more likely to try to circumvent the system.
# Length 6 can be cracked fairly easily, e.g. in an average of 40 minutes using a multi-threaded `su` brute-forcer.
# Length 12 would take roughly 500,000 hours under the same conditions, so it has a fairly large safety margin.

LOCK_CODE_LENGTH = 16 # The length (characters) of the randomly-generated lock code your requester account gets when you ask for a lock code. (See the blog post for an explanation of what lock codes are. Basically, you get given a code, you use it to encrypt a file you want to keep around but don't want to be able to access for the next while, then you throw away the lock code. Root has a copy of the lock code that you ca't read until you have root access.)

##INANDOUT_FORBIDDEN_LEVELS = set("root") # Set of access-levels that you're not allowed to inandout into. Root should definitely be in this list (because else you could just nullify the "out" part as soon as you're "in"), but you could also add other access-levels here.


##################################################
# END CONFIGURATION OPTIONS

if __name__ == "__main__":
	print "YOU MUST EDIT THIS FILE TO CONFIGURE COMSYS. This is NOT an automatic configuration script."
	exit(1)

