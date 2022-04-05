from .enum import ConnectionStateEnum


class Publisher:

    def __init__(self):
        self.__subscribers = []

    def register(self, listener: object) -> None:
        """
        Register a subscriber to receive connection status updates.

            :param listener: object/class instance that wants to receive
                connection status updates
            :type listener: object

        Usage:

        .. code-block::

            class StatusUpdateReceiver:

                def status_update(self, status):
                    print(status)
                    # or do something else with the received status

            status_update_receives = StatusUpdateReceiver()

            from proton.vpn.connection import VPNConnection

            vpnconnection = VPNConnection.get_from_factory()
            vpnconnection(vpnserver, vpncredentials)
            vpnconnection.register(status_update_receives)

        Each subscriber should have a `status_update()`
        method to receive updates.
        """
        if listener is None:
            raise TypeError("Listener can not be None")

        if listener in self.__subscribers:
            return

        if not hasattr(listener, "status_update"):
            raise AttributeError("Missing `status_update` callback")

        self.__subscribers.append(listener)

    def unregister(self, listener) -> None:
        """
        Unregister subscriber to stop receiving connection status updates.

            :param listener: the subscriber object
            :type listener: obj

        Usage:

        .. code-block::

            class StatusUpdateReceiver:

                def status_update(self, status):
                    print(status)
                    # or do something else with the received status

            status_update_receives = StatusUpdateReceiver()

            from proton.vpn.connection import VPNConnection

            vpnconnection = VPNConnection.get_from_factory()
            vpnconnection(vpnserver, vpncredentials)
            vpnconnection.register(status_update_receives)

            # lower in the code I then decide that I no longer wish to
            # receive connection status updates, so I decide to
            # unregister myself as a subscriber:
            vpnconnection.unregister(status_update_receives)

        """
        try:
            self.__subscribers.remove(listener)
        except ValueError:
            pass

    def _notify_subscribers(self, connection_status: ConnectionStateEnum) -> None:
        """*For developers*

        Notifies the subscribers about connection state changes.

        Each backend and/or protocol have to call this method whenever the connection
        state changes, so that each subscriber can receive states changes whenever they occur.

            :param connection_status: the current status of the connection
            :type connection_status: ConnectionStateEnum

        """
        for subscriber in self.__subscribers:
            subscriber.status_update(connection_status)
