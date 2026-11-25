# En la consola de Python de Blender:
#   exec(open(r"E:\assets\DOWNLOADS\OpenSew_test\run\launch.py").read())
import os, subprocess, bpy
H = r"E:\assets\DOWNLOADS\OpenSew_test\run"
os.makedirs(os.path.join(H, "logs"), exist_ok=True)
subprocess.Popen([bpy.app.binary_path, "-b", "--factory-startup", "--python", os.path.join(H, "runner.py")],
                 stdout=open(os.path.join(H, "logs", "runner.txt"), "w"), stderr=subprocess.STDOUT,
                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
print("lanzado; cpu:", os.cpu_count())
