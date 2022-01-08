import click
import json
import arrow
from pathlib import Path
from typing import cast
from appdirs import AppDirs
from arrow.arrow import Arrow

from simpletodo.model import (
    DB,
    ErrMsg,
    IdxTodoList,
    Repeat,
    TodoItem,
    TodoList,
    TodoStatus,
    new_db,
    now,
)

todo_db_name = "todo-db.json"
DateFormat = "YYYY-MM-DD"

app_dirs = AppDirs("todo", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
db_path = app_config_dir.joinpath(todo_db_name)


def ensure_db_file() -> None:
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(new_db(), f, indent=4, ensure_ascii=False)


def load_db() -> DB:
    with open(db_path, "rb") as f:
        return cast(DB, json.load(f))


def split_db(db: DB) -> tuple[IdxTodoList, IdxTodoList, IdxTodoList]:
    todo_list: IdxTodoList = []
    done_list: IdxTodoList = []
    repeat_list: IdxTodoList = []
    for idx, item in enumerate(db["items"]):
        if TodoStatus[item["status"]] is TodoStatus.Incomplete:
            todo_list.append((idx, item))
        if item["dtime"] > 0:
            done_list.append((idx, item))
        if Repeat[item["repeat"]] is not Repeat.Never:
            repeat_list.append((idx, item))
    todo_list.sort(key=lambda x: x[1]["ctime"], reverse=True)
    done_list.sort(key=lambda x: x[1]["dtime"], reverse=True)
    repeat_list.sort(key=lambda x: x[1]["n_date"])
    return todo_list, done_list, repeat_list


def update_db(db: DB) -> None:
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def print_todolist(l: IdxTodoList, all: bool) -> None:
    print("\nTodo\n------------")
    if not l:
        print("(none)")
        if not all:
            print("\nTry 'todo -a' to include completed items.")
        return
    for idx, item in l:
        print(f"{idx+1}. {item['event']}")


def print_donelist(l: IdxTodoList) -> None:
    print("\nCompleted\n------------")
    if not l:
        print("(none)")
        return
    for idx, item in l:
        print(f"{idx+1}. {item['event']}")


def print_repeatlist(l: IdxTodoList) -> None:
    print("\nSchedule\n------------")
    if not l:
        print("(none)")
        return
    for idx, item in l:
        repeat = item["repeat"]
        if Repeat[repeat] is Repeat.Week:
            print(
                f"{idx+1}. every {arrow.get(item['s_date']).format('dddd')} "
                f"[{item['n_date']}] {item['event']}"
            )
        else:
            print(f"{idx+1}. every {repeat.lower()} [{item['n_date']}] {item['event']}")


def is_last_day(date: Arrow) -> bool:
    """Is it the last day of month?"""
    last_day = date.ceil("month").format(DateFormat)
    return date == last_day


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


def stop_schedule(db: DB, idx: int, item:TodoItem, ctx:click.Context,) -> None:
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


def make_schedule(db: DB, i: int, every: str, start: Arrow, ctx: click.Context) -> None:
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
