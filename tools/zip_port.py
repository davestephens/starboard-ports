#!/usr/bin/env python3
"""Zips a staged port with fixed timestamps, modes and entry order.

An unchanged build then gives a byte-identical zip, so the catalogue's md5 and
date_updated change only when the port does.

Usage: zip_port.py OUT.zip STAGE_DIR
Every entry of STAGE_DIR goes at the top of the zip.
"""
import os
import stat
import sys
import zipfile

# The earliest time a zip header can hold.
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def add(zf, path, arcname):
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        sys.exit(f"zip_port: refusing symlink {path}")
    if stat.S_ISDIR(st.st_mode):
        info = zipfile.ZipInfo(arcname + "/", FIXED_TIME)
        info.external_attr = ((stat.S_IFDIR | 0o755) << 16) | 0x10
        zf.writestr(info, b"")
        for name in sorted(os.listdir(path)):
            add(zf, os.path.join(path, name), f"{arcname}/{name}")
        return
    mode = 0o755 if st.st_mode & stat.S_IXUSR else 0o644
    info = zipfile.ZipInfo(arcname, FIXED_TIME)
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    with open(path, "rb") as f:
        zf.writestr(info, f.read(), compresslevel=9)


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__.strip().splitlines()[-2])
    out, stage = argv[1], argv[2]
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w") as zf:
        for name in sorted(os.listdir(stage)):
            add(zf, os.path.join(stage, name), name)
    os.replace(tmp, out)


if __name__ == "__main__":
    main(sys.argv)
