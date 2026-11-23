// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - Fase 8: el "Tipo de tela" del instalador. Instala el underbust de
// Manuka como encaje recortado y como transparente y comprueba el shader de
// lilToon, su modo y los materiales de color. Tools > OpenSew > Prueba Fase 8.
// Log en Logs/opensew_fase8.txt.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace OpenSew.EditorTools
{
    static class OpenSewPruebaFase8
    {
        const string Model = "Assets/OpenSew/Fase7/Manuka_UNDERBUST.fbx";
        const string Avatar = "Assets/MANUKA/Prefab/MANUKA_lilToon.prefab";
        static readonly string LogPath = Path.Combine(Directory.GetCurrentDirectory(), "Logs", "opensew_fase8.txt");
        static int fails;

        static void Log(string s) => File.AppendAllText(LogPath, DateTime.Now.ToString("HH:mm:ss ") + s + Environment.NewLine);
        static void Check(bool ok, string what) { Log((ok ? "  ok   " : "  FALLO ") + what); if (!ok) fails++; }

        [MenuItem("Tools/OpenSew/Prueba Fase 8")]
        static void Run()
        {
            File.WriteAllText(LogPath, "");
            fails = 0;
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Model);
            var avatarPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(Avatar);
            if (model == null || avatarPrefab == null) { Log("FALLO: falta " + (model == null ? Model : Avatar)); return; }
            string[] names = { "opaca", "encaje", "transparente" };
            float[] modes = { 0f, 1f, 2f };
            foreach (int cloth in new[] { 1, 2, 0 })
            {
                Log("---- tela " + names[cloth]);
                EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
                var av = (GameObject)PrefabUtility.InstantiatePrefab(avatarPrefab);
                string report;
                var go = OutfitInstaller.Install(av, model, true, true, out report, true, cloth);
                Check(go != null, "instalada");
                if (go == null) { Log(report); continue; }
                var mats = go.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Where(m => m != null).ToArray();
                var want = OutfitInstaller.ClothShaders[cloth];
                Check(mats.Length > 0 && mats.All(m => m.shader.name == want),
                      "shader " + want + ": " + string.Join(", ", mats.Select(m => m.shader.name).Distinct()));
                Check(mats.All(m => !m.HasProperty("_TransparentMode") || Mathf.Approximately(m.GetFloat("_TransparentMode"), modes[cloth])),
                      "modo de lilToon " + modes[cloth]);
                var dir = Path.GetDirectoryName(Model).Replace('\\', '/') + "/" + Path.GetFileNameWithoutExtension(Model) + "_OpenSew";
                var colours = AssetDatabase.FindAssets("t:Material", new[] { dir }).Select(AssetDatabase.GUIDToAssetPath)
                    .Select(AssetDatabase.LoadAssetAtPath<Material>).Where(m => m != null && m.name.Contains("_")).ToArray();
                // the colour variants follow the garment's Tipo de tela when it is installed again
                Check(colours.Length == 5 && colours.All(m => m.shader.name == want),
                      "los 5 colores con el mismo shader (" + string.Join(", ", colours.Select(m => m.shader.name).Distinct()) + ")");
            }
            Log(fails == 0 ? "==== Fin: 0 fallos" : "==== Fin: " + fails + " fallos");
        }
    }
}
