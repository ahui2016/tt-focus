import re
import arrow
from typing import Final, TypedDict
from result import Err, Ok, Result
from dataclasses import dataclass, asdict
from enum import Enum, auto
from random import randrange
import msgpack


OK: Final = Ok("OK")
UnknownReturn: Final = Exception("Unknown-return")
RecentItemsMax: Final[int] = 9

DateFormat: Final = "YYYY-MM-DD"
TimeFormat: Final = "HH:mm:ss"
ConfigName: Final = "meta-config"

NameForbidPattern: Final = re.compile(r"[^_0-9a-zA-Z\-]")
"""只允许使用 -, _, 0-9, a-z, A-Z"""


def now() -> int:
    """timestamp"""
    return arrow.now().int_timestamp


def date_id() -> str:
    """时间戳转base36"""
    return base_repr(now(), 36)


def rand_id() -> str:
    """只有 4 个字符的随机字符串"""
    n_min = int("1000", 36)
    n_max = int("zzzz", 36)
    n_rand = randrange(n_min, n_max + 1)
    return base_repr(n_rand, 36)


class AppConfig(TypedDict):
    """最基本的设定，比如语言、数据库文件的位置。"""

    lang: str  # 'cn' or 'en'
    db_path: str


class Config(TypedDict):
    split_min: int  # 单位：分钟，小于该值自动忽略
    pause_min: int  # 单位：分钟，小于该值自动忽略
    pause_max: int  # 单位：分钟，大于该值自动忽略


def default_cfg() -> Config:
    return Config(split_min=5, pause_min=5, pause_max=60)


def pack(obj) -> bytes:
    return msgpack.packb(obj)


def unpack(data: bytes):
    return msgpack.unpackb(data, use_list=False)


@dataclass
class MultiText:
    cn: str
    en: str

    def str(self, lang: str) -> str:
        return asdict(self)[lang]


class EventStatus(Enum):
    Running = auto()
    Pausing = auto()
    Stopped = auto()


class LapName(Enum):
    Split = auto()
    Pause = auto()


Lap = tuple[str, int, int, int]
"""(name, start, end, length) : (LapName, timestamp, timestamp, seconds)"""


def check_name(name: str) -> Result[str, MultiText]:
    if NameForbidPattern.search(name) is None:
        return OK
    else:
        err = MultiText(
            cn="出错: 名称只允许由 0-9, a-z, A-Z 以及下划线、短横线组成",
            en="Error: The name may only contain -, _, 0-9, a-z, A-Z",
        )
        return Err(err)


@dataclass
class Task:
    """请勿直接使用 Task(), 请使用 NewTask(dict)"""

    id: str  # rand_id
    name: str
    alias: str

    def __str__(self):
        if self.alias:
            return f"{self.name} ({self.alias})"
        return f"{self.name}"


def new_task(d: dict) -> Result[Task, MultiText]:
    t_id = d.get("id", rand_id())
    name = d["name"]
    alias = d.get("alias", "")
    task = Task(id=t_id, name=name, alias=alias)
    err = check_name(name).err()
    if err is None:
        return Ok(task)
    else:
        return Err(err)


