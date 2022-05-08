import click
import sqlite3
from typing import Final, Callable

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


def set_db_path(ctx, _, value):
    if not value or ctx.resilient_parsing:
        return
    app_cfg["db_path"] = value
    db.write_cfg_file(app_cfg)
    ctx.exit()


def show_info(ctx, _, value):
    if not value or ctx.resilient_parsing:
        return
    print()
    print(f" [tt-focus] {__file__}")
    print(f"  [version] {__version__}")
    with connect() as conn:
        util.show_cfg(conn, app_cfg, config)
    ctx.exit()


help_set_db_folder = MultiText(
    cn="指定一个文件夹，用于保存数据库文件(tt-focus.db)。",
    en="Specify a folder for the database (tt-focus.db).",
)
help_info = MultiText(
    cn="显示关于本软件的一些有用信息。", en="Show informations about tt-focus."
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
    help=help_info[lang],
    expose_value=False,
    callback=show_info,
)
@click.option(
    "--set-db-folder",
    help=help_set_db_folder[lang],
    expose_value=False,
    callback=set_db_path,
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


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "lang",
    "-lang",
    help="Set language (语言) -> cn: 中文, en: English",
    type=click.Choice(["cn", "en"]),
)
@click.pass_context
def set(ctx, lang: str):
    """Change settings of tt-focus, or properties of a task/event.

    更改 tt-focus 的设置，或更改任务/事件的属性。
    """
    if lang:
        app_cfg["lang"] = lang
        db.write_cfg_file(app_cfg)
        msg = MultiText(cn=" [语言] cn (中文)", en=" [language] en")
        print(msg[lang])
        ctx.exit()
