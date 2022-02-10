### Copyright 2011, 2012 Magus Freston, Domino Marama, and Gaia Clary
### Modifications 2014-2015 Gaia Clary
### Modification  2015      Matrice Laville
###
### This file is part of Avastar 1.
### 

### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
import bpy, bgl
from bpy.props import *
from struct import pack, unpack, calcsize
from mathutils import Matrix, Vector, Euler, Quaternion

import re, os, logging, gettext
from math import *
from .const import *
from . import create, data, messages, rig, shape, util, context_util
from .context_util import set_context
from .util import mulmat
from bpy_extras.io_utils import ExportHelper
from bpy_extras.io_utils import ImportHelper
from collections import OrderedDict

from bpy.types import Menu, Operator
from bl_operators.presets import AddPresetBase

LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')
translator = gettext.translation('avastar', LOCALE_DIR, fallback=True)

log = logging.getLogger('avastar.animation')
registerlog = logging.getLogger("avastar.register")

ALL_CHANNELS = "CHANNELS 6 Xposition Yposition Zposition Xrotation Yrotation Zrotation"
ROT_CHANNELS = " Xrotation Yrotation Zrotation"
LOC_CHANNELS = " Xposition Yposition Zposition"

BVH_CHANNELS_TEMPLATE = "CHANNELS %d%s%s"  #usage: BVH_CHANNELS_TEMPLATE % (6, LOC_CHANNELS, ROT_CHANNELS)

msg_too_many_bones = 'Max Bonecount(32) exceeded|'\
                +  'DETAIL:\n'\
                +  'This animation uses %d bones, while in SL the maximum number\n'\
                +  'of bones per animation sequence is limitted to 32.\n'\
                +  'You possibly run into this problem when you first \n'\
                +  'select all bones and then add a keyframe.\n\n'\
                +  'YOUR ACTION:\n'\
                +  'Remove unnecessary bones from the animation (use the Dopesheet)\n'\
                +  'or split the animation into 2 or more separate animations\n'\
                +  'and run the animations in parallel in the target system.|'

g_reference_frame = IntProperty(name='Reference Frame', 
                  min=0, 
                  default=0, 
                  description= "In the reference frame the poses of the source and the target match best to each other.\n"
                             + "We need this match pose to find the correct translations\n"
                             + "between the source animation and the target animation"
                  )

g_use_restpose = BoolProperty(name="Use Restpose", 
               default=True, 
               description = "Assume the restpose of the source armature\n"
                           + "matches best to the current pose of the target armature.\n"
                           + "Hint:Enable this option when you import animations\n"
                           + "which have been made for SL"
               )

g_keep_reference_frame = BoolProperty(
                   name="Keep Reference frame",
                   default=False,
                   description="Often the first frame of a BVH Animation is only a control frame.\n"\
                              +"However You may want to keep this frame for debugging purposes"
                   )

def get_target_bone_info(mocap, with_translation=True):
    '''
    Returns the list of targetbones that have animation data in the source rig.
    The returned OrderedDict preserves the bone processing order (from top to bottom)
    Note: we need preserved order because joint locations depend on parent joint matrices
    '''
    target_bone_info = OrderedDict()
    target = bpy.data.objects[mocap.target]
    for targetbone in data.get_mt_bones(target):




        sourcebone = getattr(mocap, targetbone)
        if sourcebone != "":
            if targetbone == "COGloc":
                key = 'COG'
                has_loc = True
            else:
                key = targetbone
                has_loc = with_translation
            bone_target = TargetBoneInfo(source=sourcebone,target=key,loc=has_loc, frames={}, locs=[], rots=[])
            target_bone_info[sourcebone] = bone_target
    return target_bone_info





#


#


def set_best_match(mocap, source, target):
    mocap.flavor, source_bones = find_best_match(source, target)
    log.warning("Retarget rig using flavor [%s] " % mocap.flavor)
    target_bones = data.get_mt_bones(target)
    retarget_rig(source, source_bones, target_bones, mocap)

def retarget_bone(sourcerig, sourcebone, targetbone, mocap):
    if sourcebone in sourcerig.pose.bones:
        setattr(mocap, targetbone, sourcebone)

    else:
        is_mapped=False
        map = RETARGET_MAPPING.get(sourcebone)
        if map:
            for mappedBone in map:
                if mappedBone in sourcerig.pose.bones:
                    log.warning(" sourcebone:%s remapped to %s" % (sourcebone, mappedBone) )
                    setattr(mocap, targetbone, mappedBone)
                    is_mapped=True
                    break
        if not is_mapped:
            if sourcebone == '':
                msg = "  No fcurves will be assigned to targetbone %s (no mapping from source)" % targetbone
            else:
                msg = "  No match found in rig for sourcebone:%s (do not assign %s)" % (sourcebone, targetbone)
            log.warning(msg)
            setattr(mocap, targetbone, "")

def retarget_rig(sourcerig, source_bones, target_bones, mocap):
    for sourcebone, targetbone in zip(source_bones, target_bones):
        retarget_bone(sourcerig, sourcebone, targetbone, mocap)

def find_best_match(source, target):

    SLBONES = data.get_msl_bones(target)
    slcount = len ([bone for bone in SLBONES if bone in source.pose.bones])
    if slcount > 18:
        return "SL/OpenSim, etc.", SLBONES
    
    CMBONES = data.get_mcm_bones(target)
    cmcount = len ([bone for bone in CMBONES if bone in source.pose.bones])
    if cmcount > 18:
        return "Carnegie Mellon", CMBONES
        
    return "", data.get_mt_bones(target)
    
    
    

def clamp(inputval, lower, upper):
    '''
    Limit a value to be between the lower and upper values inclusive
    '''
    return max( min( inputval, upper), lower)



def U16_to_F32(inputU16, lower, upper):
    '''
    The way LL uncompresses floats from a U16. Fudge for 0 included
    In 2 bytes have 256**2 = 65536 values
    '''
    temp = inputU16 / float(65535)
    temp *= (upper - lower)
    temp += lower
    delta = (upper - lower)



    if abs(temp) < delta/float(65535):
        temp = 0

    return temp


def F32_to_U16(inputF, lower, upper):
    '''
    The way LL compresses a float into a U16.
    In 2 bytes have 256**2 = 65536 values
    '''
    inputF = clamp(inputF, lower, upper)
    inputF -= lower
    if upper!=lower:
        inputF /= (upper - lower)
    inputF *= 65535


    return int(floor(inputF))

def get_restpose_mat(pbone, M, MP):
    pparent = pbone.parent
    dbone   = pbone.bone
    dparent = dbone.parent
    PP  = pparent.matrix if pparent else Matrix()#get_restpose_mat(pparent) if pparent else Matrix()#
    PPI = PP.inverted()
    MPI = MP.inverted()
    pmat = mulmat(PP, MPI, M)
    return pmat


def visualmatrix(context, armobj, pbone):
    dbone   = pbone.bone
    '''
        return a local delta transformation matrix that captures the visual
        transformation from the bone's parent to the bone. This includes
        the influence of the IK chain etc relative to parent

        N.B. pose_bone.matrix_basis will not capture rotations due to IK

        Hint: The caller must ensure that dbone is a data.bone and pbone is a pose.bone
              also the bone must have a parent!
    '''

    if util.use_sliders(context) and armobj.RigProp.rig_use_bind_pose:
        M = Matrix(dbone['mat0']).copy() # bone pose matrix in objects frame
        MP = Matrix(dbone.parent['mat0']).copy() if dbone.parent else Matrix()
    else:
        M = dbone.matrix_local.copy() # bone data matrix in objects frame
        MP = dbone.parent.matrix_local.copy() if dbone.parent else Matrix()

    pmat = get_restpose_mat(pbone, M, MP)
    P = pbone.matrix.copy()
    V = mulmat(pmat.inverted(), P)

    C = M.to_3x3().to_4x4()
    CI = C.inverted()

    visual_matrix = mulmat(C, V, CI)

    return visual_matrix


def dot(v1,v2):
    '''
    return the dot product between v1 and v2
    '''
   
    ans=0
    for a in map(lambda x,y:x*y, v1,v2):
        ans+=a
    return ans



def distanceToLine(P,A,B):
    '''
    Calculate Euclidean distance from P to line A-B in any number of dimensions
    '''

    P = tuple(P)
    A = tuple(A)
    B = tuple(B)

    AP = [v for v in map(lambda x,y:x-y, A,P)] 
    AB = [v for v in map(lambda x,y:x-y, A,B)] 

    ABAP = dot(AB,AP)
    ABAB = dot(AB,AB)
    APAP = dot(AP,AP)

    d = sqrt(abs(APAP-ABAP**2/ABAB))

    return d



class ExportActionsPropIndex(bpy.types.PropertyGroup):
    index : IntProperty(name="index")

class ExportActionsProp(bpy.types.PropertyGroup):
    select : BoolProperty(
                name = "has_head",
                description = "has Head",
                default = False,
    )

class AVASTAR_UL_ExportActionsPropVarList(bpy.types.UIList):

    def draw_item(self,
                  context,
                  layout,
                  data,
                  item,
                  icon,
                  active_data,
                  active_propname
                  ):

        layout.prop(item.AnimProp,"select", text=item.name)


class JointOffsetPropIndex(bpy.types.PropertyGroup):
    index : IntProperty(name="index")

class JointOffsetProp(bpy.types.PropertyGroup):
    has_head : BoolProperty(
                name = "has_head",
                description = "has Head",
                default = False,
    )
    has_tail : BoolProperty(
                name = "has_tail",
                description = "has Tail",
                default = False,
    )
    
    head : FloatVectorProperty(
                name = "Head",
                description = "Head",
    )
    
    tail : FloatVectorProperty(
                name = "Tail",
                description = "Tail",
    )

class AVASTAR_UL_JointOffsetPropVarList(bpy.types.UIList):

    def draw_item(self,
                  context,
                  layout,
                  data,
                  item,
                  icon,
                  active_data,
                  active_propname
                  ):

        def get_icon_value(key):
            if key in SLATTACHMENTS:
                ikey = 'aeye'
            elif key in SLVOLBONES:
                ikey = 'veye'
            elif key in SLBONES:
                ikey = 'meye'
            else:
                ikey = 'ceye'
            return get_icon(ikey)

        armobj = util.get_armature(context.object)
        key = item.name
        H = "H" if item.has_head else ""
        T = "T" if item.has_tail else ""
        marker = "%s%s" % (H,T)
        factor = 1
        if armobj.RigProp.display_joint_tails:
            factor *= 0.6
        if armobj.RigProp.display_joint_heads:
            factor *= 0.6

        if factor < 1:

           spl = layout.split(factor=factor)
           row1= spl.row()
           row2= spl.row()
        else:
           row1 = layout.row(align=True)
           row2 = row1

        row1.alignment='LEFT'
        icon_value = get_icon_value(key)
        row1.operator('avastar.focus_on_selected', text="", icon_value=icon_value, emboss=False).bname=key
        row1.operator('avastar.focus_on_selected', emboss=False, text="%s - (%s)" % (key, marker)).bname=key
        if factor <1:

            h = 1000 * Vector(item.head)
            H = ("h:% 04d, % 04d, % 04d" % (h[0], h[1], h[2])) if armobj.RigProp.display_joint_heads else ""
            if len(H) > 0:
                row2.label(text=H)

            t = 1000 * Vector(item.tail)
            T = ("t:% 04d, % 04d, % 04d" % (t[0], t[1], t[2])) if armobj.RigProp.display_joint_tails else ""
            if len(T) > 0:
                row2.label(text=T)


