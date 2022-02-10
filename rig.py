### Copyright 2015 Matrice Laville
###
### This file is part of Avastar
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

import bpy, os, logging, traceback, re
from bpy.props import *
from bpy.app.handlers import persistent

from . import animation, create, data, const, util
from .util import PVector, s2b, mulmat, matrixScale, matrixLocation
from .data import Skeleton
from .context_util import *
from .const import *
from mathutils import Vector, Matrix, Euler, Quaternion
from bpy.types import Menu, Operator
from bl_operators.presets import AddPresetBase

log = logging.getLogger('avastar.rig')
connectlog = logging.getLogger('avastar.rig.connect')
registerlog = logging.getLogger("avastar.register")

log_cache = logging.getLogger('avastar.cache')

def appearance_editable(context):
    armobj = util.get_armature(context.object)
    if armobj:
        editable = armobj.RigProp.rig_appearance_editable
    else:
        editable = context.scene.SceneProp.panel_appearance_editable
    return editable

def set_appearance_editable(context, editable, armobj=None):
    if not armobj:
        armobj = context.object
    if armobj.type == 'ARMATURE':
        armobj.RigProp.rig_appearance_editable = editable
    else:
        context.scene.SceneProp.panel_appearance_editable = editable


def matrixToStringArray(Mat, precision=0):
    if precision:
        M = Mat.copy()
        util.sanitize(M, precision)
    else:
        M = Mat

    mat = ["% g%s" % (M[ii][jj] if abs(M[ii][jj]) > 0.000000001 else 0, "\n" if jj==3 else "") for ii in range(4) for jj in range(4)]
    mat[0] = "\n " + mat[0]
    return mat

def calculate_bind_shape_matrix(arm, mesh):
    Marm = arm.matrix_world
    


    t = mulmat(Rz90I, mesh.matrix_local).to_translation()
    mat = Matrix.Translation(t)
    return mat

#


#
def get_offset_to_parent(bone, get_roll=True):
    
    head = Vector(bone.head)
    tail = Vector(bone.tail)
    roll = bone.roll if get_roll else 0;
    
    parent = bone.parent
    if parent:
        head -= bone.parent.head
        tail -= bone.parent.tail

    return head, tail, roll
#

#
def get_offset_from_sl_bone(bone, corrs=None, get_roll=True):
    head, tail, roll = get_offset_to_parent(bone, get_roll)
    head -= Vector(bone[JOINT_BASE_HEAD_ID])
    tail -= Vector(bone[JOINT_BASE_TAIL_ID])
    
    if corrs:
        corr = corrs.get(bone.name, None)
        if corr:
            head -= Vector(corr['head'])
            tail -= Vector(corr['tail'])    

    return head, tail, roll

def get_bone_names_with_jointpos(arm):

    joints = util.get_joint_cache(arm)
    if joints == None:
        return []

    boneset = joints.keys()
    bones   = util.get_modify_bones(arm)

    resultset = set()
    for name in boneset:
        resultset.add(name)
        if name[0]=='m' and name[1:] in bones:
            resultset.add(name[1:])
        elif 'm' + name in bones:
            resultset.add('m'+name)
    return resultset

def get_first_connected_child(bone):
    for child in bone.children:
        if child.use_connect:
            return child
    return None

def treat_as_linked(bone,ebones):
    connected = is_linked(bone, ebones)
    if not connected and bone.name[0] == 'm':
        dbone = ebones.get(bone.name[1:])
        if dbone:
            connected = dbone.use_connect
    return connected

def is_linked(bone,ebones):
    connected = bone.use_connect
    if not connected and bone.parent:
        head = getattr(bone,        'head_local', getattr(bone,'head'))
        tail = getattr(bone.parent, 'tail_local', getattr(bone.parent,'tail'))
        mag = (head - tail).magnitude
        connected = mag < 0.0001
    return connected

def set_connect(bone, connect, msg=None):
    if bone.parent and bone.use_connect != connect:
        has_changed = True
        bone.use_connect = connect
        if msg:
            connectlog.info("%s bone %s o-- %s %s" % (\
              "Connecting" if connect else "Disconnect",
              bone.parent.name, 
              bone.name, 
              msg
             ))
    else:
        has_changed = False
    return has_changed


def get_joint_offset_count(armobj):
    joints = util.get_joint_cache(armobj)
    joint_count = len(joints) if joints else 0
    return joint_count

def get_joint_bones(arm, all=True, sort=True, order='TOPDOWN'):
    if all:
        return get_all_deform_bones(arm, sort, order)

    ebones = util.get_modify_bones(arm)
    keys = Skeleton.bones_in_hierarchical_order(arm, order=order) if sort else ebones.keys()
    log.warning("get joint bones: got %d initial keys" % len(keys) )

    rbones = [b for b in ebones if b.select or b.select_head or (b.parent and b.parent.select_tail and treat_as_linked(b,ebones))]
    log.warning("get joint bones: got %d selected keys" % len(rbones) )

    bones = []

    for bone in rbones:
        name = bone.name
        if name[0] == 'm':
            bones.append(bone)
            cb = ebones.get(name[1:])
            if cb:
                bones.append(cb)
        elif 'm' + name in ebones:
            bones.append(bone)
            mb = ebones.get('m'+name)
            if mb:
                bones.append(mb)
        elif name[0] == "a" or name in SLVOLBONES or name == 'COG':
            bones.append(bone)

    log.warning("get joint bones: got %d relevant keys" % len(bones) )
    return bones

def get_all_deform_bones(arm, sort=True, order='TOPDOWN'):
    ebones = util.get_modify_bones(arm)
    keys = Skeleton.bones_in_hierarchical_order(arm, order=order) if sort else ebones.keys()

    bones = [ebones[name] for name in keys if name[0] in ["m", "a"] or name in SLVOLBONES or name == 'COG']

    return bones
    
def get_cb_partner(bone, bones):
    pname = bone.name[1:] if bone.name[0] == 'm' else 'm' + bone.name
    return bones.get(pname)

def reset_bone(armobj, bone, boneset):
    h, t = get_sl_restposition(armobj, bone, use_cache=True)
    head  = h     #Skeleton.head(context, bone, ebones)
    tail  = h + t #Skeleton.tail(context, bone, ebones)
    roll  = boneset[bone.name].roll if bone.name in boneset else 0

    if 'fix_head' in bone: del bone['fix_head'] 
    if 'fix_tail' in bone: del bone['fix_tail']
    if 'cache' in bone: del bone['cache']
    
    if armobj.mode == 'EDIT':
        bone.head = head
        bone.tail = tail
        bone.roll = roll

    else:
        bone.head_local = head
        bone.tail_local = tail

def remove_joint_from_armature(bone, joints):

    def remove_joint_data(bone):
        to_remove = [JOINT_O_HEAD_ID, JOINT_OFFSET_HEAD_ID, JOINT_OFFSET_TAIL_ID, JOINT_O_TAIL_ID, 'joint']
        for key in to_remove:
            if key in bone:
                del bone[key]

    if bone.name in joints:
        del joints[bone.name]
        remove_joint_data(bone)
        util.remove_head_offset(bone)
        util.remove_tail_offset(bone)
        return 1
    return 0

def del_offset_from_sl_armature(context, arm, delete_joint_info, all=True):
    log.info("Delete %s Joint Offsets from [%s]" % ("All" if all else "Selected", arm.name))
    ebones = arm.data.edit_bones
    boneset = data.get_reference_boneset(arm)
    bones = get_joint_bones(arm, all=all, order='BOTTOMUP')

    joint_offset_list = arm.data.JointOffsetList
    joint_offset_list.clear()

    oumode = util.set_operate_in_user_mode(False)
    if delete_joint_info:
        log.info("delete_joint_info Found %d relevant edit bones for reverting to SL Restpose in Armature:[%s]" % (len(bones), arm.name) )
        for b in bones:
            mbone, cbone = get_sync_pair(b, ebones)
            if mbone and cbone:

                reset_bone(arm, mbone, boneset)
                reset_bone(arm, cbone, boneset)
            else:

                reset_bone(arm, b, boneset)

    joints  = util.get_joint_cache(arm)
    if joints:
        counter = 0
        for b in bones:
            mbone, cbone = get_sync_pair(b, ebones)
            if mbone and cbone:
                counter += remove_joint_from_armature(mbone, joints)
                counter += remove_joint_from_armature(cbone, joints)
            else:
                counter += remove_joint_from_armature(b, joints)
        if all:
            orphans = 0
            for key in joints.keys():
                if key not in bones:
                    log.debug("Removing orphan Joint [%s]" % (key) )
                    del joints[key]
                    orphans += 1

            del arm['sl_joints']

    reset_cache(arm, full=True)
    util.set_operate_in_user_mode(oumode)
    return

def copy_bone (from_bone, to_bone, mode):
   if mode == 'EDIT':


       to_bone.head = from_bone.head
       to_bone.tail = from_bone.tail
       to_bone.roll = from_bone.roll
   else:


       to_bone.head_local = from_bone.head_local
       to_bone.tail_local = from_bone.tail_local

   
def get_sync_pair(bone, bones):
    name = bone.name
    if name[0] == 'm' and name != 'mPelvis':
        mbone = bone
        cbone = bones.get(name[1:])
    elif name[0] == "a" or name in SLVOLBONES:
        mbone = cbone = None
    else:
        cbone = bone
        mbone = bones.get('m'+name, None)
    return mbone, cbone

def synchronize_bone(bone, bones, mode):
    mbone, cbone = get_sync_pair(bone, bones)
        
    if mbone and cbone:
        if mbone.select_head:
            copy_bone (mbone, cbone, mode)
        else:
            copy_bone (cbone, mbone, mode)

def get_toe_location(armobj):
    bones = util.get_modify_bones(armobj, only='mToeRight')    
    loc = bones[0].head if armobj.mode == 'EDIT' else bones[0].head_local
    return loc

def get_sl_bone(bone, bones):


    return bone if bone.name[0] in ['m','a'] else bones.get('m'+bone.name, bone)


def calculate_joint_offset_from_restpose(context=None, armobj=None, dbone=None, bones=None):

    def safe_add_vec(v1, v2):
        v1 = Vector(v1) if v1 else Vector((0,0,0))
        v2 = Vector(v2) if v2 else Vector((0,0,0))
        vlen = min(len(v1), len(v2))
        vadd = Vector([v1[n]+v2[n] for n in range(vlen)])
        return vadd

    if not context:
        context = bpy.context
    if not armobj:
        armobj = util.get_armature(context.object)
    if not dbone:
        dbone = bpy.context.active_bone
    if not bones:
        bones = util.get_modify_bones(armobj)

    master = get_deform_bone_for(bones, dbone)
    MinJointOffset = util.get_min_joint_offset()

    mparent = get_parent_bone(master)
    MHI  = util.get_bone_scale_matrix(mparent,inverted=True) if mparent else Matrix()
    MTI  = util.get_bone_scale_matrix(master, inverted=True) if mparent else Matrix()


    h0, unused = get_custom_bindposition(armobj, mparent)
    head = master.head
    tail = master.tail
    relhead = Vector(master.get(JOINT_BASE_HEAD_ID, (0,0,0)))
    reltail = Vector(master.get(JOINT_BASE_TAIL_ID, (0,0,0)))

    dhead = MHI*(head -h0) - relhead  # head offset for neutral shape
    dtail = MTI*(tail-head) - reltail # tail offset for neutral shape

    hmag = dhead.magnitude
    tmag = dtail.magnitude
    roll  = master.roll

    enabled = master.name != 'mPelvis' and (hmag > MinJointOffset or tmag > MinJointOffset)
    if hmag > MinJointOffset:
        o = Vector(master.get('offset', (0,0,0) ))
        dhead += o

    h0 = relhead #original distance to parent bone in rest shape




    joint   = {'key':master.name,
               'head':dhead,
               'tail':dtail,
               'roll':roll,
               'enabled':enabled,
               'hmag':hmag,
               'tmag':tmag,
               'h0':h0}

    return master, joint

def prepare_joint_offset_dict(armobj):
    joint_dict = util.get_joint_cache(armobj)
    if joint_dict is None:
        log.info("cofa: Create new joint repository for armature %s" % (armobj.name) )
        joint_dict = {}
    else:
        log.info("cofa: Reset existing joint repository for armature %s" % (armobj.name) )
        joint_dict.clear()
    return joint_dict


def calculate_offset_from_sl_armature(
        context,
        armobj,
        corrs=None,
        with_joint_tails=True):

    JointOffset = util.get_min_joint_offset()

    joint_dict      = prepare_joint_offset_dict(armobj)
    deform_bones    = get_all_deform_bones(armobj)
    edit_bones      = armobj.data.edit_bones

    log.info("cofa: processing %d joint bones for armobj %s" % (len(deform_bones), armobj.name) )

    reset_cache(armobj)
    ignored = 0

    joint_offset_list = armobj.data.JointOffsetList
    joint_offset_list.clear()

    for jointBone in deform_bones:

        bone, joint = calculate_joint_offset_from_restpose(context, armobj, jointBone, edit_bones)
        head = Vector(joint['head'])
        tail = Vector(joint['tail'])

        if joint['enabled'] :
            key, dummy = get_joint_for_bone(joint_dict, bone) # Only want the name here

            prop = None
            if joint['hmag'] > JointOffset:

                prop = joint_offset_list.add()
                prop.has_head = True
                prop.head = head
            if joint['tmag'] > JointOffset and with_joint_tails:

                if not prop:
                    prop = joint_offset_list.add()
                prop.has_tail = True
                prop.tail=tail
            if prop:
                prop.name = key
                try:
                    joint_dict[key] = joint
                except:
                    print("ERROR cofa: key %s: joint %s %d" % (key, joint, len(joint_dict)) )

        elif bone.name in joint_dict:
            log.info("cofa: Offset removed: %s  for %s" % (head, jointBone.name) )
        else:
            ignored += 1

    if ignored > 0:
        log.info("cofa: %d bones located close to their default position (offset < %0.2f mm) (armature:%s)" % (ignored, JointOffset*1000, armobj.name) )

    try:
        armobj['sl_joints'] = joint_dict
    except:
        log.error("ERROR cofa: Can not assign joint offset list to armature:")
        log.error("ERROR cofa: armature type[%s]" % type(armobj))
        log.error("ERROR cofa: armature name[%s]" % armobj.name)
        log.error("ERROR cofa: joints type [%s]" % type(joint_dict))
        log.error("ERROR cofa: joints len [%s]" % len(joint_dict))
        raise
    return joint_dict


def rebuild_joint_position_info(arm_obj, with_joint_tails=True):
    log.debug("| Rebuilding joint position info")
    ebones = arm_obj.data.edit_bones
    MinJointOffset = util.get_min_joint_offset()
    joint_dict = prepare_joint_offset_dict(arm_obj)
    joint_offset_list = arm_obj.data.JointOffsetList
    joint_offset_list.clear()

    deform_bones = get_all_deform_bones(arm_obj)
    reset_cache(arm_obj)
    use_bind_pose = arm_obj.RigProp.rig_use_bind_pose
    
    mPelvis = ebones['mPelvis']
    COG = ebones.get('COG', mPelvis)
    aCenter = ebones.get('aAvatar Center', mPelvis)
    
    log.debug("| Update armature bone location meta...")
    for ebone in [b for b in ebones if not b.get(JOINT_BASE_HEAD_ID)]:
        update_rel_loc(arm_obj, ebone)

    log.debug("| Create the Joint data...")
    for ebone in deform_bones:
        create_joint_info(ebone, arm_obj, joint_offset_list, joint_dict, with_joint_tails)

    adjust_hand_structure(arm_obj, joint_offset_list, joint_dict, with_joint_tails, 1.4)

    return joint_dict


def adjust_hand_structure(arm_obj, joint_offset_list, joint_dict, with_joint_tails,scale):
    handStructureBones = sym(["HandPinky0.", "HandRing0.", "HandMiddle0.", "HandIndex0."])
    util.adjust_hand_structure(arm_obj, scale)
    for name in handStructureBones:
        ebone = arm_obj.data.edit_bones.get(name)
        if ebone:
            create_joint_info(ebone, arm_obj, joint_offset_list, joint_dict, with_joint_tails)


def create_joint_info(ebone, arm_obj, joint_offset_list, joint_dict, with_joint_tails):
    MinJointOffset = util.get_min_joint_offset()
    use_bind_pose = arm_obj.RigProp.rig_use_bind_pose
    ebones = arm_obj.data.edit_bones
    mPelvis = ebones.get('mPelvis')
    COG = ebones.get('COG', mPelvis)
    aCenter = ebones.get('aAvatar Center', mPelvis)
    master = get_deform_bone_for(ebones, ebone)
    head = master.head
    tail = master.tail
    key = master.name
    mparent = get_parent_bone(master)
    MHI = util.get_bone_scale_matrix(mparent,inverted=True) if mparent else Matrix()
    MTI = util.get_bone_scale_matrix(master, inverted=True) if mparent else Matrix()
    R   = bind_rotation_diff(arm_obj, master, use_cache=True, use_bind_pose=use_bind_pose)
    RI  = R.inverted()
    RP  = bind_rotation_diff(arm_obj, mparent, use_cache=True, use_bind_pose=use_bind_pose) if mparent else Matrix()
    RPI = RP.inverted()

    offset =  util.toVector(master.get(JOINT_BASE_OFFSET_ID))
    relhead = get_rel_head(arm_obj, master, update=False)
    bindtail = get_bind_tail(arm_obj, master, use_cache=True)
    if master == mPelvis:
        rh0, rt0 = get_sl_restposition(arm_obj, mPelvis, use_cache=True)
        h0, t0 = get_sl_bindposition(arm_obj, mPelvis, use_cache=True)
        h0, t0, dh, dt = get_floor_compensation(arm_obj, h0, t0, use_cache=True)

        dhead = head - h0
        dtail = mulmat(MTI, (tail - head - rt0))
    elif master == aCenter:
        reltail = aCenter.get('reltail')
        dhead = aCenter.head - mPelvis.head
        dtail = aCenter.tail-aCenter.head - Vector(reltail) if reltail else V0.copy()
    elif master == COG:
        MHI = util.get_bone_scale_matrix(mPelvis,inverted=True) if mparent else Matrix()
        dhead = COG.head - mPelvis.tail
        reltail = COG.get('reltail')
        dtail = COG.tail-COG.head-Vector(reltail) if reltail else V0.copy()
    else:
        h0, unused = get_custom_bindposition(arm_obj, mparent, with_joint_offset=True, use_cache=True, relative=True, joints=joint_dict)
        dhead = mulmat(RP, MHI, RPI, (head - h0)) - (relhead + offset)   # head offset for neutral shape
        dtail = (mulmat(R, MTI, RI, (tail-head)) - mulmat(MTI, bindtail)) if bindtail else V0.copy()

    hmag = dhead.magnitude
    tmag = dtail.magnitude
    enabled = hmag > MinJointOffset or tmag > MinJointOffset
    if enabled :
        joint   = {'key':key,
                    'head':dhead+offset,
                    'tail':dtail,
                    'roll':master.roll,
                    'enabled':True,
                    'hmag':hmag,
                    'tmag':tmag,
                    'h0':relhead + offset}
        prop = None
        if hmag > MinJointOffset:

            prop = joint_offset_list.add()
            prop.has_head = True
            prop.head = dhead
        if tmag > MinJointOffset and with_joint_tails:

            if not prop:
                prop = joint_offset_list.add()
            prop.has_tail = True
            prop.tail=dtail
        if prop:
            prop.name = key
            joint_dict[key] = joint

    arm_obj['sl_joints'] = joint_dict


def reset_scales(arm_obj):
    from . import shape
    bones = util.get_modify_bones(arm_obj)
    for dbone in bones:
        dbone['scale']  = (0.0, 0.0, 0.0)
        dbone['offset'] = (0.0, 0.0, 0.0)
    reset_cache(arm_obj, full=True)

def get_all_slider_targets(arm_obj):
    from . import shape
    targets = []
    for section, pids in SHAPEUI.items():
        targets.extend(pids)
    meshtargets, bonetargets = shape.expandDrivers(arm_obj, targets)
    return meshtargets, bonetargets

def get_joint_for_bone(joint_dict, bone):

    if joint_dict == None:
        return bone.name, None

    jname = bone.name
    joint = joint_dict.get(jname)

    return jname, joint

def get_sl_bone_offset(arm_obj, dbone, parent, Bones):
    p    = 6

    head, unused  = get_sl_restposition(arm_obj, dbone, use_cache=True, Bones=Bones)
    if parent:
        phead, unused = get_sl_restposition(arm_obj, parent, use_cache=True, Bones=Bones)
        bone_offset = head - phead
    else:
        bone_offset = head
    
    return bone_offset, head, p




