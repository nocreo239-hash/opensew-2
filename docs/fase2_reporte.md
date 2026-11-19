# Fase 2: proporciones anime, reporte

Fecha: 2026-11-19 · Rama `fase-2` (sale de `fase-1`) · Blender 5.2.4 (pruebas automáticas)

## Resumen

1. **Mangas en T-pose (lo más importante).** Los avatares de VRChat descansan
   en T-pose y las mangas se salían del brazo al coser. Ahora el add-on cose
   con los brazos bajados y Finalize devuelve la prenda a la T-pose: las
   mangas envuelven el brazo y lo siguen.
2. **Manos grandes y muñecas finas.** El puño de las mangas largas no pasaba
   por la mano de Mao y la manga salía disparada. Ahora el puño se patrona
   contra la palma.
3. **Cabeza grande para el cuello.** La capucha salía del contorno del
   cuello y en Mao medía 0,72 veces su cabeza. Ahora sale de la cabeza.
4. **Figura.** No había que arreglar nada: Hanka, Minase y Vlau son
   masculinos y Mao femenina, y el add-on acertaba. El "Hanka sale como
   hombre" de la Fase 1 era un error mío (ya corregido en
   `docs/fase1_reporte.md`).
5. **Pecho, cintura, cadera y cuello.** Revisados dibujando las secciones
   sobre los seis cuerpos: caen en su sitio. Cinturas finas y piernas largas
   ya se resuelven porque todo se mide sobre la malla y los huesos (bajos,
   cinturilla y largo de pantalón pasan en los cuatro avatares).
6. **Tests nuevos:** `tests/test_anime_bodies.py`.

Nora y Theo (los cuerpos de upstream) miden y patronan exactamente igual que
antes: ninguna de las reglas nuevas se activa con ellos.

## 1. Pose de ajuste para avatares en T-pose (`clothing_design/fitpose.py`)

**Qué pasaba.** El cuerpo de la camiseta tiene la sisa en el costado del
torso, que es donde queda con los brazos bajados. En T-pose la copa de la
manga rodea un brazo horizontal, y las costuras la arrastraban hacia esa sisa
y la sacaban del brazo. Se ve en las capturas de fases: colocada, bien; a
mitad del cosido, ya arrugada hacia el torso.

**Qué hace ahora.**
- Set Avatar: si los brazos están a más de 70° de la vertical, los baja a 60°
  (la pose con la que upstream prueba Nora y Theo). Es solo una pose: el
  rest pose del rig no se toca. Se mide, se patrona y se cose así.
- Finalize: después de atar los pesos calcula, para cada vértice, la inversa
  de la mezcla de matrices de sus huesos (el skinning inverso) y guarda la
  malla en la pose de reposo. Con el rig en la pose de ajuste se ve igual que
  al coser, y cuando el rig vuelve a la T-pose las mangas suben con el brazo.
- El botón **Rest Pose** (o **T-Pose** en el panel Avatar) devuelve los
  brazos a su sitio.
- Opción en el panel Avatar: **Lower Arms to Sew** (activada) y el ángulo.

**Resultado** (`tests/test_booth_avatars.py --drape`, T-Shirt finalizada y el
rig de vuelta en T-pose):

| | Hanka | Mao | Minase | Vlau |
|---|---|---|---|---|
| Manga respecto al eje del brazo | 54 mm | 38 mm | 49 mm | 64 mm |
| Manga al bajar el brazo (mediana) | 115 mm | 90 mm | 111 mm | 105 mm |
| Torso al bajar el brazo | 0 mm | 0 mm | 0 mm | 0 mm |

Entre 38 y 64 mm del eje significa que la manga rodea el brazo. En la Fase 1
la manga colgaba debajo.

## 2. Puño de manga larga contra la palma

La manga larga se corta pasada la muñeca (1,08 × el brazo) y termina sobre la
mano. Su puño salía del ancho del bíceps × 0,82. En Nora eso da un puño de
1,35 veces su palma; en Mao, de 0,92: no le pasa la mano, la colisión lo
expulsa y la manga sale disparada al empezar a coser.

- `avatar.palm_girth()`: contorno real de la palma, sin dedos, 2–6 cm pasada
  la muñeca (como polígono, porque la palma es plana). Nora 19,6 cm, Theo
  25,5, Hanka 24,2, Mao 19,3, Minase 28,3, Vlau 23,6.
- El puño de una manga que llega a la mano mide al menos 1,3 veces la palma,
  el margen que ya tiene Nora.
- Como el puño ensanchado deja la manga más holgada en el antebrazo y se
  arruga más al coser, esa manga se corta un 16% más larga.

Probé también estrechar la manga hasta la muñeca y ensancharla solo sobre la
mano: fue peor (la manga de Mao llegaba al 26% del brazo) y lo descarté.

