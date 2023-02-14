"""
Connection persistence.

Connection parameters are persisted to disk so that they can be loaded after a crash.
"""

import json
import os
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Optional

from proton.utils.environment import VPNExecutionEnvironment
from proton.vpn import logging

logger = logging.getLogger(__name__)


@dataclass
class ConnectionParameters:
    """Connection parameters to be persisted to disk."""
    connection_id: str
    backend: str
    protocol: str
    server_id: str
    server_name: str


class ConnectionPersistence:
    """Saves/loads connection parameters to/from disk."""
    FILENAME = "connection_persistence.json"

    def __init__(self, persistence_directory: str = None):
        self._directory = persistence_directory

    @property
    def _connection_file_path(self):
        if not self._directory:
            self._directory = os.path.join(
                VPNExecutionEnvironment().path_cache, "connection"
            )
            os.makedirs(self._directory, mode=0o700, exist_ok=True)

        return os.path.join(self._directory, self.FILENAME)

    def load(self) -> Optional[ConnectionParameters]:
        """Returns the connection parameters loaded from disk, or None if
        no connection parameters were persisted yet."""
        if not os.path.isfile(self._connection_file_path):
            return None

        with open(self._connection_file_path, encoding="utf-8") as file:
            try:
                file_content = json.load(file)
                return ConnectionParameters(
                    connection_id=file_content["connection_id"],
                    backend=file_content["backend"],
                    protocol=file_content["protocol"],
                    server_id=file_content["server_id"],
                    server_name=file_content["server_name"],
                )
            except (JSONDecodeError, KeyError):
                logger.exception(
                    "Unexpected error parsing connection persistence file: "
                    f"{self._connection_file_path}",
                    category="CONN", subcategory="PERSISTENCE", event="LOAD"
                )
                return None

    def save(self, connection_parameters: ConnectionParameters):
        """Saves connection parameters to disk."""
        with open(self._connection_file_path, "w", encoding="utf-8") as file:
            json.dump(connection_parameters.__dict__, file)

    def remove(self):
        """Removes the connection persistence file, if it exists."""
        if os.path.isfile(self._connection_file_path):
            os.remove(self._connection_file_path)
        else:
            logger.warning(
                f"Connection persistence not found when trying "
                f"to remove it: {self._connection_file_path}",
                category="CONN", subcategory="PERSISTENCE", event="REMOVE"
            )
