# Cola de trabajos en el PC: vigila QUEUE y cose en paralelo las tandas que van llegando.
#   blender -b --factory-startup --python queue_runner.py
# Cada tanda es una carpeta QUEUE\<nombre>\ con scripts\addons\clothing_design, tests\, render.py,
# jobs.json y, al final, READY.txt (se escribe el último para no empezar a medio copiar).
# La cola escribe <tanda>\logs\..., <tanda>\logs\ALL_DONE.txt al terminar, y QUEUE\HEARTBEAT.txt
# cada pocos segundos (tandas en espera / trabajos corriendo). QUEUE\STOP.txt la detiene.
import os, subprocess, json, time, bpy
QUEUE = os.path.dirname(os.path.abspath(__file__))
BL = bpy.app.binary_path
N = max(1, (os.cpu_count() or 2) // 2)
seen, pending, running = set(), [], []          # pending: (dir, job); running: (proc, file, dir, log)
left = {}                                        # dir -> jobs not finished
t0 = time.time()
print("cola: %s, %d a la vez" % (QUEUE, N), flush=True)
while not os.path.exists(os.path.join(QUEUE, "STOP.txt")):
    for name in sorted(os.listdir(QUEUE)):
        d = os.path.join(QUEUE, name)
        if d in seen or not os.path.isfile(os.path.join(d, "READY.txt")):
            continue
        seen.add(d)
        if os.path.exists(os.path.join(d, "logs", "ALL_DONE.txt")):
            continue
        try:
            jobs = json.load(open(os.path.join(d, "jobs.json"), encoding="utf-8"))
        except Exception as e:
            os.makedirs(os.path.join(d, "logs"), exist_ok=True)
            open(os.path.join(d, "logs", "ALL_DONE.txt"), "w").write("jobs.json ilegible: %s\n" % e)
            continue
        os.makedirs(os.path.join(d, "logs", "img"), exist_ok=True)
        left[d] = len(jobs)
        pending += [(d, j) for j in jobs]
        print("tanda %s: %d trabajos" % (name, len(jobs)), flush=True)
        if not jobs:
            open(os.path.join(d, "logs", "ALL_DONE.txt"), "w").write("0 trabajos\n")
    while pending and len(running) < N:
        d, j = pending.pop(0)
        env = dict(os.environ, BLENDER_USER_SCRIPTS=os.path.join(d, "scripts"), **j.get("env", {}))
        f = open(os.path.join(d, j["log"]), "w", encoding="utf-8")
        cmd = [BL, "-b", "--factory-startup", "--python", os.path.join(d, j["script"]), "--"] + j.get("args", [])
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=d,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        running.append((p, f, d, j["log"], time.time()))
    for r in list(running):
        if r[0].poll() is None and time.time() - r[4] > 1800:      # 30 min: colgado
            r[0].kill()
        if r[0].poll() is not None:
            r[1].close(); running.remove(r)
            left[r[2]] -= 1
            if left[r[2]] == 0:
                open(os.path.join(r[2], "logs", "ALL_DONE.txt"), "w").write("ok\n")
                print("tanda lista: %s" % os.path.basename(r[2]), flush=True)
    try:
        open(os.path.join(QUEUE, "HEARTBEAT.txt"), "w").write(
            "%s\nen espera: %d\ncorriendo: %s\n" % (time.ctime(), len(pending),
            ", ".join("%s/%s" % (os.path.basename(r[2]), os.path.basename(r[3])) for r in running)))
    except OSError:
        pass
    time.sleep(3)
for r in running:
    r[0].kill()
print("cola detenida", flush=True)
