# En la consola de Python de Blender:
#   exec(open(r"E:\assets\DOWNLOADS\OpenSew_test\queue\start_queue.py").read())
import os, subprocess, bpy
Q = r"E:\assets\DOWNLOADS\OpenSew_test\queue"
try: os.remove(os.path.join(Q, "STOP.txt"))
except OSError: pass
subprocess.Popen([bpy.app.binary_path, "-b", "--factory-startup", "--python", os.path.join(Q, "queue_runner.py")],
                 stdout=open(os.path.join(Q, "queue_log.txt"), "a"), stderr=subprocess.STDOUT,
                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
print("cola lanzada; cpu:", os.cpu_count())
