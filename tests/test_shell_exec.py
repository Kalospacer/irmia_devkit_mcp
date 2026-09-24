"""Tests for shell_exec safe command wrapper."""

import subprocess

from tools.shell_exec import run, split_command, truncate_output, validate_command


class TestShellExec:
    def test_rejects_shell_control_chars(self):
        try:
            split_command("pytest -q; echo bad")
        except ValueError as exc:
            assert "shell control" in str(exc)
        else:
            raise AssertionError("expected ValueError")

    def test_rejects_path_separator_in_command(self):
        result = run(r"C:\Python\python -m pytest", dry_run=True)
        assert result["ok"] is False
        assert "bare executable name" in result.get("error", "")

    def test_allows_pytest_dry_run(self):
        result = run("pytest -q", dry_run=True)
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["args"] == ["pytest", "-q"]

    def test_blocks_unknown_command(self):
        result = validate_command(["powershell", "Get-ChildItem"])
        assert result["ok"] is False
        assert "not allowed" in result["error"]

    def test_high_risk_requires_flag(self):
        result = validate_command(["pip", "install", "pytest"])
        assert result["ok"] is False
        assert result["evidence"]["risk"] == "high"

    def test_truncate_output_keeps_head_and_tail(self):
        text = "\n".join(f"line {i}" for i in range(20))
        truncated, flag = truncate_output(text, max_lines=5)
        assert flag is True
        assert "line 0" in truncated
        assert "line 19" in truncated
        assert "omitted" in truncated

    def test_nonzero_exit_is_not_ok(self):
        result = run("python -m pytest missing_test_file.py", timeout=10)
        assert result["ok"] is False
        assert result["returncode"] != 0
        assert "exited with code" in result["error"]

    def test_timeout_bytes_output_is_decoded(self, monkeypatch):
        class FakeProc:
            pid = 1
            returncode = -9
            calls = 0

            def communicate(self, timeout=None):
                self.calls += 1
                if self.calls == 1:
                    raise subprocess.TimeoutExpired(cmd="pytest", timeout=timeout, output=b"partial stdout", stderr=b"partial stderr")
                return "partial stdout", "partial stderr"

            def kill(self):
                pass

        monkeypatch.setattr("tools.shell_exec.subprocess.Popen", lambda *a, **k: FakeProc())
        monkeypatch.setattr("tools.shell_exec.subprocess.run", lambda *a, **k: None)

        result = run("python -m pytest tests", timeout=1)

        assert result["ok"] is False
        assert result["stdout"] == "partial stdout"
        assert result["stderr"] == "partial stderr"

    def test_timeout_clamped_to_600(self, monkeypatch):
        """timeout 上限 600 秒，防止误传超大值导致进程悬挂。"""
        captured = {}

        class FakeProc:
            pid = 1
            returncode = -9
            calls = 0

            def communicate(self, timeout=None):
                if timeout is not None:
                    captured["timeout"] = timeout
                self.calls += 1
                if self.calls == 1:
                    raise subprocess.TimeoutExpired(cmd="pytest", timeout=timeout)
                return "", ""

            def kill(self):
                pass

        monkeypatch.setattr("tools.shell_exec.subprocess.Popen", lambda *a, **k: FakeProc())
        monkeypatch.setattr("tools.shell_exec.subprocess.run", lambda *a, **k: None)

        run("python -m pytest tests", timeout=99999)

        assert captured["timeout"] == 600
