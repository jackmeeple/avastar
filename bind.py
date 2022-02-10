### Copyright 2015, Gaia Clary
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
import bpy, bmesh, sys
import logging, gettext, os, time, re, shutil
import addon_utils

from . import armature_util, const, create, data, mesh, messages, rig, shape, util, weights
from .const import *
from bpy.props import *
from bl_operators.presets import AddPresetBase
from bpy.types import Menu, Operator
from mathutils import Matrix

log = logging.getLogger('avastar.bind')
registerlog = logging.getLogger("avastar.register")

def get_basis_pose_from_armature(arm):
    dict = {}
    bones = arm.pose.bones
    for bone in bones:
        dict[bone.name] = bone.matrix_basis.copy()
    return dict

def read_basis_pose_from_textblock(bindname):
    text = bpy.data.texts[bindname]
    txt = text.as_string()
    dict = eval(txt)
    return dict

def set_bindpose_matrix(arm):
    dict = read_basis_pose_from_textblock(arm['bindpose'])
    bones = arm.pose.bones
    rig.set_bone_rotation_limit_state(arm, False, all=True)
    for bone in bones:
        name=bone.name
        mat = dict[name]
        bone.matrix_basis = mat

def set_invbindpose_matrix(arm):
    dict = read_basis_pose_from_textblock(arm['bindpose'])
    bones = arm.pose.bones
    rig.set_bone_rotation_limit_state(arm, False, all=True)
    for bone in bones:
        name=bone.name
        mat = dict[name]
        bone.matrix_basis = mat.inverted()

def write_basis_pose_to_textblock(arm, bindname):
    rig.set_bone_rotation_limit_state(arm, False, all=True)
    dict = get_basis_pose_from_armature(arm)
    if bindname in bpy.data.texts:
        text = bpy.data.texts[bindname]
        util.remove_text(text, do_unlink=True)
    text = bpy.data.texts.new(bindname)
    text.write(str(dict))
    arm['bindpose']=text.name
        
class AvastarStoreBindData(bpy.types.Operator):
    bl_idname      = "avastar.store_bind_data"
    bl_label       = "Set Bind Pose"
    bl_description = '''Apply Current Pose as Restpose.
This is only used to bind an object to a different pose!

Warning:  Meshes already bound to the Armature 
will revert to T-Pose. Also the appearence sliders
will be disabled!'''

    @classmethod
    def poll(self, context):
        obj=context.object
        if obj != None:
            arm = util.get_armature(obj)
            return arm != None
        return False

    def execute(self, context):
        obj=context.object
        arm = util.get_armature(obj)
        bindname = "posemats_%s" % arm.name
        write_basis_pose_to_textblock(arm, bindname)
        omode = None

        if obj != arm:
            omode = util.ensure_mode_is('OBJECT')
            active = context.active_object
            util.set_active_object(context, arm)

        amode = util.ensure_mode_is('POSE')
        bpy.ops.pose.armature_apply()
        util.ensure_mode_is(amode)
        
        if obj != arm:
            util.set_active_object(context, active)
            util.ensure_mode_is(omode)
        
        return{'FINISHED'}
     
    
class AvastarDisplayInRestpose(bpy.types.Operator):
    bl_idname      = "avastar.display_in_restpose"
    bl_label       = "Display Default Pose"
    bl_description = "Set Armature Pose to the default Avastar Pose for inspection\nNote: This operation neither changes the armature nor the object"

    @classmethod
    def poll(self, context):
        obj=context.object
        if obj != None:
            arm = util.get_armature(obj)
            if arm:
                return 'bindpose' in arm
        return False

    def execute(self, context):

        obj=context.object
        arm = util.get_armature(obj)
        set_invbindpose_matrix(arm)
        omode = None
        if obj != arm:
            omode = util.ensure_mode_is('OBJECT')
            active = context.active_object
            util.set_active_object(context, arm)
        if obj != arm:
            util.set_active_object(context, active)
            util.ensure_mode_is(omode)
        return{'FINISHED'}

