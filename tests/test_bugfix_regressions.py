"""Regression tests for security and pagination fixes."""

from tools import git_smart, safe_read, test_runner
from tools._file_utils import detect_encoding
from tools._http_utils import validate_url
from tools.file_remove import move, remove
from tools.rg_search import search as rg_search
from tools.shell_exec import validate_command_args


def test_git_push_rejects_option_injection(monkeypatch):
    calls = []

    def fake_run(cwd, args, timeout=15):
        calls.append(args)
        if args[:2] == ["check-ref-format", "--branch"]:
            return {"ok": True, "stdout": "", "stderr": ""}
        return {"ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(git_smart, "_run_git", fake_run)
    result = git_smart.push(".", branch="--receive-pack=evil")
    assert result["ok"] is False
    assert not any(args[:1] == ["push"] for args in calls)


def test_shell_exec_checks_option_path_values(tmp_path):
    result = validate_command_args(
        ["pytest", "--basetemp=/outside"], tmp_path.resolve()
    )
    assert result is not None
    assert result["ok"] is False


def test_safe_read_tail_does_not_add_trailing_ghost_line(tmp_path):
    path = tmp_path / "tail.txt"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    result = safe_read.read(str(path), tail=1)
    assert result["ok"] is True
    assert result["content"].endswith("│ three")
    assert result["start_line"] == result["end_line"] == 3


def test_detect_encoding_checks_bytes_after_ascii_prefix(tmp_path):
    path = tmp_path / "late-gbk.txt"
    path.write_bytes(("a" * 600).encode("ascii") + "中文".encode("gb18030"))
    assert detect_encoding(path) in {"gb18030", "gbk"}


def test_move_does_not_overwrite_duplicate_names(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    dest = tmp_path / "dest"
    left.mkdir()
    right.mkdir()
    (left / "same.txt").write_text("left", encoding="utf-8")
    (right / "same.txt").write_text("right", encoding="utf-8")
    result = move([str(left / "same.txt"), str(right / "same.txt")], str(dest))
    assert result["ok"] is True
    assert result["moved"] == 1
    assert (dest / "same.txt").read_text(encoding="utf-8") == "left"
    assert (right / "same.txt").exists()


def test_file_remove_requires_confirmation(tmp_path):
    path = tmp_path / "protected-by-confirm.txt"
    path.write_text("x", encoding="utf-8")
    result = remove(str(path))
    assert result["ok"] is False
    assert path.exists()


def test_ssrf_blocks_unspecified_cgnat_and_mapped_addresses():
    for address in ("0.0.0.0", "100.64.0.1", "[::ffff:127.0.0.1]"):
        assert validate_url(f"http://{address}/")["ok"] is False


def test_rg_rejects_alternation_quantifier_redos(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.rg_search._find_rg", lambda: None)
    result = rg_search(r"(a|aa)+$", path=str(tmp_path))
    assert result["ok"] is False
    assert result["error"] == "nested_quantifiers"


def test_test_runner_passes_selected_file_to_pytest(tmp_path, monkeypatch):
    test_file = tmp_path / "test_one.py"
    test_file.write_text("def test_one(): pass\n", encoding="utf-8")
    captured = {}

    def fake_run(args, cwd, timeout):
        captured["args"] = args
        return 0, "1 passed", "", 0.01, False

    monkeypatch.setattr(test_runner, "_run", fake_run)
    result = test_runner.run(filepath=str(test_file), project_dir=str(tmp_path))
    assert result["ok"] is True
    assert result["cmd"].endswith("test_one.py")
    assert captured["args"][-1] == "test_one.py"
