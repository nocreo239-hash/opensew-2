// OpenSew - prueba de las prendas de la Fase 4 en Unity (proyecto de prueba).
//
// Tools > OpenSew > Prueba Fase 4: por cada FBX de Assets/OpenSew/Fase4/,
//   1. escena nueva con el avatar (prefab de Hanka) y la prenda instalada con
//      OutfitInstaller (lilToon + Setup Outfit de Modular Avatar),
//   2. Play: la prenda tiene que usar los huesos del avatar y moverse con
//      ellos (capucha con la cabeza, mangas con el brazo, faldas con el muslo),
//   3. capturas en Logs/fase4/<prenda>_*.png.
// Resultado en Logs/opensew_fase4.txt. Usa SessionState para seguir entre
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
    static class OpenSewPruebaFase4
    {
        const string Dir = "Assets/OpenSew/Fase4";
        const string KIdx = "OpenSew.F4.Idx", KStep = "OpenSew.F4.Step", KVerts = "OpenSew.F4.Verts";
        static readonly string Out = Path.Combine(Directory.GetCurrentDirectory(), "Logs");
        static int frames;

        static OpenSewPruebaFase4()
        {
            EditorApplication.playModeStateChanged += OnPlay;
            if (SessionState.GetInt(KStep, 0) == 3)      // volvió de Play: siguiente prenda
                EditorApplication.delayCall += () => EditorApplication.delayCall += Next;
        }

        [MenuItem("Tools/OpenSew/Prueba Fase 4")]
        static void Start()
        {
            File.WriteAllText(Path.Combine(Out, "opensew_fase4.txt"), "");
            Log("==== Prueba Fase 4 (Unity " + Application.unityVersion + ")");
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
            File.AppendAllText(Path.Combine(Out, "opensew_fase4.txt"), DateTime.Now.ToString("HH:mm:ss ") + s + Environment.NewLine);
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
                SessionState.SetString("OpenSew.F4.Name", Path.GetFileNameWithoutExtension(path));
                Directory.CreateDirectory("Assets/OpenSew/Fase4/Escenas");
                EditorSceneManager.SaveScene(scene, "Assets/OpenSew/Fase4/Escenas/" + Path.GetFileNameWithoutExtension(path) + ".unity");
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
            string name = SessionState.GetString("OpenSew.F4.Name", "prenda");
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
                Snap(name, "1_frente", 0); Snap(name, "2_tres_cuartos", 40); Snap(name, "3_espalda", 180);
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
            var dir = Path.Combine(Out, "fase4"); Directory.CreateDirectory(dir);
            var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var center = Vector3.Lerp(hips.position, head.position, 0.40f);
            float h = head.position.y - root.position.y + 0.25f;
            var go = new GameObject("OpenSewCam4"); var cam = go.AddComponent<Camera>();
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
