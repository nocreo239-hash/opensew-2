# Fase 4 — detalles góticos (estado al 2026-11-21)

Rama `fase-4`. Probado en la mujer de prueba, Hanka y Mao (Blender 5.2, sin GPU).

## Prendas nuevas

| Preset | Qué es | Estado |
|---|---|---|
| COAT | Abrigo largo hasta la rodilla, con vuelo, cerrado hasta el muslo, abertura trasera | Bien en la mujer y en Hanka; test_export pasa |
| CORSET | Corsé de 7 paneles, escote corazón, pico, cintura entallada | Bien en la mujer (sobre el pecho); en Hanka sale bajo el pecho (figura de hombre). Una esquina superior de la espalda queda irregular |
| PLEATED | Falda de pliegues de cuchillo sobre un canesú | Se sostiene y los pliegues se marcan; algo ondulados |
| TIERED | Falda de tres pisos de volantes fruncidos sobre un canesú | Sin rendija y con el bajo parejo; los pisos se distinguen poco |

## Cambios en el motor

- `build._pleat_map`: una pieza con `pleats > 0` se coloca ya doblada en pliegues. La tela toma ese estado como forma de reposo y mantiene los dobleces. El doblado empieza a mitad de una cara, así que los dos bordes de cada pieza caen en tela visible.
- `build._head_transform` (anclas HEAD_L / HEAD_R): la capucha se coloca sobre la cabeza. Se proyecta sobre la superficie real de la cabeza y el cuello mediante rayos contra el cuerpo y la cabeza separada.
- La cabeza separada (Mao, Hanka, Vlau) entra en la colisión.
- Instalador de Unity: sombra lilToon suave por defecto, en el color de la tela.

## Capucha

| Avatar | Resultado |
|---|---|
| Mujer de prueba | Puesta sobre la cabeza (1–3 puntadas abiertas) |
| Hanka | Puesta, algo torcida |
| Mao | No: la costura de la coronilla queda con las dos mitades a los lados de la cabeza (12–17 cm), la cabeza en medio |

Lo que se probó para Mao y se deshizo:
- Dejar el borde de la cara al 85 % de la frente: empeora Mao y Hanka.
- Profundizar la capucha según la cabeza: no cierra Mao y estropea a la mujer y a Hanka.

Los resultados de la capucha varían entre una tirada y otra.

## Pendiente

- Capucha de Mao (cabeza enorme sobre un cuello muy fino).
- Probar PLEATED y TIERED en Hanka y en Mao.
- Esquina del corsé.
