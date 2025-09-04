import shutil
import subprocess
from pathlib import Path


def init(project_devct_path: Path, template_path: Path) -> None:
    shutil.copytree(template_path, project_devct_path)


def run(project_devct_path: Path, service: str, compose_backend: Path, *args) -> None:
    subprocess.check_call(
        [
            str(compose_backend),
            "-f",
            project_devct_path / "compose.yaml",
            "run",
            *args,
            service,
        ]
    )