def initialisation():
    bpy.types.Armature.JointOffsetIndex = PointerProperty(type=JointOffsetPropIndex)
    bpy.types.Armature.JointOffsetList = CollectionProperty(type=JointOffsetProp)
    bpy.types.Scene.ExportActionsIndex = PointerProperty(type=ExportActionsPropIndex)
    bpy.types.Scene.ExportActionsList = CollectionProperty(type=ExportActionsProp)

def terminate():

    del bpy.types.Scene.ExportActionsList
    del bpy.types.Scene.ExportActionsIndex
    del bpy.types.Armature.JointOffsetList
    del bpy.types.Armature.JointOffsetIndex


def get_dependecies(master, key):
    dependencies = master.get(key, None)
    if dependencies == None:
        dependencies = {}
        master[key] = dependencies
    return dependencies


def add_dependency(arm, bone, constraint, drivers, drivenby):
 



    try:

        target     = constraint.target
        subtarget  = constraint.subtarget
    except:

        return

    if target == None or subtarget == '' or target != arm:


        return

    if subtarget in drivers and subtarget in drivenby:

        return

    slave  = bone.name
    master = subtarget


    bone_drivers = get_dependecies(drivers, slave)
    
    try:
        tbone = arm.pose.bones[subtarget]
        bone_drivers[slave] = tbone


        for sub_constraint in tbone.constraints:
            add_dependency(arm, tbone, sub_constraint, drivers, drivenby)
    except:
        if subtarget.startswith('ik'):
            log.debug("Found IK bone animation from %s" % subtarget)
        else:
            log.warning("Can not assign subtarget %s" % subtarget)
        

    driven_bones = get_dependecies(drivenby, master)    
    driven_bones[master] = bone
            
def init_dependencies(arm):
    dependencies = {}
    drivers      = {}
    drivenby     = {}

    dependencies['drivers']   = drivers
    dependencies['drivenby']  = drivenby

    for bone in arm.pose.bones:
        for constraint in bone.constraints:
            add_dependency(arm, bone, constraint, drivers, drivenby)
    return dependencies

def get_slaves(dependencies, master):
    drivenby = dependencies['drivenby']
    return drivenby.get(master, None)

def get_masters(dependencies, slave):
    drivers = dependencies['drivers']
    return drivers.get(slave, None)
    
def is_driven_by(dependencies, master, slave):
    drivenby = dependencies['drivenby']
    bone_drivers = drivenby[master.name]
    return slave.name in bone_drivers

def drives_other(dependencies, master, slave):
    drivers = dependencies['drivers']
    driven_bones = drivers[master.name]
    return slave.name in driven_bones

def get_props_from_action(armobj, action):
    props  = action.AnimProp if action else armobj.AnimProp
    return props
    
def get_props_from_arm(armobj):
    action = armobj.animation_data.action
    return get_props_from_action(armobj, action)
    
def get_props_from_obj(obj):
    arm    = util.get_armature(obj)
    return get_props_from_arm(arm)

def get_props_from_context(context):
    obj    = context.active_object
    return get_props_from_obj(obj)

def exportAnimation(context, action, filepath, mode):

    logging.debug("="*50)
    logging.debug("Export for %s animation", mode)
    logging.debug("file: %s", filepath)
    logging.debug("-"*50)

    ANIM = {}

    ANIM["version"]    = 1
    ANIM["subversion"] = 0


    ANIM["emote_name"] = ""

    context = bpy.context
    obj    = context.active_object
    arm    = util.get_armature(obj)
    scn    = context.scene
    props  = get_props_from_arm(arm)


    fps = scn.render.fps
    frame_start = scn.frame_start
    frame_end = scn.frame_end

    log.warning("animation: %4d frame_start" % (frame_start) )
    log.warning("animation: %4d frame_end" % (frame_end) )
    log.warning("animation: %4d fps" % (fps) )

    ANIM["fps"] = fps
    ANIM["frame_start"] = frame_start
    ANIM["frame_end"] = frame_end
    ANIM["duration"] = (frame_end-frame_start)/float(fps)


    meshes = util.findAvastarMeshes(obj)
    for key,name in (
                    ("express_tongue_out_301","express_tongue_out"),
                    ("express_surprise_emote_302","express_surprise_emote"),
                    ("express_wink_emote_303","express_wink_emote"),
                    ("express_embarrassed_emote_304","express_embarrassed_emote"),
                    ("express_shrug_emote_305","express_shrug_emote"),
                    ("express_kiss_306","express_kiss"),
                    ("express_bored_emote_307","express_bored_emote"),
                    ("express_repulsed_emote_308","express_repulsed_emote"),
                    ("express_disdain_309","express_disdain"),
                    ("express_afraid_emote_310","express_afraid_emote"),
                    ("express_worry_emote_311","express_worry_emote"),
                    ("express_cry_emote_312","express_cry_emote"),
                    ("express_sad_emote_313","express_sad_emote"),
                    ("express_anger_emote_314","express_anger_emote"),
                    ("express_frown_315","express_frown"),
                    ("express_laugh_emote_316","express_laugh_emote"),
                    ("express_toothsmile_317","express_toothsmile"),
                    ("express_smile_318","express_smile"),
                    ("express_open_mouth_632","express_open_mouth"),
                    ("express_closed_mouth_300",""),
                    ):

        try:

           if meshes["headMesh"].data.shape_keys.key_blocks[key].value !=0:
               emote = name if name != "" else "closed mouth"
               print("Setting emote to %s" % emote )
               ANIM["emote_name"] = name;
               break;
        except (KeyError, AttributeError): pass    

    ANIM["hand_posture"] = int(arm.RigProp.Hand_Posture)
    ANIM["priority"] = props.Priority

    if props.Loop:
        ANIM["loop"] = 1 
        ANIM["loop_in_frame"] = props.Loop_In
        ANIM["loop_out_frame"] = props.Loop_Out
    else:
        ANIM["loop"] = 0
        ANIM["loop_in_frame"] = 0
        ANIM["loop_out_frame"] = 0


    ANIM["ease_in"] = props.Ease_In
    ANIM["ease_out"] = props.Ease_Out
    ANIM["translations"] = props.Translations


    ANIM["with_reference_frame"] = props.with_reference_frame
    ANIM["with_bone_lock"] = props.with_bone_lock
    ANIM["with_pelvis_offset"] = props.with_pelvis_offset if util.get_ui_level() > 2 else False

    if scn.MeshProp.apply_armature_scale:
        ANIM["apply_scale"] = True
        Marm = obj.matrix_world
        tl,tr,ts = Marm.decompose() 
        ANIM["armature_scale"] = ts
    else:
        ANIM["apply_scale"] = False



    ROTS, LOCS, BONE0 = collectBones(obj, context, with_translation=props.Translations)
    log.info("Found %d ROTS and %d LOCS" % (len(ROTS), len(LOCS)) )

    ANIM['ROTS'] = ROTS
    ANIM['LOCS'] = LOCS
    ANIM['BONE0'] = BONE0


    FRAMED = collectVisualTransforms(obj, context, ROTS, LOCS)

    if mode == 'anim':

        log.info("Simplify animation for armature %s..." % (arm.name))
        FRAMED = simplifyCollectedTransforms(arm, FRAMED, ROTS, LOCS)
        ANIM['FRAMED'] = FRAMED
        ANIM['BONES'], ANIM['CBONES'] = collectBoneInfo(obj, context, ROTS, LOCS) 
        log.info("Export to ANIM")
        exportAnim(arm, filepath, ANIM)

    else:

        ANIM['FRAMED'] = FRAMED
        ANIM['BONES'], ANIM['CBONES'] = collectBoneInfo(obj, context, ROTS, LOCS)         
        log.info("Export to BVH")
        exportBVH(context, arm, filepath, ANIM)


def collectBones(obj, context, with_translation):

    def get_regular_children_of(dbone):
        limbset = []
        while len(dbone.children) > 0:
            childset = [b for b in dbone.children if b.name[0] != 'a' and not b.name.startswith('ik')]
            if len(childset) == 1:
                dbone = childset[0]
                limbset.append(dbone.name)
        return limbset

    def get_bone_names_of_limb(ikbone):
        limbset = get_limb_from_ikbone(ikbone)
        if not limbset:
            return None
        return [key for key in limbset if not key.startswith('ik')]

    def add_bone_data(ROTS, LOCS, BONE0, obj, bonenames, use_bind_pose):
        for bonename in bonenames:
            if BONE0.get(bonename):

                continue

            dbone = obj.data.bones[bonename]
            if use_bind_pose:
                p0=Matrix(dbone['mat0']).to_translation()
                if bonename == "mPelvis":

                    p0p=p0
                else:
                    p0p=Matrix(dbone.parent['mat0']).to_translation()

            else:
                p0=dbone.matrix_local.to_translation()
                if bonename == "mPelvis":

                    p0p=p0
                else:
                    p0p=dbone.parent.matrix_local.to_translation()

            ds, s0 = util.get_bone_scales(dbone.parent)
            r0 = dbone.get('rot0', (0,0,0))
            rot0 = (r0[0], r0[1], r0[2])
            rh = dbone.get(JOINT_BASE_HEAD_ID,(0,0,0))
            relhead = (rh[0], rh[1], rh[2])
            BONE0[bonename] = {'rot0'   : rot0,
                               'pscale0': s0,
                               'pscale' : ds,
                               'offset' : tuple(p0-p0p),
                               JOINT_BASE_HEAD_ID: relhead
                              }

            if bonename in ROTS or bonename in LOCS:

                continue


            ROTS.add(bonename)
            log.debug("1: Add ROT for %s" % bonename)



        return




    use_bind_pose = util.use_sliders(context) and obj.RigProp.rig_use_bind_pose
    action = obj.animation_data.action
    nla_tracks = obj.animation_data.nla_tracks

    ROTS = set()
    LOCS = set()
    BONE0 = {} # this will hold scale0 rot0 etc

    logging.debug("Collecting bones...")

    solo = False
    if obj.animation_data.use_nla and len(nla_tracks)>0:

        tracks = []
        for track in nla_tracks:
            if track.is_solo:
                tracks = [track]
                solo = True
                break
            else:
                tracks.append(track)

        for track in tracks:
            if track.mute:
                logging.debug("    skipping muted track '%s'", track.name)
                continue

            for strip in track.strips:
                if strip.mute:
                    logging.debug("    skipping muted strip '%s'", strip.name)
                    continue

                if strip.action is not None:
                    R, L = collectActionBones(obj, strip.action, with_translation)
                    ROTS = ROTS.union(R)
                    LOCS = LOCS.union(L)

                logging.debug("    grabbing animated bones from NLA track '%s', strip '%s'", track.name, strip.name)

    if action is not None and not solo: 
        logging.debug("    grabbing animated bones from Action '%s'", action.name)
        R, L = collectActionBones(obj, action, with_translation)
        ROTS = ROTS.union(R)
        LOCS = LOCS.union(L)





    if len(ROTS)>0 or len(LOCS)>0:
        for bonename in set().union(ROTS).union(LOCS):
            dbone = obj.data.bones[bonename]

            if dbone.parent is None:

                continue

            add_bone_data(ROTS, LOCS, BONE0, obj, [bonename], use_bind_pose)

            if bonename in ALL_IK_BONES:
                log.debug("Find limb affected by %s" % (bonename) )
                limb_names = get_bone_names_of_limb(bonename)
                if limb_names and len(limb_names) > 0:
                    log.info("Add    Limb: %s (for IK %s)" % (limb_names, bonename))
                    add_bone_data(ROTS, LOCS, BONE0, obj, limb_names, use_bind_pose)

            if bonename[0:5] == "mHand":

                limb_names = get_regular_children_of(dbone)
                if limb_names and len(limb_names) > 0:
                    log.info("Add fingers: %s ( for root: %s)" % (limb_names, bonename))
                    add_bone_data(ROTS, LOCS, BONE0, obj, limb_names, use_bind_pose)

    return ROTS, LOCS, BONE0


