#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 
# Copyright (C) 2017 Angelo Falchetti
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The names of its contributors may not be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import os
import json
import binascii
import hashlib

def hashdigest(message, salt):
	""" Compute the hexadecimal digest of a message using the SHA256 algorithm."""
	
	processor = hashlib.sha256()
	
	processor.update(salt.encode("utf8"))
	processor.update(message.encode("utf8"))
	
	return processor.hexdigest()

def parseticket(ticket, salt, config):
	"""Parse and validate an update ticket."""
	
	components = ticket.split("-")
	
	if len(components) != 2:
		raise FormatError("Tickets must be of the form 'randomprefix-oldschedule'.")
	
	prefix      = components[0]
	oldschedule = components[1]
	
	if len(oldschedule) != config["schedulesize"]:
		raise FormatError("The 'schedule' section of the ticket " +
		                  "must have length {}.".format(config["schedulesize"]))
		
	
	if any([x != '0' and x != '1' for x in oldschedule]):
		raise FormatError("The 'schedule' section of the ticket " +
		                  "must only contain 0 and 1 characters.")
	
	tickethash = hashdigest(ticket, salt)
	
	return prefix, oldschedule, tickethash

def process(votername, schedule, ticket, config):
	"""Add a user vote to the aggregate."""
	
	statefname = os.path.join("server", "private", "state")
	
	# persistent state loading ---------
	# create file if it doesn't exist
	with open(statefname, "a") as statefile:
		pass
	
	with open(statefname, "r") as statefile:
		data = statefile.read()
		
		if len(data) == 0:
			data = "{}"
		
		state = json.loads(data)
	
	# ----------------------------------
	
	# first run
	if not "votes" in state:
		state["votes"] = {}
	
	if not "tally" in state:
		state["tally"] = [0 for i in range(config["schedulesize"])]
	
	# ticket hash computation
	if votername in state["votes"]:
		salt = state["votes"][votername]["salt"]
	else:
		salt = binascii.b2a_base64(os.urandom(32)).decode().strip('\n=')
	
	try:
		prefix, oldschedule, tickethash = parseticket(ticket, salt, config)
	except FormatError as e:
		print("Incorrect ticket format.", file=sys.stderr)
		print(e, file=sys.stderr)
		return
	
	# actual voting
	if not votername in state["votes"]:
		if oldschedule != schedule:
			print("First time voter: invalid ticket, uses different schedule", file=sys.stderr)
			return
		
		state["votes"][votername] = {
			"hash": tickethash,
			"salt": salt
		}
		
		# update tally
		for i in range(config["schedulesize"]):
			state["tally"][i] += ord(schedule[i]) - ord('0')
		
	# avoiding duplicates by removing old vote (and warning) when the user has already voted
	else:
		print("voter {} already voted, chaging their vote".format(votername), file=sys.stderr)
		
		if tickethash != state["votes"][votername]["hash"]:
			print("Incorrect update ticket. Operation denied.", file=sys.stderr)
			return
		
		newhash = hashdigest(prefix + "-" + schedule, salt)
		diff    = [ord(schedule[i]) - ord(oldschedule[i]) for i in range(config["schedulesize"])]
		
		state["votes"][votername]["hash"] = newhash
		
		# update tally with diff
		for i in range(config["schedulesize"]):
			state["tally"][i] += diff[i]
	
	# persistent state dumping ---------
	with open(statefname, "w") as statefile:
		statefile.write(json.dumps(state))
	
	# ----------------------------------
	
	return state

def displayusage():
	"""Print the usage of this command to the command line."""
	
	print(("usage: python {} votername schedule ticket [configfile=config.json]\n\n" +
	       "\tvotername  | voter's username\n" +
	       "\tschedule   | voter's schedule as a bitmap of availability,\n" +
	       "\t             i.e. schedule[bit 3] is 1 if the voter can meet\n" +
	       "\t             at timeslot 3. It must encoded in base64.\n" +
	       "\tticket     | update ticket (secret key to prove vote update is valid)\n" +
	       "\tconfigfile | scheduler configuration file.").format(__file__), file=sys.stderr)

def main():
	"""Main server entry point."""
	
	# argument parsing and validation
	
	if len(sys.argv) < 4 or len(sys.argv) > 5:
		displayusage()
		return
	
	votername   = sys.argv[1]
	schedule    = sys.argv[2]
	ticket      = sys.argv[3]
	configfname = sys.argv[4] if len(sys.argv) > 4 else "config.json"
	
	if len(votername) < 1:
		print("The voter's name cannot be empty.", file=sys.stderr)
		displayusage()
		return
	
	try:
		with open(configfname, "r") as configfile:
			configuration = json.loads(configfile.read())
	except IOError:
		print("Can't open configuration file.", file=sys.stderr)
		displayusage()
		return
	
	if len(schedule) != configuration["schedulesize"]:
		print("The schedule is the wrong size,\n" +
		      "schedule len == {} != {} == config len.".format(len(schedule),
		                                                       configuration["schedulesize"]),
		      file=sys.stderr)
		displayusage()
		return
	
	if any([x != '0' and x != '1' for x in schedule]) > 0:
		print("Couldn't decode schedule.", file=sys.stderr)
		displayusage()
		return
	
	# actual server processing
	print("processing vote from {}: {}".format(votername, schedule), file=sys.stderr)
	state = process(votername, schedule, ticket, configuration)
	print("tally: {}".format(state["tally"]), file=sys.stderr)

if __name__ == "__main__":
	main()