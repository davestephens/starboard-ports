# Starboard Ports

Linux game ports for Starboard, the Android app that runs PortMaster ports, published as a
PortMaster-style catalogue. Starboard adds it like any other port source, and the ports then
install, update and show in the library like PortMaster's own.

| Port | Game | Runs on |
|---|---|---|
| [`lincity`](ports/lincity) | LinCity 1.12.1, the original X11 city simulation | Westonpack runtime (downloaded from PortMaster) |
| [`lincity-ng`](ports/lincity-ng) | LinCity-NG 2.14.2 | Native SDL2, no runtime |

## Add the catalogue to Starboard

In Starboard, go to Settings > Port sources, choose Add source, and paste:

```
https://github.com/davestephens/starboard-ports/releases/download/ports-latest/starboard.source.json
```

Ports install into `Starboard/ports.starboard/` and any runtimes into `Starboard/libs.starboard/`.

The catalogue follows PortMaster's `PortMasterV3` format, so harbourmaster can read it too, but
the ports are built and tested for Starboard only. LinCity-NG needs glibc 2.35, which older
handheld firmwares lack.

## Layout

```
catalogue.json              the source's prefix, name and GitHub repo
ports/<port>/
  build.sh                  builds the game in Docker and writes dist/<port>.zip and dist/source/
  Dockerfile                the arm64 build image
  starboard-test.sh         copies the built port to a device and launches it
  README.md                 how the port was made
  <port>/                   the port folder, laid out as in PortMaster-New
tools/
  zip_port.py               writes a port zip that is byte-identical for an unchanged build
  catalogue.py              writes ports.json, images.zip and starboard.source.json
  publish.sh                builds, writes the catalogue and uploads what changed to a release
  test_catalogue.py         tests for the two Python tools
```

## Build a port

```bash
ports/lincity-ng/build.sh
```

Each build runs in an arm64 Debian container. On an x86 machine, Docker needs arm64 emulation
first:

```bash
docker run --privileged --rm tonistiigi/binfmt --install arm64
```

A build writes:

- `dist/<port>.zip`, laid out like a PortMaster release zip: the launcher `.sh` and `<port>/`
  at the top, with `port.json`, `gameinfo.xml`, `README.md`, `screenshot.jpg` and `cover.jpg`
  inside `<port>/`
- `dist/source/`, holding the source tarballs and patches the binary was built from

To try a build on a device running Starboard, use `ports/<port>/starboard-test.sh [adb-serial]`.
It copies the port into `Starboard/ports.local/` and launches it, so it needs a Starboard build
that knows the sideloaded `local` source.

## The catalogue

`tools/catalogue.py` reads every `ports/*/dist/*.zip` and writes:

- `ports.json`, where each entry is the port's own `port.json` plus a `source` block with the
  zip's URL, md5, size, `date_added` and `date_updated`
- `images.zip`, holding `<port>.screenshot.jpg` and `<port>.cover.jpg` from each zip
- `starboard.source.json`, the descriptor Starboard is given, pointing at `ports.json`

It rejects a zip without a launcher at the top, without `<port>/port.json`, whose `port.json`
name or `items` do not match the zip, or without a screenshot and cover.

`date_added` is kept from the published `ports.json`. `date_updated` changes only when a
zip's md5 does. Zips are written with fixed timestamps, so rebuilding unchanged code does not
offer players an update.

The runtimes a port needs are not in this catalogue. Starboard fetches any runtime an added
source does not list from PortMaster's own catalogue.

## Publishing

CI publishes on every push to `main`: the `Build` workflow builds each port natively on a
GitHub arm64 runner, writes the catalogue and uploads what changed to the `ports-latest`
release. Pull requests build and check the catalogue without publishing.

A build is byte-identical from one CI run to the next, but a local build is not identical to
CI's: the same zip built on another machine has a different md5, and publishing it offers
players an update. Leave `ports-latest` to CI.

To publish by hand, for example to a test release, with the `gh` CLI logged in and the commit
pushed:

```bash
tools/publish.sh                     # build everything and publish to ports-latest
tools/publish.sh --tag ports-test    # publish to another release, for testing
tools/publish.sh --skip-build --dry-run
```

Only changed files are uploaded: port zips and their source first, then `images.zip`, then
`ports.json`. The release tag is moved to the published commit, so GitHub's source archive on
the release matches the build scripts that made it.

## Adding a port

1. Create `ports/<port>/` with a `build.sh` that writes `dist/<port>.zip` (use
   `tools/zip_port.py`) and copies the corresponding source into `dist/source/`.
2. Put the port folder at `ports/<port>/<port>/`: the launcher, `port.json` (its `name` is
   `<port>.zip` and its `items` list the zip's top level), `gameinfo.xml`, `README.md`,
   `screenshot.jpg`, `cover.jpg` and the game folder with its `licenses/`.
3. Run `tools/publish.sh --dry-run` and open a pull request.

CI finds new ports by listing `ports/`.

## Licences

The scripts and tools in this repository are MIT licensed (see [LICENSE](LICENSE)). Each game
keeps its own licence. The texts are in `ports/<port>/<port>/<port>/licenses/`, and every
release carries the source each binary was built from.
