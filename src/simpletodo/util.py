import json
import arrow
from pathlib import Path
from typing import cast
from appdirs import AppDirs

from simpletodo.model import DB, IdxTodoList, Repeat, TodoList, TodoStatus, new_db

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


def print_todolist(l: IdxTodoList) -> None:
    if not l:
        return
    print("\nTodo\n------------")
    for idx, item in l:
        print(f"{idx+1}. {item['event']}")


def print_donelist(l: IdxTodoList) -> None:
    if not l:
        return
    print("\nCompleted\n------------")
    for idx, item in l:
        print(f"{idx+1}. {item['event']}")


def print_repeatlist(l: IdxTodoList) -> None:
    print("\nSchedule\n------------")
    for idx, item in l:
        repeat = item["repeat"]
        if Repeat[repeat] is Repeat.Week:
            print(
                f"{idx+1}. every {arrow.get(item['s_date']).format('dddd')} "
                f"[{item['n_date']}] {item['event']}"
            )
        else:
            print(f"{idx+1}. every {repeat.lower()} [{item['n_date']}] {item['event']}")


def is_last_day(date: str) -> bool:
    """Is it the last day of month?"""
    last_day = arrow.get(date).ceil("month").format(DateFormat)
    return date == last_day
