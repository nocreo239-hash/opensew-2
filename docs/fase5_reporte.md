# Fase 5 — pulir lo pendiente (en curso, 2026-11-22)

Rama `fase-5`, a partir de `fase-4`. Alcance elegido por Allan: los detalles que quedaron de la Fase 4.

## Hecho

- **Aviso de colisión** (`sim._warn_colliders`). Antes, si la cabeza separada o el casco `CD_HeadProxy` fallaba al entrar en la colisión, el error se descartaba sin decir nada y la capucha podía atravesar la cabeza. Ahora se imprime un aviso.
- **Pruebas de exportación de la Fase 4 guardadas** en `docs/fase4_test_export/`. Son 8 corridas con 0 fallos: Hanka con JACKET, COAT, CORSET, PLEATED, TIERED y HOODIE, y la mujer con CORSET y TIERED.

## Nuca de la capucha en Hanka (no resuelto)

**Causa (medida en la colocación, sin simular):**
- El borde del cuello de la capucha se coloca sobre un anillo del tamaño del cuello: el radio del cuello × 1,35.
- El escote del cuerpo queda más abajo y más atrás. En Hanka, el centro de la espalda del escote está 12 cm por detrás del centro del cuello, y el borde de la capucha a 9,6 cm, además 2 cm más alto.
- Al coser, el escote sube por el cuello y forma un cuello alto. El casco de la capucha queda separado alrededor y deja ver el cuello por el hueco.

**Probado y deshecho:** `build._settle_hood_nape`, que mueve el borde del cuello de la capucha sobre el escote antes de simular, con el resto de la capucha atenuándose detrás.

| Variante | Hanka | Mujer |
|---|---|---|
| Solo espalda, alcance 7 cm | Igual (cuello alto), 0 puntadas abiertas | 2 abiertas (118 mm) |
| Espalda y frente, 12 cm | 4 abiertas (hombros) | 2 abiertas |
| Solo espalda, 12 cm | Igual, 0 abiertas | 1 abierta (capucha/frente) |

**Idea para retomarlo:**
- Colocar el anillo inferior de la capucha sobre el escote real y no sobre el cuello.
- Pasar a la forma de la cabeza de forma gradual, hacia la altura de la mandíbula.
- Para eso, `_head_transform` necesita la forma del escote. Hoy no la conoce, porque cada pieza se coloca por separado.

## Bajo de TIERED

Altura más baja del último piso, en 12 sectores alrededor:

| Avatar | Diferencia | Dónde |
|---|---|---|
| Hanka | 1,6 cm | Pareja; el último piso se recoge un poco hacia dentro |
| Mujer | 5,8 cm | El frente queda más alto que la espalda |

El largo del drapeado sobre el cuerpo, de la cintura al bajo, es igual delante y detrás (0,567 y 0,566 m). La diferencia no viene de la forma del cuerpo y no se puede compensar alargando el frente según el cuerpo. No se cambió nada.

## COAT en Hanka

Quedan 2 puntadas abiertas en el hombro izquierdo, en la manga/espalda y en la costura del hombro. Es una decisión de diseño ya existente:
- Con hasta 3 puntadas abiertas no se recose toda la prenda a fuerza completa (`ops.FALLBACK_OPEN`).
- Recoser así es lo que sacaba la chaqueta de los hombros de Hanka.

En las capturas el hombro se ve bien. El vuelo (`COAT_FLARE` 1,22) no se tocó.

## Pendiente

- La nuca de la capucha, con el enfoque de arriba.
- El frente del bajo de TIERED en la mujer.
