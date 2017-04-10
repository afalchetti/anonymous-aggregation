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

def process(votername, schedule, config):
	"""Compute and print an appropriate message for the server from the user details."""
	
	print(votername)
	print(schedule)

def displayusage():
	"""Print the usage of this command to the command line."""
	
	print(("usage: python {} votername schedule [configfile=config.json]\n\n" +
	       "\tvotername  | voter's username\n" +
	       "\tschedule   | voter's schedule as a bitmap of availability.\n" +
	       "\t             schedule[bit 3] is 1 if the voter can meet at timeslot 3.\n" +
	       "\t             It must encoded as a string of zeros and ones.\n" +
	       "\tconfigfile | scheduler configuration file.").format(__file__), file=sys.stderr)

def main():
	"""Main client entry point."""
	
	# argument parsing and validation
	
	if len(sys.argv) < 3 or len(sys.argv) > 4:
		displayusage()
	
	votername   = sys.argv[1]
	schedule    = sys.argv[2]
	configfname = sys.argv[3] if len(sys.argv) > 3 else "config.json"
	
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

if __name__ == "__main__":
	main()
