import sqlite3
from datetime import timedelta
from typing import TypeAlias
import arrow
from result import Result, Err, Ok

from . import db, model
from .model import (
    Config,
    AppConfig,
    Task,
    MultiText,
    Event,
    EventStatus,
    OK,
    UnknownReturn,
    RecentItemsMax,
    Lap,
    LapName,
)

Conn: TypeAlias = sqlite3.Connection


def show_cfg_cn(app_cfg: AppConfig, cfg: Config):
    print()
    print(f"         语言: {app_cfg['lang']}")
    print(f"   数据库文件: {app_cfg['db_path']}")
    print(f" 工作时长下限: {cfg['split_min']} 分钟")
    print(f" 休息时长下限: {cfg['pause_min']} 分钟")
    print(f" 休息时长上限: {cfg['pause_max']} 分钟")
    print()


def show_cfg_en(app_cfg: AppConfig, cfg: Config):
    print(f"  [language] {app_cfg['lang']}")
    print(f"  [database] {app_cfg['db_path']}")
    print(f" [split min] {cfg['split_min']} minutes")
    print(f" [pause min] {cfg['pause_min']} minutes")
    print(f" [pause max] {cfg['pause_max']} minutes")
    print()


def show_cfg(conn: Conn, app_cfg: AppConfig, cfg: Config | None = None):
    if not cfg:
        cfg = db.get_cfg(conn).unwrap()

    if app_cfg["lang"] == "cn":
        show_cfg_cn(app_cfg, cfg)
    else:
        show_cfg_en(app_cfg, cfg)


def show_tasks(tasks: list[Task], lang: str) -> None:
    no_task = MultiText(
        cn="尚未添加任何任务类型，可使用 'tt add NAME' 添加任务类型。",
        en="There is no any task type. Use 'tt add NAME' to add a task.",
    )
    header = MultiText(cn="\n[任务类型列表]\n", en="\nTask types:\n")
    if not tasks:
        print(no_task.str(lang))
        return

    print(header.str(lang))
    for task in tasks:
        print(f"* {task}")
    print()


def check_last_event_stopped(conn: Conn) -> Result[str, MultiText]:
    """确保上一个事件已结束。"""
    r = db.get_last_event(conn)
    if r.is_err():
        return OK  # 唯一的错误是数据库中无事件

    event = r.unwrap()
    if event.status is not EventStatus.Stopped:
        err = MultiText(
            cn="不可启动新事件，因为上一个事件未结束 (可使用 'tt status' 查看状态)",
            en="Cannot make a new event. Try 'tt status' to get more information.",
        )
        return Err(err)

    return OK


def format_date(t: int) -> str:
    return arrow.get(t).to("local").format("YYYY-MM-DD")


def format_time(t: int) -> str:
    return arrow.get(t).to("local").format("HH:mm:ss")


def format_date_time(t: int) -> str:
    return arrow.get(t).to("local").format("YYYY-MM-DD HH:mm:ss")


def format_time_len(s: int) -> str:
    return str(timedelta(seconds=s))


def get_last_task(conn: Conn) -> Result[str, MultiText]:
    match db.get_last_event(conn):
        case Err(err):
            return Err(err)
        case Ok(event):
            task = db.get_task_by_id(conn, event.task_id).unwrap()
            return Ok(task.name)
        case _:
            raise UnknownReturn


def event_start(conn: Conn, name: str | None) -> MultiText:
    err = check_last_event_stopped(conn).err()
    if err is not None:
        return err

    if name is None:
        task = get_last_task(conn)
        if task.is_err():
            return task.unwrap_err()
        else:
            name = task.unwrap()

    r = db.get_task_by_name(conn, name)
    if r.is_err():
        return MultiText(
            cn=f"不存在任务类型: {name}, 可使用 'tt add {name}' 添加此任务类型。",
            en=f"Not Found: {name}. Try 'tt add {name}' to add it as a task type.",
        )

    t = r.unwrap()
    event = Event({"task_id": t.id})
    db.insert_event(conn, event)
    started = format_time(event.started)

    if t.alias:
        return MultiText(
            cn=f"事件 id:{event.id}, 任务: {t.name} ({t.alias}), 开始于 {started}",
            en=f"Event id:{event.id}, Task: {t.name} ({t.alias}), Started from {started}",
        )
    else:
        return MultiText(
            cn=f"事件 id:{event.id}, 任务: {t.name}, 开始于 {started}",
            en=f"Event id:{event.id}, Task: {t.name}, Started from {started}",
        )


def get_last_event(conn: Conn) -> Result[Event, MultiText]:
    match db.get_last_event(conn):
        case Err(err):
            return Err(err)
        case Ok(event):
            if event.status is EventStatus.Stopped:
                err = MultiText(
                    cn="当前无正在计时的事件，可使用 'tt start TASK' 启动一个事件。",
                    en="No running event. Try 'tt start TASK' to make an event.",
                )
                return Err(err)
            else:
                return Ok(event)
        case _:
            raise UnknownReturn


