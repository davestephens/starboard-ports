#!/bin/bash
# Copies the built port to a device running Starboard and launches it.
set -euo pipefail

here="$(cd -- "$(dirname "$0")" && pwd)"
adb=(adb)
[ $# -ge 1 ] && adb=(adb -s "$1")
dest=/storage/emulated/0/Starboard/ports/lincity

[ -f "$here/lincity/lincity/xlincity.aarch64" ] || { echo "Run ./build.sh first" >&2; exit 1; }

"${adb[@]}" shell "rm -rf $dest/lincity $dest/LinCity.sh; mkdir -p $dest"
"${adb[@]}" push "$here/lincity/LinCity.sh" "$here/lincity/lincity" "$dest/" > /dev/null
"${adb[@]}" shell "echo lincity > $dest/.starboard_installed"
"${adb[@]}" shell "am force-stop org.force9.starboard; am start -n org.force9.starboard/.ui.game.GameActivity --es zip_name lincity --es launcher LinCity.sh" > /dev/null
echo "Launched. Log: ${adb[*]} shell run-as org.force9.starboard cat files/ipc/game.log"
