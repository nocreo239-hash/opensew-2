# Clothing Design - humanoid bone naming.
#
# Avatars sold for social VR (VRChat and similar) mostly follow Unity's
# humanoid naming, but every author spells it differently: "UpperArm_L",
# "Upper Arm.L", "Upperarm_L", "Left Hand", "LeftUpperArm", "J_Bip_L_UpperArm".
# The same rigs carry dozens of physics and cloth bones whose names contain the
# body-part words ("neckless", "Spine.002outer_L", "Waistbelt_Root",
# "W_Upper Arm.Twist.L", "IK.Foot.L"), so matching a substring picks the wrong
# bone. Here a name is normalised as a whole - namespace and prefixes stripped,
# the side pulled out, separators removed - and only an exact match on the
# remaining word counts.
import re

L, R = ".l", ".r"

# canonical part -> spellings of the part word, once side and separators are gone
ALIASES = {
    "hips":       ("hips", "hip", "pelvis"),
    "spine":      ("spine",),
    "chest":      ("chest",),
    "upper_chest": ("upperchest",),
    "neck":       ("neck",),
    "head":       ("head",),
    "shoulder":   ("shoulder", "clavicle"),
    "upper_arm":  ("upperarm", "uparm"),
    "lower_arm":  ("lowerarm", "forearm", "lowarm"),
    "hand":       ("hand", "wrist"),
    "upper_leg":  ("upperleg", "upleg", "thigh"),
    "lower_leg":  ("lowerleg", "lowleg", "shin", "calf"),
    "foot":       ("foot", "ankle"),
    "toe":        ("toe", "toes", "toebase"),
}
SIDED = {"shoulder", "upper_arm", "lower_arm", "hand", "upper_leg", "lower_leg",
         "foot", "toe"}
_LOOKUP = {a: k for k, al in ALIASES.items() for a in al}

_FINGER = re.compile(r"^(thumb|index|middle|ring|little|pinky|pinkie)"
                     r"(proximal|intermediate|distal|metacarpal|[0-9])?$")

# helper, IK and secondary bones: never a body part even if the word matches
_REJECT_TOKENS = {"ik", "fk", "mch", "org", "ctrl", "ctl", "pole", "target",
                  "helper", "end", "tip", "w", "z", "adj", "socket", "null"}
_REJECT_SUB = ("twist", "roll", "share")

_PREFIXES = ("cc_base_", "j_bip_c_", "j_bip_l_", "j_bip_r_", "j_bip_", "j_",
             "def-", "def_", "bip01_", "bip001_", "bip01 ", "bip001 ")


