import random
from pathlib import Path

import arrow
import click
import pyperclip
from typing import cast

from simpletodo.model import (
    ErrMsg,
    Repeat,
    TodoItem,
    TodoStatus,
    new_todoitem,
    now,
)
from simpletodo.util import (
    ensure_db_file,
    load_db,
    print_donelist,
    print_repeatlist,
    print_result,
    print_todolist,
    split_lists,
    update_db,
    validate_n,
    make_schedule,
    update_schedules,
    load_cfg,
    change_db_path,
    todo_cfg_path,
    print_mottos,
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


def show_where(ctx: click.Context, _, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"[todo] {__file__}")
    click.echo(f"[config] {todo_cfg_path}")
    click.echo(f"[database] {db_path}")
    ctx.exit()


def dump(ctx: click.Context, _, value):
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
    "show_all",
    "-a",
    "--all",
    is_flag=True,
    help="Show all items (including 'Completed' and 'Schedule').",
)
@click.option(
    "new_path", "--set-db-path", type=click.Path(), help="Change the database location."
)
@click.pass_context
def cli(ctx, show_all, new_path):
    """simple-todo: Yet another command line TODO tool (命令行TODO工具)

    Just run 'todo' (with no options and no command) to list all items.

    https://pypi.org/project/simpletodo/
    """
    if ctx.invoked_subcommand is None:
        if new_path:
            err = change_db_path(Path(new_path))
            check(ctx, err)
            ctx.exit()

        db = load_db()

        # 显示格言
        if (not db["hide_motto"]) and db["mottos"]:
            n = db["select_motto"]
            if n:
                # 固定显示
                click.echo(f"\n【{db['mottos'][n-1]}】")
            else:
                # 随机显示（并且随机不显示）
                # 五分之一的概率会显示
                if random.randint(1, 5) == 1:
                    click.echo(f"\n【{random.choice(db['mottos'])}】")

        # 显示 todo
        update_schedules(db)
        if not db["items"]:
            click.echo("There's no todo item.")
            click.echo("Use 'todo add ...' to add a todo item.")
            click.echo("Use 'todo --help' to get more information.")
            ctx.exit()

        todo_list, done_list, repeat_list = split_lists(db)
        print_todolist(todo_list, show_all)

        if show_all:
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
    subject = " ".join(event).strip()
    if not subject:
        click.echo(ctx.get_help())
        ctx.exit()

    db = load_db()
    db["items"].insert(0, new_todoitem(subject))
    update_db(db)
    print_result(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=int)