def check_command(op: str, status: EventStatus, lang: str) -> bool:
    """检查 op 与 status 是否匹配，不匹配则返回 True。"""
    alert = MultiText(
        cn=f"当前事件的状态是 {status.name}, 不可使用 {op} 命令。",
        en=f"The current event is '{status.name}', cannot use the '{op}' command.",
    )
    when_running = MultiText(
        cn="\n可使用: split/pause/stop",
        en="\nAvailable commands: split/pause/stop",
    )
    when_pausing = MultiText(
        cn="\n可使用: resume/stop", en="\nAvailable commands: resume/stop"
    )

    err = False
    if status is EventStatus.Running and op == "resume":
        err = True
        alert.append(when_running)
    elif status is EventStatus.Pausing and op == "pause":
        err = True
        alert.append(when_pausing)
    elif status is EventStatus.Pausing and op == "split":
        err = True
        alert.append(when_pausing)

    if err:
        print(alert.str(lang))
    return err


def event_operate(conn: Conn, cfg: Config, lang: str, op: str) -> Event | None:
    r = get_last_event(conn)
    if r.is_err():
        print(r.unwrap_err().str(lang))
        return None

    event: Event = r.unwrap()
    if check_command(op, event.status, lang):
        return None

    match op:
        case "split":
            event.split(cfg)
        case "pause":
            event.pause(cfg)
        case "resume":
            event.resume(cfg)
        case "stop":
            event.stop(cfg)
        case _:
            raise KeyError(f"Unknown operator: {op}")

    db.update_laps(conn, event)
    show_event_details(conn, event, lang)
    return event


def event_split(conn: Conn, cfg: Config, lang: str) -> None:
    event_operate(conn, cfg, lang, "split")


def event_pause(conn: Conn, cfg: Config, lang: str) -> None:
    event_operate(conn, cfg, lang, "pause")


def del_if_below_min(conn: Conn, cfg: Config, lang: str, event: Event) -> None:
    if event.work <= cfg["split_min"]:
        info = MultiText(
            cn="以上所示事件，由于总工作时长小于下限，已自动删除。\n",
            en="The event above is automatically deleted.\n",
        )
        print(info.str(lang))
        db.delete_event(conn, event.id)


def event_resume(conn: Conn, cfg: Config, lang: str) -> None:
    event = event_operate(conn, cfg, lang, "resume")
    if event is None:
        return

    if event.status is EventStatus.Stopped:
        del_if_below_min(conn, cfg, lang, event)
        info = MultiText(
            cn="以上所示事件休息时长大于上限，已自动结束，并自动启动了新事件。\n",
            en="The event above is automatically stopped, and an new event is started.\n",
        )
        print(info.str(lang))
        info = event_start(conn, None)
        print(info.str(lang))
        print()


def event_stop(conn: Conn, cfg: Config, lang: str) -> None:
    event = event_operate(conn, cfg, lang, "stop")
    if event:
        del_if_below_min(conn, cfg, lang, event)


def show_stopped_status(lang: str) -> None:
    info = MultiText(
        cn="当前无正在计时的事件，可使用 'tt list' 查看最近的事件。",
        en="No event running. Try 'tt list' to list out recent events.",
    )
    print(info.str(lang))


def show_event_details(conn: Conn, event: Event, lang: str) -> None:
    task = db.get_task_by_id(conn, event.task_id).unwrap()
    date = format_date(event.started)
    status = f"(id:{event.id}) {date} **{event.status.name.lower()}**"
    start = format_time(event.started)
    now = format_time(model.now())
    work = format_time_len(event.work)

    header = MultiText(
        cn=f"任务 | {task}\n事件 | {status}", en=f"Task | {task}\nEvent| {status}"
    )
    if event.notes:
        notes = MultiText(
            cn=f"\n备注 | {event.notes} ", en=f"\nNotes| {event.notes}"
        )
        header.append(notes)

    total = MultiText(
        cn=f"合计   {start} -> {now} [{work}]",
        en=f"total  {start} -> {now} [{work}]",
    )
    print(
        f"\n{header.str(lang)}\n\n{total.str(lang)}\n-------------------------------------"
    )

    for lap in event.laps:
        start = format_time(lap[1])
        link_mark = ".." if lap[2] == 0 else "->"
        end = model.now() if lap[2] == 0 else lap[2]
        length = format_time_len(end - lap[1])
        if lap[0] == LapName.Split.name:
            print(
                f"{lap[0]}  {start} {link_mark} {format_time(end)} [{length}]"
            )
        else:
            print(f"{lap[0]}  [{length}]")
    print()

    footer_running = MultiText(
        cn="可接受命令: pause/split/stop", en="Waiting for pause/split/stop"
    )
    footer_pausing = MultiText(
        cn="可接受命令: resume/stop", en="Waiting for resume/stop"
    )
    footer_stopped = MultiText(
        cn=f"该事件已结束。生产效率/集中力: {event.productivity()}",
        en=f"The event has stopped. Productivity: {event.productivity()}",
    )
    match event.status:
        case EventStatus.Running:
            print(footer_running.str(lang))
        case EventStatus.Pausing:
            print(footer_pausing.str(lang))
        case EventStatus.Stopped:
            print(footer_stopped.str(lang))
    print()


