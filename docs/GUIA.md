# Guía de OpenSew 2 para VRChat

Del avatar en Blender al paquete listo para vender en Booth o Jinxxy. Probado con Blender 5.2, Unity 2022.3.22f1, VRChat SDK 3.10, Modular Avatar 1.19 y lilToon 2.4, sobre Hanka.

## 1. Instalar

**En Blender (una vez)**
1. Genera el zip: `python tools/build_zip.py` → `dist/opensew2_vrchat-<versión>.zip`.
2. En Blender, abre *Edit > Preferences > Get Extensions*.
3. Abre el menú de arriba a la derecha y elige *Install from Disk…*.
4. Elige el zip. Aparece como **OpenSew 2 - VRChat**.
5. En la vista 3D, pulsa `N` para abrir la barra lateral y busca la pestaña **Clothing**.

**En Unity (una vez por proyecto)**
1. Genera el paquete: `python tools/build_unitypackage.py` → `dist/OpenSew_Unity_Tools-<versión>.unitypackage`.
2. Abre el proyecto con el VRChat Creator Companion o ALCOM, y añade **Modular Avatar** y **lilToon**.
3. Importa el paquete: *Assets > Import Package > Custom Package…*.
4. Aparece el menú **Tools > OpenSew**.

## 2. Hacer la prenda en Blender

Todos los botones están en la barra lateral, pestaña **Clothing**.

1. **Importa el avatar**: *File > Import > FBX*. Usa el FBX del avatar que viene en su paquete de Booth.
   - Puedes borrar u ocultar la ropa que trae el avatar para verlo mejor.
   - La ropa original no participa en la colisión.
2. **Panel Avatar**: selecciona el cuerpo y pulsa **Set Avatar**.
   - Revisa las medidas que muestra: altura, pecho, cintura, cadera y cuello.
   - Revisa que diga cuántos huesos reconoce.
   - Si la cabeza es una malla aparte (Hanka, Mao), sale como «+ Body».
3. **Panel Patterns**: pulsa **Add Garment**.
   - Elige la prenda: T-Shirt, Tank Top, Skirt, Pleated Skirt, Ruffled Skirt, Trousers, Jumpsuit, Dress, Jacket, Hoodie, Long Coat o Corset.
   - **Ease** es la holgura: menos es más ajustada.
   - **Length** (largo): Short, Regular o Long. Regular es la prenda tal cual; debajo sale qué significa en esa prenda (por ejemplo, en la camiseta Short es corta a la cintura y Long una túnica hasta medio muslo; en el pantalón Short es un short).
   - **Sleeves** (mangas): Regular, Short, Elbow (hasta el codo) o Long. Se miden en el brazo del avatar, así que valen igual en un avatar pequeño que en uno alto. None (sin mangas) solo sirve en el vestido.
   - En el panel **Arrangement**, cada pieza tiene Width y Length para cambiar el largo o el ancho.
4. **Panel Garments**: pulsa **Sew**. Tarda unos minutos.
   - La lista indica si quedan puntadas abiertas («open»).
   - Una o dos abiertas no se notan. Muchas significan que la prenda no encaja: prueba otra holgura.
5. **Panel Finalize**: pulsa **Finalize**. Congela la forma, suelda las costuras y pasa los pesos del avatar a la prenda.
6. *(Opcional)* **Test On The Move**: pulsa **Animate** para ver la prenda caminando y comprobar que no se abre ni atraviesa el cuerpo.

## 3. Exportar

En el panel **Finalize**:
- **Subdiv 0** y **Thickness apagado** son lo normal para VRChat.
  - El panel muestra los triángulos que tendrá la exportación, por ejemplo unos 4.000 en una camiseta.
  - Cada nivel de subdivisión multiplica los triángulos por 4, y el grosor los duplica.
  - Referencia: VRChat da a un avatar entero en PC el rango Excellent hasta 32.000 triángulos y Good hasta 70.000, y la ropa se suma al avatar. En Quest el SDK avisa a partir de 20.000.
- **Export FBX** guarda la prenda con una copia de los huesos del avatar que usa, terminados en `_OpenSew`.

La prenda lleva dos mapas UV:
- **UVMap** (el primero, el que usa Unity): todas las piezas planas, sin solaparse, dentro del cuadrado 0–1. Es para pintar una textura propia, en Substance, Krita o Photoshop.
- **Fabric**: el patrón en metros (1 unidad = 1 m). Es para una tela que se repite, como cuadros, encaje o terciopelo.

## 4. Instalar en el avatar (Unity)

1. Copia el FBX dentro de `Assets/`.
2. Pon el avatar en la escena.
3. Abre **Tools > OpenSew > Instalar ropa (Modular Avatar)**.
4. Elige el avatar de la escena y el FBX.
5. Deja **lilToon** y **Doble cara** marcados. «Doble cara» hace que se vea el interior de las mangas, porque la prenda se exporta sin grosor.
6. Pulsa **Instalar**. Se crean:
   - la carpeta `<prenda>_OpenSew/`, con el material lilToon;
   - el prefab `<prenda>_MA.prefab`, ya configurado con Modular Avatar (Merge Armature).
7. Entra en **Play** y mueve el avatar para comprobar que la ropa le sigue.

**Para ponerle textura**:
1. Selecciona el material lilToon de `<prenda>_OpenSew/`.
2. Arrastra tu imagen a **Main Texture**.

## 5. Empaquetar para vender

1. Abre **Tools > OpenSew > Empaquetar para vender**.
2. Elige el prefab `<prenda>_MA` y escribe el nombre del producto, la tienda y el avatar.
3. Pulsa **Exportar .unitypackage**. El paquete lleva:
   - el FBX, el material, las texturas y el prefab;
   - un `LEEME_<producto>.txt` con los requisitos y el uso, en español y en inglés.

**No van dentro**: lilToon, Modular Avatar, el VRChat SDK ni el avatar. El comprador ya los tiene o los instala él, como en cualquier ropa de Booth.

El comprador importa el paquete y arrastra el prefab sobre su avatar. Modular Avatar une la ropa al esqueleto al entrar en Play o al subir el avatar.

## Licencia

OpenSew 2 es GPL-3.0-or-later. Es un fork del add-on de Marcello Morettoni.
- **Las prendas que hagas con él son tuyas**: en general, la GPL cubre el código del programa, no lo que produces con él. No es asesoría legal.
- **Si publicas el add-on modificado**, el código tiene que ir público y con la misma licencia.

## Limitaciones conocidas

- La capucha puesta deja un hueco en la nuca en avatares de cabeza grande, como Hanka. En Mao no funciona.
- En la falda de volantes, el frente queda unos centímetros más alto en la figura de mujer.
- Probado de punta a punta en Unity con Hanka y Manuka. Otros avatares necesitan su propia prueba.