#





#






def calculate_pivot_matrix(context=None, arm_obj=None, dbone=None, bones=None, with_rot=True, with_joints=True, Bones=None, apply_armature_scale=True, with_structure=False, joints=None):

    def export_sl_definition(dbone, arm_obj, apply_armature_scale, joints):
        if not util.use_sliders(context):

            return False

        if apply_armature_scale:
            s = arm_obj.scale
            if s[0]!=1 or s[1]!=1 or s[2]!=1:
                return False

        if not joints:
            return True

        jh,jt = util.get_joint_position(joints, dbone)
        if not jh:

            return True

        return jh.magnitude < util.get_min_joint_offset()

    if not context:
        context=bpy.context
    if not arm_obj:
        arm_obj=util.get_armature(context.object)
    if not dbone:
        dbone = context.active_bone
    if joints == None:
        joints = util.get_joint_cache(arm_obj)
    if not bones:
        bones = data.get_reference_boneset(arm_obj)

    parent  = get_parent_bone(dbone, with_structure)
    p = 6
    bone_type = "sl_standard"

    if with_structure:
        head = dbone.head.copy() #the bone is moved around if you omitt the copy() here!
        bone_offset = head - parent.head if parent else head
        bone_type = "raw"

    elif with_joints and arm_obj.RigProp.rig_use_bind_pose:
        if 'rest_mat' in dbone:
            array = Vector(dbone['rest_mat'])
            M = util.matrix_from_array(array)

            if arm_obj.RigProp.up_axis == 'Y' and dbone.name=='mPelvis':

                M = mulmat(YUPtoZUP, M)

            return M, p, bone_type
        else:
            bone_offset, hd, p = get_sl_bone_offset(arm_obj, dbone, parent, Bones)
            ui_level = util.get_ui_level()
            if ui_level < UI_EXPERIMENTAL or arm_obj.RigProp.rig_export_visual_matrix:
                bind_mat = animation.visualmatrix(context, arm_obj, arm_obj.pose.bones.get(dbone.name))
                bind_offset = bind_mat.to_translation()
                bone_offset += bind_offset

    elif export_sl_definition(dbone, arm_obj, apply_armature_scale, joints):

        bone_offset, hd, p = get_sl_bone_offset(arm_obj, dbone, parent, Bones)

    else:
        if with_joints:
            h, t = get_custom_restposition(arm_obj, dbone, with_joint_offset=True)
            if dbone.parent:
               p, t = get_custom_restposition(arm_obj, dbone.parent, with_joint_offset=True)
               bone_offset = h - p
        else:
            head = dbone.head.copy() #the bone is moved around if you omitt the copy() here!
            if dbone.parent:
               bone_offset = head - dbone.parent.head
        sl_bone_offset, hd, pr = get_sl_bone_offset(arm_obj, dbone, parent, Bones)
        if sl_bone_offset != bone_offset:
            bone_type = "custom_pos"

    if with_rot:
        bone_offset = Vector((-bone_offset.y, bone_offset.x, bone_offset.z))

    if apply_armature_scale:
        bone_offset = Vector([a*b for a,b in zip(bone_offset, arm_obj.scale)])

    M    = matrixLocation(bone_offset)
    return M, p, bone_type

def set_bone_to_restpose(arm, bone, boneset):
    if bone.name[0] in ["m", "a"] or bone.name in SLVOLBONES:
        restloc, scale, scale0 = calculate_local_matrix(arm, bone, boneset)


        loc     =  bone.head # returns same value as Skeleton.head(context=None, bone, bones)
        disposition = (restloc - loc).magnitude
        if disposition >= 0.001:

            bone.head = restloc
            if bone.name[0]=='m':
                bones = util.get_modify_bones(arm)
                cBone = bones.get(bone.name[1:], None)
                if cBone:
                    cBone.head = restloc


    for child in bone.children:
        set_bone_to_restpose(arm, child, boneset)

def set_to_restpose(context, arm):
    rigType = arm.RigProp.RigType
    jointType = arm.RigProp.JointType
    filepath = util.get_skeleton_file()

    boneset   = get_rigtype_boneset(rigType, jointType, filepath)

    active = context.object
    util.set_active_object(bpy.context, arm)
    omode = util.ensure_mode_is('EDIT')

    roots = roots = [b for b in arm.data.edit_bones if b.parent == None]
    for root in roots:
        set_bone_to_restpose(arm, root, boneset)

    util.ensure_mode_is('OBJECT')
    util.ensure_mode_is(omode)
    util.set_active_object(bpy.context, active)
    return

def calculate_local_matrix(arm, bone, boneset = None, rotate=False, verbose=False):

    if boneset == None:
        rigType = arm.RigProp.RigType
        jointType = arm.RigProp.JointType
        filepath = util.get_skeleton_file()

        boneset   = get_rigtype_boneset(rigType, jointType, filepath)

    Bone    = boneset[bone.name]
    pivot   = Vector(Bone.pivot0)    # pivot comint from avatar_skeleton
    offset  = Vector(bone['offset']) # offset coming from avatar_lad
    loc     = pivot + offset

    if bone.name in ['mPelvis'] or not bone.parent:
        L      = Vector((0,0,0))
        scale  = Vector((0,0,0))
        scale0 = Vector((1,1,1))
    else:
        L, scale, dummy = calculate_local_matrix(arm, bone.parent, boneset, rotate, verbose)
        scale  = Vector(bone.parent['scale'])
        scale0 = Vector(bone.parent['scale0'])

    if rotate:
        L += Vector([ -loc[1], loc[0], loc[2]])
    else:
        L += Vector([ loc[0],  loc[1], loc[2]])
    
    if verbose:
        print("bone %s pivot %s trans %s scale %s" % (bone.name, Vector(pivot), (M*L).translation, scale) )

    return L, scale, scale0

def mpp(M):
    print( "Matrix((({: 6f}, {: 6f}, {: 6f}, {: 6f}),".format  (*M[0]))
    print( "        ({: 6f}, {: 6f}, {: 6f}, {: 6f}),".format  (*M[1]))
    print( "        ({: 6f}, {: 6f}, {: 6f}, {: 6f}),".format  (*M[2]))
    print( "        ({: 6f}, {: 6f}, {: 6f}, {: 6f}))),".format(*M[3]))

def rot0_mat(dbone):

    if 'rot0' in dbone:
        rot0 = util.toVector(dbone['rot0'])
        Rot0 = Euler(rot0,'XYZ').to_matrix().to_4x4()
    else:
        Rot0 = Matrix()
    return Rot0


def pose_mat(armobj, dbone):
    
    if dbone.name in SLVOLBONES:
        return pose_mat(armobj, dbone.parent)

    custom_tail = custom_restpose_tail(armobj, dbone)
    sl_tail = util.toVector(dbone.get(JOINT_BASE_TAIL_ID, custom_tail))
    Q = sl_tail.rotation_difference(custom_tail)
    M = Q.to_matrix().to_4x4()
    return M

def custom_restpose_tail(armobj, dbone):

    b0tail = Vector(dbone.get('b0tail'))
    joint = armobj.data.JointOffsetList.get(dbone.name)

    if joint:
        return b0tail + Vector(joint.tail)
    else:
        return b0tail

def custom_restpose_head(armobj, dbone):

    b0head = Vector(dbone.get('b0head'))
    joint = armobj.data.JointOffsetList.get(dbone.name)

    if joint:
        return b0head + Vector(joint.head)
    else:
        return b0head

def scale_mat(armobj, dbone, apply_armature_scale, with_appearance):

    S, sb = util.getBoneScaleMatrix(armobj, dbone, normalize=False, use_custom=True, with_appearance=with_appearance)





        



    
    if apply_armature_scale:
        Marm = armobj.matrix_world
        tl,tr,ts = Marm.decompose()
        S[0][0] = S[0][0]/ts[0]
        S[1][1] = S[1][1]/ts[1]
        S[2][2] = S[2][2]/ts[2]
    return S

def has_bind_mats(armobj):
    if not armobj:
        return False

    for b in armobj.data.bones:
        if 'bind_mat' in b:
            return True
    return False

def calculate_bind_matrix(armobj, dbone, apply_armature_scale=False, with_sl_rot=True, use_bind_pose=True, with_appearance=True):

    loc = dbone.head_local
    if with_appearance and use_bind_pose and dbone.parent:
        R = pose_mat(armobj, dbone)
    else:
        R = Matrix()

    if apply_armature_scale:
        loc = mulmat(loc, armobj.matrix_local)

    L = matrixLocation(loc)
    R0 = rot0_mat(dbone)
    S = scale_mat(armobj, dbone, apply_armature_scale=False, with_appearance=with_appearance)

    M = mulmat(L, R, R0, S)

    if with_sl_rot:
        M= mulmat(Rz90I, M, Rz90)
  
    return M

def calculate_inverse_bind_matrix(armobj, dbone, apply_armature_scale=False, with_sl_rot=True, use_bind_pose=True, with_appearance=True):
    def get_bind_mat_array(dbone):
        array = dbone.get('bind_mat')
        if array != None:
            array = Vector(array)
        return array

    M = None
    if with_appearance:
        bind_mat = get_bind_mat_array(dbone)
        if bind_mat != None:
            M = util.matrix_from_array(bind_mat)
            if armobj.RigProp.up_axis == 'Y':
                M = mulmat(YUPtoZUP, M)

    if M == None: 
        M = calculate_bind_matrix(armobj, dbone, apply_armature_scale, with_sl_rot, use_bind_pose, with_appearance=with_appearance)
    
    Minv = M.inverted()
    return Minv


def get_bones_from_layers(armobj, layers):
    bones   = util.get_modify_bones(armobj)
    boneset = [b for b in bones if any (b.layers[layer] for layer in layers)]
    return boneset

def get_skeleton_from(armobj):
    objRigType   = armobj.RigProp.RigType
    objJointType = armobj.RigProp.JointType
    S = data.getSkeletonDefinition(objRigType, objJointType)
    return S

def adjustAvatarBonesToRig(armobj, boneset):

    S = get_skeleton_from(armobj)

    for cbone in boneset:
        try:

            Cbone = S[cbone.name] # The original cbone bone descriptor
            Mbone = Cbone.parent  # The original mBone descriptor       
            mbone = cbone.parent  # The mBone partner of the cbone

            DCT   = Vector(Cbone.tail() - Mbone.tail())
            DCH   = Vector(Cbone.head() - Mbone.head())    # The original mBone in <0,0,0>

            M     = Vector(Mbone.tail() - Mbone.head())
            m     = mbone.tail_local - mbone.head_local
            rot   = M.rotation_difference(m) # rotation relative to its default location

            DCH.rotate(rot)
            DCT.rotate(rot)

            cbone.head_local = mbone.head_local + DCH
            cbone.tail_local = mbone.tail_local + DCT

        except:
            print("Could not adjust Bone %s" % (cbone.name) )
            raise

def adjustVolumeBonesToRig(armobj):
    omode=util.ensure_mode_is('EDIT')
    bones = util.get_modify_bones(armobj)
    boneset = [b for b in bones if b.layers[B_LAYER_VOLUME]]
    S = get_skeleton_from(armobj)

    for b in boneset:
        if b.parent == None: continue
        p = b.parent                   # The mBone of the volume
        n = Vector(p.head - p.tail)    # The mBone in <0,0,0>

        B = S[b.name]                  # The original volume bone descriptor
        if B:
            P = B.parent                   # The original mBone descriptor
            N = Vector(P.head() - P.tail())# The original mBone in <0,0,0>

            M = N.rotation_difference(n)

            l = M*Vector(B.head() - P.head())
            t = b.tail - b.head
            bhead  = p.head + l
            btail  = bhead  + t
            b.head = bhead
            b.tail = btail
        else:
            print("Bone %s has no Definition in SKELETON" % (b.name) )

    util.ensure_mode_is(omode)

def adjustAttachmentBonesToRig(armobj):
    bones = util.get_modify_bones(armobj)
    boneset = [b for b in bones if b.layers[B_LAYER_ATTACHMENT]]
    S = get_skeleton_from(armobj)

    for b in boneset:
        if b.parent == None: continue
        p = b.parent                   # The mBone of the volume
        n = Vector(p.head - p.tail)    # The mBone in <0,0,0>

        B = S[b.name]                  # The original volume bone descriptor
        if B:
            P = B.parent                   # The original mBone descriptor
            N = Vector(P.head() - P.tail())# The original mBone in <0,0,0>

            M = N.rotation_difference(n)

            l = M*Vector(B.head() - P.head())
            t = Vector((0,0,0.03))

            bhead  = p.head + Vector(l)
            btail  = bhead  + Vector(t)
            b.head = bhead
            b.tail = btail
        else:
            print("Bone %s has no Definition in SKELETON" % (b.name) )


def adjustAvatarCenter(armobj):

    if armobj.mode != 'EDIT':
         raise Exception("adjustAvatarCenter: object:mode is: %s:%s Expected an edit mode here" % (armobj.name, armobj.mode))

    bones = armobj.data.edit_bones



    mPelvis = bones.get('mPelvis')
    if not mPelvis:
        log.error("adjustSupportRig: mPelvis bone missing in armature %s. Maybe not an Avastar Rig?" % (armobj.name))
        return

    Pelvis = bones.get('Pelvis')
    COG = bones.get('COG')
    Tinker = get_tinker_bone(bones)
    Torso = bones.get("Torso")
    mTorso = bones.get("mTorso")
    
    master = Pelvis if Pelvis else mPelvis
    torso  = Torso if Torso else mTorso


    for bb in [b for b in bones if b.parent and b.parent.name=="Origin" and b.name[0]=="a"]:
        try:
            bb.head = master.head
            bb.tail = master.head + Vector((0,0,0.03))
        except KeyError as e:
            logging.debug("KeyError: %s", e)

    if COG:
        d = torso.head - COG.head
        COG.head = torso.head
        COG.tail += d

    torso = bones.get('Torso')
    if COG and torso:
        d = torso.head - COG.head
        COG.head = torso.head
        COG.tail = COG.tail + d

    if Pelvis:
        set_connect(Pelvis, False)
        Pelvis.head = master.head
        Pelvis.tail = master.tail
        if Tinker:
            set_connect(Tinker, False)
            Tinker.head = torso.head
            Tinker.tail = master.head

def adjustSpineBones(armobj):

    dbones = armobj.data.edit_bones
    joints = util.get_joint_cache(armobj)
    
    def adjust_bone(bname, pname):
        dbone = dbones.get(bname)
        pbone = dbones.get(pname)
        if dbone==None or pbone==None:
            return
        if util.has_joint_position(joints, dbone):
            return
        dbone.head = pbone.tail.copy()
        dbone.tail = pbone.head.copy()

    adjust_bone('Spine1', 'Pelvis')
    adjust_bone('mSpine1', 'mPelvis')
    adjust_bone('Spine2', 'Spine1')
    adjust_bone('mSpine2', 'mSpine1')
    adjust_bone('Spine3', 'Torso')
    adjust_bone('mSpine3', 'mTorso')
    adjust_bone('Spine4', 'Spine3')
    adjust_bone('mSpine4', 'mSpine3')


def adjustCollarLink(armobj, side):
    if armobj.mode != 'EDIT':
         raise "adjustCollarLink: must be called in edit mode"

    bones = armobj.data.edit_bones
    mNeck = bones.get('mNeck', None)
    mCollar = bones.get('mCollar'+side, None)
    CollarLink = bones.get('CollarLink'+side, None)

    if mNeck and mCollar and CollarLink:
        CollarLink.head = mNeck.head
        CollarLink.tail = mCollar.head
    else:
        log.debug("Armature %s has no %s Collar Link" % (armobj.name, side))


def adjustHipLink(armobj, side):
    if armobj.mode != 'EDIT':
         raise "adjustHipLink: must be called in edit mode"

    bones = armobj.data.edit_bones
    mTorso = bones.get('mTorso',None)
    mHip = bones.get('mHip' + side, None)
    HipLink = bones.get('HipLink' + side, None)

    if mTorso and mHip and HipLink:
        set_connect(HipLink, False, msg="Adjust HipLink")
        HipLink.head = mTorso.head
        HipLink.tail = mHip.head

    else:
        log.debug("Armature %s has no %s Hip Link" % (armobj.name, side))

def show_wrist(armobj, side, msg):
    if side == 'Left':
        return

    omode=util.ensure_mode_is('EDIT')
    bones = armobj.data.edit_bones
    Wrist = bones.get('Wrist%s'%side, None)
    if Wrist:
        log.warning("show_bone: Wrist%s head %s - %s (%s)" % (side, Wrist.head, Wrist.tail, msg))
        log.warning(''.join(traceback.format_stack()))
    util.ensure_mode_is(omode)
    

def adjustThumbController(armobj, side):
    if armobj.mode != 'EDIT':
         raise "adjustThumbController: must be called in edit mode"

    bones = armobj.data.edit_bones
    Wrist = bones.get('Wrist%s' % side, None)
    ThumbController = bones.get('ThumbController%s' % side, None)
    if Wrist and ThumbController:
        ThumbController.head = Wrist.head
        ThumbController.tail = Wrist.tail
        Elbow = bones.get('Elbow%s' % side, None)
        Thumb0= bones.get('HandThumb0%s' % side, None)
        if Elbow and Thumb0:
            Thumb0.head = Elbow.tail
    else:
        log.debug("Armature %s has no %s thumb controller" % (armobj.name, side))


def adjustFingerLink(armobj, side):

    if armobj.mode != 'EDIT':
         raise "adjustFingerLink: must be called in edit mode"

    bones = armobj.data.edit_bones
    fingers = [b for b in bones if re.match("Hand.*1%s"%side, b.name) and b.parent and not b.use_connect]
    for finger in fingers:
        finger.parent.tail = finger.head



def getFootPivotRange(bones,side, subtype):

    if subtype =='Hind':
        mFoot  = bones.get('mHindLimb4'+side, None)
        mAnkle = bones.get('mHindLimb3'+side, None)
    else:
        mFoot  = bones.get('mFoot' +side, None)
        mAnkle = bones.get('mAnkle'+side, None)

    if mFoot and mAnkle:
        lb = PVector(mFoot.tail)
        la = mAnkle.head
        lh = PVector((la.x, la.y, lb.z))
        return lb, lh
    return None, None


def adjustFootBall(bones, side, subtype=""):
    lh = lb = None
    bname = 'ik%sFootBall%s' % (subtype, side)
    ikFootBall = bones.get(bname, None)
    if ikFootBall:
        lb, lh = getFootPivotRange(bones, side, subtype)
        if lb:
            ikFootBall.head = lb
            ikFootBall.tail = lb + Vector(s2b((0,0,-0.1)))
        else:
            log.info("Armature has no %s Ankle or Toe" % (side))
    else:
        log.info("Armature has no %s" % (bname))
    return lh, lb


def adjustIKToRig(armobj):
    bones = util.get_modify_bones(armobj)

    adjustIKFootToRig(bones, 'Left')
    adjustIKFootToRig(bones, 'Right')

    adjustIKHandToRig(bones, 'Left')
    adjustIKHandToRig(bones, 'Right')

    if armobj.RigProp.RigType == 'EXTENDED':
        adjustIKHindFootToRig(bones, 'Left')
        adjustIKHindFootToRig(bones, 'Right')




def adjustIKFootToRig(bones, side):

    origin = bones.get('Origin')
    Ankle = bones.get('Ankle' + side)
    Knee = bones.get('Knee' + side)

    ikAnkle = bones.get('ikAnkle' + side)
    ikKneeLine = bones.get('ikKneeLine' + side)
    ikKneeTarget = bones.get('ikKneeTarget' + side)

    ikHeel = bones.get('ikHeel'+side)
    ikFootPivot = bones.get('ikFootPivot'+side)
    if ikHeel and ikFootPivot and Ankle:
        d = ikHeel.tail - ikHeel.head
        z = origin.head[2]
        ikHeel.head      = Ankle.head
        ikHeel.head[2]   = z
        ikHeel.tail      = ikHeel.head + d
        ikFootPivot.head = ikHeel.head
        ikFootPivot.tail = ikHeel.tail

    adjustFootBall(bones, side)

    if ikKneeLine and Knee and ikKneeTarget and ikAnkle and Ankle:

        ikAnkle.head = Ankle.head
        ikAnkle.tail = Ankle.tail
        ikAnkle.roll = Ankle.roll

        td = ikKneeTarget.tail - ikKneeTarget.head
        ikKneeTarget.head.z = Knee.head.z
        ikKneeTarget.tail = ikKneeTarget.head + td

        ikKneeLine.head = Knee.head.copy()
        ikKneeLine.tail = ikKneeTarget.head.copy()


