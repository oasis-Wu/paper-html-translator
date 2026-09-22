# Paper HTML Translator

将浏览器保存的学术论文 HTML 转换为**图文完整、结构对应的中英文 Markdown 文档包**。

本项目是一项面向 Codex 的技能（Skill）。它从“网页，全部”形式保存的论文中提取正文、元数据、图像、表格、公式、脚注与参考文献，生成忠于原文的英文 Markdown，再由智能体完成中文全文翻译和交付前校验。

> 适用于本地保存的论文网页，不适用于 PDF、MHTML、普通网页摘要或仅靠 JavaScript 动态加载正文的页面。

## 功能特性

- **学术正文识别**：优先选择 `article`、`main` 等语义区域，并过滤导航栏、登录提示、推荐内容、广告和分享控件。
- **论文元数据提取**：按 Highwire / Google Scholar、Schema.org、Open Graph、可见标题的优先级识别题名、作者、期刊、日期、DOI 和来源 URL。
- **本地图像归档**：复制论文插图到 `assets/`，支持懒加载属性、`srcset`、`picture`、Data URI 和 SVG，并对字节相同的图像去重。
- **结构忠实保留**：保留标题层级、段落、列表、引文、公式、表格、图注、脚注、附录和参考文献；必要时使用原始 HTML 避免语义损失。
- **中英文对应输出**：英文文件保留原文，中文文件逐段翻译，并复用完全相同的图片路径、编号、交叉引用和学术结构。
- **结果自动校验**：检查中英文 Markdown、`assets/` 目录、本地图像引用、重复一级标题和疑似网页导航残留。
- **缺失资源显式披露**：遇到远程图片、登录墙、验证码或资源不完整时发出警告，不静默省略或虚构内容。

功能边界与执行流程详见 [`SKILL.md`](SKILL.md)，提取与翻译规则分别见 [`references/extraction-rules.md`](references/extraction-rules.md) 和 [`references/translation-style.md`](references/translation-style.md)。

## 项目结构

```text
paper-html-translator/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── extraction-rules.md
│   └── translation-style.md
└── scripts/
    ├── extract_paper_html.py
    └── validate_package.py
```

## 环境要求

- **Codex**：用于执行完整的提取、人工式复核、中文翻译与校验工作流。
- **Python 3.9 或更高版本**：用于运行随附脚本。
- **lxml**：HTML 解析的唯一第三方 Python 依赖。

安装脚本依赖：

```bash
python -m pip install lxml
```

如果系统 Python 未安装 `lxml`，也可以使用已经包含该依赖的 Codex Python 运行时。

## 安装

将仓库克隆或复制到 Codex 的技能目录：

```bash
git clone <your-repository-url> "$CODEX_HOME/skills/paper-html-translator"
```

Windows PowerShell 示例：

```powershell
git clone <your-repository-url> "$env:CODEX_HOME\skills\paper-html-translator"
```

安装后的核心入口应位于：

```text
$CODEX_HOME/skills/paper-html-translator/SKILL.md
```

重新启动或刷新 Codex 会话后即可调用该技能。

## 输入要求

推荐在浏览器中使用“**网页，全部**”保存论文。完整输入通常包含：

```text
saved-paper.html
saved-paper_files/
```

HTML 文件和配套资源目录应保持相对位置不变。技能会同时检查常见的 `<文件名>_files`、`<文件名>.files` 以及出版商生成的资源目录。

### 支持范围

| 输入类型 | 支持情况 | 说明 |
|---|---:|---|
| 浏览器完整保存的 `.html` | **支持** | 最佳输入形式，建议同时提供配套资源目录 |
| 资源不完整的 `.html` | **有限支持** | 提取可恢复内容，并报告无法解析的资源 |
| 仅包含摘要的论文页面 | **有限支持** | 不会推测或补写缺失的全文 |
| `.mhtml` | **不支持** | 应先使用适合 MHTML 的转换流程 |
| PDF / DOCX | **不支持** | 应改用对应的 PDF 或文档处理技能 |
| 仅靠 JavaScript 加载的页面 | **不支持** | 浏览器保存文件可能不包含实际论文正文 |

## 使用方法

### 在 Codex 中运行完整工作流

将保存的 HTML 及其配套资源目录放入同一工作区，然后向 Codex 提交类似指令：

```text
使用 $paper-html-translator 处理 saved-paper.html，生成图文完整的中英文 Markdown 文档包。
```

完整工作流包括：

1. 检查 HTML 和本地资源是否完整。
2. 运行确定性提取脚本生成英文 Markdown 和 `assets/`。
3. 对照原始 HTML 复核正文、标题层级、公式、表格、图注、脚注和参考文献。
4. 创建忠实的中文全文译本，保持编号、引文和资源路径一致。
5. 运行校验脚本并修复可解决的问题。
6. 报告输出目录、文档名称和未解决资源。

