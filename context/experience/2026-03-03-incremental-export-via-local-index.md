# 增量导出：基于本地索引过滤

## 背景
用户希望“只导出上次导出后新增或已修改的笔记”，减少全量扫描与 getNote 调用。

## 现象
- 断点续传已在 export_note 内按 .export-index.json 的 updated 跳过，但依然会对每条笔记调用 export_note（含 getNote 前的 should_skip 判断），列表与进度条仍是全量。
- 若在“拉取笔记列表”之后先过滤，再只对需导出的条目调用 export_note，可减少 API 与体感工作量。

## 结论
- 在 Exporter 中提供 `should_export(meta, notebook)` 与 `filter_notes_to_export(metas, notebook)`，复用现有 _ResumeIndex.should_skip，仅语义取反。
- CLI：增加 --incremental，在 fetcher.iter_notes 得到列表后对每个笔记本用 filter_notes_to_export 过滤，再 _export_notes；增量时隐含 resume。
- GUI：增加「仅增量」勾选，Worker 在收集 all_metas 后用 exporter.should_export 过滤 (meta, nb) 再导出；可发 incremental_stats 信号便于界面展示“共 X 条，需导出 Y 条”。
- 不依赖服务端 USN/同步 API，完全基于本地 .export-index.json，实现简单、行为可预期。

## 影响
- 增量与断点续传共用同一索引，逻辑一致；后续若上 USN 可再增加“只拉变更”的拉取层，过滤层可保留。
