// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - prueba de la Fase 7 en Unity: el cuerpo de Hanka oculto bajo la prenda (MA Mesh Cutter).
//
// Tools > OpenSew > Prueba Fase 7: por cada FBX de Assets/OpenSew/Fase7/,
//   1. escena nueva con el avatar (prefab de Hanka) y la prenda instalada con
//      OutfitInstaller (lilToon + Setup Outfit de Modular Avatar),
//   2. Play: la prenda tiene que usar los huesos del avatar y moverse con
//      ellos (capucha con la cabeza, mangas con el brazo, faldas con el muslo),
//   3. capturas en Logs/fase7/<prenda>_*.png.
// Resultado en Logs/opensew_fase7.txt. Usa SessionState para seguir entre
// recargas de dominio al entrar y salir de Play.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OpenSew.EditorTools
{
    [InitializeOnLoad]
    static class OpenSewPruebaFase7
    {
        const string Dir = "Assets/OpenSew/Fase7";
        const string KIdx = "OpenSew.F7.Idx", KStep = "OpenSew.F7.Step", KVerts = "OpenSew.F7.Verts";
        static readonly string Out = Path.Combine(Directory.GetCurrentDirectory(), "Logs");
        static int frames;

        static OpenSewPruebaFase7()
        {
            EditorApplication.playModeStateChanged += OnPlay;
            if (SessionState.GetInt(KStep, 0) == 3)      // volvió de Play: siguiente prenda
                EditorApplication.delayCall += () => EditorApplication.delayCall += Next;
            if (SessionState.GetInt(KStep, 0) == 5)      // recompilado tras importar las herramientas
                EditorApplication.delayCall += () => EditorApplication.delayCall += AfterImport;
        }

        // the tools package built by tools/build_unitypackage.py, imported without
        // the dialog: tests the package itself and updates the scripts in place
        static readonly string ToolsPkg = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads", "OpenSew_Unity_Tools-1.1.0.unitypackage");

        static Type PackagerType() =>
            AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("OpenSew.EditorTools.OpenSewPackager")).FirstOrDefault(t => t != null);

        static object Pk(string method, params object[] args)
        {
            var t = PackagerType();
            var m = t.GetMethods().First(x => x.Name == method && x.GetParameters().Length == args.Length);
            return m.Invoke(null, args);
        }

        static double waitStart;
        static void WaitImport()
        {
            if (EditorApplication.isCompiling || EditorApplication.isUpdating) { waitStart = EditorApplication.timeSinceStartup; return; }
            if (EditorApplication.timeSinceStartup - waitStart < 8.0) return;
            EditorApplication.update -= WaitImport;
            if (SessionState.GetInt(KStep, 0) == 5) AfterImport();
        }

        static void AfterImport()
        {
            Check(PackagerType() != null, "paquete de herramientas importado: menú Empaquetar para vender disponible");
            Check(File.Exists("Assets/OpenSew/Editor/OpenSewPackager.cs.meta")
                  && File.ReadAllText("Assets/OpenSew/Editor/OpenSewPackager.cs.meta").Contains("39f9bf3c6f39593db80609e584e01d82"),
                  "el empaquetador conserva su GUID");
            Check(Directory.GetFiles("Assets/OpenSew/Editor", "OpenSewOutfitInstaller*.cs").Length == 1,
                  "el instalador se actualizó en su sitio, sin duplicarse");
            SessionState.SetInt(KStep, 3);
            Next();
        }

        [MenuItem("Tools/OpenSew/Prueba Fase 7")]
        static void Start()
        {
            File.WriteAllText(Path.Combine(Out, "opensew_fase7.txt"), "");
            Log("==== Prueba Fase 7 (Unity " + Application.unityVersion + ")");
            SessionState.SetInt(KIdx, -1);
            SessionState.SetInt(KStep, 3);
            Next();
        }

        static string[] Fbxs() =>
            AssetDatabase.FindAssets("t:Model", new[] { Dir })
                .Select(AssetDatabase.GUIDToAssetPath).Where(p => p.EndsWith(".fbx")).OrderBy(p => p).ToArray();

        static void Log(string s)
        {
            Directory.CreateDirectory(Out);
            File.AppendAllText(Path.Combine(Out, "opensew_fase7.txt"), DateTime.Now.ToString("HH:mm:ss ") + s + Environment.NewLine);
        }
        static void Check(bool ok, string what) => Log((ok ? "  ok   " : "  FALLO ") + what);

        static GameObject AvatarPrefab()
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Prefab"))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (!path.StartsWith("Assets/") || path.Contains("_OpenSew/") || path.StartsWith("Assets/OpenSew")) continue;
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (go != null && go.name.IndexOf("hanka", StringComparison.OrdinalIgnoreCase) >= 0
                    && go.GetComponents<Component>().Any(c => c != null && c.GetType().Name == "VRCAvatarDescriptor"))
                    return go;
            }
            return null;
        }

        static void Next()
        {
            try
            {
                var list = Fbxs();
                int i = SessionState.GetInt(KIdx, -1) + 1;
                SessionState.SetInt(KIdx, i);
                if (i >= list.Length) { SessionState.SetInt(KStep, 0); Log("==== Fin (" + list.Length + " prendas)"); return; }
                var path = list[i];
                Log("---- " + Path.GetFileNameWithoutExtension(path));
                var prefab = AvatarPrefab();
                if (prefab == null) { Log("FALLO: no hay prefab de Hanka"); SessionState.SetInt(KStep, 0); return; }
                var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
                var avatar = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                string report;
                var outfit = OutfitInstaller.Install(avatar, model, true, true, out report);
                var smr = outfit.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                Check(smr.Length > 0, "instalada (" + report.Split('\n').Length + " líneas de informe)");
                if (smr.Length == 0) { SessionState.SetInt(KStep, 3); EditorApplication.delayCall += Next; return; }
                SessionState.SetInt(KVerts, smr[0].sharedMesh.vertexCount);
                var mesh = smr[0].sharedMesh;
                var uv = mesh.uv;
                bool uvOk = uv.Length == mesh.vertexCount && uv.All(u => u.x >= 0f && u.x <= 1f && u.y >= 0f && u.y <= 1f);
                Check(uvOk, "UVs en uv0 dentro de 0..1 (" + uv.Length + " de " + mesh.vertexCount + ")");
                Check(mesh.uv2 != null && mesh.uv2.Length == mesh.vertexCount, "segundo mapa UV (Fabric) presente");
                int tris = mesh.triangles.Length / 3;
                Check(tris <= 20000, "triángulos: " + tris);
                var cutGo = outfit.transform.Find("OpenSew_OcultarCuerpo");
                var cutter = cutGo ? cutGo.GetComponents<Component>().FirstOrDefault(c => c != null && c.GetType().Name == "ModularAvatarMeshCutter") : null;
                int filters = cutGo ? cutGo.GetComponents<Component>().Count(c => c != null && c.GetType().Name == "VertexFilterByMaskComponent") : 0;
                Check(cutter != null && filters > 0, "MA Mesh Cutter con " + filters + " máscara(s) en la prenda");
                var line = report.Split('\n').FirstOrDefault(l => l.Contains("Mesh Cutter") || l.Contains("máscara"));
                Log("  " + line);
                // the body the installer pointed the cutter at
                string refPath = "";
                if (cutter != null)
                {
                    var o = cutter.GetType().GetProperty("Object").GetValue(cutter);
                    refPath = (string)o.GetType().GetField("referencePath").GetValue(o);
                }
                var bodyT = avatar.transform.Find(refPath);
                var bodyR = bodyT ? bodyT.GetComponent<SkinnedMeshRenderer>() : null;
                Check(bodyR != null, "el cutter apunta al cuerpo: " + refPath);
                if (bodyR == null) bodyR = avatar.GetComponentsInChildren<SkinnedMeshRenderer>(true).First();
                SessionState.SetString("OpenSew.F7.Body", bodyR.name);
                SessionState.SetInt("OpenSew.F7.BodyTris", bodyR.sharedMesh.triangles.Length / 3);
                AssetDatabase.SaveAssets();
                // the sale package from the installed prefab
                var prefabAsset = PrefabUtility.GetCorrespondingObjectFromSource(outfit);
                string prefabPath = AssetDatabase.GetAssetPath(prefabAsset);
                var pkgDir = Path.Combine(Out, "fase7"); Directory.CreateDirectory(pkgDir);
                var pkg = Path.Combine(pkgDir, Path.GetFileNameWithoutExtension(path) + ".unitypackage");
                string pr;
                var pargs = new object[] { prefabAsset, Path.GetFileNameWithoutExtension(path), "OpenSew test", "Hanka", pkg, null };
                bool okPkg = (bool)Pk("Export", pargs);
                pr = (string)pargs[5];
                var files = (System.Collections.Generic.List<string>)Pk("Contents", prefabAsset);
                var missing = (System.Collections.Generic.List<string>)Pk("MissingRequirements", prefabAsset);
                Check(okPkg && new FileInfo(pkg).Length > 10000, "paquete para vender (" + new FileInfo(pkg).Length / 1024 + " KB, prefab " + prefabPath + ")");
                Check(files.Any(f => f.EndsWith(".fbx")) && files.Any(f => f.EndsWith(".mat")) && files.Any(f => f.EndsWith(".prefab"))
                      && files.Any(f => f.Contains("_mask_")), "el paquete lleva FBX, material, prefab y máscara (" + files.Count + " archivos)");
                Check(missing.Count == 0, "sin avisos para el comprador: " + string.Join("; ", missing));
                Log("  " + pr.Replace("\n", " | "));
                SessionState.SetString("OpenSew.F7.Name", Path.GetFileNameWithoutExtension(path));
                Directory.CreateDirectory("Assets/OpenSew/Fase7/Escenas");
                EditorSceneManager.SaveScene(scene, "Assets/OpenSew/Fase7/Escenas/" + Path.GetFileNameWithoutExtension(path) + ".unity");
                SessionState.SetInt(KStep, 2);
                EditorApplication.EnterPlaymode();
            }
            catch (Exception e) { Log("EXCEPCION: " + e); SessionState.SetInt(KStep, 0); }
        }

        static void OnPlay(PlayModeStateChange st)
        {
            int step = SessionState.GetInt(KStep, 0);
            if (st == PlayModeStateChange.EnteredPlayMode && step == 2) { frames = 0; EditorApplication.update += Tick; }
            if (st == PlayModeStateChange.EnteredEditMode && step == 3) EditorApplication.delayCall += Next;
        }

        static void Tick()
        {
            frames++;
            try
            {
                if (frames == 30) Phase(false);
                else if (frames == 36) Phase(true);
                else return;
            }
            catch (Exception e) { Log("EXCEPCION en Play: " + e); frames = 36; }
            if (frames >= 36)
            {
                EditorApplication.update -= Tick;
                SessionState.SetInt(KStep, 3);
                EditorApplication.ExitPlaymode();
            }
        }

        static Transform root; static Animator anim; static SkinnedMeshRenderer cloth;
        static Vector3[] rest; static Transform moved; static Quaternion movedRot; static string movedWhat;

        static void Phase(bool posed)
        {
            string name = SessionState.GetString("OpenSew.F7.Name", "prenda");
            if (!posed)
            {
                var desc = UnityEngine.Object.FindObjectsOfType<Component>().First(c => c.GetType().Name == "VRCAvatarDescriptor");
                root = desc.transform; anim = root.GetComponent<Animator>();
                int verts = SessionState.GetInt(KVerts, -1);
                cloth = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault(r => r.sharedMesh && r.sharedMesh.vertexCount == verts);
                Check(cloth != null, "prenda presente en Play");
                if (cloth == null) return;
                var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
                int own = cloth.bones.Count(b => b && b.name.EndsWith("_OpenSew"));
                Check(own == 0 && cloth.bones.All(b => b && b.IsChildOf(hips)),
                      "huesos fusionados con los del avatar (" + cloth.bones.Length + ", " + own + " sin fusionar)");
                // ocultar la ropa original del avatar para las capturas
                var keep = new[] { "body", "face", "head", "hair", "kemo", "eye" };
                foreach (var r in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (r != cloth && !keep.Any(k => r.name.IndexOf(k, StringComparison.OrdinalIgnoreCase) >= 0)) r.enabled = false;
                var bodies = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.name == SessionState.GetString("OpenSew.F7.Body", "")).ToList();
                foreach (var r in bodies) Log("  cuerpo en Play: " + r.name + " activo=" + r.gameObject.activeInHierarchy + "/" + r.enabled
                                              + " malla=" + (r.sharedMesh ? r.sharedMesh.name + " " + r.sharedMesh.triangles.Length / 3 + " tris, " + r.sharedMesh.blendShapeCount + " shapes" : "-"));
                var body = bodies.FirstOrDefault(r => r.gameObject.activeInHierarchy && r.enabled) ?? bodies.FirstOrDefault();
                int before = SessionState.GetInt("OpenSew.F7.BodyTris", 0);
                // Mesh Cutter either deletes the polygons (fewer triangles) or, in
                // Play, hides them by collapsing their vertices: count both
                int after = -1, hidden = 0;
                if (body && body.sharedMesh)
                {
                    var bm = new Mesh(); body.BakeMesh(bm, true);
                    var v = bm.vertices; var t = bm.triangles; after = t.Length / 3;
                    for (int k = 0; k < t.Length; k += 3)
                    {
                        Vector3 a = v[t[k]], b = v[t[k + 1]], c = v[t[k + 2]];
                        float area = Vector3.Cross(b - a, c - a).magnitude;
                        if (float.IsNaN(area) || float.IsInfinity(area) || area < 1e-12f) hidden++;
                    }
                }
                Check(body != null && (after < before || hidden > 0),
                      "Mesh Cutter quitó piel bajo la prenda: cuerpo " + before + " -> " + after + " triángulos, " + hidden + " ocultos");
                Snap(name, "1_frente", 0); Snap(name, "2_tres_cuartos", 40); Snap(name, "3_espalda", 180);
                cloth.enabled = false;
                Snap(name, "6_cuerpo_sin_prenda_frente", 0); Snap(name, "7_cuerpo_sin_prenda_espalda", 180);
                cloth.enabled = true;
                // qué mover según la prenda: cabeza si llega por encima del cuello,
                // brazo si tiene mangas, muslo si baja de la cadera
                var b0 = new Mesh(); cloth.BakeMesh(b0, true);
                var w = b0.vertices.Select(v => cloth.transform.TransformPoint(v)).ToArray();
                rest = w;
                var head = anim.GetBoneTransform(HumanBodyBones.Head);
                var arm = anim.GetBoneTransform(HumanBodyBones.LeftUpperArm);
                var thigh = anim.GetBoneTransform(HumanBodyBones.LeftUpperLeg);
                bool hood = w.Any(p => p.y > head.position.y + 0.05f);
                bool sleeve = w.Any(p => Vector3.Distance(p, anim.GetBoneTransform(HumanBodyBones.LeftLowerArm).position) < 0.06f);
                bool skirt = w.Any(p => p.y < thigh.position.y - 0.08f);
                anim.enabled = false;
                if (hood) { moved = head; movedWhat = "girar la cabeza 30° mueve la capucha"; moved.localRotation = Quaternion.AngleAxis(30f, Vector3.up) * moved.localRotation; }
                else if (sleeve) { moved = arm; movedWhat = "bajar el brazo 50° mueve la manga"; moved.rotation = Quaternion.AngleAxis(50f, root.forward) * moved.rotation; }
                else if (skirt) { moved = thigh; movedWhat = "levantar el muslo 40° mueve la falda"; moved.rotation = Quaternion.AngleAxis(-40f, root.right) * moved.rotation; }
                else { moved = anim.GetBoneTransform(HumanBodyBones.Spine); movedWhat = "inclinar la columna 25° mueve la prenda"; moved.rotation = Quaternion.AngleAxis(25f, root.right) * moved.rotation; }
            }
            else
            {
                if (cloth == null) return;
                var b1 = new Mesh(); cloth.BakeMesh(b1, true);
                var w = b1.vertices.Select(v => cloth.transform.TransformPoint(v)).ToArray();
                int n = 0; float mx = 0;
                for (int i = 0; i < w.Length; i++) { float d = (w[i] - rest[i]).magnitude; if (d > 0.01f) n++; mx = Mathf.Max(mx, d); }
                Check(n > w.Length / 20, movedWhat + " (" + n + " de " + w.Length + " verts, máx " + mx.ToString("0.000") + " m)");
                Snap(name, "4_pose_frente", 0); Snap(name, "5_pose_tres_cuartos", 40);
            }
        }

        static void Snap(string garment, string tag, float yaw)
        {
            var dir = Path.Combine(Out, "fase7"); Directory.CreateDirectory(dir);
            var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var center = Vector3.Lerp(hips.position, head.position, 0.40f);
            float h = head.position.y - root.position.y + 0.25f;
            var go = new GameObject("OpenSewCam7"); var cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.32f, 0.33f, 0.36f); cam.fieldOfView = 30f;
            var rt = new RenderTexture(768, 1152, 24); cam.targetTexture = rt;
            float dist = h * 0.5f / Mathf.Tan(15f * Mathf.Deg2Rad) * 1.15f;
            go.transform.position = center + Quaternion.AngleAxis(yaw, Vector3.up) * root.forward * dist;
            go.transform.LookAt(center);
            cam.Render(); RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); tex.Apply(); RenderTexture.active = null;
            File.WriteAllBytes(Path.Combine(dir, garment + "_" + tag + ".png"), tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex); UnityEngine.Object.DestroyImmediate(go); rt.Release();
        }
    }
}
