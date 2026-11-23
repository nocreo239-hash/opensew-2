# Fase 8 — comodidad de uso (2026-11-23)

Rama `fase-8`, sobre `prueba-gotica` (lleva la capa y el corsé underbust). Los 7 puntos que propuso el advisor tras revisar el add-on como lo usaría Allan a mano.

## 1. Proteger lo cosido

- **Antes**: tocar Size, Subdivision, cualquier valor de una pieza o una casilla de costura rehacía la prenda desde las piezas planas (Live Sync), aunque estuviera cosida o terminada. Un clic tiraba una costura de 5 minutos y, en una prenda terminada, el enlace con el esqueleto.
- **Ahora**: una prenda cosida (`ob.cd.sewn`) o terminada (con Armature) no se rehace (`props._locked`, `build.is_locked`). El valor se guarda y se aplica en el siguiente Unsew. El panel lo dice con un candado: «Sewn: changes apply after Unsew».
- **La forma cosida queda en la malla y congelada**: al terminar Sew, la forma se copia a la malla y se quita el simulador (`sim.freeze_garment`, lo mismo que ya hacía Add Outfit con sus capas). Antes la prenda cosida solo existía en la caché, atada al fotograma: mover la línea de tiempo la perdía. La primera versión de esta fase dejaba el simulador puesto sobre la forma copiada, y el advisor midió que así la tela se volvía a encoger un 5 % cada vez que seguía simulando y que un salto en la línea de tiempo la reventaba (300–590 mm). Congelada, se queda quieta en cualquier fotograma (también las capas de dentro mientras se cose otra) y sigue chocando. Settle, Relax y Grab le vuelven a poner simulador cuando se les pide.
- De paso: **Settle** y **Grab** no reiniciaban el simulador al ponerlo de nuevo en una prenda congelada (`kick_solver`), y la prenda explotaba (24 m en la prueba). Pasaba ya con las capas de Add Outfit.
- **Sew sobre una prenda ya cosida o terminada** la descose primero, como Unsew: antes seguía desde la forma soldada (Sew después de Quick Sew no recosía y borraba el aviso) y, en una prenda terminada, aplicaba dos veces la deformación del esqueleto.

## 2. Coser sin congelar Blender

- `CD_OT_sew` es ahora modal: cose unos fotogramas por cada tic de un temporizador y devuelve la ventana a Blender. Abajo muestra «Sewing T-Shirt: 40 % (frame 52 of about 130) - Esc to stop» y la barra de progreso del cursor. **Esc** para y avisa de pulsar Unsew; al parar se quitan los alfileres y la gravedad baja de la costura.
- Mientras cose solo pasan los eventos de mover la vista. Todo lo demás (un slider, Ctrl+Z, otro Sew, Delete, la línea de tiempo) se ignora, los demás botones de prendas quedan en gris (`sewing()` en sus `poll`) y los live updates no rehacen nada. Si Blender corta el modal desde fuera (abrir otro archivo), `cancel` limpia el temporizador, el progreso y el texto.
- La costura entera es un generador (`_sew_steps`, `_stitch_steps`); desde un script (`bpy.ops.cd.sew()`) corre de un tirón, como antes, así que las pruebas automáticas no cambian.
- Las puntadas que quedan abiertas salen en el mensaje final, no solo en la consola (que en Windows no se ve).
- El botón viejo **Sew & Drape** ya no está en la interfaz (el operador sigue existiendo).
- Con prendas grandes Blender responde entre fotograma y fotograma (cada uno puede tardar 1–2 s en Hanka).

## 3. Cambiar o borrar una prenda, y Quick Sew

- Add Garment guarda en la prenda de qué preset salió y con qué Ease, Length y Sleeves (`ob.cd.preset`, `opt_*`).
- **Change…** reabre ese diálogo con los valores actuales y rehace la prenda con el mismo nombre y capa (sus costuras se sustituyen, no se suman). Vuelve sin coser.
- **Delete** borra piezas, costuras y prenda 3D, con una confirmación que dice el nombre, y deja elegida en la lista la prenda que queda.
- **Quick Sew**: el 45 % de los fotogramas de costura, el 30 % de los de asentar, la mitad de la calidad durante la costura (al soldar vuelve a la normal) y sin el reintento a fuerza total; los fotogramas extra para cerrar puntadas se mantienen enteros, para no juzgar el ajuste con costuras abiertas. En la camiseta de la mujer integrada tarda unos 40 s. La prenda queda marcada; Finalize y el panel Steps avisan de coserla bien antes de vender, y pulsar Sew la recose desde las piezas planas.

## 4. Interfaz por pasos

- Panel **Steps** arriba: 1 Avatar, 2 Garment, 3 Sew, 4 Finalize, 5 Export, con el paso hecho, el que toca y lo que hay que pulsar.
- Lo avanzado va plegado y con «Advanced» en el nombre: dibujo y malla (subpanel de Patterns), colocación de piezas, costuras, tela y simulación.
- **Finalize All** termina todas las prendas cosidas.
- **Export Selected** exporta solo la prenda elegida (para venderla suelta), y propone siempre el nombre de la prenda para no pisar el FBX del conjunto; **Export All** sigue metiendo todas en un FBX. El panel recuerda copiar a Unity el json y las máscaras con el FBX.

## 5. Pose de brazos coherente

- Animate y Rest Pose devolvían los brazos arriba, y solo Set Avatar los bajaba: la siguiente prenda se dibujaba y cosía en otra pose.
- Ahora Add Garment, Change Garment y Sew los vuelven a bajar si *Lower Arms to Sew* está activado (`_ensure_lowered`). Si el avatar seguía caminando, paran el paseo antes, también con Lower Arms apagado. Probado en Hanka: tras Rest Pose, Add Garment los baja; tras Animate, Sew para el paseo y los deja bajados.