def collectActionBones(obj, action, with_translation):

    def add_to_list(list, bonename, msg):
        if not bonename in list:
            list.add(bonename)
            log.warning(msg % bonename)

    def get_parent_bone(arm, bone):
        if bone.name == 'HandThumb1Right':
            return arm.data.bones.get('WristRight')
        elif bone.name == 'HandThumb1Left':
            return arm.data.bones.get('WristLeft')
        else:
            rig.get_parent_bone(bone)
    
    def hierarchy_changed(arm, bonename):





        if not bonename.startswith('m'):
            return False # We only test hierarchy change in mBones


        deform_bone = arm.data.bones.get(bonename)
        if not deform_bone:
            return False # Should never happen

        anim_bone = arm.data.bones.get(bonename[1:])
        if not anim_bone:
            return False # TODO: works only for mBones

        deform_parent = deform_bone.parent
        anim_parent = get_parent_bone(arm, anim_bone)

        has_modified_hierarchy = (deform_parent and anim_parent) and  deform_parent.name != 'm'+anim_parent.name
        if has_modified_hierarchy:
            log.warning("check for bone %s : deform parent: %s anim_parent: %s" % (bonename, deform_parent.name, 'm'+anim_parent.name) )
        return has_modified_hierarchy



    ROTS = set()
    LOCS = set()

    arm = util.get_armature(obj)
    dependencies = init_dependencies(arm)
    ignored_bones = set()

    for fc in action.fcurves:



        if fc.mute:

            logging.debug("    skipping muted channel: %s", fc.data_path)
            continue

        mo = re.search('"([\w\. ]+)".+\.(rotation|location|scale)', fc.data_path)
        if mo is None:


            continue

        bonename = mo.group(1)
        keytype = mo.group(2)
        
        if bonename in ['Origin']:
            continue
        elif bonename in ['COG']:

            bonename = 'Pelvis'
        elif bonename in ['Tinker', 'PelvisInv']:
            add_to_list(ROTS, "mTorso",    "Added Tinker ROTS action curve for bone %s")
            bonename = 'Pelvis'
        elif bonename == 'EyeTarget' and keytype=='location':

            add_to_list(ROTS, "mEyeLeft",  "Added Eyetarget ROTS action curve for bone %s")
            add_to_list(ROTS, "mEyeRight", "Added Eyetarget ROTS action curve for bone %s")
            continue
        elif bonename == 'FaceEyeAltTarget' and keytype=='location':

            add_to_list(ROTS, "mFaceEyeAltLeft", "Added Eyetarget ROTS action curve for bone %s")
            add_to_list(ROTS, "mFaceEyeAltRight", "Added Eyetarget ROTS action curve for bone %s")
            continue

        if "m"+bonename in obj.data.bones:

            bonename = "m"+bonename
        elif not bonename in obj.data.bones:
            ignored_bones.add(bonename)
            continue





        if keytype=='rotation':
            add_to_list(ROTS, bonename, "Added ROT for bone %s")
            if with_translation and hierarchy_changed(arm, bonename):
                add_to_list(LOCS, bonename, "Added dependent LOC for bone %s")
        elif keytype=='location' and ( with_translation or bonename == 'mPelvis'):

            add_to_list(LOCS, bonename, "Added LOC for bone %s")
        else:
            slaves = get_slaves(dependencies, bonename)
            if slaves:
                for slave in slaves.keys():
                    bn = "m" + slave if "m"+slave in obj.data.bones else slave
                    if bn[0] == 'm':
                        add_to_list(ROTS, bn, "Added ROT for slave bone %s")






    if len(ignored_bones) > 0:
        log.warning("%d Bones refered in fcurves but missing in rig:" % (len(ignored_bones)))
        for name in ignored_bones:
            log.warning("- %s" % name)

    log.warning("Collected %d ROTS, %d LOCS" % (len(ROTS), len(LOCS)) )
    return ROTS, LOCS


def collectVisualTransforms(obj, context, ROTS, LOCS):




    FRAMED = {}

    BONES = set().union(ROTS).union(LOCS)
   
    scn   = context.scene
    arm   = util.get_armature(obj)
    props = get_props_from_arm(arm)

    frame_start = scn.frame_start
    frame_end = scn.frame_end
    logging.debug("Collecting visual transformations from frames %d-%d ...", frame_start, frame_end)


    frame_original = scn.frame_current

    for frame in range(frame_start, frame_end+1):

        FRAMED[frame] = {}


        bpy.context.scene.frame_set(frame)

        for bonename in BONES:

            if bonename[0] != 'm' and 'm'+bonename in arm.data.bones:
                bonename = 'm'+bonename

            pbone = arm.pose.bones[bonename]
            dbone = arm.data.bones[bonename]


            try:
                matrix = visualmatrix(context, arm, pbone)
                parent_pose_mat = pbone.parent.matrix if pbone.parent else Matrix()
                pose_mat        = pbone.matrix
                FRAMED[frame][bonename] = {'visual':matrix, 'parent_pose_mat':parent_pose_mat.copy(), 'pose_mat':pose_mat.copy()}
            except:
                log.warning("Collect visual transforms from %s:%s failed (ignore)" % (arm.name, bonename))


    context.scene.frame_set(frame_original)

    return FRAMED


def simplifyCollectedTransforms(arm, FRAMED, ROTS, LOCS, tol=0.02):


    logging.debug("Simplifying bone curves (Lowes global method, tol=%f) ...", tol)

    curve = []

    frames = list(FRAMED.keys())
    frames.sort()

    for frame in frames:
        point = [frame]
        framed = FRAMED[frame]
        for bone in ROTS:
            mats = framed.get(bone)
            if mats:
                matrix = mats.get('visual')
                if matrix:
                    q = matrix.to_quaternion()
                    point.extend(list(q))

        for bone in LOCS:
            mats = framed.get(bone)
            if mats:
                matrix = mats.get('visual')
                if matrix:

                    l = 2*matrix.to_translation()
                    point.extend(list(l))

        curve.append(point)

    sframes = simplifyLowes(curve, 0, len(curve)-1, set(), tol=tol)


    props = get_props_from_arm(arm)
    allframes = FRAMED.keys()

    if props.Loop:
        if props.Loop_In in allframes:
            sframes.add(props.Loop_In)
        if props.Loop_Out in allframes:
            sframes.add(props.Loop_Out)

    for marker in bpy.context.scene.timeline_markers:
        if marker.name == 'fix' and marker.frame in allframes:
            logging.debug("Keeping fixed frame %d", marker.frame)
            sframes.add(marker.frame) 


    Ni=len(curve)
    Nf=len(sframes)

    logging.debug("    keyframe simplification: %d -> %d (%.1f%% reduction)"%(Ni, Nf, round((1-Nf/Ni)*100) ) )

    SIMP = {}

    for frame in sframes:
        SIMP[frame] = FRAMED[frame]

    return SIMP


def collectBoneInfo(armobj, context, ROTS, LOCS):


    scn    = context.scene
    props  = get_props_from_obj(armobj)
    pbones = armobj.pose.bones


    BONES = {}
    CBONES = {}
    
    for bname in set().union(ROTS).union(LOCS):
        if bname.startswith("a") or bname.startswith("m") or 'm'+bname in pbones or bname in SLVOLBONES:
            BONES[bname] = {}
        else:
            CBONES[bname] = {}
            if bname.startswith('ik'):
                log.debug("IK Bone is not directly exported: %s (only its influence on FK Bones)" % (bname) )
            else:
                log.info("FK bone is not directly supported: %s (but can influence supported bones)" % (bname) )

    log.debug("collectBoneInfo: Found %d LOCS, %d ROTS %d BONES" % (len(LOCS), len(ROTS), len(BONES)) )
    for ROT in ROTS:
        log.debug("collectBoneInfo:  ROT %s" % (ROT) )
    for LOC in LOCS:
        log.debug("collectBoneInfo:  LOC %s" % (LOC) )
    for B in BONES:
        log.debug("collectBoneInfo: BONE %s" % (B) )

    for bname in BONES.keys():

        B =  BONES[bname]
        B["name"] = bname


        try:        
            slpriority = clamp(pbones[bname]['priority'], NULL_BONE_PRIORITY, MAX_PRIORITY)
        except KeyError:
            slpriority = NULL_BONE_PRIORITY

        try:        
            if bname == 'mPelvis':
                pelvispriority = clamp(pbones['Pelvis']['priority'], NULL_BONE_PRIORITY, MAX_PRIORITY)
                tinkerpriority = clamp(pbones['Tinker']['priority'], NULL_BONE_PRIORITY, MAX_PRIORITY)
                if pelvispriority > NULL_BONE_PRIORITY:

                    rigpriority = pelvispriority
                else:
                    rigpriority = tinkerpriority

            else:
                rigpriority = clamp(pbones[bname[1:]]['priority'], NULL_BONE_PRIORITY, MAX_PRIORITY) # sans "m"

        except KeyError:
            rigpriority = NULL_BONE_PRIORITY



        if slpriority > NULL_BONE_PRIORITY:

            priority = slpriority 
        elif rigpriority > NULL_BONE_PRIORITY:

            priority = rigpriority
        else:

            priority = props.Priority 

        B["priority"] = priority

    return BONES, CBONES


