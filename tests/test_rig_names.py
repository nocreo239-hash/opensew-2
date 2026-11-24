# Bone and vertex-group name recognition (clothing_design/rig.py).
#
#   python tests/test_rig_names.py
#
# Plain Python: rig.py does not import bpy, and the armature lookups run on
# small stand-in objects. The names come from real avatars - Hanka, Mao,
# Minase, Vlau (Booth), Mixamo, CC4, Rigify and VRM exports.
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "rig", os.path.join(HERE, "..", "clothing_design", "rig.py"))
rig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rig)

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print("  FAIL", msg)


L, R = ".l", ".r"
PARSE = {
    # Unity humanoid as Booth authors spell it
    "Hips": ("hips", ""), "Spine": ("spine", ""), "Chest": ("chest", ""),
    "UpperChest": ("upper_chest", ""), "Upper Chest": ("upper_chest", ""),
    "Neck": ("neck", ""), "Head": ("head", ""),
    "Shoulder_L": ("shoulder", L), "Shoulder.R": ("shoulder", R),
    "UpperArm_L": ("upper_arm", L), "UpperArm.L": ("upper_arm", L),
    "UpperArm_R": ("upper_arm", R), "Upper Arm.L": ("upper_arm", L),
    "Upperarm_R": ("upper_arm", R), "upperarm.r": ("upper_arm", R),
    "LowerArm_L": ("lower_arm", L), "Lower Arm.R": ("lower_arm", R),
    "Lowerarm_L": ("lower_arm", L),
    "Hand_L": ("hand", L), "Hand.R": ("hand", R), "Left Hand": ("hand", L),
    "Right Hand": ("hand", R), "hand_l": ("hand", L),
    "UpperLeg_L": ("upper_leg", L), "Upper Leg.R": ("upper_leg", R),
    "Upperleg_L": ("upper_leg", L),
    "LowerLeg_R": ("lower_leg", R), "Lower Leg.L": ("lower_leg", L),
    "Foot_L": ("foot", L), "Foot.R": ("foot", R),
    "Toe_L": ("toe", L), "Toes.R": ("toe", R),
    # side as a prefix, glued or separated
    "Left UpperArm": ("upper_arm", L), "Right UpperLeg": ("upper_leg", R),
    "LeftUpperArm": ("upper_arm", L), "RightLowerLeg": ("lower_leg", R),
    "L_UpperArm": ("upper_arm", L), "R_Hand": ("hand", R),
    "Left_UpperLeg": ("upper_leg", L), "Left_ForeArm": ("lower_arm", L),
    "UpperArmLeft": ("upper_arm", L),
    # namespaces and exporter prefixes
    "mixamorig:Hips": ("hips", ""), "mixamorig:LeftForeArm": ("lower_arm", L),
    "mixamorig:LeftUpLeg": ("upper_leg", L), "mixamorig1:RightHand": ("hand", R),
    "Armature|UpperArm_L": ("upper_arm", L),
    "CC_Base_L_Upperarm": ("upper_arm", L), "CC_Base_R_Thigh": ("upper_leg", R),
    "CC_Base_Pelvis": ("hips", ""), "CC_Base_L_Calf": ("lower_leg", L),
    "DEF-upper_arm.L": ("upper_arm", L), "DEF-thigh.R": ("upper_leg", R),
    "J_Bip_C_Hips": ("hips", ""), "J_Bip_L_UpperArm": ("upper_arm", L),
    "J_Bip_R_LowerLeg": ("lower_leg", R), "J_Bip_C_UpperChest": ("upper_chest", ""),
    "Bip01 L UpperArm": ("upper_arm", L),
    # fingers
    "Index Proximal.L": ("finger_index", L), "LittleProximal_L": ("finger_pinky", L),
    "Thumb1_R": ("finger_thumb", R), "Middle Distal.R": ("finger_middle", R),
    # Mixamo's words: decided by the armature, flagged here
    "mixamorig:LeftArm": ("_arm", L), "Left_Arm": ("_arm", L),
    "mixamorig:RightLeg": ("_leg", R),
}
REJECT = [
    # physics, cloth and accessory bones whose names contain a body word
    "neckless", "neckless.001", "neckless_2", "Spine.002outer_L", "Waistbelt_Root",
    "Waistbelt1_L", "Necklace1", "Coat_Root", "Hair_Root", "PB_L_HipCloth",
    "Left_Hip", "DEF-pelvis.L", "Z_knees_L",
    # helpers: IK, twist, roll, end bones, cloth-weight bones
    "IK.Foot.L", "IK.Toe.R", "UpperArm_Twist_L", "Z_UpperArm_twist_L",
    "W_Upper Arm.Twist.L", "Left_ForeArm_Twist", "Left_UpperLeg_Twist_00",
    "CC_Base_L_UpperarmTwist01", "CC_Base_NeckTwist01", "Hand_L_end", "MCH-thigh.L",
    "ORG-hand.R", "upper_arm_ik.L",
    # duplicates and ambiguous lone words
    "Right Hand.001", "Toe.L.001", "Hand", "Foot", "Arm",
    # not body parts
    "eye_L", "Eye.L", "Tail1", "Ear1_L", "HairMidA1", "Cube",
]
LABELS = {
    "Upper Arm.L": "upper_arm.l", "UpperArm_L": "upper_arm.l",
    "Lower Arm.R": "forearm.r", "LowerLeg_L": "shin.l", "UpperLeg_R": "thigh.r",
    "Left_Arm": "upper_arm.l", "Left_Arm_Twist_00": "upper_arm.l",
    "Right_Arm_Twist_01": "upper_arm.r", "UpperArm_Twist_L": "upper_arm.l",
    "W_Upper Arm.Twist.L": "upper_arm.l", "Z_LowerArm_twist_L": "forearm.l",
    "Left_UpperLeg_Twist_00": "thigh.l", "Little Proximal_L": "pinky.l",
    "mixamorig:LeftForeArm": "forearm.l",
    # unknown names come back lower-cased and otherwise untouched
    "mixamorig:LeftLeg": "mixamorig:leftleg", "neckless_2": "neckless_2",
    "IK.Foot.L": "ik.foot.l", "Waistbelt1_L": "waistbelt1_l",
}
HEAD_GROUPS = {"Head": True, "Neck": True, "eye_L": True, "SK_L_Eye": True,
               "Eye.weight.L": True, "Jaw": True, "ThoothUpper": True,
               "neckless": False, "neckless_2": False, "Necklace1": False,
               "HairMidA1": False, "Chest": False}

