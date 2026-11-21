// OpenSew - prueba automática de la Fase 3 (solo para el proyecto OpenSew_Prueba).
//
// Tools > OpenSew > Prueba Fase 3 (también arranca sola una vez por sesión).
//   1. Importa el unitypackage de Hanka si no hay un prefab de avatar.
//   2. Pone el avatar en la escena e instala Hanka_Jacket_OpenSew.fbx con
//      OutfitInstaller (lilToon + Setup Outfit de Modular Avatar).
//   3. Entra en Play (Modular Avatar/NDMF procesan el avatar) y comprueba que
//      la chaqueta usa los huesos del avatar y que la manga sigue al brazo.
// Todo queda en Logs/opensew_fase3.txt.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OpenSew.EditorTools
{
    [InitializeOnLoad]
    static class OpenSewPruebaFase3
    {
        const string HankaPackage = @"E:\assets\DOWNLOADS\Hanka\斑霞-Hanka-Ver1.2\斑霞-Hanka-Ver1.2\斑霞-Hanka-Ver1.2.unitypackage";
        const string JacketPath = "Assets/OpenSew/Hanka_Jacket_OpenSew.fbx";
        const string StepKey = "OpenSew.Fase3.Step";
        static readonly string LogPath = Path.Combine(Directory.GetCurrentDirectory(), "Logs", "opensew_fase3.txt");

        static OpenSewPruebaFase3()
        {
            Application.logMessageReceived += OnLog;
            EditorApplication.playModeStateChanged += OnPlayMode;
            if (!SessionState.GetBool("OpenSew.Fase3.Started", false))
            {
                SessionState.SetBool("OpenSew.Fase3.Started", true);
                SessionState.SetInt(StepKey, 0);
                EditorApplication.delayCall += () => EditorApplication.delayCall += Run;
            }
            else if (SessionState.GetInt(StepKey, -1) == 1)
                EditorApplication.delayCall += () => EditorApplication.delayCall += Run;
        }

        [MenuItem("Tools/OpenSew/Prueba Fase 3")]
        static void Menu() { SessionState.SetInt(StepKey, 0); Run(); }

        static void Log(string s)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(LogPath));
            File.AppendAllText(LogPath, DateTime.Now.ToString("HH:mm:ss ") + s + Environment.NewLine);
        }

        static void OnLog(string msg, string stack, LogType type)
        {
            if (type == LogType.Error || type == LogType.Exception || msg.StartsWith("[OpenSew]"))
                Log(type + ": " + msg + (type == LogType.Exception ? "\n" + stack : ""));
        }

        static GameObject FindAvatarPrefab()
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Prefab"))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (!path.StartsWith("Assets/") || path.Contains("_OpenSew/")) continue;
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (go != null && go.GetComponents<Component>().Any(c => c != null && c.GetType().Name == "VRCAvatarDescriptor")
                    && go.name.IndexOf("hanka", StringComparison.OrdinalIgnoreCase) >= 0)
                    return go;
            }
            return null;
        }

        static void Run()
        {
            try { Step(); }
            catch (Exception e) { Log("EXCEPCION: " + e); }
        }

        static void Step()
        {
            int step = SessionState.GetInt(StepKey, 0);
            if (step == 0)
            {
                Log("==== Prueba Fase 3 (Unity " + Application.unityVersion + ")");
                Log("Modular Avatar: " + (OutfitInstaller.SetupOutfitMethod() != null ? "si" : "NO")
                    + ", lilToon: " + (Shader.Find(OutfitInstaller.LilToonShader) != null ? "si" : "NO"));
                if (FindAvatarPrefab() == null)
                {
                    if (!File.Exists(HankaPackage)) { Log("FALLO: no encuentro " + HankaPackage); return; }
                    Log("Importando Hanka...");
                    SessionState.SetInt(StepKey, 1);
                    AssetDatabase.importPackageCompleted += n => { Log("Importado: " + n); EditorApplication.delayCall += Run; };
                    AssetDatabase.importPackageFailed += (n, err) => Log("FALLO importando " + n + ": " + err);
                    AssetDatabase.ImportPackage(HankaPackage, false);
                    return;
                }
                SessionState.SetInt(StepKey, 1);
                step = 1;
            }
            if (step == 1)
            {
                SessionState.SetInt(StepKey, 15);   // en curso: no repetir tras recargas
                var prefab = FindAvatarPrefab();
                if (prefab == null) { Log("FALLO: no hay prefab de Hanka con VRC Avatar Descriptor"); return; }
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(JacketPath);
                if (model == null) { Log("FALLO: falta " + JacketPath); return; }
                Log("Avatar: " + AssetDatabase.GetAssetPath(prefab));

                var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
                var avatar = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                var report = "";
                var outfit = OutfitInstaller.Install(avatar, model, true, true, out report);
                Log("Instalador:\n  " + report.Replace("\n", "\n  "));

                var merge = outfit.GetComponentsInChildren<Component>(true)
                    .FirstOrDefault(c => c != null && c.GetType().Name == "ModularAvatarMergeArmature");
                Check(merge != null, "Merge Armature añadido");
                if (merge != null)
                {
                    var target = merge.GetType().GetMethod("get_mergeTargetObject")?.Invoke(merge, null) as GameObject;
                    Log("  Merge Armature en '" + merge.gameObject.name + "' -> objetivo '" + (target ? target.name : "?") + "'");
                }
                var smr = outfit.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                Check(smr.Length > 0, "la chaqueta tiene SkinnedMeshRenderer (" + smr.Length + ")");
                if (smr.Length > 0) SessionState.SetInt("OpenSew.Fase3.Verts", smr[0].sharedMesh.vertexCount);
                foreach (var r in smr)
                    Log("  " + r.name + ": " + r.sharedMesh.vertexCount + " verts, " + r.bones.Length + " huesos, material "
                        + string.Join(",", r.sharedMaterials.Select(m => m ? m.shader.name : "null")));

                Directory.CreateDirectory("Assets/OpenSew");
                EditorSceneManager.SaveScene(scene, "Assets/OpenSew/Prueba_Fase3.unity");
                SessionState.SetInt(StepKey, 2);
                Log("Entrando en Play...");
                EditorApplication.EnterPlaymode();
            }
        }

        static string PathOf(Transform t, Transform root)
        {
            var s = t.name;
            for (var p = t.parent; p != null && p != root; p = p.parent) s = p.name + "/" + s;
            return s;
        }

        static void Check(bool ok, string what) => Log((ok ? "  ok   " : "  FALLO ") + what);

        static int frames;
        static void OnPlayMode(PlayModeStateChange st)
        {
            if (SessionState.GetInt(StepKey, 0) != 2) return;
            if (st == PlayModeStateChange.EnteredPlayMode) { frames = 0; EditorApplication.update += InPlay; }
            if (st == PlayModeStateChange.EnteredEditMode) { SessionState.SetInt(StepKey, 3); Log("==== Fin de la prueba"); }
        }

        static void InPlay()
        {
            if (++frames < 30) return;
            EditorApplication.update -= InPlay;
            try { PlayChecks(); } catch (Exception e) { Log("EXCEPCION en Play: " + e); }
            EditorApplication.ExitPlaymode();
        }

        static void PlayChecks()
        {
            var desc = UnityEngine.Object.FindObjectsOfType<Component>().FirstOrDefault(c => c.GetType().Name == "VRCAvatarDescriptor");
            if (desc == null) { Log("FALLO: no hay avatar en Play"); return; }
            var root = desc.transform;
            var anim = root.GetComponent<Animator>();
            int verts = SessionState.GetInt("OpenSew.Fase3.Verts", -1);
            var jacket = root.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Where(x => x.sharedMesh && x.sharedMesh.vertexCount == verts).ToArray();
            Check(jacket.Length == 1, "chaqueta de OpenSew presente en Play (" + jacket.Length + ", " + verts + " verts)");
            if (jacket.Length == 0) return;
            Log("  ruta: " + PathOf(jacket[0].transform, root));
            var r = jacket[0];

            var hips = anim && anim.isHuman ? anim.GetBoneTransform(HumanBodyBones.Hips) : null;
            int own = r.bones.Count(b => b && b.name.EndsWith("_OpenSew"));
            int onAvatar = r.bones.Count(b => b && hips && b.IsChildOf(hips));
            Check(own == 0, "ningún hueso con sufijo _OpenSew tras la fusión (" + own + " de " + r.bones.Length + ")");
            Check(hips && onAvatar == r.bones.Length, "todos los huesos son del avatar (" + onAvatar + "/" + r.bones.Length + ")");
            Log("  huesos: " + string.Join(", ", r.bones.Take(8).Select(b => b ? b.name : "null")) + (r.bones.Length > 8 ? ", ..." : ""));

            var arm = anim && anim.isHuman ? anim.GetBoneTransform(HumanBodyBones.LeftUpperArm) : null;
            if (arm == null) { Log("FALLO: sin hueso del brazo izquierdo"); return; }
            var before = new Mesh(); r.BakeMesh(before, true);
            arm.localRotation = Quaternion.AngleAxis(60f, Vector3.forward) * arm.localRotation;
            var after = new Mesh(); r.BakeMesh(after, true);
            var a = before.vertices; var b2 = after.vertices;
            int moved = 0; float maxd = 0;
            for (int i = 0; i < a.Length; i++) { float d = (a[i] - b2[i]).magnitude; if (d > 0.01f) moved++; maxd = Mathf.Max(maxd, d); }
            Check(moved > 100, "girar el brazo izquierdo 60° mueve la manga (" + moved + " verts, máx " + maxd.ToString("0.000") + " m)");

            var body = root.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Where(x => x != r && x.bones.Contains(arm) && x.name.IndexOf("body", StringComparison.OrdinalIgnoreCase) >= 0).OrderByDescending(x => x.sharedMesh.vertexCount).FirstOrDefault();
            Log("  malla del cuerpo de referencia: " + (body ? body.name : "?"));
        }
    }
}
