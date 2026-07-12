# devct

A thin wrapper around `podman-compose` for managing per-project development container environments defined in a `.devct/` directory.

## Why

Installing a project's toolchain directly on your machine pollutes it and drifts between projects. It also means every development tool - package managers pulling third-party dependencies, editors and their plugins, coding agents - runs with full access to your host: your home directory, your credentials, your SSH keys. Running them inside a container instead confines them to the project directory and whatever you explicitly mount in. Full-blown solutions like devcontainers solve this but drag in an IDE integration, a JSON spec, and a lifecycle of their own.

`devct` takes the middle path: your dev environment is just a compose file. Each project carries a `.devct/` directory containing a `compose.yml` (plus any supporting files such as a `Containerfile`) that describes one or more service containers with the project mounted inside. `devct` then removes the ceremony of using it:

- No `-f .devct/compose.yml` on every invocation; the compose file is discovered from the project directory.
- Reusable environment templates can be stamped out into new projects with `devct init -t NAME`.
- It stays a thin shell over `podman-compose`: every command maps to a single compose invocation, which `--dry-run` will print instead of running. Anything compose can do, your environment can do.

## Requirements

- Python 3.10+
- `podman-compose` on `PATH`, or set `DEVCT_COMPOSE` to another compose-compatible binary

## Install

```sh
# uv tool (isolated, adds devct to PATH)
uv tool install .

# or editable, for development
uv tool install -e .
```

### Shell completion

Completion (including service names read from the project's compose file) is provided through `argcomplete`. Register it in your shell:

```sh
eval "$(register-python-argcomplete devct)"
```

## Usage

```
devct [-p PROJECT] [-n] <command> [options]
```

Global flags apply to every command and go before the command name:

| Flag | Default | Description |
|------|---------|-------------|
| `-p`, `--project` | current directory | Project directory containing `.devct/` |
| `-n`, `--dry-run` | off | Print the underlying commands without executing them |

`devct` looks for `.devct/compose.yml` (or `compose.yaml`) under the project directory and fails with an error if neither exists.

### `init` (alias: `i`)

Create the `.devct/` directory.

```sh
devct init [-t NAME] [-f]
```

| Flag | Description |
|------|-------------|
| `-t`, `--template NAME` | Copy the template directory `$XDG_CONFIG_HOME/devct/NAME` (default `~/.config/devct/NAME`) instead of generating a default file |
| `-f`, `--force` | Remove and recreate an existing `.devct/` |

Without a template, `init` writes a minimal `compose.yml` with a single Alpine-based `dev` service that mounts the project at `/workdir`:

```yaml
services:
  dev:
    image: docker.io/library/alpine:latest
    volumes:
      - .:/workdir
    working_dir: /workdir
```

A template is simply a directory whose entire contents are copied into `.devct/`, so it can ship a `Containerfile`, config files, and anything else alongside the compose file.

### `build` (alias: `b`)

Build service container images, equivalent to `podman-compose build`.

```sh
devct build [SERVICE...] [--podman-build-args ARG]...
```

With no services given, all services are built. `--podman-build-args` is repeatable and each value is forwarded verbatim to the compose build command.

### `run` (alias: `r`)

Run a one-off command in a service container, equivalent to `podman-compose run`.

```sh
devct run [--rm | --no-rm] [--podman-run-args ARG]... SERVICE [ARGS...]
```

- `--rm` is on by default, so containers are removed after the command exits; pass `--no-rm` to keep them.
- Everything after `SERVICE` is passed verbatim to the container, including flags, so `devct run dev make -j4` works without escaping.
- With no `ARGS`, the service's default `command` runs.
- `--podman-run-args` is repeatable and forwarded verbatim to the compose run command.

```sh
devct run dev sh              # interactive shell in the dev service
devct run dev pytest tests/   # run the test suite in a throwaway container
```

### `list` (aliases: `l`, `ls`)

List the project's running service containers, equivalent to `podman-compose ps`.

```sh
devct list
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVCT_COMPOSE` | `podman-compose` | Compose binary to invoke |
| `XDG_CONFIG_HOME` | `~/.config` | Base directory for `devct/` templates |

## Example: a Nix-based environment

[`examples/nix/`](examples/nix/) shows a more complete setup usable as a template. It defines a `dev` service built on the `nixos/nix` image that enters a `nix-shell` from a checked-in `dev-shell.nix`, with the Nix store on a shared volume so builds are cached across containers, plus `editor` and `claude` services that extend `dev` with an editor and agent configuration mounted in. Copy it to `~/.config/devct/nix` and any project gets the same environment with:

```sh
devct init -t nix
devct run dev
```
