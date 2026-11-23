# Fase 7 — ocultar el cuerpo y colores (2026-11-22; Hanka y Manuka)

Rama `fase-7`. De la lista del advisor: formas para esconder el cuerpo bajo la ropa, variantes de color y más controles al elegir la prenda.

## 1. Ocultar el cuerpo bajo la prenda

`clothing_design/shrink.py`.

**Qué piel está tapada:** desde cada vértice del cuerpo se lanza un rayo hacia fuera, contra la prenda.
- Está **tapado** si hay tela delante, de 4 cm por dentro de la piel a 15 cm por fuera, mirando hacia el mismo lado.
- Está **oculto para siempre** si, además, la tela que lo tapa está a más de 3,5 cm de cualquier borde (bajo, puños, escote, cara) y a **no más de 4 cm** de la piel (`HIDE_GAP`).
- El grosor de la prenda se quita al medir, porque si no cierra los bordes.
- Los 15 cm sirven para el shape key, porque una sudadera cuelga de 8 a 10 cm separada de la parte baja de la espalda de Hanka. Para la máscara no: con tela tan suelta, al agacharse o sentarse se vería por debajo un hueco donde estaba la piel. Por eso la máscara solo borra piel con la tela pegada (4 cm), y la parte suelta se tapa con el shape key o se deja.

**Dos salidas:**
- **Shape key `Shrink_<prenda>`** en el cuerpo (botón junto a «Hide Body Under It», en Finalize). Mete la piel tapada detrás de la tela, con 4 mm de holgura y como mucho 3 cm. Sirve para tu propio avatar o para previsualizar, no se vende.
- **Máscara para Unity:** al exportar, junto al FBX salen:
  - `<fbx>_mask_<n>.png`, negra donde la piel queda oculta, en las UV del cuerpo;
  - `<fbx>.opensew.json`, con el nombre del cuerpo y sus materiales.

  Solo viaja la máscara: el cuerpo del avatar es obra de otra persona y nunca se exporta.

**En Unity:** el instalador añade **MA Mesh Cutter** en un hijo de la prenda (`OpenSew_OcultarCuerpo`).
- *Object* apunta al cuerpo del avatar, con un *Vertex Filter – By Mask* por material: borrar negro, solo polígonos con todas sus esquinas dentro.
- Es un componente reactivo de Modular Avatar. Existe desde la 1.14, pero hasta la **1.19** no funcionaba en VRChat si se activaba por menú, así que el LEEME pide la 1.19 o más nueva. Es reactivo: borra esa piel al compilar el avatar, y solo si la prenda está puesta.
- El empaquetador incluye la máscara.
- La máscara se dibuja en el primer mapa UV del cuerpo (el `uv0` de Unity), y las UV fuera de 0..1 se envuelven. El json guarda qué mapa se usó.
- Si algo falla al montar el Mesh Cutter o el menú (otra versión de MA, campos cambiados), el instalador borra lo que dejó a medias y lo avisa en el informe: la ropa queda instalada sin esa parte.

## 2. Menú de colores

El instalador añade el submenú «Color <prenda>» al menú del avatar (opción «Menú de colores», activada por defecto):
- Un toggle exclusivo por color: Original (por defecto), Negro, Vino, Morado, Azul noche y Blanco.
- Cada toggle lleva un **MA Material Setter** con una copia teñida del material lilToon (color y sombra).
- Un solo parámetro entero `OpenSew/<prenda>/Color`, sincronizado y guardado.

## 3. Largo y mangas al añadir la prenda

El diálogo **Add Garment** tiene dos controles nuevos (`library.LENGTH_OPTIONS`, `library.preset_kwargs`). Solo aparecen en las prendas donde tienen sentido, y debajo del largo sale qué significa en esa prenda.

**Length** (largo): Short, Regular o Long. Regular es la prenda tal cual estaba, así que los patrones por defecto no cambian (comprobado comparando los 13 presets en Hanka y Manuka contra la versión anterior; solo cambia la falda lisa, ver abajo).

| Prenda | Short | Long |
|---|---|---|
| Camiseta, tirantes, sudadera | corta a la cintura | túnica a medio muslo |
| Chaqueta | a la cintura | a medio muslo |
| Abrigo, vestido | medio muslo | media pantorrilla |
| Pantalón, mono | short a medio muslo | a la rodilla (Regular es largo entero) |
| Faldas (lisa, pliegues, volantes) | mini (×0,70–0,75) | bajo la rodilla (×1,35–1,45) |