## 3. Capucha a la medida de la cabeza

Las cabezas de estos avatares no son grandes respecto a la altura (10–13%,
como Nora); lo anime es la cabeza respecto al cuello. La capucha salía del
cuello (alto = cuello × 0,62).

- `avatar.head_size()`: largo, fondo y ancho de la cabeza, incluida la malla
  de la cara si va aparte.
- La capucha llega al menos a lo que tiene Nora: 0,96 veces el fondo de la
  cabeza y ~1,05 veces su largo. El borde que se cose al escote no cambia;
  para el fondo se agranda solo la parte trasera de la coronilla.

| Capucha / cabeza | antes | ahora |
|---|---|---|
| Mao (fondo / largo) | 0,76 / 0,72 | 0,96 / 1,04 |
| Hanka | 0,83 / 0,87 | 0,96 / 1,05 |
| Minase, Vlau, Nora, Theo | ya por encima | sin cambio |

## 4. Revisión de las medidas

| | Altura | Pecho | Cintura | Cadera | Cuello | Figura |
|---|---|---|---|---|---|---|
| Nora (upstream) | 160,6 | 87,5 | 67,2 | 91,5 | 32,9 | mujer |
| Theo (upstream) | 185,8 | 102,1 | 79,9 | 93,6 | 38,5 | hombre |
| Hanka | 172,5 | 85,3 | 61,8 | 77,2 | 25,9 | hombre |
| Mao | 147,6 | 60,4 | 51,2 | 77,7 | 19,3 | mujer |
| Minase | 166,8 | 82,4 | 57,5 | 75,9 | 29,6 | hombre |
| Vlau | 185,4 | 112,0 | 82,7 | 96,5 | 40,8 | hombre |

Dibujé los anillos de cada medida sobre los seis cuerpos, de frente y de lado.
Caen en su sitio: el cuello en su base, el pecho bajo las axilas en los
hombres y en el busto en Mao y Nora, la cintura en lo más estrecho, y bien la
cadera, la entrepierna y la rodilla. En los avatares anime el pecho queda más
cerca del hombro (4–8 cm) que en Theo (11 cm), por el torso en V.

Los cuellos finos (Mao 19,3 cm) son reales: el escote se patrona a esa medida
y, en el simulador, la cabeza no tiene que pasar por él.

## 5. Tests

- **`tests/test_anime_bodies.py` (nuevo).** Al estilo de `test_bodies.py`
  (puntos de medida en orden y separaciones sensatas) y de `test_fit.py`
  (cose las 8 prendas y comprueba bajo, cinturilla y manga respecto al propio
  cuerpo), más las reglas nuevas: puño/palma, capucha/cabeza, pose de ajuste.
  Con `--quick` solo mide y patrona.
- **`tests/test_booth_avatars.py`:** ahora comprueba también que en T-pose la
  manga queda alrededor del brazo.

**Resultados finales** (con el código de este commit):

- `test_anime_bodies.py`: **152 comprobaciones, 0 fallos**. Las 8 prendas
  en los 4 avatares con el bajo, la cinturilla y la manga en su sitio. Mangas
  largas: Hanka 1,05 / 1,06, Mao 0,92 / 0,85, Minase 1,00 / 1,02, Vlau
  0,96 / 0,97 del brazo (Jacket / sudadera; rango válido 0,80–1,18).
- `test_booth_avatars.py --drape`: **76 comprobaciones, 0 fallos** (4 avatares, T-Shirt y Jacket, Finalize, brazo, T-pose).
- `test_presets.py` (upstream): 0 fallos; Nora y Theo con las mismas medidas.
- `test_rig_names.py`: 145/145.

## Pendiente

- **Sudadera de Vlau, resultados que varían:** en una corrida su manga
  izquierda llegó solo al 0,61 del brazo, arrugada en el codo; en la
  siguiente, con el mismo patrón, al 0,97. La simulación de Blender no da
  siempre lo mismo y esta prenda está cerca del límite. La manga izquierda
  retorcida también aparece en Nora con la camiseta de upstream. No lo aislé.
- **Mangas largas arrugadas en Mao:** llegan a la muñeca pero con muchos
  pliegues. Es tela de Blender sobre un brazo muy fino.
- **Aspecto de upstream:** la camiseta y la sudadera tienen el cuello alto y
  dejan piel entre el cuerpo y la manga en el hombro, también en Nora. Es el
  patrón original, no las proporciones; para la Fase 4 (detalles).
- **Cintura entallada:** upstream limita el entallado del costado a 2,2 cm
  para no pellizcar la tela. En cinturas anime muy finas las prendas quedan
  rectas; entallarlas de verdad necesita pinzas (Fase 4).
- **En el PC de Allan:** la Fase 2 no la he probado todavía en su Blender.