def adjustIKHindFootToRig(bones, side):

    origin = bones.get('Origin')
    Ankle = bones.get('HindLimb3' + side)
    Knee = bones.get('HindLimb2' + side)

    ikAnkle = bones.get('ikHindLimb3' + side)
    ikKneeLine = bones.get('ikHindLimb2Line' + side)
    ikKneeTarget = bones.get('ikHindLimb2Target' + side)

    ikHeel = bones.get('ikHindHeel'+side)
    ikFootPivot = bones.get('ikHindFootPivot'+side)
    if ikHeel and ikFootPivot and Ankle:
        d = ikHeel.tail - ikHeel.head
        z = origin.head[2]
        ikHeel.head      = Ankle.head
        ikHeel.head[2]   = z
        ikHeel.tail      = ikHeel.head + d
        ikFootPivot.head = ikHeel.head
        ikFootPivot.tail = ikHeel.tail

    adjustFootBall(bones, side, "Hind")

    if ikKneeLine and Knee and ikKneeTarget and ikAnkle and Ankle:

        ikAnkle.head = Ankle.head
        ikAnkle.tail = Ankle.tail
        ikAnkle.roll = Ankle.roll

        td = ikKneeTarget.tail - ikKneeTarget.head
        ikKneeTarget.head.z = Knee.head.z
        ikKneeTarget.tail = ikKneeTarget.head + td

        ikKneeLine.head = Knee.head.copy()
        ikKneeLine.tail = ikKneeTarget.head.copy()


def adjustIKHandToRig(bones, side):

    Wrist = bones.get('Wrist' + side)
    Elbow = bones.get('Elbow' + side)

    ikWrist = bones.get('ikWrist' + side)
    ikElbowLine = bones.get('ikElbowLine' + side)
    ikElbowTarget = bones.get('ikElbowTarget' + side)

    if ikElbowLine and Elbow and ikElbowTarget and ikWrist and Wrist:

        ikWrist.head = Wrist.head
        ikWrist.tail = Wrist.tail
        ikWrist.roll = Wrist.roll

        td = ikElbowTarget.tail - ikElbowTarget.head
        ikElbowTarget.head.z = Elbow.head.z
        ikElbowTarget.tail  = ikElbowTarget.head + td
        
        ikElbowLine.head = Elbow.head.copy()
        ikElbowLine.tail = ikElbowTarget.head.copy()


def adjustHandStructure(armobj):
    bones  = get_structure_bones(armobj)
    for finger0 in bones:
       name = finger0.name
       if name.startswith("Hand") and (name.endswith("0Left") or name.endswith("0Right")):
           name = name.replace("0", "1")
           finger1 = armobj.data.edit_bones.get(name)
           if finger1:
               finger0.tail=finger1.head
               finger1.use_connect=True
               finger1.parent=finger0

def SLBoneStructureRestrictStates(armobj):
    bones  = get_structure_bones(armobj)
    mute_count = len([b for b in bones if b.hide_select])
    all_count = len(bones)
    if mute_count==all_count:
        return 'Disabled', 'Enable'
    if mute_count == 0:
        return 'Enabled', 'Disable'
    return 'Mixed', ''
    
        
def setSLBoneStructureRestrictSelect(armobj, restrict):
    bones  = get_structure_bones(armobj, include_all=True)
    for bone in bones:
        bone.hide_select     = restrict
        if restrict:
            bone.select      = False
            bone.select_tail = False
            bone.select_head = False
        elif bone.select_tail == True and bone.select_head == True:
            bone.select      = True
    
def getControlledBonePairs(armobj):
    bones  = util.get_modify_bones(armobj)
    bone_pairs = [[bones[b.name[1:]],b] for b in bones if b.name[0]=='m' and b.name[1:] in bones]
    return bone_pairs

def get_structure_bones(armobj, include_all=False):
    def append(bones, bone):
        if bone:
            bones.append(bone)

    bones  = util.get_modify_bones(armobj)
    structure_bones = [b for b in bones if b.layers[B_LAYER_STRUCTURE] and b.name[0:2]!="ik"]
    if include_all:
        append(structure_bones, bones.get('Pelvis'))
    return structure_bones

def needRigFix(armobj):
    bones = util.get_modify_bones(armobj)
    for b in bones:
        if b.name[0] != 'm':
            continue
        cname = b.name[1:]
        c = bones.get(cname)
        if not c:
            log.info("Bone %s missing (unexpected)" % (cname))
            continue
        chead = Vector(c.head) if armobj.mode == 'EDIT' else Vector(c.head_local) 
        bhead = Vector(b.head) if armobj.mode == 'EDIT' else Vector(b.head_local) 
        diff = (chead - bhead).magnitude
        if diff > MIN_JOINT_OFFSET:

            return True
    return False

def needTinkerFix(armobj, msg="ops"):
    bones = armobj.data.edit_bones if armobj.mode=='EDIT' else armobj.pose.bones
    needFix = False

    try:

        mpelvis = bones.get('mPelvis')
        if not mpelvis:
            return False

        pelvis = bones.get('Pelvis')
        if not pelvis:
            return False

        pelvisi = get_tinker_bone(bones) # old rig

        if not pelvisi:
            return False

        cog = bones.get('COG')
        if not cog:
            return False

        f1 = MIN_JOINT_OFFSET < (Vector(pelvisi.tail) - Vector(pelvis.head)).magnitude
        f2 = MIN_JOINT_OFFSET < (Vector(pelvisi.head) - Vector(pelvis.tail)).magnitude
        f3 = MIN_JOINT_OFFSET < (Vector(cog.head) - Vector(pelvis.tail)).magnitude
        f4 = MIN_JOINT_OFFSET < (Vector(mpelvis.head) - Vector(pelvis.head)).magnitude
        f5 = MIN_JOINT_OFFSET < (Vector(mpelvis.tail) - Vector(pelvis.tail)).magnitude

        needFix = f1 or f2 or f3 or f4 or f5



    except Exception as e:
        log.warning("Serious issue with Rig, missing Bone Pelvis,Tinker or COG")
        needFix = False # Can't fix actually
        raise e

    return needFix

def get_tinker_bone(bones):
    tinker = bones.get('Tinker')
    if not tinker:
        tinker = bones.get('PelvisInv') # old name
    return tinker

def matchTinkerToPelvis(context, armobj, alignToDeform=False):
    with set_context(context, armobj, 'EDIT'):
        bones = armobj.data.edit_bones
        
        mpelvis = bones.get('mPelvis')
        pelvis = bones.get('Pelvis')
        master = mpelvis if alignToDeform == 'ANIMATION_TO_DEFORM' else pelvis
        
        pelvisi = get_tinker_bone(bones)
        cog = bones.get('COG')
        
        pelvis.head = master.head.copy()
        pelvis.tail = master.tail.copy()
        mpelvis.head = master.head.copy()
        mpelvis.tail = master.tail.copy()
        
        pelvisi.tail = master.head.copy()
        pelvisi.head = master.tail.copy()
        
        cogdiff = cog.tail - cog.head
        cog.head = pelvis.tail.copy()
        cog.tail = cog.head + cogdiff

        log.warning("Adjusted root bone group using [%s] as master" % master.name)
        log.warning("Pelvis   : t:%s h:%s" % (PVector(pelvis.tail), PVector(pelvis.head) ))
        log.warning("Tinker: h:%s t:%s" % (PVector(pelvisi.head), PVector(pelvisi.tail)))
        log.warning("COG      : h:%s t:%s" % (PVector(cog.head), PVector(cog.tail)))

        reset_cache(armobj)

def adjustRigToSL(armobj):
    pairs = getControlledBonePairs(armobj)
    log.debug("adjustRigToSL for %d pairs of armature %s in mode %s" % (len(pairs), armobj.name, armobj.mode))
    for bone, slBone in pairs:
        log.debug("Adjust control Bone [%s] to sl bone [%s]" % (bone.name, slBone.name) )
        bone.head = slBone.head.copy()
        bone.tail = slBone.tail.copy()
        bone.roll = slBone.roll

def adjustSLToRig(armobj):
    pairs = getControlledBonePairs(armobj)
    log.debug("adjustSLToRig for %d pairs of armature %s in mode %s" % (len(pairs), armobj.name, armobj.mode))
    for bone, slBone in pairs:
        log.debug("Adjust slBone [%s] to control bone [%s]" % (slBone.name, bone.name) )
        slBone.head = bone.head.copy()
        slBone.tail = bone.tail.copy()
        slBone.roll = bone.roll

def mesh_uses_collision_volumes(obj):
    volbones = data.get_volume_bones()
    for vg in obj.vertex_groups:
        if vg.name in volbones:
            return True
    return False
    
def armature_uses_collision_volumes(arm):
    volbones = data.get_volume_bones()
    bones = util.get_modify_bones(arm)
    for bone in bones:
        if bone.use_deform and not bone.name.startswith("m") and bone.name in volbones:
            return True
    return False

def is_collision_rig(obj):
    if obj.type == 'MESH':
        return mesh_uses_collision_volumes(obj)
    else:
        return armature_uses_collision_volumes(obj)




def adjustBoneRoll(arm):

    def matrix_from_axis_pair(y_axis, other_axis, axis_name):

        assert axis_name in 'xz'

        y_axis = Vector(y_axis).normalized()

        if axis_name == 'x':
            z_axis = Vector(other_axis).cross(y_axis).normalized()
            x_axis = y_axis.cross(z_axis)
        else:
            x_axis = y_axis.cross(other_axis).normalized()
            z_axis = x_axis.cross(y_axis)

        return Matrix((x_axis, y_axis, z_axis)).transposed()

    def deselect_all_bones(arm):
        for b in arm.data.edit_bones:
            b.select=False

    def select_bone_set(roll_change_bones):
        for bone in roll_change_bones:
            bone.select = True

    omode = util.set_object_mode('EDIT')
    roll_change_bones = get_bones_from_layers(arm, [B_LAYER_WING, B_LAYER_HAND, B_LAYER_FACE, B_LAYER_TAIL])
    deselect_all_bones(arm)
    select_bone_set(roll_change_bones)
    arm.update_from_editmode()

    bpy.ops.armature.roll_clear()
    deselect_all_bones(arm)
    for bone in roll_change_bones:
        if bone.name.startswith("HandThumb"):
            if bone.name.startswith("HandThumb0"):
                deg       = -20 if bone.name.endswith("Left") else 20
            else:
                deg       = 45 if bone.name.endswith("Left") else -45
            bone.roll += deg * DEGREES_TO_RADIANS
        elif bone.name.startswith("FaceLipLower") or bone.name.startswith("FaceForehead"):

            matrix = matrix_from_axis_pair(bone.y_axis, (0,0,1), 'z').to_4x4()
            matrix.translation = bone.head
            bone.matrix = matrix


    util.set_object_mode(omode)

def get_ik_constraint(pose_bones, bone_name, ik_bone_name):
    iks = [con for con in pose_bones[bone_name].constraints if con.type=="IK" and con.subtarget==ik_bone_name]
    if len(iks) == 0:
        log.info("get_ik_constraint: No IK constraint found for bone %s and subtarget %s" % (bone_name, ik_bone_name) )
    return iks[0] if len(iks) > 0 else None

def get_IK_constraint(bone):
    con = bone.constraints.get("AVA_IK")
    if con:
        return con

    con = bone.constraints.get("IK")
    if con:
        return con        

    constraints = [con for con in bone.constraints if con.type=='IK']
    con = constraints[0] if constraints else None
    return con    

def get_ik_influence(pose_bones, bone_name, ik_bone_name):
    try:
        ik = get_ik_constraint(pose_bones, bone_name, ik_bone_name)
        influence = ik.influence if ik else 0
    except:

        influence = 0
    return influence
    
def create_ik_button(row, active, layer):
    if active == None or active.pose == None: return

    pose_bones = active.pose.bones
    text="???"
    try:
        prop = None

        if layer == B_LAYER_IK_LEGS:
            ik = get_ik_influence(pose_bones, "KneeRight", "ikAnkleRight") + get_ik_influence(pose_bones, "KneeLeft", "ikAnkleLeft")
            icon = ICON_RADIOBUT_ON if ik > 1.9 else ICON_RADIOBUT_OFF
            text = "IK Legs"
            prop = 'legs_ik_enabled'
        elif layer == B_LAYER_IK_LIMBS:
            ik = get_ik_influence(pose_bones, "HindLimb2Right", "ikHindLimb3Right") + get_ik_influence(pose_bones, "HindLimb2Left", "ikHindLimb3Left")
            icon = ICON_RADIOBUT_ON if ik > 1.9 else ICON_RADIOBUT_OFF
            text = "IK Limbs"
            prop = 'hinds_ik_enabled'
        elif layer == B_LAYER_IK_ARMS:
            ik = get_ik_influence(pose_bones, "ElbowRight", "ikWristRight") + get_ik_influence(pose_bones, "ElbowLeft", "ikWristLeft")
            icon  = ICON_RADIOBUT_ON if ik  > 1.9 else ICON_RADIOBUT_OFF
            text = "IK Arms"
            prop = 'arms_ik_enabled'

        elif layer == B_LAYER_IK_FACE:
            ik = active.IKSwitchesProp.face_ik_enabled
            icon = ICON_RADIOBUT_ON if ik else ICON_RADIOBUT_OFF
            text = "IK Face"
            prop = 'face_ik_enabled'
        elif layer == B_LAYER_IK_HAND:
            row.prop(active.IKSwitchesProp,"Enable_Hands", text="", icon=ICON_CONSTRAINT_BONE)
            if active.IKSwitchesProp.Enable_Hands in ['FK', 'GRAB']:
                props = row.operator("avastar.ik_apply", text="", icon=ICON_POSE_DATA)
                props.limb='HAND'
                props.symmetry='BOTH'
            return
        else:
            icon = ICON_BLANK1
    except:
        raise


    icon_value = visIcon(active, layer, type='ik')
    row.prop(active.data, "layers", index=layer, toggle=True, text=text, icon_value=icon_value)
    if prop:
        row.prop(active.IKSwitchesProp,prop, text='', icon=icon)
    else:
        row.operator(op, text="",icon=icon)

def get_bone_constraint(bone, type, namehint=None):
    if not bone: return None

    candidates = [c for c in bone.constraints if c.type==type]
    if len(candidates) == 0:
        return None

    if len(candidates) == 1:
       return candidates[0]

    if namehint:
        for c in candidates:
            if namehint in c:
                return c

    return candidates[0]

def setEyeTargetInfluence(arm, prep):
    left  = "%sLeft" % prep
    right = "%sRight" % prep

    EyeLeft      = arm.pose.bones.get(left,None)
    EyeRight     = arm.pose.bones.get(right,None)
    EyeLeftCons  = get_bone_constraint(EyeLeft, 'DAMPED_TRACK', namehint='DAMPED_TRACK')
    EyeRightCons = get_bone_constraint(EyeRight, 'DAMPED_TRACK', namehint='DAMPED_TRACK')

    state = arm.IKSwitchesProp.Enable_Eyes if prep == 'Eye' else arm.IKSwitchesProp.Enable_AltEyes
    if state:
        if EyeLeftCons: EyeLeftCons.influence=1
        if EyeRightCons: EyeRightCons.influence=1
    else:
        if EyeLeftCons: EyeLeftCons.influence=0
        if EyeRightCons: EyeRightCons.influence=0

def get_posed_bones(armobj):
    posed_bones = []
    Q0 = Quaternion((1,0,0,0))
    for b in armobj.pose.bones:
        if b.matrix_basis.decompose()[1].angle > 0.001:
            log.warning("Found posed bone %s" % b.name)
            posed_bones.append(b)
    return posed_bones

def set_rotation_limit(bones, state):
    backup = {}
    for b in bones:
        store = {}
        backup[b.name] = [store, b.use_ik_limit_x, b.use_ik_limit_y, b.use_ik_limit_z, b.bone.select]
        b.use_ik_limit_x = state
        b.use_ik_limit_y = state
        b.use_ik_limit_z = state
        
        for c in b.constraints:
            if c.type =='LIMIT_ROTATION':
                store[c.name] = [c.influence, c.use_limit_x, c.use_limit_y, c.use_limit_z]
                c.influence = 1 if state else 0
                c.use_limit_x = state
                c.use_limit_y = state
                c.use_limit_z = state

    return backup
    
def restore_bone_rotation_limit_state(bones, backup):
    for b in bones:
        store, b.use_ik_limit_x, b.use_ik_limit_y, b.use_ik_limit_z, b.bone.select = backup.get(b.name)
        for c in b.constraints:
            if c.type =='LIMIT_ROTATION':
                c.influence, b.use_ik_limit_x, b.use_ik_limit_y, b.use_ik_limit_z = store[c.name]

def set_bone_rotation_limit_state(arm, state, all=False):
    if all:
        bones = arm.pose.bones
    else:
        bones = [b for b in arm.pose.bones if b.bone.select]

    return set_rotation_limit(bones, state)

class AvastarFaceWeightGenerator(bpy.types.Operator):
    bl_idname      = "avastar.face_weight_generator"
    bl_label       = "Generate Face weights"
    bl_description = "Generate Face weights (very experimental)"
    bl_options = {'REGISTER', 'UNDO'}

    focus : FloatProperty(name="Focus", min=0, max=1.5, default=0, description="Bone influence offset (very experimental)")
    limit  : BoolProperty(name="Limit to 4", default=True, description = "Limit Weights per vert to 4 (recommended)" )
    gain   : FloatProperty(name="Gain", min=0, max=10, default=1, description="Weight factor(level gain)")
    clean  : FloatProperty(name="Clean", min=0, max=1.0, description="Remove weights < this value")
    use_mirror_x : BoolProperty(name="X Mirror", default=False, description = "Use X-Mirror" )
    suppress_implode : BoolProperty(name="Suppress Implode", default=False, description = "Do not move the Bones back after weighting (for demonstration purposes only, please dont use!)" )

    @classmethod
    def poll(self, context):
        obj=context.object
        if obj != None and obj.type == 'MESH':
            arm = util.get_armature(obj)
            return arm != None
        return False

    @staticmethod
    def explode(arm, use_mirror_x, full_armature=False, bone_names=None, focus=0):

        selects = {}
        deforms = {}
        offsets = {}


        for b in arm.data.edit_bones:
            selects[b.name] = b.select
            b.select=False

        for bname in bone_names:
            b = arm.data.edit_bones.get(bname)
            if bname != 'mHead':


                b.select=True
                h = b.head
                t = b.tail
                d = t - h
                f = focus
                offset = Vector((d[0]*f, d[1]*f, d[2]*f))
                b.tail  += offset
                b.head  += offset
                offsets[bname]=offset


            if bname in NONDEFORMS:
                deforms[b.name]=b.use_deform
                b.use_deform = False
        return selects, deforms, offsets

    @staticmethod
    def implode(arm, selects, deforms, offsets):
        bones=arm.data.edit_bones
        for name, select in selects.items():
            bones[name].select = select

        for bname, offset in offsets.items():
            b = bones[bname]
            b.head -= offset
            b.tail -= offset

            if b.name in NONDEFORMS and b.name in deforms:
                b.use_deform = deforms[b.name]

    @staticmethod
    def store_parameters(arm, focus, gain, clean):
        bones=[b for b in util.get_modify_bones(arm) if b.select]
        for b in bones:
            b['focus']  = focus
            b['gain']   = gain
            b['clean']  = clean

    def invoke(self, context, event):
        self.use_mirror_x = context.object.data.use_mirror_x
        return self.execute(context)

    def execute(self, context):
        return AvastarFaceWeightGenerator.generate(context, self.use_mirror_x, self.focus, self.gain, self.clean, self.limit, self.suppress_implode, 'ALL')

    @staticmethod
    def generate(context, use_mirror_x, focus, gain, clean, limit, suppress_implode, bone_selection_type):

        def get_target_bones(armobj, bone_selection_type, use_mirror_x):
            excludes = [B_EXTENDED_LAYER_SL_EYES, B_EXTENDED_LAYER_ALT_EYES]
            sections =  [B_LAYER_DEFORM_FACE]
            selected_bone_names = data.get_selected_bones(armobj, bone_selection_type, sections, excludes)
            if use_mirror_x:
                bone_names = set(selected_bone_names)
                for name in selected_bone_names:
                    mirror_name = util.get_mirror_name(name)
                    if mirror_name:
                        bone_names.add(mirror_name)
                selected_bone_names = list(bone_names)
            return selected_bone_names

        obj=context.object
        omode = obj.mode
        arm = util.get_armature(obj)
        amode = arm.mode
        selected_bone_names = get_target_bones(arm, bone_selection_type, use_mirror_x)
        use_full_armature = not 'avastar' in arm

        util.ensure_mode_is("OBJECT")

        util.set_active_object(bpy.context, arm)
        arm.data.pose_position="REST"
        active_bone_name = arm.data.bones.active.name if arm.data.bones.active else None

        util.ensure_mode_is("EDIT")
        selects, deforms, offsets = AvastarFaceWeightGenerator.explode(arm, use_mirror_x, full_armature=use_full_armature, bone_names=selected_bone_names, focus=focus)
        util.ensure_mode_is("POSE")

        util.set_active_object(bpy.context, obj)
        util.ensure_mode_is("WEIGHT_PAINT")
        bpy.ops.paint.weight_from_bones()

        bpy.ops.object.vertex_group_levels(group_select_mode='BONE_SELECT', gain=gain)
        bpy.ops.object.vertex_group_clean(group_select_mode='BONE_SELECT', limit=clean)

        if limit:
            bpy.ops.object.vertex_group_limit_total(group_select_mode='BONE_SELECT')

        util.set_active_object(bpy.context, arm)

        AvastarFaceWeightGenerator.store_parameters(arm, focus, gain, clean)

        util.ensure_mode_is("EDIT")
        if not suppress_implode:
            AvastarFaceWeightGenerator.implode(arm, selects, deforms, offsets)

        util.ensure_mode_is(amode)
        bpy.context.object.data.pose_position="POSE"
    
        bpy.ops.pose.select_all(action='DESELECT')
        for bname in selected_bone_names:
            arm.data.bones[bname].select=True
        if active_bone_name:
            arm.data.bones[active_bone_name].select=True
            if obj.vertex_groups.get(active_bone_name):
                obj.vertex_groups.active = obj.vertex_groups[active_bone_name]

        return{'FINISHED'}

