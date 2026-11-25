// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - el camino del comprador: sin instalador, arrastra el prefab _MA
// sobre su avatar. Dos casos con Manuka: el cuerpo con su nombre y renombrado.
// Tools > OpenSew > Prueba comprador. Log en Logs/opensew_comprador.txt.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OpenSew.EditorTools
{
    [InitializeOnLoad]
    static class OpenSewPruebaComprador
    {
        const string Prefab = "Assets/OpenSew/Fase7/Manuka_HOODIE_OpenSew/Manuka_HOODIE_MA.prefab";
        const string KCase = "OpenSew.Buyer.Case", KTris = "OpenSew.Buyer.Tris";
        static readonly string LogPath = Path.Combine(Directory.GetCurrentDirectory(), "Logs", "opensew_comprador.txt");
        static int frames, errors;

        static OpenSewPruebaComprador()
        {
            EditorApplication.playModeStateChanged += st =>
            {
                int c = SessionState.GetInt(KCase, -1);
                if (c < 0) return;
                if (st == PlayModeStateChange.EnteredPlayMode) { frames = 0; errors = 0; Application.logMessageReceived += OnLog; EditorApplication.update += Tick; }
                if (st == PlayModeStateChange.EnteredEditMode) EditorApplication.delayCall += () => Run(c + 1);
            };
        }

        static void Log(string s) => File.AppendAllText(LogPath, DateTime.Now.ToString("HH:mm:ss ") + s + Environment.NewLine);
        static void OnLog(string msg, string stack, LogType t)
        {
            if (t == LogType.Error || t == LogType.Exception) { errors++; Log("  error de Unity: " + msg.Split('\n')[0]); }
        }

        [MenuItem("Tools/OpenSew/Prueba comprador")]
        static void Start() { File.WriteAllText(LogPath, ""); Run(0); }

        static void Run(int c)
        {
            if (c > 1) { SessionState.SetInt(KCase, -1); Log("==== Fin"); return; }
            SessionState.SetInt(KCase, c);
            Log("---- " + (c == 0 ? "cuerpo con su nombre" : "cuerpo renombrado"));
            var avatarPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/MANUKA/Prefab/MANUKA_lilToon.prefab");
            var outfit = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            if (avatarPrefab == null || outfit == null) { Log("FALLO: falta el avatar o el prefab"); SessionState.SetInt(KCase, -1); return; }
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            var av = (GameObject)PrefabUtility.InstantiatePrefab(avatarPrefab);
            var body = av.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r => r.name == "Manuka_body");
            if (c == 1) body.name = "Mi_cuerpo";
            SessionState.SetString("OpenSew.Buyer.Body", body.name);
            SessionState.SetInt(KTris, body.sharedMesh.triangles.Length / 3);
            // what a buyer does: drop the prefab on the avatar
            PrefabUtility.InstantiatePrefab(outfit, av.transform);
            EditorApplication.EnterPlaymode();
        }

        static void Tick()
        {
            if (++frames < 30) return;
            EditorApplication.update -= Tick;
            Application.logMessageReceived -= OnLog;
            try
            {
                var desc = UnityEngine.Object.FindObjectsOfType<Component>().First(x => x.GetType().Name == "VRCAvatarDescriptor");
                var anim = desc.GetComponent<Animator>();
                var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
                var body = desc.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r => r.name == SessionState.GetString("OpenSew.Buyer.Body", ""));
                var cloth = desc.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(r => r.bones.Any(b => b && b.name.Contains("Hips")) && r.sharedMesh && r.sharedMesh.name.Contains("Hoodie"));
                int before = SessionState.GetInt(KTris, 0), after = body.sharedMesh.triangles.Length / 3;
                bool merged = cloth.bones.All(b => b && b.IsChildOf(hips)) && !cloth.bones.Any(b => b.name.EndsWith("_OpenSew"));
                Log("  " + (merged ? "ok  " : "FALLO") + " prenda unida al esqueleto");
                Log("  cuerpo " + before + " -> " + after + " triángulos (" + (after < before ? "piel oculta" : "piel sin tocar") + ")");
                Log("  errores de Unity en Play: " + errors);
            }
            catch (Exception e) { Log("EXCEPCION: " + e.Message); }
            EditorApplication.ExitPlaymode();
        }
    }
}