@click.pass_context
def copy(ctx, n):
    """Copy the content of an event to the clipboard.

    复制指定事项的内容到剪贴板。

    Example: todo copy 3
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    content = db["items"][n - 1]["event"]
    try:
        pyperclip.copy(content)
    except Exception:
        pass
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=int)
@click.pass_context
def done(ctx, n):
    """Mark the N'th item as 'Completed'.

    Example: todo done 1
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    idx = n - 1
    status = db["items"][idx]["status"]
    repeat = db["items"][idx]["repeat"]
    if TodoStatus[status] is not TodoStatus.Incomplete:
        click.echo("Warning: It is not in the incomplete-list, nothing changes.")
        ctx.exit()
    
    if Repeat[repeat] is Repeat.Never:
        db["items"][idx]["dtime"] = now()
        db["items"][idx]["status"] = TodoStatus.Completed.name
    else:
        db["items"][idx]["status"] = TodoStatus.Waiting.name

    update_db(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=int)
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
    print_result(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def clean(ctx):
    """Clear the completed list (delete all completed items)."""
    db = load_db()
    items = [
        x for x in db["items"] if TodoStatus[x["status"]] is not TodoStatus.Completed
    ]
    db["items"] = items
    update_db(db)
    print_result(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=int)
@click.pass_context
def redo(ctx, n):
    """Mark the N'th item as 'Incomplete'.

    Example: todo redo 1
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

    idx = n - 1
    status = db["items"][idx]["status"]
    if TodoStatus[status] is not TodoStatus.Completed:
        click.echo("Warning: It is not in the completed-list, nothing changes.")
        ctx.exit()

    db["items"][idx]["status"] = TodoStatus.Incomplete.name
    db["items"][idx]["ctime"] = now()
    db["items"][idx]["dtime"] = 0
    update_db(db)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("n", nargs=1, type=int)
@click.option("every", "-every", "--every", help="Every 'week' or 'month' or 'year'.")
@click.option(
    "start",
    "-from",
    "--start-from",
    help="Example: -from 2021-04-01",
)
@click.pass_context
def repeat(ctx, n, every, start: str):
    """Set the N'th item to repeat every week/month/year.

    Example: todo repeat 1 -every month -from today
    """
    db = load_db()
    err = validate_n(db["items"], n)
    check(ctx, err)

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

    idx = n - 1
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


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option("show_list", "-l", "--list", is_flag=True, help="List all mottos.")
@click.option(
    "is_show", "-on", is_flag=True, help="Show a motto when listing todo items"
)
@click.option(
    "is_hide", "-off", is_flag=True, help="Do not show motto when listing todo items"
)
@click.option(
    "randomly", "-r", "--random", is_flag=True, help="Randomly display a motto."
)
@click.option(
    "select", "-s", "--select", type=int, help="Select which motto to display."
)
@click.option(
    "top", "-t", "--top", type=int, help="Move a motto to the top of the list"
)
@click.option("sentence", "-a", "--add", help="Add a motto.")
@click.option("edit", "-e", "--edit", type=(int, str), help="Edit a motto.")
@click.option("del_n", "-d", "--delete", type=int, help="Example: todo motto -d 1")
@click.pass_context
def motto(
    ctx,
    show_list,
    is_show,
    is_hide,
    randomly,
    select,
    top,
    sentence,
    edit: tuple[int, str],
    del_n,
):
    """Motto (格言/座右铭/目标)

    Control how to display a motto when listing todo items.

    设置格言，可显示也可隐藏，如果设为显示，则会在待办事项列表的上方显示。
    """
    db = load_db()
    mottos = db["mottos"]
    hide_motto = db["hide_motto"]
    select_n = db["select_motto"]

    if show_list:
        print_mottos(mottos, hide_motto, select_n)
        ctx.exit()

    if is_show:
        db["hide_motto"] = False
        update_db(db)
        ctx.exit()

    if is_hide:
        db["hide_motto"] = True
        update_db(db)
        ctx.exit()

    if sentence:
        sentence = sentence.strip()
        if not sentence:
            click.echo(ctx.get_help())
            ctx.exit()
        db["mottos"].append(sentence)
        update_db(db)
        ctx.exit()

    if edit:
        n, value = edit
        err = validate_n(db["mottos"], n)
        check(ctx, err)
        db["mottos"][n - 1] = value
        update_db(db)
        ctx.exit()

    if randomly:
        db["select_motto"] = 0
        update_db(db)
        ctx.exit()

    if select:
        err = validate_n(db["mottos"], select)
        check(ctx, err)
        db["select_motto"] = select
        update_db(db)
        ctx.exit()

    if top:
        err = validate_n(db["mottos"], top)
        check(ctx, err)
        item = db["mottos"].pop(top - 1)
        db["mottos"].insert(0, item)
        update_db(db)
        print_mottos(mottos, hide_motto, select_n)
        ctx.exit()

    if del_n:
        err = validate_n(db["mottos"], del_n)
        check(ctx, err)
        del db["mottos"][del_n - 1]
        update_db(db)
        print_mottos(mottos, hide_motto, select_n)
        ctx.exit()

    click.echo(ctx.get_help())
    ctx.exit()


# 初始化
ensure_db_file()
db_path = load_cfg()["db_path"]

if __name__ == "__main__":
    cli(obj={})
