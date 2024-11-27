## Build Automation

I found myself repeating things, so I scripted it.

This is mainly for me tracking my things, but if it helps anyone else that's fine.


## TODO

Crap I just found another issue I want to address with this tool I am building.

Basically I am testing out options right now and I wish to test only the
configuration phase of the building.

Which means I kinda want a way to fetch and configure only, without build.

So it makes me think I need to introduce some options to the command line.

-f --fetch
-c --configure
-b --build
-t --test

But they are kinda dependent on each other, I still want to be able to run them
in isolation, so I can skip re-building If for instance the test harness
changes, but the code doesn't need to be re-built.

That's for another day though, because it's too much work for the simple thing I
wish to do right now.

I could default to if nothing is specified then all.
