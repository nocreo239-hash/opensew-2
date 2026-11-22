# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the Unity tools as one importable package:
dist/OpenSew_Unity_Tools-<version>.unitypackage

    python tools/build_unitypackage.py

Everything under unity/Assets/ that has a .meta next to it goes in, with the
GUIDs from those .meta files (so a project that already has the scripts gets
them updated in place instead of duplicated). A .unitypackage is a gzipped
tar with one folder per asset GUID holding `asset`, `asset.meta` and
`pathname`. Plain Python, no Unity needed."""
import gzip, io, os, re, sys, tarfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITY = os.path.join(ROOT, "unity")


def _add(tar, name, data=None):
    """A file, or with data None a directory - Unity's own packages have one
    directory entry per GUID before its files, and Unity imports nothing
    from a package without them."""
    info = tarfile.TarInfo(name)
    info.mtime = int(time.time())
    if data is None:
        info.type = tarfile.DIRTYPE
        info.mode = 0o777
        tar.addfile(info)
        return
    info.size = len(data)
    info.mode = 0o777
    tar.addfile(info, io.BytesIO(data))


def main():
    manifest = open(os.path.join(ROOT, "clothing_design", "blender_manifest.toml"), encoding="utf-8").read()
    version = re.search(r'^version\s*=\s*"([^"]+)"', manifest, re.M).group(1)
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "OpenSew_Unity_Tools-%s.unitypackage" % version)
    n = 0
    # Unity's packages end with exactly two zero blocks, GNU headers
    # ("ustar  "), and Unity imports nothing - silently - from a tar padded
    # out to the usual 10 KiB record, so the record is one block here
    tarfile.RECORDSIZE = tarfile.BLOCKSIZE
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for base, dirs, files in os.walk(os.path.join(UNITY, "Assets")):
            for f in sorted(files):
                if not f.endswith(".meta"):
                    continue
                meta_path = os.path.join(base, f)
                asset_path = meta_path[:-5]
                meta = open(meta_path, "rb").read()
                guid = re.search(rb"^guid:\s*([0-9a-f]{32})", meta, re.M).group(1).decode()
                rel = os.path.relpath(asset_path, UNITY).replace(os.sep, "/")
                _add(tar, guid)
                if os.path.isfile(asset_path):
                    _add(tar, guid + "/asset", open(asset_path, "rb").read())
                _add(tar, guid + "/asset.meta", meta)
                _add(tar, guid + "/pathname", rel.encode("utf-8"))
                n += 1
    with open(out, "wb") as f:
        # gzip the way Unity writes it: inner name archtemp.tar
        with gzip.GzipFile(filename="archtemp.tar", mode="wb", fileobj=f, mtime=int(time.time())) as gz:
            gz.write(buf.getvalue())
    print("%s (%d assets)" % (out, n))
    return out


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