def exportAnim(armobj, animationfile, ANIM):

    def get_export_bone_set(armobj, ANIM):
        export_bones = {}
        for B in ANIM["BONES"].values():
            bname = B["name"]
            export_name = 'm'+bname if 'm'+bname in armobj.data.bones else bname

            if export_name in export_bones.keys():
                log.warning("%s already exported using data from %s" % (bname, export_name))
                continue


            BDATA = {}
            for f in ANIM["FRAMED"]:
                if bname in ANIM["FRAMED"][f]:
                    BDATA[f] = ANIM["FRAMED"][f][bname]

            if len(BDATA) == 0:
                log.warning("%s has no animation data" % (bname))
                continue



            ename = export_name[1:] if export_name[0]=="a" else export_name
            export_bones[ename]=[B, BDATA]

        return export_bones




    buff = open(animationfile, "wb")



    data = pack("HHif", ANIM["version"] , ANIM["subversion"], ANIM["priority"], ANIM["duration"])
    buff.write(data)



    data = pack("%dsB"%len(ANIM["emote_name"]), bytes(ANIM["emote_name"], 'utf8'), 0)
    buff.write(data)


    loop_in_point = (ANIM["loop_in_frame"]-ANIM["frame_start"])/float(ANIM["fps"])
    loop_out_point = (ANIM["loop_out_frame"]-ANIM["frame_start"])/float(ANIM["fps"])

    export_bones = get_export_bone_set(armobj, ANIM)
    other_bones = ANIM["CBONES"].keys()

    hand_posture = ANIM["hand_posture"]
    if hand_posture < 1:
        hand_posture=0

    data = pack("ffiffii",
                loop_in_point,
                loop_out_point,
                ANIM["loop"],
                ANIM["ease_in"],
                ANIM["ease_out"],
                hand_posture,
                len(export_bones))
    buff.write(data)

    duration = ANIM['duration']
    log.info("+-----------------------------------------------------------------")
    log.info("| Export Summary for %s" % animationfile)
    log.info("+-----------------------------------------------------------------")
    log.info("| Duration: %.2f sec, Priority: %d, Hands: '%s', Emote: '%s'"%(ANIM["duration"], ANIM["priority"], ANIM["hand_posture"], ANIM["emote_name"]))
    log.info("| Loop: %d, In: %.2f sec, Out: %.2f sec"%(ANIM["loop"],loop_in_point, loop_out_point))
    log.info("| Ease In: %.2f sec, Ease Out: %.2f sec"%(ANIM["ease_in"],ANIM["ease_out"]))
    log.info("| Hand pose: %s" % (ANIM["hand_posture"]) )
    log.info("+-----------------------------------------------------------------")
    log.info("| used Bones    %4d" % (len(export_bones)) )
    log.info("| related Bones %4d (indirectly used)" % (len(other_bones))  )
    log.info("| Rotations     %4d (from used and related bones)" % (len(ANIM['ROTS'])) )
    log.info("| Locations     %4d (from used and related bones)" % (len(ANIM['LOCS'])) )
    log.info("|")
    log.info("| Startframe    %4d" % ANIM["frame_start"] )
    log.info("| Endframe      %4d" % ANIM["frame_end"] )
    log.info("| fps           %4d" % ANIM["fps"] )
    log.info("+-----------------------------------------------------------------")

    for ename, bdata in export_bones.items():
        B = bdata[0]
        BDATA = bdata[1]
        bname = B["name"]
        frames = list(BDATA.keys())
        frames.sort()

        data = pack("%dsB"%len(ename), bytes(ename,'utf8') , 0)
        buff.write(data)

        data = pack("i", B["priority"])
        buff.write(data)


        rotloc = "%s%s" % ( 'ROT' if bname in ANIM['ROTS'] else '',
                            'LOC' if bname in ANIM['LOCS'] else '')

        log.debug("Export %d frames for bone %s (%s)" % (len(BDATA), ename, rotloc))

        has_data = False
        if bname in ANIM['ROTS']:
            has_data = True
            log.debug("Export ROT data of Bone %s" % (ename) )

            data = pack("i", len(BDATA))
            buff.write(data)

            for f in frames:






                #
                
                matrix = BDATA[f].get('visual')


                t = (f-ANIM["frame_start"])/float(ANIM["fps"])
                time = F32_to_U16(float(t), 0, duration)
                data = pack("H",time)
                buff.write(data)

                euler = None
                try:
                    r0 = ANIM['BONE0'][bname]['rot0']
                    rot0 = (r0[0], r0[1], r0[2])
                    euler = Euler(rot0,'ZYX')
                except:
                    log.warning("%s.rot0 seems broken. use (0,0,0)" % (bname) )
                    euler = Euler((0,0,0),'ZYX')

                M3    = euler.to_matrix()
                R     = M3.to_4x4() # this is RxRyRz
                q     = mulmat(Rz90I, matrix, R, Rz90).to_quaternion().normalized()



                x = F32_to_U16(q.x, -1, 1)
                y = F32_to_U16(q.y, -1, 1)
                z = F32_to_U16(q.z, -1, 1)
                data = pack("HHH", x, y, z)


                buff.write(data)


        else:

            data = pack("i", 0)
            buff.write(data)


        if bname in ANIM['LOCS']:
            has_data = True
            log.debug("Export LOC data of Bone %s" % (ename) )

            data = pack("i", len(BDATA))
            buff.write(data)

            for f in frames:
                matrix = BDATA[f].get('visual')





                t = (f-ANIM["frame_start"])/float(ANIM["fps"])
                time = F32_to_U16(float(t), 0, duration)
                data = pack("H",time)
                buff.write(data)

                abone  = ANIM['BONE0'][bname]
                b = armobj.data.bones.get(bname)
                L = matrix.to_translation()
                ts = ANIM['armature_scale'] if ANIM.get('apply_scale', False) else (1,1,1)

                try:
                    rot0   = abone['rot0'] if 'rot0' in abone else Vector((0,0,0))
                    psx0, psy0, psz0 = abone['pscale0'] if 'pscale0' in abone else Vector((1,1,1))
                    psx,  psy,  psz  = abone['pscale']  if 'pscale' in abone else Vector((1,1,1))
                    offset = Vector(abone['offset'])  if 'offset' in abone else Vector((0,0,0))

                    L += offset
                except:
                    log.warning("Data corruption in bone %s" % (bname) )
                    raise

                R = Euler(rot0,'ZYX').to_matrix().to_4x4() # this is RxRyRz
                S = Matrix()
                S[0][0] = ts[0]/(psx0+psx)
                S[1][1] = ts[1]/(psy0+psy)
                S[2][2] = ts[2]/(psz0+psz)

                L = mulmat(Rz90.inverted(), S, R, L)
                x = F32_to_U16(L.x/LL_MAX_PELVIS_OFFSET, -1, 1)
                y = F32_to_U16(L.y/LL_MAX_PELVIS_OFFSET, -1, 1)
                z = F32_to_U16(L.z/LL_MAX_PELVIS_OFFSET, -1, 1)

                data = pack("HHH",x, y, z)
                buff.write(data)

        else:

            data = pack("i", 0)
            buff.write(data)


        if not has_data:
            log.warning ("Bone %s ignored (has no animation data)" % (ename) )
    #

    #

    #

    #













    #

    

    data = pack("i",0)
    buff.write(data)

    buff.close()

    logging.debug("-"*50)
    logging.info("Wrote animation to %s"%animationfile)

def get_bvh_name(bone):
    if 'bvhname' in bone:
        return bone['bvhname']
    elif bone.name.startswith("m"):
        return bone.name
    else:
        return None

def get_bvh_offset(armobj):
    dbones = armobj.data.bones
    mPelvis = dbones['mPelvis']
    offset = mPelvis.head_local/INCHES_TO_METERS
    return offset

def get_export_bone_set(arm, animated_bone_names):
    keys = set()
    keys.add("mPelvis")

    for name in animated_bone_names:
        db = arm.data.bones.get(name)
        while db and db.name not in keys:
            keys.add(db.name)
            db = db.parent
    return keys
    
def exportBVH(context, armobj, animationfile, ANIM):
    export_bone_set = get_export_bone_set(armobj, ANIM["BONES"].keys())
    log.warning("+-----------------------------------------------------------------")
    log.warning("| export bone set:\n%s" % (export_bone_set) )
    log.warning("+-----------------------------------------------------------------")

    dbones = armobj.data.bones
    hierarchy = ['mPelvis'] 
    mPelvis = dbones['mPelvis']
    offset = get_bvh_offset(armobj) if ANIM["with_pelvis_offset"] else Vector((0.00, 0.00, 0.00))

    buff = open(animationfile, "w")



    buff.write("HIERARCHY\n")
    buff.write("ROOT hip\n{\n")
    buff.write("\tOFFSET %f %f %f\n" % (offset[0], offset[2], offset[1]))
    buff.write("\t" + ALL_CHANNELS + "\n")
  
    LOCS = ANIM['LOCS']
    for child in mPelvis.children:
        if get_bvh_name(child):
            hierarchy.extend(bvh_hierarchy_recursive(buff, child, export_bone_set, LOCS, 1))

    buff.write("}\n")

    generate_ref = ANIM["with_reference_frame"]
    with_bone_lock = ANIM["with_bone_lock"]


    frame_time = 1/float(ANIM['fps'])
    frame_count = ANIM['frame_end']-ANIM['frame_start']+1
    if generate_ref:
        frame_count += 1

    buff.write("MOTION\nFrames: %d\nFrame Time: %f\n"%(frame_count, frame_time))

    logging.debug("-"*50)
    logging.debug("Summary for %s"%animationfile)
    logging.debug("-"*50)
    logging.debug("Frames: %d at %d fps. Frame time: %.2f"%(frame_count, ANIM["fps"], frame_time))

    FRAMED = ANIM['FRAMED']


    summary = {'mPelvis loc':[]}
    for name in hierarchy:
        summary[name] = []
        summary['%s loc'%name] = []

    frames = list(FRAMED.keys())
    if len(frames) == 0:
        log.warning("No key frames found in animation (abort export)")
        return

    frames.sort()
    frame_original = context.scene.frame_current

    if generate_ref:
        line = bvh_create_reference_frame(armobj, hierarchy, export_bone_set, ANIM, frames[0])
        buff.write("%s\n" % line)
        log.warning("Added the reference frame as first frame.")

    for frame in frames:
        context.scene.frame_set(frame)
        line = bvh_create_frame(armobj, hierarchy, export_bone_set, ANIM, frame)
        buff.write("%s\n" % line)

    context.scene.frame_set(frame_original)
    buff.close()    

    for bname in summary:
        logging.debug(bname)
        for line in summary[bname]:
            logging.debug(line)
    logging.debug("-"*50)
    logging.info("Wrote animation to %s"%animationfile)
    
    export_bones = ANIM["BONES"].keys()
    other_bones = ANIM["CBONES"].keys()
    
    log.info("+-----------------------------------------------------------------")
    log.info("| Export Summary for %s" % animationfile)
    log.info("+-----------------------------------------------------------------")
    log.info("| used Bones    %4d" % (len(export_bones)) )
    log.info("| related Bones %4d (indirectly used)" % (len(other_bones))  )
    log.info("| Rotations     %4d (from used and related bones)" % (len(ANIM['ROTS'])) )
    log.info("| Locations     %4d (from used and related bones)" % (len(ANIM['LOCS'])) )
    log.info("|")
    log.info("| Startframe    %4d" % ANIM["frame_start"] )
    log.info("| Endframe      %4d" % ANIM["frame_end"] )
    log.info("| fps           %4d" % ANIM["fps"] )
    log.info("+-----------------------------------------------------------------")

def get_used_channels(bone, LOCS):

    cc = 3
    loc_channels = ''

    if bone.name in LOCS:
        cc +=3
        loc_channels = LOC_CHANNELS

    used_channels = BVH_CHANNELS_TEMPLATE % (cc, loc_channels, ROT_CHANNELS)
    return used_channels


def bvh_hierarchy_recursive(buff, bone, export_bone_set, LOCS, lvl=0):

    bvhname = get_bvh_name(bone)
    if bvhname == None:
        return []
    hierarchy = []

    if bone.name in export_bone_set:
        channels = get_used_channels(bone, LOCS)

        buff.write("\t"*lvl+"JOINT %s\n"%bvhname)
        buff.write("\t"*lvl+"{\n")

        hl = bone.head_local
        phl = bone.parent.head_local
        offset = mulmat(BLtoBVH, (hl-phl)/INCHES_TO_METERS)
        buff.write("\t"*(lvl+1)+"OFFSET %.4f %.4f %.4f\n"%tuple(offset))
        buff.write("\t"*(lvl+1) + channels + "\n")
        hierarchy = [bone.name]

    children = 0
    for child in bone.children:
        if get_bvh_name(child):
            sub_hierarchy = bvh_hierarchy_recursive(buff, child, export_bone_set, LOCS, lvl+1)
            if sub_hierarchy:
                hierarchy.extend(sub_hierarchy)
                children += len(sub_hierarchy)

    if bone.name in export_bone_set:
        if children == 0:
            buff.write("\t"*(lvl+1)+"End Site\n")
            buff.write("\t"*(lvl+1)+"{\n")
            offset = mulmat(BLtoBVH, Vector(bone[JOINT_BASE_TAIL_ID])/INCHES_TO_METERS)
            buff.write("\t"*(lvl+2)+"OFFSET %.4f %.4f %.4f\n"%tuple(offset))
            buff.write("\t"*(lvl+1)+"}\n")

        buff.write("\t"*lvl+"}\n")

    return hierarchy

