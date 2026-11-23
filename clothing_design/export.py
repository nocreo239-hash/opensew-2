# Export finished garments as a VRChat outfit FBX for Modular Avatar.
#
# The FBX holds the garments, already bound, and a copy of the avatar's
# armature trimmed to the bones they use. Modular Avatar's Setup Outfit then
# merges that armature into the avatar's (docs: "Requirements and
# Recommendations for Outfit Creators"):
#   * it looks for OutfitRoot -> Armature -> Hips, and the outfit's hip bone
#     must contain the avatar's hip bone name; any extra text must be the same
#     on every bone (it is inferred as a prefix/suffix and is case sensitive);
#   * bone positions must match the avatar's, rotation axes need not;
#   * the armature and bones should not have exactly the avatar's names.
# So every bone keeps its avatar name plus one common suffix, and the bones
# stay exactly where the avatar's are (rest pose, same world transform).
import bpy
from mathutils import kdtree

from . import avatar
from . import shrink as cd_shrink

DEFAULT_SUFFIX = "_OpenSew"
MAX_INFLUENCES = 4          # Unity skins with up to four bones per vertex


class ExportError(Exception):
    pass


def finished_garments(context):
    """Garment objects that have been finalized: bound to the rig, no cloth."""
    out = []
    for o in context.scene.objects:
        if not (o.type == 'MESH' and o.cd.is_garment):
            continue
        if any(m.type == 'CLOTH' for m in o.modifiers):
            continue
        if any(m.type == 'ARMATURE' and m.object for m in o.modifiers):
            out.append(o)
    return out


def _baked_copy(context, g, coll, subdiv=None, thickness=True):
    """A plain mesh of the garment in the rest pose with every modifier but the
    armature applied, keeping its vertex groups. subdiv (levels, None for the
    viewport's) and thickness choose how much of the subdivision and solidify
    goes into it."""
    arm_mods = [(m, m.show_viewport) for m in g.modifiers if m.type == 'ARMATURE']
    for m, _ in arm_mods:
        m.show_viewport = False
    sub_mods = [(m, m.levels) for m in g.modifiers if m.type == 'SUBSURF']
    if subdiv is not None:
        for m, _ in sub_mods:
            m.levels = subdiv
    sol_mods = [(m, m.show_viewport) for m in g.modifiers if m.type == 'SOLIDIFY']
    if not thickness:
        for m, _ in sol_mods:
            m.show_viewport = False
    try:
        dg = context.evaluated_depsgraph_get()
        dg.update()
        ge = g.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ge, preserve_all_data_layers=True, depsgraph=dg)
    finally:
        for m, vis in arm_mods + sol_mods:
            m.show_viewport = vis
        for m, lv in sub_mods:
            m.levels = lv
    name = g.cd.garment or g.name
    ob = bpy.data.objects.new(name, me)
    for vg in g.vertex_groups:          # same order: the mesh's weights index these
        ob.vertex_groups.new(name=vg.name)
    ob.matrix_world = g.matrix_world.copy()
    coll.objects.link(ob)
    # one material per garment, named after it: the pattern pieces all share
    # CD_Fabric, and two outfits arriving in Unity with the same material name
    # are easy to mix up when texturing
    mat = _garment_material(g, name)
    if me.materials:
        for i in range(len(me.materials)):
            me.materials[i] = mat
    else:
        me.materials.append(mat)
    return ob


