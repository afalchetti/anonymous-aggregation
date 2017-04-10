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
import base64
import Crypto
from Crypto.PublicKey import RSA
from secretsharing import secret_int_to_points, get_large_enough_prime

def vote(votername, schedule, config):
	"""Compute and print the server vote message."""
	
	keysfname = os.path.join(config["userdir"], "keys")
	
	try:
		with open(keysfname, "r") as keysfile:
			counterkeys = json.loads(keysfile.read())
	except FileNotFoundError:
		print("Didn't found any registered vote counters.", file=sys.stderr)
		return
	
	ncounters = len(counterkeys)
	
	if ncounters < 2:
		print("Not enough counters.")
		return
	
	noise = config["inputnoise"]
	schedule = [avail if random.random() > noise else chr(2 * ord('0') + 1 - ord(avail)) for avail in schedule]
	
	shares = []
	for i in range(config["schedulesize"]):
		points = secret_int_to_points(ord(schedule[i]) - ord('0'),
		                              ncounters, ncounters, config["megaprime"])
		shares.append([str(point[0]) + "-" + str(point[1]) for point in points])
	
	# transpose, remove secretsharing prefixes, serialize to string and encrypt
	sharegroups = []
	for i, counter in enumerate(counterkeys):
		name, key  = counter
		pubkey     = RSA.importKey(base64.b64decode(key))
		sharegroup = ",".join([shares[k][i] for k in range(config["schedulesize"])])
		encrypted  = pubkey.encrypt(sharegroup.encode("utf8"), 32)[0]
		sharegroups.append(name + ">" + base64.b64encode(encrypted).decode("utf8"))
		
		print(sharegroup, file=sys.stderr)
	
	print("vote")
	print(votername)
	print(";".join(sharegroups))

# NOTE Re-registering in the middle
#      of a vote, will kill the process because
#      the old private key will be lost!
def register(votername, config):
	"""Register as a vote counter."""
	
	keypair          = RSA.generate(2048, os.urandom)
	privatekey       = keypair.exportKey(format="DER")
	publickey        = keypair.publickey().exportKey(format="DER")
	
	pubkeyfname  = os.path.join(config["userdir"], "publickey")
	privkeyfname = os.path.join(config["userdir"], "privatekey")
	
	with open(pubkeyfname, "wb") as pubfile:
		pubfile.write(publickey)
	
	with open(privkeyfname, "wb") as privfile:
		privfile.write(privatekey)
	
	print("register")
	print(votername)
	print(base64.b64encode(publickey).decode("utf8"))

def decrypt(votername, config):
	"""Send secret share for aggregate decoding."""
	
	messagefname = os.path.join(config["userdir"], "messages")
	
	try:
		with open(messagefname, "r") as messagefile:
			messages = json.loads(messagefile.read())
		
	except FileNotFoundError:
		print("No messages. Not registered as a vote counter?", file=sys.stderr)
		return
	
	tally = [0 for i in range(config["schedulesize"])]
	
	x = 0
	for (user, data) in messages:
		print(data, file=sys.stderr)
		for i in range(config["schedulesize"]):
			x, y = data[i].split("-")
			tally[i] += int(y)
	
	hextally = [x + "-" + str(timeslot) for timeslot in tally]
	
	print("decrypt")
	print(votername)
	print(len(messages))
	print(",".join(hextally))

def reqsync(votername, config):
	"""Request any information that the client should know (keys and messages)."""
	
	print("sync")
	print(votername)

def decryptuser(encrypted, privatekey):
	"""Decrypt all the shares of a particular user (one per timeslot)."""
	
	decrypted = privatekey.decrypt(base64.b64decode(encrypted))
	return decrypted.decode("utf8").split(",")

def sync(votername, config):
	"""Process information the server says the client should know (keys and messages).
	
	Unlike the rest of processor, the input comes from stdin (because it can be quite
	extensive). It should be formatted as a JSON string."""
	
	keysfname    = os.path.join(config["userdir"], "keys")
	privkeyfname = os.path.join(config["userdir"], "privatekey")
	messagefname = os.path.join(config["userdir"], "messages")
	
	info = json.load(sys.stdin)
	counterkeys = info["counterkeys"]
	
	with open(keysfname, "w") as keysfile:
		keysfile.write(json.dumps(counterkeys))
	
	if "messages" in info:
		messages = info["messages"]
		
		try:
			with open(privkeyfname, "rb") as privkeyfile:
				privatekey = RSA.importKey(privkeyfile.read())
		except FileNotFoundError:
			print("Private key not found.", file=sys.stderr)
			return
		
		decrypted = [(name, decryptuser(data, privatekey)) for (name, data) in messages]
		
		with open(messagefname, "w") as messagefile:
			messagefile.write(json.dumps(decrypted))

def displayusage():
	"""Print the usage of this command to the command line."""
	
	print(("Usage:\n" +
	       "  python {0} vote votername schedule [configfile=config.json]\n" +
	       "  python {0} register votername [configfile=config.json]\n" +
	       "  python {0} decrypt votername [configfile=config.json]\n" +
	       "  python {0} reqsync votername [configfile=config.json]\n" +
	       "  python {0} sync votername [configfile=config.json]\n\n" +
	       "    'vote'     | initiate a vote\n" +
	       "    'register' | register as a vote counter\n" +
	       "    'decrypt'  | send secret share for aggregate decryption\n" +
	       "    'reqsync'  | get any info from the server (keys and messages)\n" +
	       "    'sync'     | process server response to sync\n" +
	       "    votername  | voter's username\n" +
	       "    schedule   | voter's schedule as a bitmap of availability.\n" +
	       "                 schedule[bit 3] is 1 if the voter can meet at timeslot 3.\n" +
	       "                 It must encoded as an array of zeros and ones,\n" +
	       "                 and then encrypted independently using Shamir's secret\n" +
	       "                 sharing scheme, encoded in base64 and concatenated with\n" +
	       "                 commas. Then for each vote counter, shares are concatenated\n" +
	       "                 using semicolons.\n" +
	       "    configfile | scheduler configuration file.").format(__file__), file=sys.stderr)

def main():
	"""Main client entry point."""
	
	# argument parsing and validation
	
	if len(sys.argv) < 3 or len(sys.argv) > 5:
		displayusage()
		return
	
	mode        = sys.argv[1]
	votername   = sys.argv[2]
	
	if mode == "register" or mode == "decrypt" or mode == "reqsync" or mode == "sync":
		configfname = sys.argv[3] if len(sys.argv) > 3 else "config.json"
	else:
		if len(sys.argv) < 4:
			displayusage()
			return
		
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
	
	configuration["megaprime"] = get_large_enough_prime([configuration["maxvotes"]])
	
	# all paths from here on require this folder to exist
	userdir = os.path.join("client", "private", votername)
	configuration["userdir"] = userdir
	os.makedirs(userdir, exist_ok=True)
	
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
		vote(votername, schedule, configuration)
		
	elif mode == "register":
		register(votername, configuration)
		
	elif mode == "decrypt":
		decrypt(votername, configuration)
		
	elif mode == "reqsync":
		reqsync(votername, configuration)
		
	elif mode == "sync":
		sync(votername, configuration)
		
	else:
		print("Unrecognize mode: {}".format(mode), file=sys.stderr)
		displayusage()
		return

if __name__ == "__main__":
	main()
