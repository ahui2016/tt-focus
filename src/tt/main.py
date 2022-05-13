import os
import click
import sqlite3
from typing import Final, Callable
from pathlib import Path
import shutil

from . import (
    db,
    util,
    __version__,
    __package_name__,
)
from .model import MultiText


db.ensure_cfg_file()
app_cfg = db.load_app_cfg()
db_path: Final = app_cfg["db_path"]
lang: Final = app_cfg["lang"]


def connect() -> sqlite3.Connection:
    return db.connect(db_path)


def execute(func: Callable, *args):
    with connect() as conn:
        return func(conn, *args)


config = execute(db.get_cfg).unwrap()

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def show_info(ctx, _, value):
    if not value or ctx.resilient_parsing:
        return
    print()
    print(f" [tt-focus] {__file__}")
    print(f"  [version] {__version__}")
    with connect() as conn:
        util.show_cfg(conn, app_cfg, config)
    ctx.exit()


help_info = MultiText(
    cn="显示关于本软件的一些有用信息。", en="Show information about tt-focus."
)


@click.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.version_option(
    __version__,
    "-v",
    "-V",
    "--version",
    package_name=__package_name__,
    message="%(prog)s version: %(version)s",
)
@click.option(
    "-i",
    "--info",
    is_flag=True,
    help=help_info[lang],  # type: ignore
    expose_value=False,
    callback=show_info,
)
@click.pass_context
def cli(ctx: click.Context):
    """tt-focus: command-line Time Tracker.

    命令行时间记录器，帮助你集中注意力。

    https://pypi.org/project/tt-focus/
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()


# 以上是主命令
############
# 以下是子命令


help_set_db_folder = MultiText(
    cn="指定一个文件夹，用于保存数据库文件(tt-focus.db)。",
    en="Specify a folder for the database (tt-focus.db).",
)


def update_db_path(new_db_path: Path, success: MultiText):
    app_cfg["db_path"] = new_db_path.resolve().__str__()
    db.write_cfg_file(app_cfg)
    print(success[lang])  # type: ignore


def change_db_path(new_db_path: Path):
    success = MultiText(
        cn=f"数据库文件已更改为 {new_db_path}\n注意，旧数据库未删除: {db_path}",
        en=f"Now using file {new_db_path}\n"
        + f"The old database remains: {db_path}",
    )
    update_db_path(new_db_path, success)


def move_db_file(new_db_path: Path):
    success = MultiText(
        cn=f"数据库文件已移动到 {new_db_path}",
        en=f"The database file is moved to {new_db_path}",
    )
    shutil.copyfile(db_path, new_db_path)
    os.remove(db_path)
    update_db_path(new_db_path, success)


def set_db_folder(db_folder: str):
    new_db_path = Path(db_folder).joinpath(db.DB_Filename)

    if new_db_path.exists():
        # 无变化
        if new_db_path.samefile(db_path):
            print(f"[database]: {db_path}")
            return

        # 新文件夹含有 tt-focus.db, 则认为这是新数据库文件。
        change_db_path(new_db_path)
        return

    # 新文件夹中没有 tt-focus.db, 则移动 tt-focus.db 到新文件夹。
    move_db_file(new_db_path)


help_text = MultiText(
    cn="更改 tt-focus 的设置，或更改任务/事件的属性。",
    en="Change settings of tt-focus, or properties of a task/event.",
)


@cli.command(context_settings=CONTEXT_SETTINGS, help=help_text[lang], name="set")  # type: ignore
@click.option(
    "language",
    "-lang",
    help="Set language (语言) -> cn: 中文, en: English",
    type=click.Choice(["cn", "en"]),
)
@click.option(
    "db_folder",
    "-db",
    "--db-folder",
    type=click.Path(exists=True, file_okay=False),
    help=help_set_db_folder[lang],  # type: ignore
)
@click.pass_context
def set_command(ctx: click.Context, language: str, db_folder: str):
    """Change settings of tt-focus, or properties of a task/event.

    更改 tt-focus 的设置，或更改任务/事件的属性。
    """
    if language:
        app_cfg["lang"] = language
        db.write_cfg_file(app_cfg)
        msg = MultiText(cn=" [语言] cn (中文)", en=" [language] en")
        print(msg[language])  # type: ignore
        ctx.exit()

    if db_folder:
        set_db_folder(db_folder)
        ctx.exit()