def parse(name):
    """(part, side) for a bone or vertex group name, or (None, None).

    part is a key of ALIASES (or 'finger_<name>'), side is '.l', '.r' or ''.
    """
    n = name.strip().lower()
    if ":" in n:                         # mixamorig:LeftArm, Armature|Hips
        n = n.rsplit(":", 1)[1]
    n = n.rsplit("|", 1)[-1]
    side = ""
    # VRM spells the side inside its prefix: J_Bip_L_UpperArm
    m = re.match(r"^j_bip_([lr])_", n)
    if m:
        side = L if m.group(1) == "l" else R
    for p in _PREFIXES:
        if n.startswith(p):
            n = n[len(p):]
            break
    tokens = [t for t in re.split(r"[\s._\-]+", n) if t]
    if not tokens:
        return None, None
    if any(t in _REJECT_TOKENS for t in tokens) or any(s in n for s in _REJECT_SUB):
        return None, None
    # side as a separate token at either end: UpperArm_L, L_UpperArm, Hand.R
    if not side and len(tokens) > 1:
        if tokens[-1] in ("l", "left", "r", "right"):
            side = L if tokens[-1] in ("l", "left") else R
            tokens = tokens[:-1]
        elif tokens[0] in ("l", "left", "r", "right"):
            side = L if tokens[0] in ("l", "left") else R
            tokens = tokens[1:]
    core = "".join(tokens)
    # side glued to the word: LeftUpperArm, RightHand
    if not side:
        for word, s in (("left", L), ("right", R)):
            if core.startswith(word) and len(core) > len(word):
                core, side = core[len(word):], s
                break
            if core.endswith(word) and len(core) > len(word):
                core, side = core[:-len(word)], s
                break
    part = _LOOKUP.get(core)
    if part is None and core in ("elbow", "knee") and side:
        # CATS / MMD English name the forearm and shin after the joint (Left
        # elbow, Left knee), but rigs also carry corrective "Knee_L" bones
        # beside the real shin (Vlau): weak, see humanoid_map
        return "_" + core, side
    if part is None and core in ("arm", "leg") and side:
        # Mixamo's words (LeftArm + LeftForeArm, LeftUpLeg + LeftLeg), also
        # spelled Left_Arm on avatars built from a Mixamo skeleton (Vlau):
        # only meaningful next to the bone it pairs with, see humanoid_map
        return "_" + core, side
    if part is None:
        f = _FINGER.match(core)
        if f and side:
            fn = f.group(1)
            fn = {"pinkie": "pinky", "little": "pinky"}.get(fn, fn)
            return "finger_" + fn, side
        return None, None
    if part in SIDED and not side:
        return None, None                 # a lone "Hand" or "Foot" is ambiguous
    if part not in SIDED and side:
        return None, None                 # Rigify's DEF-pelvis.L is not the hips
    return part, side


def humanoid_map(arm):
    """{'upper_arm.l': pose bone, 'hips': pose bone, ...} for an armature object.

    When two bones normalise to the same part (Mao has 'Right Hand' and
    'Right Hand.001') the one nearest the root wins: duplicates are almost
    always children added for accessories."""
    if arm is None or arm.type != 'ARMATURE':
        return {}
    # Rigify names its pelvis "spine" and numbers the rest spine.001...; leave
    # those rigs to the Rigify entries in the avatar tables
    rigify = "spine.001" in arm.pose.bones
    out = {}
    amb = {}
    for pb in arm.pose.bones:
        part, side = parse(pb.name)
        if part is None or (rigify and part == "spine"):
            continue
        key = part + side
        if part.startswith("_"):
            amb.setdefault(key, []).append(pb)
            continue
        depth = len(pb.parent_recursive)
        prev = out.get(key)
        if prev is None or depth < prev[0]:
            out[key] = (depth, pb)
    res = {k: v[1] for k, v in out.items()}

    def above(pb):
        # the parent, looking past twist and roll bones: an MMD rig not run
        # through CATS' Fix Model has Left arm > Left arm twist > Left elbow
        p = pb.parent
        while p is not None and any(t in p.name.lower() for t in _REJECT_SUB):
            p = p.parent
        return p

    def resolve(rules):
        for s_ in (L, R):
            for word, part, pair, rel in rules:
                if part + s_ in res:
                    continue
                other = res.get(pair + s_)
                if other is None:
                    continue
                for pb in amb.get(word + s_, []):
                    # compare by name: bpy hands out a new wrapper on each access
                    if rel == "parent_of":
                        up = above(other)
                        if up is not None and up.name == pb.name:
                            res[part + s_] = pb
                            break
                    else:
                        up = above(pb)
                        if up is not None and up.name == other.name:
                            res[part + s_] = pb
                            break

    # Mixamo first: "Leg" is the shin when it hangs from an UpLeg
    resolve((("_leg", "lower_leg", "upper_leg", "child_of"),))
    # then the joint names, only where no forearm or shin was found and only
    # for a bone the hand or foot hangs from - a corrective "Knee_L" beside
    # the real shin, or a "Knee.L" physics bone off the hips, never qualifies
    resolve((("_elbow", "lower_arm", "hand", "parent_of"),
             ("_knee", "lower_leg", "foot", "parent_of")))
    # and last "Arm" is the upper arm when a forearm hangs below it, "Leg" the
    # thigh when a shin does (CATS: Left leg > Left knee > Left ankle). The
    # checks keep this from firing where "Leg_L" means the whole leg.
    resolve((("_arm", "upper_arm", "lower_arm", "parent_of"),
             ("_leg", "upper_leg", "lower_leg", "parent_of")))
    return res


