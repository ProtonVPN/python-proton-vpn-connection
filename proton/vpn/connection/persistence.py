import json
import os
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Optional

from proton.utils.environment import ExecutionEnvironment
import proton.vpn.logging as logging

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
    FILENAME = "connection_persistence.json"

    def __init__(self, persistence_directory: str = None):
        self._directory = persistence_directory

    @property
    def _connection_file_path(self):
        if not self._directory:
            self._directory = os.path.join(
                ExecutionEnvironment().path_cache, "vpn", "connection"
            )
            os.makedirs(self._directory, mode=0o700, exist_ok=True)

        return os.path.join(self._directory, self.FILENAME)

    def load(self) -> Optional[ConnectionParameters]:
        if not os.path.isfile(self._connection_file_path):
            return None

        with open(self._connection_file_path) as f:
            try:
                d = json.load(f)
                return ConnectionParameters(
                    connection_id=d["connection_id"],
                    backend=d["backend"],
                    protocol=d["protocol"],
                    server_id=d["server_id"],
                    server_name=d["server_name"],
                )
            except (JSONDecodeError, KeyError):
                logger.exception(
                    "Unexpected error parsing connection persistence file: "
                    f"{self._connection_file_path}",
                    category="CONN", subcategory="PERSISTENCE", event="LOAD"
                )
                return None

    def save(self, connection_parameters: ConnectionParameters):
        with open(self._connection_file_path, "w") as f:
            json.dump(connection_parameters.__dict__, f)

    def remove(self):
        if os.path.isfile(self._connection_file_path):
            os.remove(self._connection_file_path)
        else:
            logger.warning(
                f"Connection persistence not found when trying "
                f"to remove it: {self._connection_file_path}",
                category="CONN", subcategory="PERSISTENCE", event="REMOVE"
            )
