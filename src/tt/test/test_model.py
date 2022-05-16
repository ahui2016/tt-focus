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

        n1 = 6
        a = Event({"task_id": task.id})
        a = go_back_n_minutes(a, n1)
        # 假设 6 分钟前启动了一个事件，现在执行 split, 产生一个新的小节。
        a.split(cfg)
        assert a.status == EventStatus.Running
        assert (a.work - n1 * 60) < 2  # 允许有一秒误差
        assert len(a.laps) == 2

        n2 = 3
        a = go_back_n_minutes(a, n2)
        old_laps = a.laps
        old_work = a.work
        # 假设经过 3 分钟后，再执行一次 split。
        a.split(cfg)
        assert a.status == EventStatus.Running
        assert old_work == a.work
        assert old_laps == a.laps  # 时长小于 split-min, 本次操作被忽略。

        n3 = 4
        a = go_back_n_minutes(a, n3)
        # 假设又经过了 4 分钟后，执行 pause。
        a.pause(cfg)
        assert a.status == EventStatus.Pausing
        length = n1 + n2 + n3  # 由于上一次的 split 操作被忽略，计时未中断。
        assert (a.work - length * 60) < 2  # 允许有一秒误差
        assert len(a.laps) == 3

        # pausing 状态下不可执行 split
        with pytest.raises(
            RuntimeError, match=r"Only running event can be split"
        ):
            a.split(cfg)

        # pausing 状态下不可执行 pause
        with pytest.raises(
            RuntimeError, match=r"Only running event can be paused"
        ):
            a.pause(cfg)

        n4 = 2
        a = go_back_n_minutes(a, n4)
        old_laps = a.laps
        old_work = a.work
        # 假设又经过了 2 分钟后，执行 resume。
        a.resume(cfg)
        assert a.status == EventStatus.Running
        assert old_work == a.work
        assert len(a.laps) == 3  # 时长小于 pause-min, 上一个休息小节无效。
        assert old_laps[:2] == a.laps[:2]
        assert old_laps[-1][0] == LapName.Pause.name
        assert a.laps[-1][0] == LapName.Split.name

        # running 状态下不可执行 resume
        with pytest.raises(
            RuntimeError, match=r"Only pausing event can be resumed"
        ):
            a.resume(cfg)

        # 模拟一个工作了 7 分钟的小节
        n5 = 7
        a = go_back_n_minutes(a, n5)
        a.pause(cfg)

        # 模拟一个休息了 30 分钟的小节
        n6 = 30
        a = go_back_n_minutes(a, n6)
        a.resume(cfg)

        # 模拟一个工作了 60 分钟的小节
        n7 = 60
        a = go_back_n_minutes(a, n7)
        a.pause(cfg)
        assert a.status == EventStatus.Pausing
        length = n1 + n2 + n3 + n5 + n7  # n4 被忽略, n6 是休息时间。
        assert (a.work - length * 60) < 2  # 允许有一秒误差。
        assert a.laps[3][0] == LapName.Pause.name  # n6 对应第 4 个小节，是休息小节。
        assert len(a.laps) == 6  # 一共 6 个小节，第 6 个小节未结束。

        # 模拟一个休息了 90 分钟的小节
        n6 = 90
        a = go_back_n_minutes(a, n6)
        laps_n = a.resume(cfg)
        # 休息时间超过上限，导致事件自动结束。
        assert a.status == EventStatus.Stopped
        length = n1 + n2 + n3 + n5 + n7  # n4 被忽略, n6 是休息时间。
        assert (a.work - length * 60) < 2  # 允许有一秒误差。
        assert a.laps[3][0] == LapName.Pause.name  # n6 对应第 4 个小节，是休息小节。
        assert laps_n == len(a.laps) == 5  # 一共 5 个小节，因为第 6 个小节超过上限被删除。
        print(a)

    def test_stop_with_no_laps(self):
        """模拟执行 resume/stop 后事件包含零个小节的情况。"""
        task = model.new_task({"name": "bbb"}).unwrap()
        cfg = model.default_cfg()
        n = cfg['split_min']
        n2 = cfg['pause_min']
        a = Event({"task_id": task.id})
        a = go_back_n_minutes(a, n)  # 模拟时间经过了 n 分钟
        a.pause(cfg)
        a = go_back_n_minutes(a, n2)  # 模拟时间经过了 n2 分钟
        assert a.resume(cfg) == 1
        a = go_back_n_minutes(a, n)  # 模拟时间经过了 n 分钟
        laps_n = a.stop(cfg)
        assert a.status == EventStatus.Stopped
        assert a.work == 0
        assert laps_n == len(a.laps) == 0

        b = Event({"task_id": task.id})
        b = go_back_n_minutes(b, n)  # 模拟时间经过了 n 分钟
        b.pause(cfg)
        n3 = cfg['pause_max']
        b = go_back_n_minutes(b, n3)  # 模拟时间经过了 n3 分钟
        assert b.resume(cfg) == 0
        assert b.status == EventStatus.Stopped
        assert b.work == 0


def test_base_repr():
    a = 123456
    for base in range(2, 37):
        b = model.base_repr(a, base)
        c = int(b, base)
        assert c == a