## 6. Guía al día

`docs/GUIA.md` reescrita con los nombres reales de la interfaz: las 15 prendas, el panel Steps, Quick Sew, Change/Delete, la protección de lo cosido, Hide Body Under It y Shrink Body, Export All/Selected y **los tres archivos que hay que copiar a Unity** (antes decía solo el FBX, y sin el json y las máscaras no se borra la piel), Export UV Layout para la plantilla de textura, el Menú de colores y el Tipo de tela del instalador, la licencia del avatar (VN3), una sección «Si algo sale mal» (Unsew en vez de Ctrl+Z) y un glosario inglés–español.

## 7. Encaje en Unity

- El instalador tiene **Tipo de tela**: Opaca (`lilToon`), Encaje recortado (`Hidden/lilToonCutout`, `_TransparentMode` 1, `_Cutoff` 0,5) o Transparente (`Hidden/lilToonTransparent`, modo 2). Los nombres de los shaders salen de lilToon 2.4.1 (`Shader/lts_cutout.shader`, `lts_trans.shader`).
- El modo se pone como lo hace el inspector de lilToon (`lilMaterialUtils.SetupMaterialWithRenderingMode`): shader, `_TransparentMode`, `_SrcBlend`/`_DstBlend` (transparente mezcla con 1/10), `_AlphaToMask` (1 en encaje) y la cola del shader (2000 / 2450 / 2460). Cambiar solo el shader, como en la primera versión, dejaba una tela «transparente» que se veía opaca (lo vio el advisor).
- Si se reinstala con otro tipo, el material y los 5 de color cambian de modo y conservan colores y texturas. Un material con otra variante de lilToon elegida a mano no se toca. La ventana empieza con el tipo que ya tenía la prenda, para que reinstalar por otro motivo no vuelva opaco un encaje.
- `Tools > OpenSew > Prueba Fase 8` (`unity/Tests/OpenSewPruebaFase8.cs`): instala el underbust de Manuka como encaje, luego transparente y luego opaca, y comprueba shader, modo, mezcla, alfa a máscara, cola, los 5 colores y que la ventana recuerde el tipo. **0 fallos** (`docs/fase8_unity_log.txt`).

## Pruebas

- `tests/test_comfort.py` (nuevo, mujer integrada): Quick Sew; la prenda cosida no se rehace al tocar Size ni una pieza; queda congelada, igual en el primer fotograma y 200 más adelante; Settle la mueve poco (15 mm) y no la encoge; Sew después de Quick Sew recose desde las piezas planas; Unsew, Change Garment (mismo nombre, sin copia, costuras sustituidas), Delete, Finalize All y Export Selected. **0 fallos.**
- Pose en Hanka: comprobada a mano con un script (arriba).
- `test_export`: HOODIE en Hanka y Manuka, PLEATED en Manuka y CAPE en Hanka, 0 fallos, con los mismos triángulos que antes. Los vértices de piel ocultos varían unos pocos de una ejecución a otra con el mismo código (2.583–2.594 en la sudadera de Hanka).
- `test_presets`: solo los 12 fallos de la falda de volantes que ya había.
- `test_fit` con la mujer integrada (cose todas las prendas y mira bajos, cinturillas y mangas contra el cuerpo), con la prenda congelada tras Sew: **29 ok, 0 fallos** (`docs/fase8_test_fit_mujer.txt`).
- Paneles y diálogos dibujados sin errores en todos los estados (sin prenda, con avatar, prenda, cosida y terminada), con una maqueta del layout.

## Prueba a mano como usuario (1.3.1)

En el Blender 5.2 de Allan, escena nueva, sin scripts: instalar desde disco, importar `MANUKA.fbx`, Set Avatar, Hooded Cape, Quick Sew, mover la línea de tiempo, Sew con Esc a mitad, Sew, Finalize, Export Selected y Export All; luego una camiseta para repetir Sew y Esc con la 1.3.1.

Lo que funcionó: la capa queda congelada al saltar al fotograma 212; durante Sew los demás botones se apagan y Ctrl+Z no hace nada; Finalize (3.429 triángulos); Export Selected propone `HoodedCape.fbx`, crea la carpeta y escribe fbx + json + máscara; Export All recuerda la carpeta y avisa en rojo antes de sobrescribir.

Lo que fallaba y se arregló en la 1.3.1:

- **Set Avatar tomaba la malla activa sin mirarla**: tras importar el FBX quedaba activo el moño o los shorts (19 cm, 0/8 extremidades) y solo salía un aviso. Ahora, si la malla activa mide menos del 60 % del mejor candidato, usa el candidato y lo dice. Probado: con los shorts activos eligió `Manuka_body`, 124 cm, 8/8.
- **El progreso llegaba al 100 % antes de acabar**: los fotogramas extra de las puntadas abiertas no estaban en el plan. Ahora el plan crece con ellos y la barra dice la fase: stitching, closing the last stitches, settling. Probado: 6 → 91 % y fin.
- **«sewn» antes de tiempo**: Steps y la lista daban la prenda por cosida en cuanto no quedaban bordes sueltos, también tras Esc mientras asentaba. Ahora solo cuenta la prenda congelada; una soldada y sin congelar sale como «stopped», y Sew la recose desde plano sin pasar por Unsew (el mensaje de Esc ya dice «Press Sew»).
- **Textos cortados en la barra lateral estrecha**: Steps con textos más cortos y columnas fijas; la lista de prendas da un ancho fijo al estado.

Visto y no cambiado: el aviso de clases de panel «registered before» sale solo al instalar encima de una versión ya activa (Blender quita la anterior); la ropa original del avatar sigue visible y atraviesa la prenda, se oculta con H como cualquier objeto.
