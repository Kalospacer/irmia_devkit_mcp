"""MCP 结果适配：把共享核心的后续调用参数映射到公开入口。"""


def adapt_result(value):
    """递归保留结果字段，仅修正已知的 file_diff 参数别名。"""
    if isinstance(value, list):
        return [adapt_result(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: adapt_result(item) for key, item in value.items()}
    if result.get("tool") == "file_diff" and isinstance(result.get("params"), dict):
        params = result["params"]
        for old, new in (("file_a", "file1"), ("file_b", "file2")):
            if old in params:
                params[new] = params.pop(old)
    return result
