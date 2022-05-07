import arrow
import sqlite3
from . import db
from .model import (
    Config,
    AppConfig,
)


Conn = sqlite3.Connection


def show_cfg_cn(app_cfg: AppConfig, cfg: Config):
    print()
    print(f"        [语言] {app_cfg['lang']}")
    print(f"  [数据库文件] {app_cfg['db_path']}")
    print(f"[工作时间下限] {cfg['split_min']} 分钟")
    print(f"[休息时间下限] {cfg['pause_min']} 分钟")
    print(f"[休息时间上限] {cfg['pause_max']} 分钟")
    print()
    print("* 关于时间上下限，请看 github.com/ahui2016/tt-focus 的说明。\n")


def show_cfg_en(app_cfg: AppConfig, cfg: Config):
    print(f" [language] {app_cfg['lang']}")
    print(f" [database] {app_cfg['db_path']}")
    print(f"[split min] {cfg['split_min']} minutes")
    print(f"[pause min] {cfg['pause_min']} minutes")
    print(f"[pause max] {cfg['pause_max']} minutes")
    print()
    print("* More about 'min' and 'max': github.com/ahui2016/tt-focus\n")


def show_cfg(conn: Conn, app_cfg: AppConfig, cfg: Config | None = None):
    if not cfg:
        cfg = db.get_cfg(conn).unwrap()

    if app_cfg["lang"] == "cn":
        show_cfg_cn(app_cfg, cfg)
    else:
        show_cfg_en(app_cfg, cfg)
