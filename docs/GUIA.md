# Guía de OpenSew 2 para VRChat

Del avatar en Blender al paquete listo para vender en Booth o Jinxxy. Probado con Blender 5.2, Unity 2022.3.22f1, VRChat SDK 3.10, Modular Avatar 1.19 y lilToon 2.4, con Hanka y Manuka.

La interfaz del add-on está en inglés. Al final hay un glosario con lo que significa cada botón.

## 1. Instalar

**En Blender (una vez).** Hace falta Blender 5.2 o más nuevo.
1. Toma el zip `opensew2_vrchat-<versión>.zip`. Viene hecho en `dist/`; si cambias el código, lo vuelves a generar con `python tools/build_zip.py`.
2. En Blender, abre *Edit > Preferences > Get Extensions*.
3. Abre el menú de arriba a la derecha y elige *Install from Disk…*.
4. Elige el zip. Aparece como **OpenSew 2 - VRChat**. Para actualizarlo, instala el zip nuevo encima.
5. En la vista 3D, pulsa `N` para abrir la barra lateral y busca la pestaña **Clothing**.

**En Unity (una vez por proyecto)**
1. Toma `OpenSew_Unity_Tools-<versión>.unitypackage` (en `dist/`, o `python tools/build_unitypackage.py`).
2. Abre el proyecto con el VRChat Creator Companion o ALCOM, y añade **Modular Avatar** (1.19 o más nuevo) y **lilToon**.
3. Importa el paquete: *Assets > Import Package > Custom Package…*.
4. Aparece el menú **Tools > OpenSew**.

## 2. Hacer la prenda en Blender

Todo está en la barra lateral, pestaña **Clothing**. Arriba, el panel **Steps** dice en qué paso está la prenda elegida (1 Avatar, 2 Garment, 3 Sew, 4 Finalize, 5 Export) y cuál toca. Los paneles que empiezan por **Advanced** vienen cerrados: no hacen falta para el camino normal.

**Guarda el .blend antes de coser** (*File > Save*). Coser tarda minutos, y así puedes volver atrás.

1. **Importa el avatar**: *File > Import > FBX*, con el FBX que viene en el paquete de Booth.
   - Puedes borrar u ocultar la ropa que trae el avatar. La ropa original no participa en la colisión.
2. **Panel Avatar**: selecciona el cuerpo y pulsa **Set Avatar**. Si lo activo es una pieza pequeña (tras importar un FBX suele quedar activo el pelo o unos shorts), Set Avatar la ignora, busca el cuerpo solo y lo avisa.
   - Revisa las medidas que muestra (altura, pecho, cintura, cadera, cuello) y cuántos huesos reconoce.
   - Si la cabeza es una malla aparte (Hanka, Mao), sale como «+ Body».
   - Con **Lower Arms to Sew** (activado por defecto), si el avatar está en pose T, baja los brazos para coser: las mangas cosidas en brazos horizontales se escurren. Al terminarla con Finalize, la prenda se guarda en la pose T original del avatar.
3. **Panel Patterns**: pulsa **Add Garment**.
   - **Garment**, la prenda: T-Shirt, Tank Top, Skirt, Pleated Skirt, Ruffled Skirt, Trousers, Jumpsuit, Dress, Jacket, Hoodie, Long Coat, Corset, Underbust Corset, Hooded Cape o Flat Panel (un panel suelto para dibujar a mano).
   - **Ease** es la holgura: menos es más ajustada. El corsé queda ceñido con −0,02.
   - **Length** (largo): Short, Regular o Long. Regular es la prenda tal cual; debajo sale qué significa en esa prenda (en la camiseta Short es corta a la cintura y Long una túnica a medio muslo; en el pantalón Short es un short; en la capa Short es una capita a la cadera).
   - **Sleeves** (mangas): Regular, Short, Elbow (hasta el codo) o Long, medidas sobre el brazo del avatar. None (sin mangas) solo sirve en el vestido.
   - **Outfit**, al lado, hace un conjunto entero de una vez (varias prendas en capas, de dentro afuera).
4. **Panel Garments**: la lista tiene todas las prendas; la elegida es con la que trabajan los botones.
   - **Change…** vuelve a abrir el diálogo de la prenda para cambiar largo, mangas, holgura o incluso el tipo. La prenda vuelve sin coser y conserva su nombre (si cambias una camiseta por una falda, se sigue llamando T-Shirt).
   - **Delete** la borra entera (piezas, costuras y prenda 3D).
   - **Size** la agranda o achica entera.
