# LinCity-NG port

A PortMaster port of LinCity-NG 2.14.2, the last release built on SDL2. It is a native SDL2
game and needs no runtime. `lincity-ng/` is laid out as `ports/lincity-ng/` in
[PortMaster-New](https://github.com/PortsMaster/PortMaster-New).

```
lincity-ng/                 the port
  LinCityNG.sh              launcher
  port.json, gameinfo.xml, README.md, screenshot.jpg, cover.jpg
  lincity-ng/
    lincity-ng.ini          gptokeyb2 controls
    licenses/               one LICENSE.<component>.txt per component
    lincity-ng.aarch64, data/  built by build.sh (not tracked)
build.sh                    builds the game, writes dist/lincity-ng.zip and dist/source/
Dockerfile                  arm64 bookworm build image (glibc 2.36; the binary needs 2.35)
starboard-test.sh           copies the built port to a device running Starboard and launches it
```

## Build

```bash
./build.sh
```

It downloads three tarballs and checks their SHA-256s:

- LinCity-NG 2.14.2, which needs CMake 3.21, so bullseye is too old
- fmt 11.0.2. LinCity-NG includes `fmt/base.h`, which bookworm's fmt 9 lacks.
- libxml++ 5.0.4, which bookworm does not package

fmt and libxml++ are built once as static libraries into `build/deps`. Delete that folder to
rebuild them. The game is built with the Makefile generator, because Ninja rejects two rules
that both write `messages.pot`.

The binary links SDL2, SDL2_image, SDL2_mixer, SDL2_ttf, libxml2 and zlib from the system.
Starboard's rootfs has them all.

`dist/source/` gets the three tarballs. LinCity-NG is GPL and libxml++
(LGPL-2.1) is linked statically, so the catalogue release carries them with the build scripts
in this repository.

## Controls

The `.ini` maps the pad to the mouse and the game's keys. Escape returns to the query tool, F1
opens help, B picks the bulldozer, and F12 and F9 quick save and load. The game menu is the red
button at the bottom left of the screen.

## Test on Starboard

```bash
./starboard-test.sh [adb-serial]
```

The script copies the port into `Starboard/ports.local/lincity-ng` and launches it, so it needs
a Starboard build that knows the sideloaded `local` source.

The screenshot and cover were captured at 1024x768 under Xvfb and scaled to 640x480. The New
Game screen's "Village" and "Without trees" labels overlap in upstream 2.14.2 too.
