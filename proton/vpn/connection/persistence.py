import os
from proton.utils.environment import ExecutionEnvironment


class ConnectionPersistence:

    def __init__(self):
        self._dir_path = self._get_built_path("connection_persistence")
        os.makedirs(self._dir_path, exist_ok=True)

    def get_persisted(self, prefix):
        dir_list = os.listdir(self._dir_path)
        if len(dir_list) == 0:
            return None

        for filename in dir_list:
            if filename.startswith(prefix):
                return filename

        return None

    def persist(self, conn_id):
        with open(self._get_built_path(conn_id, use_alt_base_path=self._dir_path), "w") as f:
            f.write(conn_id)

    def remove_persist(self, conn_id):
        filepath = self._get_built_path(conn_id, use_alt_base_path=self._dir_path)
        if os.path.isfile(filepath):
            os.remove(filepath)

    def _get_built_path(self, path, use_alt_base_path=False):
        if not use_alt_base_path:
            return os.path.join(ExecutionEnvironment().path_runtime, path)

        return os.path.join(use_alt_base_path, path)