for name, want in PARSE.items():
    got = rig.parse(name)
    check(got == want, "parse(%r) = %r, expected %r" % (name, got, want))
for name in REJECT:
    got = rig.parse(name)
    check(got == (None, None), "parse(%r) = %r, expected no body part" % (name, got))
for name, want in LABELS.items():
    got = rig.group_label(name)
    check(got == want, "group_label(%r) = %r, expected %r" % (name, got, want))
for name, want in HEAD_GROUPS.items():
    check(rig.is_head_group(name) == want, "is_head_group(%r) should be %s" % (name, want))


# ------------------------------------------------ armature lookups on stand-ins
class PB:
    def __init__(self, name, parent=None):
        self.name, self.parent = name, parent

    @property
    def parent_recursive(self):
        out, p = [], self.parent
        while p is not None:
            out.append(p)
            p = p.parent
        return out


class Bones(list):
    def __contains__(self, key):
        if isinstance(key, str):
            return any(b.name == key for b in self)
        return list.__contains__(self, key)


class Arm:
    type = 'ARMATURE'

    def __init__(self, spec):
        """spec: [(name, parent name or None), ...] in parent-first order"""
        made = {}
        for n, p in spec:
            made[n] = PB(n, made.get(p))
        self.pose = type("Pose", (), {})()
        self.pose.bones = Bones(made.values())


def names(arm):
    return {k: v.name for k, v in rig.humanoid_map(arm).items()}


def limbs(side_names):
    """A minimal humanoid with the given limb names (Unity-style trunk)."""
    spec = [("Hips", None), ("Spine", "Hips"), ("Chest", "Spine"), ("Neck", "Chest"),
            ("Head", "Neck")]
    for s, (sh, ua, la, ha, ul, ll, ft) in side_names.items():
        spec += [(sh, "Chest"), (ua, sh), (la, ua), (ha, la),
                 (ul, "Hips"), (ll, ul), (ft, ll)]
    return Arm(spec)


# Mixamo: LeftArm is the upper arm because LeftForeArm hangs from it; LeftLeg
# is the shin because it hangs from LeftUpLeg
mix = Arm([("mixamorig:Hips", None), ("mixamorig:Spine", "mixamorig:Hips"),
           ("mixamorig:Spine1", "mixamorig:Spine"), ("mixamorig:Spine2", "mixamorig:Spine1"),
           ("mixamorig:LeftShoulder", "mixamorig:Spine2"),
           ("mixamorig:LeftArm", "mixamorig:LeftShoulder"),
           ("mixamorig:LeftForeArm", "mixamorig:LeftArm"),
           ("mixamorig:LeftHand", "mixamorig:LeftForeArm"),
           ("mixamorig:LeftUpLeg", "mixamorig:Hips"),
           ("mixamorig:LeftLeg", "mixamorig:LeftUpLeg"),
           ("mixamorig:LeftFoot", "mixamorig:LeftLeg")])
