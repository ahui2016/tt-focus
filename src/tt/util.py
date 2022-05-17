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
)

Conn: TypeAlias = sqlite3.Connection


def show_cfg_cn(app_cfg: AppConfig, cfg: Config):
    print()
    print(f"         语言: {app_cfg['lang']}")
    print(f"   数据库文件: {app_cfg['db_path']}")
    print(f" 工作时间下限: {cfg['split_min']} 分钟")
    print(f" 休息时间下限: {cfg['pause_min']} 分钟")
    print(f" 休息时间上限: {cfg['pause_max']} 分钟")
    print()
    print("* 使用命令 'tt help min' 或 'tt help max' 可查看关于时间上下限的说明。\n")


def show_cfg_en(app_cfg: AppConfig, cfg: Config):
    print(f"  [language] {app_cfg['lang']}")
    print(f"  [database] {app_cfg['db_path']}")
    print(f" [split min] {cfg['split_min']} minutes")
    print(f" [pause min] {cfg['pause_min']} minutes")
    print(f" [pause max] {cfg['pause_max']} minutes")
    print()
    print(
        "* Try 'tt help min' or 'tt help max' to read more about time limits."
        "\n"
    )


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
    header = MultiText(cn="\n[任务类型列表]\n", en="\n[Task types]\n")
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
                    en="No running event. Try 'tt start Task' to make an event.",
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
    err = False
    if status is EventStatus.Running and op == "resume":
        err = True
    elif status is EventStatus.Pausing and op == "pause":
        err = True
    elif status is EventStatus.Pausing and op == "split":
        err = True

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
    show_running_status(conn, event, None, lang)
    return event


def event_split(conn: Conn, cfg: Config, lang: str) -> None:
    event_operate(conn, cfg, lang, "split")


def event_pause(conn: Conn, cfg: Config, lang: str) -> None:
    event_operate(conn, cfg, lang, "pause")


def del_if_below_min(conn: Conn, cfg: Config, lang: str, event: Event) -> None:
    if event.work <= cfg["split_min"]:
        info = MultiText(
            cn="以上所示事件，由于总工作时长小于下限，已自动删除。\n"
            + "可使用命令 'tt help min' 查看关于时长下限的说明。\n",
            en="The event above is automatically deleted.\n"
            + "Run 'tt help min' to get more information.\n",
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
            cn="以上所示事件休息时长大于上限，已自动结束，并自动启动了新事件。\n"
            + "可使用命令 'tt help max' 查看关于时长上限的说明。\n",
            en="The event above is automatically stopped, and an new event is started.\n"
            + "Run 'tt help max' to get more information.\n",
        )
        print(info.str(lang))
        info = event_start(conn, None)
        print(info.str(lang))


def event_stop(conn: Conn, cfg: Config, lang: str) -> None:
    event = event_operate(conn, cfg, lang, "stop")
    if event:
        del_if_below_min(conn, cfg, lang, event)


def show_stopped_status(lang: str) -> None:
    info = MultiText(
        cn="当前无正在计时的事件，可使用 'tt list -e' 查看最近的事件。",
        en="No event running. Try 'tt list -e' to list out recent events.",
    )
    print(info.str(lang))


def show_running_status(
    conn: Conn, event: Event, task: Task | None, lang: str
) -> None:
    if task is None:
        task = db.get_task_by_id(conn, event.task_id).unwrap()
    date = format_date(event.started)
    status = f"(id:{event.id}) {date} **{event.status.name.lower()}**"
    start = format_time(event.started)
    now = format_time(model.now())
    work = format_time_len(event.work)

    header = MultiText(
        cn=f"任务 | {task}\n事件 | {status}", en=f"Task | {task}\nEvent| {status}"
    )
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
        print(f"{lap[0]}  {start} {link_mark} {format_time(end)} [{length}]")
    print()

    footer_running = MultiText(
        cn="可接受命令: pause/split/stop", en="Waiting for pause/split/stop"
    )
    footer_pausing = MultiText(
        cn="可接受命令: resume/stop", en="Waiting for resume/stop"
    )
    footer_stopped = MultiText(cn="该事件已结束。", en="The event above has stopped.")
    match event.status:
        case EventStatus.Running:
            print(footer_running.str(lang))
        case EventStatus.Pausing:
            print(footer_pausing.str(lang))
        case EventStatus.Stopped:
            print(footer_stopped.str(lang))
    print()


def show_status(conn: Conn, lang: str) -> None:
    match db.get_last_event(conn):
        case Err(err):
            print(err.str(lang))
        case Ok(event):
            task = db.get_task_by_id(conn, event.task_id).unwrap()
            if event.status is EventStatus.Stopped:
                show_stopped_status(lang)
            else:
                show_running_status(conn, event, task, lang)


def show_recent_events(conn: Conn, lang: str) -> None:
    r = db.get_recent_events(conn, RecentItemsMax)
    if r.is_err():
        print(r.unwrap_err().str(lang))
        return

    print()
    events = r.unwrap()
    for e in events:
        start = format_date(e.started)
        work = format_time_len(e.work)
        t = db.get_task_by_id(conn, e.task_id).unwrap()
        if t.alias:
            print(
                f"* id: {e.id}, {t.name} ({t.alias}), {start} [{work}]",
            )
        else:
            print(
                f"* id: {e.id}, {t.name}, {start} [{work}]",
            )
    print()
