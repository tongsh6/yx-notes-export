from src.error_codes import classify_export_error


def test_classify_export_error_mapping_cases():
    assert classify_export_error("Rate limit reached") == "rate_limit"
    assert classify_export_error("socket timeout") == "network_timeout"
    assert classify_export_error("认证失败：token invalid") == "auth_failed"
    assert classify_export_error("Resource fetch failed: x") == "resource_fetch_failed"
    assert classify_export_error("失败记录中 GUID 无法找到") == "note_not_found"
    assert classify_export_error("permission denied") == "permission_denied"
    assert classify_export_error("random unknown") == "unknown_error"
