# 技术架构

## 目标
- 通过印象笔记官方 API（Thrift 协议）获取笔记数据
- 支持多种导出粒度（全量 / 指定笔记本 / 指定笔记）
- 按层级结构（stack → notebook → note）写入输出目录
- ENML 正文转换为 Markdown，附件单独展平并内联引用

## 处理流程（高层）
1. **认证**：加载配置，初始化 EvernoteClient，获取 NoteStore
2. **拉取结构**：`listNotebooks()` 获取所有笔记本（含 stack 属性）
3. **过滤范围**：根据用户参数决定导出哪些笔记本/笔记
4. **分页下载**：`findNotesMetadata()` 分页获取笔记列表，`getNote()` 获取完整内容
5. **附件处理**：`getResource()` 获取附件二进制数据，按命名规则落盘
6. **格式转换**：ENML → Markdown，注入附件相对路径
7. **写入输出**：按 stack/notebook 目录层级写入 .md 文件

## 运行时兼容性
- **Python 3.11+ 兼容**：`evernote3` 依赖 `inspect.getargspec`，在 Python 3.11+ 被移除，
  已在 `src/auth.py` 注入兼容垫片（将 `getfullargspec` 映射为 `getargspec`）。

## 限流与重试策略
- API 调用统一通过 `_with_retry(...)` 包装（`src/fetcher.py`），
  捕获 `EDAMSystemException` 的 `RATE_LIMIT_REACHED`（errorCode=19），
  根据 `rateLimitDuration` 等待后重试（最多 3 次），其他异常直接抛出。

## 项目目录结构
```
yx-notes-export/
├── main.py                  # CLI 入口（命令参数解析、主流程调度）
├── config.yaml              # 用户配置（Token/用户名密码、输出目录）
├── src/
│   ├── auth.py              # 认证模块：加载 Token / 用户名密码，初始化 Client
│   ├── fetcher.py           # 数据获取：笔记本列表、笔记列表、笔记内容、附件
│   ├── converter.py         # 格式转换：ENML/HTML → Markdown
│   ├── exporter.py          # 输出模块：目录创建、文件命名、内容写入
│   └── utils.py             # 通用工具：安全文件名、去重、时间格式化
├── tests/
│   ├── test_gui_e2e.py          # GUI 端到端（mock worker，不依赖 API）
│   ├── test_gui_e2e_real_api.py # GUI 端到端（真实 API，需 YX_TOKEN）
│   ├── test_e2e_real_api.py     # CLI 端到端（真实 API，需 YX_TOKEN）
│   └── test_*.py
└── requirements.txt
```

## 核心依赖库

| 库 | 用途 | 说明 |
|-----|------|------|
| `evernote-sdk-python3` | API 客户端 | 印象笔记官方 SDK，支持中国区 (`china=True`) |
| `html2text` | ENML 转 Markdown | 成熟库，支持表格、列表、代码块 |
| `beautifulsoup4` | ENML 预处理 | 处理 `<en-media>` / `<en-todo>` 等印象笔记特有标签 |
| `PyYAML` | Front Matter | 生成 YAML 元数据头 |
| `click` 或 `argparse` | CLI | 命令行参数解析 |
| `tqdm` | 进度显示 | 批量导出进度条 |
| `pytest` / `pytest-qt` | 测试 | 单元测试 + GUI 端到端测试 |

## 关键 API 调用
```python
# 初始化（Developer Token 方式）
client = EvernoteClient(token=dev_token, sandbox=False, china=True)
note_store = client.get_note_store()

# 获取层级结构
notebooks = note_store.listNotebooks()   # 含 notebook.stack 属性

# 分页获取笔记列表
filter = NoteFilter(notebookGuid=nb.guid)
spec = NotesMetadataResultSpec(includeTitle=True, includeCreated=True)
meta = note_store.findNotesMetadata(filter, offset, max_notes, spec)

# 获取完整笔记内容
note = note_store.getNote(guid, withContent=True, withResourcesData=True, ...)

# 获取附件二进制
resource = note_store.getResource(res_guid, withData=True, ...)
```

## ENML 处理要点
- `<en-note>` 根标签 → 跳过，只转内容
- `<en-media hash='...'>` → 根据 hash 匹配附件，替换为 `![](assets/...)` 或 `[](assets/...)`
- `<en-todo checked='...'/>` → `- [x]` / `- [ ]`
- `<br/>` → 换行

## 认证配置（config.yaml 结构）
```yaml
auth:
  # 方式一：Developer Token（优先）
  token: S=s1:U=xxx:E=xxx:C=xxx:...
  # 方式二：用户名+密码（按需选用）
  # username: your_username
  # consumer_key: your_key
  # consumer_secret: your_secret

export:
  output_dir: ./output
  format: markdown  # 期待后续扩展
```

## 输出策略
- Markdown 文件 UTF-8 编码
- YAML Front Matter 包含标题、时间、标签、来源
- 附件相对路径引用（`./assets/filename`），确保移动目录后可用
- API 频率限制：导出间隔加延时处理（印象笔记 API 有调用频率限制）

## 断点续传与失败记录
- 每个笔记本目录生成 `.export-index.json`，记录 guid + updated + 路径
- 若 guid 已存在且 updated 未变化，则跳过导出并计入跳过数
- GUI 端导出完成会输出“跳过清单”（最多展示 50 条）
- 可选生成 `export-failures.txt` 记录失败条目与错误信息

## 测试与验证
- 离线/GUI mock：`python -m pytest`
- 真实 API：设置 `YX_TOKEN` 后运行 `python -m pytest tests/test_e2e_real_api.py tests/test_gui_e2e_real_api.py -q`

## 测试执行指南
### 1) 离线单元测试 + GUI mock e2e
```
python -m pytest
```

### 2) 真实 API 端到端（CLI + GUI）
```
# Windows (cmd)
set YX_TOKEN=你的token
python -m pytest tests/test_e2e_real_api.py tests/test_gui_e2e_real_api.py -q
```

### 3) 生成 GUI 测试截图（可选）
```
# 仅在需要时输出截图
set YX_SCREENSHOT=1
python -m pytest tests/test_gui_e2e.py -q
```
