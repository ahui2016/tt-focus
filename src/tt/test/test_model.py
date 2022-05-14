import pytest
from .. import model
from ..model import Event, EventStatus, LapName


def test_date_id():
    date_id = model.date_id()
    assert type(date_id) is str
    assert len(date_id) >= 6


def assert_rand_id(a, b):
    assert len(a) == 4 and len(b) == 4
    assert a != b


def test_rand_id():
    a = model.rand_id()
    b = model.rand_id()
    assert_rand_id(a, b)


def test_default_cfg():
    a = model.default_cfg()
    assert a["split_min"] > 0 and a["pause_min"] > 0 and a["pause_max"] > 0


class TestTask:
    def test_init_without_name(self):
        # https://docs.pytest.org/en/6.2.x/assert.html#assertions-about-expected-exceptions
        with pytest.raises(KeyError, match=r"'name'"):
            model.new_task({"_": "_"})

    def test_init_without_id(self):
        a = model.new_task({"name": "aaa"}).unwrap()
        b = model.new_task({"name": "bbb"}).unwrap()
        assert_rand_id(a.id, b.id)
        assert a.alias + b.alias == ""

    def test_init_with_wrong_name(self):
        assert model.new_task({"name": "a+b"}).is_err()
        err = model.new_task({"name": " a "}).unwrap_err()
        assert type(err["cn"]) is str
        assert type(err["en"]) is str

    def test_init(self):
        a = {"id": model.rand_id(), "name": "aaa", "alias": "bbb"}
        b = model.new_task(a).unwrap()
        assert (
            b.id == a["id"] and b.name == a["name"] and b.alias == a["alias"]
        )


class TestEvent:
    def test_init_without_id(self):
        start = model.now()
        a = model.new_task({"name": "aaa"}).unwrap()
        b = Event({"task_id": a.id})
        assert len(b.id) >= 6
        assert b.task_id == a.id
        assert b.started - start < 2  # 允许有一秒误差
        assert b.status is EventStatus.Running
        assert len(b.laps) == 1
        lap = b.laps[0]
        assert lap[0] == LapName.Split.name
        assert lap[1] == b.started
        assert lap[2] + lap[3] == 0
        assert b.work == 0

    def test_init(self):
        a = model.new_task({"name": "aaa"}).unwrap()
        b = Event({"task_id": a.id})
        c = b.to_dict()
        assert len(c.keys()) == 6
        assert b.id == c["id"]
        assert b.task_id == c["task_id"]
        assert b.started == c["started"]
        assert b.status.name == c["status"]
        laps = model.unpack(c["laps"])
        assert b.laps == laps
        assert b.work == c["work"]


def test_base_repr():
    a = 123456
    for base in range(2, 37):
        b = model.base_repr(a, base)
        c = int(b, base)
        assert c == a
