#!/usr/bin/env python3
"""Writes the catalogue for a set of port zips: ports.json, images.zip and <prefix>.source.json.

Usage: catalogue.py [--tag TAG] [--previous PORTS_JSON] [--today YYYY-MM-DD] --out DIR ZIP...

The zips must be laid out like PortMaster release zips. --previous is the published
ports.json, which keeps each port's date_added, and its date_updated while the zip is
unchanged. DIR/upload.txt lists the files whose content differs from what is published.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "catalogue.json")
IMAGE_KINDS = ("screenshot", "cover")
IMAGE_EXTS = (".jpg", ".png")
PORT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
# Must match tools/zip_port.py, so an unchanged images.zip keeps its md5.
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


class PortError(Exception):
    pass


def md5_of(data):
    return hashlib.md5(data).hexdigest()


def read_port(zip_path):
    """Checks a port zip's layout and returns (port_json, {kind: (ext, bytes)})."""
    zip_name = os.path.basename(zip_path)
    base = zip_name[:-len(".zip")] if zip_name.endswith(".zip") else ""
    if not PORT_NAME_RE.match(base):
        raise PortError(f"{zip_name}: name must be <port>.zip, lowercase letters, digits, . _ -")
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as e:
        raise PortError(f"{zip_name}: {e}") from e
    with zf:
        names = zf.namelist()
        for n in names:
            parts = n.split("/")
            if n.startswith("/") or "\\" in n or ".." in parts:
                raise PortError(f"{zip_name}: unsafe entry {n}")
        top = {n.split("/")[0] for n in names}
        if not any(n.startswith(base + "/") for n in names):
            raise PortError(f"{zip_name}: no {base}/ folder at the top")
        launchers = sorted(t for t in top if t.endswith(".sh") and t in names)
        if not launchers:
            raise PortError(f"{zip_name}: no launcher .sh at the top")
        try:
            port = json.loads(zf.read(f"{base}/port.json"), object_pairs_hook=dict)
        except KeyError:
            raise PortError(f"{zip_name}: no {base}/port.json") from None
        except ValueError as e:
            raise PortError(f"{zip_name}: bad port.json: {e}") from e
        if port.get("name") != zip_name:
            raise PortError(f"{zip_name}: port.json name is {port.get('name')!r}")
        items = {i.rstrip("/") for i in port.get("items") or []}
        if items != top:
            raise PortError(f"{zip_name}: port.json items {sorted(items)} != zip top level {sorted(top)}")
        if not (port.get("attr") or {}).get("title"):
            raise PortError(f"{zip_name}: port.json has no attr.title")
        images = {}
        for kind in IMAGE_KINDS:
            for ext in IMAGE_EXTS:
                if f"{base}/{kind}{ext}" in names:
                    images[kind] = (ext, zf.read(f"{base}/{kind}{ext}"))
                    break
            else:
                raise PortError(f"{zip_name}: no {base}/{kind}.jpg or .png")
    return port, images


def build_images_zip(images_by_port):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for base in sorted(images_by_port):
            for kind in IMAGE_KINDS:
                ext, data = images_by_port[base][kind]
                info = zipfile.ZipInfo(f"{base}.{kind}{ext}", FIXED_TIME)
                info.external_attr = 0o644 << 16
                zf.writestr(info, data)
    return buf.getvalue()


def catalogue(zip_paths, config, tag, previous, today):
    """Returns (ports_json, images_zip_bytes, source_json, changed_zip_paths)."""
    base_url = f"https://github.com/{config['repo']}/releases/download/{tag}"
    prev_ports = (previous or {}).get("ports", {})
    ports, images_by_port, changed = {}, {}, []
    for path in sorted(zip_paths, key=os.path.basename):
        zip_name = os.path.basename(path)
        if zip_name in ports:
            raise PortError(f"{zip_name}: two zips with this name")
        port, images = read_port(path)
        with open(path, "rb") as f:
            data = f.read()
        md5 = md5_of(data)
        prev_source = (prev_ports.get(zip_name) or {}).get("source") or {}
        unchanged = prev_source.get("md5") == md5
        if not unchanged:
            changed.append(path)
        base = zip_name[:-len(".zip")]
        images_by_port[base] = images
        # PortMaster names covers in a "covers" list. Starboard reads "cover", and without it
        # shows the screenshot as the cover.
        port["attr"]["image"] = {
            "screenshot": f"screenshot{images['screenshot'][0]}",
            "cover": f"cover{images['cover'][0]}",
            "covers": [f"cover{images['cover'][0]}"],
            "thumbnail": None,
            "video": None,
        }
        port["source"] = {
            "date_added": prev_source.get("date_added") or today,
            "date_updated": prev_source.get("date_updated") if unchanged and prev_source.get("date_updated") else today,
            "md5": md5,
            "size": len(data),
            "url": f"{base_url}/{zip_name}",
        }
        ports[zip_name] = port

    images_zip = build_images_zip(images_by_port)
    ports_json = {
        "ports": ports,
        "utils": {
            "images.zip": {
                "name": "images.zip",
                "md5": md5_of(images_zip),
                "size": len(images_zip),
                "url": f"{base_url}/images.zip",
            },
        },
    }
    source_json = {
        "prefix": config["prefix"],
        "api": "PortMasterV3",
        "name": config["name"],
        "url": f"{base_url}/ports.json",
        "last_checked": None,
        "version": 1,
        "data": {},
    }
    return ports_json, images_zip, source_json, changed


def dumps(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--tag", default="ports-latest")
    ap.add_argument("--previous", help="the published ports.json, if there is one")
    ap.add_argument("--today", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--out", required=True)
    ap.add_argument("zips", nargs="+")
    args = ap.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)
    previous = None
    if args.previous and os.path.exists(args.previous):
        with open(args.previous) as f:
            previous = json.load(f)
    try:
        ports_json, images_zip, source_json, changed = catalogue(
            args.zips, config, args.tag, previous, args.today)
    except PortError as e:
        print(f"catalogue: {e}", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    source_name = f"{config['prefix']}.source.json"
    outputs = {
        "images.zip": images_zip,
        "ports.json": dumps(ports_json).encode(),
        source_name: dumps(source_json).encode(),
    }
    for name, data in outputs.items():
        with open(os.path.join(args.out, name), "wb") as f:
            f.write(data)

    upload = [os.path.abspath(p) for p in changed]
    prev_images = ((previous or {}).get("utils") or {}).get("images.zip") or {}
    if prev_images.get("md5") != ports_json["utils"]["images.zip"]["md5"]:
        upload.append(os.path.abspath(os.path.join(args.out, "images.zip")))
    if previous != ports_json:
        upload.append(os.path.abspath(os.path.join(args.out, "ports.json")))
    with open(os.path.join(args.out, "upload.txt"), "w") as f:
        f.writelines(p + "\n" for p in upload)
    for p in ports_json["ports"].values():
        print(f"{p['name']}: {p['source']['md5']} {p['source']['size']} bytes, updated {p['source']['date_updated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
