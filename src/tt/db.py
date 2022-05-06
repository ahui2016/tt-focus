import sqlite3
import msgpack
from pathlib import Path
from appdirs import AppDirs
from result import Err, Ok, Result
from typing import Final, Iterable
from . import stmt
from .model import (
    Config,
    ConfigName,
    AppConfig,
    new_cfg_from,
)


Conn: Final = sqlite3.Connection

NoResultError: Final = "db-query-no-result"
OK: Final = Ok("OK")

AppCfgFilename: Final = "tt-focus.cfg"
DB_Filename: Final = "tt-focus.db"

app_dirs = AppDirs("tt-focus", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
app_cfg_path = app_config_dir.joinpath(AppCfgFilename)
default_db_path = app_config_dir.joinpath(DB_Filename)


def write_cfg_file(cfg: AppConfig) -> None:
    app_cfg_path.write_bytes(msgpack.packb(cfg))


def ensure_cfg_file() -> None:
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if not app_cfg_path.exists():
        default_cfg = AppConfig(lang='en', db_path=default_db_path.__str__())
        write_cfg_file(default_cfg)


def load_app_cfg() -> AppConfig:
    return new_cfg_from(app_cfg_path.read_bytes())


def connect(db_path: str) -> Conn:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(stmt.Enable_foreign_keys)
    return conn


def connUpdate(
    conn: Conn, query: str, param: Iterable, many: bool = False
) -> Result[int, str]:
    if many:
        n = conn.executemany(query, param).rowcount
    else:
        n = conn.execute(query, param).rowcount
    if n <= 0:
        return Err("sqlite row affected = 0")
    return Ok(n)


def get_cfg(conn: Conn) -> Result[Config, str]:
    row = conn.execute(stmt.Get_metadata, (ConfigName,)).fetchone()
    if row is None:
        return Err(NoResultError)
    return Ok(new_cfg_from(row[0]))


def update_cfg(conn: Conn, cfg: Config) -> None:
    connUpdate(
        conn,
        stmt.Update_metadata,
        {"name": ConfigName, "value": cfg.pack()},
    ).unwrap()
