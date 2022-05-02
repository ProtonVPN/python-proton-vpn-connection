from proton.vpn.connection.persistence import ConnectionPersistence
import pathlib
import os
import shutil
import pytest

PERSISTENCE_DIR_PATH = os.path.join(pathlib.Path(__file__).parent.absolute(), "connection_persistence")


def teardown_module(module):
    shutil.rmtree(PERSISTENCE_DIR_PATH)


def monkey_patched_built_path(self, path, use_alt_base_path=False):
    if not use_alt_base_path:
        return os.path.join(pathlib.Path(__file__).parent.absolute(), path)

    return os.path.join(use_alt_base_path, path)


@pytest.fixture
def monkey_patched_persistence():
    x = ConnectionPersistence._get_built_path
    ConnectionPersistence._get_built_path = monkey_patched_built_path
    yield ConnectionPersistence
    ConnectionPersistence._get_built_path = x


@pytest.fixture(params=["testid1", "testid2"])
def dummy_persistence_id(request):
    return request.param


def test_get_built_path():
    cp = ConnectionPersistence()
    base = cp._get_built_path("connection_persistence")
    assert cp._get_built_path("connetion_id", base) == "{}/connetion_id".format(base)


def test_persistence_is_stored(monkey_patched_persistence, dummy_persistence_id):
    cp = monkey_patched_persistence()
    cp.persist(dummy_persistence_id)
    assert os.path.isfile(
        os.path.join(
            PERSISTENCE_DIR_PATH, dummy_persistence_id
        )
    )


def test_persistence_is_fetched(monkey_patched_persistence, dummy_persistence_id):
    cp = monkey_patched_persistence()
    assert cp.get_persisted(dummy_persistence_id)


def test_fetch_non_existing_persistence(monkey_patched_persistence):
    cp = monkey_patched_persistence()
    assert not cp.get_persisted("no_prefix")


def test_peristence_is_removed(monkey_patched_persistence, dummy_persistence_id):
    cp = monkey_patched_persistence()
    cp.persist(dummy_persistence_id)
    assert cp.get_persisted(dummy_persistence_id)
    cp.remove_persist(dummy_persistence_id)
    assert not cp.get_persisted(dummy_persistence_id)
    cp.remove_persist(dummy_persistence_id)


def test_persistence_module(monkey_patched_persistence):
    prefix = "prefix_"
    unique_id = prefix + "tested"
    cp = monkey_patched_persistence()
    assert not cp.get_persisted(prefix)
    cp.persist(unique_id)
    assert cp.get_persisted(prefix)
    cp.remove_persist(unique_id)
    assert not cp.get_persisted(prefix)
