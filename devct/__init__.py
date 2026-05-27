#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

COMPOSE = os.getenv("DEVCT_COMPOSE", "podman-compose")
DEVCT_DIR = ".devct"
COMPOSE_FILE_NAMES = ["compose.yml", "compose.yaml"]

BASIC_COMPOSE = """\
services:
  dev:
    image: docker.io/library/alpine:latest
    volumes:
      - .:/workdir
    working_dir: /workdir
"""


def _find_compose_file(project_path: Path) -> Path:
    project_devct_dir = project_path / DEVCT_DIR
    for compose_file_name in COMPOSE_FILE_NAMES:
        if (compose_file := project_devct_dir / compose_file_name).exists():
            return compose_file
    raise FileNotFoundError(f'No compose file found under "{project_devct_dir}"')


def cmd_init(args: argparse.Namespace) -> None:
    devct_dir = args.project / DEVCT_DIR
    compose_file = devct_dir / "compose.yml"
    if args.dry_run:
        logger.info(devct_dir)
        logger.info(compose_file)
    else:
        devct_dir.mkdir(exist_ok=True)
        compose_file.write_text(BASIC_COMPOSE)
        logger.info("Created %s", compose_file)


def cmd_build(args: argparse.Namespace) -> None:
    compose_file = _find_compose_file(args.project)
    extra = [a for pair in args.podman_build_args for a in pair] if args.podman_build_args else []
    cmd = [COMPOSE, "-f", str(compose_file), "build", *extra, *args.services]
    if args.dry_run:
        logger.info(subprocess.list2cmdline(cmd))
    else:
        subprocess.check_call(cmd, cwd=args.project)


def cmd_run(args: argparse.Namespace) -> None:
    compose_file = _find_compose_file(args.project)
    run_flags = ["--rm"] if args.rm else []
    extra = [a for pair in args.podman_run_args for a in pair] if args.podman_run_args else []
    cmd = [COMPOSE, "-f", str(compose_file), "run", *run_flags, *extra, args.service, *args.args]
    if args.dry_run:
        logger.info(subprocess.list2cmdline(cmd))
    else:
        subprocess.check_call(cmd, cwd=args.project)


def build_parser() -> argparse.ArgumentParser:
    fmt_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=fmt_class)

    parser.add_argument(
        "--project",
        "-p",
        help="Project directory",
        type=Path,
        default=Path.cwd(),
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print actions without executing them",
    )

    subparsers = parser.add_subparsers(required=True)
    init_parser = subparsers.add_parser(
        "init",
        aliases=["i"],
        formatter_class=fmt_class,
        help="Create .devct/ with a basic compose.yml",
    )
    init_parser.set_defaults(func=cmd_init)

    build_parser = subparsers.add_parser(
        "build",
        aliases=["b"],
        formatter_class=fmt_class,
        help="Build service containers",
    )
    build_parser.set_defaults(func=cmd_build)
    build_parser.add_argument(
        "--podman-build-args",
        metavar="ARG",
        nargs=1,
        action="append",
        default=[],
        help="Extra argument forwarded to podman-compose build (repeatable)",
    )
    build_parser.add_argument(
        "services",
        nargs="*",
        help="Services to build, if not provided, all services are built",
    )

    run_parser = subparsers.add_parser(
        "run",
        aliases=["r"],
        formatter_class=fmt_class,
        help="Run a one-off command in a service container",
    )
    run_parser.set_defaults(func=cmd_run)
    run_parser.add_argument(
        "--rm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pass --rm to podman-compose run",
    )
    run_parser.add_argument(
        "--podman-run-args",
        metavar="ARG",
        nargs=1,
        action="append",
        default=[],
        help="Extra argument forwarded to podman-compose run (repeatable)",
    )
    run_parser.add_argument("service", help="Service to run")
    run_parser.add_argument(
        "args",
        nargs="*",
        help="Command to run inside the container",
    )

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
