# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the Unity tools as one importable package:
dist/OpenSew_Unity_Tools-<version>.unitypackage

    python tools/build_unitypackage.py

Everything under unity/Assets/ that has a .meta next to it goes in, with the
GUIDs from those .meta files (so a project that already has the scripts gets
them updated in place instead of duplicated). A .unitypackage is a gzipped
tar with one folder per asset GUID holding `asset`, `asset.meta` and
`pathname`. Plain Python, no Unity needed."""
import io, os, re, sys, tarfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITY = os.path.join(ROOT, "unity")


def _add(tar, name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = int(time.time())
    tar.addfile(info, io.BytesIO(data))


def main():
    manifest = open(os.path.join(ROOT, "clothing_design", "blender_manifest.toml"), encoding="utf-8").read()
    version = re.search(r'^version\s*=\s*"([^"]+)"', manifest, re.M).group(1)
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "OpenSew_Unity_Tools-%s.unitypackage" % version)
    n = 0
    with tarfile.open(out, "w:gz") as tar:
        for base, dirs, files in os.walk(os.path.join(UNITY, "Assets")):
            for f in sorted(files):
                if not f.endswith(".meta"):
                    continue
                meta_path = os.path.join(base, f)
                asset_path = meta_path[:-5]
                meta = open(meta_path, "rb").read()
                guid = re.search(rb"^guid:\s*([0-9a-f]{32})", meta, re.M).group(1).decode()
                rel = os.path.relpath(asset_path, UNITY).replace(os.sep, "/")
                _add(tar, guid + "/asset.meta", meta)
                _add(tar, guid + "/pathname", rel.encode("utf-8"))
                if os.path.isfile(asset_path):
                    _add(tar, guid + "/asset", open(asset_path, "rb").read())
                n += 1
    print("%s (%d assets)" % (out, n))
    return out


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
