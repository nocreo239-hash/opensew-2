// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - empaquetar una prenda instalada para venderla (.unitypackage).
//
// Tools > OpenSew > Empaquetar para vender
//
// Recibe el prefab que deja "Instalar ropa" (<prenda>_OpenSew/<prenda>_MA.prefab)
// y exporta un .unitypackage con todo lo que la prenda usa (FBX, materiales,
// texturas, prefab) y un LEEME.txt con los requisitos.
//
// No se incluyen lilToon, Modular Avatar ni el VRChat SDK: el comprador los
// instala él mismo (es lo habitual en Booth y Jinxxy, y sus licencias son de
// sus autores). Tampoco el avatar: solo la ropa.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace OpenSew.EditorTools
{
    public class OpenSewPackagerWindow : EditorWindow
    {
        GameObject prefab;
        string product = "";
        string shop = "";
        string avatarName = "";
        string lastReport = "";
        Vector2 scroll;

        [MenuItem("Tools/OpenSew/Empaquetar para vender")]
        static void Open()
        {
            var w = GetWindow<OpenSewPackagerWindow>("OpenSew - Empaquetar");
            w.minSize = new Vector2(400, 320);
        }

        void OnEnable()
        {
            if (Selection.activeObject is GameObject go && PrefabUtility.IsPartOfPrefabAsset(go))
                prefab = go;
            if (prefab != null && string.IsNullOrEmpty(product)) product = OpenSewPackager.GuessProduct(prefab);
        }

        void OnGUI()
        {
            EditorGUILayout.LabelField("Prenda lista para vender", EditorStyles.boldLabel);
            var before = prefab;
            prefab = (GameObject)EditorGUILayout.ObjectField(
                new GUIContent("Prefab de la prenda", "El prefab _MA que crea 'Instalar ropa'"),
                prefab, typeof(GameObject), false);
            if (prefab != before && prefab != null) product = OpenSewPackager.GuessProduct(prefab);
            product = EditorGUILayout.TextField(new GUIContent("Nombre del producto"), product);
            shop = EditorGUILayout.TextField(new GUIContent("Tienda / autor", "Sale en el LEEME"), shop);
            avatarName = EditorGUILayout.TextField(new GUIContent("Avatar", "Para qué avatar es (sale en el LEEME)"),
                                                   avatarName);
            using (new EditorGUI.DisabledScope(prefab == null || string.IsNullOrEmpty(product)))
            {
                if (GUILayout.Button("Exportar .unitypackage", GUILayout.Height(28)))
                {
                    var path = EditorUtility.SaveFilePanel("Guardar paquete", "", OpenSewPackager.FileName(product),
                                                           "unitypackage");
                    if (!string.IsNullOrEmpty(path))
                        OpenSewPackager.Export(prefab, product, shop, avatarName, path, out lastReport);
                }
            }
            if (!string.IsNullOrEmpty(lastReport))
            {
                scroll = EditorGUILayout.BeginScrollView(scroll);
                EditorGUILayout.HelpBox(lastReport, MessageType.Info);
                EditorGUILayout.EndScrollView();
            }
        }
    }

    public static class OpenSewPackager
    {
        // carpetas de paquetes de terceros que nunca van dentro: el comprador los instala
        static readonly string[] ThirdParty = { "lilToon", "nadena", "ModularAvatar", "VRChat", "VRCSDK", "NDMF" };

        public static string GuessProduct(GameObject prefab)
        {
            var n = Path.GetFileNameWithoutExtension(AssetDatabase.GetAssetPath(prefab));
            if (n.EndsWith("_MA")) n = n.Substring(0, n.Length - 3);
            return n;
        }

        public static string FileName(string product)
        {
            var bad = Path.GetInvalidFileNameChars();
            return new string(product.Select(c => bad.Contains(c) || c == ' ' ? '_' : c).ToArray());
        }

        /// <summary>Assets that go in the package: the prefab and everything it
        /// depends on inside Assets/, minus scripts and third-party packages.</summary>
        public static List<string> Contents(GameObject prefab)
        {
            var root = AssetDatabase.GetAssetPath(prefab);
            return AssetDatabase.GetDependencies(root, true)
                .Where(p => p.StartsWith("Assets/"))
                .Where(p => !p.EndsWith(".cs") && !p.EndsWith(".dll") && !p.EndsWith(".asmdef"))
                .Where(p => !ThirdParty.Any(t => p.IndexOf("/" + t, StringComparison.OrdinalIgnoreCase) >= 0))
                .Where(p => !p.EndsWith(".shader") && !p.EndsWith(".cginc") && !p.EndsWith(".hlsl"))
                .Distinct().OrderBy(p => p).ToList();
        }

        public static string ReadmeText(string product, string shop, string avatarName, IEnumerable<string> files,
                                        string bodyName = null)
        {
            var nl = Environment.NewLine;
            return product + (string.IsNullOrEmpty(shop) ? "" : "  -  " + shop) + nl + nl
                 + (string.IsNullOrEmpty(avatarName) ? "" : "Avatar: " + avatarName + nl + nl)
                 + "Requisitos (instálalos antes, con el VRChat Creator Companion o ALCOM):" + nl
                 + "  - VRChat SDK - Avatars" + nl
                 + "  - Modular Avatar 1.19 o más nuevo" + nl
                 + "  - lilToon" + nl + nl
                 + "Uso:" + nl
                 + "  1. Importa este paquete." + nl
                 + "  2. Arrastra el prefab de la prenda sobre tu avatar en la jerarquía." + nl
                 + "     Modular Avatar la une al esqueleto al subir o al entrar en Play." + nl
                 + (string.IsNullOrEmpty(bodyName) ? "" :
                    "  3. La piel bajo la prenda se oculta sola (MA Mesh Cutter). Para eso el cuerpo del avatar" + nl
                  + "     tiene que llamarse '" + bodyName + "' como en el avatar original; si lo renombraste," + nl
                  + "     selecciona OpenSew_OcultarCuerpo dentro de la prenda y elige tu cuerpo en 'Object'." + nl)
                 + nl
                 + "Requirements: VRChat SDK - Avatars, Modular Avatar 1.19+, lilToon." + nl
                 + "Usage: import, then drag the outfit prefab onto your avatar in the hierarchy." + nl + nl
                 + "Archivos:" + nl + string.Join(nl, files.Select(f => "  " + f)) + nl + nl
                 + "Hecho con OpenSew 2 (add-on de Blender, GPL-3.0)." + nl;
        }

        public static bool Export(GameObject prefab, string product, string shop, string avatarName,
                                  string outPath, out string report)
        {
            var log = new List<string>();
            var files = Contents(prefab);
            if (files.Count == 0)
            {
                report = "El prefab no tiene nada que empaquetar.";
                return false;
            }
            var dir = Path.GetDirectoryName(AssetDatabase.GetAssetPath(prefab)).Replace('\\', '/');
            var readme = dir + "/LEEME_" + FileName(product) + ".txt";
            File.WriteAllText(readme, ReadmeText(product, shop, avatarName, files, BodyName(prefab)));
            AssetDatabase.ImportAsset(readme);
            files.Add(readme);

            var missing = MissingRequirements(prefab);
            foreach (var m in missing) log.Add("Aviso: " + m);

            AssetDatabase.ExportPackage(files.ToArray(), outPath, ExportPackageOptions.Default);
            log.Add("Paquete: " + outPath);
            log.Add(files.Count + " archivos:");
            log.AddRange(files.Select(f => "  " + f));
            report = string.Join("\n", log);
            Debug.Log("[OpenSew] " + report.Replace("\n", " | "));
            return File.Exists(outPath);
        }

        /// <summary>The avatar body the outfit's Mesh Cutter points at, by its path
        /// under the avatar (MA stores it relative to the avatar root).</summary>
        public static string BodyName(GameObject prefab)
        {
            var c = prefab.GetComponentsInChildren<Component>(true).FirstOrDefault(x => x != null && x.GetType().Name == "ModularAvatarMeshCutter");
            if (c == null) return null;
            var r = c.GetType().GetProperty("Object")?.GetValue(c);
            return r?.GetType().GetField("referencePath")?.GetValue(r) as string;
        }

        /// <summary>What a buyer would find wrong: no Modular Avatar merge, or
        /// materials not on lilToon.</summary>
        public static List<string> MissingRequirements(GameObject prefab)
        {
            var out_ = new List<string>();
            bool merge = prefab.GetComponentsInChildren<Component>(true)
                .Any(c => c != null && c.GetType().Name == "ModularAvatarMergeArmature");
            if (!merge) out_.Add("el prefab no tiene Merge Armature de Modular Avatar: usa el prefab _MA de 'Instalar ropa'.");
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true))
            foreach (var m in r.sharedMaterials)
                if (m != null && m.shader != null && !m.shader.name.StartsWith("lilToon") && !m.shader.name.Contains("lil"))
                    out_.Add("el material '" + m.name + "' no usa lilToon (" + m.shader.name + ").");
            return out_;
        }
    }
}
