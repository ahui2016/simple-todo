# simple-todo

Yet another command line TODO tool (命令行 todo 工具)


## 特色

命令行 todo list 工具有很多，但要么功能非常复杂，而功能简单的又很可能缺少我需要的功能。

为了解决这个矛盾，获得一个功能很少很简单，同时我想要的功能都有的工具，就只能自己做了。

也许这个工具不能满足你的需求，但你可以参考，可以修改，本工具的代码量很小，都是些简单的 Python 语句，没有啥复杂算法，也没啥奇技淫巧，而且结构清晰，变量命名认真，必要的地方都有注释。

## 主要功能

1. 简便、快捷地临时记录待办事宜；
2. 周期提醒，可设置每周、或每月、每年重复提醒；
3. 随机显示格言/座右铭。

## 哲学

每一个效率工具，都体现了一种事务管理哲学。本工具有两个主要理念：

**理念1**: 临时待办事项必须尽快清理，不可长期积压。  
**理念2**: 功能多不一定好，同时代码越少越好。（代码少 bug 就少，容易维护，容易修改）

举个例子，基于这两个理念，调整事项顺序的功能、分类或打标签功能等我就不做了，不做这些功能有三个大好处：

1. 当待办事项的列表变长时会直观地感受到不舒服，并且没有办法掩盖（如果能调整顺序，就会堆积大量事项在列表底部，如果能分类或按标签筛选，就会造成待办事项不多的错觉）
2. 调整顺序与分类有一定的趣味性，也会让“强迫症患者”忍不住去整理列表，浪费时间和精力。
3. 不做这些功能可以少写很多代码，用户也可以少看几行文档，少学几种操作。

## 安装

