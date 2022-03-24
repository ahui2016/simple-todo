import os
import shutil

import click
import json
import arrow
from pathlib import Path
from appdirs import AppDirs
from arrow.arrow import Arrow

from simpletodo.model import (
    DB,
    ErrMsg,
    IdxTodoList,
    Repeat,
    TodoStatus,
    new_db,
    TodoConfig,
)
from . import __version__

todo_cfg_name = "todo-config.json"
todo_db_name = "todo-db.json"
DateFormat = "YYYY-MM-DD"

app_dirs = AppDirs("todo", "github-ahui2016")
app_config_dir = Path(app_dirs.user_config_dir)
todo_cfg_path = app_config_dir.joinpath(todo_cfg_name)
default_db_path = app_config_dir.joinpath(todo_db_name)


def write_cfg(cfg: TodoConfig) -> None:
    with open(todo_cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def ensure_cfg_file() -> None:
    app_config_dir.mkdir(parents=True, exist_ok=True)
    if not todo_cfg_path.exists():
        default_cfg = TodoConfig(db_path=default_db_path.__str__(), upgrade="0.1.6")
        write_cfg(default_cfg)


def ensure_db_file() -> TodoConfig:
    ensure_cfg_file()
    cfg = load_cfg()
    db_path = Path(cfg["db_path"])
    if not db_path.exists():
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(new_db(), f, indent=4, ensure_ascii=False)
    return cfg


def change_db_path(new_path: Path, cfg: TodoConfig) -> ErrMsg:
    """new_path 是一个不存在的文件或一个已存在的文件夹，不能是一个已存在的文件"""
    new_path = new_path.resolve()
    if new_path.is_dir():
        new_path = new_path.joinpath(todo_db_name)
    if new_path.exists():
        return f"{new_path} already exists."
    old_path = cfg["db_path"]
    shutil.copyfile(old_path, new_path)
    cfg["db_path"] = new_path.__str__()
    with open(todo_cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
    os.remove(old_path)
    return ""


def load_cfg() -> TodoConfig:
    with open(todo_cfg_path, "rb") as f:
        cfg_dict = json.load(f)
        return TodoConfig(
            db_path=cfg_dict["db_path"],
            upgrade=cfg_dict.get("upgrade", ""),
        )


def load_db(cfg: TodoConfig) -> DB:
    with open(cfg["db_path"], "rb") as f:
        db_dict = json.load(f)
        return DB(
            u_date=db_dict.get("u_date", ""),
            items=db_dict.get("items", []),
            hide_motto=db_dict.get("hide_motto", False),
            select_motto=db_dict.get("select_motto", 0),
            mottos=db_dict.get("mottos", []),
        )


def split_lists(db: DB) -> tuple[IdxTodoList, IdxTodoList, IdxTodoList]:
    todo_list: IdxTodoList = []
    done_list: IdxTodoList = []
    repeat_list: IdxTodoList = []

    for idx, item in enumerate(db["items"]):
        match TodoStatus[item["status"]]:
            case TodoStatus.Incomplete:
                todo_list.append((idx, item))
            case TodoStatus.Completed:
                done_list.append((idx, item))
            case TodoStatus.Waiting:
                repeat_list.append((idx, item))
            case _:
                raise ValueError(f"Unknown status: {item['status']}")

    todo_list.sort(key=lambda x: x[1]["ctime"], reverse=True)
    done_list.sort(key=lambda x: x[1]["dtime"], reverse=True)
    repeat_list.sort(key=lambda x: x[1]["n_date"])
    return todo_list, done_list, repeat_list


def update_db(db: DB, cfg: TodoConfig) -> None:
    with open(cfg["db_path"], "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


def print_mottos(mottos: list[str], is_hide: bool, n: int) -> None:
    status = "hide" if is_hide else "show"
    select = f"{n}" if n else "random"
    print(f"\nMottos [{status}] [{select}]\n----------------------")
    if not mottos:
        print("(none)")
        print("\nUse 'todo motto --add \"...\"' to add a motto.")
    for idx, item in enumerate(mottos):
        print(f"{idx+1}. {item}")
    print()


def print_todolist(t_list: IdxTodoList, show_all: bool) -> None:
    print("\nTodo\n------------")
    if not t_list:
        print("(none)")
        if not show_all:
            print("\nTry 'todo -a' to include completed items.")
        return
    for idx, item in t_list:
        print(f"{idx+1}. {item['event']}")


def print_donelist(t_list: IdxTodoList) -> None:
    print("\nCompleted\n------------")
    if not t_list:
        print("(none)")
        return
    for idx, item in t_list:
        print(f"{idx+1}. {item['event']}")


def print_repeatlist(t_list: IdxTodoList) -> None:
    print("\nSchedule\n------------")
    if not t_list:
        print("(none)")
        return
    for idx, item in t_list:
        repeat = item["repeat"]
        if Repeat[repeat] is Repeat.Week:
            print(
                f"{idx+1}. every {arrow.get(item['s_date']).format('dddd')} "
                f"[{item['n_date']}] {item['event']}"
            )
        else:
            print(f"{idx+1}. every {repeat.lower()} [{item['n_date']}] {item['event']}")


def print_result(db: DB) -> None:
    todo_list, _, _ = split_lists(db)
    print_todolist(todo_list, True)
    print()


def is_last_day(date: Arrow) -> bool:
    """Is it the last day of month?"""
    last_day = date.ceil("month").format(DateFormat)
    return date == last_day


def validate_n(a_list: list, n: int) -> ErrMsg:
    if not a_list:
        return "There is no item in the list."
    if n < 1:
        return "Please input a number bigger than zero."

    size = len(a_list)
    if n > size:
        if size == 1:
            return "There is only 1 item."
        else:
            return f"There are only {size} items"
    return ""


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
        db["items"][i]["status"] = TodoStatus.Waiting.name
        db["items"][i]["n_date"] = db["items"][i]["s_date"]
    if start.format(DateFormat) == today.format(DateFormat):
        db["items"][i]["status"] = TodoStatus.Incomplete.name
        n_date = shift_next_date(start, start, Repeat[repeat])
        db["items"][i]["n_date"] = n_date


def shift_next_date(s_date: Arrow, n_date: Arrow, repeat: Repeat) -> str:
    today = arrow.now().format(DateFormat)
    next_date = n_date.format(DateFormat)
    while next_date <= today:
        match repeat:
            case Repeat.Week:
                n_date = n_date.shift(days=7)
            case Repeat.Month:
                if is_last_day(s_date):
                    n_date = n_date.shift(months=1).ceil("month")
                else:
                    n_date = n_date.shift(months=1)
            case Repeat.Year:
                if is_last_day(s_date):
                    n_date = n_date.shift(year=1).ceil("month")
                else:
                    n_date = n_date.shift(year=1)
            case _:
                raise ValueError(repeat)

        next_date = n_date.format(DateFormat)

    return next_date


def update_schedules(db: DB, cfg: TodoConfig, force: bool = False) -> None:
    today = arrow.now().format(DateFormat)
    u_date = today.format(DateFormat)
    if not force and u_date == db["u_date"]:
        # 如果今天已经更新过，就不用更新了（每天只更新一次）
        return
    db["u_date"] = u_date
    for idx, item in enumerate(db["items"]):
        if TodoStatus[item["status"]] is TodoStatus.Waiting and today >= item["n_date"]:
            db["items"][idx]["status"] = TodoStatus.Incomplete.name
            s_date = arrow.get(item["s_date"])
            n_date = arrow.get(item["n_date"])
            next_date = shift_next_date(s_date, n_date, Repeat[item["repeat"]])
            db["items"][idx]["n_date"] = next_date
    update_db(db, cfg)


def upgrade_to_v016() -> None:
    """Upgrade to v0.1.6

    从低于 v0.1.6 升级到 v0.1.6 及以上时自动升级。
    """
    cfg = load_cfg()
    if cfg["upgrade"] == "0.1.6" or __version__ < "0.1.6":
        return

    print("Upgrading to v0.1.6...")
    cfg["upgrade"] = "0.1.6"
    write_cfg(cfg)

    db = load_db(cfg)
    for idx, item in enumerate(db["items"]):
        if TodoStatus[item["status"]] is TodoStatus.Completed and item["dtime"] <= 0:
            db["items"][idx]["status"] = TodoStatus.Waiting.name
    update_schedules(db, cfg, force=True)
