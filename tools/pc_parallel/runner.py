# Corre en paralelo, en el PC, la lista de trabajos de jobs.json con el código de
# scripts/addons/clothing_design (sin tocar el add-on instalado).
#   blender -b --factory-startup --python runner.py
# jobs.json: [{"script": "tests/test_fit.py", "args": [...], "env": {...}, "log": "logs/x.txt"}, ...]
import os, subprocess, json, time, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
BL = bpy.app.binary_path
jobs = json.load(open(os.path.join(HERE, "jobs.json"), encoding="utf-8"))
os.makedirs(os.path.join(HERE, "logs", "img"), exist_ok=True)
env0 = dict(os.environ, BLENDER_USER_SCRIPTS=os.path.join(HERE, "scripts"))
N = max(1, (os.cpu_count() or 2) // 2)
print("runner: %d jobs, %d at a time" % (len(jobs), N), flush=True)
running, t0 = [], time.time()
while jobs or running:
    while jobs and len(running) < N:
        j = jobs.pop(0)
        env = dict(env0, **j.get("env", {}))
        f = open(os.path.join(HERE, j["log"]), "w", encoding="utf-8")
        cmd = [BL, "-b", "--factory-startup", "--python", os.path.join(HERE, j["script"]), "--"] + j.get("args", [])
        running.append((subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=HERE), f, j["log"]))
    for r in list(running):
        if r[0].poll() is not None:
            r[1].close(); running.remove(r)
            print("done %s (%.0f s)" % (r[2], time.time() - t0), flush=True)
    time.sleep(2)
open(os.path.join(HERE, "logs", "ALL_DONE.txt"), "w").write("%.0f s\n" % (time.time() - t0))
