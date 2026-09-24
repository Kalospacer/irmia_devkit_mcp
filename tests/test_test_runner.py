"""Tests for test_runner discovery and parsing."""

import subprocess
from pathlib import Path

from tools import test_runner


class TestTestRunner:
    def test_default_discovers_pytest(self, tmp_dir):
        framework, args = test_runner.discover(Path(tmp_dir))
        assert framework == "pytest"
        assert args[-3:] == ["pytest", "-q", "--tb=short"]

    def test_discovers_go(self, tmp_dir):
        Path(tmp_dir, "go.mod").write_text("module example\n", encoding="utf-8")
        framework, args = test_runner.discover(Path(tmp_dir))
        assert framework == "go"
        assert args[:2] == ["go", "test"]

    def test_parse_pytest_summary(self):
        result = test_runner._parse_pytest(
            "FAILED tests/test_a.py::test_x - AssertionError\n= 1 failed, 2 passed, 3 skipped in 0.12s =",
            "",
            1,
            0.12,
            False,
        )
        assert result["ok"] is False
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["skipped"] == 3
        assert result["errors"][0]["test"] == "tests/test_a.py::test_x"

    def test_rejects_unsafe_custom_command(self, tmp_dir):
        result = test_runner.run(project_dir=tmp_dir, test_cmd="pytest -q; echo bad")
        assert result["ok"] is False
        assert "shell control" in result["error"]

    def test_timeout_bytes_output_is_decoded(self, tmp_dir, monkeypatch):
        class FakeProc:
            pid = 1
            returncode = -9
            calls = 0

            def communicate(self, timeout=None):
                self.calls += 1
                if self.calls == 1:
                    raise subprocess.TimeoutExpired(cmd="pytest", timeout=timeout, output=b"1 failed", stderr=b"timeout detail")
                return "1 failed", "timeout detail"

            def kill(self):
                pass

        monkeypatch.setattr("tools.test_runner.subprocess.Popen", lambda *a, **k: FakeProc())
        monkeypatch.setattr("tools.test_runner.subprocess.run", lambda *a, **k: None)

        result = test_runner.run(project_dir=tmp_dir, timeout=1)

        assert result["ok"] is False
        assert result["timeout"] is True
        assert "1 failed" in result["raw_summary"]

    def test_timeout_clamped_to_600(self, tmp_dir, monkeypatch):
        """timeout 上限 600 秒。"""
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

        monkeypatch.setattr("tools.test_runner.subprocess.Popen", lambda *a, **k: FakeProc())
        monkeypatch.setattr("tools.test_runner.subprocess.run", lambda *a, **k: None)

        test_runner.run(project_dir=tmp_dir, timeout=99999)

        assert captured["timeout"] == 600
