# Your first background job (FlyRank A7)

An API that takes a report request, answers in milliseconds, and builds the report in a
separate process where nobody is waiting on it.

## Bad input against a bad moment

A wrong input and a wrong moment are different failures and deserve different answers. A
request with no topic is wrong in a way that will still be wrong in four seconds, so it is
rejected at the door with a 400 and no job is ever created. A request that failed because the
oven broke might work on the next try, so it is retried with a growing wait between attempts.
Retrying bad input only burns the same error three times.

## Reading a cron expression

Five fields, left to right: minute, hour, day of month, month, day of week. A `*` means every.

The heartbeat here runs `* * * * *`, every minute, which is a testing schedule and nothing else.
To run it **every day at 08:00** the expression is `0 8 * * *`: at minute 0 of hour 8, every day
of every month. To run it **every Sunday at 22:00** it is `0 22 * * 0`: at minute 0 of hour 22,
only on day-of-week 0, which is Sunday.

Both were built on crontab.guru rather than decoded by hand. Servers usually run cron in UTC, so
a schedule that looks like 08:00 to you may not be 08:00 where it runs.
