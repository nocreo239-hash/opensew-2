// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - capturas de la ropa instalada (proyecto de prueba).
// Tools > OpenSew > Capturas: entra en Play (Modular Avatar fusiona los huesos),
// oculta la ropa original del avatar, renderiza varias vistas a
// Logs/capturas/*.png y sale de Play.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace OpenSew.EditorTools
{
    [InitializeOnLoad]
    static class OpenSewCapturas
    {
        const string Key = "OpenSew.Capturas";
        static int frames;

        static OpenSewCapturas() { EditorApplication.playModeStateChanged += OnPlay; }

        [MenuItem("Tools/OpenSew/Capturas")]
        static void Start()
        {
            SessionState.SetBool(Key, true);
            EditorApplication.EnterPlaymode();
        }

        static void OnPlay(PlayModeStateChange st)
        {
            if (!SessionState.GetBool(Key, false)) return;
            if (st == PlayModeStateChange.EnteredPlayMode) { frames = 0; EditorApplication.update += Tick; }
            if (st == PlayModeStateChange.EnteredEditMode) SessionState.SetBool(Key, false);
        }

        static void Tick()
        {
            frames++;
            try
            {
                if (frames == 30) Shoot(false);
                else if (frames == 36) Shoot(true);
                else return;
            }
            catch (Exception e) { Debug.LogException(e); frames = 36; }
            if (frames >= 36) { EditorApplication.update -= Tick; EditorApplication.ExitPlaymode(); }
        }

        static void Shoot(bool posed)
        {
            var dir = Path.Combine(Directory.GetCurrentDirectory(), "Logs", "capturas");
            Directory.CreateDirectory(dir);
            var desc = UnityEngine.Object.FindObjectsOfType<Component>().First(c => c.GetType().Name == "VRCAvatarDescriptor");
            var root = desc.transform;
            var anim = root.GetComponent<Animator>();
            int verts = SessionState.GetInt("OpenSew.Fase3.Verts", 23144);
            var keep = new[] { "body", "face", "head", "hair", "kemo", "eye" };
            var hidden = "";
            foreach (var r in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                bool ours = r.sharedMesh && r.sharedMesh.vertexCount == verts;
                bool body = keep.Any(k => r.name.IndexOf(k, StringComparison.OrdinalIgnoreCase) >= 0);
                if (!ours && !body) { r.enabled = false; hidden += r.name + " "; }
            }
            File.WriteAllText(Path.Combine(dir, "ocultos.txt"), hidden);

            var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var center = Vector3.Lerp(hips.position, head.position, 0.45f);
            float h = head.position.y - root.position.y + 0.2f;

            var go = new GameObject("OpenSewCam");
            var cam = go.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.32f, 0.33f, 0.36f);
            cam.fieldOfView = 30f;
            var rt = new RenderTexture(1024, 1536, 24);
            cam.targetTexture = rt;
            float dist = h * 0.5f / Mathf.Tan(15f * Mathf.Deg2Rad) * 1.15f;
            var fwd = root.forward;

            void Snap(string name, float yaw, Vector3 c, float d)
            {
                var dirv = Quaternion.AngleAxis(yaw, Vector3.up) * fwd;
                go.transform.position = c + dirv * d;
                go.transform.LookAt(c);
                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
                tex.Apply();
                RenderTexture.active = null;
                File.WriteAllBytes(Path.Combine(dir, name + ".png"), tex.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(tex);
            }

            var la = anim.GetBoneTransform(HumanBodyBones.LeftUpperArm);
            if (!posed)
            {
                Snap("1_frente", 0, center, dist);
                Snap("2_tres_cuartos", 40, center, dist);
                Snap("3_lado", 90, center, dist);
                Snap("4_espalda", 180, center, dist);
                var chest = anim.GetBoneTransform(HumanBodyBones.Chest) ?? hips;
                Snap("7_detalle_hombro", 35, Vector3.Lerp(chest.position, la.position, 0.6f), dist * 0.35f);
                // brazos bajados 55° para la siguiente tanda (la piel se actualiza en el próximo frame)
                anim.enabled = false;
                var ra = anim.GetBoneTransform(HumanBodyBones.RightUpperArm);
                la.rotation = Quaternion.AngleAxis(55f, fwd) * la.rotation;
                ra.rotation = Quaternion.AngleAxis(-55f, fwd) * ra.rotation;
            }
            else
            {
                Snap("5_brazos_abajo_frente", 0, center, dist);
                Snap("6_brazos_abajo_tres_cuartos", 40, center, dist);
                Snap("8_brazos_abajo_espalda", 180, center, dist);
            }
            UnityEngine.Object.DestroyImmediate(go);
            rt.Release();
            Debug.Log("[OpenSew] capturas en " + dir);
        }
    }
}
