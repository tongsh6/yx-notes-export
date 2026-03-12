# 跨平台版本发布脚本与 GitHub Release

## 背景
需要可重复的发布流程：更新版本号、归并 CHANGELOG、打 tag、推送，并在 GitHub 上创建 Release，且能在 Windows/macOS/Linux 运行。

## 现象
- 手动改 VERSION、剪贴 CHANGELOG、git commit/tag 易漏步或出错。
- 推送 tag 后 GitHub 上不会自动出现“Release”说明页，需在网页或 gh 再操作一次。

## 结论
- **发布脚本**（如 `scripts/release_version.py`）：用 Python 统一完成：读 VERSION、按 --bump 或 --version 计算新号、写回 VERSION、用正则把 CHANGELOG 中 `## [Unreleased]` 下内容归入 `## [X.Y.Z] - 日期`、git add/commit/tag；可选 --push 推送分支与 tag。跨平台仅用 subprocess 调 git，避免 shell 差异。
- **GitHub Release**：在 --push 且推送 tag 成功后，调用 `gh release create <tag> --title <tag> --notes-file <临时文件>`；Release 说明从 CHANGELOG 中提取该版本区块（正则匹配 `## [X.Y.Z] - ...` 到下一 `## [`）写入临时文件。若未安装或未登录 gh，仅打警告不中断。
- 脚本参数建议：--bump patch|minor|major、--version X.Y.Z、--dry-run、--no-commit（只改文件不提交）。

## 影响
- 一次命令完成版本号、日志、提交、tag、推送与 Release；新成员或 CI 可复用同一脚本。
- 文档中注明“需 gh 以创建 GitHub Release”，README 与 scripts/README 保持一致。
