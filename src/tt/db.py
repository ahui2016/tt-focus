import sqlite3
from dataclasses import asdict

import arrow
import msgpack
from pathlib import Path
from appdirs import AppDirs
from result import Err, Ok, Result
from typing import Final, Iterable, TypeAlias
from . import stmt, model
from .model import (
    Config,
    ConfigName,
    AppConfig,
    Task,
    MultiText,
    Event,
    UnknownReturn,
)

Conn: TypeAlias = sqlite3.Connection

NoResultError: Final = MultiText(cn="数据库检索无结果", en="db-query-no-result")
OK: Final = Ok("OK")

AppCfgFilename: Final = "tt-focus.cfg"
DB_Filename: Final = "tt-focus.db"

app_dirs = AppDirs("tt-focus", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
app_cfg_path = app_config_dir.joinpath(AppCfgFilename)
default_db_path = app_config_dir.joinpath(DB_Filename)


def write_cfg_file(cfg: AppConfig) -> None:
    app_cfg_path.write_bytes(msgpack.packb(cfg))


def load_app_cfg() -> AppConfig:
    return model.unpack(app_cfg_path.read_bytes())


def connect(db_path: str) -> Conn:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(stmt.Enable_foreign_keys)
    return conn


def conn_update(
    conn: Conn, query: str, param: Iterable, many: bool = False
) -> Result[int, str]:
    if many:
        n = conn.executemany(query, param).rowcount
    else:
        n = conn.execute(query, param).rowcount
    if n <= 0:
        return Err("Error: sqlite row affected = 0")
    return Ok(n)


def ensure_cfg_file() -> None:
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if not app_cfg_path.exists():
        default_cfg = AppConfig(lang="en", db_path=default_db_path.__str__())
        write_cfg_file(default_cfg)

    app_cfg = load_app_cfg()
    db_path = Path(app_cfg["db_path"])
    if not db_path.exists():
        with connect(str(db_path)) as conn:
            conn.executescript(stmt.Create_tables)
            init_cfg(conn)


def get_cfg(conn: Conn) -> Result[Config, MultiText]:
    row = conn.execute(stmt.Get_metadata, (ConfigName,)).fetchone()
    if row is None:
        return Err(NoResultError)
    cfg: Config = model.unpack(row[0])
    return Ok(cfg)


def update_cfg(conn: Conn, cfg: Config) -> None:
    conn_update(
        conn,
        stmt.Update_metadata,
        {"name": ConfigName, "value": model.pack(cfg)},
    ).unwrap()


def init_cfg(conn: Conn) -> None:
    if get_cfg(conn).is_err():
        conn_update(
            conn,
            stmt.Insert_metadata,
            {"name": ConfigName, "value": model.pack(model.default_cfg())},
        ).unwrap()


def get_task(conn: Conn, query: str, value: str) -> Result[Task, MultiText]:
    row = conn.execute(query, (value,)).fetchone()
    if row is None:
        return Err(NoResultError)

    task = model.new_task(dict(row)).unwrap()
    return Ok(task)


def get_task_by_name(conn: Conn, name: str) -> Result[Task, MultiText]:
    return get_task(conn, stmt.Get_task_by_name, name)


def get_task_by_id(conn: Conn, task_id: str) -> Result[Task, MultiText]:
    return get_task(conn, stmt.Get_task_by_id, task_id)


def insert_task(conn: Conn, task: Task) -> Result[str, MultiText]:
    old_task = get_task_by_name(conn, task.name).ok()
    if old_task is None:
        conn_update(conn, stmt.Insert_task, asdict(task)).unwrap()
        return OK

    err = MultiText(
        cn=f"出错: 任务类型已存在: {old_task}",
        en=f"Error: Task type exists: {old_task}",
    )
    return Err(err)


def get_all_task(conn: Conn) -> list[Task]:
    rows = conn.execute(stmt.Get_all_tasks).fetchall()
    return [model.new_task(dict(row)).unwrap() for row in rows]


def set_task_alias(conn: Conn, alias: str, name: str) -> None:
    conn_update(
        conn, stmt.Set_task_alias, dict(alias=alias, name=name)
    ).unwrap()


def set_task_name(conn: Conn, new_name: str, old_name: str) -> None:
    conn_update(
        conn, stmt.Set_task_name, dict(new_name=new_name, old_name=old_name)
    ).unwrap()


def insert_event(conn: Conn, event: Event) -> None:
    conn_update(conn, stmt.Insert_event, event.to_dict()).unwrap()


def set_event_notes(conn: Conn, notes: str, event_id: str) -> None:
    conn_update(
        conn, stmt.Set_event_notes, dict(notes=notes, id=event_id)
    ).unwrap()


def get_event_by_id(conn: Conn, event_id: str) -> Result[Event, MultiText]:
    row = conn.execute(stmt.Get_event_by_id, (event_id,)).fetchone()
    if row is None:
        err = MultiText(
            cn=f"找不到此事件: {event_id}", en=f"Event Not Found: {event_id}"
        )
        return Err(err)

    return Ok(Event(dict(row)))


def get_last_event(conn: Conn) -> Result[Event, MultiText]:
    match get_recent_events(conn, 1):
        case Err(err):
            return Err(err)
        case Ok(events):
            return Ok(events[0])
        case _:
            raise UnknownReturn


def count_events_range(conn: Conn, start: int, end: int) -> int:
    row = conn.execute(
        stmt.Count_events_range, dict(start=start, end=end)
    ).fetchone()
    return row[0]


def get_recent_events(conn: Conn, n: int) -> Result[list[Event], MultiText]:
    rows = conn.execute(stmt.Get_recent_events, (n,)).fetchall()
    if not rows:
        err = MultiText(
            cn="没有任何事件数据，可使用 'tt start TASK' 启动一个事件。",
            en="No event. Try 'tt start TASK' to make an event.",
        )
        return Err(err)

    events = [Event(dict(row)) for row in rows]
    return Ok(events)


def get_dates(date: str, d_or_m: str) -> Result[tuple[int, int], MultiText]:
    """检查日期格式是否符合要求。如果格式正式，则返回 Ok((start, end))"""
    err1 = MultiText(
        cn=f"日期格式错误: {date}  正确示范: 2022-05-01",
        en=f"Wrong date: {date}  A correct example: 2022-05-01",
    )
    err2 = MultiText(
        cn=f"日期格式错误: {date}  正确示范: 2022-05",
        en=f"Wrong date: {date}  A correct example: 2022-05",
    )
    if d_or_m == "day" and len(date) != 10:
        return Err(err1)
    if d_or_m == "month" and len(date) != 7:
        return Err(err2)

    try:
        start = arrow.get(date)
        end = start.shift(days=1) if d_or_m == "day" else start.shift(months=1)
    except arrow.parser.ParserError:
        err = err1 if d_or_m == "day" else err2
        return Err(err)

    return Ok((start.int_timestamp, end.int_timestamp))


def get_events_by_date(
    conn: Conn, date: str, d_or_m: str
) -> Result[list[Event], MultiText]:
    match get_dates(date, d_or_m):
        case Err(err):
            return Err(err)
        case Ok((start, end)):
            rows = conn.execute(
                stmt.Get_events_by_date, dict(start=start, end=end)
            ).fetchall()
            events = [Event(dict(row)) for row in rows]
            return Ok(events)
        case _:
            raise UnknownReturn


def update_laps(conn: Conn, event: Event) -> None:
    data = event.to_dict()
    conn_update(
        conn,
        stmt.Update_laps,
        dict(
            status=data["status"],
            laps=data["laps"],
            work=data["work"],
            id=data["id"],
        ),
    ).unwrap()


def delete_event(conn: Conn, event_id: str) -> None:
    conn_update(conn, stmt.Delete_event, (event_id,)).unwrap()