5. **Quick Sew (to check the fit)**: cose en más o menos la mitad del tiempo y con menos calidad, para ver si el largo y la holgura van bien antes de coser en serio. Si no te gusta, **Change…** y prueba otra vez. Si te gusta, pulsa **Sew**: vuelve a coser desde las piezas planas, ya con la calidad buena.
6. **Sew**: cose la prenda de verdad. Tarda unos minutos.
   - Blender no se congela: abajo sale el progreso («Sewing T-Shirt: 40 %») y **Esc** lo para. Responde entre un fotograma y el siguiente (cada uno tarda 1–2 s en un avatar como Hanka). Mientras cose solo puedes mover la vista (rueda, botón del medio); el resto de botones esperan a que termine.
   - Al terminar, el mensaje dice si quedaron puntadas abiertas. Una o dos no se notan; muchas significan que la prenda no encaja: prueba otra holgura con **Change…**.
   - **Sew All** cose todas las prendas, de la capa de dentro a la de fuera.
   - Cuando está cosida, la prenda queda **congelada y protegida**: se queda quieta aunque muevas la línea de tiempo, y tocar Size, los valores de las piezas o las costuras ya no la deshace (sale «Sewn: changes apply after Unsew»). La forma cosida queda guardada en el .blend: puedes cerrar Blender y seguir otro día. *Settle*, *Relax* y *Grab Fabric* (en Advanced) la vuelven a simular a propósito. *Arrange on Body* y *Reset Simulation* (también en Advanced) sí la vuelven a dejar sin coser, sin preguntar.
7. **Panel Finalize**: pulsa **Finalize** (o **Finalize All** para todas las prendas cosidas). Congela la forma, suelda las costuras, pone grosor y pasa los pesos del avatar a la prenda.
8. **Hide Body Under It** (activado por defecto): al exportar, guarda una máscara con la piel que la prenda tapa, para que Unity la borre y no atraviese la ropa al moverse. El botón de al lado (**Shrink Body**) además mete la piel hacia dentro con un shape key en el cuerpo, para la piel cerca de los bordes.
9. *(Recomendado)* **Test On The Move > Animate**: el avatar camina en el sitio para ver si la prenda se abre o atraviesa el cuerpo. **Rest Pose** (la flecha) lo para. La siguiente prenda que añadas o cosas vuelve a bajar los brazos sola.

## 3. Exportar

En el panel **Finalize**:
- **Subdiv 0** y **Thickness apagado** son lo normal para VRChat.
  - El panel muestra los triángulos que tendrá la exportación (unos 4.000 en una camiseta).
  - Cada nivel de subdivisión multiplica los triángulos por 4, y el grosor los duplica.
  - Referencia: VRChat da a un avatar entero en PC el rango Excellent hasta 32.000 triángulos y Good hasta 70.000, y la ropa se suma al avatar. En Quest el SDK avisa a partir de 20.000.
- **Export All** mete todas las prendas terminadas en un FBX (un conjunto). **Export Selected** solo la prenda elegida en la lista, para venderla suelta.

Cada exportación escribe varios archivos con el mismo nombre. **Cópialos juntos a Unity**:
- `<nombre>.fbx`: la prenda y una copia de los huesos del avatar que usa, terminados en `_OpenSew`.
- `<nombre>.opensew.json` y `<nombre>_mask_0.png` (uno por material del cuerpo): la máscara para borrar la piel. Sin ellos la prenda se instala igual, pero no borra la piel.

La prenda lleva dos mapas UV:
- **UVMap** (el primero, el que usa Unity): todas las piezas planas, sin solaparse, dentro del cuadrado 0–1. Es para pintar una textura propia. Para tener la plantilla: selecciona la prenda, entra en el *UV Editor* y usa *UV > Export UV Layout*; pinta encima en Krita, Photoshop o Substance.
- **Fabric**: el patrón en metros (1 unidad = 1 m). Es para una tela que se repite, como cuadros, encaje o terciopelo.

## 4. Instalar en el avatar (Unity)

1. Copia el FBX, el `.opensew.json` y los `_mask` PNG a la misma carpeta dentro de `Assets/`.
2. Pon el avatar en la escena.
3. Abre **Tools > OpenSew > Instalar ropa (Modular Avatar)**.
4. Elige el avatar de la escena y el FBX.
5. Opciones:
   - **Materiales lilToon** y **Doble cara** marcados. «Doble cara» hace que se vea el interior de mangas y cuello.
   - **Menú de colores**: añade al menú del avatar en VRChat un submenú para cambiar la prenda entre el color original y 5 más (negro, vino, morado, azul noche, blanco).
   - **Tipo de tela**: *Opaca* para tela normal; *Encaje (recortado)* si tu textura tiene partes transparentes (alfa), para encaje o rejilla; *Transparente* para tul o gasa (pesa más en VRChat). Si la prenda ya estaba instalada, la ventana empieza con el tipo que tenía. Si reinstalas con otro tipo, el material y sus 5 colores cambian de tipo y conservan los colores y texturas que les pusiste; si elegiste a mano otra variante de lilToon (con contorno, por ejemplo), esa no se toca.
6. Pulsa **Crear prefab e instalar en el avatar**. Se crean:
   - la carpeta `<prenda>_OpenSew/`, con el material lilToon y los de color;
   - el prefab `<prenda>_MA.prefab`, ya configurado con Modular Avatar (Merge Armature, el recorte de la piel y el menú de colores).
