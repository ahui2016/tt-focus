import sqlite3
from . import db
from .model import Config, AppConfig, Task, MultiText


Conn = sqlite3.Connection


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
        print(no_task[lang])  # type: ignore
        return

    print(header[lang])  # type: ignore
    for task in tasks:
        print(f"* {task}")
    print()