def get_islands(ob, minsize=1):
    island_id    = 0
    island_map   = {}
    islands      = {}

    def merge_islands(parts):
        iterparts = iter(parts)
        first= next(iterparts)
        for part in iterparts:
            src  = islands[part]
            islands[first].update(src)
            for key in src:
                island_map[key] = first
            islands[part].clear()
        return first

    for poly in ob.data.polygons:
        parts = sorted({island_map[index] for index in poly.vertices if index in island_map})

        if len(parts) > 0:
            id = merge_islands(parts)
        else:
            id = island_id
            islands[id] = {}
            island_id  += 1

        island = islands[id]
        for vert in poly.vertices:
            island_map[vert] = id
            island[vert]=True
            
    return [island for island in islands.values() if len(island) >= minsize]

def select_island(ob, minsize=1):
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.reveal()
    ob.update_from_editmode()
    
    islands = get_islands(ob, minsize)
    active_island = None
    for island in islands:
        if (active_island == None or len(island) > len(active_island)) and len(island) >= minsize:
            active_island = island

    if active_island:
        log.info("Found island of size %d" % len(active_island))
        util.mode_set(mode='OBJECT')
        for index in active_island:
            ob.data.vertices[index].select = True
        util.mode_set(mode='EDIT')
    return active_island

def convert_weight_groups(armobj, obj, armature_type=SLMAP):
    for group in obj.vertex_groups:
        tgt_name = map_sl_to_Avastar(group.name, type=armature_type, all=True)
        if tgt_name and tgt_name in armobj.pose.bones:
            gname = tgt_name
            if 'm' + gname in armobj.pose.bones:
                gname = 'm' + gname

            if gname != group.name:
                log.info("|- convert weightgroup %s to %s" % (group.name, gname) )
                if gname in obj.vertex_groups:
                    util.merge_weights(obj, group, obj.vertex_groups[gname])
                    obj.vertex_groups.remove(group)
                else:
                    group.name = gname
            if gname in armobj.data.bones:
                dbone = armobj.data.bones.get(gname)
                dbone.use_deform = True
        else:
            log.info("convert_weight_groups: Ignore Group %s (not a %s group)" % (group.name, armature_type) )

class AvastarFromManuelLab(bpy.types.Operator):

    bl_idname = "avastar.convert_from_manuel_lab"
    bl_label = "Convert to Avastar"
    bl_description = "Store current Slider settings in last selected Preset"

    def convert_weights(self, context, children):
        log.info("Converting %d children from Manuel_Lab to Avastar..." % len(children) )
        for ob in children:
            log.info("Converting %s" % ob.name)

            if ob.type == 'MESH':
               log.info("ob is a MESH")
               arm = util.get_armature(ob)
               if arm and arm.get('avastar',None) is None:
                   log.info("ob ARMATURE %s" % arm.name)
                   util.set_active_object(bpy.context, ob)
                   bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
                   for mod in [ mod for mod in ob.modifiers if mod.type=='ARMATURE']:
                       log.info("Removed Modifier %s" % mod.name)
                       bpy.ops.object.modifier_apply(modifier=mod.name)
                   util.remove_object(context, arm)
                   log.info("deleted %s" % arm.name)

            convert_weight_groups(arm, obj, armature_type=MANUELMAP)













    def execute(self, context):
        active = bpy.context.active_object
        children = util.get_meshes(context, type='MESH', select=True, visible=True, hidden=False)

        self.convert_weights(context, children)

        avastars = [arm for arm in util.get_meshes(context, type='ARMATURE', select=True, visible=True, hidden=False) if arm.get('avastar',None)]
        if len(avastars) == 0:
            avastars = [arm for arm in util.get_meshes(context, type='ARMATURE', select=None, visible=True, hidden=False) if arm.get('avastar',None)]

        if len(avastars) == 1:
            util.set_active_object(bpy.context, avastars[0])
            select = util.object_select_get(active) 
            util.object_select_set(active, True)
            bpy.ops.avastar.store_bind_data()
            context.scene.MeshProp.weightSourceSelection = 'NONE'
            context.scene.MeshProp.bindSourceSelection = 'NONE'
            excludes=[B_EXTENDED_LAYER_SL_EYES, B_EXTENDED_LAYER_ALT_EYES]
            from . import mesh
            mesh.bind_to_armature(self,
                context, 
                avastars[0],
                excludes=excludes,
                enforce_meshes = None )

            bpy.ops.avastar.alter_to_restpose()
            util.object_select_set(active, select)

        util.set_active_object(bpy.context, active)
        return {'FINISHED'}
import time

def fix_manuel_object_name(ob):

    if not (ob.data and ob.data.vertices and len(ob.data.vertices) > 0):
        log.error("Found issues with MANUELLAB object %s" % (ob.name) )

    vcount = len(ob.data.vertices)

    try:
        name, part = ob.name.split('.')
    except:
        name= ob.name
        part = 'Brows'
    side = ''
    if   vcount == 114:   part = "Tongue"
    elif vcount == 3475:  part = "Teeth"
    elif vcount  > 10000: part = "Body"
    else:
        side = "Right" if ob.data.vertices[0].co.x < 0 else "Left"
        if   vcount == 286: part = "Eyeball"
        elif vcount == 346: part = "Iris"
        else: side = ''
    if part != '':
        ob.name = "%s.%s%s" % (name,part,side)
    ob.name = ob.name.replace("humanoid_human","avatar_")

def avastar_split_manuel(context, active, island_min_vcount):
    omode  = active.mode
    mesh_select_mode = util.set_mesh_select_mode((True, False, False))
    running = True
    sepcount = 0
    while running:
        util.set_active_object(context, active)
        util.mode_set(mode='EDIT')
        island = select_island(active, minsize=island_min_vcount)
        if not island:
            break

        if sepcount == 0:
            if len(island) == len(active.data.vertices):
                log.warning("The Mesh %s has no islands, maybe not a MANUELLAB character?" % active.name)
                break

        util.progress_update(100, absolute=False)

        bpy.ops.mesh.separate(type='SELECTED')
        util.mode_set(mode='OBJECT')
        sepcount += 1

    bpy.ops.mesh.select_all(action='DESELECT')
    util.mode_set(mode=omode)
    util.set_mesh_select_mode(mesh_select_mode)
    return sepcount


class AvastarMergeWeights(bpy.types.Operator):

    bl_idname = "avastar.merge_weights"
    bl_label = "Merge weights of selected to active"
    bl_description = "Try automatic weight from bones using islands"

    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH'

    def convert_weight_groups(self, obj, active, selected):
        active_group = obj.vertex_groups.get(active.name,None)
        if not active_group:
            active_group = obj.vertex_groups.new(name=active.name)

        for bone in selected:
            bgroup = obj.vertex_groups[bone.name]
            util.merge_weights(obj, bgroup, active_group)
            obj.vertex_groups.remove(bgroup)

        return active_group

    def execute(self, context):
        obj    = context.object
        arm    = util.get_armature(obj)
        bones  = util.get_modify_bones(arm)
        active_bone = bones.active
        
        selected = [b for b in bones if b.select and not b==active_bone and b.name in obj.vertex_groups]
        
        if not active_bone:
            self.report({'ERROR'},"No bone selected")
            return {'CANCELLED'}
 
        active_group = self.convert_weight_groups(obj, active_bone, selected)
        active_bone.select = True
        util.mode_set(toggle=True) # Enforce display of updated weight group in edit mode
        util.mode_set(toggle=True)
        return {'FINISHED'}


class ButtonEnableIK(bpy.types.Operator):
    bl_idname = "avastar.ik_enable"
    bl_label = "IK"
    bl_description = "Enable IK"
    
    @staticmethod
    def set_ik_status(context, enable_ik, ik_target_name, ik_property):
        active = context.active_object
        arm = util.get_armature(active)
        if enable_ik:
            ik_property = True
            ButtonEnableIK.set_ik_influence(arm, 1.0, ik_target_name)
        else:

            if arm.IKSwitchesProp.snap_on_switch:
                if ik_property: # switching IK off

                    ButtonApplyIK.apply(context, ik_target_name, 'BOTH')
                else:
                    apply_ik_orientation(context, arm, apply_all=True, target=ik_target_name)

            ik_property = ButtonEnableIK.toggle_ik_influence(arm, ik_property, ik_target_name)
            
        return ik_property

    @staticmethod 
    def toggle_ik_influence( arm, switch, bname):
        switch = not switch
        influence = 1.0 if switch else 0

        ButtonEnableIK.set_ik_influence(arm, influence, bname)

        omode = util.ensure_mode_is('OBJECT')
        util.ensure_mode_is(omode)

        return switch

    @staticmethod    
    def set_ik_influence(arm, influence, bname):
    
        def set_influence(side):
            bone = arm.pose.bones.get(bname+side, None)
            if bone:
                set_ik_val(bone.parent, influence)
                set_targetless_val(bone, 1-influence)
            else:
                log.info("Ignore IK for missing bone %s" % bname+'Left')

        def set_ik_val(bone, val):
            con = bone.constraints.get(IKNAME)
            if con:
                con.influence = val
            else:
                log.warning("Can not find an 'IK' constraint on %s" % bone.name)

        def set_targetless_val(bone, val):
            con = bone.constraints.get(TARGETLESS_NAME)
            if val:
                if not con:
                    con = create.create_ik_targetless_cons(bone)
                con.influence = val
            else:
                if con:
                    bone.constraints.remove(con)

        def set_arm_ik_seed():
            Q_L_SEED = Quaternion((1.0, 6.940589810255915e-05, 0.00010705369641073048, -0.0004172624321654439))
            Q_R_SEED = Quaternion((1.0, -1.9306872767188565e-10, -3.7021419263538746e-10, 0.00043633230961859226))

            if util.similar_quaternion(arm.pose.bones['ElbowLeft'].rotation_quaternion, Quaternion()):
                arm.pose.bones['ElbowLeft'].rotation_quaternion = Q_L_SEED
            if util.similar_quaternion(arm.pose.bones['ElbowRight'].rotation_quaternion, Quaternion()):
                arm.pose.bones['ElbowRight'].rotation_quaternion = Q_R_SEED

        if bname == 'Face':
            ButtonEnableIK.set_face_controller_influence(arm, arm.IKSwitchesProp.face_ik_value)            
        else:
            set_influence('Left')
            set_influence('Right')
            if bname == 'Wrist' and influence > 0:
                set_arm_ik_seed()

        return

    @staticmethod
    def set_face_controller_influence(arm, influence):

        def set_influence(bname, side):
            bone = arm.pose.bones.get(bname+side, None)
            if bone:
                con = rig.get_IK_constraint(bone)
                if con:
                    con.influence = influence
                else:
                    log.warning("Can not find an 'IK' constraint on %s" % bname)
            else:
                log.info("Ignore IK for missing bone %s" % bname+'Left')

        face_controller = create.FaceController(arm.get(create.FaceController.ID))
        face_controller.adjust_influences(arm, influence)
        return

class ButtonApplyIK(bpy.types.Operator):
    bl_idname = "avastar.ik_apply"
    bl_label ="Apply to FK Rig"
    bl_description ="Apply IK pose to FK Rig"

    limb_items = (
            ('NONE', 'None',   'None'),
            ('HAND', 'Hand',   'Bake Hand Bone IK to FK'),
            ('ARM' , 'Arm',    'Bake Arm  Bone IK to FK'),
            ('LEG' , 'Leg',    'Bake Leg  Bone IK to FK'),
            ('HIND' , 'Hind',  'Bake Hind Bone IK to FK'),
            ('FACE' , 'Face',  'Bake Face Bone IK to FK')
    )

    symmetry_items = (
            ('Left', 'None', 'None'),
            ('Right', 'Hand', 'Bake Hand Bones IK to FK'),
            ('BOTH' , 'Arm',  'Bake Arm  Bones IK to FK')
    )

    limb : EnumProperty(
        items=limb_items,
        name = "Limb",
        description = "Which Limb shall be baked from IK to FK",
        default='NONE')
        
    symmetry : EnumProperty(
        items=symmetry_items,
        name="Symmetry",
        description="Which side of the Skeleton shall be baked from IK to FK",
        default='BOTH')
    
    @classmethod
    def description(cls, context, properties):
        limb = ButtonApplyIK.limb_items[properties['limb']][1]
        symmetry = properties['symmetry']
        templ = "Affects only the %s FK Bones\n\n"\
              + "Detail:\n"\
              + "Pose the %s FK bones ++such that they keep in the position enforced by the IK bones.\n"\
              + "This ensures the bones remain in place when you disable IK.\n\n"\
              + "Important: Remember to keyframe the FK Bones!"
        return templ % (limb,limb)

    @staticmethod
    def apply(context, limb, symmetry):
        active = context.active_object
        armobj = util.get_armature(active)
        bone_names = []

        if   limb == 'ARM' or limb == 'Wrist':
            bone_names = LArmBones if symmetry == 'Left' else RArmBones if symmetry == 'Right' else  LArmBones|RArmBones
        elif limb == 'LEG' or limb == 'Ankle':
            bone_names = LLegBones if symmetry == 'Left' else RLegBones if symmetry == 'Right' else  LLegBones|RLegBones
        elif limb == 'LIMB' or limb == 'HindLimb3':
            bone_names = LHindBones if symmetry == 'Left' else RHindBones if symmetry == 'Right' else  LHindBones|RHindBones
        elif limb == 'FACE' or limb == 'Face':
            pass # disabled for now

        elif limb == 'HAND':
            hand_ik_bones = [b.name for b in armobj.pose.bones if b.name.startswith("ik") and "Target" in b.name]
            for name in hand_ik_bones:
                part = name[2:name.index("Target")]
                if part in ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']:
                    sym = "Left" if name.endswith("Left") else "Right"
                    if sym == symmetry or symmetry == 'BOTH':
                        for index in range(1,4):
                            name = "Hand%s%d%s" % (part, index, sym)
                            bone_names.append(name)

        if bone_names:
            old_states = util.get_pose_bone_select(armobj)
            util.set_bone_select_mode(armobj, state=True, boneset=bone_names, additive=False)
            bpy.ops.pose.visual_transform_apply()
            util.restore_pose_bone_select(armobj, old_states)

    def execute(self, context):
        ButtonApplyIK.apply(context, self.limb, self.symmetry)
        return{'FINISHED'}


def get_bone_recursive(posebone, ii, stopname='Pelvis'):
    result = posebone    
    if result.name != stopname:
        for i in range(0,ii):
            result = result.parent
            if result.name == stopname:
                break
    return result

def setIKTargetOrientation(armobj, parent, child, target, line, handle, is_arm):

    try:
        pbones = armobj.pose.bones
        bchild = pbones.get(child)
        bparent = pbones.get(parent)
        btarget = pbones.get(target)
        bhandle = pbones.get(handle)

        ph=bparent.matrix.translation
        ch=bchild.matrix.translation
        ct=bhandle.matrix.translation
        cross= (ph-ch).cross(ch-ct)
        if is_arm and cross.magnitude > 0.0001:
            cv = (ct-ch).normalized()
            pv = (ch-ph).normalized()
            n= 1 if pv.dot(cv) < 0 else -1
            trans = ((cv-pv)*n).normalized()*(btarget.head-bchild.head).magnitude+bchild.head
            btarget.matrix.translation=trans
        else:
            M1 = bparent.matrix
            M2 = bparent.bone.matrix_local
            m = btarget.bone.matrix_local
            M = mulmat(M1, M2.inverted(), m)    
            btarget.matrix = M

    except KeyError:
        log.error("Can not calculate Pole Target location (bones missing)")

def setIKPoleboneOrientation(context, obj, ankle, ikAnkle, ikHeel, ikKneeTarget):
    try:
        M1 = obj.pose.bones[ankle].matrix
        M2 = obj.pose.bones[ikAnkle].matrix
        M3 = obj.pose.bones[ikHeel].matrix
        m = obj.pose.bones[ikKneeTarget].matrix
        t = m.to_translation()

        #
        con = obj.pose.bones[ikKneeTarget].constraints.new('LIMIT_LOCATION')
        con.owner_space = 'POSE'
        con.min_x = con.max_x = t.x
        con.min_y = con.max_y = t.y
        con.min_z = con.max_z = t.z
        con.use_min_x = con.use_max_x = True
        con.use_min_y = con.use_max_y = True
        con.use_min_z = con.use_max_z = True


        obj.pose.bones[ikHeel].matrix = mulmat(M1, M2.inverted(), M3)

        util.update_view_layer(context)


        obj.pose.bones[ikKneeTarget].matrix = m


        obj.pose.bones[ikKneeTarget].constraints.remove(con)
    except KeyError: pass

def setIKElbowTargetOrientation(context, obj, side):
    parent = 'Shoulder' + side
    child = 'Elbow' + side
    target = 'ikElbowTarget' + side
    line = 'ikElbowLine' + side
    handle = 'ikWrist' + side
    setIKTargetOrientation(obj, parent, child, target, line, handle, is_arm=True)

def setIKKneeTargetOrientation(context, obj, side):
    parent = 'Hip' + side
    child = 'Knee' + side
    target = 'ikKneeTarget' + side
    line = 'ikKneeLine' + side
    handle = 'ikAnkle' + side

    setIKTargetOrientation(obj, parent, child, target, line, handle, is_arm=False)

def setIKHindLimb2TargetOrientation(context, obj, side):
    parent = 'HindLimb1' + side
    child = 'HindLimb2' + side
    target = 'ikHindLimb2Target' + side
    line = 'ikHindLimb2Line' + side
    handle = 'ikHindLimb3' + side
    
    setIKTargetOrientation(obj, parent, child, target, line, handle, is_arm=False)

def setIKAnkleOrientation(context, obj, side):
    ankle        = 'Ankle' + side
    ikAnkle      = 'ik' + ankle
    ikHeel       = 'ikHeel' + side
    ikKneeTarget = 'ikKneeTarget' + side
    setIKPoleboneOrientation(context, obj, ankle, ikAnkle, ikHeel, ikKneeTarget)

def setIKHindLimb3Orientation(context, obj, side):
    ankle        = 'HindLimb3' + side
    ikAnkle      = 'ik' + ankle
    ikHeel       = 'ikHindHeel' + side
    ikKneeTarget = 'ikHindLimb2Target' + side
    setIKPoleboneOrientation(context, obj, ankle, ikAnkle, ikHeel, ikKneeTarget)


def setIKWristOrientation(context, obj, side):
    wrist         = 'Wrist'         + side
    ikWrist       = 'ik' + wrist
    ikElbowTarget = 'ikElbowTarget' + side

    try:
        M = obj.pose.bones[wrist].matrix.copy()
        m = obj.pose.bones[ikElbowTarget].matrix.copy()
        t = m.to_translation()


        con = obj.pose.bones[ikElbowTarget].constraints.new('LIMIT_LOCATION')
        con.owner_space = 'POSE'
        con.min_x = con.max_x = t.x
        con.min_y = con.max_y = t.y
        con.min_z = con.max_z = t.z
        con.use_min_x = con.use_max_x = True
        con.use_min_y = con.use_max_y = True
        con.use_min_z = con.use_max_z = True


        obj.pose.bones[ikWrist].matrix = M
        util.update_view_layer(context)


        obj.pose.bones[ikElbowTarget].matrix = m


        obj.pose.bones[ikElbowTarget].constraints.remove(con)
    except KeyError:
        print ("Key error wrist:[%s] ikWrist:[%s] ikElbowTarget:[%s] (ignore)" % (wrist, ikWrist, ikElbowTarget))
        pass


