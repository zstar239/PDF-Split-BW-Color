# PDF Color Splitter

一个用于自动识别 PDF 中彩色页和黑白页，并将它们拆分成不同 PDF 文件的 Python 工具。

适合打印论文、报告、书籍等场景，可以将彩色页和黑白页分别提取出来，方便分别使用彩色打印机和黑白打印机打印，从而节省打印成本。

## 功能

* 自动检测 PDF 中的彩色页和黑白页
* 将所有黑白页合并为一个 PDF
* 将所有彩色页合并为一个 PDF
* 支持单面打印模式（Simplex）
* 支持双面打印模式（Duplex）
* 支持将连续的彩色/黑白区段分别输出
* 支持 Windows、Linux 和 macOS
* 支持中文路径和带空格的文件名
* 不依赖 `pdftk`
* 使用 Ghostscript 进行页面颜色检测
* 使用 `pypdf` 生成新的 PDF 文件

## 工作原理

程序会先使用 Ghostscript 将 PDF 的每一页低分辨率渲染成 PPM 图片，然后检查每个像素的 RGB 三个通道。

如果页面中的所有像素均满足：

```text
R = G = B
```

则该页面被认为是黑白页。

如果存在任意像素满足：

```text
R != G
或
G != B
或
R != B
```

则该页面被认为是彩色页。

检测完成后，程序使用 `pypdf` 从原始 PDF 中提取对应页面并生成新的 PDF 文件。

## 环境要求

需要：

* Python 3
* Ghostscript
* pypdf

### 安装 Python 依赖

```bash
pip install pypdf
```

或者：

```bash
python -m pip install pypdf
```

## 安装 Ghostscript

### Windows

下载安装 Ghostscript 后，确认下面的命令可以正常运行：

```powershell
gswin64c -version
```

例如：

```text
GPL Ghostscript 10.x.x
```

程序会自动查找：

```text
gswin64c
gswin32c
gs
```

因此通常不需要手动修改 Ghostscript 路径。

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install ghostscript
```

安装后测试：

```bash
gs --version
```

### macOS

使用 Homebrew：

```bash
brew install ghostscript
```

测试：

```bash
gs --version
```

## 使用方法

基本格式：

```bash
python split.py [OPTIONS] <PDF-file>
```

例如：

```bash
python split.py document.pdf
```

默认使用**双面打印模式**。

## 单面打印

如果使用单面打印，请添加：

```text
-s
```

例如：

```bash
python split.py -s document.pdf
```

Windows PowerShell 示例：

```powershell
python .\split.py -s ".\博士开题报告_最终版.pdf"
```

在单面模式下，每一页都会独立判断为彩色或黑白。

## 双面打印

不添加 `-s` 时，程序默认使用双面打印模式：

```bash
python split.py document.pdf
```

双面打印时：

```text
第 1 页 + 第 2 页 = 同一张纸
第 3 页 + 第 4 页 = 同一张纸
……
```

如果一张纸的任意一面是彩色，则这张纸对应的两页都会被归入彩色 PDF。

例如：

```text
第 1 页：彩色
第 2 页：黑白
```

在双面打印模式下，两页都会进入彩色 PDF。

这样可以避免实际双面打印时，一张纸的一面需要彩印、另一面却被错误分配到黑白打印任务中。

## 查看详细检测结果

使用：

```text
-v
```

例如：

```bash
python split.py -s -v document.pdf
```

输出示例：

```text
Analyzing: document.pdf
Ghostscript: C:\Program Files\gs\gs10.07.1\bin\gswin64c.exe

Page analysis:
------------------------------
Page    1: B/W
Page    2: B/W
Page    3: COLOR
Page    4: B/W
Page    5: COLOR

Simplex mode enabled.

============================================================
Result
============================================================
Black/White pages: 3
Color pages:       2
```

## 输出文件

例如输入：

```text
document.pdf
```

程序通常会生成：

```text
document_bwsplit.pdf
document_colorsplit.pdf
```

其中：

| 文件                        | 内容    |
| ------------------------- | ----- |
| `document_bwsplit.pdf`    | 所有黑白页 |
| `document_colorsplit.pdf` | 所有彩色页 |

如果 PDF 中全部都是黑白页，则不会生成空的彩色 PDF。

同样，如果全部都是彩色页，也不会生成空的黑白 PDF。

## 分段输出模式

默认情况下，程序会把所有彩色页合并成一个 PDF，把所有黑白页合并成另一个 PDF。

如果希望按照原 PDF 中连续的彩色/黑白区段分别生成文件，可以使用：

```text
-m
```

例如：

```bash
python split.py -s -m document.pdf
```

假设原 PDF 为：

```text
1-3    黑白
4-5    彩色
6-10   黑白
11     彩色
```

则会分别生成多个 PDF 文件。

## 参数说明

```text
-s    使用单面打印模式（Simplex）

      不指定 -s 时默认使用双面打印模式（Duplex）

-m    将连续的彩色/黑白区段分别输出

-v    显示详细检测过程

-h    显示帮助
```

查看帮助：

```bash
python split.py -h
```

## 推荐用法

对于论文、毕业论文、开题报告等需要**单面打印**的文档，推荐：

```bash
python split.py -s -v document.pdf
```

对于需要**双面打印**的书籍或资料，推荐：

```bash
python split.py -v document.pdf
```

## 中文文件名

程序使用 `subprocess` 调用 Ghostscript，因此支持中文路径和包含空格的文件名。

例如：

```powershell
python .\split.py -s -v ".\博士开题报告_最终版.pdf"
```

## 注意事项

### 1. 极少量颜色也会被判定为彩色

目前的判断规则非常严格。

只要页面中存在一个非灰度像素，就会被认为是彩色页。

例如：

* 一个蓝色超链接
* 一个彩色 Logo
* 一个红色批注
* 一张几乎黑白但存在轻微颜色偏差的图片

都有可能让该页面被判定为彩色页。

### 2. Ghostscript 只用于颜色检测

程序不会使用 Ghostscript 重新生成最终 PDF。

Ghostscript 只负责将页面临时渲染成低分辨率 PPM 图片，用于判断页面是否包含颜色。

最终输出 PDF 由 `pypdf` 直接从原 PDF 中提取页面，因此不会因为颜色检测过程降低最终 PDF 的分辨率。

### 3. 临时文件

程序会在系统临时目录中生成 PPM 图片。

分析完成后会自动删除这些临时文件。

### 4. PDF 页数

程序会检查 Ghostscript 渲染得到的页面数量是否与原 PDF 页数一致。

如果不一致，会停止处理并提示错误。

## 示例

### 单面打印

```bash
python split.py -s report.pdf
```

### 单面打印 + 显示详细信息

```bash
python split.py -s -v report.pdf
```

### 双面打印

```bash
python split.py report.pdf
```

### 双面打印 + 显示详细信息

```bash
python split.py -v report.pdf
```

### 按连续区段分别输出

```bash
python split.py -s -m report.pdf
```

## 适用场景

这个工具比较适合：

* 博士 / 硕士论文
* 开题报告
* 学术论文
* 教材
* 讲义
* 技术文档
* PDF 书籍
* 大批量打印资料

尤其适合需要提前统计和拆开彩色页、黑白页的打印任务。