7. Lee el informe de la ventana: dice si encontró la máscara y cuántos vértices de piel borra.
8. Entra en **Play** y mueve el avatar para comprobar que la ropa le sigue y que no asoma piel.

**Para ponerle textura**: selecciona el material lilToon de `<prenda>_OpenSew/` y arrastra tu imagen a **Main Texture**.

## 5. Empaquetar para vender

1. Abre **Tools > OpenSew > Empaquetar para vender**.
2. Elige el prefab `<prenda>_MA` y escribe el nombre del producto, la tienda y el avatar.
3. Pulsa **Exportar .unitypackage**. El paquete lleva el FBX, los materiales, las texturas, la máscara, el prefab y un `LEEME_<producto>.txt` en español y en inglés con los requisitos (Modular Avatar 1.19 o más nuevo), cómo se llama el cuerpo que espera la prenda y qué hacer si el comprador lo renombró.

**No van dentro**: lilToon, Modular Avatar, el VRChat SDK ni el avatar. El comprador ya los tiene o los instala él, como en cualquier ropa de Booth. El comprador importa el paquete y arrastra el prefab sobre su avatar.

**Antes de vender** ropa para un avatar de Booth, lee su licencia (por ejemplo VN3): dice si se puede vender ropa hecha para él y con qué condiciones. El paquete no lleva nada del avatar, solo la máscara en blanco y negro.

## 6. Si algo sale mal

- **Deshacer después de coser**: Ctrl+Z no sirve bien para la costura. Usa **Unsew**: deja la prenda abierta otra vez, con las piezas planas, lista para cambiar cosas y volver a coser. **Unsew All** lo hace con todas.
- **Paré la costura con Esc**: la lista marca la prenda con «stopped»; vuelve a pulsar **Sew** y empieza otra vez desde las piezas planas.
- **Quedaron puntadas abiertas**: prueba otra holgura (**Change…**, Ease un poco más alto). Si es una manga, prueba otro largo de manga.
- **Cambié algo y no pasa nada**: si la prenda está cosida, los cambios esperan al **Unsew** (lo dice el aviso con el candado).
- **La prenda sale en otra pose que las anteriores**: deja **Lower Arms to Sew** activado; la siguiente prenda que añadas o cosas vuelve a bajar los brazos.
- **En Unity no se borra la piel**: faltan el `.opensew.json` o los `_mask` PNG junto al FBX. Cópialos e instala otra vez.
- **Quiero empezar una prenda de cero**: **Delete** y **Add Garment**.

## Glosario de la interfaz

| En el add-on | Qué es |
|---|---|
| Steps | los pasos y en cuál está la prenda |
| Set Avatar | usar esta malla como cuerpo y medirla |
| Lower Arms to Sew | bajar los brazos para coser |
| Add Garment / Outfit | añadir una prenda / un conjunto |
| Ease, Length, Sleeves | holgura, largo, mangas |
| Change… / Delete | cambiar / borrar la prenda elegida |
| Size | tamaño de toda la prenda |
| Quick Sew | costura rápida de prueba |
| Sew / Unsew (All) | coser / descoser (todas) |
| Finalize (All) | terminar: congelar, soldar, grosor y pesos |
| Hide Body Under It / Shrink Body | borrar la piel tapada / meterla hacia dentro |
| Export All / Export Selected | exportar todas / solo la elegida |
| Test On The Move > Animate / Rest Pose | caminar para probar / volver a la pose |
| Advanced: Draw And Mesh | dibujar piezas a mano, resolución de la malla |
| Advanced: Piece Arrangement | colocación de cada pieza (alto, giro, ancho, largo) |
| Advanced: Seams | la lista de costuras |
| Advanced: Fabric And Simulation | tela y ajustes de la simulación |

## Licencia

OpenSew 2 es GPL-3.0-or-later. Es un fork del add-on de Marcello Morettoni.
- **Las prendas que hagas con él son tuyas**: en general, la GPL cubre el código del programa, no lo que produces con él. No es asesoría legal.
- **Si publicas el add-on modificado**, el código tiene que ir público y con la misma licencia.

## Limitaciones conocidas

- La capucha puesta deja un hueco en la nuca en avatares de cabeza grande, como Hanka. En Mao no funciona, y en Manuka cae a la espalda.
- En la falda de volantes, el frente queda unos centímetros más alto en la figura de mujer.
- La tela (rigidez, peso) es una para toda la escena: en un conjunto con tela rígida y tela ligera, cámbiala entre una costura y otra en *Advanced: Fabric And Simulation*.
- Los puntos del patrón no se pueden mover a mano y regenerar; cambia el largo, las mangas y la holgura con **Change…**, o el ancho y largo de cada pieza en *Advanced: Piece Arrangement* (con la prenda descosida).
- Probado de punta a punta en Unity con Hanka y Manuka. Otros avatares necesitan su propia prueba: revisa la prenda cosida antes de venderla.
