# Fase 1: rigs de VRChat, reporte

Fecha: 2026-11-19 · Rama `fase-1` · Blender 5.2.4 (pruebas automáticas) y
Blender 5.2.0 en el PC de Allan (prueba con la interfaz)

## Resumen

El add-on ya reconoce los rigs humanoides de los avatares de Booth y mide,
cose, finaliza y anima con ellos. Probado con **Hanka, Mao, Minase y Vlau**:
los cuatro dan 17/17 partes del cuerpo y 8/8 extremidades, la T-Shirt y el
Jacket se quedan puestas, y tras Finalize la manga sigue al brazo. En la
Fase 0 la ropa se caía al suelo.

Manuka, Shinra y Shinano no están en el PC: revisé `E:\assets\DOWNLOADS`
(listado completo) y las carpetas de `E:\assets`. En su lugar probé con
**Minase** y con **Vlau** (ROKOSHOP, rig de origen Mixamo hecho en Maya).

## Qué se cambió

| Commit | Qué hace |
|---|---|
| `7fcb016` `7bcb82a` | `clothing_design/rig.py` (nuevo): normaliza el nombre entero del hueso |
| `c6694e7` `d64f871` | `avatar.py`: mide con las partes humanoides, la cabeza separada y elige bien el cuerpo |
| `4ac5a59` | `sim.py`: el test de caminar encuentra las piernas de Booth |
| `5c1711c` | Panel: cuello, huesos/extremidades reconocidos y cabeza medida |
| `b3f75d8` | No crear la pestaña sola al activar el add-on (cerraba Blender 5.2.0) |
| `01e47ec` | Finalize: las mangas toman los pesos de su brazo |
| `7949b62` `8e4505e` `0897dec` | Tests |

### 1. Nombres de huesos (`rig.py`)

En vez de alargar las listas de upstream, `rig.parse()` limpia el nombre y
solo acepta una coincidencia exacta:

- Quita namespaces y prefijos: `mixamorig:`, `Armature|`, `CC_Base_`,
  `DEF-`, `J_Bip_L_`, `Bip01 `.
- Saca el lado venga como venga: `_L`, `.L`, ` L`, `L_`, `Left `, `Left_`,
  `LeftUpperArm`, `UpperArmLeft`.
- Ignora espacios, puntos y guiones: `Upper Arm.L` = `UpperArm_L` = `Upperarm_L`.
- Reconoce Hips, Spine, Chest, UpperChest, Neck, Head, Shoulder, UpperArm,
  LowerArm/ForeArm, Hand, UpperLeg/UpLeg/Thigh, LowerLeg/Shin/Calf, Foot,
  Toe y los dedos.
- `Left_Arm` y `Left_Leg` (estilo Mixamo) se resuelven por la jerarquía: Arm
  es el brazo superior si el ForeArm cuelga de él; Leg es la espinilla si
  cuelga de un UpLeg.
- Rechaza los huesos que solo se parecen: `neckless` (Mao), `Spine.002outer_L`
  (Mao), `Waistbelt_Root` (Hanka), `IK.Foot.L` y los `W_` de ropa (Minase),
  los `Z_` y todos los twist, roll, end, MCH y ORG.
- Si dos huesos dan la misma parte (`Right Hand` y `Right Hand.001` en Mao),
  gana el más cercano a la raíz.

Las tablas de Mixamo, CC4 y Rigify se quedan como respaldo. Para Rigify se
ignora `spine` porque ahí es la pelvis.

Los vertex groups pasan por el mismo filtro (`rig.group_label`). Los twist
cuentan como parte de su miembro (`Left_Arm_Twist_00` → brazo superior), así
que no se cuelan en las secciones del torso. Sin eso, el pecho de Vlau medía
162 cm.

### 2. Cabeza separada

Hanka, Mao y Vlau traen la cabeza como malla aparte (por las blendshapes de
la cara). Si los vértices del cuerpo pesados a Head abarcan menos de 10 cm,
se busca la malla que pesa casi entera a la cabeza, el cuello o los ojos, y
se mide junto con el cuerpo. El pelo y los collares no entran.

### 3. Set Avatar

Antes elegía la malla más alta, y en Minase eso era el pelo. Ahora puntúa
por cuántas partes distintas del cuerpo cubre la malla.

### 4. Finalize con avatares en T-pose

Hallazgo de esta fase. Hanka, Mao y Minase vienen en T-pose: la manga cosida
cuelga **por debajo** del brazo horizontal, y la transferencia de pesos por
cercanía la ataba al costado del cuerpo. En Hanka la manga se movía **0 mm**
al levantar el brazo; en VRChat se habría quedado quieta. Ahora las piezas
ancladas a un brazo toman los pesos de ese brazo según su posición a lo largo
de él, mezclados en el codo y en la costura del hombro:

| Hanka, T-Shirt | Antes | Después |
|---|---|---|
| Hueso principal de la manga izquierda | Spine 123, Hips 69, Chest 25 verts | UpperArm_L 176, Chest 40 |
| Movimiento al levantar el brazo | 0 mm | 137 mm |

