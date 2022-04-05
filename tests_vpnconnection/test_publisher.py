from proton.vpn.connection.publisher import Publisher
import pytest
val = "test-val"


class ExpectedClass:
    def status_update(self, status):
        assert status == val


class MalformedClass:
    def _callback(self, status):
        pass


def test_register_and_notify_expected_object():
    p = Publisher()
    p.register(ExpectedClass())
    p._notify_subscribers(val)


def test_register_and_notify_malformed_object():
    p = Publisher()
    with pytest.raises(AttributeError):
        p.register(MalformedClass())


def test_register_and_remove_existing_object():
    p = Publisher()
    obj = ExpectedClass()
    p.register(obj)
    p.unregister(obj)


def test_register_twice_same_object():
    p = Publisher()
    obj = ExpectedClass()
    p.register(obj)
    p.register(obj)
    p._notify_subscribers(val)


def test_remove_non_registered_object():
    p = Publisher()
    obj = ExpectedClass()
    p.unregister(obj)


def test_register_none_object():
    p = Publisher()
    with pytest.raises(TypeError):
        p.register(None)
