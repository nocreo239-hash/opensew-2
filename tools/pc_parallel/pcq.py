#!/usr/bin/env python3
# Prepara una tanda para la cola de trabajos del PC de Allan.
#   pcq.py prep WORKTREE NOMBRE JOBS.json
# JOBS.json: lista [{"script": "tests/test_fit.py" | "render.py" | "tests/...", "args": [...],
#                    "env": {...}, "log": "logs/x.txt"}]  (rutas relativas a la tanda; las imágenes de
#                    render.py van con OUT "logs/img/<prefijo>")
# Avatares en el PC (para --fbx / render.py / CD_AVATARS): `pcq.py avatars` los imprime con su DROP.
# Escribe /tmp/pcq_<NOMBRE>_files.json (lista {devicePath, stagedPath} para UNA llamada a
# mcp__remote-devices__device_commit_files) y /tmp/pcq_<NOMBRE>_ready.json (READY.txt, en una
# SEGUNDA llamada, después de la primera). Resultados: device_list_dir de <tanda>\logs hasta que
# aparezca ALL_DONE.txt; luego device_stage_files de los logs/imágenes que quieras leer.
import os, sys, json, shutil, subprocess, re
Q = "E:\\assets\\DOWNLOADS\\OpenSew_test\\queue"
sys.path.insert(0, "/home/claude/opensew-2/tools/pc_parallel")
GJ = "/home/claude/opensew-2/tools/pc_parallel/genjobs.py"


def avatars():
    src = open(GJ, encoding="utf-8").read()
    ns = {}
    exec(src.split("FIT =")[0], ns)
    return ns["AV"], ns["DROP"]


if sys.argv[1] == "avatars":
    av, drop = avatars()
    print(json.dumps({"AV": av, "DROP": drop}, ensure_ascii=False, indent=1))
    sys.exit()
_, cmd, wt, name, jobsf = sys.argv
assert re.fullmatch(r"[A-Za-z0-9_-]+", name), "nombre: solo letras, números, _ y -"
out = "/mnt/user-data/outputs/pcq/" + name
shutil.rmtree(out, ignore_errors=True)
files = subprocess.check_output(["git", "-C", wt, "ls-files", "clothing_design", "tests"], text=True).split()
# include uncommitted edits too: copy from the working tree
pairs = []
for f in files:
    if f.startswith("tests/") and not f.endswith(".py"):
        continue
    rel = ("scripts/addons/" + f) if f.startswith("clothing_design") else f
    pairs.append((os.path.join(wt, f), rel))
rp = os.path.join(wt, "tools/pc_parallel/render.py")
pairs.append((rp if os.path.exists(rp) else "/home/claude/opensew-2/tools/pc_parallel/render.py", "render.py"))
for s, r in pairs:
    d = os.path.join(out, r); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy(s, d)
jobs = json.load(open(jobsf))
for j in jobs:
    assert j["log"].startswith("logs/"), j
shutil.copy(jobsf, os.path.join(out, "jobs.json"))
open(os.path.join(out, "READY.txt"), "w").write("ready\n")
H = Q + "\\" + name
res, ready = [], []
for d, _, fs in os.walk(out):
    for f in fs:
        p = os.path.join(d, f)
        e = {"devicePath": H + "\\" + os.path.relpath(p, out).replace("/", "\\"), "stagedPath": p}
        (ready if f == "READY.txt" and d == out else res).append(e)
assert len(res) <= 50, len(res)
json.dump(res, open("/tmp/pcq_%s_files.json" % name, "w"))
json.dump(ready, open("/tmp/pcq_%s_ready.json" % name, "w"))
print("%d archivos + READY -> %s" % (len(res), H))
