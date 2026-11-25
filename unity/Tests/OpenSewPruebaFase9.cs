// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - prueba de la Fase 9 en Unity: la ropa cosida con el código de la
// fase 9 sobre The Beast, MANUKA y Hanka, instalada y movida en Play.
//
// Tools > OpenSew > Prueba Fase 9:
//   0. si The Beast no está en el proyecto, importa Poiyomi y The Beast sin
//      diálogo y sigue cuando Unity termina de importar y recompilar;
//   1. por cada FBX de Assets/OpenSew/Fase9/ (el avatar sale del nombre:
//      TheBeast_TANK -> The Beast): escena nueva con el prefab del avatar y la
//      prenda instalada con OutfitInstaller (lilToon + Setup Outfit de Modular
//      Avatar); comprueba instalada, UVs y MA Mesh Cutter;
//   2. Play: huesos fusionados, piel quitada bajo la prenda y un paso de
//      caminar de 2 s (muslos ±30°, rodillas, brazos bajados y balanceándose):
//      la tela pegada sigue al cuerpo, ningún vértice se aleja de él, ninguno
//      sale disparado ni estira sus aristas; en el underbust, además, levanta
//      los brazos 70°;
//   3. capturas en Logs/fase9/<prenda>_*.png.
// Resultado en Logs/opensew_fase9.txt (líneas ok / FAIL y "==== Fin: N fallos").
// Usa SessionState para seguir entre recargas de dominio (importar paquetes,
// entrar y salir de Play).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OpenSew.EditorTools
{
    [InitializeOnLoad]
    static class OpenSewPruebaFase9
    {
        const string Dir = "Assets/OpenSew/Fase9";
        const string Pkgs = @"E:\assets\DOWNLOADS\The Beast 1.0";
        static readonly string PoiPkg = Path.Combine(Pkgs, "poi_Toon_7.3.50_UpTo_9.2.79.unitypackage");
        static readonly string BeastPkg = Path.Combine(Pkgs, "The Beast_1.0.unitypackage");
        // the avatar's own clothes, hidden in Play (the names Blender drops too)
        static readonly string[] Drop = ("coat,jacket,tops,pants,belt,accessories,tanktop,tsyatu,outer,hat,arm cover,gloves,"
            + "necklace,shirt,inner,skinny,neckless,outfit,manuka_costume_apron,manuka_costume_apron_nameplate,"
            + "manuka_costume_shirt,manuka_costume_shorts,manuka_costume_tie,manuka_underwear_stocking").Split(',');

        // steps: 0 idle, 2 entering Play, 3 next garment due, 4 garment in edit mode,
        // 5 importing Poiyomi, 6 importing The Beast
        const string K = "OpenSew.F9.";
        static readonly string Out = Path.Combine(Directory.GetCurrentDirectory(), "Logs");
        static readonly string LogFile = Path.Combine(Out, "opensew_fase9.txt");
        static int frames;

        static int Step { get => SessionState.GetInt(K + "Step", 0); set => SessionState.SetInt(K + "Step", value); }

        static OpenSewPruebaFase9()
        {
            EditorApplication.playModeStateChanged += OnPlay;
            int s = Step;
            if (s == 3)                       // back from Play after a domain reload
                EditorApplication.delayCall += () => EditorApplication.delayCall += Next;
            if (s == 5 || s == 6)             // recompiled after a package import
            {
                waitStart = 0;
                EditorApplication.update -= WaitImport;
                EditorApplication.update += WaitImport;
            }
        }

        static void Log(string s)
        {
            Directory.CreateDirectory(Out);
            File.AppendAllText(LogFile, DateTime.Now.ToString("HH:mm:ss ") + s + Environment.NewLine);
        }

        static void Check(bool ok, string what)
        {
            Log((ok ? "  ok   " : "  FAIL ") + what);
            if (!ok) SessionState.SetInt(K + "Fails", SessionState.GetInt(K + "Fails", 0) + 1);
        }

        static void Finish(string why)
        {
            Step = 0;
            int n = SessionState.GetInt(K + "Fails", 0);
            Log("==== Fin: " + n + " fallos (" + why + ")");
        }

        [MenuItem("Tools/OpenSew/Prueba Fase 9")]
        static void Start()
        {
            if (EditorApplication.isPlaying) { Debug.LogError("OpenSew: sal de Play antes de la prueba"); return; }
            Directory.CreateDirectory(Out);
            File.WriteAllText(LogFile, "");
            SessionState.SetInt(K + "Fails", 0);
            SessionState.SetInt(K + "Idx", -1);
            SessionState.SetInt(K + "Retry", 0);
            Log("==== Prueba Fase 9 (Unity " + Application.unityVersion + ")");
            if (AvatarSource("TheBeast") == null && Fbxs().Any(p => Who(p) == "TheBeast"))
            {
                // The Beast's package needs Poiyomi: both without the dialog
                if (!File.Exists(BeastPkg)) { Check(false, "no encuentro " + BeastPkg); }
                else
                {
                    Log("  The Beast no está en el proyecto: importo los paquetes (tarda varios minutos)");
                    bool poi = AssetDatabase.FindAssets("t:Shader Poiyomi").Length > 0 || Directory.Exists("Assets/_PoiyomiShaders");
                    if (!poi && File.Exists(PoiPkg))
                    {
                        Step = 5;
                        Log("  importando " + Path.GetFileName(PoiPkg));
                        WaitFrom(); AssetDatabase.ImportPackage(PoiPkg, false);
                    }
                    else
                    {
                        Log(poi ? "  Poiyomi ya está en el proyecto" : "  FAIL no encuentro " + PoiPkg);
                        if (!poi) SessionState.SetInt(K + "Fails", SessionState.GetInt(K + "Fails", 0) + 1);
                        Step = 6;
                        Log("  importando " + Path.GetFileName(BeastPkg));
                        WaitFrom(); AssetDatabase.ImportPackage(BeastPkg, false);
                    }
                    return;
                }
            }
            Step = 3;
            Next();
        }

        static double waitStart;
        static void WaitFrom()
        {
            waitStart = EditorApplication.timeSinceStartup;
            EditorApplication.update -= WaitImport;
            EditorApplication.update += WaitImport;
        }

        /// <summary>Waits until Unity has been quiet (no import, no compile) for
        /// 10 s, then imports the next package or goes on with the test. Runs on
        /// whether the import reloaded the domain (scripts) or not.</summary>
        static void WaitImport()
        {
            if (EditorApplication.isCompiling || EditorApplication.isUpdating || waitStart == 0)
            { waitStart = EditorApplication.timeSinceStartup; return; }
            if (EditorApplication.timeSinceStartup - waitStart < 10.0) return;
            EditorApplication.update -= WaitImport;
            try
            {
                if (Step == 5)
                {
                    Check(!EditorUtility.scriptCompilationFailed, "Poiyomi importado y compilado");
                    Step = 6;
                    Log("  importando " + Path.GetFileName(BeastPkg));
                    WaitFrom(); AssetDatabase.ImportPackage(BeastPkg, false);
                    return;
                }
                if (Step == 6)
                {
                    var p = AvatarSource("TheBeast");
                    if (p == null && SessionState.GetInt(K + "Retry", 0) < 6)
                    {
                        // the import may still be landing: look again in a while
                        SessionState.SetInt(K + "Retry", SessionState.GetInt(K + "Retry", 0) + 1);
                        WaitFrom();
                        return;
                    }
                    bool compiled = !EditorUtility.scriptCompilationFailed;
                    Check(compiled, "The Beast importado y los scripts compilan"
                                    + (compiled ? "" : " (mira la consola: sin compilar no se puede entrar en Play)"));
                    Check(p != null, "The Beast en el proyecto: " + (p ?? "ni prefab ni escena"));
                    Step = 3;
                    Next();
                }
            }
            catch (Exception e) { Log("EXCEPCION: " + e); Finish("excepción al importar"); }
        }

        static string[] Fbxs() =>
            AssetDatabase.FindAssets("t:Model", new[] { Dir })
                .Select(AssetDatabase.GUIDToAssetPath).Where(p => p.EndsWith(".fbx")).OrderBy(p => p).ToArray();

        // the avatar from the FBX's name: TheBeast_TANK -> TheBeast
        static string Who(string fbx) => Path.GetFileNameWithoutExtension(fbx).Split('_')[0];

        static string Norm(string s) => new string(s.Where(char.IsLetterOrDigit).ToArray()).ToLowerInvariant();

        static GameObject AvatarPrefab(string who)
        {
            // the prefabs used in earlier phases first, then any avatar prefab
            // whose name holds the avatar's (lilToon first, then Poiyomi: Booth
            // avatars often ship one per shader), skipping Quest/PhysBone-less copies
            var known = new Dictionary<string, string>
            {
                { "manuka", "Assets/MANUKA/Prefab/MANUKA_lilToon.prefab" },
                { "hanka", "Assets/StudioYONO/Hanka-斑霞-/Prefab/Hanka.prefab" },
            };
            string w = Norm(who);
            if (known.TryGetValue(w, out var kp))
            {
                var g = AssetDatabase.LoadAssetAtPath<GameObject>(kp);
                if (g != null) return g;
            }
            foreach (var path in AssetDatabase.FindAssets("t:Prefab").Select(AssetDatabase.GUIDToAssetPath)
                         .Where(p => p.StartsWith("Assets/") && !p.Contains("_OpenSew/") && !p.StartsWith("Assets/OpenSew"))
                         .OrderBy(p => p.IndexOf("quest", StringComparison.OrdinalIgnoreCase) >= 0 ? 1 : 0)
                         .ThenBy(p => p.IndexOf("liltoon", StringComparison.OrdinalIgnoreCase) >= 0 ? 0
                                    : p.IndexOf("poi", StringComparison.OrdinalIgnoreCase) >= 0 ? 1 : 2)
                         .ThenBy(p => p.Length))
            {
                if (Norm(Path.GetFileNameWithoutExtension(path)).IndexOf(w, StringComparison.Ordinal) < 0) continue;
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (go != null && go.GetComponents<Component>().Any(c => c != null && c.GetType().Name == "VRCAvatarDescriptor"))
                    return go;
            }
            return null;
        }

        /// <summary>Where the avatar comes from: its prefab, or else the scene it
        /// ships in (The Beast has no avatar prefab: it comes in "_OPEN ME Avatar
        /// Scene - The Beast.unity", with VRCFury components that a prefab could
        /// not even be saved with while VRCFury is missing).</summary>
        static string AvatarSource(string who)
        {
            var p = AvatarPrefab(who);
            if (p != null) return AssetDatabase.GetAssetPath(p);
            string w = Norm(who);
            return AssetDatabase.FindAssets("t:Scene").Select(AssetDatabase.GUIDToAssetPath)
                .Where(s => s.StartsWith("Assets/") && !s.StartsWith("Assets/OpenSew")
                            && Norm(Path.GetFileNameWithoutExtension(s)).Contains(w))
                .OrderBy(s => s.Length).FirstOrDefault();
        }

        /// <summary>A fresh scene with the avatar in it: the prefab in a new
        /// scene, or the avatar's own scene opened (saved later under
        /// Fase9/Escenas, so the original file is not touched).</summary>
        static GameObject PlaceAvatar(string src)
        {
            if (src.EndsWith(".prefab"))
            {
                EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
                return (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(src));
            }
            var scene = EditorSceneManager.OpenScene(src, OpenSceneMode.Single);
            var descs = scene.GetRootGameObjects().SelectMany(g => g.GetComponentsInChildren<Component>(true))
                .Where(c => c != null && c.GetType().Name == "VRCAvatarDescriptor").ToList();
            if (descs.Count > 1) Log("  la escena tiene " + descs.Count + " avatares: " + string.Join(", ", descs.Select(d => d.name)));
            var desc = descs.FirstOrDefault(d => d.gameObject.activeInHierarchy) ?? descs.FirstOrDefault();
            if (desc == null) return null;
            // only this avatar in Play: the others would be built and found too
            foreach (var d in descs) if (d != desc) d.gameObject.SetActive(false);
            desc.gameObject.SetActive(true);
            return desc.gameObject;
        }

        static void Skip()
        {
            Step = 3;
            EditorApplication.delayCall += Next;
        }

        static void Next()
        {
            if (Step != 3) return;            // already handled (reload and play event both call this)
            Step = 4;
            try
            {
                var list = Fbxs();
                int i = SessionState.GetInt(K + "Idx", -1) + 1;
                SessionState.SetInt(K + "Idx", i);
                if (list.Length == 0) { Check(false, "no hay FBX en " + Dir); Finish("sin prendas"); return; }
                if (i >= list.Length) { Finish(list.Length + " prendas"); return; }
                var path = list[i];
                string name = Path.GetFileNameWithoutExtension(path);
                Log("---- " + name);
                var src = AvatarSource(Who(path));
                Check(src != null, "avatar " + Who(path) + ": " + (src ?? "ni prefab ni escena"));
                if (src == null) { Skip(); return; }
                var avatar = PlaceAvatar(src);
                Check(avatar != null, "avatar en la escena: " + (avatar ? avatar.name : "sin VRC Avatar Descriptor"));
                if (avatar == null) { Skip(); return; }
                var scene = avatar.scene;
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                string report;
                var outfit = OutfitInstaller.Install(avatar, model, true, true, out report);
                var smr = outfit ? outfit.GetComponentsInChildren<SkinnedMeshRenderer>(true) : new SkinnedMeshRenderer[0];
                Check(smr.Length > 0, "instalada (" + report.Split('\n').Length + " líneas de informe)");
                foreach (var l in report.Split('\n')) Log("    | " + l);
                if (smr.Length == 0) { Skip(); return; }
                var mesh = smr[0].sharedMesh;
                SessionState.SetInt(K + "Verts", mesh.vertexCount);
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
                string refPath = "";
                if (cutter != null)
                {
                    var o = cutter.GetType().GetProperty("Object").GetValue(cutter);
                    refPath = (string)o.GetType().GetField("referencePath").GetValue(o);
                }
                var bodyT = refPath != "" ? avatar.transform.Find(refPath) : null;
                var bodyR = bodyT ? bodyT.GetComponent<SkinnedMeshRenderer>() : null;
                Check(bodyR != null, "el cutter apunta al cuerpo: " + refPath);
                if (bodyR == null)
                    bodyR = avatar.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                        .Where(r => r.sharedMesh && !r.transform.IsChildOf(outfit.transform))
                        .OrderByDescending(r => r.sharedMesh.vertexCount).First();
                // what Play needs to rebuild the whole body (Mesh Cutter takes the skin
                // under the garment away there): the mesh asset and its bones by path
                SessionState.SetString(K + "Body", bodyR.name);
                SessionState.SetString(K + "BodyPath", AnimationUtility.CalculateTransformPath(bodyR.transform, avatar.transform));
                SessionState.SetString(K + "BodyMesh", AssetDatabase.GetAssetPath(bodyR.sharedMesh) + "|" + bodyR.sharedMesh.name);
                SessionState.SetString(K + "BodyBones", string.Join("|", bodyR.bones.Select(b => b ? AnimationUtility.CalculateTransformPath(b, avatar.transform) : "")));
                SessionState.SetInt(K + "BodyTris", bodyR.sharedMesh.triangles.Length / 3);
                SessionState.SetString(K + "Name", name);
                AssetDatabase.SaveAssets();
                Directory.CreateDirectory(Dir + "/Escenas");
                EditorSceneManager.SaveScene(scene, Dir + "/Escenas/" + name + ".unity");
                Step = 2;
                EditorApplication.EnterPlaymode();
            }
            catch (Exception e) { Log("EXCEPCION: " + e); SessionState.SetInt(K + "Fails", SessionState.GetInt(K + "Fails", 0) + 1); Skip(); }
        }

        static void OnPlay(PlayModeStateChange st)
        {
            if (st == PlayModeStateChange.EnteredPlayMode && Step == 2)
            {
                frames = 0; phase = 0;
                EditorApplication.update -= Tick;
                EditorApplication.update += Tick;
            }
            if (st == PlayModeStateChange.EnteredEditMode && Step == 3) EditorApplication.delayCall += Next;
            // Play refused (compile errors) or left by hand: go on with the next garment
            if (st == PlayModeStateChange.EnteredEditMode && Step == 2)
            {
                Check(false, "no se pudo entrar en Play o se salió antes de tiempo");
                Step = 3; EditorApplication.delayCall += Next;
            }
        }

        // ---------------------------------------------------------------- Play

        static Transform root; static Animator anim; static SkinnedMeshRenderer cloth, bodyProxy;
        static string garment; static bool underbust;
        static int phase; static double t0, lastSample; static int snapsDone;
        static Transform[] poseBones; static Quaternion[] restLocal;
        static float downL, downR;
        static Vector3[] clothRest, bodyRest; static float[] dRest; static float restMax;
        static int[] edgeA, edgeB; static float[] edgeLen;
        // worst values over the move
        static float wTightGrowP98, wTightGrowMax, wFar, wStretchP99, wStretchMax, wMove, wBodyMove;
        static int wNaN, samples, tightCount;
        static string wFarAt, wStretchAt;

        static void Tick()
        {
            frames++;
            try
            {
                if (phase == 0)
                {
                    if (frames == 24) Prep();
                    else if (frames == 30) { Setup(); phase = cloth != null ? 1 : 9; t0 = EditorApplication.timeSinceStartup; lastSample = -1; snapsDone = 0; }
                    return;
                }
                double t = EditorApplication.timeSinceStartup - t0;
                if (phase == 1)                    // walk, 2 s: two strides
                {
                    if (t >= 2.0)
                    {
                        Pose(2.0, 0f); Sample("paso");
                        ReportMove("paso de caminar 2 s");
                        phase = underbust ? 2 : 9; t0 = EditorApplication.timeSinceStartup; lastSample = -1; snapsDone = 0;
                        ResetWorst();
                        return;
                    }
                    Pose(t, 0f);
                    if (t - lastSample >= 0.08) { Sample("paso t=" + t.ToString("0.00")); lastSample = t; }
                    if (snapsDone == 0 && t >= 0.25) { Snap("2_paso_a_lado", 90); Snap("2_paso_a_frente", 20); snapsDone = 1; }
                    if (snapsDone == 1 && t >= 0.75) { Snap("3_paso_b_lado", 90); Snap("3_paso_b_espalda", 200); snapsDone = 2; }
                }
                else if (phase == 2)               // underbust: arms up 70°, 1.2 s
                {
                    float up = 70f * Mathf.Clamp01((float)t / 0.8f);
                    if (t >= 1.2)
                    {
                        Pose(-1, 70f); Sample("brazos 70°");
                        Snap("4_brazos_arriba_frente", 0); Snap("4_brazos_arriba_lado", 90); Snap("4_brazos_arriba_espalda", 180);
                        ReportMove("levantar los brazos 70°");
                        phase = 9;
                        return;
                    }
                    Pose(-1, up);
                    if (t - lastSample >= 0.08) { Sample("brazos " + up.ToString("0") + "°"); lastSample = t; }
                }
                if (phase != 9) return;
            }
            catch (Exception e) { Log("EXCEPCION en Play: " + e); SessionState.SetInt(K + "Fails", SessionState.GetInt(K + "Fails", 0) + 1); phase = 9; }
            if (phase == 9)
            {
                EditorApplication.update -= Tick;
                if (bodyProxy) UnityEngine.Object.Destroy(bodyProxy.gameObject);
                Step = 3;
                EditorApplication.ExitPlaymode();
            }
        }

        static bool Hidden(string n)
        {
            n = n.ToLowerInvariant();
            return Drop.Contains(n);
        }

        /// <summary>The avatar's animator off, its own clothes hidden and the
        /// shrink keys its prefab set for them undone. Skinning catches up with
        /// blendshape changes only on the next frames.</summary>
        static void Prep()
        {
            var desc = UnityEngine.Object.FindObjectsOfType<Component>().FirstOrDefault(c => c != null && c.GetType().Name == "VRCAvatarDescriptor");
            if (desc == null) return;
            var a = desc.GetComponent<Animator>();
            if (a) a.enabled = false;
            int verts = SessionState.GetInt(K + "Verts", -1);
            foreach (var r in desc.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (r.sharedMesh && r.sharedMesh.vertexCount == verts) continue;
                if (Hidden(r.name)) { r.enabled = false; continue; }
                if (r.sharedMesh)
                    for (int k = 0; k < r.sharedMesh.blendShapeCount; k++)
                        if (r.sharedMesh.GetBlendShapeName(k).StartsWith("Shrink", StringComparison.OrdinalIgnoreCase))
                            r.SetBlendShapeWeight(k, 0f);
            }
        }

        static void Setup()
        {
            garment = SessionState.GetString(K + "Name", "prenda");
            underbust = garment.IndexOf("UNDERBUST", StringComparison.OrdinalIgnoreCase) >= 0;
            cloth = null; bodyProxy = null;
            var desc = UnityEngine.Object.FindObjectsOfType<Component>().FirstOrDefault(c => c != null && c.GetType().Name == "VRCAvatarDescriptor");
            Check(desc != null, "avatar en Play");
            if (desc == null) return;
            root = desc.transform; anim = root.GetComponent<Animator>();
            int verts = SessionState.GetInt(K + "Verts", -1);
            cloth = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault(r => r.sharedMesh && r.sharedMesh.vertexCount == verts);
            Check(cloth != null, "prenda presente en Play");
            if (cloth == null) return;
            Check(anim != null && anim.isHuman, "avatar humanoide (Animator con Avatar humano)");
            if (anim == null || !anim.isHuman) { cloth = null; return; }
            anim.enabled = false;
            var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
            int own = cloth.bones.Count(b => b && b.name.EndsWith("_OpenSew"));
            Check(own == 0 && cloth.bones.All(b => b && b.IsChildOf(hips)),
                  "huesos fusionados con los del avatar (" + cloth.bones.Length + ", " + own + " sin fusionar)");

            // Mesh Cutter: polygons deleted (fewer triangles) or collapsed in Play
            string bodyName = SessionState.GetString(K + "Body", "");
            var bodies = root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.name == bodyName).ToList();
            var body = bodies.FirstOrDefault(r => r.gameObject.activeInHierarchy && r.enabled) ?? bodies.FirstOrDefault();
            int before = SessionState.GetInt(K + "BodyTris", 0), after = -1, hidden = 0;
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
                UnityEngine.Object.Destroy(bm);
            }
            Check(body != null && (after < before || hidden > 0),
                  "Mesh Cutter quitó piel bajo la prenda: cuerpo " + before + " -> " + after + " triángulos, " + hidden + " ocultos");

            bodyProxy = BuildBodyProxy(body);
            Check(bodyProxy != null, "cuerpo entero (sin Mesh Cutter) para medir distancias: "
                                     + (bodyProxy ? bodyProxy.sharedMesh.vertexCount + " vértices" : "no se pudo"));
            if (bodyProxy == null) { cloth = null; return; }

            // the bones the walk moves, their rest rotations, and how far down the
            // arms go: to 60° below the horizontal from whatever the rest pose is
            var ids = new[] { HumanBodyBones.LeftUpperLeg, HumanBodyBones.RightUpperLeg, HumanBodyBones.LeftLowerLeg,
                              HumanBodyBones.RightLowerLeg, HumanBodyBones.LeftUpperArm, HumanBodyBones.RightUpperArm,
                              HumanBodyBones.LeftLowerArm, HumanBodyBones.RightLowerArm };
            poseBones = ids.Select(anim.GetBoneTransform).ToArray();
            Check(poseBones.All(b => b != null), "huesos de piernas y brazos en el Animator");
            if (poseBones.Any(b => b == null)) { cloth = null; return; }
            restLocal = poseBones.Select(b => b.localRotation).ToArray();
            downL = ArmDown(poseBones[4], poseBones[6]);
            downR = ArmDown(poseBones[5], poseBones[7]);
            Log("  brazos en reposo a " + (60f - downL).ToString("0") + "° / " + (60f - downR).ToString("0")
                + "° bajo la horizontal: se bajan " + downL.ToString("0") + "° / " + downR.ToString("0") + "° para caminar");

            // rest: cloth, body, the distance of each cloth vertex to the skin
            clothRest = BakeWorld(cloth);
            bodyRest = BakeWorld(bodyProxy);
            var grid = new Grid(bodyRest);
            dRest = clothRest.Select(p => grid.Nearest(p)).ToArray();
            restMax = dRest.Where(d => !float.IsInfinity(d)).DefaultIfEmpty(0f).Max();
            tightCount = dRest.Count(d => d <= 0.025f);
            Log("  en reposo: " + clothRest.Length + " vértices de tela, " + tightCount + " pegados al cuerpo (<= 2,5 cm), el más lejano a "
                + (restMax * 100).ToString("0.0") + " cm de la piel");
            var tri = cloth.sharedMesh.triangles; var edges = new HashSet<long>();
            for (int k = 0; k < tri.Length; k += 3)
                for (int e = 0; e < 3; e++)
                {
                    int a = tri[k + e], b = tri[k + (e + 1) % 3];
                    edges.Add(a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a);
                }
            edgeA = edges.Select(e => (int)(e >> 32)).ToArray();
            edgeB = edges.Select(e => (int)(e & 0xffffffff)).ToArray();
            edgeLen = edgeA.Select((a, k) => (clothRest[a] - clothRest[edgeB[k]]).magnitude).ToArray();
            ResetWorst();
            Snap("1_reposo_frente", 0); Snap("1_reposo_tres_cuartos", 40); Snap("1_reposo_espalda", 180);
        }

        static float ArmDown(Transform upper, Transform lower)
        {
            var d = (lower.position - upper.position).normalized;
            float below = Mathf.Asin(Mathf.Clamp(-Vector3.Dot(d, Vector3.up), -1f, 1f)) * Mathf.Rad2Deg;
            return Mathf.Clamp(60f - below, 0f, 80f);
        }

        /// <summary>A hidden copy of the avatar's body with its original mesh (the
        /// one before Mesh Cutter) on the same bones, to measure cloth-to-skin
        /// distances where the skin under the garment was taken away.</summary>
        static SkinnedMeshRenderer BuildBodyProxy(SkinnedMeshRenderer body)
        {
            var spec = SessionState.GetString(K + "BodyMesh", "").Split('|');
            if (spec.Length < 2) return null;
            var mesh = AssetDatabase.LoadAllAssetsAtPath(spec[0]).OfType<Mesh>().FirstOrDefault(m => m.name == spec[1]);
            if (mesh == null) { Log("  no encuentro la malla " + spec[1] + " en " + spec[0]); return null; }
            var paths = SessionState.GetString(K + "BodyBones", "").Split('|');
            var bones = paths.Select(p => p == "" ? null : root.Find(p)).ToArray();
            int missing = bones.Count(b => b == null);
            if (missing > 0) Log("  " + missing + " de " + bones.Length + " huesos del cuerpo no están en Play (se usa la raíz)");
            for (int i = 0; i < bones.Length; i++) if (bones[i] == null) bones[i] = root;
            var where = root.Find(SessionState.GetString(K + "BodyPath", "")) ?? (body ? body.transform : root);
            var go = new GameObject("OpenSew_CuerpoEntero");
            go.transform.SetParent(where.parent, false);
            go.transform.localPosition = where.localPosition;
            go.transform.localRotation = where.localRotation;
            go.transform.localScale = where.localScale;
            var r = go.AddComponent<SkinnedMeshRenderer>();
            r.sharedMesh = mesh;
            r.bones = bones;
            r.rootBone = body && body.rootBone ? body.rootBone : bones.FirstOrDefault();
            r.forceRenderingOff = true;      // only baked, never drawn
            // the body's shape keys as the avatar has them (shrink keys already undone)
            if (body && body.sharedMesh)
                for (int k = 0; k < mesh.blendShapeCount; k++)
                {
                    int j = body.sharedMesh.GetBlendShapeIndex(mesh.GetBlendShapeName(k));
                    if (j >= 0) r.SetBlendShapeWeight(k, body.GetBlendShapeWeight(j));
                }
            return r;
        }

        static Vector3[] BakeWorld(SkinnedMeshRenderer r)
        {
            var m = new Mesh(); r.BakeMesh(m, true);
            var tr = r.transform;
            var w = m.vertices.Select(v => tr.TransformPoint(v)).ToArray();
            UnityEngine.Object.Destroy(m);
            return w;
        }

        /// <summary>The pose at time t of the walk (t &lt; 0: no walk), with the arms
        /// raised by up degrees from the rest pose (underbust) instead of lowered.</summary>
        static void Pose(double t, float up)
        {
            for (int i = 0; i < poseBones.Length; i++) poseBones[i].localRotation = restLocal[i];
            Vector3 right = root.right, fwd = root.forward;
            if (t >= 0)
            {
                // one stride a second; s > 0: left leg forward
                float s = Mathf.Sin((float)(t * 2.0 * Math.PI));
                Turn(poseBones[0], -30f * s, right);                       // thighs ±30°
                Turn(poseBones[1], 30f * s, right);
                Turn(poseBones[2], 10f + 30f * Mathf.Max(0f, s), right);   // knees bend on the swing
                Turn(poseBones[3], 10f + 30f * Mathf.Max(0f, -s), right);
                // arms down to the side, then swinging against the legs, elbows a little bent
                poseBones[4].rotation = Quaternion.AngleAxis(20f * s, right) * Quaternion.AngleAxis(downL, fwd) * poseBones[4].rotation;
                poseBones[5].rotation = Quaternion.AngleAxis(-20f * s, right) * Quaternion.AngleAxis(-downR, fwd) * poseBones[5].rotation;
                Turn(poseBones[6], -15f, right);
                Turn(poseBones[7], -15f, right);
            }
            else if (up > 0f)
            {
                poseBones[4].rotation = Quaternion.AngleAxis(-up, fwd) * poseBones[4].rotation;
                poseBones[5].rotation = Quaternion.AngleAxis(up, fwd) * poseBones[5].rotation;
            }
        }

        static void Turn(Transform b, float deg, Vector3 axis) => b.rotation = Quaternion.AngleAxis(deg, axis) * b.rotation;

        static void ResetWorst()
        {
            wTightGrowP98 = wTightGrowMax = wFar = wMove = wBodyMove = 0f; wStretchP99 = wStretchMax = 1f;
            wNaN = 0; samples = 0; wFarAt = wStretchAt = "";
        }

        static void Sample(string when)
        {
            var c = BakeWorld(cloth);
            var b = BakeWorld(bodyProxy);
            samples++;
            int nan = c.Count(p => float.IsNaN(p.x) || float.IsNaN(p.y) || float.IsNaN(p.z) || float.IsInfinity(p.x) || float.IsInfinity(p.y) || float.IsInfinity(p.z));
            wNaN = Math.Max(wNaN, nan);
            var grid = new Grid(b);
            var grow = new List<float>(tightCount);
            float far = 0f, move = 0f, bmove = 0f;
            for (int i = 0; i < c.Length; i++)
            {
                float d = grid.Nearest(c[i]);
                if (d > far) far = d;
                if (dRest[i] <= 0.025f) grow.Add(d - dRest[i]);
                move = Mathf.Max(move, (c[i] - clothRest[i]).magnitude);
            }
            for (int i = 0; i < b.Length; i++) bmove = Mathf.Max(bmove, (b[i] - bodyRest[i]).magnitude);
            if (grow.Count > 0)
            {
                grow.Sort();
                wTightGrowP98 = Mathf.Max(wTightGrowP98, grow[(int)(0.98f * (grow.Count - 1))]);
                wTightGrowMax = Mathf.Max(wTightGrowMax, grow[grow.Count - 1]);
            }
            if (far > wFar) { wFar = far; wFarAt = when; }
            var st = new float[edgeA.Length];
            for (int k = 0; k < st.Length; k++)
                st[k] = edgeLen[k] > 1e-5f ? (c[edgeA[k]] - c[edgeB[k]]).magnitude / edgeLen[k] : 1f;
            Array.Sort(st);
            if (st.Length > 0)
            {
                wStretchP99 = Mathf.Max(wStretchP99, st[(int)(0.99f * (st.Length - 1))]);
                if (st[st.Length - 1] > wStretchMax) { wStretchMax = st[st.Length - 1]; wStretchAt = when; }
            }
            wMove = Mathf.Max(wMove, move); wBodyMove = Mathf.Max(wBodyMove, bmove);
        }

        static string Cm(float m) => (m * 100f).ToString("0.0") + " cm";

        static void ReportMove(string what)
        {
            Log("  -- " + what + " (" + samples + " muestras)");
            Check(wNaN == 0, "sin vértices NaN/infinito (" + wNaN + ")");
            Check(wBodyMove > 0.05f, "el esqueleto se mueve (cuerpo hasta " + Cm(wBodyMove) + ", prenda hasta " + Cm(wMove) + ")");
            // tight cloth follows the skin under it
            if (tightCount >= 20)
                Check(wTightGrowP98 <= 0.03f && wTightGrowMax <= 0.10f,
                      "la tela pegada sigue al cuerpo: " + tightCount + " vértices, se separan hasta " + Cm(wTightGrowP98)
                      + " (p98) y " + Cm(wTightGrowMax) + " (máx); límites 3 y 10 cm");
            else Log("  --   menos de 20 vértices pegados al cuerpo: sin prueba de seguir a la piel");
            // nothing flies off
            float lim = Mathf.Max(0.20f, restMax + 0.10f);
            Check(wFar <= lim, "ningún vértice lejos del cuerpo: el más lejano a " + Cm(wFar) + " (" + wFarAt + "), límite " + Cm(lim)
                               + " (reposo " + Cm(restMax) + " + 10 cm, mínimo 20)");
            Check(wMove <= wBodyMove + 0.05f, "ningún vértice sale disparado: la prenda se mueve hasta " + Cm(wMove)
                                              + ", el cuerpo hasta " + Cm(wBodyMove) + " (+5 cm)");
            Check(wStretchMax <= 3.0f && wStretchP99 <= 1.6f,
                  "aristas sin estirarse de más: p99 " + wStretchP99.ToString("0.00") + "x, máx " + wStretchMax.ToString("0.00")
                  + "x (" + wStretchAt + "); límites 1,6x y 3x");
        }

        /// <summary>Uniform grid over the body's vertices for nearest-vertex
        /// distances (5 cm cells, searched outwards ring by ring).</summary>
        class Grid
        {
            const float Cell = 0.05f;
            readonly Dictionary<long, List<Vector3>> cells = new Dictionary<long, List<Vector3>>();
            static long Key(int x, int y, int z) => ((long)(x + 4096) << 26) | ((long)(y + 4096) << 13) | (long)(z + 4096);
            static int C(float v) => Mathf.FloorToInt(v / Cell);

            public Grid(Vector3[] pts)
            {
                foreach (var p in pts)
                {
                    if (float.IsNaN(p.x) || float.IsInfinity(p.x) || float.IsNaN(p.y) || float.IsNaN(p.z)) continue;
                    long k = Key(C(p.x), C(p.y), C(p.z));
                    if (!cells.TryGetValue(k, out var l)) cells[k] = l = new List<Vector3>();
                    l.Add(p);
                }
            }

            public float Nearest(Vector3 p)
            {
                if (float.IsNaN(p.x) || float.IsInfinity(p.x)) return float.PositiveInfinity;
                int cx = C(p.x), cy = C(p.y), cz = C(p.z);
                float bestSq = float.PositiveInfinity;
                for (int r = 0; r <= 40; r++)
                {
                    // a cell r rings away is at least (r - 1) cells from p
                    float near = Mathf.Max(0, r - 1) * Cell;
                    if (bestSq <= near * near) break;
                    // only the shell of the cube of rings r
                    for (int x = -r; x <= r; x++)
                    for (int y = -r; y <= r; y++)
                    {
                        bool side = Math.Abs(x) == r || Math.Abs(y) == r;
                        for (int z = -r; z <= r; z += side ? 1 : Math.Max(1, 2 * r))
                        {
                            if (!cells.TryGetValue(Key(cx + x, cy + y, cz + z), out var l)) continue;
                            foreach (var q in l) { float d = (q - p).sqrMagnitude; if (d < bestSq) bestSq = d; }
                        }
                    }
                }
                return Mathf.Sqrt(bestSq);
            }
        }

        static void Snap(string tag, float yaw)
        {
            var dir = Path.Combine(Out, "fase9"); Directory.CreateDirectory(dir);
            var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var center = Vector3.Lerp(hips.position, head.position, 0.25f);
            center.y = Mathf.Lerp(root.position.y, head.position.y + 0.15f, 0.5f);
            float h = head.position.y - root.position.y + 0.30f;
            var go = new GameObject("OpenSewCam9"); var cam = go.AddComponent<Camera>();
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
