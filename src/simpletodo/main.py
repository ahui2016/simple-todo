from typing import cast
import click

from simpletodo.model import ErrMsg, TodoStatus, new_todoitem, now
from simpletodo.util import (
    db_path,
    ensure_db_file,
    load_db,
    print_donelist,
    print_todolist,
    split_db,
    update_db,
)
from . import (
    __version__,
    __package_name__,
)


def check(ctx: click.Context, err: ErrMsg) -> None:
    """检查 err, 有错误则打印并终止程序，无错误则什么都不用做。"""
    if err:
        click.echo(f"Error: {err}")
        ctx.exit()


def show_where(ctx: click.Context, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"[todo] {__file__}")
    click.echo(f"[database] {db_path}")
    ctx.exit()


@click.group(invoke_without_command=True)
@click.version_option(
    __version__,
    "-V",
    "--version",
    package_name=__package_name__,
    message="%(prog)s version: %(version)s",
)
@click.option(
    "-W",
    "--where",
    is_flag=True,
    is_eager=True,
    help="Show locations about simple-todo.",
    expose_value=False,
    callback=show_where,
)
@click.pass_context
def cli(ctx):
    """simple-todo: Yet another command line TODO tool (命令行TODO工具)

    Just run 'todo' (with no options and no command) to list all items.
    """
    if ctx.invoked_subcommand is None:
        db = load_db()
        if not db["items"]:
            click.echo("There's no todo items.")
            click.echo("Use 'todo add ...' to add a todo item.")
            click.echo("Use 'todo --help' to get help.")
            ctx.exit()

        todo_list, done_list, _ = split_db(db)
        print_todolist(todo_list)
        print_donelist(done_list)
        print()


# 以上是主命令
############
# 以下是子命令


@cli.command()
@click.argument("event", nargs=-1, is_eager=True)
@click.pass_context
def add(ctx, event):
    """Add an event.

    [EVENT] is a string describing a todo item.
    Example: todo Buy more beer.
    """
    event = cast(tuple[str], event)
    subject = " ".join(event)
    db = load_db()
    db["items"].insert(0, new_todoitem(subject))
    update_db(db)
    ctx.exit()


@cli.command()
@click.argument('n', nargs=1, type=click.INT)
@click.pass_context
def done(ctx, n):
    """Mark the [N] item as 'Completed'

    Example: todo done 1
    """
    if n < 1:
        click.echo("Please input a number bigger than zero.")
        ctx.exit()

    db = load_db()
    todo_list, _, _ = split_db(db)
    size = len(todo_list)
    if n > size:
        if size == 1:
            msg = "There is only 1 item."
        else:
            msg = f"There are only {size} items"
        click.echo(msg)
        ctx.exit()
    
    i = db["items"].index(todo_list[n-1])
    db["items"][i]["status"] = TodoStatus.Completed.name
    db["items"][i]["dtime"] = now()
    update_db(db)


# 初始化
ensure_db_file()

if __name__ == "__main__":
    cli(obj={})
