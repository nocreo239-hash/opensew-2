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

        static GameObject AvatarPrefab(string who)
        {
            // the lilToon prefab first: Booth avatars often ship one per shader
            foreach (var path in AssetDatabase.FindAssets("t:Prefab").Select(AssetDatabase.GUIDToAssetPath)
                         .OrderBy(p => p.IndexOf("liltoon", StringComparison.OrdinalIgnoreCase) >= 0 ? 0 : 1))
            {
                if (!path.StartsWith("Assets/") || path.Contains("_OpenSew/") || path.StartsWith("Assets/OpenSew")) continue;
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (go != null && go.name.IndexOf(who, StringComparison.OrdinalIgnoreCase) >= 0
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
                // the avatar from the FBX's name: Hanka_HOODIE -> Hanka
                var who = Path.GetFileNameWithoutExtension(path).Split('_')[0];
                var prefab = AvatarPrefab(who);
                if (prefab == null) { Log("FALLO: no hay prefab de " + who); SessionState.SetInt(KStep, 3); EditorApplication.delayCall += Next; return; }
                Log("  avatar: " + AssetDatabase.GetAssetPath(prefab));
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
                var colors = outfit.transform.Find("OpenSew_Colores");
                int setters = colors ? colors.GetComponentsInChildren<Component>(true).Count(c => c != null && c.GetType().Name == "ModularAvatarMaterialSetter") : 0;
                int items = colors ? colors.GetComponentsInChildren<Component>(true).Count(c => c != null && c.GetType().Name == "ModularAvatarMenuItem") : 0;
                Check(colors != null && setters == OutfitInstaller.Palette.Length && items == setters + 2,
                      "menú de colores: " + items + " entradas, " + setters + " Material Setter");
                Log("  " + report.Split('\n').FirstOrDefault(l => l.StartsWith("Menú de colores")));
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
                if (frames == 24) Prep();
                else if (frames == 30) Phase(false);
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

        /// <summary>Frames before the captures: the avatar's animator off, its own
        /// clothes hidden and the shrink keys its prefab set for them undone.
        /// Skinning catches up with blendshape changes only on the next frames.</summary>
        static void Prep()
        {
            var desc = UnityEngine.Object.FindObjectsOfType<Component>().FirstOrDefault(c => c.GetType().Name == "VRCAvatarDescriptor");
            if (desc == null) return;
            var a = desc.GetComponent<Animator>();
            if (a) a.enabled = false;
            int verts = SessionState.GetInt(KVerts, -1);
            var keep = new[] { "body", "face", "head", "hair", "kemo", "eye", "underwear_bra", "underwear_panty", "pants" };
            foreach (var r in desc.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (r.sharedMesh && r.sharedMesh.vertexCount == verts) continue;
                if (!keep.Any(k => r.name.IndexOf(k, StringComparison.OrdinalIgnoreCase) >= 0)) { r.enabled = false; continue; }
                if (r.sharedMesh)
                    for (int k = 0; k < r.sharedMesh.blendShapeCount; k++)
                        if (r.sharedMesh.GetBlendShapeName(k).StartsWith("Shrink", StringComparison.OrdinalIgnoreCase))
                            r.SetBlendShapeWeight(k, 0f);
            }
        }

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
                var keep = new[] { "body", "face", "head", "hair", "kemo", "eye", "underwear_bra", "underwear_panty", "pants" };
                foreach (var r in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (r != cloth && !keep.Any(k => r.name.IndexOf(k, StringComparison.OrdinalIgnoreCase) >= 0)) r.enabled = false;
                // the avatar's own animator sets its shrink keys every frame: stop it first
                anim.enabled = false;
                // with the avatar's own clothes off, undo the shrink keys its prefab set
                // for them (Manuka's legs are shrunk under her stockings)
                foreach (var r in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (r != cloth && r.enabled && r.sharedMesh)
                        for (int k = 0; k < r.sharedMesh.blendShapeCount; k++)
                            if (r.sharedMesh.GetBlendShapeName(k).StartsWith("Shrink", StringComparison.OrdinalIgnoreCase))
                                r.SetBlendShapeWeight(k, 0f);
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
                CheckColorMenu(desc, name);
                Snap(name, "1_frente", 0); Snap(name, "2_tres_cuartos", 40); Snap(name, "3_espalda", 180);
                cloth.enabled = false;
                Snap(name, "6_cuerpo_sin_prenda_frente", 0); Snap(name, "7_cuerpo_sin_prenda_espalda", 180);
                cloth.enabled = true;
                // what each colour looks like (the material the menu would set)
                var orig = cloth.sharedMaterial;
                foreach (var (cname, _) in OutfitInstaller.Palette)
                {
                    var m = AssetDatabase.FindAssets(orig.name.Replace("(Clone)", "").Trim() + "_" + cname + " t:Material")
                        .Select(AssetDatabase.GUIDToAssetPath).Select(AssetDatabase.LoadAssetAtPath<Material>).FirstOrDefault();
                    if (m == null) continue;
                    cloth.sharedMaterial = m;
                    Snap(name, "8_color_" + cname.Replace(" ", "_"), 30);
                }
                cloth.sharedMaterial = orig;
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

        static void CheckColorMenu(Component desc, string garment)
        {
            // after the build Modular Avatar ran on Play: the FX layer must hold
            // animations that set the garment's material, and the parameter must exist
            var layers = desc.GetType().GetField("baseAnimationLayers").GetValue(desc) as Array;
            UnityEditor.Animations.AnimatorController fx = null;
            foreach (var l in layers)
            {
                var type = l.GetType().GetField("type").GetValue(l).ToString();
                if (type == "FX") fx = l.GetType().GetField("animatorController").GetValue(l) as UnityEditor.Animations.AnimatorController;
            }
            int matCurves = 0; var mats = new System.Collections.Generic.HashSet<string>();
            if (fx != null)
                foreach (var clip in fx.animationClips)
                foreach (var b in AnimationUtility.GetObjectReferenceCurveBindings(clip))
                    if (b.propertyName.Contains("m_Materials"))
                    {
                        matCurves++;
                        foreach (var k in AnimationUtility.GetObjectReferenceCurve(clip, b)) if (k.value) mats.Add(k.value.name);
                    }
            int found = OutfitInstaller.Palette.Count(p => mats.Any(m => m.EndsWith("_" + p.name)));
            Check(fx != null && found == OutfitInstaller.Palette.Length,
                  "FX de VRChat cambia el material: " + matCurves + " curvas, " + found + " de " + OutfitInstaller.Palette.Length + " colores");
            var expr = desc.GetType().GetField("expressionParameters").GetValue(desc);
            var ps = expr?.GetType().GetField("parameters").GetValue(expr) as Array;
            string param = "OpenSew/" + garment + "/Color";
            bool has = false; string kind = "";
            if (ps != null) foreach (var p in ps)
            {
                if ((string)p.GetType().GetField("name").GetValue(p) != param) continue;
                has = true;
                kind = p.GetType().GetField("valueType").GetValue(p) + ", saved=" + p.GetType().GetField("saved").GetValue(p)
                       + ", synced=" + p.GetType().GetField("networkSynced").GetValue(p);
            }
            Check(has, "parámetro del menú en VRChat: " + param + " (" + kind + ")");
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
