"""
认证模块：支持 Developer Token 和用户名+密码两种方式。
"""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Optional

from evernote.api.client import EvernoteClient


@dataclass
class AuthConfig:
    mode: str  # "token" | "password"
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    consumer_key: Optional[str] = None
    consumer_secret: Optional[str] = None


def build_client(cfg: AuthConfig) -> EvernoteClient:
    """根据配置返回已认证的 EvernoteClient（向后兼容入口）。"""
    _ensure_inspect_getargspec()
    client, _ = build_client_with_token(cfg)
    return client


def build_client_with_token(cfg: AuthConfig) -> tuple[EvernoteClient, str]:
    """
    返回 (client, session_token)。
    - token 模式：session_token 即 cfg.token
    - 密码模式：session_token 来自 authenticateLongSession 返回值，不是明文密码
    """
    _ensure_inspect_getargspec()
    if cfg.mode == "token":
        token = cfg.token
        if not token:
            raise ValueError("认证方式为 token，但 config.yaml 中 auth.token 为空")
        client = _client_by_token(cfg)
        return client, token
    elif cfg.mode == "password":
        return _client_by_password_with_token(cfg)
    else:
        raise ValueError(
            f"不支持的认证方式：{cfg.mode!r}，请设置 'token' 或 'password'"
        )


# ── 方式一：Developer Token ──────────────────────────────────────────────────


def _client_by_token(cfg: AuthConfig) -> EvernoteClient:
    if not cfg.token:
        raise ValueError("认证方式为 token，但 config.yaml 中 auth.token 为空")
    return EvernoteClient(token=cfg.token, sandbox=False, china=True)


# ── 方式二：用户名 + 密码 ────────────────────────────────────────────────────


def _client_by_password(cfg: AuthConfig) -> EvernoteClient:
    """向后兼容包装，忽略返回的 token。"""
    client, _ = _client_by_password_with_token(cfg)
    return client


def _client_by_password_with_token(cfg: AuthConfig) -> tuple[EvernoteClient, str]:
    """
    使用 UserStore.authenticateLongSession 获取 session token,
    再用该 token 构造 EvernoteClient，并将 token 一并返回。
    调用方应保存 token 供后续使用，无需再存储明文密码。
    """
    _validate_password_cfg(cfg)

    bootstrap_client = EvernoteClient(
        consumer_key=cfg.consumer_key,
        consumer_secret=cfg.consumer_secret,
        sandbox=False,
        china=True,
    )
    user_store = bootstrap_client.get_user_store()

    try:
        auth_result = user_store.authenticateLongSession(
            cfg.username,
            cfg.password,
            cfg.consumer_key,
            cfg.consumer_secret,
            "yx-notes-export",  # deviceId
            "yx-notes-export-tool",  # deviceDescription
            False,  # supportsTwoFactor
        )
    except Exception as exc:
        raise RuntimeError(
            f"用户名/密码认证失败：{exc}\n"
            "请检查用户名、密码以及 consumer_key/consumer_secret 是否正确。"
        ) from exc

    token: str = auth_result.token
    client = EvernoteClient(token=token, sandbox=False, china=True)
    return client, token


def _validate_password_cfg(cfg: AuthConfig) -> None:
    missing = [
        field
        for field in ("username", "password", "consumer_key", "consumer_secret")
        if not getattr(cfg, field)
    ]
    if missing:
        raise ValueError(
            f"认证方式为 password，但以下字段为空：{', '.join(missing)}\n"
            "请在 config.yaml 的 auth 节点中补全以上字段。"
        )


def _ensure_inspect_getargspec() -> None:
    """为 Python 3.11+ 兼容 evernote3 依赖的 inspect.getargspec。"""
    if hasattr(inspect, "getargspec"):
        return
    from collections import namedtuple

    ArgSpec = namedtuple("ArgSpec", "args varargs keywords defaults")

    def getargspec(func):
        spec = inspect.getfullargspec(func)
        return ArgSpec(spec.args, spec.varargs, spec.varkw, spec.defaults)

    setattr(inspect, "getargspec", getargspec)
