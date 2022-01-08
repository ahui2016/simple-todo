import arrow
from arrow.arrow import Arrow
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
    is_last_day,
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
@click.option(
    "all",
    "-a",
    "--all",
    is_flag=True,
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


@cli.command()
@click.argument("event", nargs=-1, required=True)
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
def repeat(ctx, n, every, start: str, stop):
    """Sets the N'th item to repeat every week/month/year.

    Example: todo repeat 1 -every month -from today
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    idx = n - 1
    item = db["items"][idx]

    # 优先处理 stop
    if stop:
        if Repeat[item["repeat"]] is Repeat.Never:
            click.echo("Warning: It is not set to repeat, nothing changes.")
            ctx.exit()
        db["items"][idx]["repeat"] = Repeat.Never.name
        db["items"][idx]["s_date"] = ""
        db["items"][idx]["n_date"] = ""
        if TodoStatus[item["status"]] is TodoStatus.Completed:
            # 只有当该项目在 Completed 列表中时，才需要设置 dtime
            db["items"][idx]["dtime"] = now()
        update_db(db)
        ctx.exit()

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

    make_schedule(ctx, db, idx, every, s_date)
    update_db(db)
    ctx.exit()


@cli.command()
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


def make_schedule(ctx: click.Context, db: DB, i: int, every: str, start: Arrow) -> None:
    """Set up a new schedule (repeat event)."""

    # 验证 start
    today = arrow.now()
    if start < today.floor("day"):  # floor("day") 返回本地时间当天零时零分
        click.echo("Error: Cannot start from a past day.")
        ctx.exit()

    # set "s_date"
    db["items"][i]["s_date"] = start.format(DateFormat)

    # set "dtime"
    # 一个事件只要设置了重复提醒，那么它的 dtime 就必须为零
    if db["items"][i]["dtime"]:
        db["items"][i]["dtime"] = 0

    # set "repeat"
    repeat = every.capitalize()
    if repeat not in (Repeat.Week.name, Repeat.Month.name, Repeat.Year.name):
        click.echo(f"Error: Cannot set '-every' to {every}")
        click.echo("Try 'todo repeat --help' to get more information.")
        ctx.exit()
    db["items"][i]["repeat"] = repeat

    # set "status" and "n_date"
    # 在本函数的开头已经验证过 start, 防止其小于今天。
    if start > today.ceil("day"):  # ceil("day") 返回本地时间当天最后一秒
        db["items"][i]["status"] = TodoStatus.Completed.name
        db["items"][i]["n_date"] = db["items"][i]["s_date"]
    if start.format(DateFormat) == today.format(DateFormat):
        db["items"][i]["status"] = TodoStatus.Incomplete.name
        n_date = shift_next_date(start, start, Repeat[repeat])
        db["items"][i]["n_date"] = n_date.format(DateFormat)


# 在调用本函数之前，要限定 repeat 的值的范围。
def shift_next_date(s_date: Arrow, n_date: Arrow, repeat: Repeat) -> Arrow:
    match repeat:
        case Repeat.Week:
            return n_date.shift(days=7)
        case Repeat.Month:
            if is_last_day(s_date):
                return n_date.shift(months=1).ceil("month")
            return n_date.shift(months=1)
        case Repeat.Year:
            if is_last_day(s_date):
                return n_date.shift(year=1).ceil("month")
            return n_date.shift(year=1)
        case _:
            raise ValueError(repeat)


def update_schedules(db: DB) -> None:
    today = arrow.now()
    u_date = today.format(DateFormat)
    if u_date == db["u_date"]:
        # 如果今天已经更新过，就不用更新了（每天只更新一次）
        return
    db["u_date"] = u_date
    for idx, item in enumerate(db["items"]):
        if today.format(DateFormat) == item["n_date"]:
            db["items"][idx]["status"] = TodoStatus.Incomplete.name
            s_date = arrow.get(item["s_date"])
            n_date = arrow.get(item["n_date"])
            n_date = shift_next_date(s_date, n_date, Repeat[item["repeat"]])
            db["items"][idx]["n_date"] = n_date.format(DateFormat)
    update_db(db)


# 初始化
ensure_db_file()

if __name__ == "__main__":
    cli(obj={})
