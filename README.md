# CXS Controlroom Core

Crossbar/Autobahn powered controlroom API. Provided a controllers.json file specifying a list of controller types (e.g. thorlabs, newport, andor), server.py generates a controller, providing remote procedure calls for common commands (move, home, abort, close shutter, capture, etc) and pubsub telemetry reflection (on telemetry change, telemetry publishes on the 'com.controlroom.measurements' channel).

## Usage
To run, ensure the desired hardware is connected and any necessary control
software running (mar345 notably requires this), then execute:
```bash
python server.py
```

Optionally, if the crossbar router is on a different host:
```bash
python server.py --host=<crossbar_host> --port=<crossbar_port>
```

Additionally, if you wish to run the server as a service (recommended for
production), modify the provided systemd and copy it to /etc/systemd/multiuser

## Writing a Controlroom node - the WAMP way

Provided the url of the crossbar router is set correctly, the node in question at a minimum need only expose the `.describe` RPC (the only mandatory field being "type", set to one of `camera`, `source`, `sensor`, `motor`), and publish measurements and status information to the `.measurements` and `.status` endpoints, respectively. Aside from those, you're free to expose as many or as few RPC endpoints as you like. If your language of choice (there are, as of this writing, 25 implementations in 15 languages) has reflection, as python does, its suggested to use it for RPC exposure (as demonstrated in server.py).

## Writing a Controlroom node - no WAMP, just HTTP

You must change the crossbar router config - adding a HTTP callee, a HTTP Subscribe and a HTTP Publisher per node. Registering RPCs (to be routed via the HTTP callee bridge) is of course, a little tricker, since the crossbar router's knowledge stops at the HTTP bridge. On binding/listening to the HTTP caller address and the HTTP Subscriber address, the node should POST a message to the HTTP Publisher address, with the `com.controlroom.announce_capabilities` topic. The subscription should respond to `com.controlroom.request_capabilities`. Publish calls proceed as normal, replacing `self.publish` calls with your language's AJAX POST methods (the key stipulation being that data is in JSON). RPC Call responses proceed similarly to responding to a normal AJAX request.

An important thing to note is that you'll largely need to call procedures based on the payload data rather than the url - depending on how many procedures you have associated, it may be worthwhile to use your routing library's data-dependent routing (.NET Web APIs allow this in route decorators).

If you're finding yourself producing *a lot* of HTTP Controlroom nodes, either:

1. Consider using the WAMP approach outright for some of them, *OR*
2. Shift the logic into a minimal intermediate WAMP node, registering simple AJAX wrapper functions at all the endpoints corresponding to its subsidiary controllers (e.g. controller 674674 is attached, to node X, node X registers foo() to `'com.controlroom.674674.foo'`). This will incur somewhat less than one round-trip period (tiny if the node is on the same machine as the subsidiary controller), in exchange for dissociating client nodes from the crossbar router configuration. This is a must if you don't have control over the crossbar configuration (i.e. request one intermediate controller be added to the configuration, then pipe everything through that at your discretion).

# Design
## Locking considerations
We want to be able to stop a motor in mid-motion regardless of its current status (part of a scanning procedure or otherwise); this is provided by all known motor control systems (either through a signal in an asynchronous connection, or a signal via a new synchronous connection). We also want to prevent new commands being accepted (better yet, ever fired) when one is in progress (or temporarily locked).

Controllers should respond to a command:
1. immediately, if the command is abort.
2. reject if locked with status 'in progress' and a time remaining of greater than 5s, with the remaining time and the reason (in progress).
3. reject if locked with status 'temporary hold', with the remaining time and the name of the client that placed the hold.
4. wait if locked with any status and a time remaining of less than 5s, then proceed. Note that this requires scanning procedures to lock all requisite controllers for the duration of the scan (otherwise a motor could be used during the after_move phase).
5. proceed as normal if not locked.
