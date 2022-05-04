import click
import sqlite3
from typing import Final

from . import (
    db,
    __version__,
    __package_name__,
)


app_cfg = db.load_app_cfg()


def connect() -> sqlite3.Connection:
    return db.connect(app_cfg["db_path"])


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


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


