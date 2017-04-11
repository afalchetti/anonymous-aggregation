# Anonymous Meeting Scheduler

A simple way to agree on the date for a meeting, considering everyone's schedule and making
sure to leak the minimum amount of information of each participant as possible.

Copyright (C) 2017 Angelo Falchetti.
All rights reserved.

## Dependencies
This project depends on PyCrypto and secret-sharing. You may install both of them by running

```
sudo -H pip3 install pycrypto secretsharing
```

Note: A recent version of secret-sharing is required, compatible with Python 3.

## Usage
There are two main scripts: the server and the client scripts. Also, the `config.json` file contains
general configurations about the scheduling process including input noise, max number of voters and number of timeslots.

Every time a client wants to participate in schedule vote, the client script should be called with appropriate arguments,

```
python3 client.py vote votername schedule 
```

where the schedule is binary data (one bit per timeslot) encoded as a string of '1' and '0' characters.

This script will calculate any encryption required to protect the voter's secret (currently based on Shamir's
secret sharing scheme) and output the appropriate communication to be sent the server.

Then, the server script must be called with the appropriate arguments,

```
python3 server.py vote votername schedule
```

Both scripts can performed several kinds of operations detailed when calling them without arguments.

A number of bash scripts, `vote.sh`, `register.sh`, `decrypt.sh`, `sync.sh` and `clear.sh`, pipe both processors for
a given operation and output their communication to stdout, so there's no need for the user to call the python scripts
directly. All private client information will be saved in the `client/private/votername` folder and similarly, any
private server information will be saved in `server/private`. Of course, in practice the client private folder should
never leave the client's hardware. Also, concurrency is disregarded but it should be considered in production. In
particular, the server should be completely sequential if a blockchain is to be used to verify the server computations.

The vote should proceed in stages. First, a number of vote counters should register using `register.sh countername`.
Then anyone may vote using `vote.sh votername schedule`. Finally, every counter should use `decrypt.sh countername` to
send their secret aggregate share. When all shares have been received, the server will output the final tally. A new
process can be initiated by calling `clear.sh`, which removes the data folders.

Note that you should never need to call `sync.sh`, which synchronizes the client with the server (the server sends the
client the counter public keys and any messages other clients may have sent them). It is called internally by the rest
of the scripts when needed.

## License

This project is licensed under the 3-clause BSD license. See the [LICENSE](LICENSE) file for more details.


