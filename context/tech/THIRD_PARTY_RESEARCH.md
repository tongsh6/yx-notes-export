# 第三方项目调研

调研时间：2026-02

## 参考项目一览

### 1. evernote-backup（★ 1.4k）
- **地址**：https://github.com/vzhd1701/evernote-backup
- **定位**：完整备份方案，支持增量同步、断点续传
- **认证**：OAuth / Developer Token / 用户名+密码（印象笔记中国区均支持）
- **特色**：SQLite 本地缓存、USN（updateSequenceNumber）增量跟踪
- **局限**：只导出 .enex，不做 Markdown 转换
- **对本项目价值**：认证流程和增量同步机制的最佳参考

### 2. ExportAllEverNote（★ 38）
- **地址**：https://github.com/dong-s/ExportAllEverNote
- **定位**：轻量 ENEX 批量导出，按 stack→notebook 目录结构落盘
- **认证**：Developer Token
- **特色**：层级目录生成逻辑简洁清晰（可直接参考）
- **局限**：Python 2.7，不导出标签，不转 Markdown
- **对本项目价值**：目录生成逻辑参考（`notebook.stack` 属性使用）

### 3. enex2md（★ 16，已归档）
- **地址**：https://github.com/janik6n/enex2md
- **定位**：本地 ENEX → Markdown 转换器
- **特色**：支持 GFM（表格、任务列表、代码块），附件处理，元数据保留
- **局限**：已停止维护，不直接连接 API
- **对本项目价值**：ENML 转换规则参考

### 4. zibuyu_evernote（★ 2）
- **地址**：https://github.com/zibuyu2015831/zibuyu_evernote
- **定位**：对官方 SDK 的 Python 3 现代化封装
- **特色**：类型注解，Markdown ↔ 印象笔记双向转换
- **对本项目价值**：Python 3 SDK 封装方式参考

## 关键技术结论

### 认证
- `evernote-backup` 已验证：印象笔记中国区支持用户名+密码直接初始化
  ```bash
  evernote-backup init-db --backend china --user <username> --password <password>
  ```
- Developer Token 最简单，从 https://app.yinxiang.com/api/DeveloperToken.action 获取

### 层级结构遍历
```python
notebooks = note_store.listNotebooks()
for nb in notebooks:
    stack = nb.stack or ""   # 无分组时为 None
    path = os.path.join(output, stack, nb.name) if stack else os.path.join(output, nb.name)
```

### ENML 特殊标签处理
- `<en-media hash="...">` → 根据 hash 匹配 resource，替换为 Markdown 图片/链接
- `<en-todo checked="true"/>` → `- [x]`，`checked="false"` → `- [ ]`
- `<en-crypt>` → 保留为提示文字（加密内容无法解密）

### 推荐库组合
```
evernote-sdk-python3  → API 调用
beautifulsoup4        → ENML 预处理（特殊标签替换）
html2text             → HTML → Markdown
PyYAML                → Front Matter 生成
click                 → CLI
tqdm                  → 进度显示
```

## 官方文档
- API 文档：https://dev.yinxiang.com/doc/
- Python SDK：https://github.com/yinxiang-dev/evernote-sdk-python
- Developer Token：https://app.yinxiang.com/api/DeveloperToken.action
- 认证文档：https://dev.yinxiang.com/doc/articles/authentication.php