def get_bvh_location(armobj, bone_name, ANIM, frame):

    LOCS = ANIM['LOCS']
    FRAMED = ANIM['FRAMED']
    FBONES = FRAMED[frame]

    if bone_name not in FBONES and bone_name != 'mPelvis':
        bone_name = bone_name[1:]

    is_root = bone_name in ['Pelvis', 'mPelvis']
    loc = None
    if is_root or bone_name in FBONES and bone_name in LOCS:
        db=armobj.data.bones[bone_name]
        pb=armobj.pose.bones[bone_name]
        dbp=db.parent
        t=Matrix.Translation(db.head_local)
        it=t.inverted()
        pb_mat = pb.matrix # mats['pose_mat']
        pbp_mat= pb.parent.matrix if pb.parent else Matrix() # mats['parent_pose_mat']
        matf = mulmat(it, dbp.matrix_local, pbp_mat.inverted(), pb_mat, db.matrix_local.inverted(), t)
        off = matf.to_translation()
        bl =  Vector((0,0,0)) if not dbp else (db.head_local - dbp.head_local)
        loc = mulmat(BLtoBVH,(off+bl)/INCHES_TO_METERS)
        loc = util.sanitize_v(loc, precision=4)

    return loc

def get_bvh_rotation(armobj, bone_name, ANIM, frame):

    LOCS = ANIM['LOCS']
    FRAMED = ANIM['FRAMED']
    FBONES = FRAMED[frame]

    if bone_name not in FBONES:
        bone_name = bone_name[1:]

    if bone_name in FBONES:
        mats = FBONES[bone_name]
        matrix = mats['visual']
        matrix = mulmat(BLtoBVH, matrix, BLtoBVH.inverted())




        #


        r = matrix.to_euler('ZYX')



        rx,ry,rz = tuple(Vector(r)/DEGREES_TO_RADIANS)

        rx = round(rx,4)
        ry = round(ry,4)
        rz = round(rz,4)
        rot = Vector((rx, ry, rz))
        rot = util.sanitize_v(rot, precision=4)

    else:
        rot = None

    return rot

'''
    =========================================================
    Important to know about BVH export (PLEASE READ THIS!!!)
    =========================================================

    Remark 1: It looks like the first frame of an animation is not used for animation in SL.
              However the value of the Hip bone location in the first frame seems to be the
              reference location where the animation starts (transition wise)
    Remark 2: It appears as if an animation does not NEED a reference frame. So if only
              one single static pose shall be created, then exporting a single-frame animation
              seems to be accepted by SL. In that case this single frame is used as the
              static pose.
    Remark 3: From Remark 1 it looks like it is sufficient to simply generate the first frame
              twice (once as the reference frame, once as the first frame of the actual animation.
    Remark 4: A bone is considered as not animated when the rot and loc values
              are exactly identical on all exported frames. The decision if a bone is animated
              or not seems to be made by the BVH importer's animation optimizer. The exact values
              for rot and loc seem to be not important as long as they are all the same on all frames.
              It seems fully ok to just set rotation of static (not animated) bones to <0,0,0> on every frame.
              It equally seems ok to set translation of static (not animated) bones to <0,0,0> on every frame.
'''

def get_Hip_reference(armobj):
    b = armobj.data.bones.get('mPelvis')
    if not b:
        b = armobj.data.bones.get('COG')
        if not b:
            return Vector((0,42.1,0))

    ref = b.head_local/INCHES_TO_METERS
    ref.z,ref.y=ref.y,ref.z
    return ref

def bvh_create_reference_frame(armobj, hierarchy, export_bone_set, ANIM, frame):
    log.warning("Create Reference Frame data for frame %d" % frame)

    with_bone_lock = ANIM["with_bone_lock"]
    if with_bone_lock:

        line = bvh_create_frame(armobj, hierarchy, export_bone_set, ANIM, frame, is_reference=True)
        return line

    LOCS = ANIM['LOCS']
    FRAMED = ANIM['FRAMED']
    FBONES = FRAMED[frame]

    line = ""
    log.info("    ==============================================================================")
    for export_name in hierarchy:

        loc = get_bvh_location(armobj, export_name, ANIM, frame)
        if loc:
            if export_name == 'mPelvis':
                loc = get_Hip_reference(armobj)
            else:
                loc = V0.copy()
                loc[2] = 0.00001 # to enforce a small change in the reference frame (ugly!)
            offset = '%.4f %.4f %.4f ' %(loc[0], loc[1], loc[2])
        else:
            offset = ''

        rot = V0.copy()
        rotate = '%.4f %.4f %.4f ' %(rot[0], rot[1], rot[2])

        bd = offset + rotate
        line += bd
        log.info("    [%25s] offset:[%26s] rot:[%26s]" % (export_name, offset, rotate))
    log.info("    ==============================================================================")
    return line

def bvh_create_frame(armobj, hierarchy, export_bone_set, ANIM, frame, is_reference=False):

    def mark_as_reference(vec):
        if any([ abs(vec[i]) > MIN_BONE_LENGTH for i in range(len(vec))]):
            return Vector((0,0,0)), True
        else:
            return Vector((0,0,1)), False

    log.warning("Create Frame data for frame %d" % frame)
    LOCS = ANIM['LOCS']
    FRAMED = ANIM['FRAMED']
    FBONES = FRAMED[frame]

    line = ""
    log.info("    ==============================================================================")
    for index, export_name in enumerate(hierarchy):

        loc = get_bvh_location(armobj, export_name, ANIM, frame)
        if loc:
            if export_name == 'mPelvis':
                ref = get_Hip_reference(armobj)
                loc = ref if is_reference else loc
            offset = '%.4f %.4f %.4f ' %(loc[0], loc[1], loc[2])
            log.info("LOC % 3d: Enabled bone %s" % (index, export_name) )
        else:
            offset = ''

        rot = get_bvh_rotation(armobj, export_name, ANIM, frame)
        if not rot:
            rot = Vector((0,0,0))
        
        if is_reference:
            if export_name in FBONES:
                mrot, is_restpose = mark_as_reference(rot)
                log.info("ROT % 3d: %s bone %s" % (index, "Enabled" if is_restpose else "Locked ", export_name) )
                rot = mrot
            else:
                log.info("ROT % 3d: Ignored bone %s" % (index, export_name) )

        rotate = '%.4f %.4f %.4f ' %(rot[0], rot[1], rot[2])

        bd = offset + rotate
        line += bd
        log.info("    [%25s] offset:[%26s] rot:[%26s]" % (export_name, offset, rotate))
    log.info("    ==============================================================================")
    return line
    

def getCenterBoneDistance(context, source, target, frame=None):
    mocap = context.scene.MocapProp
    
    src_ppos = source.data.pose_position
    tgt_ppos = target.data.pose_position
    
    if frame != None:
        context.scene.frame_set(frame)
    else:
        source.data.pose_position='REST'
        target.data.pose_position='REST'
    
    Goffset = Matrix()
    
    target_bname = 'COG'
    mapped_bname = mocap.get('COG')
    if not mapped_bname:
        return Goffset
    
    spbone = source.pose.bones.get(mapped_bname)
    tpbone = target.pose.bones.get(target_bname)
    
    if not (spbone and tpbone):
        return Goffset
    
    MWS = source.matrix_world
    MWT = target.matrix_world
    spb = spbone.matrix if frame != None else spbone.bone.matrix_local
    tpb = tpbone.matrix if frame != None else tpbone.bone.matrix_local
    l1 = mulmat(MWS, spb).to_translation()
    l2 = mulmat(MWT, tpb).to_translation()
    
    Goffset = MWT.inverted() @ Matrix.Translation(l2-l1)
    
    log.warning("get CenterBone Distance: begin ============")
    log.warning("get CenterBone Distance: source bone: %s" % spbone.name)
    log.warning("get CenterBone Distance: target bone: %s" % tpbone.name)
    log.warning("get CenterBone Distance: source loc : %s" % l1)
    log.warning("get CenterBone Distance: target loc : %s" % l2)
    log.warning("get CenterBone Distance: l2-l1        %s" % (l2-l1) )
    log.warning("get CenterBone Distance: offset: \n%s" % Goffset)
    log.warning("get CenterBone Distance: end ==============")
    
    source.data.pose_position = src_ppos
    target.data.pose_position = tgt_ppos
    
    return Goffset

def setReference(context, src_armobj, tgt_armobj, target_bone_info, frame=None):

    src_ppos = src_armobj.data.pose_position
    tgt_ppos = tgt_armobj.data.pose_position

    if frame != None:
        context.scene.frame_set(frame)
        log.warning("setReferenceFrame to %d" % (frame) )
    else:
        src_armobj.data.pose_position='REST'
        tgt_armobj.data.pose_position='REST'
        log.warning("setReferenceFrame force into restpose: source:%s target:%s" % (src_armobj.name, tgt_armobj.name) )

    sbones = src_armobj.pose.bones
    tbones = tgt_armobj.pose.bones

    MWS = src_armobj.matrix_world
    MWT = tgt_armobj.matrix_world

    Goffset = getCenterBoneDistance(context, src_armobj, tgt_armobj, frame=frame)
    log.warning("setReference(): Goffset: %s " % Goffset)

    for channel in target_bone_info.values():

        channel.Goffset = Goffset
        spb = sbones.get(channel.source, None)
        tpb = tbones.get(channel.target, None)

        if not spb:
            log.warning("Can not set reference pose for missing source bone %s" % (channel.source) )
            continue
        if not tpb:
            log.warning("Can not set reference pose for missing target bone %s" % (channel.target) )
            continue

        spbm = spb.matrix
        tpbm = tpb.matrix




        channel.offset   = mulmat(mulmat(MWT, tpbm).inverted(), mulmat(MWS, spbm))


    src_armobj.data.pose_position = src_ppos
    tgt_armobj.data.pose_position = tgt_ppos


def group_fcurves(source, transforms):
    pbones = source.pose.bones
    for fcurve in source.animation_data.action.fcurves:
        path = fcurve.data_path
        split = path.split('"')

        if len(split) < 2:
            log.warning("Can not process fcurve with name [%s] " % (path) )
            continue

        bname = path.split('"')[1]
        bone = pbones.get(bname)
        if bone:
            transform = transforms.get(bname)
            if not transform:
                log.info("Found bone %s without transform" % bname)
                continue



            if '.rotation' in path:
                transform.rots.append(fcurve)
            elif '.location' in path:
                transform.locs.append(fcurve)



def collectMotionData(context, source, target, target_bone_info, reference_frame, start_frame, end_frame):

    MWS  = source.matrix_world



    log.warning("Collecting motion Data...")
    for frame in range(start_frame, end_frame+1):

        if frame == reference_frame:
            log.warning("Skip reference frame %d from collecting frame data" % frame)
            continue

        context.scene.frame_set(frame)

        for key, channel in target_bone_info.items():

            spb = source.pose.bones.get(channel.source)
            if not spb:
                log.warning("Translation map: bone \"%s\" not in source rig %s" % (channel.source, source.name) )
                continue

            spbm = spb.matrix
            


            m2 = mulmat(MWS, spbm)
            if channel.target=="_COG": # disable COG treatment for debugging
                m = mulmat(channel.Goffset, m2)
                loc, rot0, scl0 = m.decompose()
                M = mulmat(m, channel.offset.inverted())
                loc_unused, quat, scale_unused = m2.decompose()
            else:
                m = m2.normalized()

                loc, quat, scale_unused = m.decompose()

            channel.frames[frame] = [loc, quat]