def apply_ik_orientation(context, armature, apply_all=False, target=None):

    if target == 'Face':

        return

    bones = set([b.name for b in armature.data.bones if apply_all or b.select])
    hasLLegBones  = not bones.isdisjoint(LLegBones)
    hasRLegBones  = not bones.isdisjoint(RLegBones)
    hasLArmBones  = not bones.isdisjoint(LArmBones)
    hasRArmBones  = not bones.isdisjoint(RArmBones)
    hasLHindBones = not bones.isdisjoint(LHindBones)
    hasRHindBones = not bones.isdisjoint(RHindBones)
    

    hasLPinchBones = not bones.isdisjoint(LPinchBones)
    hasRPinchBones = not bones.isdisjoint(RPinchBones)
    hasGrabBones  = not bones.isdisjoint(GrabBones)

    if target==None or target=='Wrist':
        if hasLArmBones:
            setIKWristOrientation(context, armature, 'Left')
            setIKElbowTargetOrientation(context, armature, 'Left')
        if hasRArmBones:
            setIKWristOrientation(context, armature, 'Right')
            setIKElbowTargetOrientation(context, armature, 'Right')

    if target==None or target=='Ankle':
        if hasLLegBones:
            setIKAnkleOrientation(context, armature, 'Left')
            setIKKneeTargetOrientation(context, armature, 'Left')
        if hasRLegBones:
            setIKAnkleOrientation(context, armature, 'Right')
            setIKKneeTargetOrientation(context, armature, 'Right')

    if target==None or target=='HindLimb3':
        if hasLHindBones:
            setIKHindLimb3Orientation(context, armature, 'Left')
            setIKHindLimb2TargetOrientation(context, armature, 'Left')
        if hasRHindBones:
            setIKHindLimb3Orientation(context, armature, 'Right')
            setIKHindLimb2TargetOrientation(context, armature, 'Right')





def copy_pose_from_armature(context, srcarm, tgtarm, all=True, use_bonemap=False):

    def matches_filter(name,filter):
        if filter:
            for key in filter:
                if key in name:
                    return True
        return False

    def bones_in_hierarchical_order(arm, roots=None, bone_names=None, filter=None):
        if not bone_names:
            bone_names = []
        if not roots:
            roots = [b for b in arm.data.bones if b.parent == None]
        for root in [n for n in roots]:
            if not matches_filter(root.name, filter):
                bone_names.append(root.name)
            if root.children:
                bones_in_hierarchical_order(arm, root.children, bone_names, filter=filter)
        return bone_names

    active = util.get_active_object(context)
    util.set_active_object(context, tgtarm)
    src_bones = srcarm.pose.bones
    tgt_bones = tgtarm.pose.bones
    names  = bones_in_hierarchical_order(tgtarm, filter=['ik', 'Link'])
    setSLBoneLocationMute(None, context, True, 'ALL')
    setSLBoneRotationMute(None, context, True, 'ALL')
    set_bone_rotation_limit_state(tgtarm, False, all=True)
    bonemap = bpy.context.scene.MocapProp if use_bonemap else None
    
    MSW  = srcarm.matrix_world
    MSWI = MSW.inverted()
    MTW  = tgtarm.matrix_world
    MTWI = MTW.inverted()
    SCA  = MSW.to_scale()
    S = matrixScale(SCA)
    
    for name in names:
        tgt = tgt_bones[name]
        source_name = bonemap.get(name) if bonemap else name
        if not source_name:

            continue

        src = src_bones.get(source_name,None)
        if src and (tgt.bone.select or all):
            M = src.matrix
            tgt.matrix = mulmat(S, M)
            tgt.scale = (1,1,1)
            util.mode_set(mode='OBJECT')
            util.mode_set(mode='POSE')

    util.set_active_object(context, active)

class FocusOnBone(bpy.types.Operator):
    """selects a bone and set focus on it (view selected)"""
    bl_idname = "avastar.focus_on_selected"
    bl_label = "Focus Bone"
    bl_options = {'REGISTER', 'UNDO'}

    bname : StringProperty(
        name        = 'Bone',
        description = 'A Bone to put focus on'
    )

    @classmethod
    def poll(self, context):
        ob = context.object
        return ob and ob.type=='ARMATURE'

    def get_location(self, context):
        armobj = context.object
        bones = armobj.pose.bones if armobj.mode in ['POSE','OBJECT'] else armobj.data.edit_bones if armobj.mode=='EDIT' else armobj.data.bones
        bone = bones.get(self.bname, None)

        loc = bone.head if armobj.mode in ['POSE','OBJECT'] else bone.head_local
        if loc != None:
            loc = loc + armobj.matrix_local.translation
        return loc

    def execute(self, context):

        loc = self.get_location(context)

        if loc != None:
            util.set_bone_select_mode(context.object, True, boneset=[self.bname], additive=False)
            cloc = util.get_cursor(context)
            util.set_cursor(context, loc)
            ctx = util.find_view_context(context)
            if ctx:
                bpy.ops.view3d.view_center_cursor(ctx)

        return {'FINISHED'}


class DrawOffsets(bpy.types.Operator):
    '''Draw offsets from current rig to SL Default Rig (Using the Grease Pencil)
    
Please use the Grease Pencil tools in the 'N' properties sidebar
to edit or remove the lines when you no longer need them'''    

    bl_idname = "avastar.draw_offsets"
    bl_label = "Draw Joint Offsets"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        ob = context.object
        return ob and ob.type=='ARMATURE'

    def execute(self, context):
        armobj = context.object
        omode = util.ensure_mode_is('OBJECT')
        pbones  = armobj.pose.bones
        dbones  = armobj.data.bones

        reset_cache(armobj)

        for pbone in pbones:
            dbone = pbone.bone
            if util.bone_is_visible(armobj, dbone):




                slHead, slTail = get_sl_bindposition(armobj, dbone, use_cache=True)       # Joint: SL Restpose location
                cuHead, cuTail = get_custom_bindposition(armobj, dbone, use_cache=True)   # Joint: With Joint offsets added
                if slHead and cuHead:

                    slHead = Vector(slHead)
                    cuHead = Vector(cuHead)
                    slTail = Vector(slTail)
                    cuTail = Vector(cuTail)
                    util.gp_draw_line(context, slHead,        cuHead,        lname='offsets', color_index=pbone.bone_group_index, dots=40)
                    util.gp_draw_line(context, slHead+slTail, cuHead+cuTail, lname='offsets', color_index=pbone.bone_group_index, dots=40)





                if cuHead and cuTail:

                    util.gp_draw_line(context, cuHead, cuHead + Vector(cuTail), lname='user-skeleton', color_index=pbone.bone_group_index)





                if slHead and slTail:

                    util.gp_draw_line(context, slHead, slHead + Vector(slTail), lname='sl-skeleton', color_index=pbone.bone_group_index)

        return {'FINISHED'}




def armatureAsDictionary(armobj):
    context = bpy.context
    active = util.get_active_object(context)
    util.set_active_object(context, armobj)
    amode = armobj.mode
    util.mode_set(mode='EDIT')

    dict = {}
    names = Skeleton.bones_in_hierarchical_order(armobj, order='TOPDOWN')
    for name in names:
        dbone = armobj.data.edit_bones[name]
        dict[name] = [dbone.head.copy(), 
                      dbone.tail - dbone.head, 
                      dbone.roll, 
                      None, 
                      dbone.matrix.copy()
                     ]

    util.mode_set(mode='POSE')
    for name in names:
        pbone = armobj.pose.bones[name]
        val = dict[name]
        val[3] = pbone.matrix.copy()
        dict[name] = val

    util.mode_set(mode=amode)
    util.set_active_object(context, active)
    return dict

def matches_filter(name, filter):
    if filter:
        for key in filter:
            if key in name:
                return True
    return False

def bones_in_hierarchical_order(armobj, roots=None, bone_names=None, filter=None, reverse=False):
    if not bone_names:
        bone_names = []
    if not roots:
        roots = [b for b in armobj.data.bones if b.parent == None]

    if reverse:
        bnames = get_bones_in_reverse_hierarchical_order(armobj, roots, bone_names, filter)
    else:
        bnames = get_bones_in_hierarchical_order(armobj, roots, bone_names, filter)
    return bone_names

def get_bones_in_hierarchical_order(armobj, roots, bone_names, filter):
    for root in roots:
        if not matches_filter(root.name, filter):
            bone_names.append(root.name)
        if root.children:
            bone_names = bones_in_hierarchical_order(armobj, root.children, bone_names, filter=filter)
    return bone_names

def get_bones_in_reverse_hierarchical_order(armobj, roots, bone_names, filter):
    for root in roots:
        if root.children:
            bone_names = bones_in_hierarchical_order(armobj, root.children, bone_names, filter=filter, reverse=True)
        if not matches_filter(root.name, filter):
            bone_names.append(root.name)
    return bone_names

def retargetPoseBone(context, 
                     target_pose_bone, 
                     source_rig, 
                     mocap, 
                     source_ref_pose=None, 
                     target_ref_pose=None):

    source_pose_bone = get_source_pose_bone(source_rig, target_pose_bone, mocap)
    if not source_pose_bone:
        return target_pose_bone.matrix.copy(), False

    sm_world = source_rig.matrix_world
    spbonem = source_pose_bone.matrix.copy()

    sdbonem = source_pose_bone.bone.matrix_local.copy()
    if source_ref_pose:

        binfo = source_ref_pose.get(source_pose_bone.name)
        if binfo:
            sdbonem = binfo[3].copy()

    tdbonem = target_pose_bone.bone.matrix_local.copy()
    if target_ref_pose:

        binfo = target_ref_pose.get(target_pose_bone.name)
        if binfo:
            tdbonem = binfo[3].copy()

    matrix = mulmat(spbonem, sdbonem.inverted(), tdbonem)
    matrix.translation = tdbonem.translation + mulmat(sm_world, spbonem.translation) - mulmat(sm_world, sdbonem.translation)

    return matrix, True

def get_source_pose_bone(source_rig, target_pose_bone, mocap):
    source_bone_name = mocap.get(target_pose_bone.name)
    if source_bone_name:
        spbone = source_rig.pose.bones.get(source_bone_name)
        if not spbone:
            log.warning("Mocap bone %s not found in source rig %s" % (source_bone_name, source_rig.name) )
    else:
        spbone = None
        log.debug("Target Bone %s not mapped to source rig %s" % (target_pose_bone.name, source_rig.name) )
        
    return spbone


def armatureFromMocap(context, target, mocap, with_mbones=True, source_ref_pose=None, target_ref_pose=None, refloc=None):

    source = bpy.data.objects[mocap.source]
    active = util.get_active_object(context)
    amode   = active.mode if active else None
    if active:
        util.mode_set(mode='OBJECT')

    util.set_active_object(context, target)
    omode = target.mode
    util.mode_set(mode='POSE')

    bone_names = bones_in_hierarchical_order(target, roots=None, bone_names=None, filter=['ik'])
    pbones  = target.pose.bones






    for bname in bone_names:
        if bname in SLVOLBONES:
            continue # This is for testing only. it looks like some data is applied twice when Volume bones are affected...
        if not with_mbones and bname[0]=='m':
            continue # For retargeting we only retarget to the animation bones

        tpbone = pbones.get(bname, None)
        matrix, changed = retargetPoseBone(context, tpbone, source, mocap, source_ref_pose, target_ref_pose)
        if changed:
            tpbone.matrix = matrix
            util.update_depsgraph(context) # need this to recalculate internal matrices of all pose bones

    tpbone = pbones.get('COG', None)
    if tpbone and refloc:
        tpbone.location -= refloc


    util.mode_set(mode=amode)
    util.mode_set(mode='OBJECT')
    util.mode_set(mode=omode)
    util.set_active_object(context, active)
    util.mode_set(mode=amode)
    
def armatureFromDictionary(context, armobj, dict, mocap=None, with_mbones=True, corr = None):

    if corr == None:
        corr = Vector((0,0,0))

    if mocap == None:
        sceneProps = context.scene.SceneProp
        apply_as_restpose = sceneProps.armature_preset_apply_as_Restpose
        all_bones         = sceneProps.armature_preset_apply_all_bones
        adjust_tails      = sceneProps.armature_preset_adjust_tails
    else:
        source = bpy.data.objects[mocap.source]
        target = bpy.data.objects[mocap.target]
    
        apply_as_restpose = False
        all_bones         = True
        adjust_tails      = False
    
    active = util.get_active_object(context)
    amode   = active.mode if active else None
    if active:
        util.mode_set(mode='OBJECT')
    util.set_active_object(context, armobj)
    omode = armobj.mode
    bone_names = bones_in_hierarchical_order(armobj, roots=None, bone_names=None, filter=['ik'])

    util.mode_set(mode='POSE')










    setSLBoneLocationMute(None, context, True, 'CONTROLLED', is_link=True)
    setSLBoneRotationMute(None, context, True, 'CONTROL',    filter='Link')
    set_bone_rotation_limit_state(armobj, False, all=True)

    pbones  = armobj.pose.bones
    dbones  = armobj.data.bones
    cbones = util.getControlBones(armobj, filter='Link')
    parent_offset = {}


    for bname in bone_names:
        if bname in SLVOLBONES:
            continue # This is for testing only. it looks like some data is applied twice when Volume bones are affected...
        if not with_mbones and bname[0]=='m':
            continue # For retargeting we only retarget to the animation bones



        mapped_name = getattr(mocap,bname,bname) if mocap else bname
        tpbone = pbones.get(bname, None)
        tdbone = dbones.get(bname, None)


        selected = all_bones or (tpbone and tpbone.bone.select)
        if tpbone and selected:

            if mocap and source and target:
                matrix, changed = retargetPoseBone(context, tpbone, source, mocap)
                if changed:
                    tpbone.matrix = matrix
                    util.update_view_layer(context)
                continue

            val = dict.get(mapped_name)
            if val:


                hs = tpbone.bone.hide_select
                tpbone.bone.hide_select=False


                tdmatw  = tdbone.matrix_local
                tdquatw = tdmatw.to_quaternion()


                shead = val[0] # relative to Armature
                stail = val[1] # actually the source bone length vector

                if len(val) > 3:
                    spmatw  = val[3] # source bone pose matrix
                    sdmatw  = val[4] # source bone local matrix (restpose)
                    spquatw = spmatw.to_quaternion()
                    sdquatw = sdmatw.to_quaternion()
                    srot    = sdquatw.rotation_difference(spquatw) # source bone rot relative to its restpose
                    std     = sdquatw.rotation_difference(tdquatw) # rot diff of restposes (source to target)
                    tq      = tdquatw @ std.inverted() @ srot
                    matrix = tq.to_matrix().to_4x4()
                    matrix.translation = spmatw.translation+corr

                else:
                    shead = val[0] # relative to Armature
                    stail = val[1] # actually the source bone length vector
                    matrix = tpbone.matrix.to_3x3()
                    dv     = tpbone.tail - tpbone.head
                    dq     = dv.rotation_difference(stail)
                    matrix.rotate(dq)
                    matrix = matrix.to_4x4()
                    matrix.translation = shead
                
                tpbone.matrix = matrix
                util.mode_set(mode='OBJECT')
                util.mode_set(mode='POSE')

                if adjust_tails and (bname in cbones.keys() or 'Link' in bname) and not apply_as_restpose:
                    pmag = Vector(tpbone.head - tpbone.parent.head).magnitude
                    parent_offset[bname] = pmag
                tpbone.bone.hide_select=hs
                util.update_view_layer(context)


    util.mode_set(mode=amode)

    if apply_as_restpose:

        bpy.ops.avastar.apply_as_restpose()
    elif adjust_tails:

        util.mode_set(mode='EDIT')
        ebones = armobj.data.edit_bones


        for key in bone_names:
            pmag = parent_offset.get(key)
            if pmag:
                ebone = ebones[key]
                eparent = ebone.parent
                if 'Wrist' in eparent.name:

                    continue

                evec = Vector(eparent.tail - eparent.head).normalized()
                if pmag < 0.0000001:
                    print("armatureFromDictionary: Bone parent %s in armature %s too short for calculation" % (ebone.parent.name, armobj.name) )
                else:
                    eparent.tail = eparent.head + evec*pmag

                    mbone = ebones.get('m'+eparent.name)
                    if mbone:
                        mbone.tail = eparent.tail

    util.mode_set(mode='OBJECT')

    util.mode_set(mode=omode)
    util.set_active_object(context, active)
    util.mode_set(mode=amode)


def autosnap_bones(armobj, snap_control_to_rig=False):
    log.info("| autosnap %s" % ("control to rig" if snap_control_to_rig else "rig to control") )
    ebones = armobj.data.edit_bones
    connects = []

    for dbone in [b for b in ebones if b.name[0] == 'm' and b.name[1:] in ebones]:
        cbone = ebones.get(dbone.name[1:])
        if dbone.head==cbone.head and dbone.tail==cbone.tail and dbone.roll==cbone.roll:
            continue    

        master = dbone if snap_control_to_rig else cbone
        slave  = cbone if snap_control_to_rig else dbone
        if slave.use_connect:
            connects.append(slave)
            slave.use_connect=False

        if master.use_connect:
            connects.append(master)
            master.use_connect=False

        slave.head = master.head.copy()
        slave.tail = master.tail.copy()
        slave.roll = master.roll

        if dbone.name == 'mPelvis':
            Pelvis = cbone
            Tinker = get_tinker_bone(ebones)
            if Tinker:
                Tinker.head = Pelvis.tail.copy()
                Tinker.tail = Pelvis.head.copy()

    for slave in connects:
        if slave.parent.tail == slave.head:
            slave.use_connect = True


def add_armature_preset(context, filepath):
    armobj = util.get_armature(context.object)
    pbones = armobj.pose.bones

    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "import avastar\n"
    "from avastar import shape, util, rig\n"
    "from mathutils import Vector, Matrix\n"
    "\n"
    "context=bpy.context\n"
    "armobj = util.get_armature(context.object)\n"
    "print ('Armature Preset:Upload into [%s]' % (armobj.name) )"
    "\n"
    )
    dict = armatureAsDictionary(armobj)
    file_preset.write("dict=" + str(dict) + "\n")
    file_preset.write("rig.armatureFromDictionary(context, armobj, dict)\n")
    file_preset.close()

class AVASTAR_MT_armature_presets_menu(Menu):
    bl_label  = "Armature Presets"
    bl_description = "Armature Presets (bone configurations)\nStore the editbone matrix values for a complete Armature\nThis can later be used\n\n- as Restpose template to setup other Armatures\n- as pose template for posing another armature."
    preset_subdir = os.path.join("avastar","armatures")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class AvastarAddPresetArmature(AddPresetBase, Operator):
    bl_idname = "avastar.armature_presets_add"
    bl_label = "Add Armature Preset"
    bl_description = "Create new Preset from current Rig"
    preset_menu = "AVASTAR_MT_armature_presets_menu"

    preset_subdir = os.path.join("avastar","armatures")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_armature_preset(context, filepath)

class AvastarUpdatePresetArmature(AddPresetBase, Operator):
    bl_idname = "avastar.armature_presets_update"
    bl_label = "Update Armature Preset"
    bl_description = "Store current Slider settings in last selected Preset"
    preset_menu = "AVASTAR_MT_armature_presets_menu"
    preset_subdir = os.path.join("avastar","armatures")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_armature_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_armature_preset(context, filepath)

class AvastarRemovePresetArmature(AddPresetBase, Operator):
    bl_idname = "avastar.armature_presets_remove"
    bl_label = "Remove Armature Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_armature_presets_menu"
    preset_subdir = os.path.join("avastar","armatures")

def getActiveArmature(context):
    active = context.active_object
    if not active:
        return None, None
    if  active.type == "ARMATURE":
        armobj = active
    else:
        armobj = active.find_armature()
    return active, armobj

