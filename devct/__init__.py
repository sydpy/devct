import argparse
import os
import subprocess
from pathlib import Path

COMPOSE = os.getenv("DEVCT_COMPOSE", "podman-compose")
DEVCT_DIR = ".devct"
COMPOSE_FILE_NAMES = ["compose.yml", "compose.yaml"]


def _find_compose_file(project_path: Path) -> Path:
    project_devct_dir = project_path / DEVCT_DIR
    for compose_file_name in COMPOSE_FILE_NAMES:
        if (compose_file := project_devct_dir / compose_file_name).exists():
            return compose_file
    raise FileNotFoundError(f'No compose file found under "{project_devct_dir}"')


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
        "args",
        nargs="*",
        help="Additional compose args",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    compose_file = _find_compose_file(args.project)
    subprocess.check_call(
        [COMPOSE, "-f", str(compose_file), *args.args],
        cwd=args.project,
    )


if __name__ == "__main__":
    main()
