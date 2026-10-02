"""上游新能力在 MCP 公开入口和编辑链中的回归测试。"""
import json
from pathlib import Path

import pytest

from mcp_results import adapt_result
from tools import config, multi_edit, safe_edit, safe_write, syntax_check


@pytest.fixture
def backups(tmp_path):
    config.set_config({"backup_dir": str(tmp_path / "backups")})
    return tmp_path


@pytest.mark.parametrize("suffix,before,after", [
    (".json", '{"value": 1}', '{"value": }'),
    (".toml", 'value = 1', 'value = '),
    (".yaml", 'value: [1]', 'value: ['),
])
def test_new_formats_are_checked_and_restored(backups, suffix, before, after):
    target = backups / ("config" + suffix)
    target.write_text(before, encoding="utf-8")
    result = safe_edit.edit(str(target), before, after)
    assert result["ok"] is False
    assert result["rolled_back"] is True
    assert target.read_text(encoding="utf-8") == before
    assert syntax_check.supports(target)


def test_multi_edit_rejects_bad_json_before_any_commit(backups):
    a, b = backups / "a.txt", backups / "b.json"
    a.write_text("before", encoding="utf-8")
    b.write_text('{"value": 1}', encoding="utf-8")
    result = multi_edit.run([
        {"file": str(a), "old": "before", "new": "after"},
        {"file": str(b), "old": "1", "new": ""},
    ])
    assert result["ok"] is False
    assert a.read_text(encoding="utf-8") == "before"
    assert b.read_text(encoding="utf-8") == '{"value": 1}'


@pytest.mark.parametrize("ok", [True, False])
def test_skipped_check_never_claims_success(backups, monkeypatch, ok):
    fake = lambda _path: {"ok": ok, "skipped": True, "reason": "test checker unavailable"}
    monkeypatch.setattr(safe_edit, "syntax_check", fake)
    monkeypatch.setattr(safe_write, "syntax_check", fake)
    target = backups / "example.py"
    target.write_text("value = 1\n", encoding="utf-8")
    result = safe_edit.edit(str(target), "1", "2")
    assert result["ok"] is True
    assert result["syntax_ok"] is None
    result = safe_write.write(str(target), "value = 3\n", overwrite=True)
    assert result["syntax_ok"] is None
    created = safe_write.write(str(backups / "new.py"), "value = 4\n")
    assert created["syntax_ok"] is None


def test_public_mcp_schema_exposes_core_parameters():
    import server
    tools = {tool.name: tool for tool in server.mcp._tool_manager.list_tools()}
    assert len(tools) == 60
    edit = tools["safe_edit"].parameters
    assert {"mode", "line", "start_line", "end_line", "align_whitespace"} <= edit["properties"].keys()
    assert "old" not in edit.get("required", [])
    assert "new" not in edit.get("required", [])
    for tool in ("file_patch", "file_preview"):
        assert {"occurrence", "preserve_inner_indent"} <= tools[tool].parameters["properties"].keys()
    assert tools["safe_read"].parameters["properties"]["include_metadata"]["default"] is False
    assert "line_numbers" in tools["safe_read"].parameters["properties"]
    assert "files_or_dir" in tools["file_zip"].parameters["properties"]
    schema = tools["db_query"].parameters["properties"]["params"]
    assert any("items" in node for node in schema.get("anyOf", [schema]))


def test_public_edit_modes_and_empty_new(backups, monkeypatch):
    import server
    monkeypatch.setattr(server, "_auto_index", lambda _path: None)
    target = backups / "text.txt"
    target.write_bytes(b"first\r\nsecond\r\n")
    result = json.loads(server.safe_edit(str(target), mode="insert_at_line", line=0, new="header\n"))
    assert result["ok"] is True
    result = json.loads(server.safe_edit(str(target), mode="delete_lines", start_line=2, end_line=2))
    assert result["ok"] is True
    result = json.loads(server.safe_edit(str(target), old="second", new=""))
    assert result["ok"] is True
    assert b"\r\n" in target.read_bytes()


def test_public_read_can_disable_line_numbers(backups):
    import server
    target = backups / "text.txt"
    target.write_text("first\n", encoding="utf-8")
    result = json.loads(server.safe_read(str(target), line_numbers=False))
    assert result["content"] == "first"


def test_zip_compatible_single_source_and_multiple_sources(backups):
    import server
    a, b = backups / "a.txt", backups / "b.txt"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    assert json.loads(server.file_zip(source=str(a)))["ok"] is True
    assert json.loads(server.file_zip(files_or_dir=[str(a), str(b)], output=str(backups / "both.zip")))["ok"] is True
    assert json.loads(server.file_zip(files_or_dir=[str(a), str(b)]))["ok"] is False
    assert json.loads(server.file_zip(source=str(a), files_or_dir=[str(b)]))["ok"] is False


def test_http_post_object_body_is_preserved(monkeypatch):
    import server
    calls = []
    monkeypatch.setattr(server, "_http_post", lambda url, **kwargs: calls.append(kwargs) or {"ok": True})
    server.http_post("https://example.org", data={"value": 1})
    server.http_post("https://example.org", data='{"value": 2}')
    assert [call["data"] for call in calls] == [{"value": 1}, {"value": 2}]


def test_followup_diff_parameters_match_public_schema():
    result = adapt_result({"ok": False, "options": [{"tool": "file_diff", "params": {"file_a": "old", "file_b": "new"}}]})
    assert result["options"][0]["params"] == {"file1": "old", "file2": "new"}


def test_jsx_and_tsx_remain_nonblocking(tmp_path):
    for suffix in (".jsx", ".tsx"):
        path = tmp_path / ("Component" + suffix)
        path.write_text("export const Widget = () => <div />;", encoding="utf-8")
        result = syntax_check.check(str(path))
        assert result["skipped"] is True


def test_missing_new_checker_is_nonblocking_for_multi_edit(backups, monkeypatch):
    monkeypatch.setattr(multi_edit, "syntax_check_file", lambda _path: {"ok": False, "skipped": True})
    path = backups / "example.rs"
    path.write_text("fn old() {}", encoding="utf-8")
    result = multi_edit.run([{"file": str(path), "old": "old", "new": "new"}])
    assert result["ok"] is True
    assert path.read_text(encoding="utf-8") == "fn new() {}"
    assert result["syntax_ok"] is None
    assert result["syntax_checks"][str(path)]["skipped"] is True


def test_java_parser_ignores_filename_and_missing_dependencies(tmp_path):
    import shutil
    if not shutil.which("javac") or not shutil.which("java"):
        pytest.skip("JDK unavailable")
    path = tmp_path / "random.java"
    path.write_text("public class Foo { UnknownType field; }", encoding="utf-8")
    result = syntax_check.check(str(path))
    assert result["ok"] is True, result
    path.write_text("public class { }", encoding="utf-8")
    result = syntax_check.check(str(path))
    assert result["ok"] is False
    assert result["errors"][0]["line"] == 1