def setSLBoneRotationMute(operator, context, mute, selection, filter=None, with_reconnect=True, with_synchronize=False):

    def in_range(qsrc, qtgt, maxdiff):
        return 1 - abs(qsrc.dot(qtgt)) < maxdiff

    def synchronize_deform_bones(armobj, bone):
        try:


            cname = bone.name[1:]
            if cname in armobj.pose.bones:
                cbone = armobj.pose.bones[cname]
                if not in_range(bone.rotation_quaternion, cbone.rotation_quaternion, 0.001):

                    if mute:
                        tgt=bone
                        src=cbone
                    else:
                        tgt=cbone
                        src=bone

                    log.warning("Setting %s to %s %s -> %s " % (tgt.name, src.name, tgt.rotation_euler, src.rotation_euler))
                    tgt.rotation_euler = src.rotation_euler.copy()
                    armobj.update_tag(refresh={'DATA'})
                    util.update_view_layer(context) # Need this to update the matrix data of children
        except:
            print(traceback.format_exc())
            pass

    active, armobj = getActiveArmature(context)

    if armobj is None:
        if operator:
            operator.report({'WARNING'},"Active Object %s is not attached to an Armature"%active.name)
        return
    else:
        armature_mode = armobj.mode

        util.set_active_object(context, armobj)
        util.mode_set(mode='POSE')
        locked_bone_names = []

        deformBones = get_pose_bones(armobj, selection, filter, deforming=True)
        Bones = data.get_reference_boneset(armobj, rigtype='EXTENDED')

        for sb in Skeleton.bones_in_hierarchical_order(armobj, order='TOPDOWN'):
            bone = deformBones.get(sb)
            if not bone:
                continue
            rcs = [c for c in bone.constraints if c.type=='COPY_ROTATION']
            if len(rcs) > 0:
                for rc in rcs:
                    rc.mute = True
                    if with_synchronize:
                        synchronize_deform_bones(armobj, bone)
                    rc.mute = mute

                lcs = [c for c in bone.constraints if c.type=='COPY_LOCATION']
                if len(lcs) > 0:
                    for con in lcs:
                        if mute:
                            con.target_space = 'LOCAL'
                            con.owner_space = 'LOCAL'
                        else:
                            con.target_space = 'WORLD'
                            con.owner_space = 'WORLD'

            if with_reconnect:
                locked_bone_names.append(bone.name)

        util.mode_set(mode='EDIT')
        disconnect_errors = 0
        for name in locked_bone_names:
            if name in Bones and name in armobj.data.edit_bones:
                bone = armobj.data.edit_bones[name]
                set_connect(bone, Bones[name].connected if not mute else False, "setSLBoneRotationMute")
            else:
                disconnect_errors += 1
                if disconnect_errors < 10:
                    print("Can not modify rotation lock of bone [%s] " % (name) )

        if disconnect_errors >9:
            print("Could not modify %d more bone rotation locks from %s" % (disconnect_errors-10, armobj.name) )

        bpy.ops.object.editmode_toggle()
        util.mode_set(mode=armature_mode)
        util.set_active_object(bpy.context, active)

def setSLBoneLocationMute(operator, context, mute, selection, is_link=False):

    def lock_ik_bone(armobj, bone, iks, connect_bones):

        if not mute:
            for rc in iks:

                rc.mute = mute

        for ikc in iks:
            ikc.influence = 0.0 if mute else 1.0

        connect_bones[bone.name] = not mute #parent connect


    active, armobj = getActiveArmature(context)
    if armobj is None:
        if operator:
            operator.report({'WARNING'},"Active Object %s is not attached to an Armature"%active.name)
        return
    else:
        armature_mode = armobj.mode

        util.set_active_object(context, armobj)
        util.mode_set(mode='POSE')
        connect_bones = {}

        poseBones = get_pose_bones(armobj, selection, "Link" if is_link else None, deforming=False)

        Bones = data.get_reference_boneset(armobj, rigtype='EXTENDED')
        for bone in poseBones.values():
            has_location_constraint = False
            iks = [c for c in bone.constraints if c.type=='IK' and c.target==None]
            if len(iks) > 0:

                lock_ik_bone(armobj, bone, iks, connect_bones)
                has_location_constraint = True

            if is_link and "Link" in bone.name:

                connect_bones[bone.name]=not mute
            
            if bone.name=='Tinker' or not has_location_constraint:

                bone.lock_location[0] = not mute
                bone.lock_location[1] = not mute
                bone.lock_location[2] = not mute
                connect_bones[bone.name] = not mute

        util.mode_set(mode='EDIT')
        disconnect_errors = 0
        for name, muted in connect_bones.items():
            Bone = Bones.get(name)
            if name == 'Tinker' or (Bone and Bone.connected):
                try:
                    bone = armobj.data.edit_bones[name]
                    set_connect(bone, muted, "setSLBoneLocationMute")
                    mbone = armobj.data.edit_bones.get('m'+name)
                    if mbone:
                        set_connect(mbone, muted, "setSLBoneLocationMute")
                except:
                    disconnect_errors += 1
                    if disconnect_errors < 10:
                        print("Can not modify connect of bone [%s] " % (name) )
                        raise

        if disconnect_errors >9:
            print("Could not modify %d more location locks from %s" % (disconnect_errors-10, armobj.name) )

        bpy.ops.object.editmode_toggle()
        util.mode_set(mode=armature_mode)
        util.set_active_object(context, active)


def setSLBoneVolumeMute(operator, context, mute, selection, filter=None):
    active, armobj = getActiveArmature(context)
    if armobj is None:
        if operator:
            operator.report({'WARNING'},"Active Object %s is not attached to an Armature"%active.name)
        return
    else:
        armature_mode = armobj.mode
        util.set_active_object(context, armobj)
        util.mode_set(mode='POSE')

        pose_bones = get_pose_bones(armobj, selection, filter, deforming=True)
        for name in [ b for b in SLVOLBONES if not filter or (filter and filter in b.name)]:
            bone = pose_bones.get(name)
            if not bone:
                continue

            bone.lock_location[0] = mute
            bone.lock_location[1] = mute
            bone.lock_location[2] = mute

        bpy.ops.object.editmode_toggle()
        util.mode_set(mode=armature_mode)
        util.set_active_object(context, active)

def get_pose_bones(armobj, selection, filter=None, ordered=False, spine_check=False, deforming=True):

    def is_disabled_spine_bone(name):
        if name.startswith("Spine"):
            spine_id = int(name[5])
        elif name.startswith("mSpine"):
            spine_id = int(name[6])
        else:
            return False
        
        if spine_id in range(1,3) and armobj.RigProp.spine_unfold_lower:
            return False
        if spine_id in range(3,5) and armobj.RigProp.spine_unfold_upper:
            return False
        return True

    def collect_pose_bones_from(armobj, bones, deforming):
        pose_bones = []
        for b in bones:
            if b.name.startswith('ik'):
                continue

            pb = armobj.pose.bones.get(b.name)
            if pb:


                if deforming and not b.use_deform:
                    if 'm'+b.name in bones:
                        pb = armobj.pose.bones.get('m'+b.name)
                elif not deforming and b.use_deform:
                    if b.name[1:] in bones:
                        pb = armobj.pose.bones.get(b.name[1:])
                pose_bones.append(pb)
        return pose_bones

    def get_active_bone(armobj):
        active = armobj.data.bones.active
        if active and not active.use_deform:
            if 'm' + active.name in armobj.pose.bones:
                active = armobj.pose.bones['m'+active.name] 
            else:
                active = None
        return active

    def get_control_bones(armobj, pose_bones):
        pbs=[]
        for b in pose_bones:
            if b.name[0]=='m':
                if b.name[1:] in armobj.pose.bones:
                    pbs.append(armobj.pose.bones.get(b.name[1:]))
                else:
                    continue
            else:
                pbs.append(b)
        return pbs

    pose_bones = []
    result = {}
                
    if selection == 'SELECTION':
        pose_bones = collect_pose_bones_from(armobj, util.getVisibleSelectedBones(armobj), deforming)
    elif selection == 'VISIBLE':
        pose_bones = collect_pose_bones_from(armobj, util.getVisibleBones(armobj), deforming)
    elif selection == 'SIMILAR':
        active = get_active_bone(armobj)
        if active:
            gindex = active.bone_group_index
            pose_bones = [b for b in armobj.pose.bones if b.bone_group_index==gindex]
            if not deforming:
                pose_bones = get_control_bones(armobj, pose_bones)

    elif selection == 'CONTROL':
        return util.getControlBones(armobj, filter)
    elif selection == 'LINK':
        return util.getLinkBones(armobj)
    elif selection == 'CONTROLLED':
        return util.getControlledBones(armobj, filter)
    elif selection == 'DEFORM':
        return util.get_deform_bone_names(armobj)
    else:
        pose_bones = collect_pose_bones_from(armobj, armobj.data.bones, deforming)



    for b in pose_bones:

        if spine_check and is_disabled_spine_bone(b.name):
            continue

        result[b.name]=b

    return result

def MuteArmaturePoseConstraints(context, armobj):
    active = context.object
    armature_mode = armobj.mode
    util.set_active_object(context, armobj)
    util.mode_set(mode='OBJECT')

    names = Skeleton.bones_in_hierarchical_order(armobj)
    bones = armobj.pose.bones
    con_states = {}
    for name in names:
        bone = bones[name]
        if len(bone.constraints) > 0:
            constraints = {}
            con_states[name] = constraints
            for cons in bone.constraints:
                constraints[cons.name] = [cons.mute, cons.influence]
                cons.mute      = True
                cons.influence = 0

    util.mode_set(mode=armature_mode)
    util.set_active_object(context, active)
    return con_states

def RestoreArmaturePoseConstraintsMute(context, armobj, con_states):
    active = context.object
    armature_mode = armobj.mode
    util.set_active_object(context, armobj)
    util.mode_set(mode='OBJECT')

    names = Skeleton.bones_in_hierarchical_order(armobj, order='BOTTOMUP')
    bones = armobj.pose.bones
    for name, constraints in con_states.items():
        bone = bones[name]
        for cons_name, mute_state in constraints.items():
            cons = bone.constraints[cons_name]
            mute_state     = val[0]
            influence      = val[1]
            cons.mute      = mute_state
            cons.influence = influence

    util.mode_set(mode=armature_mode)
    util.set_active_object(context, active)






def get_master_bone(bones, bone):

    return get_deform_bone_for(bones, bone)

def get_deform_bone_for(bones, bone):

    if not bone:
        return None

    name = bone.name
    if name[0] in ['a','m']:
        return bone

    if name in ['Tinker','PelvisInv']:
        return bones.get('mPelvis', bone)

    return bones.get('m'+name, bone)

def bind_rotation_diff(armobj, dbone, use_cache=True, use_bind_pose=None):
    if use_bind_pose == None:
        use_bind_pose = armobj.RigProp.rig_use_bind_pose
    sl_tail = get_bind_tail(armobj, dbone, use_cache=use_cache)
    if not (use_bind_pose and sl_tail):
        return Matrix()

    MT  = util.get_bone_scale_matrix(dbone, inverted=False) if dbone.parent else Matrix()
    cu_tail = dbone.tail-dbone.head
    R = sl_tail.rotation_difference(cu_tail).to_matrix().to_4x4()
    return R

def get_bind_tail(armobj, dbone, use_cache=True):
    connected = [c for c in dbone.children if c.use_connect]
    if connected:
        head,dummy=get_sl_bindposition(armobj, dbone, use_cache=use_cache)
        tail,dummy=get_sl_bindposition(armobj, connected[0], use_cache=use_cache)
        reltail = tail - head
    else:
        head, tail = util.get_bone_location(armobj, dbone.name)
        MT  = util.get_bone_scale_matrix(dbone, inverted=False) if dbone.parent else Matrix()
        btail = dbone.get(JOINT_BASE_TAIL_ID, None)
        reltail = mulmat(MT, Vector(btail)) if btail else tail - head
    return reltail

def get_rest_tail(armobj, dbone, use_cache=True):
    connected = [c for c in dbone.children if c.use_connect]
    if connected:
        head,dummy=get_sl_restposition(armobj, dbone, use_cache=use_cache)
        tail,dummy=get_sl_restposition(armobj, connected[0], use_cache=use_cache)
        reltail = tail - head
    else:
        reltail = Vector(dbone[JOINT_BASE_TAIL_ID])
    return reltail

def get_parent_bone(bone, with_structure=False):
    parent = bone.parent
    if with_structure or not parent:
        return parent
    
    if parent.get('is_structure', False):
        return get_parent_bone(parent, with_structure)

    return parent

def bind_rotation_matrix(armobj, dbone, use_cache=True, use_bind_pose=None):
    if use_bind_pose == None:
        use_bind_pose = armobj.RigProp.rig_use_bind_pose


    if dbone and use_bind_pose:
        slpos, sl_tail = get_sl_restposition(armobj, dbone, use_cache=use_cache)
        cupos, cu_tail = get_custom_restposition(armobj, dbone, use_cache=use_cache, with_joint_offset=True)
        M = sl_tail.rotation_difference(cu_tail).to_matrix()
    else:
        M = Matrix()
    return M

def get_sl_bindmatrix(dbone):
    mat = dbone.get('mat', None)
    if mat:
        M = Matrix(mat)
    else:
        M = Matrix()
    return M

def get_floor_compensation(armobj, pos=None, tail=None, use_cache=False):
    bones = util.get_modify_bones(armobj)
    val = None
    if use_cache:
        val = get_item_cache(armobj, 'floor')
    
    if val:
        dh, dt = Vector(val[0]), Vector(val[1])
    else:
        toe = bones['mToeRight']


        bh,bt = get_custom_bindposition(armobj, toe, use_cache=False, with_joint_offset=True)
        rh,rt = get_custom_restposition(armobj, toe, use_cache=False, with_joint_offset=True)

        ch = toe.head if armobj.mode=='EDIT' else toe.head_local
        ct = (toe.tail if armobj.mode=='EDIT' else toe.tail_local) - ch

        dh = bh-rh
        dt = bt-rt
        dh[0] = dh[1] = 0
        dt[0] = dt[1] = 0

        if use_cache:
            set_item_cache(armobj, 'floor', [dh, dt])

    if pos:
        pos = Vector(pos) - dh
    if tail:
        tail = Vector(tail) - dt

    return pos, tail, dh, dt

def get_rel_loc(arm_obj, master):
    h = get_rel_head(arm_obj, master, update=False)
    t = get_rel_tail(arm_obj, master, update=False)
    return h, t

def update_rel_loc(arm_obj, master):
    h = get_rel_head(arm_obj, master, update=True)
    t = get_rel_tail(arm_obj, master, update=True)
    return h, t

def get_rel_head(arm_obj, master, update):
    h = master.get(JOINT_BASE_HEAD_ID)
    if not h:
        mhead = util.get_bone_head(arm_obj, master)
        phead = util.get_bone_head(arm_obj, master.parent) if master.parent else V0
        h = mhead - phead
        if update:
            master[JOINT_BASE_HEAD_ID] = h
            log.warning("added %s for b:%s h: %s" % (JOINT_BASE_HEAD_ID, master.name, util.toVector(h)) )
        else:
            log.warning("bone %s has no %s" % (master.name, JOINT_BASE_HEAD_ID) )
    h = util.toVector(h)
    return h

def get_rel_tail(arm_obj, master, update):
    t = master.get(JOINT_BASE_TAIL_ID)
    if not t:
        mhead = util.get_bone_head(arm_obj, master)
        t = util.get_bone_tail(arm_obj, master) - mhead
        if update:
            master[JOINT_BASE_TAIL_ID] = t
            log.warning("added %s for b:%s t: %s" % (JOINT_BASE_TAIL_ID, master.name, util.toVector(t)) )
        else:
            log.warning("bone %s has no %s" % (master.name, JOINT_BASE_TAIL_ID) )
    t = util.toVector(t)
    return t




def get_sl_restposition(armobj=None, dbone=None, use_cache=True, with_structure=False, Bones=None, absolute=False):

    if not armobj:
        armobj = bpy.context.object
        if not dbone:
            dbone=bpy.context.active_bone


    if dbone == None:
        return V0.copy(), V0.copy()
    parent  = get_parent_bone(dbone, with_structure)

    
    bones = util.get_modify_bones(armobj)

    
    if use_cache:
        val = get_item_cache(dbone, 'slr')
        if val:
            return Vector(val[0]), Vector(val[1])

    if parent:
        pos, dummy = get_sl_restposition(armobj, parent, use_cache, with_structure, Bones)
    else:
        pos, dummy = Vector((0,0,0)), Vector((0,0,0))

    master = get_master_bone(bones, dbone)
    if Bones:
        bone = Bones.get(master.name)
        d = Vector(bone.relhead)
        t = Vector(bone.reltail)
    else:
        d, t = get_rel_loc(armobj, master)
    pos += d

    if dbone.name in ['Tinker','PelvisInv']:

        tt = t.copy()
        pos += t
        t = -tt

    if use_cache:
        set_item_cache(dbone, 'slr', [pos, t])

    if absolute:
        pos = mulmat(armobj.world_matrix, pos)

    return pos, t

def get_custom_restposition(armobj=None, dbone=None, use_cache=True, with_joint_offset=True, absolute=False, relative=False, joints=None):
    if not armobj:
        armobj = bpy.context.object
        if not dbone:
            dbone=bpy.context.active_bone

    if dbone == None:
        return V0.copy(), V0.copy()
    if joints == None:
        joints = util.get_joint_cache(armobj)

    if use_cache:
        val = get_item_cache(dbone, 'cur')
        if val:
            return Vector(val[0]), Vector(val[1])

    bones = util.get_modify_bones(armobj)
    master = get_master_bone(bones, dbone)
    parent = get_parent_bone(master)
    

    if relative and master.name in ['COG','mPelvis', 'aAvatar Center']:
        M=Matrix()
        if armobj.mode == 'EDIT':
            pos = master.head.copy()
            tail = master.tail - pos
        else:
            pos = master.head_local.copy()
            tail = master.tail_local.copy() - pos
        return pos, tail
    elif parent:
        pos, dummy = get_custom_restposition(armobj, parent, use_cache, with_joint_offset=with_joint_offset, relative=relative, joints=joints)
    else:
        pos, dummy = Vector((0,0,0)), Vector((0,0,0))

    relhead, reltail = get_rel_loc(armobj, master)
    pos += relhead
    
    if joints and with_joint_offset:
        jhead, jtail = util.get_joint_position(joints, master)
        pos += jhead
        tail = reltail+jtail
    else:
        tail = reltail
    
    if dbone.name in ['Tinker','PelvisInv']:

        tt = tail.copy()
        pos += tail
        tail = -tt
   
    if use_cache:
        set_item_cache(dbone, 'cur', [pos, tail])

    if absolute:
        pos = mulmat(armobj.world_matrix, pos)
        tail = mulmat(armobj.matrix_world, tail)

    return pos, tail





#

#




#

def get_sl_bindposition(armobj=None, dbone=None, use_cache=True, absolute=False):
    if not armobj:
        armobj = bpy.context.object
        if not dbone:
            dbone=bpy.context.active_bone


    if dbone == None:
        return V0.copy(), V0.copy()
        
    if use_cache:
        val = get_item_cache(dbone, 'slbr')
        if val:
            return Vector(val[0]), Vector(val[1])

    bones = util.get_modify_bones(armobj)
    master = get_master_bone(bones, dbone)
    parent = get_parent_bone(master)

    if parent:
        pos, dummy = get_sl_bindposition(armobj, parent, use_cache)
    else:
        pos, dummy = Vector((0,0,0)), Vector((0,0,0))



    t   = Vector(master.get(JOINT_BASE_TAIL_ID,(0,0,0)))
    d   = Vector(master.get(JOINT_BASE_HEAD_ID,(0,0,0)))
    d += Vector(master.get('offset', (0,0,0)))

    pmaster = get_master_bone(bones, parent)
    s = util.get_bone_scale(pmaster) if pmaster else V1.copy()
    d = Vector([s[i]*d[i] for i in range(3)])
    s = util.get_bone_scale(master) if master else V1.copy()
    tail = Vector([s[i]*t[i] for i in range(3)])

    pos += d
    
    if dbone.name in ['Tinker','PelvisInv']:

        tt = tail.copy()
        pos += tail
        tail = -tt
    
    if use_cache:
        set_item_cache(dbone, 'slbr', [pos, tail])


    if absolute:
        pos = mulmat(armobj.world_matrix, pos)
        tail = mulmat(armobj.matrix_world, tail)

    return pos, tail

