# Anonymous Meeting Scheduler

A simple way to agree on the date for a meeting, considering everyone's schedule and making
sure to leak the minimum amount of information of each participant as possible.

Copyright (C) 2017 Angelo Falchetti.
All rights reserved.

## Usage
There are two main scripts: the server and the client scripts. Also, the `configuration.json` file contains
general configurations about the scheduling process.

Every time a client wants to participate in schedule vote, the client script should be called with appropriate arguments,

```
python3 client.py votername schedule 
```
where the schedule is binary data (one bit per timeslot) encoded as a string of '1' and '0' characters.

This script will calculate any encryption required to protect the voter's secret (for now, no encryption is applied),
generate an update ticket (which can be used to update the vote later) and output the appropriate communication to
be sent the server.

Then, the server script must be called with the appropriate arguments,

```
python3 server.py votername schedule ticket
```

A third bash script, `vote.sh` (which takes the same arguments as `client.py`) pipes both processor and outputs
their communication to stdout, so there's no need for the user to call the server script directly. All private
client information will be saved in the `client/private/votername` folder and similarly, any private server
information will be saved in `server/private`. Any public information will be saved in the corresponding
`client/public/votername` and `server/public`. Of course, in practice the client private folder should never leave
the client's hardware. Also, concurrency is disregarded but it should be considered in production. In particular,
the server should be completely sequential if a blockchain is to be used to verify the server computations.

## License

This project is licensed under the 3-clause BSD license. See the [LICENSE](LICENSE) file for more details.


