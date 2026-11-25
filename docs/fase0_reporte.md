# Fase 0: reporte de prueba con Hanka

Fecha: 2026-11-19 · Blender 5.2.4 LTS · OpenSew 2 `86b4322` (main de upstream)
Avatar: 斑霞 Hanka Ver1.2, `FBX/Hanka.fbx`
Script reproducible: `tools/fase0_test.py`

## Resumen

El add-on se instala y todos los operadores terminan sin error (Set Avatar, Add Garment,
Sew, Finalize), **pero con Hanka el resultado no sirve**: la T-Shirt y el Jacket se caen
del cuerpo durante el asentado y acaban más de 2 m por debajo del suelo. Con el avatar
incluido (Nora) todo funciona, así que la instalación y el flujo están bien. El fallo
está en cómo lee a Hanka.

Hay tres causas, en orden de importancia. Las dos primeras están confirmadas con un
experimento: parcheando nombres de huesos y uniendo la cabeza, la ropa se queda puesta.

## Lo que funcionó

| Paso | Resultado |
|---|---|
| Empaquetar `clothing_design` como zip e instalar (*Install from Disk*) | OK |
| Importar `Hanka.fbx` | OK: 16 mallas, 1 armature con 169 huesos |
| Set Avatar | Elige `BodyAll` (el cuerpo con 55 vertex groups), orientación `-Y` correcta |
| Base con Nora (avatar del add-on) | T-Shirt: 4 piezas, 10 costuras, Sew 51 s, 0,4 % de vértices dentro del cuerpo. Jacket: 5 piezas, 11 costuras, Sew 90 s, 0,3 %. Finalize ata al rig en ambos |
| Finalize con Hanka | Termina, transfiere pesos y pone Armature → Subsurf → Solidify. Pero ata una prenda que ya se cayó |

## Medidas que lee de Hanka (sin modificar)

| Medida | Valor | Comentario |
|---|---|---|
| Altura | **154,1 cm** | Incorrecta. La cabeza es otra malla (`Body`); con ella son ~172,5 cm |
| Pecho | 74,1 cm | |
| Cintura | 61,5 cm | |
| Cadera | 75,8 cm | |
| Cuello | 26,1 cm | Cuello anime fino; queda fuera del rango que el test de upstream considera plausible (28–45) |
| Figura | WOMAN (score −0,59) | Por poco. Con la cabeza unida pasa a **MAN** |
| Rig | **Parcial** | Tronco sí (Hips, Chest, Neck); brazos y piernas no (0 de 8 cadenas) |

Huesos que encontró: `neck → Neck`, `chest → Chest`, `hip → Hips`, y
`waist → Waistbelt_Root`, que está **mal**: es un hueso del cinturón y lo eligió porque
contiene "waist". Lo salva que la cintura se recalcula después por la sección más
estrecha.

## Lo que falló y por qué

### 1. No reconoce los huesos de brazos y piernas (causa principal de la caída)

Hanka usa nombres tipo Unity Humanoid con sufijo: `UpperArm_L`, `LowerArm_L`,
`Hand_L`, `UpperLeg_L`, `LowerLeg_L`, `Foot_L`. Las tablas solo conocen CC4, Mixamo
y Rigify (`upper_arm.l`, `forearm.l`, `thigh.l`, `shin.l`...).

Consecuencia: sin cadenas de brazo no hay medida del hombro, y el add-on lo adivina
por proporción (81,8 % de la altura). Con la altura sin cabeza, el hombro queda en
z = 1,279 m cuando el real está en 1,413 m: **13 cm más bajo**. La camiseta se
patrona y se cuelga por debajo de los hombros. El alfiler de hombros la sostiene
mientras cose, pero en cuanto se suelta (gravedad completa, tras el soldado) queda como
un tubo sin nada de qué colgar y cae libre: z 1,12 m en el fotograma 30 → −2,25 m en
el 75.

Código responsable:
- `clothing_design/avatar.py:22` `BONE_TABLE` (tronco; la búsqueda por subcadena es la que elige `Waistbelt_Root`)
- `clothing_design/avatar.py:30` `LIMB_CHAINS` (brazos y piernas)
- `clothing_design/avatar.py:57` `LIMB_GROUPS` (qué vertex groups son de cada miembro)
- `clothing_design/avatar.py:52` `EXCLUDE_TORSO`: no excluye `LowerArm` ni los dedos `*Proximal/Intermediate/Distal`, así que pueden colarse en las secciones del torso
- `clothing_design/avatar.py:526` el hombro sale de `arm_l`; sin él, `z_of()` (`avatar.py:407`) usa `PROPORTIONS` (`avatar.py:16`)
- `clothing_design/avatar.py:116` `_find_bone`: coincidencia exacta y luego subcadena, primer acierto gana
- `clothing_design/sim.py:866` `WALK_BONES`: la animación de caminar tiene **su propia** tabla de huesos y también habrá que adaptarla
- `clothing_design/ops.py:1035` donde se suelta el alfiler y empieza el asentado con gravedad completa