def _garment_material(g, name):
    """The garment's own material for the export, named after it: a copy of
    its fabric material (colour and all), or a plain one in its object colour."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    src = g.data.materials[0] if g.data.materials else None
    if src is not None:
        mat = src.copy()
        mat.name = name
    else:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = tuple(g.color)
    return mat


def clean_weights(ob, bones, max_influences=MAX_INFLUENCES):
    """Keep only bone groups, at most max_influences per vertex, normalized;
    a vertex left with no weight takes its nearest weighted neighbour's.
    Returns (vertices refilled, vertices trimmed)."""
    for vg in list(ob.vertex_groups):
        if vg.name not in bones:
            ob.vertex_groups.remove(vg)
    me = ob.data
    groups = ob.vertex_groups
    weights = []
    for v in me.vertices:
        ws = sorted(((g.group, g.weight) for g in v.groups if g.weight > 1e-4),
                    key=lambda t: -t[1])
        weights.append(ws)
    trimmed = sum(1 for ws in weights if len(ws) > max_influences)
    have = [i for i, ws in enumerate(weights) if ws]
    if not have:
        raise ExportError("%s has no weights to the armature" % ob.name)
    refilled = 0
    if len(have) < len(weights):
        kd = kdtree.KDTree(len(have))
        for n, i in enumerate(have):
            kd.insert(me.vertices[i].co, n)
        kd.balance()
        for i, ws in enumerate(weights):
            if not ws:
                _, n, _ = kd.find(me.vertices[i].co)
                weights[i] = list(weights[have[n]])
                refilled += 1
    for i, ws in enumerate(weights):
        ws = ws[:max_influences]
        total = sum(w for _, w in ws)
        weights[i] = [(gi, w / total) for gi, w in ws]
    # rewrite: clear every group, then add back per group in one call per weight
    for vg in groups:
        vg.remove(range(len(me.vertices)))
    by_group = {}
    for i, ws in enumerate(weights):
        for gi, w in ws:
            by_group.setdefault((gi, round(w, 6)), []).append(i)
    for (gi, w), idx in by_group.items():
        groups[gi].add(idx, w, 'REPLACE')
    # the weight transfer makes a group for every bone of the avatar, most of
    # them empty: drop those so only the bones in use are exported
    used = {gi for ws in weights for gi, _ in ws}
    for vg in [groups[i] for i in range(len(groups)) if i not in used]:
        groups.remove(vg)
    return refilled, trimmed


def _armature_copy(context, arm, keep, suffix, coll):
    data = arm.data.copy()
    data.pose_position = 'REST'
    ob = bpy.data.objects.new("Armature" + suffix, data)
    ob.matrix_world = arm.matrix_world.copy()
    coll.objects.link(ob)
    # drop the bones no garment uses, keeping the chain up to the root.
    # (mode_set ignores a temp_override's active object: make it active.)
    vl = context.view_layer
    prev = vl.objects.active
    vl.objects.active = ob
    ob.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        for eb in list(data.edit_bones):
            if eb.name not in keep:
                data.edit_bones.remove(eb)
        bpy.ops.object.mode_set(mode='OBJECT')
    finally:
        ob.select_set(False)
        vl.objects.active = prev
    if len(data.bones) != len(keep):
        raise ExportError("could not trim the armature (%d bones, %d wanted)"
                          % (len(data.bones), len(keep)))
    return ob


def _keep_bones(arm, used):
    keep = set()
    bones = arm.data.bones
    for name in used:
        b = bones.get(name)
        while b is not None and b.name not in keep:
            keep.add(b.name)
            b = b.parent
    return keep


def triangle_count(g, subdiv=0, thickness=False):
    """Triangles the export of garment g will have: the cage's, four times per
    subdivision level, and the solidify's two shells plus their rim."""
    me = g.data
    base = sum(len(p.vertices) - 2 for p in me.polygons)
    tris = base * 4 ** subdiv
    if thickness and any(m.type == 'SOLIDIFY' and m.show_viewport for m in g.modifiers):
        cnt = {}
        for p in me.polygons:
            for k in p.edge_keys:
                cnt[k] = cnt.get(k, 0) + 1
        boundary = sum(1 for n in cnt.values() if n == 1)
        tris = tris * 2 + boundary * 2 ** subdiv * 2
    return tris


MASK_SIZE = 1024