class AvastarCleanupBinding(bpy.types.Operator):
    bl_idname      = "avastar.cleanup_binding"
    bl_label       = "Cleanup Binding Data"
    bl_description = "Generate Joint offsets from current binding\n\nNote:\nThis operation replaces the bind data by a list of Joint Offsets.\nThis is for now the preferred way to go until we have true bind pose support!"

    @classmethod
    def poll(self, context):
        obj=context.object
        if obj != None:
            arm = util.get_armature(obj)
            if arm:
                return 'bindpose' in arm
        return False

    def execute(self, context):
        armobj = util.get_armature(context.active_object)
        cleanup_binding(context, armobj)
        return{'FINISHED'}

class AvastarAlterToRestpose(bpy.types.Operator):
    bl_idname      = "avastar.alter_to_restpose"
    bl_label       = "Alter to Default Pose"
    bl_description = "Reset Armature back to the default Avastar Pose\nAfter Reverting the Avatar shape will be back in operation"
    
    @classmethod
    def poll(self, context):
        obj=context.object
        if obj != None:
            arm = util.get_armature(obj)
            if arm:
                return 'bindpose' in arm
        return False

    def execute(self, context):
        active      = context.active_object
        active_mode = util.ensure_mode_is('OBJECT')
        

        obj = context.object
        arm = util.get_armature(obj)
        set_invbindpose_matrix(arm)
        omode = None

        meshes = util.getCustomChildren(arm, type='MESH') if obj==arm else [obj]
        
        for obj in meshes:
            util.apply_armature_modifiers(context, obj, preserve_volume=True)

        util.set_active_object(context, arm)
        amode = util.ensure_mode_is('POSE')
        bpy.ops.pose.armature_apply()
        util.ensure_mode_is(amode)
        
        for obj in meshes:
            mod = create_armature_modifier(obj, arm, name=arm.name, preserve_volume=True)

        set_bindpose_matrix(arm)
        arm['export_pose'] = arm['bindpose']
        del arm['bindpose']



        
        util.set_active_object(context, active)
        util.ensure_mode_is(active_mode)
        
        return{'FINISHED'}

def add_bind_preset(context, filepath):
    arm    = util.get_armature(context.object)
    pbones = arm.pose.bones

    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "import avastar\n"
    "from avastar import shape, util, bind\n"
    "from mathutils import Vector, Matrix\n"
    "\n"
    "arm    = util.get_armature(bpy.context.object)\n"
    "\n"
    )
    dict = get_basis_pose_from_armature(arm)
    file_preset.write("dict=" + str(dict) + "\n\n")
    file_preset.write(
    "bones = arm.pose.bones\n"
    "for bone in bones:\n"
    "    name=bone.name\n"
    "    mat = dict[name]\n"
    "    bone.matrix_basis = mat.inverted()\n"
    "\n"
    )

    file_preset.close()


