# Fase 8 — comodidad de uso (en curso, 2026-11-23)

Rama `fase-8`, sobre `prueba-gotica` (lleva la capa y el corsé underbust). Los 7 puntos que propuso el advisor tras revisar el add-on como lo usaría Allan a mano.

## 1. Proteger lo cosido

- **Antes**: tocar Size, Subdivision, cualquier valor de una pieza o una casilla de costura rehacía la prenda desde las piezas planas (Live Sync), aunque estuviera cosida o terminada. Un clic tiraba una costura de 5 minutos y, en una prenda terminada, el enlace con el esqueleto.
- **Ahora**: una prenda cosida (`ob.cd.sewn`) o terminada (con Armature) no se rehace (`props._locked`, `build.is_locked`). El valor se guarda y se aplica en el siguiente Unsew. El panel lo dice con un candado: «Sewn: changes apply after Unsew».
- **La forma cosida queda en la malla**: al terminar Sew, la forma se copia a la malla (`sim.bake_shape`) y la caché de la tela empieza en ese fotograma (`sim.reset_cache`). Antes la prenda cosida solo existía en la caché, atada al fotograma: mover la línea de tiempo, tocar la tela o cerrar Blender la perdía. Ahora va en el .blend y Finalize la lee en cualquier fotograma.

## 2. Coser sin congelar Blender

- `CD_OT_sew` es ahora modal: cose unos fotogramas por cada tic de un temporizador y devuelve la ventana a Blender. Abajo muestra «Sewing T-Shirt: 40 % (frame 52 of about 130) - Esc to stop» y la barra de progreso del cursor. **Esc** para y avisa de pulsar Unsew.
- La costura entera es un generador (`_sew_steps`, `_stitch_steps`); desde un script (`bpy.ops.cd.sew()`) corre de un tirón, como antes, así que las pruebas automáticas no cambian.
- Las puntadas que quedan abiertas salen en el mensaje final, no solo en la consola (que en Windows no se ve).
- El botón viejo **Sew & Drape** ya no está en la interfaz (el operador sigue existiendo).
- Con prendas grandes Blender responde entre fotograma y fotograma (cada uno puede tardar 1–2 s en Hanka).

## 3. Cambiar o borrar una prenda, y Quick Sew

- Add Garment guarda en la prenda de qué preset salió y con qué Ease, Length y Sleeves (`ob.cd.preset`, `opt_*`).
- **Change…** reabre ese diálogo con los valores actuales y rehace la prenda con el mismo nombre y capa (sus costuras se sustituyen, no se suman). Vuelve sin coser.
- **Delete** borra piezas, costuras y prenda 3D, con confirmación.
- **Quick Sew**: el 45 % de los fotogramas de costura, el 30 % de los de asentar, la mitad de la calidad y sin el reintento a fuerza total. En la camiseta de la mujer integrada tarda unos 36 s. La prenda queda marcada; Finalize y el panel Steps avisan de coserla bien antes de vender.

## 4. Interfaz por pasos

- Panel **Steps** arriba: 1 Avatar, 2 Garment, 3 Sew, 4 Finalize, 5 Export, con el paso hecho, el que toca y lo que hay que pulsar.
- Lo avanzado va plegado y con «Advanced» en el nombre: dibujo y malla (subpanel de Patterns), colocación de piezas, costuras, tela y simulación.
- **Finalize All** termina todas las prendas cosidas.
- **Export Selected** exporta solo la prenda elegida (para venderla suelta); **Export All** sigue metiendo todas en un FBX. El panel recuerda copiar a Unity el json y las máscaras con el FBX.

## 5. Pose de brazos coherente

- Animate y Rest Pose devolvían los brazos arriba, y solo Set Avatar los bajaba: la siguiente prenda se dibujaba y cosía en otra pose.
- Ahora Add Garment, Change Garment y Sew los vuelven a bajar si *Lower Arms to Sew* está activado (`_ensure_lowered`), y si el avatar seguía caminando, paran el paseo antes. Probado en Hanka: tras Rest Pose, Add Garment los baja; tras Animate, Sew para el paseo y los deja bajados.

## 6. Guía al día

`docs/GUIA.md` reescrita con los nombres reales de la interfaz: las 15 prendas, el panel Steps, Quick Sew, Change/Delete, la protección de lo cosido, Hide Body Under It y Shrink Body, Export All/Selected y **los tres archivos que hay que copiar a Unity** (antes decía solo el FBX, y sin el json y las máscaras no se borra la piel), Export UV Layout para la plantilla de textura, el Menú de colores y el Tipo de tela del instalador, la licencia del avatar (VN3), una sección «Si algo sale mal» (Unsew en vez de Ctrl+Z) y un glosario inglés–español.

## 7. Encaje en Unity

- El instalador tiene **Tipo de tela**: Opaca (`lilToon`), Encaje recortado (`Hidden/lilToonCutout`, `_TransparentMode` 1, `_Cutoff` 0,5) o Transparente (`Hidden/lilToonTransparent`, modo 2). Los nombres de los shaders salen de lilToon 2.4.1 (`Shader/lts_cutout.shader`, `lts_trans.shader`).
- Si se reinstala con otro tipo, el material y los 5 de color cambian de shader sin perder lo que se les puso a mano.
- `Tools > OpenSew > Prueba Fase 8` (`unity/Tests/OpenSewPruebaFase8.cs`): instala el underbust de Manuka con los tres tipos. **0 fallos** (`docs/fase8_unity_log.txt`).

## Pruebas

- `tests/test_comfort.py` (nuevo, mujer integrada): Quick Sew, la prenda cosida no se rehace al tocar Size ni una pieza, la forma cosida sigue en el primer fotograma, Unsew, Change Garment (mismo nombre, sin copia, costuras sustituidas), Delete, Finalize All y Export Selected. **0 fallos.**
- Pose en Hanka: comprobada a mano con un script (arriba).
- `test_export`: HOODIE en Hanka y Manuka, PLEATED en Manuka y CAPE en Hanka, 0 fallos, con los mismos triángulos que antes. Los vértices de piel ocultos varían unos pocos de una ejecución a otra con el mismo código (2.583–2.594 en la sudadera de Hanka).
- `test_presets`: solo los 12 fallos de la falda de volantes que ya había.
- Paneles y diálogos dibujados sin errores en todos los estados (sin prenda, con avatar, prenda, cosida y terminada), con una maqueta del layout.

**Sin probar todavía**: el modo modal de Sew con la ventana de Blender (no se puede sin interfaz), y el uso a mano de punta a punta. El advisor propuso que Allan haga una prenda siguiendo la guía y apunte dónde se atasca.