def simplifyMotionData(translation, reference_frame, start_frame, end_frame, mocap):

    if mocap.simplificationMethod == "loweslocal":
        log.warning("simplify Motion Data: simplifying channel curves (Lowes local method, tol=%f)" % (mocap.lowesLocalTol))
        Ni=Nf=0
        for channel in translation.values():
            curve = []
            



            for frame in channel.frames:
                point = [frame]
                if channel.target=='COG':
                    point.extend(channel.frames[frame][0])
                
                point.extend(channel.frames[frame][1])
                curve.append(point)


            channel.sframes = simplifyLowes(curve, 0, len(curve)-1, set(),tol=mocap.lowesLocalTol)

            Ni+=len(curve)
            Nf+=len(channel.sframes)
        log.warning("simplify Motion Data: total keyframes on all bones: %d -> %d (%.1f%% reduction)" %(Ni, Nf, round((1-Nf/Ni)*100) ) )

    elif mocap.simplificationMethod == "lowesglobal":
        log.warning("simplify Motion Data: simplifying channel curves (Lowes global method, tol=%f)"%(mocap.lowesGlobalTol))

        Ni=Nf=0
        curve = []


        for frame in range(start_frame, end_frame+1):

            if frame == reference_frame:

                continue

            point = [frame]
            for channel in translation.values():
                try:
                    if channel.target=='COG':
                        point.extend(channel.frames[frame][0])
                    point.extend(channel.frames[frame][1])
                except:
                    log.warning("Frame %d has no record for channel %s " % (frame, channel.target))
                    pass
            curve.append(point)

        sframes = simplifyLowes(curve, 0, len(curve)-1, set(),tol=mocap.lowesGlobalTol)
        Ni+=len(curve)
        Nf+=len(sframes)
        for channel in translation.values():
            channel.sframes = sframes

        log.warning("simplify Motion Data: total keyframes on all bones: %d -> %d (%.1f%% reduction)" % (Ni, Nf, round((1-Nf/Ni)*100) ) )
    else:
        log.warning("simplify Motion Data: No channel curves simplifiction specified (keep raw)")
        for channel in translation.values():
            channel.sframes = channel.frames.keys()


def transferActionData(context, source, target, target_bone_info, reference_frame, start_frame, end_frame, keep_reference_frame, progress):

    pbones = target.pose.bones
    mocap = context.scene.MocapProp



    old_settings = rig.set_bone_rotation_limit_state(target, False, all=True)
    if reference_frame == None:
        log.warning("transfer Motion Data: Use Rig Restposes as reference frames")
        source_ref_pose=None 
        target_ref_pose=None
    else:
        log.warning("transfer Motion Data: Use animation frame %d as reference frame (makes sense only for motion transfer between rigs)")
        context.scene.frame_set(reference_frame)
        source_ref_pose = rig.armatureAsDictionary(source)
        target_ref_pose = rig.armatureAsDictionary(target)

    current_frame = start_frame
    if not keep_reference_frame:
        start_frame += 1

    context.scene.frame_set(start_frame)
    refloc = getCenterBoneDistance(context, source, target, frame=reference_frame).translation

    for frame in range(start_frame, end_frame+1):
                
        if frame == reference_frame:
            continue

        progress += 1
        util.progress_update(progress)
        context.scene.frame_set(frame)
        rig.armatureFromMocap(context, target, mocap, False, source_ref_pose, target_ref_pose, refloc)

        for pbone in pbones:

            has_rot, has_loc = has_keyframes(context, frame, pbone, target_bone_info)

            if has_rot:
                if pbone.rotation_mode=='QUATERNION':
                    pbone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=pbone.name)
                else:
                    pbone.keyframe_insert(data_path="rotation_euler", frame=frame, group=pbone.name)
            if has_loc:
                pbone.keyframe_insert(data_path="location", index=-1, frame=frame, group=pbone.name)

    rig.restore_bone_rotation_limit_state(target.pose.bones, old_settings)

def has_keyframes(context, frame, pbone, target_bone_info):
    has_rot = False
    has_loc = False

    mocap = context.scene.MocapProp
    with_translation = mocap.with_translation
    key = mocap.get(pbone.name)
    if key == None:

        return has_rot, has_loc

    channel = target_bone_info.get(key)
    if channel == None:

        return has_rot, has_loc


    if frame not in channel.sframes:

        return has_rot, has_loc

    has_rot = True
    has_loc = (channel.target=='COG' or (with_translation and len(channel.locs) > 0))
    return has_rot, has_loc


def transferAction(context, source, target, target_bone_info, reference_frame, start_frame, end_frame, mocap, with_translation, keep_reference_frame):

    util.progress_begin(0,10000)
    progress = 0
    util.progress_update(progress)

    group_fcurves(source, target_bone_info)

    #

    #

    log.warning("transfer Motion: reading source transformations")
    log.warning("transfer Motion: reference frame: %s" % reference_frame)
    log.warning("transfer Motion: start frame:     %d" % start_frame)
    log.warning("transfer Motion: end frame:       %d" % end_frame)

    collectMotionData(context, source, target, target_bone_info, reference_frame, start_frame, end_frame)

    #

    #


    #

    #
    util.progress_update(progress)
    seamlessRotFrames = int(mocap.seamlessRotFrames) if mocap.seamlessRotFrames else 0
    seamlessLocFrames = int(mocap.seamlessLocFrames) if mocap.seamlessLocFrames else 0
    
    log.warning("transfer Motion:seamlessRotFrames %d" % seamlessRotFrames)
    log.warning("transfer Motion:seamlessLocFrames %d" % seamlessLocFrames)
    
    if seamlessRotFrames>0 or seamlessLocFrames>0:
        log.warning("transfer Motion:: adjusting motion at end to make seamless")
        for channel in target_bone_info.values():
            makeSeamless(channel, seamlessLocFrames, seamlessRotFrames)    

    #

    #
    util.progress_update(progress)
    simplifyMotionData(target_bone_info, reference_frame, start_frame, end_frame, mocap)

    #

    #
    util.progress_update(progress)
    log.warning("transfer Motion:: Transfer Action range [%d - %d]" % (start_frame, end_frame) )

    transferActionData(context, source, target, target_bone_info, reference_frame, start_frame, end_frame, keep_reference_frame, progress)
        
    context.scene.frame_set(start_frame)
    util.progress_end()


class TargetBoneInfo:
    
    def __init__(self, **keys):
        
        for key,value in keys.items():
            setattr(self,key,value) 



def simplifyLowes(curve, i,f, simplified, tol=.1):

    #






 
    pl1 = curve[i]
    pl2 = curve[f]
    

    simplified.add(pl1[0])
    simplified.add(pl2[0])
    
    maxd = 0
    maxi = 0

    for ii in range(i+1,f):
        p = curve[ii]
        d = distanceToLine(p,pl1,pl2)
        if d > maxd:
            maxd = d
            maxi = ii
            
    if maxd > tol:
        
        if maxi==f-1:
            simplified.add(curve[maxi][0])
        else:
            simplified = simplifyLowes(curve, maxi, f, simplified, tol=tol)

        if maxi==i+1:
            simplified.add(curve[maxi][0])
        else:
            simplified = simplifyLowes(curve, i, maxi, simplified, tol=tol)

    return simplified


def makeSeamless(channel, loc_frames, rot_frames):



    F = list(channel.frames.keys())
    F.sort()

    if loc_frames>0:
        for ii in range(len(channel.frames[F[0]][0])):
        
            p0 = channel.frames[F[0]][0][ii]
            p1 = channel.frames[F[-1]][0][ii]
      
            channel.frames[F[-1]][0][ii]=p0
    
            for f in range(loc_frames):
                channel.frames[F[-(f+2)]][0][ii]+=(loc_frames-f)*(p0-p1)/float(loc_frames+1)
                
    if rot_frames>0:
        for ii in range(len(channel.frames[F[0]][1])):
            p0 = channel.frames[F[0]][1][ii]
            p1 = channel.frames[F[-1]][1][ii]
      
            channel.frames[F[-1]][1][ii]=p0
    
            for f in range(rot_frames):
                channel.frames[F[-(f+2)]][1][ii]+=(rot_frames-f)*(p0-p1)/float(rot_frames+1)




def find_animated_bones(arm):
    bones = {}
    try:
        for fcurve in arm.animation_data.action.fcurves:
            bone_name = fcurve.group.name
            if bone_name not in bones and bone_name in arm.data.bones:
                co=None
                for point in fcurve.keyframe_points:
                    if co == None:
                        co = point.co
                    elif co == point.co:
                        continue
                    else:
                        bones[bone_name]=bone_name
                        break
    except:
        pass
        
    return bones

class AvatarAnimationTrimOp(bpy.types.Operator):
    bl_idname = "avastar.action_trim"
    bl_label = "Trim Timeline"
    bl_description ="Adjust start frame, end frame and fps to action"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        active = context.active_object
        if active:
            arm = util.get_armature(active)
            if arm:
                animation_data = arm.animation_data
                if animation_data:
                    action = arm.animation_data.action
                    return action != None

    def execute(self, context):
        arm = util.get_armature(context.active_object)
        action = arm.animation_data.action
        scn=context.scene
        fr = action.frame_range
        scn.frame_start, scn.frame_end = fr[0], fr[1]
        prop = action.AnimProp

        prop.frame_start = fr[0]
        prop.frame_end = fr[1]

        if prop.Loop_In < fr[0]:
            prop.Loop_In = fr[0]
        if fr[0] > prop.Loop_Out:
            prop.Loop_Out = fr[0]
        if fr[1] <= prop.Loop_Out:
            prop.Loop_Out = fr[1]
        prop.Loop = prop.Loop_Out == prop.Loop_In
        return {'FINISHED'}




