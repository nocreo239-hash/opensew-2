# Fase 6 — que el add-on se pueda usar y vender (2026-11-22)

Rama `fase-6`. Son los cinco puntos que el advisor marcó para poder hacer y vender una prenda para Hanka.

## 1. UVs

Lo hace `build.uv_layout` y lo comprueba `tests/test_export.py`. Cada prenda sale con dos mapas UV:
- **UVMap**, el primero, que es el `uv0` de Unity: las piezas del patrón tal cual, sin estirar, todas a la misma escala y empaquetadas en 0–1 sin solaparse (`docs/img/fase6_uvmap_hoodie.png`).
- **Fabric**: el patrón en metros, para telas que se repiten.

En Unity, con una textura de cuadros (`docs/img/fase6_uv_hanka.jpg`), los cuadros salen enteros y sin deformar en la sudadera y en la falda de pliegues.

## 2. Triángulos

- **Exportación por defecto**: sin subdivisión ni grosor, en `export_subdiv` y `export_thickness`.
- **Panel Finalize**: muestra los triángulos que tendrá la exportación.
- **Instalador**: dibuja la tela a doble cara.

Triángulos por prenda:

| Prenda | Antes (subdiv 1 + grosor) | Ahora |
|---|---|---|
| T-Shirt (mujer) | 33.120 | 4.068 |
| Hoodie (Hanka) | — | 6.419 |
| Pleated (Hanka) | — | 3.988 |

Referencia de VRChat (creators.vrchat.com): en PC, un avatar entero es Excellent hasta 32.000 triángulos y Good hasta 70.000. El SDK avisa a partir de 70.000 en PC y 20.000 en Quest.

## 3. Add-on instalable

- **`clothing_design/blender_manifest.toml`**: el add-on es una extensión de Blender 5.2 llamada «OpenSew 2 - VRChat», GPL-3.0-or-later, con los dos autores en el copyright.
- **`tools/build_zip.py`**: genera `dist/opensew2_vrchat-1.1.0.zip`.
- **Probado**: se instala con `extensions.package_install_files` en un Blender limpio, y después importa la mujer y crea una camiseta.

## 4. Empaquetar para vender

- **`unity/Assets/OpenSew/Editor/OpenSewPackager.cs`** (menú **Tools > OpenSew > Empaquetar para vender**): exporta en un `.unitypackage` el prefab `_MA`, el FBX, el material y las texturas, con un `LEEME` de requisitos en español y en inglés. No incluye lilToon, Modular Avatar, el SDK ni el avatar.
- **`tools/build_unitypackage.py`**: empaqueta las herramientas de Unity en `dist/OpenSew_Unity_Tools-1.1.0.unitypackage`. Usa los GUID de los `.meta`, así que al reimportar actualiza los scripts en su sitio.
  - Formato, comparado con los paquetes que exporta el propio Unity: cabeceras GNU y exactamente dos bloques de ceros al final.
  - Si se rellena el tar hasta el registro habitual de 10 KiB, Unity dice que lo importó pero no importa nada. Lo comprobamos en este proyecto.
- **Material**: cada prenda exportada lleva su propio material con su nombre, en lugar de `CD_Fabric`.

## 5. Guía

`docs/GUIA.md`, en español: instalar, hacer la prenda, exportar, instalar en el avatar, empaquetar, licencia y limitaciones.

## Prueba en Unity (Hanka)

`Tools > OpenSew > Prueba Fase 6` (`unity/Tests/OpenSewPruebaFase6.cs`). Log en `docs/fase6_unity_log.txt`. Todo pasa, con la sudadera y la falda de pliegues:
- El paquete de herramientas se importa sin diálogo, conserva los GUID y no duplica el instalador.
- La prenda se instala.
- UVs en `uv0` dentro de 0–1, y segundo mapa presente.
- Triángulos: 6.419 la sudadera y 3.988 la falda.
- Paquete para vender: 315 KB y 220 KB, con FBX, material, prefab, textura y LEEME, y sin avisos.
- En Play, los huesos se fusionan y la capucha y la falda siguen a la cabeza y al muslo.

## Queda (de la lista del advisor)

- **Importante**:
  - variantes de color;
  - otros avatares (Manuka, Shinra, Shinano);
  - shape keys para encoger el cuerpo;
  - más controles al elegir prenda.
- **Deseable**:
  - PhysBones;
  - interruptor en el menú del avatar.
