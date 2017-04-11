#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# server.py
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
from secretsharing import points_to_secret_int, get_large_enough_prime

def vote(votername, schedule, config):
	"""Add a user vote to the aggregate."""
	
	state = config["state"]
	
	if not "votes" in state:
		state["votes"] = []
	
	if not "messages" in state:
		state["messages"] = {}
	
	if not "decrypting" in state:
		state["decrypting"] = False
	
	if state["decrypting"]:
		print("Decryption process already started, polls are closed", file=sys.stderr)
		return
	
	if votername in [name for (name, vote) in state["votes"]]:
		print("voter {} already voted, changing their vote".format(votername), file=sys.stderr)
	
	state["votes"] = [(name, vote) for (name, vote) in state["votes"] if name != votername]
	sgroups        = schedule.split(";")
	state["votes"].append((votername, sgroups))
	
	for sharegroup in sgroups:
		counter, data = sharegroup.split(">")
		
		if not counter in state["messages"]:
			state["messages"][counter] = {}
		
		state["messages"][counter][votername] = data

def register(votername, publickey, config):
	"""Add a voter to the vote counters."""
	
	state = config["state"]
	
	if not "counterkeys" in state:
		state["counterkeys"] = []
	
	state["counterkeys"].append((votername, publickey))

def parsepoint(point):
	"""Parse and validate string point representation."""
	comps = point.split("-")
	return (int(comps[0]), int(comps[1]))

def decrypt(votername, votesize, share, config):
	"""Receive aggregate secret share and decrypt if possible."""
	
	state = config["state"]
	state["decrypting"] = True
	
	if not "decryption" in state:
		state["decryption"] = {}
	
	if not votername in [name for (name, key) in state["counterkeys"]]:
		print("You are not a vote counter!", file=sys.stderr)
		return
	
	if votesize != len(state["votes"]):
		print("Inconsistent number of votes, sync up!", file=sys.stderr)
		return
	
	state["decryption"][votername] = share.split(",")
	
	if len(state["counterkeys"]) == len(state["decryption"]):
		countervotes = list(state["decryption"].values())
		ncounters    = len(countervotes)
		
		shares = [[parsepoint(countervotes[i][k]) for i in range(ncounters)] for k in range(config["schedulesize"])]
		tally  = [points_to_secret_int(row, config["megaprime"]) for row in shares]
		
		print(countervotes, file=sys.stderr)
		print(shares, file=sys.stderr)
		print(tally, file=sys.stderr)
		
		state["finaltally"] = tally
		
		tallyfname = os.path.join("server", "public", "tally.json")
		
		with open(tallyfname, "w") as tallyfile:
			tallyfile.write(json.dumps(tally))

def sync(votername, config):
	"""Send any information that the client should know (keys and messages).
	
	Unlike the other processor, this outputs to stdout because it can be quite
	a large message."""
	
	state = config["state"]
	
	if not "counterkeys" in state:
		print("Nothing to inform about.", file=sys.stderr)
		return
	
	if not "messages" in state:
		state["messages"] = {}
	
	info = {}
	info["counterkeys"] = state["counterkeys"]
	
	if votername in state["messages"]:
		info["messages"] = [(name, state["messages"][votername][name]) for (name, vote) in state["votes"] if name in state["messages"][votername]]
	
	print(json.dumps(info))

def displayusage():
	"""Print the usage of this command to the command line."""
	
	print(("Usage:\n" +
	       "  python {0} vote votername schedule [configfile=config.json]\n" +
	       "  python {0} register votername publickey [configfile=config.json]\n" +
	       "  python {0} decrypt votername len share [configfile=config.json]\n" +
	       "  python {0} sync votername [configfile=config.json]\n\n" +
	       "    'vote'     | initiate a vote\n" +
	       "    'register' | register as a vote counter\n" +
	       "    'decrypt'  | send secret share for aggregate decryption\n" +
	       "    'sync'     | send any relevant messages to client\n" +
	       "    votername  | voter's username\n" +
	       "    schedule   | voter's schedule as a bitmap of availability.\n" +
	       "                 schedule[bit 3] is 1 if the voter can meet at timeslot 3.\n" +
	       "                 It must encoded as an array of zeros and ones,\n" +
	       "                 and then encrypted independently using Shamir's secret\n" +
	       "                 sharing scheme, encoded in base64 and concatenated with\n" +
	       "                 commas. Then for each vote counter, shares are concatenated\n" +
	       "                 using semicolons.\n" +
	       "    publickey  | vote counter's communication public key\n" +
	       "    len        | number of votes used in calculating share \n" +
	       "    share      | secret shamir's share to decrypt final tally\n" +
	       "    configfile | scheduler configuration file.").format(__file__), file=sys.stderr)

def main():
	"""Main server entry point."""
	
	# argument parsing and validation
	
	if len(sys.argv) < 3 or len(sys.argv) > 6:
		displayusage()
		return
	
	mode        = sys.argv[1]
	votername   = sys.argv[2]
	
	if mode == "register" or mode == "vote":
		if len(sys.argv) < 4:
			displayusage()
			return
		
		publickey   = sys.argv[3]
		schedule    = sys.argv[3]
		configfname = sys.argv[4] if len(sys.argv) > 4 else "config.json"
	elif mode == "decrypt":
		if len(sys.argv) < 5:
			displayusage()
			return
		
		votesize    = int(sys.argv[3])
		share       = sys.argv[4]
		configfname = sys.argv[5] if len(sys.argv) > 5 else "config.json"
	else:
		configfname = sys.argv[3] if len(sys.argv) > 3 else "config.json"
	
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
	
	configuration["megaprime"] = get_large_enough_prime([configuration["maxvotes"]])
	
	# persistent state loading ---------
	privatedir = os.path.join("server", "private")
	publicdir  = os.path.join("server", "public")
	os.makedirs(privatedir, exist_ok=True)
	os.makedirs(publicdir,  exist_ok=True)
	
	statefname = os.path.join(privatedir, "state")
	
	# create file if it doesn't exist
	with open(statefname, "a") as statefile:
		pass
	
	with open(statefname, "r") as statefile:
		data = statefile.read()
		
		if len(data) == 0:
			data = "{}"
		
		state = json.loads(data)
		configuration["state"] = state
	
	state["privatedir"] = privatedir
	state["publicdir"]  = publicdir
	
	# ----------------------------------
	
	if mode == "vote":
		# actual server processing
		print("processing vote from {}".format(votername), file=sys.stderr)
		vote(votername, schedule, configuration)
		
	elif mode == "register":
		register(votername, publickey, configuration)
		
	elif mode == "decrypt":
		decrypt(votername, votesize, share, configuration)
		
		if "finaltally" in state:
			print("final tally: {}".format(state["finaltally"]), file=sys.stderr)
		
	elif mode == "sync":
		sync(votername, configuration)
		
	else:
		print("Unrecognize mode: {}".format(mode), file=sys.stderr)
		displayusage()
		return
	
	# persistent state dumping ---------
	with open(statefname, "w") as statefile:
		statefile.write(json.dumps(state))
	
	# ----------------------------------

if __name__ == "__main__":
	main()