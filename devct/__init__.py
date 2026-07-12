#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

try:
    import yaml
    from argcomplete import autocomplete

    HAS_ARGCOMPLETE = True
except ModuleNotFoundError:
    HAS_ARGCOMPLETE = False

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


def _templates_dir() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(config_home) / "devct"


def cmd_init(args: argparse.Namespace) -> None:
    devct_dir = args.project / DEVCT_DIR
    if devct_dir.exists():
        if not args.force:
            raise FileExistsError(f'"{devct_dir}" already exists, use --force to overwrite')
        if args.dry_run:
            logger.info("rm -r %s", devct_dir)
        else:
            shutil.rmtree(devct_dir)
    if args.template:
        template_dir = _templates_dir() / args.template
        if not template_dir.is_dir():
            raise FileNotFoundError(f'No template named "{args.template}" under "{_templates_dir()}"')
        if args.dry_run:
            logger.info("%s -> %s", template_dir, devct_dir)
        else:
            shutil.copytree(template_dir, devct_dir, dirs_exist_ok=True)
            logger.info("Created %s from template %s", devct_dir, args.template)
    else:
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


def cmd_list(args: argparse.Namespace) -> None:
    compose_file = _find_compose_file(args.project)
    cmd = [COMPOSE, "-f", str(compose_file), "ps"]
    if args.dry_run:
        logger.info(subprocess.list2cmdline(cmd))
    else:
        subprocess.check_call(cmd, cwd=args.project)


def cmd_exec(args: argparse.Namespace) -> None:
    # podman-compose exec only accepts service names, so target the container directly
    cmd = ["podman", "exec", "--interactive", "--tty", args.container, *args.args]
    if args.dry_run:
        logger.info(subprocess.list2cmdline(cmd))
    else:
        subprocess.check_call(cmd)


def _service_completer(parsed_args: argparse.Namespace, **kwargs: object) -> list[str]:
    try:
        data = yaml.safe_load(_find_compose_file(parsed_args.project).read_text())
    except (FileNotFoundError, yaml.YAMLError):
        return []
    return list((data or {}).get("services", {}))


def _container_completer(parsed_args: argparse.Namespace, **kwargs: object) -> list[str]:
    try:
        compose_file = _find_compose_file(parsed_args.project)
        proc = subprocess.run(
            [COMPOSE, "-f", str(compose_file), "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=parsed_args.project,
        )
        containers = json.loads(proc.stdout)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return [name for c in containers if c.get("State") == "running" for name in c.get("Names", [])]


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
    init_parser.add_argument(
        "--template",
        "-t",
        metavar="NAME",
        help=f"Template directory under {_templates_dir()} to copy",
    )
    init_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite an existing .devct/ directory",
    )

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
    action = build_parser.add_argument(
        "services",
        nargs="*",
        help="Services to build, if not provided, all services are built",
    )
    if HAS_ARGCOMPLETE:
        action.completer = _service_completer

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
    action = run_parser.add_argument("service", help="Service to run")
    if HAS_ARGCOMPLETE:
        action.completer = _service_completer
    run_parser.add_argument(
        "args",
        nargs="*",
        help="Command to run inside the container",
    )
    list_parser = subparsers.add_parser(
        "list",
        aliases=["l", "ls"],
        formatter_class=fmt_class,
        help="List running service containers",
    )
    list_parser.set_defaults(func=cmd_list)

    exec_parser = subparsers.add_parser(
        "exec",
        aliases=["e"],
        formatter_class=fmt_class,
        help="Run a command in a running container",
    )
    exec_parser.set_defaults(func=cmd_exec)
    action = exec_parser.add_argument("container", help="Running container to exec into")
    if HAS_ARGCOMPLETE:
        action.completer = _container_completer
    exec_parser.add_argument(
        "args",
        nargs="*",
        help="Command to run inside the container",
    )

    if HAS_ARGCOMPLETE:
        autocomplete(parser)

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
