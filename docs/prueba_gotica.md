# Prueba gótica — capa con capucha y corsé underbust (2026-11-22)

Rama `prueba-gotica`, sobre `fase-7`. Es una prueba, no una fase.

## Por qué no se usan patrones de la web tal cual

El advisor revisó qué patrones góticos o victorianos hay en la web y con qué licencia:
- **Libros de costura del siglo XIX** (dominio público): sirven como referencia de formas, redibujadas por nosotros.
- **Antique Pattern Library**: los escaneos son CC BY-NC-SA, no se pueden vender. Solo como referencia visual.
- **FreeSewing**: código MIT, uso comercial permitido. Si algún día se porta algo, hay que conservar su aviso MIT.
- **Patrones comerciales** (Simplicity, Etsy…) y **gratis "para uso personal"**: no se copian sus piezas.

Copiar las formas exactas de un patrón solo vale con dominio público o licencias abiertas. Inspirarse en el tipo de prenda y dibujarla desde las medidas del avatar es libre: en EE. UU. la forma de una prenda útil no tiene copyright, sí los estampados o encajes separables. No es asesoría legal.

Además, un patrón de la web viene a una talla humana fija, con márgenes de costura y sin costuras con nombre. Un preset se recalcula para cada avatar. Por eso la prueba es un **preset propio**: `preset_cape` en `clothing_design/library.py`.

## La capa

**Hooded Cape** en Add Garment. Espalda y dos delanteros que cuelgan de los hombros, cerrados desde el cuello hasta el pecho (`CAPE_CLOSE`, 12 cm en un cuerpo de 1,65 m) y abiertos por debajo, con la capucha de la sudadera.
- Los delanteros miden un cuarto de la cadera cada uno, con un 25 % de vuelo. La espalda es más amplia (×1,6) y se coloca un poco más afuera, para que sus lados caigan por encima de los delanteros y no los atraviesen al colocarla.
- **Sobre cada brazo cae una solapa** hasta el codo (`_cape_sleeve`): cosida a la sisa de la capa y abierta por debajo, ensanchándose hacia el bajo. Su copa se calcula para medir lo mismo que la sisa en la que se cose. El vuelo del bajo se limita a 0,9 vueltas al brazo, para que la pieza no se monte sobre sí misma al colocarla (en Hanka y Manuka queda entre 0,71 y 0,90). Con `arms=False` queda sin solapas, como un tabardo.
- El cierre empieza justo donde termina la curva del cuello. Empezaba 2 cm más abajo, y ese salto descuadraba las costuras del cuello con la capucha y del cierre (lo detectó `tests/test_presets.py`, que ahora pasa con la capa).
- Pasada la cadera, la capa se corta 12 cm más larga (`CAPE_EXTRA`, como `COAT_EXTRA` del abrigo), porque al coserla se queda más corta: en Hanka, la de largo Regular acababa 13 cm por encima de la rodilla.
- **Length:** Short es una capita hasta la cadera, Regular hasta la rodilla y Long hasta media pantorrilla.
- La capucha sale de `_hood_pieces`, extraída de la sudadera sin cambiarla.

## El corsé underbust

**Underbust Corset** en Add Garment (`preset_underbust`): las siete piezas del corsé, con el borde de arriba bajo el pecho en lugar de encima.
- El borde de arriba va al 60 % del camino de la axila a la cintura (`UNDERBUST_DROP`), nunca por encima de la línea del pecho y al menos 6 cm sobre la cintura. En Manuka manda ese mínimo de 6 cm. La línea de pecho que mide el add-on no sirve de guía: en Hanka está 4 cm bajo el hombro.
- El borde de arriba del delantero va recto, sin la bajada en el centro del corsé de siempre.
- Desde el diálogo, la holgura sale en 0,08, como en todas las prendas; el corsé queda más ceñido con −0,02.
- Es una opción nueva de `preset_corset` (`top_to="underbust"`). El corsé de siempre no cambia.

Los 13 presets anteriores dan exactamente los mismos patrones que en `fase-7`, en todas las combinaciones de Length y Sleeves (comparado por el advisor en Hanka, Manuka, mujer y hombre).

## Resultados

| | Capa (Hanka) | Capa (Manuka) | Underbust (Hanka) | Underbust (Manuka) |
|---|---|---|---|---|
| Puntadas abiertas al coser | 0 | 0 | 0 | 0 |
| Triángulos (exportación ligera) | 7.676 | 3.525 | 1.064 | 448 |
| Vértices del cuerpo ocultos | 1.082 de 8.985 | 1.282 de 15.064 | 567 de 8.985 | 657 de 15.064 |
| `test_export` | 0 fallos | 0 fallos | 0 fallos | 0 fallos |

`tests/test_presets.py` pasa con las dos (sus únicos fallos son los 6 de la falda de volantes por figura, que ya estaban en `fase-7`).

`docs/img/prueba_gotica_hanka.jpg`: las dos prendas en Hanka, de frente, lado, 3/4 y espalda. Las capturas de Manuka no van al repo.

## En Unity

Las dos prendas se probaron con la Prueba Fase 7 (`unity/Tests/OpenSewPruebaFase7.cs`) en el proyecto de prueba, junto a las 6 de la Fase 7: **10 prendas, 0 fallos** (`docs/prueba_gotica/unity_log.txt`). Para cada una:
- Se instala con lilToon, Modular Avatar une la prenda al esqueleto del avatar sin dejar huesos sueltos, y el paquete para vender lleva FBX, materiales, prefab, máscara y LEEME.
- La máscara borra piel en Play: con la capa, el cuerpo de Hanka baja de 17.946 a 16.189 triángulos y el de Manuka de 30.106 a 28.000; con el underbust, a 16.931 y 28.915.
- El menú de colores cambia el material en VRChat (5 colores).
- Girar la cabeza 30° mueve la capucha de la capa (333 vértices en Hanka, 230 en Manuka). Inclinar la columna 25° mueve el underbust.

`docs/img/prueba_gotica_unity_hanka.jpg`: capturas de Unity con lilToon en Hanka.

Lo que se ve en las capturas:
- La capa queda como una túnica larga abierta con mangas anchas, con la capucha puesta en Hanka. En Manuka cuelga bien, pero la capucha cae a la espalda.
- **El underbust de Hanka choca con su pantalón**: el pantalón de Hanka es de tiro alto y el corsé baja hasta la cadera, así que el pantalón asoma a manchas a través del corsé. Hay que llevarlo con otra ropa, o acortarlo para ese avatar. En Manuka, sin pantalón, queda limpio.
- En la captura del cuerpo sin la prenda se ve que la capa borra piel en hombros y parte alta de los brazos, bajo las solapas. Con la capa puesta no se ve, pero hay que comprobarlo moviéndose en VRChat, porque las solapas están abiertas por debajo.

**Pendiente:**
- En Manuka la capucha cae a la espalda, igual que con su sudadera, y las solapas quedan más tiesas, casi horizontales.
- El underbust de Manuka sale con poca malla (448 triángulos), como su corsé.
- Al pasar los pesos del esqueleto a la capa, solo el 39 % (Hanka) y el 51 % (Manuka) de los vértices se emparejan directamente, frente al 74–79 % de la sudadera. En Unity hay que mirar cómo se mueven la caída y las solapas al andar y al levantar los brazos.
- Idea por probar: la sisa de la capa está más hacia el centro que la de las otras prendas; puede ser la causa de que las solapas de Manuka queden tiesas.
- Con el frente y los lados abiertos de la capa, conviene revisar en Unity qué piel borra la máscara antes de vender.