class ImportAvatarAnimationOp(bpy.types.Operator, ImportHelper):
    bl_idname = "avastar.import_avatar_animation"
    bl_label = "SL Animation (bvh)"
    bl_description ="Create new default Avastar Character and import bvh"
    bl_options = {'REGISTER', 'UNDO'}


    filename_ext = ".bvh"
    files : CollectionProperty(type=bpy.types.PropertyGroup)

    filter_glob : StringProperty(
            default="*.bvh",
            options={'HIDDEN'},
            )

    rigtypes = [
       ('BASIC', "Basic", "This Rig type Defines the Legacy Rig:\nThe basic Avatar with 26 Base bones and 26 Collision Volumes"),
       ('EXTENDED', "Extended", "This Rig type Defines the extended Rig:\nNew bones for Face, Hands, Tail, Wings, ... (the Bento rig)"),
    ]
    rigtype : EnumProperty(
        items       = rigtypes,
        name        = "Rig Type",
        description = "Basic: Old Avatar Skeleton, Extended: Bento Bones",
        default     = 'EXTENDED')

    reference_frame : g_reference_frame
    use_restpose : g_use_restpose

    with_translation : BoolProperty(name="with Translation", default=True, description = "Prepare the Rig to allow translation animation")
    with_sanitize : BoolProperty(
                       name="Cleanup action",
                       default=True,
                       description = "Remove animation curves with less than 2 keyframes"
                       )

    keep_source_rig : BoolProperty(
                       name="Keep Source Rig",
                       default=False,
                       description = "Do not destroy the imported Source Rig (for debugging purposes)"
                       )

    keep_reference_frame : g_keep_reference_frame

    global_scale : FloatProperty(
                       name = "Scale",
                       default = INCHES_TO_METERS,
                       description = "Scale factor for Skeleton size adjustment.\n"\
                                   + "The default factor is to convert Inches to Meters\n"\
                                   + "since SL uses Inches as unit of measurement for BVH animations"
                       )

    def draw(self, context):
        armobj = None
        obj = context.object
        if obj:
            armobj = util.get_armature(obj)

        layout = self.layout
        col = layout.column()
        if armobj:
            col.label(text='Assign to Armature')
        else:
            col.label(text='Import with Rig')
            row=layout.row(align=True)
            row.prop(self,"rigtype",expand=True)

        col = layout.column()

        col.prop(self, 'with_translation')
        col.prop(self, 'global_scale')
        col.prop(self, 'with_sanitize')
        col.prop(self, 'keep_source_rig')
        col.prop(self, 'keep_reference_frame')

        if util.get_ui_level() > UI_ADVANCED:
            col.prop(self,'use_restpose')
            col = layout.column()
            col.prop(self,'reference_frame')
            col.enabled= not self.use_restpose

    @staticmethod
    def exec_imp(
        context,
        target,
        filepath,
        use_restpose,
        reference_frame,
        with_translation=True,
        with_sanitize=True,
        global_scale=1,
        keep_source_rig=False,
        keep_reference_frame=False):

        scn = context.scene
        log.warning("BVH Load from : %s", filepath)

        bpy.ops.import_anim.bvh(filepath=filepath)
        source = context.object

        source.scale *= global_scale

        prop = scn.MocapProp
        prop.source = source.name
        prop.target = target.name
        set_best_match(prop, source, target)
        
        log.warning("BVH Retarget source:%s to target:%s" % (source.name,target.name))
        source_action = ImportAvatarAnimationOp.exec_trans(
            context,
            source,
            target,
            use_restpose,
            reference_frame,
            with_translation,
            keep_source=False,
            with_sanitize=with_sanitize,
            keep_reference_frame=keep_reference_frame)

        if source_action and not keep_source_rig:
            util.remove_object(context, source)
            util.remove_action(source_action, do_unlink=True)

    @staticmethod
    def sanitize_action(action):
        remove_counter = 0
        for fcurve in action.fcurves:
            if len(fcurve.keyframe_points) < 2:
                remove_counter +=1
                action.fcurves.remove(fcurve)
        log.warning("removed %d unneeded fcurves" % remove_counter)
    
        
    @staticmethod
    def exec_trans(
        context,
        source,
        target,
        use_restpose,
        reference_frame,
        with_translation=True,
        keep_source=False,
        with_sanitize=True,
        keep_reference_frame=False):
    
        def set_restpose(target):
            ll = [l for l in target.data.layers]
            target.data.layers=[True]*32
            omode = util.ensure_mode_is('POSE')
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.pose.transforms_clear()
            target.data.layers=ll
            return ll

        log.warning("Source scale is set to: %s" % source.scale)

        oselect_modes = util.set_mesh_select_mode((False,True,False))
        ll = None
        if use_restpose:
            reference_frame = None
            context.scene.frame_set(0)

            util.set_active_object(context, source)
            omode = util.ensure_mode_is('POSE')
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.pose.rot_clear()
            bpy.ops.anim.keyframe_insert_menu(type='Rotation')
            source_action      = source.animation_data.action
            action_name        = source_action.name
            source_action.name = action_name if keep_source else "%s_del" % action_name
            util.ensure_mode_is(omode)

            util.set_active_object(context, target)
            ll = set_restpose(target)

        else:
            util.set_active_object(context, source)
            omode = util.ensure_mode_is('POSE')
            source_action      = source.animation_data.action
            action_name        = source_action.name
            source_action.name = action_name if keep_source else "%s_del" % action_name
            util.ensure_mode_is(omode)

            util.set_active_object(context, target)
            omode = util.ensure_mode_is('POSE')

        log.warning("import_avatar_animation: Create new action with name %s" % (action_name))
        try:
            rig.sync_timeline_enabled = False
            if target.animation_data is None:
                target.animation_data_create()

            action = bpy.data.actions.new(action_name)
            action.use_fake_user=True
            target.animation_data.action = action
            bpy.ops.anim.keyframe_insert_menu(type='Rotation')

            scn = context.scene
            frame_range = source.animation_data.action.frame_range
            scn.frame_start = frame_range[0]
            scn.frame_end   = frame_range[1]

            log.warning("import_avatar_animation: Transfer to action   %s" % (action_name))
            log.warning("import_avatar_animation: reference_frame      %s" % (reference_frame))
            log.warning("import_avatar_animation: with_translation     %s" % (with_translation))
            log.warning("import_avatar_animation: with_sanitize        %s" % (with_sanitize))
            log.warning("import_avatar_animation: keep reference frame %s" % (keep_reference_frame))

            mocap = context.scene.MocapProp
            if use_restpose != None:
                mocap.use_restpose = use_restpose
            if reference_frame != None:
                mocap.referenceFrame = reference_frame

            ButtonTransfereMotion.transferMotion(context, keep_reference_frame)
            if with_translation:
                set_restpose(target)

            if with_sanitize and target.animation_data:
                ImportAvatarAnimationOp.sanitize_action(target.animation_data.action)

            util.set_mesh_select_mode(oselect_modes)
            bpy.ops.avastar.bone_preset_animate()
            util.ensure_mode_is(omode)

        finally:
            rig.sync_timeline_enabled=True
        return source_action
        
    def execute(self, context):

        if util.get_ui_level() > UI_ADVANCED:
            self.use_restpose=True



        armobj = None
        obj = context.object
        if obj:
            omode = obj.mode
            armobj = util.get_armature(obj)
        else:
            omode = None
        
        if not armobj:
            armobj = create.createAvatar(context, rigType=self.rigtype, no_mesh=True)
            util.set_active_object(context, armobj)
            shape.resetToRestpose(armobj, context)
            armobj.RigProp.Hand_Posture = HAND_POSTURE_DEFAULT

        folder = (os.path.dirname(self.filepath))

        util.set_active_object(context, armobj)
        util.set_mode(context, 'POSE')
        ostate = util.set_disable_handlers(context.scene, True)

        try:
            for i in self.files:
                filepath = (os.path.join(folder, i.name))
                log.warning("Importing Animation from %s" % filepath)
                try:
                    log.warning("use Restpose     : %s" % self.use_restpose)
                    log.warning("reference frame  : %d" % self.reference_frame)
                    log.warning("with Translation : %s" % self.with_translation)
                    log.warning("with Sanitize    : %s" % self.with_sanitize)
                    log.warning("seamlessRotFrames: %d" % context.scene.MocapProp.seamlessRotFrames)
                    log.warning("seamlessLocFrames: %d" % context.scene.MocapProp.seamlessRotFrames)
                    ImportAvatarAnimationOp.exec_imp(
                        context,
                        armobj,
                        filepath,
                        self.use_restpose,
                        self.reference_frame,
                        self.with_translation,
                        self.with_sanitize,
                        self.global_scale,
                        self.keep_source_rig,
                        self.keep_reference_frame
                        )

                except Exception as e:
                    log.error("Importing Animation from", filepath)
                    raise e
        finally:
            util.set_disable_handlers(context.scene, ostate)
            if obj:
                util.set_active_object(context, obj)
                if omode:
                    util.set_mode(context, omode)

        return {'FINISHED'}


class ButtonTransfereMotion(bpy.types.Operator):
    bl_idname = "avastar.transfer_motion"
    bl_label = "Transfer Motion"
    bl_description = \
'''Transfer motion between start and end frames using reference frame as guide

This operator is disabled when:

- The COG Bone is not mapped to a bone in the Source Rig'''

    bl_options = {'REGISTER', 'UNDO'}

    keep_reference_frame : g_keep_reference_frame
    
    @classmethod
    def poll(cls, context):
        scn = context.scene
        mocap = scn.MocapProp
        hip_name = mocap.get('COG')
        return hip_name is not None

    @staticmethod
    def transferPoses(context, reference_frame, start_frame, end_frame, keep_reference_frame):
        scn = context.scene
        mocap = scn.MocapProp
        source = bpy.data.objects[mocap.source]
        target = bpy.data.objects[mocap.target]

        target_bone_info = get_target_bone_info(mocap, with_translation=True)
        setReference(context, source, target, target_bone_info, reference_frame)
        transferAction(context, source, target, target_bone_info, reference_frame, start_frame, end_frame, mocap, False, keep_reference_frame)


    def execute(self, context):
        osupp = util.set_disable_handlers(context.scene, True)
        try:
            ButtonTransfereMotion.transferMotion(context, self.keep_reference_frame)
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'CANCELLED'}
        finally:
            util.set_disable_handlers(context.scene, osupp)
        
        return{'FINISHED'}


    @staticmethod
    def transferMotion(context, keep_reference_frame):
        scn = context.scene
        mocap = scn.MocapProp
        reference_frame = None if mocap.use_restpose else mocap.referenceFrame
        source = bpy.data.objects[mocap.source]
        target = bpy.data.objects[mocap.target]
        start_frame, end_frame = [int(f) for f in source.animation_data.action.frame_range]

        ButtonCleanupTarget.delete_action_data(context, target, reference_frame) # to get rid of a previous transfer on the same action
        ButtonTransfereMotion.transferPoses(context, reference_frame, start_frame, end_frame, keep_reference_frame)



class ButtonTransferePose(bpy.types.Operator):
    bl_idname = "avastar.transfer_pose"
    bl_label ="Transfer Pose"
    bl_description ="Transfer pose on current frame for selected bones using reference frame as guide"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            scn = context.scene
            mocap = scn.MocapProp
            reference_frame = None if mocap.use_restpose else mocap.referenceFrame
            current_frame = scn.frame_current

            ButtonTransfereMotion.transferPoses(context, reference_frame, current_frame, current_frame, True)

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonMatchScales(bpy.types.Operator):
    bl_idname = "avastar.match_scales"
    bl_label ="Match scales"
    bl_description ="Match the scale of the imported armature to the Avastar"
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def execute_imp(context):
        try:
            scn  = context.scene
            prop = scn.MocapProp

            source = bpy.data.objects[prop.source]
            target = bpy.data.objects[prop.target]

            if source and target:
                util.match_armature_scales(source, target)
            else:
                print("WARN: Need 2 armatures to call the Armature Scale matcher")

        except Exception as e:
            util.ErrorDialog.exception(e)

    def execute(self, context):
        self.execute_imp(context)
        return{'FINISHED'}