# Labels in the vocabulary the measuring code already keys on (Rigify style),
# so its keyword tables keep working unchanged for every naming scheme.
_LABEL = {"upper_arm": "upper_arm", "lower_arm": "forearm", "hand": "hand",
          "upper_leg": "thigh", "lower_leg": "shin", "foot": "foot", "toe": "toe",
          "shoulder": "shoulder", "upper_chest": "chest"}


def bone_labels(arm):
    """{bone name: label} for the humanoid bones of an armature, with the same
    labels group_label gives ('thigh.l', 'upper_arm.r', 'hips'), but decided
    with the whole skeleton in view, so ambiguous names come out right."""
    out = {}
    for key, pb in humanoid_map(arm).items():
        part, side = (key[:-2], key[-2:]) if key.endswith((L, R)) else (key, "")
        if part.startswith("finger_"):
            part = part[7:]             # as group_label: 'index.l', not 'finger_index.l'
        out[pb.name] = _LABEL.get(part, part) + side
    return out


def group_label(name):
    """Normalised, lower-case label for a vertex group name: 'Upper Arm.L' and
    'UpperArm_L' both become 'upper_arm.l'. Names that are not a humanoid part
    come back lower-cased and otherwise unchanged."""
    part, side = parse(name)
    if part is None:
        # skin weights painted on a twist or cloth-helper bone still belong to
        # that limb: Hanka's UpperArm_Twist_L, Minase's W_Upper Arm.Twist.L
        stripped = re.sub(r"(?i)(^|[\s._\-])(w|z|twist|roll|share|adj)(?=$|[\s._\-])",
                          " ", name)
        stripped = re.sub(r"(?i)twist|roll", " ", stripped)
        # and the numbered segments a twist chain comes in: Left_Arm_Twist_00
        stripped = re.sub(r"(^|[\s._\-])\d{1,3}(?=$|[\s._\-])", " ", stripped)
        if stripped != name:
            part, side = parse(stripped)
    if part is None:
        return name.lower()
    if part.startswith("finger_"):
        return part[7:] + side
    if part == "_arm":
        return "upper_arm" + side          # a sided "Arm" group is never torso
    if part in ("_leg", "_elbow", "_knee"):
        return name.lower()
    return _LABEL.get(part, part) + side


def is_head_group(name):
    """Whether a vertex group belongs to the head: the head or neck bone, or
    the eyes, jaw and mouth that hang off it (SK_L_Eye, Eye.weight.L, Jaw).
    Exact parts only - Mao's necklace bones are called "neckless"."""
    part, _ = parse(name)
    if part in ("head", "neck"):
        return True
    toks = re.split(r"[\s._\-:]+", name.lower())
    return any(t in ("eye", "eyes", "jaw", "teeth", "tooth", "tongue", "thooth",
                     "thoothupper", "thoothlower") for t in toks) or \
        bool(re.match(r"^(eye|jaw|teeth|tongue)", name.lower()))


def describe(arm):
    """Short summary for the UI and reports: which humanoid parts were found."""
    hm = humanoid_map(arm)
    want = ["hips", "spine", "chest", "neck", "head"] + [
        p + s for p in ("upper_arm", "lower_arm", "hand", "upper_leg", "lower_leg", "foot")
        for s in (L, R)]
    found = [k for k in want if k in hm]
    return {"found": len(found), "of": len(want),
            "missing": [k for k in want if k not in hm],
            "bones": {k: hm[k].name for k in found}}
