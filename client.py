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
import random
import json
import binascii

def process(votername, schedule, config):
	"""Compute and print an appropriate message for the server from the user details."""
	
	userdir     = os.path.join("client", "private", votername)
	ticketfname = os.path.join(userdir, "ticket")
	
	os.makedirs(userdir, exist_ok=True)
	
	# ticket format: random 32 bits prefix + last schedule (to be able to validate diff)
	try:
		with open(ticketfname, "r") as ticketfile:
			ticket = json.loads(ticketfile.read())
		
		newticket = ticket.split("-")[0] + "-" + schedule
		
	except FileNotFoundError:
		newticket  = binascii.b2a_base64(os.urandom(32)).decode().strip('\n=')
		newticket += "-" + schedule
		ticket     = newticket
	
	with open(ticketfname, "w") as ticketfile:
		ticketfile.write(json.dumps(newticket))
	
	print(votername)
	print(schedule)
	print(ticket)

def displayusage():
	"""Print the usage of this command to the command line."""
	
	print(("Usage:\n" +
	       "\tpython {} vote votername schedule [configfile=config.json]\n" +
	       "\tpython {} response votername message [configfile=config.json]\n\n" +
	       "\t'vote'     | initiate a vote\n" +
	       "\t'response' | process server response\n" +
	       "\tvotername  | voter's username\n" +
	       "\tschedule   | voter's schedule as a bitmap of availability.\n" +
	       "\t             schedule[bit 3] is 1 if the voter can meet at timeslot 3.\n" +
	       "\t             It must encoded as a string of zeros and ones.\n" +
	       "\message     | content of server response\n" +
	       "\tconfigfile | scheduler configuration file.").format(__file__), file=sys.stderr)

def main():
	"""Main client entry point."""
	
	# argument parsing and validation
	
	if len(sys.argv) < 4 or len(sys.argv) > 5:
		displayusage()
		return
	
	mode        = sys.argv[1]
	votername   = sys.argv[2]
	schedule    = sys.argv[3]
	message     = sys.argv[3]
	configfname = sys.argv[4] if len(sys.argv) > 4 else "config.json"
	
	if len(votername) < 1:
		print("The voter's name cannot be empty.", file=sys.stderr)
		displayusage()
		return
	
	try:
		with open(configfname) as configfile:
			configuration = json.loads(configfile.read())
	except IOError:
		print("Can't open configuration file.", file=sys.stderr)
		displayusage()
		return
	
	if mode == "vote":
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
		
		# actual processing of the vote
		print("sending vote as {}: {}".format(votername, schedule), file=sys.stderr)
		process(votername, schedule, configuration)
		
	elif mode == "response":
		# actual processing of the server response
		ticket = message
		ticketfname = os.path.join("client", "private", votername, "ticket")
		with open(ticketfname, "w") as ticketfile:
			ticketfile.write(json.dumps(ticket))
		
	else:
		print("Unrecognize mode: {}".format(mode))
		displayusage()

if __name__ == "__main__":
	main()
