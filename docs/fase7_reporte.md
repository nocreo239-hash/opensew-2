# Fase 7 — ocultar el cuerpo y colores (en curso, 2026-11-22; Hanka y Manuka)

Rama `fase-7`. De la lista del advisor: formas para esconder el cuerpo bajo la ropa y variantes de color.

## 1. Ocultar el cuerpo bajo la prenda

`clothing_design/shrink.py`.

**Qué piel está tapada:** desde cada vértice del cuerpo se lanza un rayo hacia fuera, contra la prenda.
- Está **tapado** si hay tela delante, de 4 cm por dentro de la piel a 15 cm por fuera, mirando hacia el mismo lado.
- Está **oculto para siempre** si, además, la tela que lo tapa está a más de 3,5 cm de cualquier borde (bajo, puños, escote, cara).
- El grosor de la prenda se quita al medir, porque si no cierra los bordes.
- Los 15 cm hacen falta porque una sudadera cuelga de 8 a 10 cm separada de la parte baja de la espalda de Hanka (`docs/img/fase7_cobertura_hanka.png`: rojo oculto, amarillo tapado cerca del borde, azul descubierto).

**Dos salidas:**
- **Shape key `Shrink_<prenda>`** en el cuerpo (botón junto a «Hide Body Under It», en Finalize). Mete la piel tapada detrás de la tela, con 4 mm de holgura y como mucho 3 cm. Sirve para tu propio avatar o para previsualizar, no se vende.
- **Máscara para Unity:** al exportar, junto al FBX salen:
  - `<fbx>_mask_<n>.png`, negra donde la piel queda oculta, en las UV del cuerpo;
  - `<fbx>.opensew.json`, con el nombre del cuerpo y sus materiales.

  Solo viaja la máscara: el cuerpo del avatar es obra de otra persona y nunca se exporta.

**En Unity:** el instalador añade **MA Mesh Cutter** en un hijo de la prenda (`OpenSew_OcultarCuerpo`).
- *Object* apunta al cuerpo del avatar, con un *Vertex Filter – By Mask* por material: borrar negro, solo polígonos con todas sus esquinas dentro.
- Es un componente reactivo de Modular Avatar 1.13+: borra esa piel al compilar el avatar, y solo si la prenda está puesta.
- El empaquetador incluye la máscara.

## 2. Menú de colores

El instalador añade el submenú «Color <prenda>» al menú del avatar (opción «Menú de colores», activada por defecto):
- Un toggle exclusivo por color: Original (por defecto), Negro, Vino, Morado, Azul noche y Blanco.
- Cada toggle lleva un **MA Material Setter** con una copia teñida del material lilToon (color y sombra).
- Un solo parámetro entero `OpenSew/<prenda>/Color`, sincronizado y guardado.

## Prueba en Unity (Hanka)

`Tools > OpenSew > Prueba Fase 7`, log en `docs/fase7_unity_log.txt`. Todo pasa con la sudadera y la falda de pliegues:

| | Hoodie | Pleated |
|---|---|---|
| Vértices del cuerpo ocultos (de 8.985) | 3.097 | 949 |
| Triángulos del cuerpo en Play (antes 17.946) | 11.986 | 16.213 |
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
| Hoodie | 2.477 | 4.977 |
| Corset | 522 | 797 |
| Pleated | 2.326 | 1.541 |
| Tiered | 3.680 | 1.319 |

**Unity:** las 4 prendas de Manuka pasan, junto con las 2 de Hanka; 6 de 6 y 0 fallos.
- La prenda se instala con el prefab lilToon de Manuka, y los huesos se fusionan.
- El cuerpo pierde piel bajo la prenda: de 30.106 triángulos a 20.318 con la sudadera, 28.656 con el corsé, 27.244 con la falda de pliegues y 28.024 con la de volantes.
- El menú de colores funciona: 5 de 5 colores en el FX y parámetro sincronizado.
- La capucha sigue a la cabeza y las faldas siguen al muslo.

Las capturas de Manuka se guardan en el PC (`Logs/fase7/`), no en el repo, porque muestran el cuerpo base del avatar.

## Limitaciones

- Si el cuerpo del avatar comparte UVs entre izquierda y derecha (UVs espejadas), una prenda asimétrica ocultaría los dos lados. Los presets son simétricos.
- La piel justo al lado de un bajo (3,5 cm) se conserva para que no se vea un hueco al moverse. Si en una pose extrema asoma piel ahí, se puede bajar `EDGE_MARGIN`.
- Hanka trae los calzoncillos como malla aparte: no se tocan.

## Pendiente de la Fase 7

- Más controles al elegir prenda (largo, mangas).
- Probar Mao, Vlau y Minase (hay paquetes en el PC de Allan).
