#!/bin/bash
# Builds LinCity-NG for aarch64 from the 2.14.2 release (the last SDL2 one), with fmt and
# libxml++ linked statically, fills lincity-ng/lincity-ng/ with the binary and game data, and
# zips the port into dist/. dist/source/ gets the tarballs the binary was built from.
# On an x86 host, Docker needs arm64 emulation (docker run --privileged --rm tonistiigi/binfmt --install arm64).
set -euo pipefail

here="$(cd -- "$(dirname "$0")" && pwd)"
work="$here/build"
image=lincity-ng-build:bookworm

fetch() {
    local name=$1 url=$2 sha256=$3
    if [ ! -f "$work/$name" ]; then
        curl -sSfL -o "$work/$name.tmp" "$url"
        mv "$work/$name.tmp" "$work/$name"
    fi
    echo "$sha256  $work/$name" | sha256sum -c --quiet
}

mkdir -p "$work"
fetch lincity-ng-2.14.2-Source.tar.xz \
    https://github.com/lincity-ng/lincity-ng/releases/download/lincity-ng-2.14.2/lincity-ng-2.14.2-Source.tar.xz \
    772c0d127d396b307e1d612c41c569196c536b1ed87d242a5403aa3de8de687d
fetch fmt-11.0.2.tar.gz \
    https://github.com/fmtlib/fmt/archive/refs/tags/11.0.2.tar.gz \
    6cb1e6d37bdcb756dbbe59be438790db409cdb4868c66e888d5df9f13f7c027f
fetch libxml++-5.0.4.tar.xz \
    https://download.gnome.org/sources/libxml++/5.0/libxml++-5.0.4.tar.xz \
    42891b7863d2ccf4d7bf029f06fe3a52a4376c94bbba91f8945e48520ffae82f

docker build -q --platform linux/arm64 -t "$image" "$here" >/dev/null
docker run --rm --platform linux/arm64 --user "$(id -u):$(id -g)" \
    -v "$work:/work" -w /work "$image" bash -c '
        set -e
        jobs=$(nproc)
        # The static dependencies are built once; delete build/deps to rebuild them.
        if [ ! -f deps/lib/libxml++-5.0.a ]; then
            rm -rf deps fmt-11.0.2 libxml++-5.0.4
            tar -xzf fmt-11.0.2.tar.gz
            cmake -S fmt-11.0.2 -B fmt-11.0.2/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
                -DCMAKE_INSTALL_PREFIX=/work/deps -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
                -DFMT_TEST=OFF -DFMT_DOC=OFF > fmt.log
            cmake --build fmt-11.0.2/build -j"$jobs" >> fmt.log
            cmake --install fmt-11.0.2/build >> fmt.log
            tar -xJf libxml++-5.0.4.tar.xz
            meson setup libxml++-5.0.4/build libxml++-5.0.4 --prefix=/work/deps --libdir=lib \
                --buildtype=release -Ddefault_library=static -Dbuild-documentation=false \
                -Dbuild-examples=false -Dbuild-tests=false > libxml++.log
            meson install -C libxml++-5.0.4/build >> libxml++.log
        fi
        rm -rf lincity-ng-2.14.2-Source install
        tar -xJf lincity-ng-2.14.2-Source.tar.xz
        # Ninja rejects the gettext rules: two of them generate messages.pot.
        PKG_CONFIG_PATH=/work/deps/lib/pkgconfig cmake -S lincity-ng-2.14.2-Source \
            -B lincity-ng-2.14.2-Source/build -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_PREFIX_PATH=/work/deps -DCMAKE_INSTALL_PREFIX=/work/install > lincity-ng.log
        cmake --build lincity-ng-2.14.2-Source/build -j"$jobs" >> lincity-ng.log 2>&1 \
            || { tail -40 lincity-ng.log; exit 1; }
        cmake --install lincity-ng-2.14.2-Source/build --strip >> lincity-ng.log'

port="$here/lincity-ng"
game="$port/lincity-ng"
rm -rf "$game/data"
cp "$work/install/bin/lincity-ng" "$game/lincity-ng.aarch64"
cp -r "$work/install/share/lincity-ng" "$game/data"

# A PortMaster release zip carries the metadata inside the game folder.
stage="$work/zip"
rm -rf "$stage" "$here/dist"
mkdir -p "$stage" "$here/dist/source"
cp "$port/LinCityNG.sh" "$stage/"
cp -r "$game" "$stage/lincity-ng"
rm -rf "$stage/lincity-ng/conf" "$stage/lincity-ng/log.txt"
cp "$port/port.json" "$port/gameinfo.xml" "$port/README.md" "$port/screenshot.jpg" "$port/cover.jpg" \
    "$stage/lincity-ng/"
python3 "$here/../../tools/zip_port.py" "$here/dist/lincity-ng.zip" "$stage"

# The corresponding source: LinCity-NG is GPL, and libxml++ (LGPL) is linked statically.
cp "$work/lincity-ng-2.14.2-Source.tar.xz" "$work/fmt-11.0.2.tar.gz" "$work/libxml++-5.0.4.tar.xz" \
    "$here/dist/source/"
echo "Built $game/lincity-ng.aarch64 and $here/dist/lincity-ng.zip"
