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
        bool colorMenu = true;
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
                colorMenu = EditorGUILayout.Toggle(
                    new GUIContent("Menú de colores", "Añade al menú del avatar un submenú para cambiar el color de la prenda en VRChat"), colorMenu);

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
                        var go = OutfitInstaller.Install(avatar, outfitModel, useLilToon, doubleSided, out lastReport, colorMenu);
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
                                         bool doubleSided, out string report, bool colorMenu = true)
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

            // 3b. hide the avatar's skin under the garment (Blender's body mask)
            if (setup != null) AddBodyCutter(avatarRoot, inst, dir, name, log);
            if (setup != null && colorMenu) AddColorMenu(inst, outDir, name, log);

            // 4. the prefab
            var prefabPath = outDir + "/" + name + (setup != null ? "_MA" : "") + ".prefab";
            PrefabUtility.SaveAsPrefabAssetAndConnect(inst, prefabPath, InteractionMode.UserAction);
            log.Add("Prefab: " + prefabPath);
            AssetDatabase.SaveAssets();

            report = string.Join("\n", log);
            Debug.Log("[OpenSew] " + report.Replace("\n", " | "));
            return inst;
        }

        /// <summary>The colours of the menu: gothic first. "Original" keeps the
        /// material as installed (texture and colour) and is the default.</summary>
        public static readonly (string name, Color color)[] Palette =
        {
            ("Negro", new Color(0.13f, 0.13f, 0.15f)),
            ("Vino", new Color(0.42f, 0.07f, 0.13f)),
            ("Morado", new Color(0.30f, 0.15f, 0.42f)),
            ("Azul noche", new Color(0.11f, 0.15f, 0.32f)),
            ("Blanco", new Color(0.93f, 0.93f, 0.93f)),
        };

        static void SetMember(object o, string member, object value)
        {
            var t = o.GetType();
            var p = t.GetProperty(member, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (p != null && p.CanWrite) { p.SetValue(o, value); return; }
            var f = t.GetField(member, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (f == null) throw new MissingMemberException(t.Name, member);
            f.SetValue(o, value);
        }

        static object EnumValue(Type t, string name) => Enum.Parse(t, name);

        /// <summary>A Modular Avatar menu to change the garment's colour in VRChat:
        /// a submenu "Color &lt;garment&gt;" with one exclusive toggle per colour, each
        /// with an MA Material Setter that puts a tinted copy of the garment's
        /// material on it. One synced int parameter, saved between sessions.
        /// MA types by name, as for the Mesh Cutter.</summary>
        public static bool AddColorMenu(GameObject outfit, string outDir, string name, List<string> log)
        {
            var itemT = FindType("nadena.dev.modular_avatar.core.ModularAvatarMenuItem");
            var instT = FindType("nadena.dev.modular_avatar.core.ModularAvatarMenuInstaller");
            var setT = FindType("nadena.dev.modular_avatar.core.ModularAvatarMaterialSetter");
            var swT = FindType("nadena.dev.modular_avatar.core.MaterialSwitchObject");
            var refT = FindType("nadena.dev.modular_avatar.core.AvatarObjectReference");
            var ctlT = FindType("nadena.dev.modular_avatar.core.PortableControlType");
            var srcT = FindType("nadena.dev.modular_avatar.core.SubmenuSource");
            if (itemT == null || instT == null || setT == null || swT == null || ctlT == null)
            { log.Add("Este Modular Avatar no tiene Material Setter: sin menú de colores."); return false; }
            var cloth = outfit.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault();
            if (cloth == null || cloth.sharedMaterials.Length == 0 || cloth.sharedMaterials[0] == null) return false;
            var baseMat = cloth.sharedMaterials[0];

            var old = outfit.transform.Find("OpenSew_Colores");
            if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
            var root = new GameObject("OpenSew_Colores");
            root.transform.SetParent(outfit.transform, false);
            Undo.RegisterCreatedObjectUndo(root, "OpenSew: menú de colores");

            Component MenuItem(GameObject go, string type, string label, string param, bool isDefault)
            {
                var item = go.AddComponent(itemT);
                // what the inspector's Reset does: a fresh control, saved and synced
                itemT.GetMethod("InitSettings", BindingFlags.NonPublic | BindingFlags.Instance)?.Invoke(item, null);
                var pc = itemT.GetProperty("PortableControl").GetValue(item);
                SetMember(pc, "Type", EnumValue(ctlT, type));
                if (param != null) SetMember(pc, "Parameter", param);
                SetMember(item, "label", label);
                SetMember(item, "isDefault", isDefault);
                SetMember(item, "automaticValue", true);
                SetMember(item, "isSaved", true);
                SetMember(item, "isSynced", true);
                return item;
            }

            root.AddComponent(instT);
            var sub = MenuItem(root, "SubMenu", "Color " + name, null, false);
            if (srcT != null) SetMember(sub, "MenuSource", EnumValue(srcT, "Children"));

            string param = "OpenSew/" + name + "/Color";
            var orig = new GameObject("Original");
            orig.transform.SetParent(root.transform, false);
            MenuItem(orig, "Toggle", "Original", param, true);

            var bodyPath = AssetDatabase.GetAssetPath(baseMat);
            string matDir = string.IsNullOrEmpty(bodyPath) ? outDir : Path.GetDirectoryName(bodyPath).Replace('\\', '/');
            int n = 0;
            foreach (var (cname, col) in Palette)
            {
                var matPath = matDir + "/" + Sanitize(baseMat.name + "_" + cname) + ".mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
                if (mat == null)
                {
                    mat = new Material(baseMat) { name = baseMat.name + "_" + cname };
                    if (mat.HasProperty("_Color")) mat.SetColor("_Color", col);
                    if (mat.HasProperty("_ShadowColor"))
                        mat.SetColor("_ShadowColor", new Color(col.r * 0.72f, col.g * 0.72f, col.b * 0.78f, 1f));
                    AssetDatabase.CreateAsset(mat, matPath);
                }
                var go = new GameObject(cname);
                go.transform.SetParent(root.transform, false);
                MenuItem(go, "Toggle", cname, param, false);
                var setter = go.AddComponent(setT);
                var sw = System.Activator.CreateInstance(swT);
                var r = System.Activator.CreateInstance(refT);
                refT.GetMethod("Set", new[] { typeof(GameObject) }).Invoke(r, new object[] { cloth.gameObject });
                swT.GetField("Object").SetValue(sw, r);
                swT.GetField("Material").SetValue(sw, mat);
                swT.GetField("MaterialIndex").SetValue(sw, 0);
                var list = (System.Collections.IList)setT.GetProperty("Objects").GetValue(setter);
                list.Add(sw);
                n++;
            }
            AssetDatabase.SaveAssets();
            log.Add("Menú de colores: Original + " + n + " colores (" + string.Join(", ", Palette.Select(p => p.name))
                    + "), parámetro " + param + ".");
            return true;
        }

        [Serializable] class MaskEntry { public int material_index; public string material; public string file; }
        [Serializable] class OutfitMeta { public string body; public string uv; public int hidden_vertices; public int body_vertices; public MaskEntry[] masks; }

        static Type FindType(string fullName) =>
            AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType(fullName)).FirstOrDefault(t => t != null);

        /// <summary>From &lt;fbx&gt;.opensew.json and its masks, written by OpenSew's
        /// export next to the FBX: an MA Mesh Cutter on a child of the outfit whose
        /// Object is the avatar's body, with one Vertex Filter - By Mask per body
        /// material. MA deletes the body polygons under the garment at build, and
        /// only while the outfit is on (it is a reactive component). Types are looked
        /// up by name (MA 1.13+, public API), so this compiles without MA.</summary>
        public static bool AddBodyCutter(GameObject avatarRoot, GameObject outfit, string dir, string name, List<string> log)
        {
            var metaPath = dir + "/" + name + ".opensew.json";
            if (!File.Exists(metaPath)) { log.Add("Sin máscara del cuerpo (" + name + ".opensew.json no está junto al FBX): el cuerpo queda entero."); return false; }
            var meta = JsonUtility.FromJson<OutfitMeta>(File.ReadAllText(metaPath));
            if (meta == null || meta.masks == null || meta.masks.Length == 0) { log.Add("La máscara del cuerpo está vacía: nada que ocultar."); return false; }
            var cutterT = FindType("nadena.dev.modular_avatar.core.ModularAvatarMeshCutter");
            var filterT = FindType("nadena.dev.modular_avatar.core.vertex_filters.VertexFilterByMaskComponent");
            var refT = FindType("nadena.dev.modular_avatar.core.AvatarObjectReference");
            if (cutterT == null || filterT == null || refT == null) { log.Add("Este Modular Avatar no tiene Mesh Cutter (hace falta 1.13 o más nuevo): el cuerpo queda entero."); return false; }

            // the body: the avatar's renderer with the name it had in Blender,
            // else the one with the most vertices outside the outfit
            var renderers = avatarRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Where(r => r.sharedMesh != null && !r.transform.IsChildOf(outfit.transform)).ToList();
            var body = renderers.FirstOrDefault(r => r.name == meta.body)
                       ?? renderers.OrderByDescending(r => r.sharedMesh.vertexCount).FirstOrDefault();
            if (body == null) { log.Add("No encontré el cuerpo del avatar: el cuerpo queda entero."); return false; }
            if (body.name != meta.body) log.Add("Aviso: el cuerpo se llamaba '" + meta.body + "' en Blender; uso '" + body.name + "'.");

            var old = outfit.transform.Find("OpenSew_OcultarCuerpo");
            if (old != null) UnityEngine.Object.DestroyImmediate(old.gameObject);
            var go = new GameObject("OpenSew_OcultarCuerpo");
            go.transform.SetParent(outfit.transform, false);
            Undo.RegisterCreatedObjectUndo(go, "OpenSew: ocultar cuerpo");
            var cutter = go.AddComponent(cutterT);
            var objRef = System.Activator.CreateInstance(refT);
            refT.GetMethod("Set", new[] { typeof(GameObject) }).Invoke(objRef, new object[] { body.gameObject });
            cutterT.GetProperty("Object").SetValue(cutter, objRef);
            var multi = cutterT.GetProperty("MultiMode");
            multi.SetValue(cutter, Enum.Parse(multi.PropertyType, "VertexUnion"));

            int n = 0;
            foreach (var m in meta.masks)
            {
                var texPath = dir + "/" + m.file;
                var imp = AssetImporter.GetAtPath(texPath) as TextureImporter;
                if (imp == null) { log.Add("Falta la máscara " + m.file + " junto al FBX."); continue; }
                // read exactly as painted: linear, uncompressed, no mipmaps, readable
                if (!imp.isReadable || imp.sRGBTexture || imp.mipmapEnabled || imp.textureCompression != TextureImporterCompression.Uncompressed)
                {
                    imp.isReadable = true; imp.sRGBTexture = false; imp.mipmapEnabled = false;
                    imp.textureCompression = TextureImporterCompression.Uncompressed;
                    imp.SaveAndReimport();
                }
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath);
                // the body's material slot: by name if the avatar still uses it,
                // else the index Blender had
                int slot = m.material_index;
                var mats = body.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                    if (mats[i] != null && mats[i].name == m.material) { slot = i; break; }
                if (slot >= mats.Length) { log.Add("La máscara " + m.file + " es del material " + slot + " y el cuerpo tiene " + mats.Length + "."); continue; }
                var f = go.AddComponent(filterT);
                filterT.GetProperty("MaterialIndex").SetValue(f, slot);
                filterT.GetProperty("MaskTexture").SetValue(f, tex);
                var dm = filterT.GetProperty("DeleteMode"); dm.SetValue(f, Enum.Parse(dm.PropertyType, "DeleteBlack"));
                // a polygon goes only if every corner is under the cloth
                var sm = filterT.GetProperty("SelectionMode"); sm.SetValue(f, Enum.Parse(sm.PropertyType, "AllVertices"));
                filterT.GetProperty("UVChannel").SetValue(f, 0);
                n++;
            }
            if (n == 0) { UnityEngine.Object.DestroyImmediate(go); return false; }
            log.Add("Modular Avatar Mesh Cutter: oculta " + meta.hidden_vertices + " de " + meta.body_vertices
                    + " vértices de '" + body.name + "' bajo la prenda (" + n + " máscara(s)).");
            return true;
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