class ButtonCleanupTarget(bpy.types.Operator):
    bl_idname = "avastar.delete_motion"
    bl_label ="Delete Motion"
    bl_description ="Delete motion from Timeline"
    bl_options = {'REGISTER', 'UNDO'}

    def delete_action_data(context, target, referenceFrame):
        scn = context.scene
        active = context.object
        util.set_active_object(context, target)
        original_mode = util.ensure_mode_is('POSE')

        if referenceFrame == None:
            target.animation_data_clear()
        else:
            context.scene.frame_set(referenceFrame)
            bpy.ops.pose.select_all(action='SELECT')
            target.animation_data_clear()
            bpy.ops.anim.keyframe_insert_menu(type='BUILTIN_KSI_LocRot')

        util.ensure_mode_is(original_mode)
        util.set_active_object(context, active)
        tag_redraw(type='TIMELINE')

    def execute(self, context):

        scn = context.scene
        mocap = scn.MocapProp
        target = bpy.data.objects[mocap.target]
        reference_frame = None if mocap.use_restpose else mocap.referenceFrame

        try:
            ButtonCleanupTarget.delete_action_data(context, target, reference_frame)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class KeyPoseChanges(bpy.types.Operator):
    bl_idname = "avastar.key_pose_changes"
    bl_label ="Key Pose changes"
    bl_description ="Enter keyframes for all pose bones\nwhich have been changed since last keyframe"
    bl_options = {'REGISTER', 'UNDO'} 

    selector : EnumProperty(
        items=(
            ('NONE', 'Current Selection', 'Keep Selection as it was before calling the Tool'),
            ('ADDED', 'Newly Keyed bones', 'Select all bones which had\n\n'\
                                           '- either no keys\n'\
                                           '- or different key values\n\n before calling the Tool\n\n'\
                                           'Note: if all bones are already keyed and\n'\
                                           'no key has changed, then no bone will be selected.\n'\
                                           'In that case you may want to  Select all keyed bones,\n'\
                                           'see next select option'),
            ('KEYED', 'All Keyed Bones', 'Select all bones which have keys in this frame')),
            default='NONE'
    )

    keyed_bones_count = 0
    added_bones_count = 0

    @classmethod
    def poll(self, context):
        return context.object and context.object.type=='ARMATURE' and context.object.mode=='POSE'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col=box.column(align=True)

        if self.keyed_bones_count > 0:
            msg = "Found keys for %d bones in this frame" % self.keyed_bones_count
        else:
            msg = "No bone keys found in this frame"
        col.label(text=msg)

        if self.added_bones_count > 0:
            msg = "Added new Bone Keys for %d bones in this frame" % self.added_bones_count      
        else:
            msg = "No new Bone keys to add this time"      
        col.label(text=msg)

        col = layout.column(align=True)
        col.separator()

        col.label(text="Which Set of Bones you want to select:")
        col.prop(self,"selector")

    def execute(self, context):

        Q0 = Quaternion()
        def has_rotation_anim(bone):
            if bone.rotation_mode == 'QUATERNION':
                return bone.rotation_quaternion != Q0
            elif bone.rotation_mode == 'AXIS_ANGLE':
                return bone.rotation_axis_angle[0] != 0
            else:
                return bone.rotation_euler.to_quaternion() != Q0

        def has_location_anim(bone):
            return bone.location.magnitude != 0

        def insert_key_frames(bone_list, ctype):
            for b in bone_list:
                b.select=True
            bpy.ops.anim.keyframe_insert_menu(type=ctype)
            bpy.ops.pose.select_all(action='DESELECT')

        arm = context.object
        frame = bpy.context.scene.frame_current
        bone_repository = {}
        keyed_bones = set()
        added_bones = set()
        if arm.animation_data.action:
            fcurves = arm.animation_data.action.fcurves
            for fcurve in fcurves:
                bone_path, ctype = fcurve.data_path.rsplit('.',1)
                bone = arm.path_resolve(bone_path)
                if not bone:

                    continue

                index = fcurve.array_index      
                data = None
                try:
                    data = arm.path_resolve(fcurve.data_path)[index]
                except:
                    log.warn("unsupported data path [%s]" %  fcurve.data_path)
                    continue

                bone_entry = bone_repository.get(bone.name)
                if bone_entry == None:
                    bone_entry = {}
                    bone_repository[bone.name] = bone_entry
                bone_channels = bone_entry.get(ctype)
                if bone_channels == None:
                    bone_channels = {}
                    bone_entry[ctype] = bone_channels
                channel_value = bone_channels.get(index)
                if channel_value == None:
                    bone_channels[index]=data

                if len(fcurve.keyframe_points) > 0:
                    for point in reversed(fcurve.keyframe_points):
                        if point.co.x <= frame:
                            if data != point.co.y:

                                fcurve.keyframe_points.insert(frame, data)
                                keyed_bones.add(bone.bone)
                                added_bones.add(bone.bone)
                            if point.co.x == frame:
                                keyed_bones.add(bone.bone)
                            break
                else:

                    fcurve.keyframe_points.insert(frame, data)
                    keyed_bones.add(bone.bone)
                    added_bones.add(bone.bone)

        M3 = Matrix().to_3x3()
        selected_bones = util.set_bone_select_mode(arm, False, boneset=None, additive=False)

        to_be_keyed=0
        loc_bones = []
        rot_bones = []
        for bone in arm.pose.bones:
            dbone=bone.bone # assume loc and rot both are keyframed
            if not util.bone_is_visible(arm, dbone):
                continue
            if bone.parent == None:
                continue # Do not touch the skeleton root bone (works for Avastar)

            bone_entry = bone_repository.get(bone.name)
            if bone_entry:

                if has_location_anim(bone) and not bone_entry.get('location'):
                    loc_bones.append(dbone)
                    keyed_bones.add(dbone)
                if has_rotation_anim(bone) and not (bone_entry.get('rotation_quaternion') or bone_entry.get('rotation_euler') or bone_entry.get('rotation_angle')):
                    rot_bones.append(dbone)
                    keyed_bones.add(dbone)
                continue # bone is already processed (see further above)

            if has_rotation_anim(bone):
                rot_bones.append(dbone)
                keyed_bones.add(dbone)
                added_bones.add(dbone)

            if has_location_anim(bone):
                loc_bones.append(dbone)
                keyed_bones.add(dbone)
                added_bones.add(dbone)

        self.keyed_bones_count = len(keyed_bones)
        self.added_bones_count = len(added_bones)

        if loc_bones:
            insert_key_frames(loc_bones, 'Location')

        if rot_bones:
            insert_key_frames(rot_bones, 'Rotation')

        if self.selector=='ADDED':
            for b in added_bones:
                b.select=True
        elif self.selector=='KEYED':
            for b in keyed_bones:
                b.select=True
        else:
            util.set_bone_select_restore(arm, selected_bones)

        return {'FINISHED'}


class ButtonCopyTimelineRange(bpy.types.Operator):
    '''
    Copy Range in Timeline
    '''
    bl_idname = "sparkles.copy_timeline"
    bl_label = "Generate Walkcycle"
    bl_description = "Analyses the first half of the Action\n"\
                   + "and generates a full walk cycle\n\n"\
                   + "Important: All keys in the second half\n"\
                   + "will be replaced by the generated Walk Cycle.\n"\
                   + "There is no need to clean up beforehand\n"
    bl_options = {"UNDO"}

    copy_pose_begin : IntProperty(default=0, min=0, name="Begin",
            description="First source frame for a timeline copy" )
    copy_pose_end : IntProperty(default=0, min=0, name="End",
            description="Last source frame for a timeline copy" )
    copy_pose_to : IntProperty(default=0, min=0, name="To",
            description="First target frame for a timeline copy" )
    copy_pose_loop_at_end : BoolProperty(default=False, name="Create endframe",
            description="Terminate target range with copy of first source frame (only if first source frame has keyframes)")
    copy_pose_loop_at_start : BoolProperty(default=False, name="Create startframe",
            description="Generate keyframes for first source key (if it has no keyframes yet)")
    copy_pose_clean_target_range : BoolProperty(default=False, name="Replace",
            description="Cleanup target range before copy (removes keyframes)")
    copy_pose_x_mirror : BoolProperty(default=False, name="x-mirror",
            description="Does an x-mirror copy (for walk cycles)")
    
    pbones   = []
    armature = None
    
    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'ARMATURE'
        

    def copy_timeframe(self, context, src_frame, bones, tgt_frame, flipped):
        context.scene.frame_set(src_frame)



        bpy.ops.pose.select_all(action='DESELECT')
        for bone in bones:
            self.pbones[bone].bone.select=True

        if flipped:

            bpy.ops.pose.select_mirror(only_active=False, extend=True)


        bpy.ops.pose.copy()
        context.scene.frame_set(tgt_frame)

        bpy.ops.pose.paste(flipped=flipped)

    def cleanup_fcurves(self,context, old_curves):
        fcurves = self.armature.animation_data.action.fcurves
        new_curves = [fcurve for fcurve in fcurves if fcurve.group and fcurve.group.name in self.armature.data.bones]
        for fcurve in new_curves:
            if not fcurve in old_curves:
                fcurves.remove(fcurve)

    def invoke(self, context, event):

        self.copy_pose_begin = int(context.scene.frame_start)
        self.copy_pose_end = int(context.scene.frame_end / 2)
        self.copy_pose_to = self.copy_pose_end+1

        self.copy_pose_loop_at_end = True
        self.copy_pose_loop_at_start = True
        self.copy_pose_clean_target_range = True
        self.copy_pose_x_mirror = True

        return self.execute(context)

    def execute(self, context):

        self.armature  = bpy.context.object
        self.pbones    = self.armature.pose.bones
        fcurves        = self.armature.animation_data.action.fcurves
        bonecurves     = [fcurve for fcurve in fcurves if fcurve.group and fcurve.group.name in self.armature.data.bones]
        timeframes     = {}
        keyed_bones    = []
        fcurves_todel  = []
        
        prop = self


        for fcurve in bonecurves:
            bone_name = fcurve.group.name
            is_in_source_range = False
            is_in_target_range = False
            
            for point in fcurve.keyframe_points:
                timeframe_id = point.co[0]
                
                if prop.copy_pose_to <= timeframe_id <= prop.copy_pose_to + prop.copy_pose_end - prop.copy_pose_begin:
                    is_in_target_range = True
                
                if prop.copy_pose_begin <= timeframe_id <= prop.copy_pose_end:
                    is_in_source_range = True
                    if timeframe_id in timeframes:
                        timeframe = timeframes[timeframe_id]
                    else:
                        timeframe = []
                        timeframes[timeframe_id] = timeframe

                    if not bone_name in timeframe:
                        timeframe.append(bone_name)
  
            if is_in_source_range and not bone_name in keyed_bones:
                keyed_bones.append(bone_name)
                
            if is_in_target_range:
                fcurves_todel.append(fcurve)

        print("Found  %d keyed timeframes in source range:" % len(timeframes) )
        print("remove %d fcurves from target range:"        % len(fcurves_todel) )

        start = prop.copy_pose_to
        end   = prop.copy_pose_to + prop.copy_pose_end - prop.copy_pose_begin
        for fcurve in fcurves_todel:
            todel = [point for point in fcurve.keyframe_points if start <= point.co[0] <= end]
            for point in reversed(todel):
                try:
                    fcurve.keyframe_points.remove(point)
                except:
                    print("failed to remove from timeframe %d of %d: %s" % (point.co[0], len(todel), point) )
                    
        current_timeframe = bpy.context.scene.frame_current
        use_keyframe_insert_auto = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = True
        
        for key, bones in timeframes.items():
            to      = key - prop.copy_pose_begin + prop.copy_pose_to
            self.copy_timeframe(context, key, bones, to, prop.copy_pose_x_mirror)

        if prop.copy_pose_loop_at_start:
            bones=keyed_bones
            to = prop.copy_pose_begin
            print("Open the loop at frame %d" % (to) )
            self.copy_timeframe(context, prop.copy_pose_begin, bones, to, False)
            
        if prop.copy_pose_loop_at_end:
            bones=keyed_bones
            to    = prop.copy_pose_to + prop.copy_pose_end - prop.copy_pose_begin
            print("Close the loop at frame %d" % (to) )
            self.copy_timeframe(context, prop.copy_pose_begin, bones, to, False)

        context.scene.frame_set(current_timeframe)
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = use_keyframe_insert_auto

        self.cleanup_fcurves(context, bonecurves)

        return {"FINISHED"}
        

def tag_redraw(type='ALL'):
    context = bpy.context
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if type == 'ALL' or area.type==type:
                for region in area.regions:
                    region.tag_redraw()

classes = (
    ExportActionsPropIndex,
    ExportActionsProp,
    AVASTAR_UL_ExportActionsPropVarList,
    JointOffsetPropIndex,
    JointOffsetProp,
    AVASTAR_UL_JointOffsetPropVarList,
    AvatarAnimationTrimOp,
    ImportAvatarAnimationOp,
    ButtonTransfereMotion,
    ButtonTransferePose,
    ButtonMatchScales,
    ButtonCleanupTarget,
    KeyPoseChanges,
    ButtonCopyTimelineRange,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered animation:%s" % cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered animation:%s" % cls)