- Medio muslo y media pantorrilla son dos alturas nuevas, entre la entrepierna y la rodilla y entre la rodilla y el tobillo.
- En el short y a la rodilla, el bajo de la pierna se corta al contorno del muslo donde acaba, con un 25 % de vuelo (`SHORTS_FLARE`, en `_leg_hem`, común al pantalón y al mono). Cortado al tobillo, como el largo entero, quedaba más estrecho que el muslo (0,5 a 0,8 veces en el mono, según el advisor).

**Sleeves** (mangas): Regular, None, Short, Elbow o Long, en camiseta, mono, vestido, chaqueta, abrigo y sudadera.
- Se miden en el brazo del avatar: Short es el 28 % del brazo, Elbow el 55 % y Long la manga larga de siempre. Así valen igual en Manuka (brazo de 36 cm) que en Hanka.
- None (sin mangas) solo existe en el vestido; en las demás prendas se ignora y el diálogo lo avisa.
- La manga al codo se corta recta (`ELBOW_HEM`), solo cuando se elige Elbow. Estrechada hacia el bajo, como la larga, apretaba en el codo y se subía hasta la axila (la chaqueta de Manuka). Las mangas Regular no cambian, tampoco en avatares de brazo corto: se comprobó con los brazos a 0,7 veces en Hanka, Manuka, la mujer y el hombre.

**Arreglo de paso, la falda lisa.** En Manuka (cintura de 39 cm, cadera de 63 cm), la falda lisa medía 49 cm de contorno a la altura de la cadera y la costura de un lado no podía cerrar: quedaba abierta 14 cm. Ahora, si la cadera es más ancha que la línea recta del costado, el costado se curva hasta la cadera (`SKIRT_HIP_EASE`) y el bajo es al menos así de ancho. Después del arreglo, al terminar de coser no queda ninguna puntada abierta más de 4,5 cm (el «Max Stitch Gap»), ni en Regular ni en Long. En Hanka y en la mujer integrada también cambia un poco el patrón; `test_export` pasa en los tres.

**Pruebas** (`CD_LENGTH` y `CD_SLEEVES` en `tests/test_export.py`):
- Se dibujaron sin simular todas las combinaciones de las 13 prendas en Hanka y Manuka: ningún error.
- Se simularon unas 25 combinaciones en los dos avatares, entre ellas el mono Short y a la rodilla (`docs/img/fase7_largos_mangas_hanka.jpg`, solo Hanka). `test_export` pasa con la falda lisa (Hanka, Manuka y mujer) y con la chaqueta Short + Elbow y el mono Short en Manuka, y con el short en Hanka; el log ahora dice qué largo y mangas se usaron.
- Comparando con la versión anterior, en Regular solo cambia la falda lisa, en los 4 cuerpos (Hanka, Manuka, mujer y hombre) y también con los brazos acortados.

**Fallan en Manuka y quedan pendientes** (también en la GUIA, en Limitaciones):
- **Sudadera con manga al codo**: las mangas se suben y quedan abiertas por debajo. En Hanka sale bien, y en Manuka salen bien la sudadera con manga corta y la chaqueta al codo.
- **Camiseta Long + Long** (túnica con manga larga): queda abierta la costura bajo el antebrazo izquierdo, unos 18 cm. Por separado (Regular + Long, o Long en Hanka) cierra.

## Prueba en Unity (Hanka)

Cifras con `HIDE_GAP` (la máscara ya no borra piel bajo tela suelta).

`Tools > OpenSew > Prueba Fase 7`, log en `docs/fase7_unity_log.txt`. Todo pasa con la sudadera y la falda de pliegues:

| | Hoodie | Pleated |
|---|---|---|
| Vértices del cuerpo ocultos (de 8.985) | 2.583 | 768 |
| Triángulos del cuerpo en Play (antes 17.946) | 13.198 | 16.617 |
| Curvas de material en el FX de VRChat | 11 (5 de 5 colores) | 11 (5 de 5 colores) |
| Parámetro | Int, saved, synced | Int, saved, synced |

- El paquete para vender lleva FBX, material, prefab, máscara y los 5 materiales de color.
- Además de quitar la piel que asomaba, borrar ese cuerpo ahorra triángulos al avatar.

