from dataclasses import dataclass
from enum import Enum, auto


class EventStatus(Enum):
    Running = auto()
    Pausing = auto()


class LapName(Enum):
    Split = auto()
    Pause = auto()


Lap = tuple(str, int, int, int)
"""(name, start, end, length) : (LapName, timestamp, timestamp, seconds)"""


@dataclass
class Event:
    id: str  # date_id
    started: int  # timestamp
    stopped: int  # timestamp
    status: EventStatus  # 状态
    laps: list[Lap]  # 过程
    work: int  # 有效工作时间合计：秒