def export_body_mask(context, filepath, garments, size=MASK_SIZE):
    """Next to the FBX: <name>_mask_<slot>.png, black where the avatar's body
    is hidden for good under the garments, and <name>.opensew.json naming the
    body and its material slots, for the Unity installer to set up Modular
    Avatar's Mesh Cutter. The body itself is not written."""
    import json, os
    av = context.scene.cd.avatar
    if av is None or av.type != 'MESH':
        return None
    cover = cd_shrink.Cover(context, av, garments)
    hidden = cover.hidden()
    masks = cd_shrink.mask_images(av, hidden, size)
    base = os.path.splitext(filepath)[0]
    entries = []
    for slot, pixels in sorted(masks.items()):
        path = "%s_mask_%d.png" % (base, slot)
        cd_shrink.save_mask(pixels, size, path)
        mat = av.data.materials[slot] if slot < len(av.data.materials) and av.data.materials[slot] else None
        entries.append({"material_index": slot, "material": mat.name if mat else "",
                        "file": os.path.basename(path)})
    meta = {"generator": "OpenSew 2", "body": av.name,
            "uv": av.data.uv_layers[0].name if av.data.uv_layers else "",
            "hidden_vertices": sum(hidden), "body_vertices": len(hidden), "masks": entries}
    with open(base + ".opensew.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta


def export_outfit(context, filepath, suffix=DEFAULT_SUFFIX, garments=None,
                  subdiv=None, thickness=None, body_mask=None):
    """Write the finished garments and a trimmed copy of the avatar's armature
    to filepath. subdiv and thickness default to the scene's export settings.
    Returns a dict describing what was written."""
    scn = context.scene
    if subdiv is None:
        subdiv = scn.cd.export_subdiv
    if thickness is None:
        thickness = scn.cd.export_thickness
    if body_mask is None:
        body_mask = scn.cd.export_body_mask
    av = scn.cd.avatar
    arm = avatar.find_armature(av) if av else None
    if arm is None:
        raise ExportError("Set an avatar with an armature first")
    garments = garments or finished_garments(context)
    if not garments:
        raise ExportError("No finished garment: sew and Finalize first")
    if context.object and context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bones = {b.name for b in arm.data.bones}
    coll = bpy.data.collections.new("CD_Export")
    scn.collection.children.link(coll)
    made_obs, made_meshes = [], []
    mats_before = set(bpy.data.materials.keys())
    info = {"garments": [], "bones": 0, "refilled": 0, "trimmed": 0, "triangles": 0}
    try:
        meshes = []
        for g in garments:
            ob = _baked_copy(context, g, coll, subdiv, thickness)
            made_obs.append(ob); made_meshes.append(ob.data)
            refilled, trimmed = clean_weights(ob, bones)
            info["refilled"] += refilled
            info["trimmed"] += trimmed
            info["garments"].append(ob.name)
            info["triangles"] += sum(len(p.vertices) - 2 for p in ob.data.polygons)
            meshes.append(ob)
        used = {vg.name for ob in meshes for vg in ob.vertex_groups}
        keep = _keep_bones(arm, used)
        ao = _armature_copy(context, arm, keep, suffix, coll)
        made_obs.append(ao)
        info["bones"] = len(ao.data.bones)
        # the suffix on every bone, and on the groups that point at them
        for b in ao.data.bones:
            b.name = b.name + suffix
        for ob in meshes:
            for vg in ob.vertex_groups:
                if not vg.name.endswith(suffix):
                    vg.name = vg.name + suffix
            mw = ob.matrix_world.copy()
            ob.parent = ao
            ob.matrix_world = mw
            mod = ob.modifiers.new("Armature", 'ARMATURE')
            mod.object = ao

        for o in context.selected_objects:
            o.select_set(False)
        for o in made_obs:
            o.select_set(True)
        context.view_layer.objects.active = ao
        with context.temp_override(active_object=ao, object=ao,
                                   selected_objects=made_obs, selected_editable_objects=made_obs):
            bpy.ops.export_scene.fbx(
                filepath=filepath, use_selection=True,
                object_types={'ARMATURE', 'MESH'},
                use_mesh_modifiers=True, mesh_smooth_type='FACE',
                add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                use_armature_deform_only=False, armature_nodetype='NULL',
                bake_anim=False, apply_scale_options='FBX_SCALE_ALL',
                axis_forward='-Z', axis_up='Y', path_mode='COPY', embed_textures=False)
        info["armature"] = ao.name
        info["hips"] = next((b.name for b in ao.data.bones if b.parent is None), "")
    finally:
        for ob in made_obs:
            data = ob.data
            bpy.data.objects.remove(ob)
            if isinstance(data, bpy.types.Armature):
                bpy.data.armatures.remove(data)
        for me in made_meshes:
            if me.users == 0:
                bpy.data.meshes.remove(me)
        for name in set(bpy.data.materials.keys()) - mats_before:
            mat = bpy.data.materials.get(name)
            if mat is not None and mat.users == 0:
                bpy.data.materials.remove(mat)
        bpy.data.collections.remove(coll)
    info["path"] = filepath
    info["mask"] = export_body_mask(context, filepath, garments) if body_mask else None
    return info