Capturas:
- `docs/img/fase7_cuerpo_oculto_hanka.jpg`: con la prenda, el cuerpo sin la prenda y en pose.
- `docs/img/fase7_colores_hanka.jpg`: cada color.

## Manuka (segundo avatar)

`MANUKA.fbx` de la carpeta de Allan, y su paquete importado al proyecto de prueba (`Tools > OpenSew > Importar Manuka`). Es una figura anime de 1,24 m con cintura de 39 cm y cadera de 63 cm.

**Arreglos que hicieron falta:**
- **Largo de las faldas**, en `library._len_scale`. Los largos (falda, canesú, pisos, volantes) estaban en metros para un cuerpo de 1,65 m; ahora escalan con la altura, entre 0,6 y 1,25 veces. A Manuka la falda de pliegues le llegaba a la rodilla y colgaba como una tienda.
- **Ancho de los pliegues**, con `PLEAT_MIN_FACE` = 3,6 cm, que son dos aristas de la malla. Con diez pliegues sobre su cintura, cada cara medía 2,5 cm, algunas costuras canesú/pliegue tenían menos de dos puntos y se saltaban, y la falda se caía hasta los muslos. Ahora salen 6 pliegues en Manuka y 10 en Hanka.
- **Nombre de la shape key:** pasa a llamarse `OpenSew_Shrink_<prenda>`. Manuka ya trae sus propias shape keys `Shrink_*` (Shrink_Shoulder, Shrink_Hips…) y el prefijo evita confundirlas.

**test_export:** 0 fallos con Hoodie, Corset, Pleated y Tiered (`docs/fase7_test_export/`).

| Prenda | Triángulos | Vértices del cuerpo ocultos (de 15.064) |
|---|---|---|
| Hoodie | 2.477 | 4.761 |
| Corset | 522 | 797 |
| Pleated | 2.326 | 1.082 |
| Tiered | 3.680 | 1.049 |

**Unity:** las 4 prendas de Manuka pasan, junto con las 2 de Hanka; 6 de 6 y 0 fallos.
- La prenda se instala con el prefab lilToon de Manuka, y los huesos se fusionan.
- El cuerpo pierde piel bajo la prenda: de 30.106 triángulos a 20.813 con la sudadera, 28.656 con el corsé, 28.178 con la falda de pliegues y 28.391 con la de volantes.
- El menú de colores funciona: 5 de 5 colores en el FX y parámetro sincronizado.
- La capucha sigue a la cabeza y las faldas siguen al muslo.

Las capturas de Manuka se guardan en el PC (`Logs/fase7/`), no en el repo, porque muestran el cuerpo base del avatar.

## Prueba del comprador

`Tools > OpenSew > Prueba comprador` (`unity/Tests/OpenSewPruebaComprador.cs`) hace lo que haría alguien que compra la prenda, sin el instalador: arrastra `Manuka_HOODIE_MA.prefab` sobre el prefab lilToon de Manuka y entra en Play.
- Con el cuerpo con su nombre original: la piel se borra (30.106 → 20.318 triángulos con la máscara anterior a `HIDE_GAP`; 20.813 con la actual) y la ropa se une al esqueleto.
- Con el cuerpo renombrado a `Mi_cuerpo`: no hay errores, la piel queda entera y la ropa se une igual. El LEEME del paquete dice cómo se llama el cuerpo que espera y cómo apuntar *Object* al cuerpo renombrado.

## Licencias de los avatares

Antes de vender ropa hecha para Manuka (u otro avatar de Booth), hay que leer sus términos (VN3 u otros). Hay que comprobar si permiten vender ropa hecha para el avatar y con qué condiciones. El paquete de OpenSew no incluye ni malla, ni texturas, ni materiales del cuerpo, solo la máscara en blanco y negro. Aun así, la decisión es de Allan según la licencia de cada avatar.

## Limitaciones

- Si el cuerpo del avatar comparte UVs entre izquierda y derecha (UVs espejadas), una prenda asimétrica ocultaría los dos lados. Los presets son simétricos.
- La piel justo al lado de un bajo (3,5 cm) se conserva para que no se vea un hueco al moverse. Si en una pose extrema asoma piel ahí, se puede bajar `EDGE_MARGIN`.
- Hanka trae los calzoncillos como malla aparte: no se tocan.

## Pendiente de la Fase 7

- Las dos combinaciones de largo y mangas que fallan en Manuka (arriba).
- Probar más avatares: Allan no tiene los modelos de Mao, Vlau y Minase.
