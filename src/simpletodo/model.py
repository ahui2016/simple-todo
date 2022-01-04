import arrow
from typing import TypedDict
from enum import Enum, auto


# 采用 ErrMsg 而不是采用 exception, 一来是受到 Go 语言的影响，
# 另一方面，凡是用到 ErrMsg 的地方都是与业务逻辑密切相关并且需要向用户反馈详细错误信息的地方，
# 这些地方用 ErrMsg 更合理。 (以后会改用 pypi.org/project/result)
ErrMsg = str
"""一个描述错误内容的简单字符串，空字符串表示无错误。"""


def now() -> float:
    return arrow.now().timestamp()


class TodoStatus(Enum):
    Incomplete = auto()
    Completed = auto()


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
    stime: float  # start-time, 第一次提醒日期
    ntime: float  # next-time, 下次提醒日期


TodoList = list[TodoItem]


def new_todoitem(event: str) -> TodoItem:
    return TodoItem(
        ctime=now(),
        dtime=0,
        event=event,
        status=TodoStatus.Incomplete.name,
        repeat=Repeat.Never.name,
        stime=0,
        ntime=0,
    )


class DB(TypedDict):
    items: list[TodoItem]


def new_db() -> DB:
    return DB(items=[])
