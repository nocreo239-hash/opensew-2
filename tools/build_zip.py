# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the installable add-on: dist/opensew2_vrchat-<version>.zip.

    python tools/build_zip.py

The zip is a Blender extension (blender_manifest.toml at its root). In
Blender 5.2: Edit > Preferences > Get Extensions > the menu at the top right
> Install from Disk, and pick the zip. Plain Python, no Blender needed."""
import os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "clothing_design")


def main():
    manifest = open(os.path.join(SRC, "blender_manifest.toml"), encoding="utf-8").read()
    version = re.search(r'^version\s*=\s*"([^"]+)"', manifest, re.M).group(1)
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "opensew2_vrchat-%s.zip" % version)
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(SRC):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith((".pyc", ".blend1")):
                    continue
                full = os.path.join(base, f)
                z.write(full, os.path.relpath(full, SRC))
                n += 1
        # the license travels with the code it covers
        z.write(os.path.join(ROOT, "LICENSE"), "LICENSE")
    print("%s (%d files, %.1f MB)" % (out, n + 1, os.path.getsize(out) / 1e6))
    return out


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