def show_status(conn: Conn, lang: str, event_id: str | None = None) -> None:
    if event_id is None:
        r = db.get_last_event(conn)
    else:
        r = db.get_event_by_id(conn, event_id)
    match r:
        case Err(err):
            print(err.str(lang))
        case Ok(event):
            if event_id is None and event.status is EventStatus.Stopped:
                show_stopped_status(lang)
            else:
                show_event_details(conn, event, lang)


def set_event_notes(
    conn: Conn, lang: str, notes: str, event_id: str | None
) -> None:
    if event_id is None:
        r = db.get_last_event(conn)
    else:
        r = db.get_event_by_id(conn, event_id)
    match r:
        case Err(err):
            print(err.str(lang))
        case Ok(event):
            notes = notes.strip()
            db.set_event_notes(conn, notes, event.id)
            if event.notes:
                if notes:
                    print(f"{event.notes}\n\n->\n\n{notes}")
                else:
                    info = MultiText(
                        cn=f"已删除事件 (id:{event.id}) 的备注: {event.notes}",
                        en=f"Notes of event (id:{event.id}) is removed: {event.notes}",
                    )
                    print(info.str(lang))
            else:
                print("OK.")


def show_events(conn: Conn, events: list[Event], verbose: bool) -> None:
    for e in events:
        start = format_date(e.started)
        work = format_time_len(e.work)
        t = db.get_task_by_id(conn, e.task_id).unwrap()

        if e.status is EventStatus.Running:
            status = " **running**"
        elif e.status is EventStatus.Pausing:
            status = " **pausing**"
        else:
            status = f" {e.productivity()}"

        alias = f" ({t.alias})" if t.alias else ""
        notes = f" Notes: {e.notes}" if e.notes else ""

        if verbose:
            start = format_date_time(e.started)
            end_time = e.laps[-1][2]
            end = (
                format_time(end_time) if end_time else format_time(model.now())
            )
            print(f"Event: {e.id}, {start} -> {end} [{work}]{status}")
            print(f"Task : {t.name}{alias}{notes}\n")
        else:
            print(f"* id: {e.id}, {t.name}{alias}, {start} [{work}]{status}")

    if not verbose:
        print()


def show_recent_events(conn: Conn, lang: str, verbose: bool = False) -> None:
    r = db.get_recent_events(conn, RecentItemsMax)
    if r.is_err():
        print(r.unwrap_err().str(lang))
        return

    events = r.unwrap()
    if not events:
        info = MultiText(
            cn="没有任何事件记录。可使用 'tt start TASK' 启动一个事件。",
            en="There is no event. Try 'tt start TASK' to make an event.",
        )
        print(info.str(lang))
        return

    header = MultiText(cn="\n[最近的事件]\n", en="\nRecent events:\n")
    print(header.str(lang))
    show_events(conn, events, verbose)


def show_events_by_date(
    conn: Conn, date: str, d_or_m: str, lang: str, verbose: bool = False
) -> None:
    r = db.get_events_by_date(conn, date, d_or_m)
    if r.is_err():
        print(r.unwrap_err().str(lang))
        return

    events = r.unwrap()
    if not events:
        info = MultiText(
            cn=f"该日期没有事件: {date}", en=f"There is no event on {date}"
        )
        print(info.str(lang))
        return

    print()
    show_events(conn, events, verbose)


def show_events_year_count(conn: Conn, year: str, lang: str) -> None:
    r = db.events_year_count(conn, year)
    if r.is_err():
        print(r.unwrap_err().str(lang))
        return

    date_count = r.unwrap()
    if len(date_count) == 0:
        info = MultiText(
            cn=f"{year} 年没有事件。", en=f"There is no event in the year {year}"
        )
        print(info.str(lang))
        return

    print()
    for month, n in date_count:
        print(f"* {month}: {n}")
    print()


def sum_event_work(laps: tuple[Lap, ...]) -> int:
    work = 0
    for lap in laps:
        if LapName[lap[0]] == LapName.Split:
            work += lap[-1]
    return work


