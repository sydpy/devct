import argparse
import os
from pathlib import Path
from . import init, run

XDG_CONFIG_HOME = Path(os.getenv("XDG_CONFIG_HOME", "~/.config"))
COMPOSE_BACKEND = Path(os.getenv("DEVCT_COMPOSE", "/usr/bin/podman-compose"))


def build_parser() -> argparse.ArgumentParser:
    fmt_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=fmt_class)
    subparser = parser.add_subparsers(dest="command", required=True)

    init_parser = subparser.add_parser("init", aliases=["i"], formatter_class=fmt_class)
    init_parser.add_argument(
        "--template-dir",
        "-d",
        help="Template directory",
        type=Path,
        default=XDG_CONFIG_HOME / "devct/",
    )
    init_parser.add_argument(
        "--project",
        "-p",
        help="Project directory",
        type=Path,
        default=Path.cwd(),
    )
    init_parser.add_argument(
        "template_name",
        help="Template name",
    )

    run_parser = subparser.add_parser("run", aliases=["r"], formatter_class=fmt_class)
    run_parser.add_argument(
        "--project",
        "-p",
        help="Project directory",
        type=Path,
        default=Path.cwd(),
    )
    run_parser.add_argument(
        "service",
        help="Service to run",
    )
    run_parser.add_argument(
        "args",
        nargs="*",
        help="Additional compose args",
    )

    return parser


def main() -> None:
    parser = build_parser()

    args = parser.parse_args()

    match args.command:
        case "init":
            project_devct_path = args.project / ".devct"
            template_path = args.template_dir / args.template_name
            init(project_devct_path, template_path)
        case "run":
            project_devct_path = args.project / ".devct"
            run(project_devct_path, args.service, COMPOSE_BACKEND, *args.args)
        case _:
            raise Exception("asdf")


if __name__ == "__main__":
    main()
