// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - instalar en Unity la ropa exportada desde Blender (Fase 3).
//
// Tools > OpenSew > Instalar ropa (Modular Avatar)
//
// 1. Crea materiales lilToon (shader "lilToon") a partir de los del FBX,
//    copiando color (_Color) y textura (_MainTex); doble cara con _Cull = 0.
// 2. Mete el FBX dentro del avatar elegido y le pone esos materiales.
// 3. Ejecuta el "Setup Outfit" de Modular Avatar (API publica
//    nadena.dev.modular_avatar.core.editor.SetupOutfit.SetupOutfitUI), que
//    anade Merge Armature (objetivo: la armadura del avatar), Outfit Root y
//    Mesh Settings, y deduce el sufijo de los huesos (_OpenSew).
// 4. Guarda el resultado como prefab ("Modular Avatar Preset") junto al FBX.
//
// Modular Avatar se busca por reflexion y lilToon por el nombre del shader,
// asi que el script compila aunque falte alguno: sin Modular Avatar se crea
// solo el prefab con materiales; sin lilToon se dejan los materiales del FBX.
//
// Codigo GPL-3.0, como el add-on OpenSew 2 del que forma parte.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace OpenSew.EditorTools
{
    public class OutfitInstallerWindow : EditorWindow
    {
        GameObject avatar;
        GameObject outfitModel;
        bool useLilToon = true;
        bool doubleSided = true;
        Vector2 scroll;
        string lastReport = "";

        [MenuItem("Tools/OpenSew/Instalar ropa (Modular Avatar)")]
        static void Open()
        {
            var w = GetWindow<OutfitInstallerWindow>("OpenSew");
            w.minSize = new Vector2(380, 300);
        }

        void OnEnable()
        {
            var sel = Selection.activeGameObject;
            if (sel != null && OutfitInstaller.FindAvatarRoot(sel) != null)
                avatar = OutfitInstaller.FindAvatarRoot(sel);
            if (Selection.activeObject is GameObject go && OutfitInstaller.IsModelAsset(go))
                outfitModel = go;
        }

        void OnGUI()
        {
            EditorGUILayout.LabelField("Ropa exportada con OpenSew", EditorStyles.boldLabel);
            avatar = (GameObject)EditorGUILayout.ObjectField(
                new GUIContent("Avatar (escena)", "La raiz del avatar, con su VRC Avatar Descriptor"),
                avatar, typeof(GameObject), true);
            outfitModel = (GameObject)EditorGUILayout.ObjectField(
                new GUIContent("FBX de la ropa", "El .fbx que exporto el add-on (Export FBX)"),
                outfitModel, typeof(GameObject), false);
            useLilToon = EditorGUILayout.Toggle(new GUIContent("Materiales lilToon"), useLilToon);
            using (new EditorGUI.DisabledScope(!useLilToon))
                doubleSided = EditorGUILayout.Toggle(
                    new GUIContent("Doble cara", "Se ve el interior de mangas y cuello"), doubleSided);

            EditorGUILayout.Space();
            bool hasMA = OutfitInstaller.SetupOutfitMethod() != null;
            bool hasLil = Shader.Find(OutfitInstaller.LilToonShader) != null;
            EditorGUILayout.HelpBox(
                (hasMA ? "Modular Avatar: encontrado" : "Modular Avatar: NO encontrado (solo se creara el prefab con materiales)")
                + "\n" + (hasLil ? "lilToon: encontrado" : "lilToon: NO encontrado (se usaran los materiales del FBX)"),
                hasMA && hasLil ? MessageType.Info : MessageType.Warning);

            string problem = null;
            if (outfitModel == null) problem = "Elige el FBX de la ropa.";
            else if (!OutfitInstaller.IsModelAsset(outfitModel)) problem = "Eso no es un modelo importado (.fbx).";
            else if (avatar == null) problem = "Elige el avatar de la escena.";
            else if (OutfitInstaller.FindAvatarRoot(avatar) != avatar)
                problem = "El avatar tiene que ser la raiz con el VRC Avatar Descriptor.";
            if (problem != null) EditorGUILayout.HelpBox(problem, MessageType.None);

            using (new EditorGUI.DisabledScope(problem != null))
            {
                if (GUILayout.Button("Crear prefab e instalar en el avatar", GUILayout.Height(30)))
                {
                    try
                    {
                        var go = OutfitInstaller.Install(avatar, outfitModel, useLilToon, doubleSided, out lastReport);
                        if (go != null) Selection.activeGameObject = go;
                    }
                    catch (Exception e)
                    {
                        lastReport = "Error: " + e.Message;
                        Debug.LogException(e);
                    }
                }
            }

            if (!string.IsNullOrEmpty(lastReport))
            {
                scroll = EditorGUILayout.BeginScrollView(scroll);
                EditorGUILayout.HelpBox(lastReport, MessageType.None);
                EditorGUILayout.EndScrollView();
            }
        }
    }

    public static class OutfitInstaller
    {
        public const string LilToonShader = "lilToon";
        const string SetupOutfitType = "nadena.dev.modular_avatar.core.editor.SetupOutfit";

        public static bool IsModelAsset(GameObject go)
        {
            if (go == null) return false;
            var path = AssetDatabase.GetAssetPath(go);
            return !string.IsNullOrEmpty(path) && AssetImporter.GetAtPath(path) is ModelImporter;
        }

        /// <summary>The GameObject carrying a VRC Avatar Descriptor at or above go.</summary>
        public static GameObject FindAvatarRoot(GameObject go)
        {
            for (var t = go != null ? go.transform : null; t != null; t = t.parent)
                if (t.GetComponents<Component>().Any(c => c != null && c.GetType().Name == "VRCAvatarDescriptor"))
                    return t.gameObject;
            return null;
        }

        public static MethodInfo SetupOutfitMethod()
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                var t = asm.GetType(SetupOutfitType, false);
                if (t == null) continue;
                var m = t.GetMethod("SetupOutfitUI", BindingFlags.Public | BindingFlags.Static,
                                    null, new[] { typeof(GameObject) }, null);
                if (m != null) return m;
            }
            return null;
        }

        public static GameObject Install(GameObject avatarRoot, GameObject model, bool lilToon,
                                         bool doubleSided, out string report)
        {
            var log = new List<string>();
            var modelPath = AssetDatabase.GetAssetPath(model);
            var dir = Path.GetDirectoryName(modelPath).Replace('\\', '/');
            var name = Path.GetFileNameWithoutExtension(modelPath);
            var outDir = dir + "/" + name + "_OpenSew";
            if (!AssetDatabase.IsValidFolder(outDir))
                AssetDatabase.CreateFolder(dir, name + "_OpenSew");

            // 1. materials
            var remap = new Dictionary<Material, Material>();
            var shader = lilToon ? Shader.Find(LilToonShader) : null;
            if (lilToon && shader == null) log.Add("lilToon no esta en el proyecto: se dejan los materiales del FBX.");
            if (shader != null)
            {
                foreach (var r in model.GetComponentsInChildren<Renderer>(true))
                foreach (var src in r.sharedMaterials)
                {
                    if (src == null || remap.ContainsKey(src)) continue;
                    var matPath = outDir + "/" + Sanitize(src.name) + ".mat";
                    var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
                    if (mat == null)
                    {
                        mat = new Material(shader) { name = src.name };
                        if (src.HasProperty("_Color")) mat.SetColor("_Color", src.GetColor("_Color"));
                        if (src.HasProperty("_MainTex") && src.GetTexture("_MainTex") != null)
                            mat.SetTexture("_MainTex", src.GetTexture("_MainTex"));
                        if (mat.HasProperty("_Cull")) mat.SetFloat("_Cull", doubleSided ? 0f : 2f);
                        ApplySoftShadow(mat);
                        AssetDatabase.CreateAsset(mat, matPath);
                        log.Add("Material lilToon: " + matPath);
                    }
                    else log.Add("Material ya existente (no se toca): " + matPath);
                    remap[src] = mat;
                }
            }

            // 2. the outfit inside the avatar
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(model, avatarRoot.transform);
            Undo.RegisterCreatedObjectUndo(inst, "OpenSew: instalar ropa");
            inst.name = name;
            inst.transform.localPosition = Vector3.zero;
            inst.transform.localRotation = Quaternion.identity;
            inst.transform.localScale = Vector3.one;
            foreach (var r in inst.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                    if (mats[i] != null && remap.TryGetValue(mats[i], out var m)) { mats[i] = m; changed = true; }
                if (changed) r.sharedMaterials = mats;
            }

            // 3. Modular Avatar's own Setup Outfit
            var setup = SetupOutfitMethod();
            if (setup != null)
            {
                setup.Invoke(null, new object[] { inst });
                var merge = inst.GetComponentsInChildren<Component>(true)
                    .FirstOrDefault(c => c != null && c.GetType().Name == "ModularAvatarMergeArmature");
                if (merge != null)
                {
                    var suffix = merge.GetType().GetField("suffix")?.GetValue(merge) as string;
                    var prefix = merge.GetType().GetField("prefix")?.GetValue(merge) as string;
                    log.Add("Modular Avatar: Merge Armature en '" + merge.gameObject.name + "' (prefijo '"
                            + prefix + "', sufijo '" + suffix + "').");
                }
                else log.Add("Modular Avatar no pudo configurar la ropa: mira la ventana de error de Setup Outfit.");
            }
            else log.Add("Modular Avatar no esta en el proyecto: la ropa queda dentro del avatar sin fusionar.");

            // 4. the prefab
            var prefabPath = outDir + "/" + name + (setup != null ? "_MA" : "") + ".prefab";
            PrefabUtility.SaveAsPrefabAssetAndConnect(inst, prefabPath, InteractionMode.UserAction);
            log.Add("Prefab: " + prefabPath);
            AssetDatabase.SaveAssets();

            report = string.Join("\n", log);
            Debug.Log("[OpenSew] " + report.Replace("\n", " | "));
            return inst;
        }

        /// <summary>lilToon's first shadow, soft and in the cloth's own colour.
        /// Off by default, the cloth renders flat white with no shading at all
        /// (seen on Hanka); lilToon's default shadow colour is a pinkish purple
        /// that blots a pale fabric, so the shade is taken from the base colour.
        /// Property names from lilToon 2.4.1 (Shader/lts.shader).</summary>
        static void ApplySoftShadow(Material mat)
        {
            if (!mat.HasProperty("_UseShadow")) return;
            mat.SetFloat("_UseShadow", 1f);
            var c = mat.HasProperty("_Color") ? mat.GetColor("_Color") : Color.white;
            var shade = new Color(c.r * 0.72f, c.g * 0.72f, c.b * 0.78f, 1f);
            if (mat.HasProperty("_ShadowColor")) mat.SetColor("_ShadowColor", shade);
            if (mat.HasProperty("_ShadowStrength")) mat.SetFloat("_ShadowStrength", 0.75f);
            if (mat.HasProperty("_ShadowBorder")) mat.SetFloat("_ShadowBorder", 0.5f);
            if (mat.HasProperty("_ShadowBlur")) mat.SetFloat("_ShadowBlur", 0.3f);
        }

        static string Sanitize(string s)
        {
            foreach (var c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_');
            return s;
        }
    }
}
