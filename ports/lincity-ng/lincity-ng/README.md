## Notes

Thanks to the [LinCity-NG](https://github.com/lincity-ng/lincity-ng) developers for the game, and to I J Peters and Greg Sharp for the original LinCity.

This is LinCity-NG 2.14.2, the last release built on SDL2. It is a native SDL2 game and needs no runtime. Saved games and settings are kept in `conf/`. The game menu is the red button at the bottom left.

## Controls

| Button | Action |
|--|--|
| Left Stick | Move mouse |
| A | Left click |
| B | Right click |
| X | Slow mouse (hold) |
| Y / Select | Escape (back to the query tool) |
| Start | Enter |
| D-Pad / Right Stick | Scroll the map |
| L1 | Help |
| R1 | Bulldoze tool |
| L2 | Quick load |
| R2 | Quick save |

## Compile

LinCity-NG 2.14 needs CMake 3.21, fmt 11 and libxml++ 5.0. On Debian bookworm, fmt and libxml++ are built from source and linked statically:

```bash
wget https://github.com/fmtlib/fmt/archive/refs/tags/11.0.2.tar.gz -O fmt-11.0.2.tar.gz
wget https://download.gnome.org/sources/libxml++/5.0/libxml++-5.0.4.tar.xz
wget https://github.com/lincity-ng/lincity-ng/releases/download/lincity-ng-2.14.2/lincity-ng-2.14.2-Source.tar.xz

tar xzf fmt-11.0.2.tar.gz
cmake -S fmt-11.0.2 -B fmt-11.0.2/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$PWD/deps \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DFMT_TEST=OFF -DFMT_DOC=OFF
cmake --build fmt-11.0.2/build && cmake --install fmt-11.0.2/build

tar xJf libxml++-5.0.4.tar.xz
meson setup libxml++-5.0.4/build libxml++-5.0.4 --prefix=$PWD/deps --libdir=lib --buildtype=release \
    -Ddefault_library=static -Dbuild-documentation=false -Dbuild-examples=false -Dbuild-tests=false
meson install -C libxml++-5.0.4/build

tar xJf lincity-ng-2.14.2-Source.tar.xz
PKG_CONFIG_PATH=$PWD/deps/lib/pkgconfig cmake -S lincity-ng-2.14.2-Source -B lincity-ng-2.14.2-Source/build \
    -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$PWD/deps -DCMAKE_INSTALL_PREFIX=$PWD/install
cmake --build lincity-ng-2.14.2-Source/build
cmake --install lincity-ng-2.14.2-Source/build --strip
cp install/bin/lincity-ng lincity-ng.aarch64
cp -r install/share/lincity-ng data
```

The Makefile generator is used because Ninja rejects two rules that both write `messages.pot`.
