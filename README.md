# tt-focus

tt-focus: Command-line time tracker to help focus  
专门为了帮助集中注意力而设计的命令行时间记录器

tt-focus 有两大特点：

1. 是一个纯命令行程序
2. 主要用途不是记录时间使用情况，而是帮助集中注意力

比如吃饭、睡觉、做运动、娱乐等的时间记录 **不适合** 使用本软件。
而写作、学习、编程等，就 **适合** 使用本软件。

## 安装

本软件使用了 Python 3.10 的新特性，如果你的系统中未安装 Python 3.10, Windows 用户可直接到 [Python官网](https://www.python.org/downloads/) 下载最新版安装即可。 Linux, MacOS 推荐使用 [pyenv](https://github.com/pyenv/pyenv) 或 [miniconda](https://docs.conda.io/en/latest/miniconda.html) 来安装最新版本的 Python。

例如，安装 miniconda 后，可以这样创建 3.10 环境：

```sh
$ conda create --name py310 python=3.10.4
$ conda activate py310
```

在有了 Python 3.10 之后，安装本软件非常简单，只要 `pip install tt-focus` 即可。

## 帮助

- `tt -h`  (查看帮助)
- `tt list -h`  (每个子命令也有帮助)

### 设置语言

- 程序界面 (包括帮助内容) 默认是英语，但可设置为中文: `tt set -lang cn`
- 也可随时设置为英文: `tt set -lang en`

## 使用方法

### 添加任务类型

在第一次使用之前，必须至少添加一种任务类型。例如：

- `tt add coding`  (添加任务类型 coding)
- `tt add reading -alias 读书`  (添加任务类型 reading 及其别名)
- `tt list -t`  (查看已添加的任务类型)

### 开始工作 (启动一个事件)

```sh
$ tt start coding

事件 id:rcdrdg, 任务: coding (编程), 开始于 17:22:28
```

### 暂停 (休息)

当你需要稍稍休息一下，可使用该命令 `tt pause` 或 `tt -p`

### 恢复 (回到工作)

从休息中回到工作时，可使用该命令 `tt resume` 或 `tt -r`

### 查看状态

可随时使用命令 `tt status` 或 `tt -s` 查看当前事件的用时情况，例如：

```sh
$ tt -s

Task | coding (编程)
Event| (id:rcbpba) 2022-05-23 **running**

total  14:42:46 -> 16:50:45 [0:41:34]
-------------------------------------
Split  14:42:46 -> 15:24:20 [0:41:34]
Pause  [0:44:37]
Split  16:08:57 .. 16:50:45 [0:41:48]
```

### 结束

工作结束，或者需要长时间休息时，使用命令 `tt stop` 结束一次计时。
结束后，会显示 "生产效率/集中力"(productivity), 意思是从该事件的开始到结束这段时间内，工作时间所占的比例。

### 事件列表

- `tt list` 查看最近发生的事件。
- `tt list -v` 查看最近事件，并且显示更详细的信息。
- `tt list <event_id>` 查看指定事件的详细信息。

## 数据备份

可使用命令 `tt -i` 查看数据库文件 (sqlite) 的位置。
也可使用 `tt set -db <path/to/folder>` 更改数据库文件夹的位置。
只要备份数据库文件 (tt-focus.db) 就可以备份本软件的全部数据。

## 高级用法

在前面的 "使用方法" 部分，列出了最常用的命令。但有时需要更多功能，使本软件变得更方便好用。

### 修改任务类型

- `tt set -t coding -alias 编程`  (可以随时添加或修改别名)
- `tt set -t reading -name read`  (也可以修改任务名称)

### 开始工作（但不指定任务类型）

使用 `tt start` 命令时，如果不指定任务类型，可自动采用上一次的任务类型。

### 工作分段

有的工作有明显的分段，比如 "需要集中精神做 3 道题"，并且做完一题不休息，马上就做第二题，此时可以使用 `tt split` 命令分割工作时间，以便了解每一道题分别用了多长时间。

注意，默认每一次 split 不可小于 5 分钟，该时间可以修改，例如：

```sh
$ tt set --split-min 3

工作时长下限: 3 分钟
```

### 事件列表

- `tt list -day 2022-05-01`  (指定某一天的全部事件)
- `tt list -v -day 2022-05-01`  (指定某一天的全部事件，更详细)
- `tt list -month 2022-05`  (指定某一个月的全部事件)
- `tt list -v -month 2022-05`  (指定某一个月的全部事件，更详细)
- `tt list -year 2022`  (指定某一年的每个月事件数量)

### 合并事件 (merge)

同一天，并且是相同的任务类型，并且相邻的事件可以合并。例如：

`tt merge rc8j1f rc8dd4`

注意，合并事件会导致 productivity(生产效率/集中力) 变低，并且一旦合并就不能分割。

可使用 `-p/--preview` 预览合并结果，例如 `tt merge -p rc8j1f rc8dd4`

### 添加或修改事件备注

每个事件，可以添加备注，例如：

`tt set -e rcftx1 -notes 某某项目添加XX功能`

如果不指定事件 ID, 则默认添加/修改最新一个事件的备注，例如：

`tt set -notes 修复某个bug`

添加备注后，可使用命令 `tt list rcftx1` 或 `tt list -v` 查看备注。

### 删除备注

把备注修改为一个空格，相当于删除备注。例如：

`tt set -notes " "`

注意要用半角引号包围空格。

### 记录时长的上下限

如果一个工作小节，或一次休息时间小于下限，或超过上限，会被自动忽略。
使用命令 `tt -i/--info` 可查看上下限，例如：

```sh
$ tt -i

         语言: cn
   数据库文件: C:\Users\root\AppData\tt-focus\tt-focus.db
 工作时长下限: 5 分钟
 休息时长下限: 5 分钟
 休息时长上限: 60 分钟
```

上述时长的上下限可以自定义，例如：

- `tt set --split-min 8`  (把工作时长下限改为 8 分钟)
- `tt set --pause-min 3`  (把休息时长下限改为 3 分钟)
- `tt set --pause-min 3`  (把休息时长下限改为 3 分钟)

### 删除事件或任务

- `tt delete -e <event id>`  (删除指定的事件)
- `tt delete -t <task name>`  (删除指定任务类型，注意，会同时删除关联的事件)
