# Fase 4 — detalles góticos (estado al 2026-11-22)

Rama `fase-4`. Probado en la mujer de prueba, Hanka y Mao (Blender 5.2, sin GPU), y en Unity 2022.3.22f1 con Hanka.

## Prendas nuevas

| Preset | Qué es | Estado |
|---|---|---|
| COAT | Abrigo largo hasta la rodilla, con vuelo, cerrado hasta el muslo, abertura trasera | Bien en la mujer y en Hanka; test_export pasa (2 puntadas abiertas en Hanka) |
| CORSET | Corsé de 7 paneles, escote corazón, pico, cintura entallada | Bien en la mujer: sobre el pecho, baja bajo la axila, espalda recta. En Hanka (figura de hombre) queda bajo el pecho |
| PLEATED | Falda de pliegues de cuchillo sobre un canesú con pespuntes | Se sostiene y los pliegues se marcan, en la mujer y en Hanka |
| TIERED | Falda de tres pisos: bandas lisas con volantes fruncidos encima | Los pisos se distinguen; el bajo queda algo desigual |

## Cambios en el motor

- `build._pleat_map`: una pieza con `pleats > 0` se coloca ya doblada en pliegues. La tela toma ese estado como forma de reposo y mantiene los dobleces. El doblado empieza a mitad de una cara, así que los dos bordes de cada pieza caen en tela visible.
- Costuras cerradas (`CDSeam.closed`): incluyen la esquina final, para que las costuras invertidas no queden desfasadas una fila (escalones de 12–18 mm en el corsé).
- `build._head_transform` (anclas HEAD_L / HEAD_R): la capucha se coloca sobre la cabeza. Se proyecta sobre la superficie real de la cabeza y el cuello mediante rayos contra el cuerpo y la cabeza separada.
- Cabeza separada:
  - Entra en la colisión.
  - Si está abierta (Mao) o hecha de muchas piezas (Hanka: 130), se usa en su lugar un casco convexo, `CD_HeadProxy`, emparentado al hueso de la cabeza.
- Pesos de la capucha: se transfieren desde el cuerpo y desde las mallas compañeras con grupos de huesos.
- Instalador de Unity: sombra lilToon suave por defecto, en el color de la tela.

## Capucha

| Avatar | Resultado |
|---|---|
| Mujer de prueba | Puesta, 0 puntadas abiertas |
| Hanka | Puesta, 0 abiertas, enmarca la cara. Queda un hueco en la nuca: la costura capucha/espalda se retuerce |
| Mao | Descartada (decisión del 2026-11-22): con 3 abiertas el borde le cae sobre los ojos |

## Prueba en Unity (Hanka)

`Tools > OpenSew > Prueba Fase 4` (`unity/Tests/OpenSewPruebaFase4.cs`). Por cada FBX de `Assets/OpenSew/Fase4/` hace lo siguiente:

1. Instala la prenda con lilToon y Modular Avatar.
2. Entra en Play y comprueba:
   - que los huesos se fusionan con los del avatar;
   - que la prenda se mueve con la cabeza, el brazo, el muslo o la columna, según la prenda.
3. Saca capturas en `Logs/fase4/`.

Resultado: 5 de 5 prendas pasan (log en `docs/fase4_unity_log.txt`, hoja de capturas en `docs/img/fase4_unity_hanka.jpg`).

| Prenda | Huesos | Movimiento |
|---|---|---|
| COAT | 16, todos fusionados | Brazo: 5462 vértices |
| CORSET | 7, todos fusionados | Columna: 3206 vértices |
| HOODIE | 15, todos fusionados | Cabeza 30°: la capucha sigue (2391 vértices) |
| PLEATED | 7, todos fusionados | Muslo: 6789 vértices |
| TIERED | 7, todos fusionados | Muslo: 12569 vértices |

Visto en las capturas:
- La cola de Hanka atraviesa el abrigo por detrás (la cola no es colisionador).
- En la vista de espalda, la capucha de Hanka deja ver el pelo en la nuca.

## Pendiente

- Hueco de la capucha en la nuca de Hanka.
- Bajo desigual de TIERED.
- Abertura para la cola (o colisión con la cola) en abrigo y faldas.
