# Fase 3: exportar a VRChat (FBX, Modular Avatar, lilToon), reporte

Fecha: 2026-11-20 · Rama `fase-3` (sale de `fase-2`) · Blender 5.2.4 (pruebas automáticas)

**Estado: falta la prueba en Unity.** Todo lo de Blender está probado; el
script de Unity está escrito contra el código fuente actual de Modular
Avatar y lilToon, pero aún no se ha compilado ni ejecutado en un proyecto.

## Resumen

1. **Botón "Export FBX"** (debajo de Finalize). Exporta las prendas
   finalizadas y una copia recortada de la armadura del avatar a un FBX listo
   para Unity y para el *Setup Outfit* de Modular Avatar.
2. **Pesos limpios para Unity:** solo grupos de huesos, como mucho 4
   influencias por vértice, normalizadas; un vértice sin peso hereda el del
   vecino más cercano.
3. **Script de Unity** (`unity/Assets/OpenSew/Editor/OpenSewOutfitInstaller.cs`):
   crea materiales lilToon, mete la ropa en el avatar, ejecuta el Setup
   Outfit de Modular Avatar y guarda un prefab.
4. **Test nuevo:** `tests/test_export.py`.

## 1. Lo que pide Modular Avatar (verificado)

De su guía para creadores de ropa y de su código (`Editor/SetupOutfit.cs`,
versión 1.19.0, commit `c97d5cb`):

- *Setup Outfit* busca `RaízDeLaRopa → Armature → Hips`; el hueso de la cadera
  de la ropa debe **contener** el nombre del del avatar, y el texto extra debe
  ser el mismo en todos los huesos (lo deduce como prefijo o sufijo, distingue
  mayúsculas).
- Las posiciones de los huesos tienen que coincidir con las del avatar; los
  ejes de rotación no.
- No conviene que la armadura y los huesos tengan exactamente los nombres del
  avatar.
- `SetupOutfit.SetupOutfitUI(GameObject)` es API pública: exige que la ropa
  esté dentro de un único avatar (VRC Avatar Descriptor) con Animator
  humanoide. Añade *Merge Armature* (objetivo: la armadura del avatar, en modo
  BaseToMerge), *Outfit Root* y *Mesh Settings*, y corrige A-pose/T-pose si
  los brazos miden igual.
- El editor de Modular Avatar enlaza las DLL del SDK de VRChat
  (`VRCSDK3A.dll`, `VRCSDKBase.dll`…): sin el SDK de avatares no compila.

lilToon (2.4.1, `Assets/lilToon/Shader/lts.shader`): el shader se llama
`"lilToon"`; color `_Color`, textura `_MainTex`, caras `_Cull` (2 = trasera,
0 = doble cara).

## 2. El FBX

`clothing_design/export.py`, sin tocar la escena (trabaja sobre copias que
borra al terminar):

- **Mallas:** copia de cada prenda en la pose de reposo, con subdivisión y
  grosor aplicados; se exporta con el nombre de la prenda (`Jacket`).
- **Armadura:** copia de la del avatar (`Armature_OpenSew`), con la misma
  transformación, recortada a los huesos con peso y sus padres; cada hueso
  lleva el sufijo `_OpenSew` (configurable en "Suffix"). La Jacket de Hanka
  sale con 14 huesos en vez de 169.
- **Ajustes FBX:** escala *FBX All*, −Z adelante, Y arriba, sin huesos hoja,
  sin animación, eje primario Y.
- **Jerarquía** (leída del FBX): `Armature_OpenSew → Hips_OpenSew → …` y la
  malla al mismo nivel que la armadura, como la ropa de Booth.

Dos fallos encontrados y corregidos al escribirlo:

- La transferencia de pesos crea un grupo por cada hueso del avatar, casi
  todos vacíos: se borran antes de decidir qué huesos se exportan.
- `bpy.ops.object.mode_set` ignora el objeto activo de un `temp_override` y
  no daba error: el recorte no se hacía. Ahora se activa el objeto de verdad
  y se comprueba el número de huesos.

## 3. Tests

`tests/test_export.py` cose, finaliza, exporta y vuelve a importar el FBX en
una escena vacía.

| Avatar / prenda | Huesos | Resultado |
|---|---|---|
| Cuerpo de serie (mujer) / T-Shirt | 14 | 16/16 ok |
| Hanka / Jacket | 14 | 16/16 ok |
| Mao / Hoodie | 19 | 16/16 ok |

Comprueba: una armadura con raíz en la cadera; sufijo en todos los huesos;
huesos donde los del avatar (0,00 mm); malla pesada a esa armadura; pesos
solo a sus huesos; todo vértice con peso, 1–4 influencias que suman 1; solo
huesos con peso y sus padres; la prenda donde estaba en Blender (0,00 mm);
al girar el brazo se mueve la manga.

## 4. Script de Unity

`unity/Assets/OpenSew/Editor/OpenSewOutfitInstaller.cs` (instrucciones en
`unity/README.md`). Busca Modular Avatar por reflexión y lilToon por el
nombre del shader: compila aunque falte alguno.

## Pendiente

- **Prueba en Unity:** proyecto de avatar nuevo con el SDK de VRChat,
  Modular Avatar, NDMF y lilToon; importar a Hanka; instalar la Jacket con
  el script; mirar en modo Play que la ropa sigue al cuerpo. No se pudo
  hacer el 2026-11-20: el Creator Companion no arrancaba en el PC y el SDK de
  avatares solo se descarga de los servidores de VRChat, bloqueados en la
  sesión de trabajo.

## Pesos robustos (2026-11-20)

Nuevo `clothing_design/weights.py`: una reimplementación en numpy de *Robust Skin Weights Transfer via Weight Inpainting* (Abdrashitov et al., 2023). Se basa en el paper, en el add-on GPL de sentfromspacevr y en la referencia MIT del autor, y no necesita scipy ni libigl. Cómo funciona:

- Copia los pesos del cuerpo solo donde la prenda está a menos de 5 cm y su normal difiere menos de 35° de la del cuerpo.
- El resto lo rellena con inpainting bi-laplaciano.

Va en Finalize con la opción **Weights**, que trae Robust por defecto; Nearest queda como alternativa.

| Avatar / prenda | Método | Salto p95 | Estiramiento p95 | Estiramiento máx | Aristas >20 % |
|---|---|---|---|---|---|
| Mujer / camiseta | Nearest | 0.115 | 27.0 % | 78 % | 346 |
| Mujer / camiseta | Robust | 0.104 | 24.4 % | 73 % | 321 |
| Hanka / chaqueta | Nearest | 0.140 | 14.4 % | 68 % | 213 |
| Hanka / chaqueta | Robust | 0.137 | 14.5 % | 61 % | 211 |

Cómo se midió: la pose es brazos 50° abajo con la columna doblada 25°. El salto es la diferencia de peso máxima entre los dos vértices de una arista.

La mejora es pequeña porque las mangas se siguen pesando a lo largo del brazo y después se suaviza. Los tests de exportación pasan con 0 fallos en mujer, Hanka y Mao, con un 79–85 % de vértices emparejados. Con Hanka tarda unos 18 s en esta máquina de 2 núcleos.
