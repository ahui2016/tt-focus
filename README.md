# tt-focus

tt-focus: Command-line time tracker to help focus  
专门为了帮助集中注意力而设计的命令行时间记录器

tt-focus 有两大特点：

1. 是一个纯命令行程序
2. 主要用途不是记录时间使用情况，而是帮助集中注意力

比如吃饭、睡觉、做运动、娱乐等的时间记录 **不适合** 使用本软件。
而写作、学习、编程等，就 **适合** 使用本软件。

## 安装

本软件使用了 Python 3.10 的新特性，如果你的系统中未安装 Python 3.10, 推荐使用 pyenv 或 miniconda 来安装最新版本的 Python。

例如，安装 miniconda 后，可以这样创建 3.10 环境：

```sh
$ conda create --name py310 python=3.10.4
$ conda activate py310
```

安装非常简单，只要 `pip install tt-focus` 即可。

## 帮助

- `tt -h`  (查看帮助)
- `tt list -h`  (每个子命令也有帮助)

### 设置语言

程序界面 (包括帮助内容) 默认是英语，但可设置为中文: `tt set -lang cn`

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

如果使用 `tt start` (省略任务类型), 则自动采用上一次的任务类型。

## 数据备份

可使用命令 `tt -i` 查看数据库文件 (sqlite) 的位置。
也可使用 `tt set -db <path/to/folder>` 更改数据库文件夹的位置。

## 高级用法

在前面的 "使用方法" 部分，列出了最常用的命令。但有时需要更多功能，使本软件变得更方便好用。

- `tt set -t coding -alias 编程`  (可以随时添加或修改别名)
- `tt set -t reading -name read`  (也可以修改任务名称)
