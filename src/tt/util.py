import arrow
import sqlite3
from . import db
from .model import (
    Config,
    AppConfig,
)


Conn = sqlite3.Connection


def show_cfg(conn: Conn, app_cfg: AppConfig, cfg: Config | None = None):
    if not cfg:
        cfg = db.get_cfg(conn).unwrap()
    if app_cfg["lang"] == "cn":
        show_cfg_cn()
    else:
        show_cfg_en()