def set_last_work(conn: Conn, n: int, event_id: str | None, lang: str) -> None:
    """修改指定事件的最后一个小节的工作时长"""
    not_stop = MultiText(
        cn="该事件尚未结束，不能修改未结束的事件。",
        en="Cannot modify. The event has not stopped yet.",
    )
    if event_id is None:
        r = db.get_last_event(conn)
    else:
        r = db.get_event_by_id(conn, event_id)
    match r:
        case Err(err):
            print(err.str(lang))
        case Ok(event):
            if event.status is not EventStatus.Stopped:
                print(not_stop.str(lang))
                return

            # 只要是已结束的事件，它的最后一个小节就一定是工作小节。
            last_lap = event.laps[-1]
            last_work = last_lap[-1]
            work = n * 60
            last_lap = (last_lap[0], last_lap[1], last_lap[1] + work, work)
            event.laps = event.laps[:-1] + (last_lap,)
            event.work = sum_event_work(event.laps)
            db.update_laps(conn, event)
            show_event_details(conn, event, lang)
            print(
                f"{format_time_len(last_work)} => {format_time_len(event.laps[-1][-1])}\n"
            )


def merge_events(
    conn: Conn, lang: str, preview: bool, *event_ids: str
) -> None:
    event_ids = tuple(set(event_ids))
    info = MultiText(
        cn=f"\n即将合并事件: {event_ids}", en=f"\nEvents to be merged: {event_ids}"
    )
    print(info.str(lang))

    if len(event_ids) < 2:
        err = MultiText(
            cn="必须至少指定两个事件。", en="Not enough events to merge (at least two)."
        )
        print(err.str(lang))
        return

    events: list[Event] = []
    for e_id in event_ids:
        match db.get_event_by_id(conn, e_id):
            case Err(err):
                print(err.str(lang))
                return
            case Ok(event):
                events.append(event)

    err1 = MultiText(
        cn="这些事件的任务类型不相同。\n", en="These events have different task type.\n"
    )
    err2 = MultiText(
        cn="这些事件并不是同一天的事件。\n",
        en="These events did not start on the same day.\n",
    )
    err3 = MultiText(
        cn="不可合并未结束的事件。\n", en="Cannot merge. The event has not stopped yet.\n"
    )
    err4 = MultiText(
        cn="这些事件并非相邻的事件。\n",
        en="These events are not adjacent to each other.\n",
    )

    events.sort(key=lambda x: x.started)
    start_day = format_date(events[0].started)
    task_id = events[0].task_id

    # 检查任务类型是否相同、是否同一天、是否未结束
    for e in events[1:]:
        if e.task_id != task_id:
            print(err1.str(lang))
            return
        if format_date(e.started) != start_day:
            print(err2.str(lang))
            return
        if e.status is not EventStatus.Stopped:
            print(err3.str(lang))
            return

    # 检查是否相邻
    count = db.count_events_range(conn, events[0].started, events[-1].started)
    if len(events) != count:
        print(err4.str(lang))
        return

    # 合并
    laps = events[0].laps
    for e in events[1:]:
        laps += e.laps
        events[0].work += e.work
        events[0].notes += " " + e.notes

    events[0].laps = laps

    # 更新数据库
    if not preview:
        db.update_laps(conn, events[0])
        for e in events[1:]:
            db.delete_event(conn, e.id)

    # 显示结果
    show_event_details(conn, events[0], lang)
    info = MultiText(
        cn="\n以上是预估合并结果，并未真正执行合并。\n",
        en="Shown above is an estimate, did not actually merge.\n",
    )
    if preview:
        print(info.str(lang))


def get_task_by_name(conn: Conn, name: str) -> Result[Task, MultiText]:
    match db.get_task_by_name(conn, name):
        case Err(_):
            err = MultiText(cn=f"找不到任务类型: {name}", en=f"Not Found: {name}")
            return Err(err)
        case Ok(task):
            return Ok(task)
        case _:
            raise UnknownReturn


def set_task_alias(conn: Conn, alias: str, name: str, lang: str) -> None:
    match db.get_task_by_name(conn, name):
        case Err(_):
            err = MultiText(cn=f"找不到任务类型: {name}", en=f"Not Found: {name}")
            print(err.str(lang))
        case Ok(task):
            db.set_task_alias(conn, alias, name)
            print(f"Task: {name} ({task.alias}) -> {name} ({alias})")


def set_task_name(conn: Conn, new_name: str, old_name: str, lang: str) -> None:
    match db.get_task_by_name(conn, old_name):
        case Err(err):
            print(err.str(lang))
        case Ok(task):
            db.set_task_name(conn, new_name, old_name)
            print(
                f"Task: {old_name} ({task.alias}) -> {new_name} ({task.alias})"
            )
