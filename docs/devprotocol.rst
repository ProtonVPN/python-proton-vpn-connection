Add Protocol
================

To add a new protocol to an existing backend, need will to add 2 class properties one method:

- `protocol`
    - The `protocol` is mostly used by the backend to find all protocols and return the correct one based on the one provided to the factory
  
- `_persistence_prefix`
    - This is crucial since connection persistence heavily depends on this. To understand the format, see below in 2)

- `_setup()`
    - Where the connection is created and configured. All the necessary configurations need to be done here, since this will be called by the `up()` method.

Depending on how the backend is built, you might also need to override the `up()` and `down()` methods.
Preferrably the `up()` and `down()` methods should be handled by the backend implementation, but that might
differ on specific cases that might require more control.

As previously mentioned, very protocol has to inherit from it's implementation class
(look at protonvpn_connection.vpnconnection.networkmanager.OpenVPN).
In the following example, we're going to implement the wireguard protocol for NetworkManager, though specifics
on how to add connection to NM and is left to the protocol.

1. Derive from the backend class

.. code-block:: python

    class Wireguard(NMConnection):
        pass

2. Add the necessary class properties and method to the class

.. code-block:: python

    protocol = "wireguard"
    # Since we're deriving from NM, the prefix should always contain nm_ so that we know about which backend we're talking about,
    # given that there can be multiple backends
    _persistence_prefix = "nm_{}_".format(protocol)

    def _setup(self):
        pass

3. Depending on how the connection is added to NetworkManager, you'll have to either create the UUID before or after adding the connection to NM. Regardless, you should always set the `self._unique_id` variable to match the UUID of your connection.

At this point, the class should look like this:

.. code-block:: python

    class Wireguard(NMConnection):
        protocol = "wireguard"
        _persistence_prefix = "nm_{}_".format(protocol)

    def _setup(self):
        # create connection
        # add connection to NM
        # set `self._unique_id` variable
        # connection is ready to be used

The methods to create/add connection to NM are ommitted since they can be done in different ways, thus it'll be up to the protocol to decide
on how to do that.
