import arrow
import click
from typing import cast

from simpletodo.model import (
    DB,
    ErrMsg,
    Repeat,
    TodoList,
    TodoStatus,
    new_todoitem,
    now,
)
from simpletodo.util import (
    DateFormat,
    db_path,
    ensure_db_file,
    load_db,
    print_donelist,
    print_repeatlist,
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
# @click.option(
#     ""
# )
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

        todo_list, done_list, repeat_list = split_db(db)
        print_todolist(todo_list)
        print_donelist(done_list)
        print_repeatlist(repeat_list)
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


@cli.command()
@click.argument("n", nargs=1, type=click.INT)
@click.pass_context
def delete(ctx, n):
    """Deletes the N'th item. (It will be removed, not marked as completed)

    Example: todo delete 2
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)
    del db["items"][n - 1]
    update_db(db)
    ctx.exit()


@cli.command()
@click.pass_context
def clean(ctx):
    """Clears the completed list (removes all items in it)."""
    db = load_db()
    _, done_list, _ = split_db(db)
    for idx, _ in done_list:
        del db["items"][idx]
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
    err = validate_n(db["items"], n)
    check(ctx, err)

    status = db["items"][n - 1]["status"]
    if TodoStatus[status] is TodoStatus.Incomplete:
        click.echo("Warning: It was in the incomplete-list, nothing changes.")

    db["items"][n - 1]["status"] = TodoStatus.Incomplete.name
    db["items"][n - 1]["ctime"] = now()
    db["items"][n - 1]["dtime"] = 0
    update_db(db)
    ctx.exit()


@cli.command()
@click.argument("n", nargs=1, type=click.INT)
@click.option(
    "every", "-every", "--every", help="Please input 'week' or 'month' or 'year'."
)
@click.option(
    "start",
    "-from",
    "--start-from",
    help="Please input a date. Example: -from 2021-04-01",
)
@click.option(
    "stop",
    "-stop",
    "--stop",
    is_flag=True,
    help="Stop repeating the event (删除指定项目的周期计划)",
)
@click.pass_context
def repeat(ctx, n, every, start:str, stop):
    """Sets the N'th item to repeat every week/month/year.

    It is set to repeat every month start from today by default.

    Example: todo repeat 1
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    item = db["items"][n - 1]

    # 优先处理 stop
    if stop:
        if Repeat[item["repeat"]] is Repeat.Never:
            click.echo("Warning: It is not set to repeat, nothing changes.")
            ctx.exit()
        db["items"][n - 1]["repeat"] = Repeat.Never.name
        db["items"][n - 1]["s_date"] = ""
        db["items"][n - 1]["n_date"] = ""
        if TodoStatus[item["status"]] is TodoStatus.Completed:
            # 只有当该项目在 Completed 列表中时，才需要设置 dtime
            db["items"][n - 1]["dtime"] = now()
        update_db(db)
        ctx.exit()

    # 为了逻辑清晰，要求同时设置重复模式与起始时间
    if not every:
        click.echo("Error: Missing option '-every'.")
        ctx.exit()
    if not start:
        click.echo("Error: Missing option '-from'.")
        ctx.exit()

    today = arrow.now().format(DateFormat)
    if (not start) or (start.lower() == 'today'):
        start = today
    if arrow.get(start) < arrow.get(today):
        click.echo("Error: Cannot start from a past day.")
        ctx.exit()

    make_schedule(ctx, db, n - 1, every, start)
    update_db(db)
    ctx.exit()


def validate_n(l: TodoList, n: int) -> ErrMsg:
    if not l:
        return "There is no item in the list."
    if n < 1:
        return "Please input a number bigger than zero."

    size = len(l)
    if n > size:
        if size == 1:
            return "There is only 1 item."
        else:
            return f"There are only {size} items"
    return ""


def make_schedule(ctx: click.Context, db: DB, i: int, every: str, start: str) -> None:
    """Set up a new schedule (repeat event)."""
    today = arrow.now().ceil("day")
    start_day = arrow.get(start)
    if start_day > today:
        db["items"][i]["status"] = TodoStatus.Completed.name
    else:
        db["items"][i]["status"] = TodoStatus.Incomplete.name

    # 一个事件只要设置了重复提醒，那么它的 dtime 就必须为零
    if db["items"][i]["dtime"]:
        db["items"][i]["dtime"] = 0

    s_date = start_day.format(DateFormat)
    db["items"][i]["s_date"] = s_date

    repeat = every.capitalize() if every else "Month"
    db["items"][i]["repeat"] = repeat
    match repeat:
        case Repeat.Week.name:
            n_day = arrow.get(s_date).shift(days=7)
        case Repeat.Month.name:
            n_day = arrow.get(s_date).shift(months=1)
        case Repeat.Year.name:
            n_day = arrow.get(s_date).shift(year=1)
        case _:
            click.echo(f"Error: Cannot set '-every' to {every}")
            click.echo("Try 'todo repeat --help' to get more information.")
            ctx.exit()
    db["items"][i]["n_date"] = n_day.format(DateFormat)


# 初始化
ensure_db_file()

if __name__ == "__main__":
    cli(obj={})