class AVASTAR_MT_bind_presets_menu(Menu):
    bl_label  = "Bind Presets"
    bl_description = "Bind Presets for the Avastar Rig"
    preset_subdir = os.path.join("avastar","bindings")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class AvastarAddPresetBind(AddPresetBase, Operator):
    bl_idname = "avastar.bind_presets_add"
    bl_label = "Add Bind Preset"
    bl_description = "Create new Preset from current Slider settings"
    preset_menu = "AVASTAR_MT_bind_presets_menu"

    preset_subdir = os.path.join("avastar","bindings")

    def invoke(self, context, event):
        log.info("Create new Bind Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_bind_preset(context, filepath)

class AvastarUpdatePresetBind(AddPresetBase, Operator):
    bl_idname = "avastar.bind_presets_update"
    bl_label = "Update Bind Preset"
    bl_description = "Store current Slider settings in last selected Preset"
    preset_menu = "AVASTAR_MT_bind_presets_menu"
    preset_subdir = os.path.join("avastar","bindings")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_bind_presets_menu.bl_label
        log.info("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_bind_preset(context, filepath)

class AvastarRemovePresetBind(AddPresetBase, Operator):
    bl_idname = "avastar.bind_presets_remove"
    bl_label = "Remove Bind Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_bind_presets_menu"
    preset_subdir = os.path.join("avastar","bindings")

def cleanup_binding(context, armobj, sync=True, with_ik_bones=False, with_joint_tails=True, delete_only=False, only_meta=False):
    if not armobj:
        return
    active = util.get_active_object(context)
    amode = util.ensure_mode_is('OBJECT')

    util.set_active_object(context, armobj)
    omode=util.ensure_mode_is('EDIT')

    bindname = armobj.get('bindpose', None)
    if bindname:
        del armobj['bindpose']
        text = bpy.data.texts.get(bindname)
        if text:
            util.remove_text(text, do_unlink=True)

    result = ArmatureJointPosStore.exec_imp(
             context, 
             delete_only=delete_only, 
             with_ik_bones=with_ik_bones, 
             with_joint_tails=with_joint_tails,
             snap_control_to_rig=True,
             only_meta=only_meta)

    util.ensure_mode_is('POSE')
    util.ensure_mode_is(omode)

    util.set_active_object(context, active)
    util.ensure_mode_is(amode)

def remove_binding(context, armobj, sync=True):
    if not armobj:
        return
    active = util.get_active_object(context)
    active_mode = util.ensure_mode_is('OBJECT')

    util.set_active_object(context, armobj)
    omode=util.ensure_mode_is('EDIT')

    bindname = armobj.get('bindpose', None)
    if bindname:
        del armobj['bindpose']
        text = bpy.data.texts.get(bindname)
        if text:
            util.remove_text(text, do_unlink=True)

    log.info("remove_binding from %s %s" % (armobj.type, armobj.name) )
    result = ArmatureJointPosRemove.exec_imp(
                context, 
                keep_edit_joints=True, 
                affect_all_joints=True
             )

    util.ensure_mode_is('POSE')
    util.ensure_mode_is(omode)

    util.set_active_object(context, active)
    util.ensure_mode_is(active_mode)


class ArmatureJointPosStore(bpy.types.Operator):
    bl_idname = "avastar.armature_jointpos_store"
    bl_label = "Store Joint Edits"
    bl_description = avastar_apply_as_restpose_text

    bl_options = {'REGISTER', 'UNDO'}

    sync : BoolProperty(
           name        = "Sync",
           description = "Synchronise Animartion bones and deform Bones",
           default     = False
           )

    delete_only : BoolProperty(
           name        = "Only Remove",
           description = "Only remove Joints\n(Only for debugging, Normally not needed)",
           default     = False
           )
           
    only_meta : BoolProperty(
           name        = "Only Meta",
           description = "Only create Metadata\n(Only for debugging, Normally not needed)",
           default     = False
           )
           
    vanilla_rig :  BoolProperty(
           name        = "Vanilla Rig",
           description = "Reset Rig Metadata\n(Only use when nothing else helps)",
           default     = False
           )

    snap_control_to_rig : const.g_snap_control_to_rig
    store_as_bind_pose : const.g_store_as_bind_pose

    def draw(self, context):
        layout = self.layout
        ob = context.object
        armobj = util.get_armature(ob)
        scn = context.scene

        col = layout.column()
        col.prop(self, "snap_control_to_rig")
        col.prop(armobj.RigProp, "generate_joint_tails")
        col.prop(armobj.RigProp, "generate_joint_ik")
        col.prop(self,"vanilla_rig")

        box = layout.box()
        box.label(text="Debugging options")
        col = box.column()
        col.prop(self, "sync")
        col.prop(self, "only_meta")
        col.prop(self, "delete_only")
        
    @staticmethod
    def exec_imp(context, 
                 delete_only=False, 
                 with_ik_bones=False, 
                 with_joint_tails=True,
                 only_meta=False,
                 vanilla_rig=False,
                 snap_control_to_rig=False,
                 store_as_bind_pose=None):





        oumode = util.set_operate_in_user_mode(False)
        try:
            util.set_use_bind_pose_update_in_progress(True)
            obj = context.object
            armobj = util.get_armature(obj)
            eye_target_states = util.disable_eye_targets(armobj)
            active = util.get_active_object(context)
            amode = omode = None

            if active != armobj:
                amode = util.ensure_mode_is("OBJECT")
                util.set_active_object(context, armobj)
            if armobj.mode != 'EDIT':
                omode = util.ensure_mode_is("EDIT")

            use_mirror_x = armobj.data.use_mirror_x
            armobj.data.use_mirror_x = False
            ArmatureJointPosRemove.exec_imp(context, keep_edit_joints=True, affect_all_joints=True)
            reset_dirty_flag(armobj)
            if vanilla_rig: #False
                create.reset_rig(armobj)

            rig.autosnap_bones(armobj, snap_control_to_rig)
            if not delete_only: #not False

                if store_as_bind_pose != None:
                    armobj.RigProp.rig_use_bind_pose = store_as_bind_pose

                rig.rebuild_joint_position_info(armobj, with_joint_tails)
                reset_dirty_flag(armobj, cleanup=True)
                armobj.update_from_editmode()

                if not only_meta:
                    shape.refreshAvastarShape(context, refresh=True, target="")

                armobj.data.use_mirror_x = use_mirror_x
                reconfigure_rig_display(context, armobj, [obj])
                armobj.update_from_editmode()

            util.enable_eye_targets(armobj, eye_target_states)
            armobj.update_from_editmode()

            if omode:
                util.ensure_mode_is(omode)
            if amode:
                util.set_active_object(context, active)
                util.ensure_mode_is(amode)

        except Exception as e:
            util.ErrorDialog.exception(e)
        finally:
            util.set_use_bind_pose_update_in_progress(False)
            util.set_operate_in_user_mode(oumode)
        return {'FINISHED'}

    def execute(self, context):
        obj     = context.object
        armobj = util.get_armature(obj)
        result = ArmatureJointPosStore.exec_imp(
                     context,
                     delete_only=self.delete_only,
                     with_ik_bones=armobj.RigProp.generate_joint_ik,
                     with_joint_tails=armobj.RigProp.generate_joint_tails,
                     only_meta=self.only_meta,
                     vanilla_rig=self.vanilla_rig,
                     snap_control_to_rig=self.snap_control_to_rig,
                     store_as_bind_pose=self.store_as_bind_pose
                     )
        return result
        
def reset_dirty_flag(armobj, cleanup=False):
    was_dirty = DIRTY_RIG in armobj

    if was_dirty:
        del armobj[DIRTY_RIG]

    if was_dirty or cleanup:
        bones = util.get_modify_bones(armobj)
        for b in [b for b in bones if 'bone_roll' in b]:
            del b['bone_roll']

    return was_dirty

class ArmatureJointPosRemove(bpy.types.Operator):
    bl_idname = "avastar.armature_jointpos_remove"
    bl_label = "Remove Joint Edits"
    bl_description = "Remove Joint Offset\n\nThe Bone Joint Data is deleted and the bone is moved back to its default location"
    bl_options = {'REGISTER', 'UNDO'}

    joint : StringProperty(default="")

    @staticmethod
    def exec_imp(context, keep_edit_joints, affect_all_joints):
        oumode = util.set_operate_in_user_mode(False)
        was_dirty = False
        obj     = context.object
        armobj = util.get_armature(obj)

        try:
            log.info("Remove Joint Positions from armature [%s]" % armobj.name)

            if armobj != obj:
                omode = util.ensure_mode_is("OBJECT")
                util.set_active_object(context, armobj)
            amode = util.ensure_mode_is("OBJECT")

            use_mirror_x = armobj.data.use_mirror_x
            armobj.data.use_mirror_x = False


            log.info("%s edited joint locations" % "Keept" if keep_edit_joints else "Removed")
            delete_joint_info = not keep_edit_joints
            all = affect_all_joints
            log.info("%s Joints are affected" % ("All" if all else "Only selected") ) 

            util.ensure_mode_is("EDIT")
            rig.del_offset_from_sl_armature(context, armobj, delete_joint_info, all=all)
            shape.update_tail_info(context, armobj, remove=affect_all_joints)

            if not context.scene.SceneProp.panel_appearance_enabled:
                shape.destroy_shape_info(context, armobj)

            if delete_joint_info:
                shape.refreshAvastarShape(context)
            armobj.data.use_mirror_x = use_mirror_x
            armobj.update_from_editmode()
            util.ensure_mode_is(amode)
            if armobj != obj:
                util.set_active_object(context, obj)
                util.ensure_mode_is(omode)

            reset_dirty_flag(armobj, cleanup=True)

            reconfigure_rig_display(context, armobj, [obj])
        except Exception as e:
            util.ErrorDialog.exception(e)
        finally:
            util.set_operate_in_user_mode(oumode)
            if keep_edit_joints:
                armobj[DIRTY_RIG] = True

    def execute(self, context):
        affect_all_joints = True #context.object.RigProp.affect_all_joints
        keep_edit_joints = context.object.RigProp.keep_edit_joints
        ArmatureJointPosRemove.exec_imp(context, keep_edit_joints, affect_all_joints)
        return{'FINISHED'}


def configure_edge_display(props, context):
    obj = context.object
    if not obj: return
    arm = util.get_armature(obj)

    obj.show_wire      = obj.ObjectProp.edge_display
    obj.show_all_edges = obj.ObjectProp.edge_display

def reconfigure_rig_display(context, arm, objs, verbose=True, force=False):
    rig_sections = [B_EXTENDED_LAYER_ALL]
    excludes = []
    if force or arm.ObjectProp.filter_deform_bones==False:
        final_set = bone_set = data.get_deform_bones(arm, rig_sections, excludes)

        type = 'DEFORM'
    else:
        type = arm.ObjectProp.rig_display_type
        for e in range(0,32):
                arm.data.layers[e] = e==B_LAYER_DEFORM

        final_set = set()
        if type == 'VOL':
            final_set = bone_set = data.get_volume_bones(arm, only_deforming=True)
        elif type == 'SL':
            final_set = bone_set = data.get_base_bones(arm, only_deforming=True)
        elif type == 'EXT':
            final_set = bone_set = data.get_extended_bones(arm, only_deforming=True)
        elif type == 'POS':


            final_set = bone_set  = rig.get_bone_names_with_jointpos(arm)
        elif type == 'MAP':
            bone_set = data.get_deform_bones(arm, rig_sections, excludes)

            for obj in [o for o in objs if o.type=='MESH']:
                final_set = get_binding_bones(context, obj, bone_set)

            final_set = list(final_set)
        else:
            final_set = bone_set = data.get_deform_bones(arm, rig_sections, excludes)

    log.debug("configure_rig_display for %d %s bones" % (len(bone_set), type) )

    weights.setDeformingBoneLayer(arm, final_set, bone_set, context)


def get_binding_bones(context, obj, bone_set):
    binding_bones = set()

    if obj.type == 'ARMATURE':
        objs = util.get_animated_meshes(context, obj)
        for ob in objs:
            binding_bones = binding_bones | get_binding_bones(context, ob, bone_set)
    else:
        armobj = util.get_armature(obj)
        vgroups = obj.vertex_groups
        for g in vgroups:
            if g.name in bone_set:
                binding_bones.add(g.name)



    return binding_bones


def configure_rig_display(props, context):
    obj = context.object
    if obj:
        arm = util.get_armature(obj)
        if arm:
            rig.deform_display_reset(arm)
            objs = util.get_animated_meshes(context, arm, with_avastar=True, only_selected=True)
            arm['rig_display_type_set'] = ''
            reconfigure_rig_display(context, arm, objs)





last_armobj = None
def fix_bone_layers(context, scene, lazy=True, force=False):
    global last_armobj

    if context is None:
         return
    if scene is None:
        scene = context.scene

    scene.ticker.tick
    if lazy and not scene.ticker.fire:
        return

    active_object = util.get_active_object(context)
    if not active_object:
        return

    try:
        arm = util.get_armature(active_object)
        if arm and 'avastar' in arm:

            adt = armature_util.get_display_type(arm)
            dt  = arm.RigProp.display_type
            if adt in ['OCTAHEDRAL','STICK']:
                if len(dt) == 0 or next(iter(dt)) != adt:
                    arm.RigProp.display_type = set([adt])
            elif len(dt) > 0:
                arm.RigProp.display_type = set()

            objs = util.get_animated_meshes(context, arm, with_avastar=True, only_selected=active_object!=arm)
            display_changed = rig.deform_display_changed(context, arm, objs)
            armobj_changed = last_armobj != arm
            if display_changed or armobj_changed:
                last_armobj = arm
                log.info("display changed :%s" % display_changed )
                log.info("armature changed:%s" % armobj_changed )
                reconfigure_rig_display(context, arm, objs, verbose=True, force=force)

    except:
        print("Force fixing bone layers failed...")
        raise





def bindpose_to_restpose(context, obj):
    armobj = obj.find_armature()
    util.set_active_object(context, armobj)
    convert_bindinfo_to_shape(armobj)
    to_restpose(obj)


def to_restpose(child, SKELETON=None):
    arm = child.find_armature()
    if not arm:
        return
    bones = util.get_modify_bones(arm)
    weightmaps, weighted_verts = shape.get_weight_groups(bones, child)
    if weightmaps:
        co = util.fast_get_verts(child.data.vertices)
        precos = shape.precalc_vertex_data(child, co)
        coflen = len(co)
        fco = co.copy()

        if SKELETON == None:
            SKELETON = data.getSkeletonDefinition('EXTENDED', 'PIVOT')






        for bname, weights in weightmaps.values():
            if weights:
                calculate_shape_delta(arm, child, bname, weights, fco, precos, SKELETON)

    util.fast_set_verts(child.data, fco)

def calculate_shape_delta(armobj, child, bname, weights, fco, precos, SKELETON):

    bone = armobj.pose.bones.get(bname)
    dbone = bone.bone

    MRest = get_reference_matrix_data(dbone)
    MBind = get_bind_matrix_data(dbone, SKELETON)
    
    coflen = len(fco)

    verts = child.data.vertices
    for index, weight in weights:
        vert = verts[index]
        dco_index = shape.get_dco_index(index, coflen, child)
        if dco_index == None:
            continue
        vert_local_co = vert.co
        if vert_local_co and weight:

            R = MRest @ MBind.inverted()
            shape_local_co = R @ vert_local_co
            DL = weight * (shape_local_co - vert_local_co)
            shape.update_shape_delta(dco_index, fco, DL)




    return


def get_bind_matrix_data(dbone, SKELETON):

    MBind = Matrix(dbone.get('BIND_MAT'))

    if dbone.name in SLVOLBONES:
        scalep = Matrix(dbone.parent.get('BIND_MAT')).to_scale()
    else:
        scalep = Matrix(dbone.parent.get('BIND_MAT')).to_scale() if dbone.parent else V1

    scaleb = MBind.to_scale()
    scale0 = data.s2bo(SKELETON[dbone.name].scale0)
    scale = Vector([a/(p*b) for p,a,b in zip(scalep, scaleb, scale0)])

    util.matrixScale(scale, M=MBind, replace=True)

    return MBind


def get_reference_matrix_data(dbone):
    MRest = Matrix(dbone.get('REST_MAT'))
    return MRest


def convert_restmat_recursive(matname, bone, pmat, sum_up):
    M = convert_mat_from_array(matname, bone, pmat, sum_up)
    bone[matname.upper()] = M
    for child in bone.children:
        convert_restmat_recursive(matname, child, M, sum_up)


def convert_mat_from_array(matname, bone, pmat, sum_up):
    M = bone.get(matname)
    if M == None:
        M = bone.matrix.copy()
    else:
        M = util.matrix_from_array(M)
        if sum_up:
            if not pmat:
                print("%s: no pmat" % bone.name)
            if not M:
                print("%s: no %s" % (bone.name, matname))
            M = pmat @ M
    return M


def convert_bindinfo_to_shape(armobj):
    omode = util.ensure_mode_is("EDIT")
    root = armobj.data.edit_bones[0]
    convert_restmat_recursive('bind_mat', root, Matrix(), sum_up=False)
    convert_restmat_recursive('rest_mat', root, Matrix(), sum_up=True)
    util.ensure_mode_is(omode)


def reset_to_bindshape(context, revert_to_bindshape):
    try:
        active = context.active_object
        armobj = util.get_armature(active)
        omode = active.mode
        amode = armobj.mode
        util.ensure_mode_is("OBJECT")
        util.set_active_object(context, armobj)
        util.ensure_mode_is("OBJECT")

        if revert_to_bindshape:
            shape.paste_shape_from_object(active, armobj)
            mesh.ButtonRebindArmature.execute_rebind(context, True)
        else:
            dict = shape.asDictionary(armobj, full=True)
            shape.paste_shape_from_object(active, armobj)
            mesh.ButtonRebindArmature.execute_rebind(context, False)
            shape.fromDictionary(armobj, dict)

        util.ensure_mode_is(amode)
        util.set_active_object(context, active)
        util.ensure_mode_is(omode)

        return{'FINISHED'}
    except Exception as e:
        util.ErrorDialog.exception(e)
        return{'FINISHED'}



classes = (
    AvastarStoreBindData,
    AvastarDisplayInRestpose,
    AvastarCleanupBinding,
    AvastarAlterToRestpose,
    AVASTAR_MT_bind_presets_menu,
    AvastarAddPresetBind,
    AvastarUpdatePresetBind,
    AvastarRemovePresetBind,
    ArmatureJointPosStore,
    ArmatureJointPosRemove,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered bind:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered bind:%s" % cls)
