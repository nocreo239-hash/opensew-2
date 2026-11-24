# Clothing Design - sidebar UI.
import bpy
from bpy.types import Panel, UIList, Menu
from . import avatar, library, build, patterns, fitpose
from . import export as cd_export

CAT = "Clothing"


class CD_UL_seams(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_prop, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="", emboss=False,
                 icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT')
        a = item.obj_a.name.split("_")[-1] if item.obj_a else "?"
        b = item.obj_b.name.split("_")[-1] if item.obj_b else "?"
        row.label(text="%s.%s" % (a, item.seg_a), icon='OUTLINER_DATA_SURFACE')
        row.label(text="", icon='FORWARD')
        row.label(text="%s.%s" % (b, item.seg_b))
        row.prop(item, "flip", text="", icon='ARROW_LEFTRIGHT', emboss=item.flip)

    def filter_items(self, context, data, propname):
        """Show only the active garment's seams."""
        items = getattr(data, propname)
        g = context.scene.cd.garment_name
        flt = []
        for s in items:
            keep = (s.obj_a and s.obj_b and
                    (s.obj_a.cd.garment == g or s.obj_b.cd.garment == g))
            flt.append(self.bitflag_filter_item if keep else 0)
        return flt, []


class CD_UL_garments(UIList):
    """All garments in the scene, innermost layer first."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_prop, index):
        # fixed shares, so the status stays readable in a narrow sidebar
        sp = layout.split(factor=0.13, align=True)
        sp.label(text="L%d" % item.cd.layer)
        sp = sp.split(factor=0.5, align=True)
        sp.prop(item.cd, "garment", text="", emboss=False)
        row = sp.row(align=True)
        from . import build
        n = len(build.loose_edges(item.data)) if item.data else 0
        if n:
            row.label(text="%d open" % n, icon='UNLINKED')
        elif item.cd.sewn or build.is_locked(item):
            row.label(text="sewn", icon='LINKED')
        else:
            # welded but never frozen: Sew was stopped while it settled
            row.label(text="stopped", icon='ERROR')

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt = [0] * len(items)
        keys = []
        for i, ob in enumerate(items):
            if ob.cd.is_garment and ob.data and len(ob.data.vertices):
                flt[i] = self.bitflag_filter_item
            keys.append((ob.cd.layer, ob.name))
        order = [i for i, _ in sorted(enumerate(keys), key=lambda t: t[1])]
        rank = [0] * len(items)
        for pos, i in enumerate(order):
            rank[i] = pos
        return flt, rank


class _Base:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CAT


class CD_PT_avatar(_Base, Panel):
    bl_label = "Avatar"
    bl_idname = "CD_PT_avatar"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row(align=True)
        row.label(text="Default", icon='OUTLINER_OB_ARMATURE')
        row.operator("cd.import_character", text="Woman").figure = 'WOMAN'
        row.operator("cd.import_character", text="Man").figure = 'MAN'
        col = L.column(align=True)
        col.prop(scn.cd, "avatar", text="")
        row = col.row(align=True)
        row.operator("cd.set_avatar", icon='USER')
        row.operator("cd.measure", text="", icon='FILE_REFRESH')
        L.prop(scn.cd, "facing")
        row = L.row(align=True)
        row.prop(scn.cd, "fit_pose")
        sub = row.row()
        sub.active = scn.cd.fit_pose
        sub.prop(scn.cd, "fit_arm_angle", text="")
        rigob = avatar.find_armature(scn.cd.avatar) if scn.cd.avatar else None
        if rigob is not None and fitpose.is_active(rigob):
            r = L.row()
            r.label(text="Arms lowered for sewing", icon='POSE_HLT')
            r.operator("cd.rest_pose", text="T-Pose", icon='LOOP_BACK')
        row = L.row(align=True)
        row.prop(scn.cd, "figure")
        if scn.cd.avatar and scn.cd.figure == 'AUTO':
            row.label(text=avatar.figure(context).title())

        m = None
        if scn.cd.avatar and "cd_measure" in scn:
            try:
                import json
                m = json.loads(scn["cd_measure"])
            except Exception:
                m = None
        if m:
            box = L.box().column(align=True)
            box.label(text="Height  %.0f cm" % (m["height"] * 100))
            for k, lab in (("chest", "Chest"), ("waist", "Waist"), ("hip", "Hip")):
                z = avatar.z_of(m, k)
                box.label(text="%-6s  %.0f cm" % (lab, avatar.girth_at(m, z) * 100))
            box.label(text="%-6s  %.0f cm" % ("Neck", avatar.neck_girth(m) * 100))
            if m.get("armature"):
                box.label(text="Rig: %s" % m["armature"], icon='ARMATURE_DATA')
                r = m.get("rig") or {}
                nl = len(m.get("limbs", {}))
                row = box.row()
                row.alert = nl < 8
                row.label(text="Bones %d/%d, limbs %d/8" % (r.get("found", 0), r.get("of", 0), nl),
                          icon='CHECKMARK' if nl == 8 else 'ERROR')
            for c in m.get("companions", []):
                box.label(text="+ %s" % c, icon='MESH_DATA')


def _garment_step(context, g):
    """Where the garment is: 2 drafted, 3 sewn, 4 finished."""
    if g is None:
        return 1
    if g in cd_export.finished_garments(context):
        return 4
    if g.cd.sewn:
        return 3
    return 2


class CD_PT_steps(_Base, Panel):
    """The five steps from avatar to FBX, and where the selected garment is."""
    bl_label = "Steps"
    bl_idname = "CD_PT_steps"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        g = build.garment_object(context, create=False)
        step = _garment_step(context, g) if scn.cd.avatar else 0
        rows = (
            (1, "Avatar", scn.cd.avatar.name if scn.cd.avatar else "pick the body"),
            (2, "Garment", g.cd.garment if g else "add one"),
            (3, "Sew", ("quick-sewn" if g and g.cd.draft else "sewn") if step >= 3 else "Sew or Quick Sew"),
            (4, "Finalize", "finished" if step >= 4 else "Finalize"),
            (5, "Export", "FBX, then Unity" if step >= 4 else "after Finalize"),
        )
        col = L.column(align=True)
        for n, name, hint in rows:
            r = col.row().split(factor=0.45)
            done = n <= step and n < 5
            nxt = n == step + 1
            r.alert = nxt and n == 3 and g is not None and g.cd.draft
            r.label(text="%d  %s" % (n, name), icon='CHECKMARK' if done else ('PLAY' if nxt else 'DOT'))
            r.label(text=hint)
        if g is not None and g.cd.draft and step >= 3:
            L.label(text="Quick Sew: Sew again before selling", icon='INFO')


class CD_PT_patterns(_Base, Panel):
    bl_label = "Patterns"
    bl_idname = "CD_PT_patterns"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row(align=True)
        row.scale_y = 1.25
        row.operator("cd.add_garment", icon='MOD_CLOTH')
        row.operator("cd.add_outfit", text="Outfit", icon='OUTLINER_OB_GROUP_INSTANCE')

        n = len(build.garment_pieces(context))
        g = build.garment_object(context, create=False)
        if n:
            info = "%d piece%s" % (n, "" if n == 1 else "s")
            if g:
                info += "  -  %d sewing springs" % g.get("cd_sewing_edges", 0)
            L.label(text=info, icon='INFO')


class CD_PT_patterns_advanced(_Base, Panel):
    bl_label = "Advanced: Draw And Mesh"
    bl_idname = "CD_PT_patterns_advanced"
    bl_parent_id = "CD_PT_patterns"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row(align=True)
        row.operator("cd.draw_pattern", icon='GREASEPENCIL')
        row.operator("cd.counterpart", text="Counterpart", icon='MOD_MIRROR')
        row.prop(scn.cd, "draw_snap", text="")
        L.prop(scn.cd, "garment_name", text="Garment")
        col = L.column(align=True)
        col.prop(scn.cd, "resolution")
        g = build.garment_object(context, create=False)
        if g is not None and g.cd.res_scale > 1.001:
            # a big avatar is meshed coarser: say what this garment really uses
            col.label(text="This garment: x%.2f for the avatar's size (%.1f cm)"
                      % (g.cd.res_scale, scn.cd.resolution * g.cd.res_scale * 100.0), icon='INFO')
        col.prop(scn.cd, "pattern_gap")
        row = L.row(align=True)
        row.prop(scn.cd, "subdiv_levels")
        row.prop(scn.cd, "subdiv_render", text="Render")
        L.operator("cd.sync", icon='SHADERFX')
        row = L.row(align=True)
        row.prop(scn.cd, "live_sync")
        row.prop(scn.cd, "keep_off_body")


class CD_PT_garments(_Base, Panel):
    bl_label = "Garments"
    bl_idname = "CD_PT_garments"

    def draw(self, context):
        import bpy as _bpy
        scn = context.scene
        L = self.layout
        row = L.row()
        row.template_list("CD_UL_garments", "", _bpy.data, "objects",
                          scn.cd, "active_garment", rows=4)
        col = row.column(align=True)
        col.operator("cd.garment_layer", text="", icon='TRIA_UP').direction = 'UP'
        col.operator("cd.garment_layer", text="", icon='TRIA_DOWN').direction = 'DOWN'
        col.separator()
        col.operator("cd.setup_layers", text="", icon='FILE_REFRESH')

        gs = [o for o in scn.objects if o.cd.is_garment and o.data and len(o.data.vertices)]
        if len(gs) > 1:
            L.label(text="Layer 0 is worn innermost", icon='INFO')
        g = build.garment_object(context, create=False)
        if g is not None:
            row = L.row(align=True)
            row.operator("cd.change_garment", text="Change...", icon='PREFERENCES')
            row.operator("cd.remove_garment", text="Delete", icon='TRASH')
            L.prop(g.cd, "size", text="Size  (%s)" % g.cd.garment)
            if build.is_locked(g):
                box = L.box()
                box.label(text="Sewn: changes apply after Unsew", icon='LOCKED')

        col = L.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.25
        op = row.operator("cd.sew", text="Sew", icon='LINKED')
        op.all_garments, op.draft = False, False
        row.operator("cd.unsew", text="Unsew", icon='UNLINKED').all_garments = False
        row = col.row(align=True)
        op = row.operator("cd.sew", text="Sew All", icon='LINKED')
        op.all_garments, op.draft = True, False
        row.operator("cd.unsew", text="Unsew All", icon='UNLINKED').all_garments = True
        op = col.operator("cd.sew", text="Quick Sew (to check the fit)", icon='TIME')
        op.all_garments, op.draft = False, True


class CD_PT_piece(_Base, Panel):
    bl_label = "Advanced: Piece Arrangement"
    bl_idname = "CD_PT_piece"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob is not None and ob.cd.is_pattern

    def draw(self, context):
        ob = context.active_object
        L = self.layout
        L.label(text=ob.name, icon='OUTLINER_OB_SURFACE')
        g = context.scene.objects.get("CD_Garment_" + ob.cd.garment)
        if g is not None and build.is_locked(g):
            L.label(text="Sewn: changes apply after Unsew", icon='LOCKED')
        col = L.column(align=True)
        col.prop(ob.cd, "anchor")
        col.prop(ob.cd, "height", slider=True)
        col.prop(ob.cd, "spin")
        col.prop(ob.cd, "wrap", slider=True)
        if ob.cd.anchor in {'ARM_L', 'ARM_R', 'LEG_L', 'LEG_R'}:
            col.prop(ob.cd, "taper", slider=True)
        col.prop(ob.cd, "ease")
        row = L.row(align=True)
        row.prop(ob.cd, "scale_w")
        row.prop(ob.cd, "scale_l")
        L.prop(ob.cd, "shift")
        segs = patterns.segment_names(ob)
        if segs:
            box = L.box()
            box.label(text="Edges: " + ", ".join(segs), icon='EDGESEL')


class CD_PT_seams(_Base, Panel):
    bl_label = "Advanced: Seams"
    bl_idname = "CD_PT_seams"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scn = context.scene
        L = self.layout
        row = L.row()
        row.template_list("CD_UL_seams", "", scn.cd, "seams", scn.cd, "active_seam", rows=4)
        col = row.column(align=True)
        col.operator("cd.remove_seam", text="", icon='X')
        col.separator()
        col.operator("cd.clear_seams", text="", icon='TRASH')
        row = L.row(align=True)
        row.operator("cd.auto_seam", icon='AUTOMERGE_ON')
        if context.mode == 'EDIT_MESH':
            L.operator("cd.add_seam", icon='EDGESEL')


class CD_PT_sim(_Base, Panel):
    bl_label = "Advanced: Fabric And Simulation"
    bl_idname = "CD_PT_sim"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scn = context.scene
        L = self.layout
        # (the old Sew & Drape button is left out: Sew in Garments replaces it)
        row = L.row(align=True)
        row.operator("cd.reset_sim", text="Reset Simulation", icon='LOOP_BACK')
        col = L.column(align=True)
        col.prop(scn.cd, "stitch_frames")
        col.prop(scn.cd, "settle_frames")
        col.prop(scn.cd, "stitch_gravity", slider=True)
        col.prop(scn.cd, "auto_close")
        row = L.row(align=True)
        row.operator("cd.close_seams", icon='AUTOMERGE_ON')
        row.operator("cd.settle", icon='FRAME_NEXT')
        row.operator("cd.relax", icon='MOD_CLOTH')
        row = L.row(align=True)
        row.scale_y = 1.2
        row.operator("cd.grab", icon='VIEW_PAN')
        L.operator("cd.setup_sim", icon='PHYSICS')

        box = L.box().column(align=True)
        box.prop(scn.cd, "fabric", text="")
        box.prop(scn.cd, "shrink", slider=True)
        sub = box.column(align=True)
        sub.prop(scn.cd, "stiff_bend")
        sub.prop(scn.cd, "stiff_compress")
        sub.prop(scn.cd, "stiff_tension")
        sub.prop(scn.cd, "stiff_shear")
        sub.prop(scn.cd, "air_damping")
        col = L.column(align=True)
        col.prop(scn.cd, "sew_force")
        col.prop(scn.cd, "quality")
        col.prop(scn.cd, "mass")
        box = L.box().column(align=True)
        box.prop(scn.cd, "self_collision")
        box.prop(scn.cd, "coll_distance")


class CD_PT_finalize(_Base, Panel):
    bl_label = "Finalize"
    bl_idname = "CD_PT_finalize"

    def draw(self, context):
        scn = context.scene
        L = self.layout
        col = L.column(align=True)
        col.prop(scn.cd, "weld_seams")
        sub = col.row()
        sub.enabled = scn.cd.weld_seams
        sub.prop(scn.cd, "weld_dist")
        col.prop(scn.cd, "thickness")
        col.prop(scn.cd, "bind_armature")
        sub = col.row()
        sub.enabled = scn.cd.bind_armature
        sub.prop(scn.cd, "weight_method")
        row = L.row(align=True)
        row.scale_y = 1.25
        row.operator("cd.finalize", text="Finalize", icon='CHECKMARK').all_garments = False
        row.operator("cd.finalize", text="Finalize All", icon='CHECKMARK').all_garments = True
        col = L.column(align=True)
        row = col.row(align=True)
        row.prop(scn.cd, "export_subdiv", text="Subdiv")
        row.prop(scn.cd, "export_thickness", text="Thickness", toggle=True)
        done = cd_export.finished_garments(context)
        if done:
            tris = sum(cd_export.triangle_count(g, scn.cd.export_subdiv, scn.cd.export_thickness)
                       for g in done)
            # VRChat's PC ranks (creators.vrchat.com, Performance Ranks): an
            # avatar is Excellent up to 32,000 triangles and Good up to 70,000,
            # and the garment adds to the avatar's own
            icon = 'CHECKMARK' if tris <= 10000 else ('INFO' if tris <= 20000 else 'ERROR')
            col.label(text="%s triangles in the export" % format(tris, ","), icon=icon)
        row = col.row(align=True)
        row.prop(scn.cd, "export_body_mask", text="Hide Body Under It", toggle=True)
        row.operator("cd.shrink_body", text="", icon='SHAPEKEY_DATA')
        L.prop(scn.cd, "export_suffix", text="Suffix")
        row = L.row(align=True)
        row.scale_y = 1.25
        row.operator("cd.export_vrchat", text="Export All", icon='EXPORT').only_active = False
        row.operator("cd.export_vrchat", text="Export Selected", icon='EXPORT').only_active = True
        L.label(text="Copy the .fbx, .opensew.json and _mask PNGs to Unity together", icon='INFO')

        # Walking the avatar is the last step: a garment that looks right on a
        # still figure can still slide, gape at the armhole or clip through a
        # thigh once the body moves.
        bound = [o for o in scn.objects if o.cd.is_garment
                 and any(m.type == 'ARMATURE' for m in o.modifiers)]
        box = L.box()
        box.label(text="Test On The Move", icon='ARMATURE_DATA')
        row = box.row(align=True)
        row.scale_y = 1.2
        row.operator("cd.animate", icon='PLAY')
        row.operator("cd.rest_pose", text="", icon='LOOP_BACK')
        if not bound:
            box.label(text="Finalize first (with Bind To Armature on)", icon='INFO')


class CD_PT_workspace(_Base, Panel):
    bl_label = "Workspace"
    bl_idname = "CD_PT_workspace"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        L = self.layout
        if bpy.data.workspaces.get("Clothing Design"):
            L.label(text="Workspace tab is present", icon='CHECKMARK')
        L.operator("cd.build_workspace", icon='WORKSPACE')
        try:
            prefs = context.preferences.addons[__package__].preferences
            L.prop(prefs, "auto_workspace")
        except Exception:
            pass
        row = L.row(align=True)
        row.operator("cd.frame_view", text="Frame 2D").target = '2D'
        row.operator("cd.frame_view", text="Frame Body").target = '3D'


def _add_menu(self, context):
    self.layout.separator()
    self.layout.operator("cd.add_garment", text="Garment Pattern", icon='MOD_CLOTH')


CLASSES = (CD_UL_seams, CD_UL_garments, CD_PT_steps, CD_PT_avatar, CD_PT_patterns,
           CD_PT_patterns_advanced, CD_PT_garments, CD_PT_finalize,
           CD_PT_piece, CD_PT_seams, CD_PT_sim, CD_PT_workspace)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_add.append(_add_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(_add_menu)
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
