# Fase 9 — todo bien antes de vender (2026-11-25) · versión 1.4.0

Rama `fase-9`. Objetivo de Allan: no pasar a vender hasta que esté todo bien; arreglar todo lo pendiente, probar en Unity, publicar, dejar Blender armado con el add-on y grabar un video de cómo lo usaría un cliente.

Se trabajó con subagentes en paralelo (una rama `fase9-<letra>` cada uno, integradas en `fase-9`) y con una **cola de trabajos en el PC de Allan** (6 Blender a la vez, 12 núcleos) para coser y renderizar; las herramientas de la cola no van en el add-on ni en `main` (rama local `dev-tools-pc`).

## Qué se arregló

### Antes de la revisión visual (agentes A–F)
- **Partes no humanas fuera de las medidas** (regla de Allan: cuernos, orejas de gato, alas, colas, halos): `avatar.drop_nonhuman`, `skull_top`, colisionador sin cuernos. The Beast pasa a medir 2,215 m; el resto, igual. `MEASURE_VERSION` 3.
- **Falda de volantes** con volantes trapecio y frunce medido (`build._pleat_map`, `fold_params`): las 12 pruebas que fallaban en `test_presets`, a 0.
- **Corsé / underbust**: en el hombre empieza 6 cm bajo la axila; cintura siempre al 0,97 de la medida.
- **Camiseta, sudadera y chaqueta holgadas** colocadas sin cruzar el costado (`loose`), y escote proporcional a la cabeza.
- **Puntadas abiertas**: se cierran tirando de las vecinas (`sim._draw_in_stitches`) y ya no se recose a fuerza completa por pocas puntadas; agujeros de esquina de 3–4 vértices se rellenan.
- **Capucha** ajustada desde la barbilla (cara visible en The Beast) y colisionador de nuca (Hanka).
- **Panel de prendas**: caja de estado fija («Quick-sewn: Sew again before selling» / «Sewn: changes apply after Unsew» / «Not sewn: Size and pieces update live»); ya no salta la interfaz al coser.

### Tras la revisión visual de 112 prendas (agentes G–N)
- **Costuras asimétricas izquierda/derecha (H, K, I, G)** — el fallo de fondo. Cada segmento de costura guardaba su esquina inicial y no la final; como el contorno da la vuelta, el lado izquierdo y el derecho cosían esquinas distintas (tirante que se corre, hueco en el hombro, bulto bajo la axila). Se cierran las dos esquinas (`closed=True`) en costados, hombros y copas de la camiseta sin mangas, vestido, abrigo, camiseta, faldas, chaqueta, sudadera (sin copas ni cuello de capucha: comprobado que empeoraban), mono y capa; y la esquina final se elige por arista de borde (`patterns.segment_verts`). Nueva prueba `tests/test_seam_symmetry.py`: pasan todas las prendas salvo el pantalón (mismo defecto, no se ve: queda para otra fase).
- **Mono y capa del hombre (G)**: la sisa del delantero caía en la espalda al colocar la pieza; ahora se coloca holgada solo en la franja de la sisa (`cd_loose = "armhole"`). La manga del mono ya no se despega y la capa no resbala del hombro.
- **Colgajo en la entrepierna del mono de Hanka (I)**: el tramo de entrepierna tenía un mínimo fijo de 9 cm; ahora usa la misma regla que el pantalón.
- **Capucha de Minase (J)**: su cabeza no tiene cuero cabelludo (el pelo hace de cráneo) y la capucha se hundía; casquete de apoyo solo para ese caso (`avatar._body_head_proxy`). `MEASURE_VERSION` 4.
- **Capucha sobre los ojos en los cuerpos integrados (M)**: en caras realistas la punta de la nariz sobresale ~12 mm de la frente y el ala de la capucha llegaba hasta ahí; ahora se recorta hasta la frente (`HOOD_NOSE`). Solo cambia WOMAN, MAN y Vlau.
- **Abrigo de Hanka caído de los hombros (L)**: lo causaba el colisionador de nuca de F al colocar prendas sin capucha; ahora solo cuenta para prendas con capucha.
- **Advisor**: el arreglo de Minase también tomaba el muñón de cuello de Vlau por un cráneo abierto (corregido); una pieza «armhole» sin sisa ya no se coloca holgada entera; código muerto fuera.

## Resultados (cola del PC)

| | Antes de la fase 9 | 1.4.0 |
|---|---|---|
| `test_fit` (8 avatares × 8 prendas + capas) | 232 ok / 0 | 231 ok / 1 (falda de The Beast: borde a 1,35 m con margen 1,35–1,49: ruido de la simulación) |
| Prendas recosidas a fuerza completa | 13 combinaciones | 3: camiseta sin mangas y vestido de The Beast, vestido de Vlau (cierran bien) |
| Puntadas abiertas al terminar | 13 combinaciones con 1–8 | 0 |
| `test_presets` | 12 fallos | 0 |
| Exportaciones (sudadera, capa, corsé × 6 avatares) | 18/18 | 18/18 |
| Comodidad (`test_comfort`) y nombres de huesos (159) | 0 fallos | 0 fallos |

## Unity (`Tools > OpenSew > Prueba Fase 9`, `docs/fase9_unity_log.txt`)

Proyecto `OpenSew_Prueba` (Unity 2022.3.22f1; se abrió directo con Unity porque el Creator Companion no arrancó). La prueba importa The Beast y Poiyomi si faltan, instala cada prenda con el instalador de OpenSew (lilToon + Modular Avatar) y en Play camina 2 s (muslos ±30°, rodillas, brazos balanceándose) y levanta los brazos 70° con el corsé.

- **Underbust de Hanka**: 0 fallos (caminar y brazos arriba: tela pegada, sin estirarse).
- **Capa de Manuka**: 0 fallos caminando.
- **Abrigo largo de The Beast**: instalado, huesos fusionados, Mesh Cutter bien; al caminar, **2 fallos**: unas pocas aristas del faldón entre las piernas se estiran hasta 4,6× (p99 1,64×, límite 1,6×) y un vértice se separa 10,7 cm. Es lo esperable en un abrigo largo pegado a los dos muslos sin física; para venderlo conviene añadir PhysBones al faldón o abrir la raja trasera. Queda como nota.

## Lo que queda (decisiones o fases futuras)
- **Pelo como colisionador**: en Manuka y Mao la capucha queda bajo el pelo. Hacer que el pelo choque con la tela es decisión de Allan.
- **Capa del hombre integrado**: cara despejada, pero las solapas de los brazos suben a los hombros.
- **Mangas de la capa**: siguen como tubos.
- **The Beast**: el vestido mantiene un pliegue en el costado (los tirantes empiezan a más de 30 cm de su sitio y se recose a fuerza completa); el underbust queda bajo.
- **Pantalón**: costuras con la misma asimetría (no se ve; cambiarlo afecta a todos los avatares).
- **Abrigo largo al caminar en Unity**: ver arriba.
- Las imágenes de Vlau en las pruebas salen con su armadura encima (el script de render no la quita); su `test_fit` sí la quita.

## Archivos
- `dist/opensew2_vrchat-1.4.0.zip`, `dist/OpenSew_Unity_Tools-1.4.0.unitypackage`.
- Pruebas nuevas: `tests/test_seam_symmetry.py`, `tests/export_unity.py`, `unity/Tests/OpenSewPruebaFase9.cs`.