def get_custom_bindposition(armobj, dbone, use_cache=True, with_joint_offset=True, absolute=False, relative=False, joints=None):
    if not armobj:
        return V0, V0
    if not dbone:
        return V0, V0


    if dbone == None:
        return V0.copy(), V0.copy()
    if joints == None:
        joints = util.get_joint_cache(armobj)

    use_bind_pose = armobj.RigProp.rig_use_bind_pose if with_joint_offset else False

    if use_cache:
        val = get_item_cache(dbone, 'cubr')
        if val != None:
            return Vector(val[0]), Vector(val[1])

    bones = util.get_modify_bones(armobj)
    master = get_master_bone(bones, dbone)
    parent = get_parent_bone(master)


    if relative and master.name in ['COG','mPelvis', 'aAvatar Center']:
        M=Matrix()
        if armobj.mode == 'EDIT':
            pos = master.head.copy()
            tail = master.tail - pos
        else:
            pos = master.head_local.copy()
            tail = master.tail_local.copy() - pos
        return pos, tail
    elif parent:
        pos, unused = get_custom_bindposition(armobj, parent, use_cache, relative=relative, joints=joints)
        M  = bind_rotation_matrix(armobj, parent, use_cache, use_bind_pose)
    else:
        pos, unused = Vector((0,0,0)), Vector((0,0,0))
        M = Matrix()


    MT = bind_rotation_matrix(armobj, master, use_cache, use_bind_pose)# if with_joint_offset else Matrix()
    
    d, t = get_rel_loc(armobj, master)


    if joints and with_joint_offset:
        jh, jt = util.get_joint_position(joints, master)
    else:
        jh, jt = V0.copy(), V0.copy()

    has_joint_offset = jh.magnitude
    has_tail_offset = jt.magnitude

    if has_joint_offset:
        d += jh
    else:
        d += util.toVector(master.get('offset'))

    if has_tail_offset:
        t += jt


    pmaster = get_master_bone(bones, parent)
    s = util.get_bone_scale(pmaster) if pmaster else V1.copy()
    dd = mulmat(d, M)
    sd = Vector([s[i]*dd[i] for i in range(3)])
    d  = mulmat(M, sd)

    s = util.get_bone_scale(master) if master else V1.copy()
    tt = mulmat(t, MT)
    st = Vector([s[i]*tt[i] for i in range(3)])
    tail = mulmat(MT, st)



    pos += d
    
    if dbone.name in ['Tinker','PelvisInv']:

        tt = tail.copy()
        pos += tail
        tail = -tt

    if use_cache:
        set_item_cache(dbone, 'cubr', [pos, tail])


    if absolute:
        pos = mulmat(armobj.world_matrix, pos)
        tail = mulmat(armobj.matrix_world, tail)

    return  pos, tail

def get_item_cache(item, key):
    cache = item.get('cache', None)
    if not cache:
        return None

    val = cache.get(key, None)
    return val

def set_item_cache(item, key, val):
    cache = item.get('cache', None)
    if cache == None:
        cache = {}

    cache[key] = val
    item['cache'] = cache

def reset_item_cache(item, full=False):
    util.remove_key(item, 'cache')
    if full:
        util.remove_key(item, 'fix_head')
        util.remove_key(item, 'fix_tail')

def reset_cache(armobj, subset=None, full=False):
    log_cache.debug("Reset %s Cache" % armobj.name)
    if subset == None:
        subset = util.get_modify_bones(armobj)
    for dbone in subset:
        reset_item_cache(dbone, full)
    reset_item_cache(armobj, full)







def store_restpose_mats(arm_obj):

    ebones = arm_obj.data.edit_bones
    for ebone in ebones:
        mat = ebone.matrix
        ebone['mat0'] = ebone.matrix.copy()

def restore_source_bone_rolls(armobj):
    omode = util.ensure_mode_is("EDIT")
    ebones = armobj.data.edit_bones
    bone_names = Skeleton.bones_in_hierarchical_order(armobj)

    for name in bone_names:
        ebone = ebones.get(name, None)
        if ebone:
            restore_reference_bone_roll(armobj, ebone)
    util.ensure_mode_is(omode)


def get_line_bone_names(pbones, selection):
    linebones = []
    for name in selection:
        posebone = pbones[name]
        if len([constraint for constraint in posebone.constraints if constraint.type == "STRETCH_TO"]) > 0:
            linebones.append(name)
            continue
    return linebones


def get_pole_bone_names(pbones, selection):
    polebones = []
    for name in selection:
        posebone = pbones[name]
        if len([constraint for constraint in posebone.constraints if constraint.type == "IK" and constraint.pole_target]) > 0:
            polebones.append(name)
    return polebones


def restore_reference_bone_roll(armobj, ebone):



    head, tail = get_sl_restposition(armobj, ebone, use_cache=True)
    hs = ebone.hide_select
    ebone.hide_select=False
    matrix = Matrix(ebone['mat0']).to_3x3()
    dv     = ebone.tail - ebone.head
    dq     = tail.rotation_difference(dv)
    matrix.rotate(dq)
    matrix = matrix.to_4x4()
    matrix.translation = ebone.head
    tail = ebone.tail.copy()
    ebone.matrix = matrix
    ebone.tail = tail
    ebone.hide_select=hs

armature_mode         = None
ik_edit_bones         = None

last_action = None
sync_timeline_enabled = True
@persistent
def sync_timeline_action(scene):
    from . import animation
    from . import propgroups

    if util.handler_can_run(scene, check_ticker=False):
        log.debug("handler [%s] started" % "sync_timeline_action")
    else:
        return

    context = bpy.context
    
    global sync_timeline_enabled
    if not sync_timeline_enabled:

        return


    active = util.get_active_object(context)
    if not ( active and active.type =='ARMATURE' and 'avastar' in active):

        return
    if not active.animation_data:
        return

    global last_action
    action = active.animation_data.action

    if not action:

        last_action = None
        return

    propgroups.set_update_scene_data(False)
    try:

        if action.AnimProp.frame_start == -2:


            fr = action.frame_range
            log.warning("Preset Action from Action Frame Range [%d -- %d]" % (fr[0], fr[1]))
            action.AnimProp.fps = scene.render.fps
            action.AnimProp.frame_start = fr[0]
            action.AnimProp.frame_end = fr[1]




        if scene.SceneProp.loc_timeline:
            if last_action != action:
                start = action.AnimProp.frame_start
                end = action.AnimProp.frame_end
                fps = action.AnimProp.fps
                log.warning("Preset Timeline from Action Frame Range [%d -- %d] fps:%d" % (start, end, fps))
                scene.frame_start = start
                scene.frame_end = end
                scene.render.fps = fps

            else:

                action.AnimProp.frame_start = scene.frame_start
                action.AnimProp.frame_end = scene.frame_end
                action.AnimProp.fps = scene.render.fps
        last_action = action

    finally:
        propgroups.set_update_scene_data(True)

@persistent
def check_dirty_armature_on_update(scene):

    if util.handler_can_run(scene, check_ticker=False):
        log.debug("handler [%s] started" % "check_dirty_armature_on_update")
    else:
        return

    context = bpy.context
    active = util.get_active_object(context)
    
    if not scene.SceneProp.panel_appearance_enabled:
        return 

    need_check = (active and active.type =='ARMATURE' and 'avastar' in active and util.is_in_user_mode())
    if not need_check:
        return

    mode_changed = util.context_or_mode_changed(active)

    if DIRTY_RIG in active:
        old_state = util.set_disable_handlers(scene, True)
        try:
            preferences = util.getAddonPreferences()
            enable_auto_rig_update = preferences.enable_auto_rig_update
            if enable_auto_rig_update:
                if mode_changed:
                    log.warning("Found dirty rig and mode change == %s" % mode_changed)
                if active.mode != 'EDIT' and mode_changed:
                    log.warning("Automatic adjust Slider data and reset DIRTY_RIG flag")
                    bpy.ops.avastar.armature_jointpos_store()
                if mode_changed:
                    log.warning("Finished dirty rig processing...")
        finally:
            util.set_disable_handlers(scene, old_state)
        return

    if active.mode=='EDIT':

        if active.get(DIRTY_RIG): # Armature is already flagged a dirty
            return

        ebones = active.data.edit_bones
        dbones = active.data.bones

        ebone = ebones.active
        if ebone:
            dbone = dbones.get(ebone.name)
            selection = [[ebone,dbone]]
        else:
            selection = [ [e, dbones.get(e.name)] for e in ebones if e.select]

        for ebone, dbone in selection:
            if not 'bone_roll' in ebone:
                ebone['bone_roll'] = ebone.roll

            if dbone == None:
                continue

            if ebone.head != dbone.head_local:
                active[DIRTY_RIG] = True
                log.warning("Dirty Bone %s:%s head mismatch" % (active.name, ebone.name) )
            if ebone.tail != dbone.tail_local:
                active[DIRTY_RIG] = True
                log.warning("Dirty Bone %s:%s tail mismatch" % (active.name, ebone.name) )
            if ebone.roll != ebone['bone_roll']:
                active[DIRTY_RIG] = True
                log.warning("Dirty Bone %s:%s roll mismatch" % (active.name, ebone.name) )

            if active.get(DIRTY_RIG): # No need to continue
                return

@persistent
def fix_linebones_on_update(scene):

    if util.handler_can_run(scene, check_ticker=False):
        log.debug("handler [%s] started" % "fix_linebones_on_update")
    else:
        return

    if util.get_shape_update_in_progres():
        return # no need to do anything
    try:
        armobj = bpy.context.object
    except:
        return # Nothing to do here

    global armature_mode
    global ik_edit_bones

    armobj = bpy.context.object
    need_update = False
    pbone       = None

    if armobj and armobj.type=='ARMATURE' and "avastar" in armobj:
        if armobj.mode == "EDIT":
            p = util.getAddonPreferences()
            if not p.auto_adjust_ik_targets:
                return

            if armature_mode == armobj.mode:

                pbone = bpy.context.active_bone
                if pbone is not None and pbone.name in IK_TARGET_BONES:
                    if ik_edit_bones == None:
                        ik_edit_bones = {}
                    if pbone.name in ik_edit_bones :
                        if pbone.head != ik_edit_bones[pbone.name][0] or pbone.tail != ik_edit_bones[pbone.name][1]:
                            need_update = True
                            ik_edit_bones[pbone.name] = [pbone.head.copy(), pbone.tail.copy()]
                    else:
                        need_update = True
                        ik_edit_bones[pbone.name] = [pbone.head.copy(), pbone.tail.copy()]
            else:

                armature_mode = armobj.mode
                need_update  = True
                ik_edit_bones = {}

        elif armobj.mode=="POSE":

            if armature_mode != armobj.mode:

                armature_mode = armobj.mode
                need_update   = True
        else:
            armature_mode = armobj.mode
    else:
        armature_mode = None

    if armature_mode !="EDIT" and ik_edit_bones: ik_edit_bones = None

    if need_update:
        old_disable_handlers = util.set_disable_handlers(scene, True)

        try:
            old_update_in_progres = util.set_shape_update_in_progres(True)
            selection = IK_LINE_BONES
            if armobj.mode == "EDIT":

                if pbone:
                    if pbone.name.endswith("TargetRight"): name=pbone.name[0:-11]
                    elif pbone.name.endswith("TargetLeft"): name=pbone.name[0:-10]
                    else:
                        return
                    selection = [name+"LineLeft", name+"LineRight"]

            elif armobj.mode == "POSE":
                if bpy.context.scene.MeshProp.adjustPoleAngle:


                    original_pose = armobj.data.pose_position
                    armobj.data.pose_position="REST"

                    for bonename in IK_POLE_BONES:

                        posebone = armobj.pose.bones[bonename] if bonename in armobj.pose.bones else None
                        if posebone and posebone.parent:
                            for constraint in posebone.constraints:
                                if constraint.type == "IK" and constraint.pole_target:

                                    fix_pole_angle(armobj, posebone, constraint)

                    armobj.data.pose_position=original_pose

            fix_stretch_to(armobj, selection)

        finally:
            util.set_shape_update_in_progres(old_update_in_progres)
            util.set_disable_handlers(scene, old_disable_handlers)
        return


def fix_stretch_to(armobj, selection=None):

    if armobj.mode != 'EDIT':
        return

    if not selection:
        selection = IK_LINE_BONES

    def reset_stretch(linebone, targetbone, con_stretchto, con_copyloc):
        muted = con_copyloc.mute
        con_copyloc.mute = True
        rest_length = (targetbone.head - linebone.head).magnitude
        con_stretchto.rest_length = rest_length
        con_copyloc.mute = muted

    def adjust_linebone(armobj, linebname, con_stretchto, con_copyloc):
        update_was_in_progres = util.set_shape_update_in_progres(True)
        try:
            line_bone   = armobj.data.edit_bones[linebname]
            pole_target = armobj.data.edit_bones[con_stretchto.subtarget]
            pole_source = armobj.data.edit_bones[con_copyloc.subtarget]
            line_bone.tail = pole_target.head
            line_bone.head = pole_source.head
        except:
            log.info("Can not fix %s Stretch To IK Target (Missing IK bones)" % linebname)
        finally:
            util.set_shape_update_in_progres(update_was_in_progres)

    omode = util.set_object_mode('EDIT')
    for linebname in selection:

        if linebname in armobj.pose.bones:
            linebone = armobj.pose.bones[linebname]
            con_stretchto = None
            con_copyloc = None

            for constraint in linebone.constraints:
                if not con_stretchto and constraint.type == "STRETCH_TO":
                    con_stretchto = constraint
                elif not con_copyloc and constraint.type == "COPY_LOCATION":
                    con_copyloc = constraint

            if con_stretchto and con_copyloc:
                log.debug("Fixing Stretch for bone %s in armature %s" % (linebone.name, armobj.name))
                adjust_linebone(armobj, linebname, con_stretchto, con_copyloc)
                linebone   = linebone.bone
                targetbone = armobj.data.bones[con_stretchto.subtarget]
                reset_stretch(linebone, targetbone, con_stretchto, con_copyloc)

    util.set_object_mode(omode)

def fix_pole_angles(armobj, selection):

    for bonename in selection:
        posebone = armobj.pose.bones[bonename]
        for constraint in posebone.constraints:
            if constraint.type == "IK":
                fix_pole_angle(armobj, posebone, constraint)

def fix_pole_angle(armobj, pbone, constraint):

    def signed_angle(vector_u, vector_v, normal):

        angle = vector_u.angle(vector_v)
        vc = vector_u.cross(vector_v)
        if vc.magnitude and vc.angle(normal) < 1:
            angle = -angle
        return angle

    def get_pole_angle(base_bone, ik_bone, pole_target):

        pole_location = pole_target.matrix.translation
        handle_tail = ik_bone.tail
        handle_head = ik_bone.head
        base_head = base_bone.head
        base_tail = base_bone.tail
        base_x_axis = base_bone.x_axis

        base_vector = base_tail-base_head

        pole_normal = (handle_tail-base_head).cross(pole_location - base_head)
        projected_pole_axis = pole_normal.cross(base_vector)
        return signed_angle(base_x_axis, projected_pole_axis, base_vector)

    if constraint.pole_target:
        pole_target = constraint.pole_target.pose.bones.get(constraint.pole_subtarget,None)
        if pole_target:
            influence = constraint.influence
            constraint.influence = 0
            util.update_depsgraph(bpy.context)

            constraint.pole_angle = get_pole_angle(
                pbone.parent,
                pbone,
                pole_target)

            constraint.influence = influence
            util.update_view_layer(bpy.context)

def fix_avastar_armature(context, armobj):
    log.debug("| fixing Avastar Armature %s" % armobj.name)
    scene=context.scene
    hidden = util.object_hide_get(armobj)
    util.object_hide_set(armobj, False)
    active_object = util.get_active_object(context)
    if active_object == None:
        return

    original_mode = active_object.mode
    util.set_active_object(context, armobj)

    original_armob_mode = util.ensure_mode_is('OBJECT')
    rig_version = armobj.get('avastar', 0)
    if rig_version < 4:
        log.warning("| Outdated rig version %d needs readjusting layers" % rig_version)
        boneset = data.get_reference_boneset(armobj)
        for bone in armobj.data.bones:
            BONE = boneset.get(bone.name)
            if BONE:
                bone.layers = [ii in BONE.bonelayers for ii in range(32)]

    if rig_version < 7:
        original_armob_mode = util.ensure_mode_is('EDIT')
        log.warning("| Outdated rig version %d needs building the joint data for rig %s" % (rig_version, armobj.name) )
        joint_dict = rebuild_joint_position_info(armobj, with_joint_tails=True)
        print("Added joints repository with %d entries to Armature %s" % (len(joint_dict), armobj.name) )
        util.ensure_mode_is('OBJECT')

    rigType = armobj.get('rigtype', None) #Old way to define the rigtype


    if rigType:
        armobj.RigProp.Rigtype = rigType
        del armobj['rigtype']

    util.ensure_mode_is('EDIT')
    bones = armobj.data.edit_bones
    pbones = armobj.pose.bones
    offset_count = 0
    
    for bone in bones:
        if not (bone.name[0:2]=='ik' or 'Link' in bone.name or bone.name=='Origin'):
            try:
                h, t = get_sl_bindposition(armobj, bone, use_cache=True)
                magnitude = (h - bone.head).magnitude
                if magnitude > MIN_BONE_LENGTH:
                    offset_count += 1
                    log.debug("| Bone %s is offset by %f from expected loc %s" % (bone.name, magnitude, h) )
            except:
                log.warning("| Could not check bone %s for having joint offset" % (bone.name))
        
        if bone.use_deform and not bone.layers[B_LAYER_DEFORM]:
            bone.layers[B_LAYER_DEFORM]=True

    if offset_count > 0:
        context.scene.UpdateRigProp.transferJoints = True
        armobj['offset_count'] = offset_count
    elif 'offset_count' in armobj:
        del armobj['offset_count']

    selection = Skeleton.bones_in_hierarchical_order(armobj)
    linebones = get_line_bone_names(pbones, selection)
    fix_stretch_to(armobj, linebones)

    util.ensure_mode_is(original_armob_mode)
    util.object_hide_set(armobj, hidden)
    util.set_active_object(context, active_object)
    util.ensure_mode_is(original_mode)
    
    adjustHandStructure(armobj)

def guess_pose_layers(armobj):
    layers = armobj.data.layers
    for pose_layer, deform_layers in DEFORM_TO_POSE_MAP.items():
        for layer in deform_layers:
            layers[pose_layer] = layers[pose_layer] or layers[layer]

    for pose_layer, deform_layers in DEFORM_TO_POSE_MAP.items():
        for dlayer in deform_layers:
            if dlayer != pose_layer:
                layers[dlayer] = False

def guess_deform_layers(armobj, replace=True):
    layers = armobj.data.layers
    at_least_one = False
    for pose_layer, deform_layers in DEFORM_TO_POSE_MAP.items():
        layers[deform_layers[0]] = layers[deform_layers[0]] or layers[pose_layer]
        at_least_one = at_least_one or layers[deform_layers[0]]

    if replace:
        for pose_layer, deform_layers in DEFORM_TO_POSE_MAP.items():
            if pose_layer != deform_layers[0]:
                layers[pose_layer] = False

    if not at_least_one:
        layers[B_LAYER_DEFORM] = True

def update_bone_roll(bones, template, substitutes, hip_compatibility):
    sign = -1
    for substitute in substitutes:
        bname = template % substitute
        dbone = bones.get(bname)
        sign *= -1
        if dbone:
           dbone.roll = sign * 5 * DEGREES_TO_RADIANS if hip_compatibility else 0
           log.warning("Set bone roll for %s to %s" % (dbone.name, dbone.roll) )

def update_hip_boneroll(context, armobj):
    bones = armobj.data.edit_bones
    update_bone_roll(bones, "Hip%s", ['Left','Right'], armobj.RigProp.hip_compatibility)
    update_bone_roll(bones, "%s_UPPER_LEG", ['L', 'R'], armobj.RigProp.hip_compatibility)
    update_bone_roll(bones, "a%s Hip", ['Left', 'Right'],armobj.RigProp.hip_compatibility)

class ResetSpineBones(bpy.types.Operator):
    bl_idname = "avastar.reset_spine_bones"
    bl_label = "Reset Spine"
    bl_description = "Reset the SPine bones to a neutral setup"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return True

    def execute(self, context):
        armobj = util.get_armature(context.object)
        has_changed = armatureSpineFold(armobj)
        if has_changed:
            bpy.ops.avastar.armature_jointpos_store()
        return{'FINISHED'}

def get_folding_state(armobj, spinea_name, spineb_name, boneset, unfolded):

    bones = armobj.data.bones
    mSpinea = bones.get(spinea_name) 
    mSpineb = bones.get(spineb_name)

    if mSpinea and mSpineb and mSpinea.use_deform==mSpineb.use_deform:
        action = "Disable" if unfolded else "Enable"
        alert = False
    else:
        action = "Reset"
        alert=True

    txt = '%s %s' % (action, boneset)
    return txt, alert