simple todo 使用了 Python 3.10 的新特性，比如 type union operator, pattern matching 等，因此，如果你的系统中未安装 Python 3.10, 推荐使用 [pyenv](https://github.com/pyenv/pyenv) 或 [miniconda](https://docs.conda.io/en/latest/miniconda.html) 来安装最新版本的 Python。

### 简单安装方法

执行以下命令即可：

```sh
pip install simpletodo
```

升级：

```sh
pip install -U simpletodo
```

### 另一种安装方法

另外，还可以使用 pipx 来安装, pipx 会自动为 simple-todo 创建一个虚拟环境，不会污染系统环境，并且使用时不用管理虚拟环境，直接使用 todo 命令即可。推荐大家多了解一下 pipx。

pipx 的介绍及安装方法: https://pypa.github.io/pipx/ 安装 pipx 后执行以下命令即可：

```sh
pipx install simpletodo
```

升级：

```sh
pipx upgrade simpletodo
```

## 基本使用方法

- 使用命令 `todo` 不带任何参数，可显示待办事项列表。这是最常用的功能，因此把最简单命令给了它。
- 使用命令 `todo -a` 可显示更多事项（包括已完成事项及未来计划）。
- 使用命令 `todo add ...`, 例如 `todo add Buy more beer` 可把 "Buy more beer" 添加到待办事项列表中。
- 使用命令 `todo done [N]`, 例如 `todo done 3` 可把序号 3 的事项标记为“已完成”。后续可以使用 `todo redo [N]` 把已完成事项恢复为待办事项，或使用 `todo delete [N]` 彻底删除一个事项，还可以用 `todo clean` 来一次性删除全部已完成事项。

一个例子（我经常用来随手记录网址，后续抽空整理到别的笔记工具中）：

```sh
todo add http://example.com
```

### 复制到剪贴板

假设上述我随手记录的网址序号为 2, 那么，使用命令 `todo copy 2` 即可把该网址复制到系统剪贴板。

### 关于序号

**注意**，每次执行 add、done、redo、delete 等操作后，都有可能使序号发生变化，因此每次操作前请先使用 `todo` 或 `todo -a` 确认序号后再操作。

这个设计虽然会使操作稍有不便，但也符合本工具的理念：让待办列表变长时感到不便从而避免积压，同时尽量减少功能、减少代码量。

### 修改事项描述

使用命令 `todo edit [N] "..."` 可修改指定事项的描述，例如：

```sh
todo edit 3 "聚会时间是晚上八点"
```

注意，这里第一个参数是序号，第二个的参数是**一个**字符串，如果是中文而且没有空格，就不需要引号；如果句子中间有空格（比如英文句子中间通常有空格）就需要使用半角引号（双引号、单引号都可以）。

这与 `todo add` 命令不同, todo add 后面即使有空格也不需要引号。 

因为 todo add 是一个很常用的命令，要让它使用起来更方便；而 todo edit 是一个很不常用的命令，因此与 "使用方便" 相比,  "代码少一点" 的优先度更高。

## 设置周期提醒日程

```sh
todo repeat 2 -every month -from today
```

使用如上所示的命令，可以让序号 2 的事项每个月重复提醒一次，从今天开始。假设今天是 1 月 5 日，那就会在每个月的 5 日自动把该事项添加进待办列表中。

其中，还可以选择 `-every week` 或 `-every year`。

`-from` 后面指定具体日期，比如 `-from 2022-2-28`, 可以使用的简称只有 `today` 与 `tomorrow`。（注意，不可设置一个过去的日期，只能设置今天或未来的日期。）

使用命令 `todo repeat [N] -stop` 可清除序号 N 的事项的周期提醒计划（仅使其不再重复提醒，不会删除事项）。

### 如何设置提前 N 天提醒？

本工具没有这个功能，但有变通的办法，比如我每月 5 日还信用卡，但我希望每月 3 日就提醒，可以添加一个内容为 “每月5日信用卡还款” 的待办事项，然后设置每月 3 日提醒即可，我自己就是这样用的。

### 如何设置精确到小时分钟，并且系统自动弹出提醒？

本工具没有这个功能，我的做法是，需要精确到小时分钟，并且需要强提醒的场景，就用手机闹钟。

举个例子，每天早上起床，每个工作日 14:45 看股市，这些我交给手机闹钟去做。而各种缴费（水电、物业、vps等等）的提醒则使用本工具。以及突然冒出的灵感、别人推荐的书影音、发现一个好网站等等也把本工具当作一个缓冲区来使用。

## 格言/座右铭/目标

（这是一个特殊功能，如果不需要，可以不看使用方法，完全不影响其他功能的正常使用。）

使用该功能，可在 todo list 的上方显示一句格言或座右铭，或者一个目标，或者一句喜欢的话。

使用命令 `todo motto --add` 添加一句话，例如

```sh
todo motto -a "考试必过！比赛必胜！"
```

- 如果要添加的句子中间没有空格，就不需要引号；如果句子中间有空格（比如英文句子中间通常有空格）就需要使用半角引号（双引号、单引号都可以）。
- 如果添加了多句话，默认随机显示其中一句，**并且随机不显示格言**。（约五分之一的概率会显示格言）
- 使用命令 `todo motto --list` 可展示全部格言。
- 使用命令 `todo motto --select [N]` 可固定显示第 N 个句子。使用 `todo motto --random` 可恢复随机显示。
- 使用命令 `todo motto -off` 可停用该功能。使用 `todo motto -on` 可启用该功能。
- 使用命令 `todo motto --top [N]` 可顶置第 N 个句子。
- 使用命令 `todo motto --edit [N] "..."` 可修改第 N 个句子的内容。

我自己使用的格言是：

```sh
$ todo motto -l

Mottos [show] [random]
----------------------
1. 在宇宙的大尺度之下
2. 不要陷入生活的琐碎而忘记想要到达的地方
3. 想要战胜时间，唯有比它更慢。
4. 意识到人生的荒谬性即意识到自由
5. 宇宙里有什么不是暂时
```

其中 1、2、3 是我自己想的句子, 4 是在已被攻击到关站的某优秀网址看来的, 5 是“我的小飞机场”的歌词。

## 数据备份

- 使用命令 `todo --where` 可查看数据库文件的具体位置，那是一个 json 文件，备份该文件即可备份全部数据。
- 使用命令 `todo --set-db-path <new path>` 可更改数据库文件的位置，其中 new path 可以是一个不存在的文件（但其父文件夹必须存在）、或一个已存在的文件夹，但不可以是一个已存在的文件；可以是绝对路径，也可以是相对路径。
- 另外还可以使用 `todo --dump` 来直接输出上述 json 文件的全部内容。

由于本工具的理念是不积压待办事项，因此该 json 文件通常体积很小，内容很少。

## 帮助信息

使用命令 `todo -h` 或 `todo add -h` 可查看帮助信息，其中 `add` 可以是其他子命令，每个子命令都有帮助信息。
