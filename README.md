# GTO-: a wrapper for GTO+'s socket interface

[GTO+](https://www.gtoplus.com/) is a state of the art solver for Texas Holdem. It provides most functionality that users would want but lacks a supported programmatic scripting interface.
However, there is an _unofficial_ socket interface, and this library provides a wrapper around that interface.

## Setup
There are two steps to access GTO+ via sockets:
1. you need to add/modify a file in the `GTO+` directory in `ProgramFiles`.
   Namely, you need to add a file `GTO+/tmp/customconnect.txt` with contents:
   ```
   override
   ```

2. you need to ensure you are connecting to the correct port.
   By default this library uses port `55143` which should be the port that GTO+ uses by default:
   if not, you can alter the port either in GTO+'s options or by specifying another port when invoking this interface.

## Use
Once you've performed both setup steps above you can import `gto` and create a new `GTO` instance which will act as your interface to the solver:
```
>>> import gto

>>> s = GTO(port=55143)
>>> s.connect()
'You are connected to GTO+'
>>> s.load_file("some/file.gto")
>>> nd = s.request_node_data()
>>> nd['pos']
'oop'
>>> nd['actions']
['Bet 1', 'Check']
```
