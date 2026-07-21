from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pyatv_http.cli import build_parser, default_config_path, main


def test_serve_subcommand_runs_uvicorn():
    fake_config = MagicMock(port=8080)
    fake_app = MagicMock()

    with (
        patch("pyatv_http.cli.load_config", return_value=fake_config) as mock_load,
        patch("pyatv_http.cli.create_app", return_value=fake_app) as mock_create_app,
        patch("pyatv_http.cli.uvicorn.run") as mock_run,
    ):
        main(["serve", "--config", "config.toml"])

    mock_load.assert_called_once_with("config.toml")
    mock_create_app.assert_called_once_with(fake_config)
    mock_run.assert_called_once_with(fake_app, host="0.0.0.0", port=8080)


def test_serve_uses_default_config_path_when_not_given():
    fake_config = MagicMock(port=8080)

    with (
        patch("pyatv_http.cli.load_config", return_value=fake_config) as mock_load,
        patch("pyatv_http.cli.create_app", return_value=MagicMock()),
        patch("pyatv_http.cli.uvicorn.run"),
        patch(
            "pyatv_http.cli.default_config_path",
            return_value=Path("/fake/config.toml"),
        ),
    ):
        main(["serve"])

    mock_load.assert_called_once_with(Path("/fake/config.toml"))


def test_default_config_path_uses_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert default_config_path() == tmp_path / "pyatv-http" / "config.toml"


def test_default_config_path_falls_back_to_dot_config(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    assert (
        default_config_path() == Path.home() / ".config" / "pyatv-http" / "config.toml"
    )


def test_gen_config_subcommand_prints_block(capsys):
    with patch(
        "pyatv_http.cli.generate_config_block",
        new=AsyncMock(return_value="[devices.living_room]\n"),
    ) as mock_gen:
        main(
            [
                "gen-config",
                "--identifier",
                "AA:BB:CC:DD:EE:FF",
                "--key",
                "living_room",
                "--address",
                "10.0.0.5",
            ]
        )

    captured = capsys.readouterr()
    assert "[devices.living_room]" in captured.out
    assert mock_gen.await_args is not None
    assert mock_gen.await_args.kwargs["identifier"] == "AA:BB:CC:DD:EE:FF"
    assert mock_gen.await_args.kwargs["key"] == "living_room"
    assert mock_gen.await_args.kwargs["address"] == "10.0.0.5"


def test_gen_config_defaults_storage_to_none():
    parser = build_parser()
    args = parser.parse_args(
        ["gen-config", "--identifier", "id", "--key", "k", "--address", "1.2.3.4"]
    )

    assert args.storage is None


def test_gen_config_reports_error_and_exits(capsys):
    from pyatv_http.gen_config import DeviceNotFoundError

    with patch(
        "pyatv_http.cli.generate_config_block",
        new=AsyncMock(side_effect=DeviceNotFoundError("no such device")),
    ):
        try:
            main(
                [
                    "gen-config",
                    "--identifier",
                    "bogus",
                    "--key",
                    "k",
                    "--address",
                    "1.2.3.4",
                ]
            )
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError("expected SystemExit")

    captured = capsys.readouterr()
    assert "no such device" in captured.err
