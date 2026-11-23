# Prueba gótica — capa con capucha (2026-11-22)

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
- Delantero y espalda solo se cosen en los hombros. Los lados quedan abiertos desde la punta del hombro, y los brazos salen por ahí.
- **Length:** Short es una capita hasta la cadera, Regular hasta la rodilla y Long hasta media pantorrilla.
- La capucha sale de `_hood_pieces`, extraída de la sudadera sin cambiarla: los 13 presets siguen dando los mismos patrones en Regular (solo la falda lisa cambió, en la Fase 7).

## Resultados

| | Hanka | Manuka |
|---|---|---|
| Puntadas abiertas al coser | 0 | 0 |
| Triángulos (exportación ligera) | 5.552 | 2.503 |
| Vértices del cuerpo ocultos | 994 de 8.985 | 1.131 de 15.064 |
| `test_export` | 0 fallos | 0 fallos |

`docs/img/prueba_capa_hanka.jpg`: frente, lado, 3/4 y espalda.

**Lo que falta para que parezca una capa de verdad:**
- No cubre los brazos: acaba en la punta del hombro. Para caer sobre los brazos en pose A haría falta otra forma de colocar la tela sobre los hombros; es lo siguiente que habría que probar.
- En Manuka la capucha cae a la espalda, igual que con su sudadera.
- Con el frente y los lados abiertos, conviene revisar en Unity qué piel borra la máscara antes de vender.
