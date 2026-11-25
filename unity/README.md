# OpenSew en Unity (VRChat, Modular Avatar, lilToon)

Script de editor que instala en un avatar la ropa exportada desde Blender con
el botón **Export FBX** del add-on.

## Requisitos

- Proyecto de avatar de VRChat (VCC) con el avatar en la escena.
- [Modular Avatar](https://modular-avatar.nadena.dev) (probado contra el código de la 1.19.0).
- [lilToon](https://github.com/lilxyzw/lilToon) (probado contra el código de la 2.4.1).

Si falta Modular Avatar, el script crea igualmente el prefab con materiales;
si falta lilToon, deja los materiales del FBX. Ninguno de los dos es una
referencia de ensamblado, así que el script compila siempre.

## Instalación

Copia la carpeta `Assets/OpenSew` dentro de la carpeta `Assets` del proyecto.

## Uso

1. Arrastra el `.fbx` exportado a la carpeta del proyecto (por ejemplo `Assets/Ropa/`).
2. **Tools > OpenSew > Instalar ropa (Modular Avatar)**.
3. Elige el avatar de la escena (la raíz con el VRC Avatar Descriptor) y el FBX.
4. **Crear prefab e instalar en el avatar**.

El script:

1. crea materiales lilToon en `<carpeta del FBX>/<nombre>_OpenSew/`, copiando
   color y textura de los del FBX (doble cara por defecto, para ver el
   interior de mangas y cuello);
2. mete la ropa dentro del avatar con esos materiales;
3. ejecuta el **Setup Outfit** de Modular Avatar, que añade *Merge Armature*
   (objetivo: la armadura del avatar), *Outfit Root* y *Mesh Settings*, y
   deduce el sufijo `_OpenSew` de los huesos;
4. guarda el resultado como `<nombre>_MA.prefab` (un "Modular Avatar Preset"):
   ese prefab se puede arrastrar a otra copia del mismo avatar.

## Qué lleva el FBX

- La ropa ya pesada a los huesos del avatar: como mucho 4 huesos por vértice
  (el límite de Unity), pesos normalizados.
- Una copia de la armadura del avatar con solo los huesos que usa la ropa y
  sus padres, cada uno con el sufijo `_OpenSew` (Modular Avatar lo quita al
  fusionar; además evita que la ropa tenga exactamente los nombres del avatar,
  algo que su documentación desaconseja).
- Los huesos en la misma posición que los del avatar, en la pose de reposo.

## Licencia

GPL-3.0, como el add-on OpenSew 2.