def get_upper_folding_state(armobj):
    return get_folding_state(armobj, 'mSpine3', 'mSpine4', "Upper", armobj.RigProp.spine_unfold_upper)


def get_lower_folding_state(armobj):
    return get_folding_state(armobj, 'mSpine1', 'mSpine2', "Lower", armobj.RigProp.spine_unfold_lower)


def update_spine_fold(context, armobj):
    with set_context(context, armobj, 'EDIT'):
        props = armobj.RigProp
        armatureSpineFold(armobj) # Make sure all spine bones are folded
        if props.spine_unfold_upper:
            armatureSpineUnfoldUpper(armobj)
        if props.spine_unfold_lower:
            armatureSpineUnfoldLower(armobj)


def update_spine_hide(context, armobj):
    props = armobj.RigProp
    armatureSpineHideLower(armobj, not props.spine_is_visible)
    armatureSpineHideUpper(armobj, not props.spine_is_visible)

def update_spine_folding(self, context):
    armobj = util.get_armature(context.object)
    if armobj:
        update_spine_fold(context, armobj)
        bpy.ops.avastar.armature_jointpos_store()

def update_spine_hiding(self, context):
    armobj = util.get_armature(context.object)
    if armobj:
        props = armobj.RigProp
        armobj.data.layers[B_LAYER_SPINE] = armobj.RigProp.spine_is_visible # Could go wrong if this leads to no layers active
        update_spine_hide(context, armobj)

def update_hip_compatibility(self, context):
    armobj = util.get_armature(context.object)
    if armobj:
        omode = util.ensure_mode_is('EDIT')
        update_hip_boneroll(context, armobj)
        util.ensure_mode_is(omode)

def update_eye_configuration(self, context):

    def set_bone_config(pose_bone, hide, bone_group=None, bone_layers=None):
        if pose_bone:
            pose_bone.bone.hide=hide
            if bone_group:
                pose_bone.bone_group = bone_group
            if bone_layers:
                pose_bone.bone.layers = [ii in bone_layers for ii in range(32)]

    active, armobj = getActiveArmature(context)
    if not armobj:
        return

    pbones = armobj.pose.bones
    bgroups= armobj.pose.bone_groups

    if self.eye_setup == 'BASIC':
        hides = SL_ALT_EYE_BONES
        shows = SL_EYE_BONES
    elif self.eye_setup == 'EXTENDED':
        hides = SL_EYE_BONES
        shows = SL_ALT_EYE_BONES
    else:
        hides = []
        shows = SL_EYE_BONES + SL_ALT_EYE_BONES

    for name in hides:
        set_bone_config(pbones.get(name), True, bone_layers=[B_LAYER_EXTRA, B_LAYER_DEFORM])
        set_bone_config(pbones.get(name[1:]), True, bone_group=bgroups.get('Face'), bone_layers=[B_LAYER_EXTRA])

    for name in shows:
        set_bone_config(pbones.get(name), False, bone_layers=[B_LAYER_DEFORM_FACE, B_LAYER_DEFORM] )
        set_bone_config(pbones.get(name[1:]), False, bone_group=bgroups.get('Eyes'), bone_layers=[B_LAYER_FACE])



def armatureSpineHideUpper(arm, hide):
    bones   = util.get_modify_bones(arm)
    set_bone_hide('Spine3', bones, hide)
    set_bone_hide('Spine4', bones, hide)

def armatureSpineHideLower(arm, hide):
    bones   = util.get_modify_bones(arm)
    set_bone_hide('Spine1', bones, hide)
    set_bone_hide('Spine2', bones, hide)

def set_bone_hide(bone_name, bones, hide):
    bone = bones.get(bone_name, None)
    if bone:
        bone.hide = hide


def armatureSpineUnfoldLower(arm):
    util.ensure_mode_is('EDIT')
    bones   = util.get_modify_bones(arm)

    cog     = bones.get('COG')
    torso   = bones.get('Torso')
    spine1  = bones.get('Spine1')
    spine2  = bones.get('Spine2')
    pelvisi = get_tinker_bone(bones)
    pelvis  = bones.get('Pelvis')

    mtorso  = bones.get('mTorso')
    mpelvis = bones.get('mPelvis')
    mspine1 = bones.get('mSpine1')
    mspine2 = bones.get('mSpine2')







    end     = Vector(mtorso.head)
    begin   = Vector(mpelvis.head)
    dv      = (end-begin)/3

    log.warning("armature spine unfold: lower begin: %s" % (begin) )
    log.warning("armature spine unfold: lower end  : %s" % (end) )









    has_changed = False
    if spine1 and spine2 and pelvis and torso:
        has_changed |= set_parent(torso, spine2)
        has_changed |= set_parent(spine2, spine1)
        has_changed |= set_parent(spine1, pelvis)

    if mspine1 and mspine2 and mpelvis and mtorso:
        has_changed |= set_parent(mtorso, mspine2)
        has_changed |= set_parent(mspine2, mspine1)
        has_changed |= set_parent(mspine1, mpelvis)

    has_changed |= set_loc(mspine2, end - dv, end)
    has_changed |= set_loc(mspine1, begin + dv, end-dv)
    has_changed |= set_loc(mpelvis, mpelvis.head, begin + dv)
 
    has_changed |= set_loc(spine2, mspine2.head, mspine2.tail)
    has_changed |= set_loc(spine1, mspine1.head, mspine1.tail)
    has_changed |= set_loc(pelvis, mpelvis.head, mpelvis.tail)

    if pelvisi:
        has_changed |= set_loc(pelvisi, pelvisi.head, begin)

    has_changed |= set_connect(mspine1, True)
    has_changed |= set_connect(mspine2, True)



    armatureSpineHideLower(arm, False)
    mspine1.use_deform = True
    mspine2.use_deform = True
    return has_changed


def reset_rig_to_restpose(armobj):
    omode = util.ensure_mode_is("POSE")
    layers = []
    for i,l in enumerate(armobj.data.layers):
        layers.append(l)
        armobj.data.layers[l]=True
    bpy.ops.pose.select_all(action='SELECT')
    armobj.data.layers = layers
    
def armatureSpineUnfoldUpper(arm):
    util.ensure_mode_is('EDIT')
    bones  = util.get_modify_bones(arm)

    mtorso  = bones.get('mTorso')
    mspine3 = bones.get('mSpine3')
    mspine4 = bones.get('mSpine4')
    mchest  = bones['mChest']
    has_changed = False

    if  mspine3.head != mtorso.tail or \
        mspine3.tail != mtorso.head or \
        mspine4.head != mspine3.tail or \
        mspine4.tail != mspine3.head:
        print("armatureSpineUnfold: Upper spine is already unfolded, nothing to do")
        return has_changed

 
    chest  = bones.get('Chest')
    spine3 = bones.get('Spine3')
    spine4 = bones.get('Spine4')
    torso  = bones.get('Torso')

    end   = Vector(mchest.head)
    begin = Vector(mtorso.head)
    dv    = (end-begin)/3

    log.warning("armature spine unfold: upper begin: %s" % (begin) )
    log.warning("armature spine unfold: upper end  : %s" % (end) )



    if chest and spine4 and spine3 and torso:
        has_changed |= set_parent(chest, spine4)
        has_changed |= set_parent(spine4, spine3)
        has_changed |= set_parent(spine3, torso)

    if mchest and mspine4 and mspine3 and mtorso:
        has_changed |= set_parent(mchest, mspine4)
        has_changed |= set_parent(mspine4, mspine3)
        has_changed |= set_parent(mspine3, mtorso)

    head = end - dv
    if mspine4.head != head:
        mspine4.head = head
        has_changed = True

    head = begin + dv
    if mspine3.head != head:
        mspine3.head = begin + dv
        has_changed = True

    has_changed |= set_loc(mspine4, end-dv, mchest.head)
    has_changed |= set_loc(mspine3, begin+dv, mspine4.head)
    has_changed |= set_loc(mtorso, mtorso.head, mspine3.head)

    has_changed |= set_loc(spine4, mspine4.head, mspine4.tail)
    has_changed |= set_loc(spine3, mspine3.head, mspine4.head)
    has_changed |= set_loc(torso, mtorso.head, mtorso.tail)
    
    if spine4 and spine3 and chest:
        has_changed |= set_connect(spine4, True)
        has_changed |= set_connect(spine3, True)
        has_changed |= set_connect(chest, True)




    armatureSpineHideUpper(arm, False)
    mspine3.use_deform = True
    mspine4.use_deform = True
    return has_changed


def armatureSpineFold(arm):

    omode = util.ensure_mode_is('EDIT')
    bones  = util.get_modify_bones(arm)

    mSpine4 = bones.get('mSpine4')
    mSpine3 = bones.get('mSpine3')
    mSpine2 = bones.get('mSpine2')
    mSpine1 = bones.get('mSpine1')
    mChest  = bones.get('mChest')
    mTorso  = bones.get('mTorso')
    mPelvis = bones.get('mPelvis')


    Spine4 = bones.get('Spine4')
    Spine3 = bones.get('Spine3')
    Spine2 = bones.get('Spine2')
    Spine1 = bones.get('Spine1')
    Chest   = bones.get('Chest')
    Torso   = bones.get('Torso')
    Pelvis  = bones.get('Pelvis')

    Tinker  = get_tinker_bone(bones)
    COG     = bones.get('COG')

    upper_end     = Vector(mChest.head)
    upper_begin   = Vector(mTorso.head)
    lower_end     = Vector(mTorso.head)
    lower_begin   = Vector(mPelvis.head)
    


    has_changed = False

    if Chest and Torso and COG:
        has_changed |= set_parent(Chest, Torso)
        has_changed |= set_parent(Torso, COG)
        has_changed |= set_parent(mChest, mTorso)
        has_changed |= set_parent(mTorso, mPelvis)



    has_changed |= set_loc(mChest, upper_end, Vector(mChest.tail))
    has_changed |= set_loc(mSpine4, upper_begin, upper_end)
    has_changed |= set_loc(mSpine3, upper_end, upper_begin)
    has_changed |= set_loc(mTorso, upper_begin, upper_end)
    has_changed |= set_loc(mSpine2, lower_begin, lower_end)
    has_changed |= set_loc(mSpine1, lower_end, lower_begin)
    has_changed |= set_loc(mPelvis, lower_begin, lower_end)

    if mSpine1 and mSpine2 and mSpine3 and mSpine4:
        mSpine1.use_deform = False
        mSpine2.use_deform = False
        mSpine3.use_deform = False
        mSpine4.use_deform = False

    has_changed |= set_loc(Chest, upper_end,  Vector(mChest.tail))
    has_changed |= set_loc(Spine4, upper_begin, upper_end)
    has_changed |= set_loc(Spine3, upper_end, upper_begin)
    has_changed |= set_loc(Torso, upper_begin, upper_end)
    has_changed |= set_loc(Spine2, lower_begin, lower_end)
    has_changed |= set_loc(Spine1, lower_end, lower_begin)
    has_changed |= set_loc(Pelvis, lower_begin, lower_end)
    has_changed |= set_loc(Tinker, lower_end, lower_begin)
    has_changed |= set_loc(COG, lower_end, None)

    armatureSpineHideUpper(arm, True)
    armatureSpineHideLower(arm, True)

    util.ensure_mode_is(omode)
    return has_changed

def set_parent(child, parent):
    if child.parent != parent:
        child.parent=parent
        parented=True
    else:
        parented = False
    return parented


def set_loc(bone, head, tail):
    relocated = False
    if bone:
        if tail and not head :
            head = bone.head + tail - bone.tail
        if head and not tail:
            tail = bone.tail + head - bone.head

        if tail and not util.is_at_same_location(tail, bone.tail, abs_tol=0.000001):
            bone.tail = tail.copy()
            relocated=True
        if head and not util.is_at_same_location(head, bone.head, abs_tol=0.000001):
            bone.head = head.copy()
            relocated=True
    else:
        relocated = False
    return relocated



def deform_display_reset(arm):
    util. remove_key(arm, 'filter_deform_bones')
    util. remove_key(arm, 'rig_display_type')
    util. remove_key(arm, 'rig_display_mesh')
    util. remove_key(arm, 'rig_display_mesh_count')

def deform_display_changed(context, arm, objs):
    changed = set()
    if arm.ObjectProp.filter_deform_bones != arm.get('filter_deform_bones'):
        arm['filter_deform_bones'] = arm.ObjectProp.filter_deform_bones
        changed.add("Filter")
    if arm.ObjectProp.rig_display_type != arm.get('rig_display_type'):
        arm['rig_display_type'] = arm.ObjectProp.rig_display_type
        changed.add("Displaytype")

    active_object = util.get_active_object(context)
    if active_object:
        obname = active_object.name
        if arm.get('rig_display_mesh') != obname:
            arm['rig_display_mesh'] = obname
            changed.add(obname)

    if arm.get('rig_display_mesh_count', -1) != len(objs):
        arm['rig_display_mesh_count'] = len(objs)
        changed.add("Meshcount:%d" % len(objs))

    return changed

def get_max_bone_count(scene, meshes):
    max_bone_count = 0
    for meshobj in meshes:
        armobj = util.get_armature(meshobj)
        bone_count = get_bone_count(meshobj, armobj)
        if bone_count > max_bone_count:
            max_bone_count = bone_count
    return max_bone_count

def get_bone_count(meshobj, armobj):
    bones = armobj.data.bones
    return len([v for v in meshobj.vertex_groups if v.name in bones and bones[v.name].use_deform])

def need_rebinding(armobj, meshes):
    to_fix=[]
    for ob in meshes:
        object_rev = ob.get('version', 0)
        checksum = ob.get(CHECKSUM)
        if object_rev < 20420 or DIRTY_MESH in ob:
            if checksum != util.calc_object_checksum(ob):
                to_fix.append(ob)
                continue

            if checksum != util.calc_object_checksum(ob):
                to_fix.append(ob)
        elif not util.is_child_of(armobj, ob):
            to_fix.append(ob)

    return to_fix


def check_bone_hierarchy(armobj, use_strict=False):
    report = []
    if not armobj:
        return report, 0, 0

    def is_child_of(child, parent, Bones):
        Child = Bones.get(child.name)
        Parent = Bones.get(parent.name)
        while Child and Child.blname in Bones and Child.blname != Parent.blname:
            Child = Child.parent
        status = Child != None and Child.blname == Parent.blname

        if not status:
            status =  (child.name == 'Torso' and parent.name == 'Spine2')

        return status


    def is_sl_bone(name, Bones):
        bone = Bones.get(name)
        if(not bone):
            return False
        if name[0] not in "ma" and bone.parent:
            name = bone.parent.blname # (possibly a Volume Bone, then parent is an mBone)
        return name[0] in ["m","a"] # mBone or attachment bone


    def accepted_parent(rig_child, ref_child, strict=True):
        accepted = rig_child.parent.name == ref_child.parent.blname
        if not accepted:
            if strict:
                return accepted

            if (rig_child.name == 'Chest' and rig_child.parent.name =='Torso') \
            or (rig_child.name == 'Torso' and rig_child.parent.name in ['Tinker','PelvisInv']) \
            or (rig_child.name == 'mChest' and rig_child.parent.name =='mTorso') \
            or (rig_child.name == 'mTorso' and rig_child.parent.name =='mPelvis'):
                accepted = True

        return accepted


    def has_valid_hierarchy(rig_parent, rig_bones, Bones, report):

        error_count = 0
        info_count = 0

        for rig_child in rig_parent.children:

            if is_sl_bone(rig_child.name, Bones):
                if not is_sl_bone(rig_parent.name, Bones) and rig_parent.name != 'Origin':
                    icon = ICON_ERROR
                    error_count += 1
                    report.append([icon, "%s has undefined parent %s" % (rig_child.name, rig_parent.name)] )
                    continue

                ref_child = Bones.get(rig_child.name)

                if not accepted_parent(rig_child, ref_child, strict=False):
                    icon = ICON_ERROR
                    error_count += 1
                    report.append([icon, "%s parented to %s" % (rig_child.name, rig_parent.name)] )

            dummy, ecount, icount = has_valid_hierarchy(rig_child, rig_bones, Bones, report)
            error_count += ecount
            info_count += icount

        return report, error_count, info_count


    def has_strict_hierarchy(rig_parent, Bones, report):

        error_count = 0
        info_count = 0

        for rig_child in rig_parent.children:
            ref_child = Bones.get(rig_child.name)
            if not ref_child:
                icon = ICON_ERROR
                error_count += 1
                report.append([icon, "%s not %s" % (rig_child.name, armobj.RigProp.RigType)] )
            elif not accepted_parent(rig_child, ref_child):
                icon = ICON_ERROR
                error_count += 1
                report.append([icon, "%s parented to %s" % (rig_child.name, rig_parent.name)] )

            dummy, ecount, icount = has_strict_hierarchy(rig_child, Bones, report)
            error_count += ecount
            info_count += icount

        return report, error_count, info_count

    Bones = data.get_reference_boneset(armobj)
    rig_bones = armobj.data.bones
    roots = [b for b in rig_bones if b.parent == None and b.name in Bones]
    error_count = 0
    info_count = 0
    if not roots:
        report.append ([None,"Not an SL Rig"])
        error_count += 1
    else:
        for root in roots:
            if root.name in Bones:
                if use_strict:
                    dummy, ecount, icount = has_strict_hierarchy(root, Bones, report)
                else:
                    dummy, ecount, icount = has_valid_hierarchy(root, rig_bones, Bones, report)
                error_count += ecount
                info_count += icount

    return report, error_count, info_count

class AvastarCheckHierarchy(Operator):
    bl_idname = "avastar.check_hierarchy"
    bl_label = "Check hierarchy"
    bl_description = "Check for SL compatible hierarchy\n\n"\
                   + "Hint: You find the check result in the\n"\
                   + "Operator Redo Panel (bottom of Tool Shelf)"
    bl_options = {'REGISTER', 'UNDO'}

    messages = []

    @staticmethod
    def draw_boneset(self, context, layout):

        def create_interface(col, skeletonProp, txt, icon):
            if icon:
                col.label(text=txt, icon=icon )
            else:
                col.label(text=txt)


        col   = layout.column()
        armobj = context.object

        skeletonProp = context.scene.SkeletonProp
        messages, error_count, info_count = check_bone_hierarchy(armobj)

        if len(messages) == 0:
            txt = "Has valid SL Hierarchy"
            create_interface (col, skeletonProp, txt, None)
        else:




            for val in messages:
                icon, msg = val
                if icon:
                    col.label(text=msg, icon=icon)
                else:
                    col.label(text=msg)

    @classmethod
    def poll(self, context):
        armobj = context.object
        if not armobj:
            return False
        return armobj.type == 'ARMATURE'

    def execute(self, context):
        armobj = context.object
        self.messages, error_count, info_count = check_bone_hierarchy(armobj)
        return {'FINISHED'}
        
class AvastarAdjustArmatureOrigin(Operator):
    bl_idname = "avastar.adjust_armature_origin"
    bl_label = "Adjust Origin"
    bl_description = "Quick fix: Adjust Root Bone position to Armature Origin"
    bl_options = {'REGISTER', 'UNDO'}
    
    adjust_origin : EnumProperty(
        items=(
            ('ROOT_TO_ORIGIN',   'Armature', UpdateRigProp_adjust_origin_armature),
            ('ORIGIN_TO_ROOT',   'Rootbone', UpdateRigProp_adjust_origin_rootbone)
        ),
        name="Origin",
        description=UpdateRigProp_adjust_origin,
        default='ORIGIN_TO_ROOT'
    )

    @classmethod
    def poll(self, context):
        armobj = context.object
        if not armobj:
            return False
        return armobj.type == 'ARMATURE'

    def execute(self, context):
        armobj = context.object

        if self.adjust_origin == 'ORIGIN_TO_ROOT':
            util.transform_origin_to_rootbone(context, armobj)
            log.warning("| Transformed Origin to Root Bone in source Armature [%s]" % armobj.name)
        else:
            util.transform_rootbone_to_origin(context, armobj)
            log.warning("| Transformed Root Bone to Origin in source Armature [%s]" % armobj.name)

        return {'FINISHED'}

classes = (
    AvastarFaceWeightGenerator,
    AvastarFromManuelLab,
    AvastarMergeWeights,
    FocusOnBone,
    DrawOffsets,
    AVASTAR_MT_armature_presets_menu,
    AvastarAddPresetArmature,
    AvastarUpdatePresetArmature,
    AvastarRemovePresetArmature,
    ResetSpineBones,
    AvastarCheckHierarchy,
    AvastarAdjustArmatureOrigin,
    ButtonEnableIK,
    ButtonApplyIK
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered rig:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered rig:%s" % cls)
