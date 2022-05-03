import arrow
from typing import Final
from dataclasses import dataclass
from enum import Enum, auto
import msgpack


DateFormat: Final = "YYYY-MM-DD"
TimeFormat: Final = "HH:mm:ss"


def now() -> int:
    return arrow.now().int_timestamp


def date_id() -> str:
    """时间戳转base36"""
    return base_repr(now(), 36)


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
class Event:
    id: str              # date_id
    status: EventStatus  # 状态
    laps: tuple[Lap]     # 过程
    work: int            # 有效工作时间合计：秒

    def __init__(self, d: dict | None) -> None:
        self.id = (d.id,)
        self.status = (EventStatus[d.status],)
        self.laps = (msgpack.unpackb(d.laps, use_list=False),)
        self.work = d.work

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