hm = names(mix)
check(hm.get("upper_arm.l") == "mixamorig:LeftArm", "Mixamo upper arm: %s" % hm.get("upper_arm.l"))
check(hm.get("lower_leg.l") == "mixamorig:LeftLeg", "Mixamo shin: %s" % hm.get("lower_leg.l"))
check(hm.get("upper_leg.l") == "mixamorig:LeftUpLeg", "Mixamo thigh: %s" % hm.get("upper_leg.l"))

# a rig whose "Leg_L" is the whole leg, with no UpLeg above it: left alone
whole = Arm([("Hips", None), ("Leg_L", "Hips"), ("Knee_L", "Leg_L")])
check(names(whole).get("lower_leg.l") != "Leg_L", "Leg_L without an UpLeg must not become the shin")

# CATS / MMD English (The Beast by EZAvatars): Left arm > Left elbow > Left
# wrist, Left leg > Left knee > Left ankle, with helper bones beside them
cats = Arm([("Hips", None), ("Spine", "Hips"), ("Chest", "Spine"),
            ("Left shoulder", "Chest"), ("Left arm", "Left shoulder"),
            ("Left elbow", "Left arm"), ("Left elbowHelper", "Left arm"),
            ("Left wrist", "Left elbow"), ("Left Shoulderhelper", "Left shoulder"),
            ("Left leg", "Hips"), ("Left knee", "Left leg"), ("Left KneeHelper", "Left leg"),
            ("Left ankle", "Left knee"), ("Left toe", "Left ankle")])
cm = names(cats)
for k, v in (("shoulder.l", "Left shoulder"), ("upper_arm.l", "Left arm"),
             ("lower_arm.l", "Left elbow"), ("hand.l", "Left wrist"),
             ("upper_leg.l", "Left leg"), ("lower_leg.l", "Left knee"),
             ("foot.l", "Left ankle"), ("toe.l", "Left toe")):
    check(cm.get(k) == v, "CATS %s: %s" % (k, cm.get(k)))

# Mao: "Right Hand.001" is an accessory child of "Right Hand"
mao = limbs({"l": ("Shoulder_L", "Upperarm_L", "Lowerarm_L", "Left Hand",
                   "Upperleg_L", "Lowerleg_L", "Foot_L"),
             "r": ("Shoulder_R", "Upperarm_R", "Lowerarm_R", "Right Hand",
                   "Upperleg_R", "Lowerleg_R", "Foot_R")})
mao.pose.bones.append(PB("Right Hand.001", mao.pose.bones[-5]))
d = rig.describe(mao)
check(d["found"] == d["of"], "Mao-style rig: %d/%d %s" % (d["found"], d["of"], d["missing"]))
check(names(mao)["hand.r"] == "Right Hand", "Mao right hand: %s" % names(mao)["hand.r"])

# Minase: spaces and dots, with cloth bones beside the limbs
mi = limbs({"l": ("Shoulder.L", "Upper Arm.L", "Lower Arm.L", "Hand.L",
                  "Upper Leg.L", "Lower Leg.L", "Foot.L"),
            "r": ("Shoulder.R", "Upper Arm.R", "Lower Arm.R", "Hand.R",
                  "Upper Leg.R", "Lower Leg.R", "Foot.R")})
mi.pose.bones += [PB("W_Upper Arm.Twist.L"), PB("IK.Foot.L"), PB("W_Neckless")]
d = rig.describe(mi)
check(d["found"] == d["of"], "Minase-style rig: %d/%d %s" % (d["found"], d["of"], d["missing"]))

# Vlau: Mixamo words with underscores
vl = limbs({"l": ("Left_Shoulder", "Left_Arm", "Left_ForeArm", "Left_Hand",
                  "Left_UpperLeg", "Left_LowerLeg", "Left_Foot"),
            "r": ("Right_Shoulder", "Right_Arm", "Right_ForeArm", "Right_Hand",
                  "Right_UpperLeg", "Right_LowerLeg", "Right_Foot")})
d = rig.describe(vl)
check(d["found"] == d["of"], "Vlau-style rig: %d/%d %s" % (d["found"], d["of"], d["missing"]))
check(names(vl)["upper_arm.l"] == "Left_Arm", "Vlau upper arm: %s" % names(vl).get("upper_arm.l"))

# Rigify: its "spine" is the pelvis, so the trunk is left to the legacy tables
rg = Arm([("spine", None), ("spine.001", "spine"), ("upper_arm.L", "spine.001")])
check("spine" not in names(rg), "Rigify 'spine' must not be read as the spine")
check(names(rg).get("upper_arm.l") == "upper_arm.L", "Rigify upper arm")

total = len(PARSE) + len(REJECT) + len(LABELS) + len(HEAD_GROUPS) + 22
print("%d checks, %d failure(s)" % (total, len(fails)))
sys.exit(1 if fails else 0)
