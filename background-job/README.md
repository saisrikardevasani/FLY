# Your first background job (FlyRank A7)

An API that takes a report request, answers in milliseconds, and builds the report in a
separate process where nobody is waiting on it.

## Bad input against a bad moment

A wrong input and a wrong moment are different failures and deserve different answers. A
request with no topic is wrong in a way that will still be wrong in four seconds, so it is
rejected at the door with a 400 and no job is ever created. A request that failed because the
oven broke might work on the next try, so it is retried with a growing wait between attempts.
Retrying bad input only burns the same error three times.
