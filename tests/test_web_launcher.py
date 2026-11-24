"""Inicialização web sem servidor, chave real ou chamadas externas."""

import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-web.sh"


def launcher_project(tmp_path):
    root = tmp_path / "projeto com espaços"
    (root / "scripts").mkdir(parents=True)
    shutil.copyfile(SCRIPT, root / "scripts" / SCRIPT.name)
    (root / ".venv-web" / "bin").mkdir(parents=True)
    python = root / ".venv-web" / "bin" / "python"
    python.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n', encoding="utf-8")
    python.chmod(0o700)
    (root / ".env").write_text(
        "NVIDIA_API_KEY=nvapi-chave-ficticia\nUNUSED=$(touch executado)\n", encoding="utf-8"
    )
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "uvicorn.py").write_text(
        "import os, json\n"
        "def run(app, **kwargs):\n"
        "    assert os.environ['NVIDIA_API_KEY'] == os.environ['EXPECTED_KEY']\n"
        "    print(json.dumps(dict(app=app, cwd=os.getcwd(), **kwargs)))\n",
        encoding="utf-8",
    )
    env = dict(os.environ, PYTHONPATH=str(stub), PORT="8123", EXPECTED_KEY="nvapi-chave-ficticia")
    env.pop("NVIDIA_API_KEY", None)
    return root, env


@pytest.mark.parametrize("environment_key", [None, "nvapi-chave-ambiente-ficticia"])
def test_launcher_uses_project_root_dotenv_and_loopback(tmp_path, environment_key):
    root, env = launcher_project(tmp_path)
    if environment_key:
        env.update(NVIDIA_API_KEY=environment_key, EXPECTED_KEY=environment_key)

    result = subprocess.run(
        ["bash", str(root / "scripts" / SCRIPT.name)], cwd=tmp_path, env=env,
        capture_output=True, text=True, check=True,
    )

    assert json.loads(result.stdout) == {
        "app": "academic_assistant.web:app", "cwd": str(root),
        "host": "127.0.0.1", "port": 8123, "access_log": False,
    }
    assert not (root / "executado").exists()
    assert "nvapi-chave" not in result.stdout + result.stderr


def test_launcher_without_environment_explains_setup(tmp_path):
    root, env = launcher_project(tmp_path)
    (root / ".venv-web" / "bin" / "python").unlink()

    result = subprocess.run(
        ["bash", str(root / "scripts" / SCRIPT.name)], env=env,
        capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "uv sync" in result.stderr
    assert ".venv-web" in result.stderr


def test_launcher_without_key_does_not_start_server(tmp_path):
    root, env = launcher_project(tmp_path)
    (root / ".env").unlink()

    result = subprocess.run(
        ["bash", str(root / "scripts" / SCRIPT.name)], env=env,
        capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "NVIDIA_API_KEY" in result.stderr
    assert not result.stdout
