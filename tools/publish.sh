#!/bin/bash
# Builds every port, writes the catalogue and uploads what changed to a GitHub release.
#
# Usage: tools/publish.sh [--tag TAG] [--skip-build] [--dry-run]
#   --tag TAG     release to publish to (default ports-latest); its URLs go into the catalogue
#   --skip-build  use the zips already in ports/*/dist (CI builds them in earlier jobs)
#   --dry-run     write the catalogue to build/catalogue and list the uploads, but upload nothing
#
# The release's tag is moved to HEAD, which must be pushed, so GitHub's source archive
# matches the published build scripts.
set -euo pipefail

root="$(cd -- "$(dirname "$0")/.." && pwd)"
tag=ports-latest
build=1
dry_run=0
while [ $# -gt 0 ]; do
    case "$1" in
        --tag) tag=$2; shift 2 ;;
        --skip-build) build=0; shift ;;
        --dry-run) dry_run=1; shift ;;
        *) echo "Unknown option $1" >&2; exit 2 ;;
    esac
done

repo=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["repo"])' "$root/catalogue.json")
prefix=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["prefix"])' "$root/catalogue.json")
base_url="https://github.com/$repo/releases/download/$tag"
out="$root/build/catalogue"

if [ "$build" = 1 ]; then
    for script in "$root"/ports/*/build.sh; do
        echo "== $script"
        "$script"
    done
fi

shopt -s nullglob
zips=("$root"/ports/*/dist/*.zip)
[ ${#zips[@]} -gt 0 ] || { echo "No zips in ports/*/dist" >&2; exit 1; }

rm -rf "$out"
mkdir -p "$out/previous"
# A missing file means a first publish.
curl -sSfL -o "$out/previous/ports.json" "$base_url/ports.json" 2>/dev/null || rm -f "$out/previous/ports.json"
curl -sSfL -o "$out/previous/source.json" "$base_url/$prefix.source.json" 2>/dev/null \
    || rm -f "$out/previous/source.json"

python3 "$root/tools/catalogue.py" --tag "$tag" --previous "$out/previous/ports.json" \
    --out "$out" "${zips[@]}"

# Port zips and their corresponding source first, the catalogue last, so ports.json
# never points at a zip that is not there yet.
uploads=()
catalogue_files=()
while read -r f; do
    case "$f" in
        *.zip)
            uploads+=("$f")
            if [ "$(basename "$f")" != images.zip ]; then
                uploads+=("$(dirname "$f")"/source/*)
            fi
            ;;
        *) catalogue_files+=("$f") ;;
    esac
done < "$out/upload.txt"
if ! cmp -s "$out/$prefix.source.json" "$out/previous/source.json"; then
    catalogue_files+=("$out/$prefix.source.json")
fi

if [ ${#uploads[@]} -eq 0 ] && [ ${#catalogue_files[@]} -eq 0 ]; then
    echo "Nothing changed."
    exit 0
fi
echo "To upload to $tag:"
printf '  %s\n' "${uploads[@]#"$root"/}" "${catalogue_files[@]#"$root"/}"
[ "$dry_run" = 1 ] && exit 0

sha=$(git -C "$root" rev-parse HEAD)
if gh release view "$tag" --repo "$repo" > /dev/null 2>&1; then
    gh api -X PATCH "repos/$repo/git/refs/tags/$tag" -f sha="$sha" -F force=true > /dev/null
else
    gh release create "$tag" --repo "$repo" --target "$sha" --title "Starboard Ports ($tag)" \
        --notes "The Starboard Ports catalogue. Add this source in Starboard: $base_url/$prefix.source.json"
fi
if [ ${#uploads[@]} -gt 0 ]; then
    gh release upload "$tag" --repo "$repo" --clobber "${uploads[@]}"
fi
if [ ${#catalogue_files[@]} -gt 0 ]; then
    gh release upload "$tag" --repo "$repo" --clobber "${catalogue_files[@]}"
fi
echo "Published $base_url/$prefix.source.json"
