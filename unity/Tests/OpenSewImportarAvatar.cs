// SPDX-License-Identifier: GPL-3.0-or-later
// OpenSew - importar al proyecto de prueba el paquete de un avatar de Booth sin diálogos.
// Tools > OpenSew > Importar Manuka (proyecto de prueba)
using System.IO;
using UnityEditor;
using UnityEngine;

namespace OpenSew.EditorTools
{
    static class OpenSewImportarAvatar
    {
        const string Manuka = @"E:\assets\DOWNLOADS\MANUKA_ver1.02\MANUKA_ver1.02\MANUKA.unitypackage";

        [MenuItem("Tools/OpenSew/Importar Manuka (proyecto de prueba)")]
        static void ImportarManuka()
        {
            var log = Path.Combine(Directory.GetCurrentDirectory(), "Logs", "opensew_importar.txt");
            File.WriteAllText(log, "importando " + Manuka + "\n");
            AssetDatabase.importPackageCompleted += n => File.AppendAllText(log, "ok " + n + "\n");
            AssetDatabase.importPackageFailed += (n, e) => File.AppendAllText(log, "FALLO " + n + ": " + e + "\n");
            AssetDatabase.ImportPackage(Manuka, false);
        }
    }
}
