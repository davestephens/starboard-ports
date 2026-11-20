# LinCity port

A PortMaster port of LinCity 1.12.1, the X11 city simulation. `lincity/` is laid out as
`ports/lincity/` in [PortMaster-New](https://github.com/PortsMaster/PortMaster-New) and is the
folder a PR would add.

```
lincity/                    the port
  LinCity.sh                launcher (Westonpack, drm/system mode: the game draws with Xlib)
  port.json, gameinfo.xml, README.md, screenshot.jpg, cover.jpg
  lincity/
    lincity.ini             gptokeyb2 controls
    licenses/               one LICENSE.<component>.txt per component
    patches/                applied to the upstream tarball by build.sh
    xlincity.aarch64, data/ built by build.sh (not tracked)
build.sh                    builds the binary and data, writes dist/lincity.zip
Dockerfile                  arm64 bullseye build image (glibc 2.31)
starboard-test.sh           copies the port to a device running Starboard and launches it
```

## Build

```bash
./build.sh
```

It downloads the upstream tarball from Debian's archive (SourceForge serves scripts an HTML
page), checks its SHA-256, applies the patch and builds in Docker under arm64 emulation.
`dist/lincity.zip` is laid out like a PortMaster release zip: `port.json`, `gameinfo.xml` and
the images sit inside `lincity/`.

The patch is the upstream source plus:

- the modern-GCC fixes from [davestephens/lincity](https://github.com/davestephens/lincity)
- an `XC_left_ptr` cursor on the game window, which otherwise inherits the root window's
- a deferred resize. lincity locks its window size during the opening screen, but Weston's
  kiosk shell and matchbox make it full screen anyway. The ConfigureNotify arrives while the
  opening screen waits for MapNotify, and `resize_geometry` then draws the month graph before
  it is allocated (segfault in `do_history_linegraph`). The patch stores that size and applies
  it after `screen_setup`.

## Test on Starboard

```bash
./starboard-test.sh [adb-serial]
```

The port is not in a catalogue, so it does not show in Starboard's games list. The script
launches it with an intent. The opening screen waits for a key: press Start.

## Display size

LinCity 1.12 reflows its UI to any window from 640x480 up, so the full-screen window Weston
(or Starboard's Xvfb, 1280x720) gives it shows more map, not bigger pixels. The `-d` pixel
doubling flag needs 960 lines and does not fit a 720-line screen. The opening screen is a
fixed 640x480 image and sits in the top-left corner of a larger screen.

On Starboard the pointer does not show. Starboard's `westonwrap.sh` starts matchbox with
`-use_cursor no`, which hides the X cursor even over a window that sets its own.
