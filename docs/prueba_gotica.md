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
- **Sobre cada brazo cae una solapa** hasta el codo (`_cape_sleeve`): cosida a la sisa de la capa y abierta por debajo, ensanchándose hacia el bajo. Su copa se calcula para medir lo mismo que la sisa en la que se cose. El bajo nunca pasa de una vuelta al brazo, para que la pieza no se monte sobre sí misma al colocarla. Con `arms=False` queda sin solapas, como un tabardo.
- **Length:** Short es una capita hasta la cadera, Regular hasta la rodilla y Long hasta media pantorrilla.
- La capucha sale de `_hood_pieces`, extraída de la sudadera sin cambiarla.

## El corsé underbust

**Underbust Corset** en Add Garment (`preset_underbust`): las siete piezas del corsé, con el borde de arriba bajo el pecho en lugar de encima.
- El borde de arriba va al 60 % del camino de la axila a la cintura (`UNDERBUST_DROP`), nunca por encima de la línea del pecho y al menos 6 cm sobre la cintura. La línea de pecho que mide el add-on no sirve de guía: en Hanka está 4 cm bajo el hombro.
- Es una opción nueva de `preset_corset` (`top_to="underbust"`). El corsé de siempre no cambia.

Los 15 presets anteriores siguen dando los mismos patrones en Regular (comparado contra la versión anterior en Hanka, Manuka, mujer y hombre; solo la falda lisa cambió, en la Fase 7).

## Resultados

| | Capa (Hanka) | Capa (Manuka) | Underbust (Hanka) | Underbust (Manuka) |
|---|---|---|---|---|
| Puntadas abiertas al coser | 0 | 0 | 0 | 0 |
| Triángulos (exportación ligera) | 6.936 | 3.139 | 1.056 | 444 |
| Vértices del cuerpo ocultos | 1.091 de 8.985 | 1.512 de 15.064 | 547 de 8.985 | 628 de 15.064 |
| `test_export` | 0 fallos | 0 fallos | 0 fallos | 0 fallos |

`docs/img/prueba_gotica_hanka.jpg`: las dos prendas en Hanka, de frente, lado, 3/4 y espalda. Las capturas de Manuka no van al repo.

**Pendiente:**
- En Manuka la capucha cae a la espalda, igual que con su sudadera, y las solapas quedan más tiesas, casi horizontales.
- El underbust de Manuka sale con poca malla (444 triángulos), como su corsé.
- Con el frente y los lados abiertos de la capa, conviene revisar en Unity qué piel borra la máscara antes de vender.
