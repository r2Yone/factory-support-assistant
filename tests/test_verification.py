"""Pruebas del corredor de verificaciones, sin correr el producto."""

import subprocess

import verification.__main__ as runner


def test_unknown_step_shows_usage(capsys):
    assert runner.run("deploy") == 2
    assert "Uso:" in capsys.readouterr().out


def test_missing_product_fails_with_a_clear_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runner, "PRODUCT", tmp_path / "product")
    assert runner.run("unit") == 1
    assert "todavía no existe product/app/" in capsys.readouterr().out


def test_step_returns_the_exit_code_of_pytest(tmp_path, monkeypatch, capsys):
    (tmp_path / "product" / "app").mkdir(parents=True)
    monkeypatch.setattr(runner, "PRODUCT", tmp_path / "product")
    calls = []

    def fake_run(command, cwd, env, check):
        calls.append((command, cwd, env, check))
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run("contract") == 1
    assert "verification/contract" in calls[0][0]
    assert "[FAIL] contract" in capsys.readouterr().out


def test_contract_can_stop_at_the_specification_being_built(tmp_path, monkeypatch):
    (tmp_path / "product" / "app").mkdir(parents=True)
    monkeypatch.setattr(runner, "PRODUCT", tmp_path / "product")
    commands = []

    def fake_run(command, **_):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run("contract", ["03"]) == 0
    files = [part for part in commands[0] if part.startswith("verification/")]
    assert files == [
        "verification/contract/test_contract.py",
        "verification/contract/test_contract_02.py",
        "verification/contract/test_contract_03.py",
    ]


def test_unit_runs_in_a_standalone_copy_of_the_product(tmp_path, monkeypatch):
    product = tmp_path / "product"
    (product / "app").mkdir(parents=True)
    personal_config = "." + "env"
    (product / personal_config).write_text("x", encoding="utf-8")
    monkeypatch.setattr(runner, "PRODUCT", product)
    monkeypatch.setitem(runner.STEPS, "unit", (["pytest"], product))
    seen = []

    def fake_run(command, cwd, **_):
        seen.append((cwd, sorted(path.name for path in cwd.iterdir())))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run("unit") == 0
    folder, files = seen[0]
    assert folder != product
    assert files == ["app"]


def test_steps_never_read_the_personal_config_file(tmp_path, monkeypatch):
    product = tmp_path / "product"
    (product / "app").mkdir(parents=True)
    monkeypatch.setattr(runner, "PRODUCT", product)
    monkeypatch.setitem(runner.STEPS, "unit", (["pytest"], product))
    monkeypatch.setenv("ENV_FILE", "personal")
    envs = []

    def fake_run(command, env, **_):
        envs.append(env)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    assert runner.run("unit") == 0
    assert envs[0]["ENV_FILE"] == "none"
