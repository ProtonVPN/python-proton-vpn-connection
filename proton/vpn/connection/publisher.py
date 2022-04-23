from .enum import ConnectionStateEnum
from typing import TypeVar

Subscriber = TypeVar("T")


class Publisher:

    def __init__(self):
        self.__subscribers = []

    def register(self, subscriber: Subscriber):
        """
        Register a subscriber to receive connection status updates.

            :param subscriber: object/class instance that wants to receive
                connection status updates

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

        :raises TypeError: if subscriber is not of valid type
        :raises AttributeError: if subscriber hasn't implemented required callback
        """
        if subscriber is None:
            raise TypeError("Subscriber can not be None")

        if subscriber in self.__subscribers:
            return

        if not hasattr(subscriber, "status_update"):
            raise AttributeError("Missing `status_update` callback")

        self.__subscribers.append(subscriber)

    def unregister(self, subscriber: Subscriber):
        """
        Unregister subscriber to stop receiving connection status updates.

            :param subscriber: the subscriber object
            :type subscriber: obj

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
            self.__subscribers.remove(subscriber)
        except ValueError:
            pass

    def _notify_subscribers(self, connection_status: ConnectionStateEnum):
        """*For developers*

        Notifies the subscribers about connection state changes.

        Each backend and/or protocol have to call this method whenever the connection
        state changes, so that each subscriber can receive states changes whenever they occur.

            :param connection_status: the current status of the connection
            :type connection_status: ConnectionStateEnum

        """
        for subscriber in self.__subscribers:
            subscriber.status_update(connection_status)
