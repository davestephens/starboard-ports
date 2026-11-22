#!/bin/bash
# Builds xlincity for aarch64 from the upstream 1.12.1 tarball plus the port's patch,
# fills lincity/lincity/ with the binary and game data, and zips the port into dist/.
# dist/source/ gets the tarball and patch the binary was built from.
# On an x86 host, Docker needs arm64 emulation (docker run --privileged --rm tonistiigi/binfmt --install arm64).
set -euo pipefail

here="$(cd -- "$(dirname "$0")" && pwd)"
port="$here/lincity"
game="$port/lincity"
work="$here/build"
image=lincity-build:bullseye

tarball=lincity_1.12.1.orig.tar.gz
# Debian's copy of the upstream release; SourceForge serves scripts an HTML page.
url=https://snapshot.debian.org/file/280375273f6e741d707dc8e11fdedb160d230c95
sha256=9223a724204e0755ed65d6ae202a5b1a876204cc835ab3e87230dc39f7b9b976

mkdir -p "$work"
if [ ! -f "$work/$tarball" ]; then
    curl -sSfL -o "$work/$tarball.tmp" "$url"
    mv "$work/$tarball.tmp" "$work/$tarball"
fi
echo "$sha256  $work/$tarball" | sha256sum -c --quiet

rm -rf "$work/lincity-1.12.1"
tar -xzf "$work/$tarball" -C "$work"

docker build -q --platform linux/arm64 -t "$image" "$here" >/dev/null
# config.guess from 2002 does not know aarch64, so the build triplet is given.
docker run --rm --platform linux/arm64 --user "$(id -u):$(id -g)" \
    -v "$work/lincity-1.12.1:/src" -v "$game/patches:/patches:ro" -w /src "$image" bash -c '
        set -e
        patch -p1 --quiet < /patches/lincity-1.12.1-portmaster.patch
        LDFLAGS=-Wl,--as-needed ./configure --build=aarch64-unknown-linux-gnu --with-x > configure.log
        make -j"$(nproc)" xlincity > make.log 2>&1 || { tail -30 make.log; exit 1; }
        strip -o xlincity.aarch64 xlincity'

src="$work/lincity-1.12.1"
rm -rf "$game/data"
mkdir -p "$game/data"
cp -r "$src/colour.pal" "$src/help" "$src/icons" "$src/messages" "$src/opening" "$game/data/"
cp "$src/xlincity.aarch64" "$game/"

# A PortMaster release zip carries the metadata inside the game folder.
stage="$work/zip"
rm -rf "$stage" "$here/dist"
mkdir -p "$stage" "$here/dist/source"
cp "$port/LinCity.sh" "$stage/"
cp -r "$game" "$stage/lincity"
rm -rf "$stage/lincity/conf" "$stage/lincity/log.txt"
cp "$port/port.json" "$port/gameinfo.xml" "$port/README.md" "$port/screenshot.jpg" "$port/cover.jpg" \
    "$stage/lincity/"
python3 "$here/../../tools/zip_port.py" "$here/dist/lincity.zip" "$stage"

# The corresponding source for the GPL binary, attached to the catalogue release.
cp "$work/$tarball" "$game/patches/lincity-1.12.1-portmaster.patch" "$here/dist/source/"
echo "Built $game/xlincity.aarch64 and $here/dist/lincity.zip"
