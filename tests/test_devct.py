import argparse
import logging

import pytest

from devct import BASIC_COMPOSE, _service_completer, build_parser


def run_cli(*argv):
    args = build_parser().parse_args([str(a) for a in argv])
    args.func(args)


@pytest.fixture
def project(tmp_path):
    devct_dir = tmp_path / ".devct"
    devct_dir.mkdir()
    (devct_dir / "compose.yml").write_text("services:\n  dev: {}\n  db: {}\n")
    return tmp_path


@pytest.fixture
def dry_run(project, caplog):
    def _dry_run(*argv):
        with caplog.at_level(logging.INFO, logger="devct"):
            run_cli("-n", "-p", project, *argv)
        return caplog.messages[-1]

    return _dry_run


class TestInit:
    def test_creates_devct_dir_with_basic_compose(self, tmp_path):
        run_cli("-p", tmp_path, "init")

        assert (tmp_path / ".devct" / "compose.yml").read_text() == BASIC_COMPOSE

    def test_refuses_to_overwrite_existing_devct_dir(self, tmp_path):
        (tmp_path / ".devct").mkdir()

        with pytest.raises(FileExistsError):
            run_cli("-p", tmp_path, "init")

    def test_force_replaces_existing_devct_dir(self, tmp_path):
        devct_dir = tmp_path / ".devct"
        devct_dir.mkdir()
        (devct_dir / "old.txt").write_text("old")

        run_cli("-p", tmp_path, "init", "--force")

        assert not (devct_dir / "old.txt").exists()
        assert (devct_dir / "compose.yml").read_text() == BASIC_COMPOSE

    def test_copies_named_template(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
        template_dir = tmp_path / "config" / "devct" / "mytpl"
        template_dir.mkdir(parents=True)
        (template_dir / "compose.yml").write_text("services: {}\n")
        project = tmp_path / "project"
        project.mkdir()

        run_cli("-p", project, "init", "--template", "mytpl")

        assert (project / ".devct" / "compose.yml").read_text() == "services: {}\n"

    def test_unknown_template_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

        with pytest.raises(FileNotFoundError):
            run_cli("-p", tmp_path, "init", "--template", "nope")

    def test_dry_run_creates_nothing(self, tmp_path):
        run_cli("-n", "-p", tmp_path, "init")

        assert not (tmp_path / ".devct").exists()


class TestBuild:
    def test_builds_all_services_by_default(self, project, dry_run):
        assert dry_run("build") == f"podman-compose -f {project}/.devct/compose.yml build"

    def test_forwards_services_and_extra_args(self, project, dry_run):
        # values starting with "-" must use the = form or argparse rejects them
        cmdline = dry_run("build", "--podman-build-args=--no-cache", "dev", "db")

        assert cmdline == f"podman-compose -f {project}/.devct/compose.yml build --no-cache dev db"

    def test_raises_when_no_compose_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            run_cli("-n", "-p", tmp_path, "build")

    def test_falls_back_to_compose_yaml(self, project, dry_run):
        (project / ".devct" / "compose.yml").rename(project / ".devct" / "compose.yaml")

        assert dry_run("build") == f"podman-compose -f {project}/.devct/compose.yaml build"


class TestRun:
    def test_passes_rm_by_default(self, project, dry_run):
        cmdline = dry_run("run", "dev", "echo", "hi")

        assert cmdline == f"podman-compose -f {project}/.devct/compose.yml run --rm dev echo hi"

    def test_no_rm_omits_rm_flag(self, project, dry_run):
        cmdline = dry_run("run", "--no-rm", "dev")

        assert cmdline == f"podman-compose -f {project}/.devct/compose.yml run dev"

    def test_forwards_extra_run_args(self, project, dry_run):
        cmdline = dry_run("run", "--podman-run-args", "-e FOO=bar", "dev")

        assert cmdline == f'podman-compose -f {project}/.devct/compose.yml run --rm "-e FOO=bar" dev'


class TestList:
    def test_runs_compose_ps(self, project, dry_run):
        assert dry_run("list") == f"podman-compose -f {project}/.devct/compose.yml ps"


class TestServiceCompleter:
    def test_lists_services_from_compose_file(self, project):
        assert _service_completer(argparse.Namespace(project=project)) == ["dev", "db"]

    def test_returns_empty_when_no_compose_file(self, tmp_path):
        assert _service_completer(argparse.Namespace(project=tmp_path)) == []

    def test_returns_empty_on_invalid_yaml(self, project):
        (project / ".devct" / "compose.yml").write_text("services: [unclosed")

        assert _service_completer(argparse.Namespace(project=project)) == []
