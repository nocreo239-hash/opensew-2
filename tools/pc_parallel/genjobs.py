# Genera jobs.json para la batería completa. Uso: python genjobs.py > jobs.json
import json
DROP = "coat,jacket,tops,pants,belt,accessories,tanktop,tsyatu,outer,hat,arm cover,gloves,necklace,shirt,inner,skinny,neckless,outfit"
AV = {
    "TheBeast": r"E:\assets\DOWNLOADS\The Beast 1.0\fbx\TheBeast.fbx",
    "Manuka": r"E:\assets\DOWNLOADS\MANUKA_ver1.02\MANUKA_ver1.02\MANUKA.fbx",
    "Hanka": "E:\\assets\\DOWNLOADS\\Hanka\\斑霞-Hanka-Ver1.2\\斑霞-Hanka-Ver1.2\\FBX\\Hanka.fbx",
    "Mao": r"E:\assets\DOWNLOADS\mao_v_1.0.9\mao\FBX\mao.fbx",
    "Vlau": r"E:\assets\DOWNLOADS\ROKOSHOP_Vlau_ver1.12\ROKOSHOP_Vlau_ver1.12\ModelData\00_FBX\Vlau.fbx",
    "Minase": r"E:\assets\DOWNLOADS\Minase_v1.1.10\FBX\Minase.fbx",
    "WOMAN": "WOMAN", "MAN": "MAN",
}
FIT = ["TSHIRT", "TANK", "SKIRT", "TROUSERS", "JUMPSUIT", "DRESS", "JACKET", "HOODIE"]
ALL = FIT + ["PLEATED", "TIERED", "COAT", "CORSET", "UNDERBUST", "CAPE"]
jobs = []
for a, p in AV.items():
    for k in FIT:
        fa = ["--figure", p] if p in ("WOMAN", "MAN") else ["--fbx", p, "--drop", DROP]
        jobs.append({"script": "tests/test_fit.py", "args": fa + ["--only", k], "log": "logs/fit_%s_%s.txt" % (a, k)})
    for k in ALL:
        jobs.append({"script": "render.py", "args": [p, k, "logs/img/%s_%s" % (a, k), DROP], "log": "logs/render_%s_%s.txt" % (a, k)})
    if p not in ("WOMAN", "MAN"):
        for k in ("HOODIE", "CAPE", "CORSET"):
            jobs.append({"script": "tests/test_export.py", "args": [k], "env": {"CD_AVATARS": p}, "log": "logs/export_%s_%s.txt" % (a, k)})
jobs.insert(0, {"script": "tests/test_presets.py", "args": [], "log": "logs/presets.txt"})
jobs.insert(0, {"script": "tests/test_comfort.py", "args": [], "log": "logs/comfort.txt"})
jobs.insert(0, {"script": "tests/test_rig_names.py", "args": [], "log": "logs/rig_names.txt"})
print(json.dumps(jobs, ensure_ascii=False, indent=0))
