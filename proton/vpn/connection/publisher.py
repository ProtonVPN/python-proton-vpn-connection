from typing import Callable
from .enum import ConnectionStateEnum


class Publisher:

    def __init__(self):
        self.__subscribers = []

    def register(self, who: object) -> None:
        """
        Register a subscriber to receive connection status updates.

            :param who: object/class instance that wants to receive connection status updates
            :type who: object
            :param callback: Optional.
                Pass an alternative callback method.
            :type callback: Callable

        Usage:

        .. code-block::

            class StatusUpdateReceiver:

                def _connection_status_update(self, status):
                    print(status)
                    # or do something else with the received status

            status_update_receives = StatusUpdateReceiver()

            from proton.vpn.connection import VPNConnection

            vpnconnection = VPNConnection.get_from_factory()
            vpnconnection(vpnserver, vpncredentials)
            vpnconnection.register(status_update_receives)

        Each subscriber should expose `_connection_status_update()` method,
        to guarantee that the callback is always called. If the subscriber does not provide
        `_connection_status_update()` method, then subscribers needs toe ensure that the
        alternative callback method is passed, ie:

        .. code-block::

            class StatusUpdateReceiver:

                def _my_custom_method(self, status):
                    print(status)
                    # or do something else with the received status

            status_update_receives = StatusUpdateReceiver()

            from proton.vpn.connection import VPNConnection

            vpnconnection = VPNConnection.get_from_factory()
            vpnconnection(vpnserver, vpncredentials)
            vpnconnection.register(
                status_update_receives,
                callback = status_update_receives._my_custom_method
            )

        """
        if who is None:
            raise RuntimeError("Who can not be None")

        if who in self.__subscribers:
            return

        self.__subscribers.append(who)

    def unregister(self, who) -> None:
        """
        Unregister subscriber to stop receiving connection status updates.

            :param who: who is the subscriber, smallcaps letters
            :type who: str

        Usage:

        .. code-block::

            class StatusUpdateReceiver:

                def _connection_status_update(self, status):
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
            self.__subscribers.remove(who)
        except KeyError:
            pass

    def _notify_subscribers(self, connection_status: ConnectionStateEnum) -> None:
        """*For developers*

        Notifies the subscribers about connection state changes.

        Each backend and/or protocol have to call this method whenever the connection
        state changes, so that each subscriber can receive states changes whenever they occur.

            :param connection_status: the current status of the connection
            :type connection_status: ConnectionStateEnum

        Usage:

        .. code-block::

            from proton.vpn.connection import VPNConnection

            class CustomBackend(VPNConnection):
                backend = "custom_backend"

                ...

                def up(self):
                    self._notify_subscribers(ConnectionStateEnum.DISCONNECTED)
                    self._setup()
                    self._persist_connection()
                    self._start_connection()
                    # Connection has been established
                    self._notify_subscribers(ConnectionStateEnum.CONNECTED)

                def down(self):
                    self._stop_connection()
                    self._remove_connection_persistence()

                def _stop_connection(self):
                    self._notify_subscribers(ConnectionStateEnum.DISCONNECTING)
                    # stopped connection
                    self._notify_subscribers(ConnectionStateEnum.DISCONNECTED)

                def _setup(self):
                    # setup connection
                    self._notify_subscribers(ConnectionStateEnum.CONNECTING)

        Note: Some code has been ommitted for readability.
        """
        for subscriber in self.__subscribers:
            subscriber.status_update(connection_status)
