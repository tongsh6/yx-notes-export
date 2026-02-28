# 工作流声明：GitFlow (Workflow: GitFlow)

## 分支约定
- `main`：生产可发布分支，仅接收 release/hotfix 合并
- `develop`：日常集成分支，功能开发的主入口
- `feature/*`：功能分支，从 `develop` 切出，完成后合并回 `develop`
- `release/*`：发布分支，从 `develop` 切出，用于版本冻结、回归和发布准备
- `hotfix/*`：线上紧急修复分支，从 `main` 切出，修复后同时回合并 `main` 和 `develop`

## 版本规则
- 使用语义化版本：`vMAJOR.MINOR.PATCH`
- 首个公开版本采用 `v0.1.0`
- 每次 release 在 `main` 打 tag，并创建 GitHub Release

## 发布流程（标准）
1. 从 `develop` 切出 `release/vX.Y.Z`
2. 在 release 分支完成版本号、变更说明、回归验证
3. 将 release 合并到 `main` 并打 tag `vX.Y.Z`
4. 将 `main` 回合并到 `develop`，保持分支一致
5. 推送 `main/develop` 与 tag，创建 GitHub Release

## 禁止项
- 禁止直接在 `main` 做日常功能开发
- 禁止未验证测试就发布
- 禁止跳过 `main -> develop` 的回合并
