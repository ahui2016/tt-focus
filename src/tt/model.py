import arrow
from typing import Final, TypedDict
from dataclasses import dataclass
from enum import Enum, auto
from random import randrange
import msgpack


DateFormat: Final = "YYYY-MM-DD"
TimeFormat: Final = "HH:mm:ss"

ConfigName: Final = "meta-config"


def now() -> int:
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

    def pack(self) -> bytes:
        return msgpack.packb(self)


def default_cfg() -> Config:
    return Config(
        split_min=5,
        pause_min=5,
        pause_max=60
    )


def new_cfg_from(data: bytes) -> Config:
    return msgpack.unpackb(data)


class MultiText(TypedDict):
    cn: str
    en: str


class EventStatus(Enum):
    Running = auto()
    Pausing = auto()
    Stopped = auto()


class LapName(Enum):
    Split = auto()
    Pause = auto()


Lap = tuple[str, int, int, int]
"""(name, start, end, length) : (LapName, timestamp, timestamp, seconds)"""


@dataclass
class Task:
    id: str  # rand_id
    name: str
    alias: str

    def __init__(self, d: dict) -> None:
        self.id = d.get("id", rand_id())
        self.name = d["name"]
        self.alias = d.get("alias", "")


@dataclass
class Event:
    id: str  # date_id
    task_id: str
    status: EventStatus  # 状态
    laps: tuple[Lap]  # 过程
    work: int  # 有效工作时间合计：秒

    def __init__(self, d: dict) -> None:
        self.id = d.get("id", date_id())
        self.task_id = d["task_id"]
        status = d.get("status", "Running")
        self.status = EventStatus[status]
        lap = (LapName.Split.name, now(), 0, 0)
        self.laps = (
            msgpack.unpackb(d["laps"], use_list=False)
            if d.get("laps", False)
            else (lap,)
        )
        self.work = d.get("work", 0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.name,
            "laps": msgpack.packb(self.laps, use_list=False),
            "work": 0,
        }


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
