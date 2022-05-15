import pytest
from .. import model
from ..model import Event, EventStatus, LapName, Lap


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


def go_back_n_minutes(event: Event, n: int) -> Event:
    """让 event 时光倒流 n 分钟。"""
    s = n * 60
    event.started -= s
    laps: tuple[Lap, ...] = ()
    for lap in event.laps:
        end = 0 if lap[2] == 0 else lap[2] - s
        laps += ((lap[0], lap[1] - s, end, lap[3]),)
    event.laps = laps
    return event


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

    def test_operation(self):
        task = model.new_task({"name": "aaa"}).unwrap()
        cfg = model.default_cfg()

        len1 = 6
        a = Event({"task_id": task.id})
        a = go_back_n_minutes(a, len1)
        a.split(cfg)
        assert a.status == EventStatus.Running
        assert (a.work - len1 * 60) < 2  # 允许有一秒误差
        assert len(a.laps) == 2

        len2 = 3
        a = go_back_n_minutes(a, len2)
        old_laps = a.laps
        old_work = a.work
        a.split(cfg)
        assert a.status == EventStatus.Running
        assert old_work == a.work
        assert old_laps == a.laps  # 时长小于 split-min, 本次操作被忽略。

        len3 = 4
        a = go_back_n_minutes(a, len3)
        a.pause(cfg)
        assert a.status == EventStatus.Pausing
        length = len1 + len2 + len3  # 由于上一次的 split 操作被忽略，计时未中断。
        assert (a.work - length * 60) < 2  # 允许有一秒误差
        assert len(a.laps) == 3

        with pytest.raises(
            RuntimeError, match=r"Only running event can be split"
        ):
            a.split(cfg)

        with pytest.raises(
            RuntimeError, match=r"Only running event can be paused"
        ):
            a.pause(cfg)


def test_base_repr():
    a = 123456
    for base in range(2, 37):
        b = model.base_repr(a, base)
        c = int(b, base)
        assert c == a
