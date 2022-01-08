import arrow
import click
from typing import cast

from simpletodo.model import (
    ErrMsg,
    Repeat,
    TodoStatus,
    new_todoitem,
    now,
)
from simpletodo.util import (
    db_path,
    ensure_db_file,
    load_db,
    print_donelist,
    print_repeatlist,
    print_todolist,
    split_db,
    stop_schedule,
    update_db,
    validate_n,
    make_schedule,
    update_schedules,
)
from . import (
    __version__,
    __package_name__,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


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


def dump(ctx: click.Context, param, value):
    if not value or ctx.resilient_parsing:
        return
    with open(db_path, "rb") as f:
        click.echo(f.read())
    ctx.exit()


@click.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.version_option(
    __version__,
    "-V",
    "--version",
    package_name=__package_name__,
    message="%(prog)s version: %(version)s",
)
@click.option(
    "-w",
    "--where",
    is_flag=True,
    help="Show locations about simple-todo.",
    expose_value=False,
    callback=show_where,
)
@click.option(
    "-d",
    "--dump",
    is_flag=True,
    help="Dump out the database (a json file).",
    expose_value=False,
    callback=dump,
)
@click.option(
    "all",
    "-a",
    "--all",
    is_flag=True,
    help="Show all items (including 'Completed' and 'Schedule').",
)
@click.pass_context
def cli(ctx, all):
    """simple-todo: Yet another command line TODO tool (命令行TODO工具)

    Just run 'todo' (with no options and no command) to list all items.

    https://pypi.org/project/simpletodo/
    """
    if ctx.invoked_subcommand is None:
        db = load_db()
        update_schedules(db)
        if not db["items"]:
            click.echo("There's no todo item.")
            click.echo("Use 'todo add ...' to add a todo item.")
            click.echo("Use 'todo --help' to get more information.")
            ctx.exit()

        todo_list, done_list, repeat_list = split_db(db)
        print_todolist(todo_list, all)

        if all:
            print_donelist(done_list)
            print_repeatlist(repeat_list)

        print()


# 以上是主命令
############
# 以下是子命令


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("event", nargs=-1, required=True)
@click.pass_context
def add(ctx, event):
    """Add an event to the todo list.

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


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=click.INT)
@click.pass_context
def done(ctx, n):
    """Mark the N'th item as 'Completed'.

    Example: todo done 1
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    status = db["items"][n - 1]["status"]
    repeat = db["items"][n - 1]["repeat"]
    if TodoStatus[status] is TodoStatus.Completed:
        click.echo("Warning: It was in the completed-list, nothing changes.")
    db["items"][n - 1]["status"] = TodoStatus.Completed.name
    if Repeat[repeat] is Repeat.Never:
        # 如果设置了重复提醒，则不修改 dtime (让它的值保持为零)
        db["items"][n - 1]["dtime"] = now()
    update_db(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=click.INT)
@click.pass_context
def delete(ctx, n):
    """Delete the N'th item. (It will be removed, not marked as completed)

    Example: todo delete 2
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)
    del db["items"][n - 1]
    update_db(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def clean(ctx):
    """Clear the completed list (delete all completed items)."""
    db = load_db()
    _, done_list, _ = split_db(db)
    for idx, _ in done_list:
        del db["items"][idx]
    update_db(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=click.INT)
@click.pass_context
def redo(ctx, n):
    """Mark the N'th item as 'Incomplete'.

    Example: todo redo 1
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    status = db["items"][n - 1]["status"]
    if TodoStatus[status] is TodoStatus.Incomplete:
        click.echo("Warning: It is in the incomplete-list, nothing changes.")

    db["items"][n - 1]["status"] = TodoStatus.Incomplete.name
    db["items"][n - 1]["ctime"] = now()
    db["items"][n - 1]["dtime"] = 0
    update_db(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=click.INT)
@click.option("every", "-every", "--every", help="Every 'week' or 'month' or 'year'.")
@click.option(
    "start",
    "-from",
    "--start-from",
    help="Example: -from 2021-04-01",
)
@click.option(
    "stop",
    "-stop",
    "--stop",
    is_flag=True,
    help="Stop repeating the event (删除指定事项的周期计划)",
)
@click.pass_context
def repeat(ctx, n, every, start: str, stop):
    """Set the N'th item to repeat every week/month/year.

    Example: todo repeat 1 -every month -from today
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    idx = n - 1
    item = db["items"][idx]

    # 优先处理 stop
    if stop:
        stop_schedule(db, idx, item, ctx)

    # 为了逻辑清晰，要求同时设置重复模式与起始时间
    if not every:
        click.echo("Error: Missing option '-every'.")
        click.echo("Try 'todo repeat --help' to get more information")
        ctx.exit()
    if not start:
        click.echo("Error: Missing option '-from'.")
        click.echo("Try 'todo repeat --help' to get more information")
        ctx.exit()

    today = arrow.now()
    match start.lower():
        case "today":
            s_date = today
        case "tomorrow":
            s_date = today.shift(days=1)
        case _:
            s_date = arrow.get(start)

    make_schedule(db, idx, every, s_date, ctx)
    update_db(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("args", type=(int, str))
@click.pass_context
def edit(ctx, args):
    """Edit the subject of an event.

    [ARGS] is a tuple[int, str].

    Example: todo edit 1 "Meet John on friday."
    """
    n, subject = args
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    subject = subject.strip()
    if not subject:
        click.echo(ctx.get_help())
        ctx.exit()

    db["items"][n - 1]["event"] = subject
    update_db(db)
    ctx.exit()


# 初始化
ensure_db_file()

if __name__ == "__main__":
    cli(obj={})
