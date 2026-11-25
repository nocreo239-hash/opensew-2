# Lista lo que lleva un .unitypackage (tar.gz de carpetas GUID con 'pathname'):
# prefabs, scripts, asmdef y dll, para saber qué compilará Unity al importarlo.
#   blender -b --python tests/n_pkglist.py -- PAQUETE.unitypackage
import sys, tarfile, collections

pkg = sys.argv[sys.argv.index("--") + 1:][0]
paths = []
with tarfile.open(pkg, "r|gz") as t:
    for m in t:
        if m.name.endswith("/pathname"):
            paths.append(t.extractfile(m).read().decode("utf-8", "replace").splitlines()[0])
print("%d assets" % len(paths))
ext = collections.Counter(p.rsplit(".", 1)[-1].lower() if "." in p.split("/")[-1] else "(dir)" for p in paths)
print(dict(ext.most_common()))
tops = collections.Counter("/".join(p.split("/")[:3]) for p in paths)
for k, v in sorted(tops.items()):
    print("  %5d %s" % (v, k))
for p in sorted(paths):
    if p.lower().endswith((".prefab", ".cs", ".asmdef", ".dll", ".asmref", ".unity")):
        print("  " + p)
