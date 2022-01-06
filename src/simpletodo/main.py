from typing import cast
import click

from simpletodo.model import ErrMsg, NotFound, TodoList, TodoStatus, new_todoitem, now
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
            click.echo("Use 'todo --help' to get more information.")
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
    """Adds an event to the todo list.

    [EVENT] is a string describing a todo item.

    Example: todo add Buy more beer.
    """
    event = cast(tuple[str], event)
    subject = " ".join(event).strip()
    if not subject:
        click.echo(ctx.get_help())
        ctx.exit()

    db = load_db()
    db["items"].insert(0, new_todoitem(subject))
    update_db(db)
    ctx.exit()


@cli.command()
@click.argument("n", nargs=1, type=click.INT)
@click.pass_context
def done(ctx, n):
    """Marks the N'th item as 'Completed'.

    Example: todo done 1
    """
    db = load_db()
    todo_list, _, _ = split_db(db)
    err = validate_todolist(todo_list, n)
    if err == NotFound:
        click.echo("No item in the todo list.")
        click.echo("Try 'todo --help' to get more information.")
        ctx.exit()
    check(ctx, err)

    i = db["items"].index(todo_list[n - 1])
    db["items"][i]["status"] = TodoStatus.Completed.name
    db["items"][i]["dtime"] = now()
    update_db(db)
    ctx.exit()


@cli.command()
@click.argument("n", nargs=1, type=click.INT)
@click.pass_context
def delete(ctx, n):
    """Deletes the N'th item. (It will be removed, not marked as completed)

    This command deletes an item in the todo list.
    Use 'todo clean' to clear the completed list.

    Example: todo delete 2
    """
    db = load_db()
    todo_list, _, _ = split_db(db)
    err = validate_todolist(todo_list, n)
    if err == NotFound:
        click.echo("No item in the todo list.")
        click.echo("Try 'todo delete --help' to get more information.")
        ctx.exit()
    check(ctx, err)
    db["items"].remove(todo_list[n - 1])
    update_db(db)
    ctx.exit()


@cli.command()
@click.pass_context
def clean(ctx):
    """Clears the completed list (removes all items in it)."""
    db = load_db()
    _, done_list, _ = split_db(db)
    for item in done_list:
        db["items"].remove(item)
    update_db(db)
    ctx.exit()


@cli.command()
@click.argument("n", nargs=1, type=click.INT)
@click.pass_context
def redo(ctx, n):
    """Marks the N'th item as 'Incomplete'.

    Example: todo redo 1
    """
    db = load_db()
    _, done_list, _ = split_db(db)
    err = validate_todolist(done_list, n)
    if err == NotFound:
        click.echo("No item in the completed list.")
        ctx.exit()
    check(ctx, err)

    i = db["items"].index(done_list[n - 1])
    db["items"][i]["status"] = TodoStatus.Incomplete.name
    db["items"][i]["ctime"] = now()
    db["items"][i]["dtime"] = 0
    update_db(db)
    ctx.exit()


def validate_todolist(l: TodoList, n: int) -> ErrMsg:
    if n < 1:
        return "Please input a number bigger than zero."

    size = len(l)
    if not size:
        return NotFound
    if n > size:
        if size == 1:
            return "There is only 1 item."
        else:
            return f"There are only {size} items"
    return ""


# 初始化
ensure_db_file()

if __name__ == "__main__":
    cli(obj={})
