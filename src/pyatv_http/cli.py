from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import uvicorn

from pyatv_http.app import create_app
from pyatv_http.config import load_config
from pyatv_http.gen_config import DeviceNotFoundError, generate_config_block

DEFAULT_STORAGE_PATH = Path.home() / ".pyatv.conf"


def default_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    config_home = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return config_home / "pyatv-http" / "config.toml"


def _serve(args: argparse.Namespace) -> None:
    config_path = args.config or default_config_path()
    config = load_config(config_path)
    app = create_app(config)
    uvicorn.run(app, host=args.host, port=config.port)


def _gen_config(args: argparse.Namespace) -> None:
    storage_path = args.storage or DEFAULT_STORAGE_PATH
    try:
        block = asyncio.run(
            generate_config_block(
                storage_path=storage_path,
                identifier=args.identifier,
                key=args.key,
                name=args.name,
                address=args.address,
            )
        )
    except DeviceNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    print(block)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyatv-http")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the HTTP server")
    serve.add_argument(
        "--config",
        default=None,
        help=f"Path to the config TOML file (default: {default_config_path()})",
    )
    serve.add_argument("--host", default="0.0.0.0", help="Interface to bind to")
    serve.set_defaults(func=_serve)

    gen_config = subparsers.add_parser(
        "gen-config",
        help="Generate a [devices.<key>] config block from an atvremote pairing",
    )
    gen_config.add_argument(
        "--storage",
        default=None,
        help=f"Path to atvremote's storage file (default: {DEFAULT_STORAGE_PATH})",
    )
    gen_config.add_argument(
        "--identifier", required=True, help="Device identifier to look up"
    )
    gen_config.add_argument(
        "--key", required=True, help="Config key / URL path segment for this device"
    )
    gen_config.add_argument("--name", default=None, help="Display name (default: key)")
    gen_config.add_argument(
        "--address", required=True, help="IP address or hostname of the Apple TV"
    )
    gen_config.set_defaults(func=_gen_config)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
