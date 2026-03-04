from __future__ import annotations


def classify_export_error(message: str) -> str:
    text = (message or "").strip().lower()
    if not text:
        return "unknown_error"

    if "rate limit" in text or "rate_limit" in text or "限流" in text:
        return "rate_limit"

    if "timeout" in text or "timed out" in text or "socket" in text or "超时" in text:
        return "network_timeout"

    if (
        "auth" in text
        or "token" in text
        or "unauthorized" in text
        or "认证" in text
        or "凭证" in text
    ):
        return "auth_failed"

    if ("resource" in text or "attachment" in text or "附件" in text) and (
        "fail" in text or "error" in text or "失败" in text or "异常" in text
    ):
        return "resource_fetch_failed"

    if (
        "not found" in text
        or "cannot find" in text
        or "无法找到" in text
        or "未找到" in text
    ):
        return "note_not_found"

    if "permission denied" in text or "forbidden" in text or "权限" in text:
        return "permission_denied"

    return "unknown_error"
