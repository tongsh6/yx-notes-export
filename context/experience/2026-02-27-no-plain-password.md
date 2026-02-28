# 不保存明文密码的配置策略

## 背景
为降低账号泄露风险，需要避免在 `config.yaml` 中保存明文密码。

## 现象
- 旧逻辑会将 `auth.password` 写入配置文件。
- 历史配置可能仍包含明文密码。

## 结论
- 密码模式连接成功后，仅保存 API 返回的 Token。
- 读取配置时忽略 `auth.password` 字段，避免回填旧密码。
- 仅保存 `username` / `consumer_key` / `consumer_secret`，不保存密码。

## 影响
- 提升安全性；用户需要在需要时手动输入密码。