La manga gira con el brazo pero conserva la forma en que se drapeó (algo
colgada). Que envuelva bien el brazo en T-pose es de la Fase 2.

### 5. Cierre de Blender 5.2.0

Al activarse, el add-on original creaba su pestaña desde un temporizador
cambiando la ventana a "Layout". Eso cerró Blender en el PC de Allan
(`EXCEPTION_ACCESS_VIOLATION` en `ED_workspace_change`, según
`blender.crash.txt`). Ahora la pestaña se crea con su botón o desde el menú
de pestañas. La opción automática sigue en Preferencias, apagada.

## Resultados

### Pruebas automáticas (Blender 5.2.4, `tests/test_booth_avatars.py --drape`)

| | Hanka | Mao | Minase | Vlau |
|---|---|---|---|---|
| Malla del cuerpo | BodyAll + `Body` | body_b + `Body` | Body | M_Basebody + `M_Head` |
| Altura | 172,5 cm | 147,6 cm | 166,8 cm | 185,4 cm |
| Pecho / cintura / cadera | 86,3 / 61,8 / 77,2 | 60,5 / 51,2 / 77,7 | 85,5 / 57,5 / 75,9 | 115,2 / 82,7 / 96,5 |
| Cuello | 25,9 | 19,3 | 29,6 | 40,8 |
| Partes / extremidades | 17/17, 8/8 | 17/17, 8/8 | 17/17, 8/8 | 17/17, 8/8 |
| Test de caminar | ok | ok | ok | ok |
| T-Shirt puesta / dentro del cuerpo | 100 % / 0,4 % | 100 % / 0,2 % | 100 % / 0,2 % | 100 % / 0,4 % |
| Jacket puesta / dentro del cuerpo | 100 % / 0,6 % | 100 % / 0,1 % | 100 % / 0,1 % | 100 % / 0,1 % |
| Manga al levantar el brazo (mediana) | 54 mm | 43 mm | 89 mm | 116 mm |
| Torso al levantar el brazo | 0 mm | 0 mm | 0 mm | 0 mm |

72 comprobaciones, 0 fallos. Además:

- `tests/test_rig_names.py`: 145 casos de nombres (Booth, Mixamo, CC4,
  Rigify, VRM), 0 fallos. Corre con Python normal, sin Blender ni avatares.
- `tests/test_presets.py` de upstream: 0 fallos. Nora y Theo miden
  exactamente igual que antes del fork.

### En el Blender 5.2.0 de Allan (con la interfaz)

Hanka, con la versión final instalada desde `clothing_design_fase1.zip`
(con la figura forzada a "Woman" por error; ver la corrección más abajo):

- Set Avatar: BodyAll + Body, 172,5 cm, "Bones 17/17, limbs 8/8" en el panel.
- T-Shirt → Sew (botón del panel): cosida y puesta.
- Jacket → Sew → Finalize: atado al Armature, 1129 vértices de manga pesados
  al brazo. Al levantar `UpperArm_L` la mano sube 36 cm, la manga se mueve
  120 mm y el torso 0 mm. Se ve en pantalla.

La figura (Woman) y la prenda se pusieron desde la consola, porque el
desplegable no respondía a clics automáticos. Sew se pulsó en el panel.
Mao, Minase y Vlau solo se probaron en las pruebas automáticas.

## Pendiente (Fases 2 y 3)

- ~~**Figura:** Hanka se detecta como hombre.~~ **Corrección (Fase 2):** no
  era un fallo. Hanka, Minase y Vlau son avatares masculinos y Mao femenino,
  y el add-on acertó con los cuatro. Lo comprobé al dibujar los anillos de
  medida sobre los cuerpos. Forzar "Woman" en Hanka, como se hizo en esta
  fase en las pruebas y en el PC de Allan, fue un error mío.
- **T-pose:** las mangas cuelgan bajo el brazo en vez de envolverlo.
- **Cuellos anime:** Hanka 25,9 cm y Mao 19,3 cm, por debajo del rango
  "plausible" de upstream (28–45 cm).
- **Lapine** (`E:\assets\Lapine_Ver.1.10_A`) está en el PC pero no lo probé:
  hace falta dar acceso a esa carpeta.
- **Piernas:** el pesado por anclaje solo se hizo para las mangas; en las
  perneras sigue la transferencia por cercanía, que funciona porque cuelgan
  a lo largo de la pierna.
- **UpperChest** se reconoce pero no se usa como punto de medida: el pecho
  se sigue calculando por la sección más ancha de la malla, como en upstream.

## Cómo repetir las pruebas

```
python tests/test_rig_names.py

set CD_AVATARS=E:\...\Hanka.fbx;E:\...\mao.fbx;E:\...\Minase.fbx;E:\...\Vlau.fbx
blender -b --python tests/test_booth_avatars.py -- --drape
blender -b --python tests/test_presets.py
```

En la consola de Python de Blender:
`AV = "hanka"; PRENDA = "JACKET"; exec(open(r"C:\Users\romer\Downloads\opensew_fase1_avatar.py", encoding="utf-8").read())`