@dataclass
class Event:
    id: str  # date_id
    task_id: str
    started: int  # timestamp
    status: EventStatus  # 状态
    laps: tuple[Lap, ...]  # 过程
    work: int  # 有效工作时间合计：秒

    def __init__(self, d: dict):
        self.id = d.get("id", date_id())
        self.task_id = d["task_id"]
        self.started = d.get("started", now())
        status = d.get("status", "Running")
        self.status = EventStatus[status]
        lap = (LapName.Split.name, self.started, 0, 0)
        self.laps = unpack(d["laps"]) if d.get("laps", False) else (lap,)
        self.work = d.get("work", 0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "started": self.started,
            "status": self.status.name,
            "laps": pack(self.laps),
            "work": self.work,
        }

    def close_last_lap(self) -> Lap:
        """上一个小节结束，填写结束时间与小节长度。"""
        last_lap = self.laps[-1]
        end = now()
        last_lap = (last_lap[0], last_lap[1], end, end - last_lap[1])
        self.laps = self.laps[:-1] + (last_lap,)
        return last_lap

    def cancel(self) -> None:
        """把上一个小节恢复原状，不添加新的小节。"""
        last_lap = self.laps[-1]
        last_lap = (last_lap[0], last_lap[1], 0, 0)
        self.laps = self.laps[:-1] + (last_lap,)

    def split(self, cfg: Config) -> None:
        if self.status is not EventStatus.Running:
            raise RuntimeError(
                f"Only running event can be split. Current status: {self.status}"
            )

        # 上一个小节结束。
        last_lap = self.close_last_lap()

        # 如果上个小节的长度小于下限，则本次 split 操作无效。
        if last_lap[-1] <= cfg["split_min"] * 60:
            self.cancel()
            return

        # 新小节的开始时间，就是上个小节的结束时间
        start = last_lap[2]
        lap = (LapName.Split.name, start, 0, 0)
        self.laps += (lap,)
        self.work += last_lap[-1]

    def pause(self, cfg: Config) -> None:
        if self.status is not EventStatus.Running:
            raise RuntimeError(
                f"Only running event can be paused. Current status: {self.status}"
            )

        # 上一个小节结束。
        last_lap = self.close_last_lap()

        # 如果上个小节的长度小于下限，则上个小节被视为无效 (直接删除)。
        if last_lap[-1] <= cfg["split_min"] * 60:
            self.laps = self.laps[:-1]
            start = now()
        else:
            # 上个小节有效，新小节的开始时间，就是上个小节的结束时间，
            # 并且把上个小节的长度累加到总工作时长中。
            start = last_lap[2]
            self.work += last_lap[-1]

        lap = (LapName.Pause.name, start, 0, 0)
        self.laps += (lap,)
        self.status = EventStatus.Pausing

    def resume(self, cfg: Config) -> None:
        if self.status is not EventStatus.Pausing:
            raise RuntimeError(
                f"Only pausing event can be resumed. Current status: {self.status}"
            )

        # 上一个小节结束。
        last_lap = self.close_last_lap()

        # 如果上个小节的长度大于上限，则视为无效，并且事件状态变为 stopped,
        # caller 要检查事件状态，如果变为 stopped 则需要在 caller 启动新的事件。
        if last_lap[-1] >= cfg["pause_max"] * 60:
            self.laps = self.laps[:-1]
            self.status = EventStatus.Stopped
            return

        # 如果上个小节的长度小于下限，则上个小节被视为无效 (直接删除)。
        if last_lap[-1] <= cfg["pause_min"] * 60:
            self.laps = self.laps[:-1]
            start = now()
        else:
            # 上个小节有效，新小节的开始时间，就是上个小节的结束时间，
            start = last_lap[2]

        lap = (LapName.Split.name, start, 0, 0)
        self.laps += (lap,)
        self.status = EventStatus.Running

    def stop(self, cfg: Config) -> None:
        if self.status is EventStatus.Stopped:
            raise RuntimeError("Cannot operate on a stopped event.")

        # 上一个小节结束。
        last_lap = self.close_last_lap()

        # 如果上个小节的长度小于下限，或大于上限，则上个小节被视为无效 (直接删除)。
        if (
            (
                self.status is EventStatus.Running
                and last_lap[-1] <= cfg["split_min"] * 60
            )
            or (
                self.status is EventStatus.Pausing
                and last_lap[-1] <= cfg["pause_min"] * 60
            )
            or (
                self.status is EventStatus.Pausing
                and last_lap[-1] > cfg["pause_max"] * 60
            )
        ):
            self.laps = self.laps[:-1]
        elif self.status is EventStatus.Running:
            # 如果不属于以上特殊情况，并且上个小节是 running 状态，则需要统计工作时长。
            self.work += last_lap[-1]

        self.status = EventStatus.Stopped


# https://github.com/numpy/numpy/blob/main/numpy/core/numeric.py
def base_repr(number: int, base: int = 10, padding: int = 0) -> str:
    """
    Return a string representation of a number in the given base system.
    """
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if base > len(digits):
        raise ValueError("Bases greater than 36 not handled in base_repr.")
    elif base < 2:
        raise ValueError("Bases less than 2 not handled in base_repr.")

    num = abs(number)
    res = []
    while num:
        res.append(digits[num % base])
        num //= base
    if padding:
        res.append("0" * padding)
    if number < 0:
        res.append("-")
    return "".join(reversed(res or "0"))
