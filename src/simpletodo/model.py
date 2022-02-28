import arrow
from typing import TypedDict
from enum import Enum, auto


# 采用 ErrMsg 而不是采用 exception, 一来是受到 Go 语言的影响，
# 另一方面，凡是用到 ErrMsg 的地方都是与业务逻辑密切相关并且需要向用户反馈详细错误信息的地方，
# 这些地方用 ErrMsg 更合理。 (以后会改用 pypi.org/project/result)
ErrMsg = str
"""一个描述错误内容的简单字符串，空字符串表示无错误。"""

NotFound: ErrMsg = "NotFound"


def now() -> float:
    return arrow.now().timestamp()


class TodoStatus(Enum):
    Incomplete = auto()  # 已经开始做，但未完成
    Completed = auto()  # 已完成，执行 clean 命令可批量删除全部已完成项目
    Waiting = auto()  # 专用于计划任务


class Repeat(Enum):
    Never = auto()
    Week = auto()
    Month = auto()
    Year = auto()


class TodoItem(TypedDict):
    ctime: float  # create-time, 用于排序, 同时也当作 ID
    dtime: float  # done-time, 完成时间，只用于排序
    event: str
    status: str  # TodoStatus
    repeat: str  # Repeat
    s_date: str  # start-date, 第一次提醒日期, "YYYY-MM-DD"
    n_date: str  # next-date, 下次提醒日期, "YYYY-MM-DD"


TodoList = list[TodoItem]
IdxTodoList = list[tuple[int, TodoItem]]  # list of (index, item)


def new_todoitem(event: str) -> TodoItem:
    return TodoItem(
        ctime=now(),
        dtime=0,
        event=event,
        status=TodoStatus.Incomplete.name,
        repeat=Repeat.Never.name,
        s_date="",
        n_date="",
    )


class DB(TypedDict):
    u_date: str  # "YYYY-DD-MM" 用来判断要不要刷新周期计划（每天刷新一次）
    items: list[TodoItem]
    hide_motto: bool
    select_motto: int
    mottos: list[str]


def new_db() -> DB:
    return DB(u_date="", items=[], hide_motto=False, select_motto=0, mottos=[])


class TodoConfig(TypedDict):
    db_path: str
    upgrade: str  # 用于避免重复执行升级程序
