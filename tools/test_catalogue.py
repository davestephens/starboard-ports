"""Tests for catalogue.py and zip_port.py. Run: python3 -m unittest discover -s tools"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalogue  # noqa: E402

CONFIG = {"prefix": "test", "name": "Test Ports", "repo": "someone/test-ports"}
BASE_URL = "https://github.com/someone/test-ports/releases/download/ports-latest"


def port_json(name="demo.zip", items=("Demo.sh", "demo")):
    return {"version": 4, "name": name, "items": list(items), "attr": {"title": "Demo", "image": None}}


def make_zip(directory, name="demo.zip", files=None, port=None):
    """Writes a zip laid out like a PortMaster release; files overrides or removes (None) entries."""
    base = name[:-4]
    entries = {
        "Demo.sh": b"#!/bin/bash\n",
        f"{base}/demo.aarch64": b"\x7fELF",
        f"{base}/port.json": json.dumps(port or port_json(name, ("Demo.sh", base))).encode(),
        f"{base}/screenshot.jpg": b"shot",
        f"{base}/cover.png": b"cover",
    }
    entries.update(files or {})
    path = os.path.join(directory, name)
    with zipfile.ZipFile(path, "w") as zf:
        for entry, data in entries.items():
            if data is not None:
                zf.writestr(entry, data)
    return path


class ReadPortTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def assertRejected(self, path, message):
        with self.assertRaises(catalogue.PortError) as cm:
            catalogue.read_port(path)
        self.assertIn(message, str(cm.exception))

    def test_good_zip(self):
        port, images = catalogue.read_port(make_zip(self.dir))
        self.assertEqual(port["attr"]["title"], "Demo")
        self.assertEqual(images["screenshot"], (".jpg", b"shot"))
        self.assertEqual(images["cover"], (".png", b"cover"))

    def test_items_may_end_in_slash(self):
        port = port_json(items=("Demo.sh", "demo/"))
        catalogue.read_port(make_zip(self.dir, port=port))

    def test_missing_launcher(self):
        port = port_json(items=("demo",))
        self.assertRejected(make_zip(self.dir, files={"Demo.sh": None}, port=port), "no launcher")

    def test_missing_port_folder(self):
        path = os.path.join(self.dir, "demo.zip")
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Demo.sh", b"")
            zf.writestr("other/port.json", b"{}")
        self.assertRejected(path, "no demo/ folder")

    def test_missing_port_json(self):
        self.assertRejected(make_zip(self.dir, files={"demo/port.json": None}), "no demo/port.json")

    def test_bad_port_json(self):
        self.assertRejected(make_zip(self.dir, files={"demo/port.json": b"{"}), "bad port.json")

    def test_port_json_name_mismatch(self):
        self.assertRejected(make_zip(self.dir, port=port_json(name="other.zip")), "name is 'other.zip'")

    def test_items_mismatch(self):
        self.assertRejected(make_zip(self.dir, files={"Extra.sh": b""}), "items")

    def test_missing_title(self):
        port = port_json()
        port["attr"]["title"] = ""
        self.assertRejected(make_zip(self.dir, port=port), "no attr.title")

    def test_missing_image(self):
        self.assertRejected(make_zip(self.dir, files={"demo/cover.png": None}), "no demo/cover")

    def test_unsafe_entry(self):
        self.assertRejected(make_zip(self.dir, files={"demo/../../evil": b""}), "unsafe entry")

    def test_bad_zip_name(self):
        path = os.path.join(self.dir, "Demo Port.zip")
        os.rename(make_zip(self.dir), path)
        self.assertRejected(path, "name must be")

    def test_not_a_zip(self):
        path = os.path.join(self.dir, "demo.zip")
        with open(path, "wb") as f:
            f.write(b"not a zip")
        self.assertRejected(path, "demo.zip")


class CatalogueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.zip = make_zip(self.dir)
        with open(self.zip, "rb") as f:
            self.md5 = hashlib.md5(f.read()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def run_catalogue(self, previous=None, today="2026-11-22"):
        return catalogue.catalogue([self.zip], CONFIG, "ports-latest", previous, today)

    def test_entry_is_port_json_plus_source(self):
        ports, _, _, changed = self.run_catalogue()
        entry = ports["ports"]["demo.zip"]
        self.assertEqual(entry["attr"]["title"], "Demo")
        self.assertEqual(entry["source"], {
            "date_added": "2026-11-22",
            "date_updated": "2026-11-22",
            "md5": self.md5,
            "size": os.path.getsize(self.zip),
            "url": f"{BASE_URL}/demo.zip",
        })
        self.assertEqual(changed, [self.zip])

    def test_image_names(self):
        ports, _, _, _ = self.run_catalogue()
        image = ports["ports"]["demo.zip"]["attr"]["image"]
        self.assertEqual(image["screenshot"], "screenshot.jpg")
        self.assertEqual(image["cover"], "cover.png")
        self.assertEqual(image["covers"], ["cover.png"])

    def test_images_zip(self):
        ports, images, _, _ = self.run_catalogue()
        with zipfile.ZipFile(io.BytesIO(images)) as zf:
            self.assertEqual(sorted(zf.namelist()), ["demo.cover.png", "demo.screenshot.jpg"])
            self.assertEqual(zf.read("demo.screenshot.jpg"), b"shot")
        util = ports["utils"]["images.zip"]
        self.assertEqual(util["md5"], hashlib.md5(images).hexdigest())
        self.assertEqual(util["url"], f"{BASE_URL}/images.zip")

    def test_images_zip_is_reproducible(self):
        _, first, _, _ = self.run_catalogue()
        _, second, _, _ = self.run_catalogue(today="2027-01-01")
        self.assertEqual(first, second)

    def test_source_json(self):
        _, _, source, _ = self.run_catalogue()
        self.assertEqual(source["prefix"], "test")
        self.assertEqual(source["name"], "Test Ports")
        self.assertEqual(source["api"], "PortMasterV3")
        self.assertEqual(source["url"], f"{BASE_URL}/ports.json")

    def test_tag_sets_urls(self):
        ports, _, source, _ = catalogue.catalogue([self.zip], CONFIG, "ports-test", None, "2026-11-22")
        self.assertTrue(ports["ports"]["demo.zip"]["source"]["url"].endswith("/download/ports-test/demo.zip"))
        self.assertTrue(source["url"].endswith("/download/ports-test/ports.json"))

    def test_republish_unchanged_keeps_dates(self):
        first, _, _, _ = self.run_catalogue(today="2026-01-01")
        second, _, _, changed = self.run_catalogue(previous=first, today="2026-11-22")
        self.assertEqual(second, first)
        self.assertEqual(changed, [])

    def test_republish_changed_keeps_date_added(self):
        first, _, _, _ = self.run_catalogue(today="2026-01-01")
        first["ports"]["demo.zip"]["source"]["md5"] = "0" * 32
        second, _, _, changed = self.run_catalogue(previous=first, today="2026-11-22")
        source = second["ports"]["demo.zip"]["source"]
        self.assertEqual(source["date_added"], "2026-01-01")
        self.assertEqual(source["date_updated"], "2026-11-22")
        self.assertEqual(changed, [self.zip])

    def test_duplicate_zip_names(self):
        other = os.path.join(self.dir, "sub")
        os.mkdir(other)
        with self.assertRaises(catalogue.PortError):
            catalogue.catalogue([self.zip, make_zip(other)], CONFIG, "ports-latest", None, "2026-11-22")


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.zip = make_zip(self.dir)
        self.config = os.path.join(self.dir, "catalogue.json")
        with open(self.config, "w") as f:
            json.dump(CONFIG, f)
        self.out = os.path.join(self.dir, "out")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *extra):
        return catalogue.main(["--config", self.config, "--out", self.out, "--today", "2026-11-22",
                               *extra, self.zip])

    def upload_list(self):
        with open(os.path.join(self.out, "upload.txt")) as f:
            return [os.path.basename(line.strip()) for line in f]

    def test_writes_outputs(self):
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(sorted(os.listdir(self.out)),
                         ["images.zip", "ports.json", "test.source.json", "upload.txt"])
        self.assertEqual(self.upload_list(), ["demo.zip", "images.zip", "ports.json"])

    def test_nothing_to_upload_when_unchanged(self):
        self.run_main()
        previous = os.path.join(self.dir, "previous.json")
        os.rename(os.path.join(self.out, "ports.json"), previous)
        self.assertEqual(self.run_main("--previous", previous), 0)
        self.assertEqual(self.upload_list(), [])

    def test_bad_zip_fails(self):
        os.remove(self.zip)
        self.zip = make_zip(self.dir, files={"demo/port.json": None})
        self.assertEqual(self.run_main(), 1)


class ZipPortTest(unittest.TestCase):
    def test_reproducible_and_keeps_exec_bit(self):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zip_port.py")
        with tempfile.TemporaryDirectory() as tmp:
            stage = os.path.join(tmp, "stage")
            os.makedirs(os.path.join(stage, "demo"))
            launcher = os.path.join(stage, "Demo.sh")
            with open(launcher, "w") as f:
                f.write("#!/bin/bash\n")
            os.chmod(launcher, 0o755)
            with open(os.path.join(stage, "demo", "data.txt"), "w") as f:
                f.write("data")
            outs = []
            for i in range(2):
                os.utime(launcher, (1_000_000 * (i + 1),) * 2)
                out = os.path.join(tmp, f"demo{i}.zip")
                subprocess.run([sys.executable, script, out, stage], check=True)
                with open(out, "rb") as f:
                    outs.append(f.read())
            self.assertEqual(outs[0], outs[1])
            with zipfile.ZipFile(io.BytesIO(outs[0])) as zf:
                self.assertEqual(zf.namelist(), ["Demo.sh", "demo/", "demo/data.txt"])
                self.assertEqual(zf.getinfo("Demo.sh").external_attr >> 16 & 0o777, 0o755)
                self.assertEqual(zf.getinfo("demo/data.txt").external_attr >> 16 & 0o777, 0o644)


if __name__ == "__main__":
    unittest.main()