### 单独运行提取脚本

```bash
python scripts/extract_paper_html.py "/path/to/saved-paper.html" \
  --output-root "/path/to/output"
```

可选参数：

```text
--output-root PATH   指定题名目录的父目录；默认使用输入 HTML 所在目录
--folder-name NAME   覆盖输出目录名和英文 Markdown 文件名
```

该脚本只执行**英文内容提取与本地资源整理**。学术结构复核和中文翻译属于 Codex 技能工作流，不由脚本单独完成。

脚本拒绝静默覆盖已有的非空输出目录。如需重新处理，请指定新的 `--output-root` 或先妥善处理原目录。

### 校验输出包

完成中文译文后，运行：

```bash
python scripts/validate_package.py "/path/to/output/<Original paper title>"
```

校验器以 JSON 输出结果：

```json
{
  "folder": "/path/to/output/Example Paper",
  "markdown_files": [
    "Example Paper.md",
    "示例论文.md"
  ],
  "errors": [],
  "warnings": [],
  "valid": true
}
```

其中，`errors` 表示必须修复的交付问题；`warnings` 表示需要人工复核的情况，例如仍引用远程图片或检测到疑似网页导航文字。

## 输出格式

技能以规范化后的英文论文题名创建目录：

```text
<Original paper title>/
├── <Original paper title>.md
├── <Chinese translated title>.md
└── assets/
    ├── figure-001.png
    ├── figure-002.jpg
    └── ...
```

Markdown 中使用相对资源路径：

```markdown
![Figure caption](assets/figure-001.png)
```

Windows 文件名中的非法字符会被替换，末尾句点和空格会被移除，过长目录名会被安全缩短；文档内部显示的论文题名不会因此改变。

## 翻译原则

- **不摘要、不扩写、不改写论断**，保持作者原有的证据强度和不确定性。
- **保持段落顺序与标题层级**，保留编号、引文、脚注标记和交叉引用。
- **专业术语首次出现时可采用“中文译名（English term）”**，后文保持译法一致。
- **基因符号、化学式、模型标识、变量、SI 单位、DOI、URL 和登录号保持不变**。
- **公式符号和编号不翻译**；复杂 MathML、LaTeX 和 HTML 表格在转换会损失语义时保留原格式。
- **参考文献默认保留原语言**，只翻译章节标题和说明性文字。

## 设计原则与限制

1. **不虚构缺失内容**：缺失的段落、元数据、公式、图注或参考文献不会被猜测补齐。
2. **不擅自下载远程资源**：默认仅处理用户提供的本地文件；远程图片保留原 URL 并作为警告报告。
3. **优先保证学术语义**：Markdown 无法无损表达复杂公式、SVG 或表格时，保留原始 HTML。
4. **不静默覆盖结果**：已有非空题名目录必须由用户明确处理或更换输出位置。
5. **提取结果需要复核**：出版商页面结构差异很大，确定性提取后仍需逐节检查正文边界、公式、图表和参考文献。

## 常见问题

### 提示 `This extractor requires lxml`

当前 Python 环境缺少 `lxml`。运行 `python -m pip install lxml`，或改用包含该依赖的 Codex Python 运行时。

### 输出中缺少论文图片

确认 HTML 旁边的配套资源目录仍在原位置，并检查图片是否只存在于远程服务器、CSS 背景或受登录权限保护。远程资源默认不会自动下载。

### 提示拒绝覆盖输出目录

目标题名目录已经存在且非空。为防止覆盖既有译文和图片，请指定新的 `--output-root` 或 `--folder-name`。

### 输出包含网站导航或推荐内容

自动正文识别对少数出版商页面可能不够精确。应对照原始 HTML 调整英文 Markdown，并在删除内容前确认其确实不属于论文正文。

### 校验器报告远程图片警告

这表示 Markdown 仍引用 `http://`、`https://` 或协议相对 URL。警告不会自动伪装为本地化成功，应在获得授权并补齐资源后再次校验。

## 贡献

欢迎提交 Issue 或 Pull Request，尤其是以下改进：

- 新的出版商页面结构适配。
- 更稳健的正文、公式、图表和脚注提取。
- 面向真实论文样本的回归测试。
- 术语一致性和中英文结构校验。
- Windows、macOS 与 Linux 的兼容性改进。

提交真实论文样本前，请确认其版权许可允许公开分发；更推荐提供可公开使用的最小化测试夹具。

## 致谢

本项目采用“**确定性脚本负责提取与校验，智能体负责语义复核与忠实翻译**”的分工方式，目标是在可追溯性、学术完整性和自动化效率之间取得平衡。
