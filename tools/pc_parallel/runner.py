# Lanza las pruebas de OpenSew en paralelo en este PC, con el código de esta carpeta
# (scripts/addons/clothing_design) y sin tocar el add-on instalado.
#   blender -b --factory-startup --python runner.py
import os, subprocess, sys, time, bpy
HERE = os.path.dirname(os.path.abspath(__file__))
BL = bpy.app.binary_path
DROP = "coat,jacket,tops,pants,belt,accessories,tanktop,tsyatu,outer,hat,arm cover,gloves,necklace,shirt,inner,skinny,neckless,outfit"
import sys as _s
WHICH = _s.argv[_s.argv.index("--") + 1] if "--" in _s.argv else "all"
BEAST = r"E:\assets\DOWNLOADS\The Beast 1.0\fbx\TheBeast.fbx"
MAO = r"E:\assets\DOWNLOADS\mao_v_1.0.9\mao\FBX\mao.fbx"
jobs = []
if WHICH == "extra":
    jobs.append(([BL, "-b", "--factory-startup", "--python", os.path.join(HERE, "tests", "test_fit.py"),
                  "--", "--fbx", BEAST, "--drop", DROP, "--only", "HOODIE"], os.path.join(HERE, "logs", "fit_TheBeast_HOODIE.txt")))
    jobs.append(([BL, "-b", "--factory-startup", "--python", os.path.join(HERE, "tests", "test_export.py"), "--", "HOODIE"],
                 os.path.join(HERE, "logs", "export_mao_HOODIE.txt"), {"CD_AVATARS": MAO}))
os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
env0 = dict(os.environ, BLENDER_USER_SCRIPTS=os.path.join(HERE, "scripts"))
N = max(1, (os.cpu_count() or 2) // 2)
print("runner: %d jobs, %d at a time" % (len(jobs), N), flush=True)
running = []
t0 = time.time()
while jobs or running:
    while jobs and len(running) < N:
        j = jobs.pop(0)
        env = dict(env0, **(j[2] if len(j) > 2 else {}))
        f = open(j[1], "w")
        running.append((subprocess.Popen(j[0], stdout=f, stderr=subprocess.STDOUT, env=env), f, j[1]))
    for r in list(running):
        if r[0].poll() is not None:
            r[1].close(); running.remove(r)
            print("done %s (%.0f s)" % (os.path.basename(r[2]), time.time() - t0), flush=True)
    time.sleep(2)
open(os.path.join(HERE, "logs", "ALL_DONE.txt"), "w").write("%.0f s\n" % (time.time() - t0))
