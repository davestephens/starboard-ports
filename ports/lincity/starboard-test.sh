#!/bin/bash
# Copies the built port to a device running Starboard, into the sideloaded ports folder, and
# launches it. Needs a Starboard build that knows the "local" source.
set -euo pipefail

here="$(cd -- "$(dirname "$0")" && pwd)"
adb=(adb)
[ $# -ge 1 ] && adb=(adb -s "$1")
dest=/storage/emulated/0/Starboard/ports.local/lincity

[ -f "$here/lincity/lincity/xlincity.aarch64" ] || { echo "Run ./build.sh first" >&2; exit 1; }

"${adb[@]}" shell "rm -rf $dest/lincity $dest/LinCity.sh; mkdir -p $dest"
"${adb[@]}" push "$here/lincity/LinCity.sh" "$here/lincity/lincity" "$dest/" > /dev/null
"${adb[@]}" shell "echo lincity > $dest/.starboard_installed"
"${adb[@]}" shell "am force-stop org.force9.starboard; am start -n org.force9.starboard/.ui.game.GameActivity --es source_id local --es zip_name lincity --es launcher LinCity.sh" > /dev/null
echo "Launched. Log: ${adb[*]} shell run-as org.force9.starboard cat files/ipc/game.log"