### 2. La cabeza es una malla separada

`BodyAll` llega solo hasta el cuello (z 0,018–1,559) y la cabeza es `Body`
(z 1,531–1,743). Set Avatar mide una sola malla, así que la estatura, y con ella todos
los puntos de respaldo por proporción, salen ~18 cm cortos. Es habitual en avatares de
Booth: el cuerpo y la cabeza vienen separados por las blendshapes de la cara.

Código: `clothing_design/avatar.py:595` `auto_avatar` y `measure()` (`avatar.py:479`),
que trabajan con un solo objeto.

### 3. Hanka viene en T-pose

Con los huesos parcheados la ropa se queda puesta, pero las mangas cuelgan por debajo
de los brazos horizontales y una manga del Jacket se sale (ver renders del experimento).
El README dice que los avatares incluidos tienen los brazos a 60° y que el drapeado
sale "notablemente más limpio con los brazos separados del torso"; `tests/test_presets.py`
comprueba brazos a más de 45° desde la vertical. Hanka está a ~90°.

Esto es una **observación, no una causa probada**: no he aislado si es la pose o la
colocación de las mangas. Lo más barato sería probar Hanka en A-pose (girar los
UpperArm en pose mode antes de Set Avatar).

## Experimento de confirmación (NO es Fase 1, no está en el commit)

Parcheé en memoria (`LIMB_CHAINS`, `LIMB_GROUPS`, `EXCLUDE_TORSO`, cintura → `Spine`)
y uní `Body` a `BodyAll`, quitando la ropa original de Hanka:

| | Sin parche | Con parche + cabeza |
|---|---|---|
| Altura | 154,1 cm | 172,5 cm |
| Pecho / cintura / cadera | 74,1 / 61,5 / 75,8 | 86,3 / 61,8 / 77,2 |
| Cadenas de miembros | 0 de 8 | 8 de 8 |
| Hombro (z) | 1,279 (adivinado) | 1,413 (del hueso) |
| T-Shirt tras Sew | se cae a −2,2 m | se queda puesta (z 0,99–1,50) |
| Jacket tras Sew | se cae | se queda puesta (z 0,98–1,50) |

Nuevo problema que aparece al corregir: con la estatura real, la figura se detecta
como **MAN** (cadera/pecho de anime). Eso es materia de la Fase 2 (proporciones anime);
mientras tanto se puede forzar *Figure = Woman* a mano.

## Recomendación para la Fase 1

1. Añadir nombres Unity Humanoid / Booth (`UpperArm`, `LowerArm`, `UpperLeg`,
   `LowerLeg`, `Hand`, `Foot`, con `_L/_R`, `.L/.R`, `Left/Right` y prefijos) a
   `LIMB_CHAINS`, `LIMB_GROUPS`, `EXCLUDE_TORSO`, `BONE_TABLE` y `WALK_BONES`.
   Mejor normalizar el nombre una vez (quitar prefijos, unificar el lado) que hacer
   crecer las listas.
2. Hacer que `_find_bone` no acepte subcadenas peligrosas (`waist` → `Waistbelt_Root`).
3. Incluir la cabeza: medir el conjunto de mallas que deforma el mismo armature
   (o dejar elegir varias). Es casi obligatorio para Booth.
4. Añadir un test headless con Hanka al estilo `tests/test_presets.py`. El FBX no se
   puede subir al repo (licencia de Booth), así que el test tiene que leer la ruta de
   una variable de entorno.

## Cómo se ejecutó

Blender 5.2.4 como módulo Python (`pip install bpy==5.2.4`), sin interfaz, en un
entorno Linux. Es el mismo Blender, pero conviene repetir la prueba en tu Blender 5.2
de Windows antes de dar la Fase 0 por cerrada:

```
blender -b --python tools/fase0_test.py -- "E:\assets\DOWNLOADS\Hanka\斑霞-Hanka-Ver1.2\斑霞-Hanka-Ver1.2\FBX\Hanka.fbx" fase0_out
```
