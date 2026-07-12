# devct

A thin wrapper around `podman-compose` for managing per-project dev container environments stored in `.devct/`.

## Requirements

- Python 3.10+
- `podman-compose` (or set `DEVCT_COMPOSE` to a different compose binary)

## Install

```sh
# uv (editable)
uv tool install -e .

# uv tool (isolated, adds devct to PATH)
uv tool install .
```

### Shell completion

Register the completer in your shell:

```sh
eval "$(register-python-argcomplete devct)"
```

## Usage

```
devct [-p PROJECT] [-n] <command>
```

**Global flags**

| Flag | Default | Description |
|------|---------|-------------|
| `-p`, `--project` | cwd | Project directory |
| `-n`, `--dry-run` | false | Print commands without running them |

### Commands

#### `init` (alias: `i`)

Create `.devct/compose.yml` with a minimal Alpine-based service.

```sh
devct init
```

#### `build` (alias: `b`)

Build service containers defined in `.devct/compose.yml`.

```sh
devct build [SERVICE...] [--podman-build-args ARG]...
```

#### `run` (alias: `r`)

Run a one-off command in a service container.

```sh
devct run [--rm | --no-rm] [--podman-run-args ARG]... SERVICE [ARGS...]
```

`--rm` is on by default. Everything after `SERVICE` is passed verbatim to the container, including flags.

#### `list` (aliases: `l`, `ls`)

List service containers.

```sh
devct list
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVCT_COMPOSE` | `podman-compose` | Compose binary to use |
