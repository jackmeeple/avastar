### Copyright 2015, Gaia Clary
### Modifications 2015 Gaia Clary
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

import bpy, bmesh, sys
from mathutils import Vector, Matrix
import  xml.etree.ElementTree as et
import xmlrpc.client
from bpy_extras.io_utils import ExportHelper
from bpy.props import *
import logging, gettext, os, time, re, shutil
from math import pi, exp
from bpy.types import Menu, Operator
from bl_operators.presets import AddPresetBase

from . import const, data, messages, propgroups, rig, util, shape, bl_info
from .const  import *
from .util import mulmat
from bpy.app.handlers import persistent

LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')

log = logging.getLogger('avastar.weights')
registerlog = logging.getLogger("avastar.register")



g_weight_template='''Generate or copy Weights also for %s.
Note:When this option is enabled, then the weights are
still only created when necessary'''

g_weight_base_bones = BoolProperty(default = True,
                   name = "SL Base",
                   description = g_weight_template % "SL Base Deform bones (exclude the Collision volumes and attachment bones)")
g_weight_eye_bones = BoolProperty(default = False,
                   name = "SL Eyes",
                   description = g_weight_template % "mEyeLeft and mEyeRight")
g_weight_alt_eye_bones = BoolProperty(default = False,
                   name = "Alt Eyes",
                   description = g_weight_template % "mFaceEyeAltLeft and mFaceEyeAltright")
g_weight_face_bones = BoolProperty(default = True,
                   name = "Face",
                   description = g_weight_template % "mFace* Bones")
g_weight_groin  = BoolProperty(default = False,
                   name = "Groin",
                   description = g_weight_template % "mGroin")
g_weight_tale = BoolProperty(default = False,
                   name = "Tail",
                   description = g_weight_template % "mTail* Bones")
g_weight_wings = BoolProperty(default = False,
                   name = "Wings",
                   description = g_weight_template % "mWing* Bones")
g_weight_hinds = BoolProperty(default = False,
                   name = "Hinds",
                   description = g_weight_template % "mHind* Bones")
g_weight_hands = BoolProperty(default = True,
                   name = "Hands",
                   description = g_weight_template % "mHand* Bones")
g_weight_volumes = BoolProperty(default = False,
                   name = "Volumes",
                   description = g_weight_template % "Volume Bones")

g_weight_visible  = BoolProperty(default = False,
                   name = "Visible Bones",
                   description = "Take weight only from visible bones")

g_submeshInterpolation = BoolProperty(
            name="Interpolate",
            default=True,
            description="Interpolate the weight values from closests point on surface of reference mesh" )

def update_with_hidden_avastar_meshes(self, context):
    armobj = util.get_armature_from_context(context)
    childset = util.get_animated_meshes(context, armobj, only_visible=False)
    for child in [child for child in childset if child != context.object]:
        child.ObjectProp.is_hidden=child.hide_get()

g_with_hidden_avastar_meshes = BoolProperty(
            update = update_with_hidden_avastar_meshes,
            name="Show hidden Sources",
            default=True,
            description="Also show all hidden Meshes bound to the Armature" )

g_with_listed_avastar_meshes = BoolProperty(
            name="Copy from all listed",
            default=False,
            description = prop_with_listed_avastar_meshes)

g_with_hair = BoolProperty(
            name="Hair",
            default=False,
            description="Include Avastar hair mesh as Weight Source" )

g_with_head = BoolProperty(
            name="Head",
            default=True, 
            description="Include Avastar head mesh as Weight Source" )

g_with_eyes = BoolProperty(
            name="Eyes",
            default=False,
            description="Include Avastar eye meshes as Weight Source" )

g_with_eyelashes = BoolProperty(
            name="Eyelashes",
            default=False,
            description="Include Avastar eyelash meshes as Weight Source" )

g_with_upper_body = BoolProperty(
            name="Upper Body",
            default=True,
            description="Include Avastar upper body mesh as Weight Source" )

g_with_lower_body = BoolProperty(
            name="Lower Body",
            default=True,
            description="Include Avastar lower body mesh as Weight Source" )

g_with_skirt = BoolProperty(
            name="Skirt",
            default=False,
            description="Include Avastar skirt mesh as Weight Source" )

g_use_mirror_x = BoolProperty(
            name="X-Mirror",
            default=True,
            description = "Ensure that for each selected bone also its symmetric counterpart weightmap is created" )

g_clearTargetWeights = BoolProperty(
            name="Clear Target Maps",
            default=True,
            description="Make sure the target Weight maps are empty before Copying the weights to them\n"\
                       +"Note: Only target weight maps are affected. All other weight maps remain unchanged.\n"\
                       +"This option is disabled on purpose when you enable the Selected verts option")

g_copyWeightsToSelectedVerts = BoolProperty(
            name="Selected Verts",
            default=False,
            description="Restrict the copy to selected vertices in the target mesh\n"\
                       +"Note: The weights of unselected vertices are preserved")

g_keep_groups = BoolProperty(
            name="Keep empty Maps",
            default=False,
            description="Keep empty weight maps in the target mesh(es)" 
        )

def module_load():
    bpy.types.WindowManager.MeshesIndexProp = PointerProperty(type=MeshesIndexPropGroup)
    bpy.types.WindowManager.MeshesPropList = CollectionProperty(type=MeshesProp)

def module_unload():
    del bpy.types.WindowManager.MeshesIndexProp
    del bpy.types.WindowManager.MeshesPropList

def mirrorBoneWeightsFromOppositeSide(context, operator, use_topology=False, algorithm='BLENDER'):
    obj        = context.object
    armobj     = obj.find_armature()
    layer_indices = [i for i, l in enumerate(bpy.data.armatures[armobj.data.name].layers) if l]

    activeBone = armobj.data.bones.active
    counter = 0
    selectedBoneNames = []
    for bone in armobj.data.bones:
        if bone.select and not bone.hide :
            bone_layers = [i for i, l in enumerate(bone.layers) if l]
            is_visible  = bool(len([i for i in bone_layers if i in layer_indices]))
            if is_visible:
                mirror_name = util.get_mirror_name(bone.name)
                if mirror_name and mirror_name in obj.vertex_groups and not bone.name in selectedBoneNames:
                    selectedBoneNames.append(bone.name)
                    counter += 1

    if len(selectedBoneNames) > 0:
        if 'toolset_pro' in dir(bpy.ops.sparkles) and algorithm=='SMART':
            import sparkles.util
            print("Calling Sparkles Mirror weight groups")
            sparkles.util.smart_mirror_vgroup(context, armobj, obj, selectedBoneNames)
        else:
            print("Calling Avastar Mirror weight groups...")
            for bone_name in selectedBoneNames:
                mirror_name = util.get_mirror_name(bone_name)
                if mirror_name and mirror_name in obj.vertex_groups:
                    mirror_vgroup(context, armobj, obj, bone_name, mirror_name, use_topology)

    armobj.data.bones.active = activeBone
    return counter


def copyBoneWeightsToActiveBone(context, operator):
    obj        = context.object
    armobj     = obj.find_armature()
    activeBone = armobj.data.bones.active
    for bone in armobj.data.bones:
        if bone.select and not bone.hide and bone != activeBone:
            if bone.name not in obj.vertex_groups:
                raise util.Error('Source Bone "%s" has no Weightgroup to copy from'%(bone.name))
            if activeBone.name in obj.vertex_groups:
                obj.vertex_groups.remove(obj.vertex_groups[activeBone.name])
            armobj.data.bones.active = bone
            util.mode_set(mode='OBJECT')
            util.mode_set(mode='WEIGHT_PAINT')
            bpy.ops.object.vertex_group_copy()
            copyName = armobj.data.bones.active.name + "_copy"
            vg = bpy.context.object.vertex_groups[copyName]
            vg.name = activeBone.name
            armobj.data.bones.active = activeBone
            break

MBONE_CVBONE_PAIRS = {
                'mHead'          : 'HEAD',
                'mNeck'          : 'NECK',
                'mChest'         : 'CHEST',

                'mTorso'         : 'BELLY',

                'mPelvis'        : 'PELVIS',

                'mCollarRight'   : 'R_CLAVICLE',
                'mShoulderRight' : 'R_UPPER_ARM',
                'mElbowRight'    : 'R_LOWER_ARM',
                'mWristRight'    : 'R_HAND',

                'mCollarLeft'    : 'L_CLAVICLE',
                'mShoulderLeft'  : 'L_UPPER_ARM',
                'mElbowLeft'     : 'L_LOWER_ARM',
                'mWristLeft'     : 'L_HAND',

                'mHipRight'      : 'R_UPPER_LEG',
                'mKneeRight'     : 'R_LOWER_LEG',
                'mAnkleRight'    : 'R_FOOT',

                'mHipLeft'       : 'L_UPPER_LEG',
                'mKneeLeft'      : 'L_LOWER_LEG',
                'mAnkleLeft'     : 'L_FOOT'
             }

MBONE_CVBONE_LABELS = {
                'mHead'          : 'Head',
                'mNeck'          : 'Neck',
                'mChest'         : 'Chest',
                'mTorso'         : 'Belly',
                'mPelvis'        : 'Pelvis',
                'mCollarRight'   : 'Right Clavicle',
                'mShoulderRight' : 'Right Upper Arm',
                'mElbowRight'    : 'Right Lower Arm',
                'mWristRight'    : 'Right Hand',
                'mCollarLeft'    : 'Left Clavicle',
                'mShoulderLeft'  : 'Left Upper Arm',
                'mElbowLeft'     : 'Left Lower Arm',
                'mWristLeft'     : 'Left Hand',
                'mHipRight'      : 'Right Upper Leg',
                'mKneeRight'     : 'Right Lower Leg',
                'mAnkleRight'    : 'Right Foot',
                'mHipLeft'       : 'Left Upper Leg',
                'mKneeLeft'      : 'Left Lower Leg',
                'mAnkleLeft'     : 'Left Foot',

                'HEAD'           : 'Head',
                'NECK'           : 'Neck',
                'CHEST'          : 'Chest',
                'BELLY'          : 'Belly',
                'PELVIS'         : 'Pelvis',
                'R_CLAVICLE'     : 'Right Clavicle',
                'R_UPPER_ARM'    : 'Right Upper Arm',
                'R_LOWER_ARM'    : 'Right Lower Arm',
                'R_HAND'         : 'Right Hand',
                'L_CLAVICLE'     : 'Left Clavicle',
                'L_UPPER_ARM'    : 'Left Upper Arm',
                'L_LOWER_ARM'    : 'Left Lower Arm',
                'L_HAND'         : 'Left Hand',
                'R_UPPER_LEG'    : 'Right Upper Leg',
                'R_LOWER_LEG'    : 'Right Lower Leg',
                'R_FOOT'         : 'Right Foot',
                'L_UPPER_LEG'    : 'Left Upper Leg',
                'L_LOWER_LEG'    : 'Left Lower Leg',
                'L_FOOT'         : 'Left Foot'
             }

BONE_PAIRS = dict (zip(MBONE_CVBONE_PAIRS.values(),MBONE_CVBONE_PAIRS.keys()))
BONE_PAIRS.update(MBONE_CVBONE_PAIRS)

def get_bone_label(name):
    try:
        return MBONE_CVBONE_LABELS.get(name, name+':uh')
    except:
        return None

def get_bone_partner(name):
    try:
        return BONE_PAIRS[name]
    except:
        return None

def is_weighted_pair(obj, bname):
    if get_bone_group(obj, bname, create=False):
        if get_bone_partner_group(obj, bname, create=False):

            return True
    return False

def get_bone_partner_group(obj, name, create=True):
    partner_name = get_bone_partner(name)
    pg = get_bone_group(obj, partner_name, create=create) if partner_name else None
    return pg

def get_bone_group(obj, name, create=True):
    group = None
    if obj and name:
        group = None
        if name in obj.vertex_groups:
            group =  obj.vertex_groups[name]
        if group == None and create:
            group = obj.vertex_groups.new(name=name)
            weights = util.get_weights(obj, group)
            log.info("Created group: %s:%s having %d entries" % (obj.name, name, len(weights)) )
    return group





class FittingValues(bpy.types.PropertyGroup):

    generate_weights : BoolProperty(default=False, name="Generate Weights",
        description="For Fitted Mesh: Create weights 'automatic from bone' for BUTT, HANDLES, PECS and BACK" )
    auto_update : BoolProperty(default=True, name="Apply auto",
        description="Apply Slider changes immediately to Shape (WARNING: This option needs a lot of computer resources, expect lag)" )
    selected_verts : BoolProperty(default=False, name="Only Selected",
        description="Apply Slider changes only to selected vertices (when in edit mode or mask select mode)" )

    butt_strength   : FloatProperty(name = "Butt",   min = -1.0, soft_max = 1.0, default = 0,
        update = eval("lambda a,b:updateFittingStrength(a,b,'butt_strength')"),
        description ="Butt Strength")
    pec_strength    : FloatProperty(name = "Pecs",    min = -1.0, soft_max = 1.0, default = 0,
        update = eval("lambda a,b:updateFittingStrength(a,b,'pec_strength')"),
        description ="Pec Strength")
    back_strength   : FloatProperty(name = "Back",   min = -1.0, soft_max = 1.0, default = 0,
        update = eval("lambda a,b:updateFittingStrength(a,b,'back_strength')"),
        description ="Back Strength")
    handle_strength : FloatProperty(name = "Handles", min = -1.0, soft_max = 1.0, default = -1,
        update = eval("lambda a,b:updateFittingStrength(a,b,'handle_strength')"),
        description ="Handle Strength")

    boneSelection : EnumProperty(
        items=(
            ('SELECTED', 'Selected', 'List Selected Deform Collision Volumes (Fitted Mesh Bones)'),
            ('WEIGHTED', 'Weighted', 'List Deform Collision Volumes (Fitted Mesh Bones) which also have a weight groups'),
            ('ALL',      'All',      'List all Deform Collision Volumes (Fitted Mesh Bones)')),
        name="Selection",
        description="The set of displayed strength sliders",
        default='WEIGHTED')

PHYSICS_GROUPS = {'butt_strength' :['BUTT'],
                 'pec_strength'   :['RIGHT_PEC','LEFT_PEC'],
                 'back_strength'  :['UPPER_BACK','LOWER_BACK'],
                 'handle_strength':['RIGHT_HANDLE','LEFT_HANDLE']
                 }

preset_fitting=False
update_fitting=True

class ButtonDeletePhysics(bpy.types.Operator):
    bl_idname = "avastar.delete_physics"
    bl_label = "Delete physics"
    bl_description = "Delete Physics weights (Armature rigging style must be 'Fitted Mesh')"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and 'physics' in obj

    def execute(self, context):
        removePhysicsWeights(context, context.object)
        return {'FINISHED'}

def ShapekeyItemsCallback(scene, context):
    items=[]
    blocks = None
    try:
        blocks = context.object.data.shape_keys.key_blocks
    except:
        pass

    if blocks:
        for key in blocks:
            items.append(
                (key.name, key.name, "relative shapekey to be used")
            )

    return items

class ButtonRebaseShapekey(bpy.types.Operator):
    bl_idname = "avastar.rebase_shapekey"
    bl_label = "Rebase Shapekey"
    bl_description = "set relative_key of active Shapekey (set to  neutral_shape by default, change in operator panel)"
    bl_options = {'REGISTER', 'UNDO'}

    relative_key_name : EnumProperty(
        items=ShapekeyItemsCallback,
        name="Relative Key",
        description="Relative Key (shape key parent)"
    )

    @classmethod
    def poll(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH': return False
        keys = obj.data.shape_keys
        if keys == None: return False
        blocks = keys.key_blocks
        return blocks != None and len(blocks) >1

    def invoke(self, context, event):
        active_key = context.object.active_shape_key
        if active_key == None:
            active_key = context.object.data.shape_keys.key_blocks[0]
        relative_key_name = active_key.relative_key.name
        return self.execute(context)

    def execute(self, context):
        obj          = context.object
        active_key   = obj.active_shape_key
        rebase_shapekey(context.object, active_key.name, self.relative_key_name)
        return{'FINISHED'}

class ButtonRegeneratePhysics(bpy.types.Operator):
    bl_idname = "avastar.regenerate_physics"
    bl_label = "Update Physics"
    bl_description = "Update weights for Physics bones preserving physics Slider values"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        status = ButtonGeneratePhysics.generate(self, context, reset=False)
        msg = "Updated Physic Bone Weights (using Bone Heat)"
        self.report({'INFO'},msg)
        return status

class ButtonEnablePhysics(bpy.types.Operator):
    bl_idname = "avastar.enable_physics"
    bl_label = "Enable Physics"
    bl_description = "Enable pre existing weights for Physics bones (preserves custom Weights"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        status = ButtonGeneratePhysics.generate(self, context, reset=True, init=False)
        msg = "Enabled Physic Bone Weight Sliders"
        self.report({'INFO'},msg)
        return status

class ButtonGeneratePhysics(bpy.types.Operator):
    bl_idname = "avastar.generate_physics"
    bl_label = "Generate Physics"
    bl_description = "Generate weights for Physics bones (Butt, Pecs, Handles, Back)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):



        status = ButtonGeneratePhysics.generate(self, context, reset=True)
        msg = "Generated Physic Bone Weights (using Bone Heat)"
        self.report({'INFO'},msg)
        return status

    @staticmethod
    def generate(self, context, reset=True, init=True):
        scene = context.scene
        obj   = context.object
        arm   = obj.find_armature()
        obj_mode = obj.mode
        arm_mode = arm.mode

        util.ensure_mode_is("OBJECT")
        arm.ObjectProp.rig_display_type ='MAP'
        active_bone = arm.data.bones.active

        util.set_active_object(context, arm)
        util.ensure_mode_is("POSE")

        select_backup = util.setSelectOption(arm, SLSHAPEVOLBONES, exclusive=True)
        util.setDeformOption(arm, SLSHAPEVOLBONES, exclusive=False)
        util.ensure_mode_is("OBJECT")
        util.ensure_mode_is("POSE")

        util.set_active_object(context, obj)
        util.createEmptyGroups(obj, names = SLSHAPEVOLBONES)
        util.ensure_mode_is("WEIGHT_PAINT")


        obj.data.use_paint_mask          = False
        obj.data.use_paint_mask_vertex   = False
        try:
            props = obj.FittingValues
            if "physics" in obj:
                del obj['physics']

            if init:

                bpy.ops.paint.weight_from_bones() #Take care that the weight groups exist before calling this operator!
                util.ensure_mode_is("OBJECT")




            if reset:

                setPresetFitting(True)
                props.butt_strength   = 0
                props.pec_strength    = 0
                props.back_strength   = 0
                props.handle_strength = -1
                setPresetFitting(False)

            scale_level(obj, props.butt_strength,   ['BUTT'])
            scale_level(obj, props.pec_strength,    ['RIGHT_PEC','LEFT_PEC'])
            scale_level(obj, props.back_strength,   ['UPPER_BACK','LOWER_BACK'])
            scale_level(obj, props.handle_strength, ['RIGHT_HANDLE','LEFT_HANDLE'])

        except Exception as e:
            util.restoreSelectOption(arm, select_backup)
            util.set_active_object(bpy.context, obj)
            util.ensure_mode_is(obj_mode, object=obj)
            util.ensure_mode_is(arm_mode, object=arm)
            print("Could not generate weights for Physic bones")
            util.ErrorDialog.exception(e)
            return{'CANCELLED'}

        if active_bone:
            if not active_bone.name in obj.vertex_groups:
                if get_bone_partner_group(obj, active_bone.name, create=False):
                    active_bone = arm.data.bones[get_bone_partner(active_bone.name)]
                else:
                    active_bone = None
        if active_bone:
            arm.data.bones.active=active_bone

        util.restoreSelectOption(arm, select_backup)
        util.ensure_mode_is(arm_mode, object=arm)

        util.set_active_object(bpy.context, obj)
        util.ensure_mode_is("OBJECT", object=obj)
        util.ensure_mode_is(obj_mode, object=obj)

        return{'FINISHED'}

def add_fitting_preset(context, filepath):

    def get_fitting_presets(obj):
        list = ""
        for key, val in obj.FittingValues.items():
            if key in ['boneSelection','auto_update']:
                continue
            list += "    obj.FittingValues.%s=%s\n"%(key,val)
        return list

    obj    = context.object

    file_preset = open(filepath, 'w')
    file_preset.write(
'''#Generated by Avastar %s with Blender %s

import bpy
import avastar
from avastar import data, util, shape, weights

context = bpy.context
active  = context.object
amode   = util.ensure_mode_is('OBJECT')
arm     = active.find_armature()

weights.setUpdateFitting(False)
selector = arm.ObjectProp.slider_selector
if selector != 'NONE':
    arm.ObjectProp.slider_selector='NONE'

deforming_bones = data.get_volume_bones(arm, only_deforming=False) + data.get_base_bones(arm, only_deforming=False) + data.get_extended_bones(arm, only_deforming=False) 
weights.setDeformingBones(arm, deforming_bones, replace=True)

selection = [active] if amode=='EDIT' else util.get_animated_meshes(context, arm, with_avastar=False, only_selected=True, return_names=False)

for obj in selection:
    util.set_active_object(bpy.context, obj)

%s

    bone_names = [b.name for b in arm.data.bones if b.use_deform]
    weights.removeBoneWeightGroupsFromSelectedBones(context, obj, only_remove_empty=True, bone_names=bone_names) #remove empty groups
    util.add_missing_mirror_groups(context)

    arm.ObjectProp.slider_selector=selector if selector != 'NONE' else 'SL'

    weights.setUpdateFitting(True)
    shape.refresh_shape(context, arm, obj, graceful=True)

util.set_active_object(bpy.context, active)
util.ensure_mode_is(amode)
    
''' % (util.get_addon_version(), bpy.app.version_string, get_fitting_presets(obj) )
    )
    file_preset.close()

class AVASTAR_MT_fitting_presets_menu(Menu):
    bl_label  = "Fitting Presets"
    bl_description = "Fitting Presets for custom attachments"
    preset_subdir = os.path.join("avastar","fittings")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class AvastarAddPresetFitting(AddPresetBase, Operator):
    bl_idname = "avastar.fitting_presets_add"
    bl_label = "Add Fitting Preset"
    bl_description = "Create new Preset from current Fitting Slider settings"
    preset_menu = "AVASTAR_MT_fitting_presets_menu"

    preset_subdir = os.path.join("avastar","fittings")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_fitting_preset(context, filepath)

class AvastarUpdatePresetFitting(AddPresetBase, Operator):
    bl_idname = "avastar.fitting_presets_update"
    bl_label = "Update Fitting Preset"
    bl_description = "Store current Slider settings in last selected Preset"
    preset_menu = "AVASTAR_MT_fitting_presets_menu"
    preset_subdir = os.path.join("avastar","fittings")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_fitting_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_fitting_preset(context, filepath)

class AvastarRemovePresetFitting(AddPresetBase, Operator):
    bl_idname = "avastar.fitting_presets_remove"
    bl_label = "Remove Fitting Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_fitting_presets_menu"
    preset_subdir = os.path.join("avastar","fittings")

def setPresetFitting(state):
    global preset_fitting
    preset_fitting = state

def setUpdateFitting(state):
    global update_fitting
    update_fitting = state

def updateFittingStrength(self, context, bone_name=None):
    global preset_fitting
    global update_fitting
    if preset_fitting:
        return
    oldstate = None
    try:
        old_handler_state = util.set_disable_handlers(context.scene, True)

        obj   = context.object
        omode = obj.mode if obj.mode !='EDIT' else util.ensure_mode_is("OBJECT")
        original_group = obj.vertex_groups.active
        
        if bone_name in PHYSICS_GROUPS.keys():
            try:

                scale_level(obj, obj.FittingValues[bone_name],  PHYSICS_GROUPS[bone_name])
                active_group = get_bone_group(obj,PHYSICS_GROUPS[bone_name][0], create=False)


            except Exception as e:
                print("Could not generate weights for Physic bones")
                util.ErrorDialog.exception(e)
                return
        else:
            only_selected = util.update_only_selected_verts(obj, omode)
            percent       = getattr(obj.FittingValues, bone_name)
            active_group  = set_fitted_strength(context, obj, bone_name, percent, only_selected, omode)

        util.ensure_mode_is(omode)

        if active_group:
            obj.vertex_groups.active_index = active_group.index
        else:
            obj.vertex_groups.active_index = -1

        armobj  = obj.find_armature()
        if update_fitting and self.auto_update:


            if active_group:
                try:
                    bone_name = active_group.name
                except:
                    active_group = None
                    log.debug("active group has been deleted")
            elif armobj.data.bones.active:
                bone_name = armobj.data.bones.active.name
            else:
                bone_name = None

            if bone_name and active_group:
                b = armobj.data.bones[bone_name]
                pname = get_bone_partner(bone_name)
                b.use_deform=True
                if pname:
                    c = armobj.data.bones[pname]
                    c.use_deform=True


            shape.refresh_shape(context, armobj, obj, graceful=True, only_weights=True)
            if CHECKSUM in obj and obj.mode != 'EDIT':
                del obj[CHECKSUM] # do not need checksum when we are not in EDIT mode

            if bone_name and active_group:
                armobj.data.bones.active = armobj.data.bones[bone_name]
            util.enforce_armature_update(context,armobj)

        if armobj.ObjectProp.rig_display_type == 'MAP':

            armobj['rig_display_mesh_count'] = 0
        util.ensure_mode_is(omode)

    finally:
        util.set_disable_handlers(context.scene, old_handler_state)
    return

def register_FittingValues_attributes():
    for bname in MBONE_CVBONE_PAIRS.values():
        exist = getattr(FittingValues, bname, None)
        if exist is None:
            setattr(FittingValues, bname,
                    FloatProperty(name = bname,
                                  update = eval("lambda a,b:updateFittingStrength(a,b,'%s')"%bname),
                                  min      = 0, max      = 1.0,
                                  soft_min = 0, soft_max = 1.0,
                                  default = 1.0))

def unregister_FittingValues_attributes():
    for bname in MBONE_CVBONE_PAIRS.values():
        exist = getattr(FittingValues, bname, None)
        if exist:
            delattr(FittingValues, bname)

def has_collision_volumes(weighted_bones):
    return any([a in SLVOLBONES for a in weighted_bones])
    
def classic_fitting_preset(obj):
    setPresetFitting(True)
    armobj = obj.find_armature()
    if armobj:
        for bone in MBONE_CVBONE_PAIRS.values():
            setattr(obj.FittingValues,bone,0)
    setPresetFitting(False)

def fitmesh_fitting_preset(obj):
    setPresetFitting(True)
    armobj = obj.find_armature()
    if armobj:
        for bone in MBONE_CVBONE_PAIRS.values():
            if bone in obj.vertex_groups:
                setattr(obj.FittingValues,bone,1)
            else:
                setattr(obj.FittingValues,bone,0)
    setPresetFitting(False)



def moveDeform2Collision(obj, adjust_deform = False):
    armobj    = obj.find_armature()
    bones = [b.name for b in armobj.data.bones if b.name.startswith("m")]
    moveBones(obj, bones, adjust_deform)

def moveCollision2Deform(obj, adjust_deform = False):
    armobj    = obj.find_armature()
    bones = [b.name for b in armobj.data.bones if not b.name.startswith("m")]
    moveBones(obj, bones, adjust_deform)

def moveBones(obj, bones, adjust_deform = False):
    print("moveBones:",bones, "object=", obj.name, "type=", obj.type)
    active = util.get_active_object(bpy.context)
    armobj    = obj.find_armature()

    util.set_active_object(bpy.context, obj)
    original_mode = util.ensure_mode_is("WEIGHT_PAINT")

    success   = 0

    for bone_name in bones:
        bone = armobj.data.bones[bone_name]
        if not bone.hide and bone.name in BONE_PAIRS and bone.name in obj.vertex_groups:
            pbone = armobj.data.bones[BONE_PAIRS[bone.name]]
            print("Move weights %s -> %s" % (bone.name, pbone.name))
            if pbone.name in obj.vertex_groups:
                util.removeWeightGroups(obj, [pbone.name])

            group      = obj.vertex_groups[bone.name]
            group.name = pbone.name
            success +=1
            if adjust_deform:
                bone.use_deform  = False
                bone.layers[B_LAYER_DEFORM]  = False
                bone.select      = False
            pbone.use_deform = True
            pbone.layers[B_LAYER_DEFORM] = True
            pbone.select     = True
            success  += 1

    if success > 0:
        util.ensure_mode_is('OBJECT')
        util.ensure_mode_is('WEIGHT_PAINT')
    util.ensure_mode_is(original_mode)

    util.set_active_object(bpy.context, active)

def swapCollision2Deform(obj, adjust_deform = False, keep_groups=False):
    print("SwapCollision2Deform object=", obj.name, "type=", obj.type)
    active = util.get_active_object(bpy.context)
    armobj    = obj.find_armature()

    util.set_active_object(bpy.context, obj)
    original_mode = util.ensure_mode_is("WEIGHT_PAINT")

    bones     = [b.name for b in armobj.data.bones if b.select]
    processed = []

    success   = 0
    noweights = 0
    nobone    = 0

    for bone_name in bones:
        bone = armobj.data.bones[bone_name]
        if not (bone.hide or bone.name in processed):

            if bone.name not in BONE_PAIRS:
                print('Bone "%s" has no paired bone'%(bone.name))
                nobone += 1
            else:
                pbone = armobj.data.bones[BONE_PAIRS[bone.name]]
                print("Processing %s - %s" % (pbone.name, bone.name))
                if bone.name not in obj.vertex_groups:
                    if pbone.name in obj.vertex_groups:
                        vgroup      = obj.vertex_groups[pbone.name]
                        vgroup.name = bone.name
                        if keep_groups:
                            obj.vertex_groups.new(name=pbone.name)
                        success +=1
                        if adjust_deform:
                            pbone.use_deform = False
                            pbone.layers[B_LAYER_DEFORM] = False
                        bone.use_deform  = True
                        bone.layers[B_LAYER_DEFORM]  = True
                        bone.select      = True
                        print ("moved weights from %s to %s" % (pbone.name, bone.name))
                    else:
                        noweights += 1
                elif pbone.name not in obj.vertex_groups:
                    if bone.name in obj.vertex_groups:
                        vgroup      = obj.vertex_groups[bone.name]
                        vgroup.name = pbone.name
                        if keep_groups:
                            obj.vertex_groups.new(name=bone.name)
                        success +=1
                        if adjust_deform:
                            bone.use_deform   = False
                            bone.layers[B_LAYER_DEFORM]   = False
                        pbone.use_deform  = True
                        pbone.layers[B_LAYER_DEFORM]  = True
                        pbone.select      = True
                        print ("moved weights from %s to %s" % (bone.name, pbone.name))
                    else:
                        noweights += 1
                else:
                    print ("swapping weights of %s <--> %s" % (bone.name, BONE_PAIRS[bone.name]))
                    from_group      = obj.vertex_groups[bone.name]
                    to_group        = obj.vertex_groups[pbone.name]
                    to_group.name   = to_group.name + "_tmp"
                    from_group.name = pbone.name
                    to_group.name   = bone.name
                    success +=1
                    bone.use_deform  = True
                    bone.layers[B_LAYER_DEFORM]  = True
                    pbone.use_deform = True
                    pbone.layers[B_LAYER_DEFORM] = True
                    bone.select      = True
                    pbone.select     = True

                processed.append(bone.name)
                processed.append(pbone.name)

    if success > 0:
        util.ensure_mode_is('OBJECT')
        util.ensure_mode_is('WEIGHT_PAINT')
    util.ensure_mode_is(original_mode)

    util.set_active_object(bpy.context, active)
    return nobone

def mirror_vgroup(context, armobj, obj, tgt_name, src_name, use_topology):

    if tgt_name in obj.vertex_groups:
        obj.vertex_groups.remove(obj.vertex_groups[tgt_name])
    original_select = armobj.data.bones[src_name].select

    armobj.data.bones.active = armobj.data.bones[src_name]
    armobj.data.bones.active.select = True
    obj.vertex_groups.active_index=obj.vertex_groups[src_name].index
    bpy.ops.object.vertex_group_copy()
    bpy.ops.object.vertex_group_mirror(use_topology=use_topology)
    bpy.ops.object.vertex_group_clean()
    vg = bpy.context.object.vertex_groups[src_name+"_copy"]
    vg.name = tgt_name
    armobj.data.bones.active = armobj.data.bones[tgt_name]
    util.mode_set(mode='OBJECT')
    util.mode_set(mode='WEIGHT_PAINT')
    armobj.data.bones[src_name].select = original_select
    print("mirrored from %s -> %s"%(src_name,tgt_name))


def getWeights(target_ob, source_ob, point, submesh = False, restrictTo=None):

    M = target_ob.matrix_world
    p = M.inverted() @ point

    status, loc, face_normal, face_index = util.closest_point_on_mesh(target_ob, p)






    target_me = target_ob.data
    target_verts  = target_me.vertices

    target_poly= target_me.polygons[face_index]
    gdata = {}

    if submesh:
        dmin = (p-loc).length

        vw = interpolation(target_ob, target_poly, loc)

        for vidx, interpw in vw.items():


            v = target_verts[vidx]

            for grp in v.groups:
                grp_index = grp.group
                source_group = source_ob.vertex_groups[grp_index]
                if not source_group:
                    print ("Copy weights from %s.%s to %s failed" % (source_ob.name, grp.group, target_ob.name) )
                else:
                    gname = source_group.name
                    if  restrictTo==None or gname in restrictTo:
                        weight = grp.weight
                        oldweight = gdata.get(gname, 0)
                        gdata[gname] = oldweight + weight*interpw



    else:



        vtx = min(target_poly.vertices, key=lambda v: (p - target_verts[v].co).length)

        v = target_verts[vtx]
        dmin = (v.co-p).length


        for grp in v.groups:
            gname = source_ob.vertex_groups[grp.group].name
            if  restrictTo==None or gname in restrictTo:
                weight = grp.weight
                gdata[gname] = weight



    return dmin, gdata



def interpolation(obj, polygon, loc):


    SMALLEST_DISTANCE = 1e-5
    SMALLEST_WSUM     = 1e-8

    D = 0
    for v1idx in polygon.vertices:
        v1 = obj.data.vertices[v1idx]
        for v2idx in polygon.vertices:
            v2 = obj.data.vertices[v2idx]
            if v1idx!=v2idx:
                d = (v1.co-v2.co).length
                D = max(D,d)
    sigma = D

    on_vertex = None
    weight_data = {}
    N = 0
    for vidx in polygon.vertices:
        v = obj.data.vertices[vidx]
        d = (loc-v.co).length

        if d < SMALLEST_DISTANCE:
            on_vertex = vidx
            break
        else:
            w = exp(-(d/sigma)**2)
            weight_data[vidx] = w
            N += w

    if on_vertex is None and N < SMALLEST_WSUM:
        on_vertex = polygon.vertices[0]

    if on_vertex is None:
        for vidx in weight_data:
            weight_data[vidx] = weight_data[vidx]/N
    else:
        for vidx, w in weight_data.items():
            weight_data[vidx] = 0.0
        weight_data[on_vertex] = 1.0

    return weight_data


def copyBoneWeightsToSelectedBones(target, sources, selectedBoneNames, submeshInterpolation=True, allVerts=True, clearTargetWeights=True):
    context = bpy.context
    scene   = context.scene
    depsgraph=context.evaluated_depsgraph_get()

    armobj = target.find_armature()
    original_mode = util.ensure_mode_is("WEIGHT_PAINT", object=target)
    if selectedBoneNames == None:
        selectedBoneNames = target.vertex_groups.keys()
        






    clones = []
    clean_target_groups = []
    print("Copy weights found %d animated mesh objects and %d target bones" % (len(sources), len(selectedBoneNames)) )
    for childobj in sources:
        if not childobj==target and not childobj.name.startswith('CustomShape_'):

            print("Found weight source [", childobj.name, "]")
            childmesh = childobj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
            childmesh.update(calc_edges=True)
            childcopyobj = bpy.data.objects.new(childobj.name, childmesh.copy())
            childcopyobj.matrix_world = childobj.matrix_world.copy()
            util.link_object(context, childcopyobj)
            clones.append((childcopyobj, childobj))

    if len(clones) == 0:
        raise "Please ensure that at least one part of the Avastar mesh is visible.\n Then try again."

    util.update_view_layer(context)



    M=target.matrix_world

    if clearTargetWeights:
        util.remove_weights_from_deform_bones(target, use_all_verts=allVerts)


    for vertex in target.data.vertices:
        if allVerts or vertex.select:
            vs = []
            pt = M @ vertex.co


            for source in clones:

                d, gdata = getWeights(source[0], source[1], pt, submeshInterpolation, selectedBoneNames)
                vs.append((d,gdata))


            vmin = min(vs, key=lambda v: v[0])

            copied=[]
            for gn,w in vmin[1].items():
                if gn in selectedBoneNames:
                    copied.append(gn)




                    if gn not in target.vertex_groups:
                        target.vertex_groups.new(name=gn)
                        clean_target_groups.append(gn)

                    target.vertex_groups[gn].add([vertex.index], w, 'REPLACE')









    for childcopyobj, childobj in clones:
        util.remove_object(context, childcopyobj)

    util.ensure_mode_is("OBJECT", object=target)
    util.ensure_mode_is(original_mode, object=target)
    return len(selectedBoneNames)

def draw(op, context):
    layout = op.layout
    scn = context.scene

    box = layout.box()
    box.label(text="Weight Copy settings")
    col = box.column(align=True)
    col.prop(op, 'submeshInterpolation')
    col.prop(op, 'cleanVerts')
    col.prop(op, 'allVisibleBones')
    col.prop(op, 'allHiddenBones')


def get_bones_from_armature(armobj, allVisibleBones, allHiddenBones):
    if allVisibleBones:
        boneNames = util.getVisibleBoneNames(armobj)
    else:
        boneNames = util.getVisibleSelectedBoneNames(armobj)
    if allHiddenBones:
        boneNames.extend(util.getHiddenBoneNames(armobj))
    return boneNames

def create_message(op, context, template):

    ss=" "
    if op.onlySelectedVerts:
        ss=" masked "

    tgt = "selected"
    if op.allVisibleBones and op.allHiddenBones:
       tgt = "all"
    elif op.allVisibleBones:
       tgt = "all visible"
    elif op.allHiddenBones:
       tgt += " + hidden"

    msg = template % (ss, tgt)
    return msg

def get_used_group_names(obj):


    vertices = obj.data.vertices
    used_group_names = set()
    vertex_groups = obj.vertex_groups
    for v in vertices:
        for group in [g for g in v.groups if g.weight > 0]:
            used_group_names.add(vertex_groups[group.group].name)
    return used_group_names

def removePhysicsWeights(context, obj):
    bone_names = []
    for names in PHYSICS_GROUPS.values():
        bone_names.extend(names)
    removeBoneWeightGroupsFromSelectedBones(context, obj, only_remove_empty=False, bone_names=bone_names)
    if 'physics' in obj:
        del obj['physics']

def removeBoneWeightGroupsFromSelectedBones(context, obj, only_remove_empty, bone_names, remove_nondeform=False):
    armobj        = obj.find_armature()
    c = 0

    if remove_nondeform:
        for name in [name for name in obj.vertex_groups.keys() if not name in armobj.data.bones.keys()]:
            group = obj.vertex_groups[name]
            obj.vertex_groups.active_index=group.index
            bpy.ops.object.vertex_group_remove()
            c+=1
            print("Removed non deforming Weight group",name)

    if bone_names:
        target_names = [name for name in bone_names if name in obj.vertex_groups]
    else:
        target_names = [g.name for g in obj.vertex_groups]

    used_group_names = get_used_group_names(obj)
    for name in [bone_name for bone_name in target_names if bone_name not in used_group_names]:
        group = obj.vertex_groups[name]
        obj.vertex_groups.active_index=group.index
        bpy.ops.object.vertex_group_remove()
        c += 1
    return c

def removeBoneWeightsFromSelectedBones(context, operator, allVerts, boneNames):
    obj           = context.object
    armobj        = obj.find_armature()
    activeBone    = armobj.data.bones.active
    original_mode = util.ensure_mode_is('EDIT')
    counter       = 0
    for bone in [b for b in armobj.data.bones if b.name in boneNames and b.name in obj.vertex_groups]:
        armobj.data.bones.active = bone
        bpy.ops.object.vertex_group_set_active(group=bone.name)
        if allVerts:
            bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove_from()
        counter += 1

    armobj.data.bones.active = activeBone
    util.ensure_mode_is(original_mode)
    return counter

class ButtonCopyBoneWeights(bpy.types.Operator):
    bl_idname = "avastar.copy_bone_weights"
    bl_label = "Copy Weights"
    bl_description = "Various Copy tools operating on Bone weight groups"
    bl_options = {'REGISTER', 'UNDO'}

    weightCopyAlgorithm : StringProperty()

    weightCopyType : EnumProperty(
        items=(
            ('ATTACHMENT', 'from Attachments',     'Copy bone weights from same bones of other attachments'),
            ('MIRROR',     'from Opposite Bones',  'Copy bone Weights from opposite bones of same object'),
            ('BONES',      'selected to active',   'Copy bone weights from selected bone to active bone (needs exactly 2 selected bones) '),
            ('CLEAR',      'Clear selected bones', 'remove bone weights from selected bones '),
            ('SWAP',       'Collision <-> SL',     'Exchange weights of selected Collision volumes with weights from associted SL Bones')),
        name="Copy",
        description="Method for Bone Weight transfer",
        default='ATTACHMENT')

    submeshInterpolation : g_submeshInterpolation

    onlySelectedVerts : BoolProperty(default=False, name="Only selected vertices",
        description="Copy weights only to selected vertices in the target mesh")

    allVisibleBones : BoolProperty(default=False, name="Include all visible bones",
        description="Copy Weights from all visbile Bones. If not set, then copy only from selected Bones")

    allHiddenBones : BoolProperty(default=False, name="Include All hidden bones",
        description="Copy Weights from all hidden Bones. If not set, then copy only from selected Bones")

    cleanVerts : BoolProperty(default=False, name="Clean Targets",
        description="Clean Target vertex Groups before performnig the copy action")

    weight_base_bones : g_weight_base_bones
    weight_eye_bones : g_weight_eye_bones
    weight_alt_eye_bones : g_weight_alt_eye_bones
    weight_face_bones : g_weight_face_bones
    weight_groin : g_weight_groin
    weight_visible : g_weight_visible
    weight_tale : g_weight_tale
    weight_wings : g_weight_wings
    weight_hinds : g_weight_hinds
    weight_hands : g_weight_hands
    weight_volumes : g_weight_volumes

    def invoke(self, context, event):
        meshProps = context.scene.MeshProp
        submeshInterpolation = meshProps.submeshInterpolation
        ob = bpy.context.object
        me = ob.data
        if ob.mode=='EDIT' or me.use_paint_mask_vertex or me.use_paint_mask:
            self.onlySelectedVerts = True
        else:
            self.onlySelectedVerts = False
        return self.execute(context)

    def execute(self, context):
        meshProps = context.scene.MeshProp

        try:
            if self.weightCopyType == "BONES":
                copyBoneWeightsToActiveBone(context, self)
                self.report({'INFO'}, "Copied Selected bone to Active bone")

            elif self.weightCopyType =="SWAP":
                if bpy.context.selected_pose_bones is None:
                    self.report({'WARNING'}, "Please select at least 1 bone")
                else:
                    obj = context.object
                    c   = swapCollision2Deform(obj)
                    if c > 0:
                        self.report({'WARNING'}, "Swap failed for %d bones" % (c))

            else:
                obj       = context.object
                armobj    = obj.find_armature()
                boneNames = get_bones_from_armature(armobj, self.allVisibleBones, self.allHiddenBones)

                if self.weightCopyType == "CLEAR":
                    c = removeBoneWeightsFromSelectedBones(context, self, boneNames)
                    self.report({'INFO'},"Removed %d Groups from %s" %(c, armobj.name) )
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}

class ButtonClearBoneWeightGroups(bpy.types.Operator):
    bl_idname = "avastar.clear_bone_weight_groups"
    bl_label = "Cleanup Weightmaps"
    bl_description = \
'''Remove not needed Weight Maps from the Active Object

- If called in Object mode, all selected Mesh objects are affected.
- More selection options available in the Redo Panel

If active Object is an armature, apply to all bound Meshes'''
    bl_options = {'REGISTER', 'UNDO'}

    allVisibleBones : BoolProperty(default=True, name="Include Visible bones",
        description="Delete weight maps of all visible bones")

    allHiddenBones : BoolProperty(default=True, name="Include Hidden bones",
        description="Delete weight maps of all hidden bones")

    allNonDeforming : BoolProperty(default=False, name="Remove non Deforming Weight Maps",
        description="Delete all weight maps which do not belong to Defrom Bones")

    only_remove_empty : BoolProperty(default=True, name="Only Empty weightmaps",
        description="Delete only empty weight maps")

    all_selected : BoolProperty(
        name = "Apply to Selected",
        default = False, 
        description = "Apply the Operator to the current selection" )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Weight Tools", icon=ICON_WPAINT_HLT)

        obj       = context.object
        armobj    = obj.find_armature()
        if armobj:
            col = box.column()
            col.prop(self, "allVisibleBones")
            col.prop(self, "allHiddenBones")
            col.prop(self, "allNonDeforming")
            if context.mode == 'OBJECT':
                col.prop(self, "all_selected", text = 'All Selected Objects')

        col = box.column()
        col.prop(self, "only_remove_empty")

    def execute(self, context):

        def get_selection(context):
            active = context.object
            armobj = util.get_armature(active)

            selection = None
            if active == armobj:
                selection = util.get_animated_meshes(context, armobj, only_visible=True)
            elif context.mode=='OBJECT' and self.all_selected:
                selection = [o for o in context.scene.objects if util.object_select_get(o) and o.type=='MESH']
            elif active.type == 'MESH':
                selection = [active]
            else:
                selection = []
            return selection, active, armobj

        selection, active, armobj = get_selection(context)
        boneNames = get_bones_from_armature(armobj, self.allVisibleBones, self.allHiddenBones) if armobj else None

        weight_count = 0
        mesh_count   = 0
        for obj in selection:
            util.set_active_object(context, obj)
            c = removeBoneWeightGroupsFromSelectedBones(context, obj, self.only_remove_empty, boneNames, remove_nondeform=self.allNonDeforming)
            if c > 0:
                msg = "Removed %d weight maps from %s" % (c, obj.name)
                mesh_count += 1
                weight_count += c
            else:
                msg = "No maps removed from %s" % obj.name
            log.info(msg)
        self.report({'INFO'}, "Removed %d weight maps from %d meshes" % (weight_count, mesh_count))
        util.set_active_object(context, active)
        return{'FINISHED'}

class ButtonClearBoneWeights(bpy.types.Operator):
    bl_idname = "avastar.clear_bone_weights"
    bl_label = "Remove Weights"
    bl_description = "Remove all weights from weight groups of selected bones"
    bl_options = {'REGISTER', 'UNDO'}

    submeshInterpolation : g_submeshInterpolation

    onlySelectedVerts : BoolProperty(default=False, name="Only selected vertices",
        description="Copy weights only to selected vertices in the target mesh")

    allVisibleBones : BoolProperty(default=False, name="Include all visible bones",
        description="Copy Weights from all visbile Bones. If not set, then copy only from selected Bones")

    allHiddenBones : BoolProperty(default=False, name="Include All hidden bones",
        description="Copy Weights from all hidden Bones. If not set, then copy only from selected Bones")

    cleanVerts : BoolProperty(default=False, name="Clean Targets",
        description="Clean Target vertex Groups before performnig the copy action")

    def invoke(self, context, event):
        meshProps = context.scene.MeshProp
        submeshInterpolation = meshProps.submeshInterpolation
        ob = bpy.context.object
        me = ob.data
        if ob.mode=='EDIT' or me.use_paint_mask_vertex or me.use_paint_mask:
            self.onlySelectedVerts = True
        else:
            self.onlySelectedVerts = False
        return self.execute(context)

    def execute(self, context):
        try:
            obj       = context.object
            armobj    = obj.find_armature()
            boneNames = get_bones_from_armature(armobj, self.allVisibleBones, self.allHiddenBones)

            c = removeBoneWeightsFromSelectedBones(context, self, not self.onlySelectedVerts, boneNames)
            if self.onlySelectedVerts:
                activeBone    = armobj.data.bones.active
            msg = create_message(self, context, "Cleared%sweights in %s Bones")
            self.report({'INFO'},msg)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}

class ButtonSwapWeights(bpy.types.Operator):
    bl_idname = "avastar.swap_bone_weights"
    bl_label = "Swap Collision & Deform"
    bl_description = "Swap weights of Collision Volumes and corresponding Classic Bones"
    bl_options = {'REGISTER', 'UNDO'}

    submeshInterpolation : g_submeshInterpolation

    onlySelectedVerts : BoolProperty(default=False, name="Only selected vertices",
        description="Copy weights only to selected vertices in the target mesh")

    allVisibleBones : BoolProperty(default=False, name="Include all visible bones",
        description="Copy Weights from all visbile Bones. If not set, then copy only from selected Bones")

    allHiddenBones : BoolProperty(default=False, name="Include All hidden bones",
        description="Copy Weights from all hidden Bones. If not set, then copy only from selected Bones")

    cleanVerts : BoolProperty(default=False, name="Clean Targets",
        description="Clean Target vertex Groups before performnig the copy action")

    def draw(self, context):
        draw(self, context)

    def invoke(self, context, event):
        meshProps = context.scene.MeshProp
        submeshInterpolation = meshProps.submeshInterpolation
        ob = bpy.context.object
        me = ob.data
        if ob.mode=='EDIT' or me.use_paint_mask_vertex or me.use_paint_mask:
            self.onlySelectedVerts = True
        else:
            self.onlySelectedVerts = False
        return self.execute(context)

    def execute(self, context):
        meshProps = context.scene.MeshProp

        try:
            if bpy.context.selected_pose_bones is None:
                self.report({'WARNING'}, "Please select at least 1 bone")
            else:
                obj = context.object
                c   = swapCollision2Deform(obj)
                if c > 0:
                    self.report({'WARNING'}, "Swap failed for %d bones" % (c))
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}

class ButtonMirrorBoneWeights(bpy.types.Operator):
    bl_idname = "avastar.mirror_bone_weights"
    bl_label = "Mirror opposite Bones"
    bl_description = "Mirror Weights from opposite side"
    bl_options = {'REGISTER', 'UNDO'}

    weightCopyAlgorithm : StringProperty()

    submeshInterpolation : g_submeshInterpolation

    onlySelectedVerts : BoolProperty(default=False, name="Only selected vertices",
        description="Mirror weights only to selected vertices in the target mesh")

    allVisibleBones : BoolProperty(default=False, name="Include all visible bones",
        description="Mirror Weights from all visbile Bones. If not set, then mirror only from selected Bones")

    allHiddenBones : BoolProperty(default=False, name="Include All hidden bones",
        description="Mirror Weights from all hidden Bones. If not set, then mirror only from selected Bones")

    cleanVerts : BoolProperty(default=False, name="Clean Targets",
        description="Clean Target vertex Groups before performnig the mirror action")

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        box = layout.box()
        box.label(text="Weight Mirror settings")
        col = box.column(align=True)
        col.prop(self, 'submeshInterpolation')
        col.prop(self, 'cleanVerts')
        col.prop(self, 'allVisibleBones')
        col.prop(self, 'allHiddenBones')

    def invoke(self, context, event):
        meshProps = context.scene.MeshProp
        submeshInterpolation = meshProps.submeshInterpolation
        ob = bpy.context.object
        me = ob.data
        if ob.mode=='EDIT' or me.use_paint_mask_vertex or me.use_paint_mask:
            self.onlySelectedVerts = True
        else:
            self.onlySelectedVerts = False
        return self.execute(context)

    def execute(self, context):
        meshProps = context.scene.MeshProp

        try:
            c = mirrorBoneWeightsFromOppositeSide(context, self, context.object.data.use_mirror_topology, algorithm=self.weightCopyAlgorithm)
            self.report({'INFO'}, "Mirrored %d bones from Opposite" % (c))
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}

class ButtonCopyWeightsFromRigged(bpy.types.Operator):
    bl_idname = "avastar.copy_weights_from_rigged"
    bl_label = "Copy from Rigged"
    bl_description = \
'''Copy weights from other Mesh objects rigged to same Armature.

Important: 
1.) Please set the Armature to Pose mode before calling this operator
2.) Only selected vertices are affected
3.) Only weightmaps for selected bones (in the armature) will be created'''

    bl_options = {'REGISTER', 'UNDO'}

    submeshInterpolation : g_submeshInterpolation

    onlySelectedVerts : BoolProperty(default=False, name="Only selected vertices",
        description="Copy weights only to selected vertices in the target mesh")

    allVisibleBones : BoolProperty(default=False, name="Include all visible bones",
        description="Copy Weights from all visbile Bones. If not set, then copy only from selected Bones")

    allHiddenBones : BoolProperty(default=False, name="Include All hidden bones",
        description="Copy Weights from all hidden Bones. If not set, then copy only from selected Bones")

    cleanVerts : BoolProperty(default=True, name="Clean Targets",
        description="Clean Target vertex Groups before performnig the copy action")




    def invoke(self, context, event):
        meshProps = context.scene.MeshProp
        self.submeshInterpolation = meshProps.submeshInterpolation
        ob = bpy.context.object
        me = ob.data
        if ob.mode=='EDIT' or me.use_paint_mask_vertex or me.use_paint_mask:
            self.onlySelectedVerts = True
        else:
            self.onlySelectedVerts = False
        return self.execute(context)

    def execute(self, context):
        meshProps = context.scene.MeshProp

        try:
            obj       = context.object
            armobj    = obj.find_armature()
            boneNames = get_bones_from_armature(armobj, self.allVisibleBones, self.allHiddenBones)
            sources = util.get_animated_meshes(context, armobj)
            copyBoneWeightsToSelectedBones(obj, sources, boneNames, self.submeshInterpolation, allVerts=not self.onlySelectedVerts, clearTargetWeights=self.cleanVerts)
            msg = create_message(self, context, "Copied%sweights from visible siblings and %s Weight Groups")
            self.report({'INFO'}, msg)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}

class ButtonCopyWeightsFromSelected(bpy.types.Operator):
    bl_idname = "avastar.copy_weights_from_selected"
    bl_label = "Copy from Selected"
    bl_description = "Copy weights from Selected Mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    submeshInterpolation : g_submeshInterpolation

    onlySelectedVerts : BoolProperty(default=False, name="Only selected vertices",
        description="Copy weights only to selected vertices in the target mesh")

    allVisibleBones : BoolProperty(default=False, name="Include all visible bones",
        description="Copy Weights from all visbile Bones. If not set, then copy only from selected Bones")

    allHiddenBones : BoolProperty(default=False, name="Include All hidden bones",
        description="Copy Weights from all hidden Bones. If not set, then copy only from selected Bones")

    cleanVerts : BoolProperty(default=False, name="Clean Targets",
        description="Clean Target vertex Groups before performnig the copy action")




    def invoke(self, context, event):
        meshProps = context.scene.MeshProp
        self.submeshInterpolation = meshProps.submeshInterpolation
        ob = bpy.context.object
        me = ob.data
        if ob.mode=='EDIT' or me.use_paint_mask_vertex or me.use_paint_mask:
            self.onlySelectedVerts = True
        else:
            self.onlySelectedVerts = False
        return self.execute(context)

    def execute(self, context):
        meshProps = context.scene.MeshProp

        try:
            obj       = context.object
            armobj    = obj.find_armature()
            boneNames = get_bones_from_armature(armobj, self.allVisibleBones, self.allHiddenBones)
            sources = context.selected_objects
            copyBoneWeightsToSelectedBones(obj, sources, boneNames, self.submeshInterpolation, allVerts=not self.onlySelectedVerts, clearTargetWeights=self.cleanVerts)
            msg = create_message(self, context, "Copied%sweights from visible siblings and %s Weight Groups")
            self.report({'INFO'}, msg)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}
            
class ButtonWeldWeightsFromRigged(bpy.types.Operator):
    bl_idname = "avastar.weld_weights_from_rigged"
    bl_label = "Weld to Rigged"
    bl_description = messages.avastar_weld_weights_from_rigged_description
    bl_options = {'REGISTER', 'UNDO'}

    submeshInterpolation : g_submeshInterpolation

    onlySelectedVerts : BoolProperty(default=True, name="Only selected vertices",
        description="Copy weights only to selected vertices in the target mesh")

    allVisibleBones : BoolProperty(default=True, name="Include all visible bones",
        description="Copy Weights from all visbile Bones. If not set, then copy only from selected Bones")

    allHiddenBones : BoolProperty(default=False, name="Include All hidden bones",
        description="Copy Weights from all hidden Bones. If not set, then copy only from selected Bones")

    cleanVerts : BoolProperty(default=True, name="Clean Targets",
        description="Clean Target vertex Groups before performnig the copy action")


    @staticmethod  
    def weld_weights_from_rigged(context,
            onlySelectedVerts,
            cleanVerts,
            submeshInterpolation=True,
            allVisibleBones=True,
            allHiddenBones=True
        ):
        meshProps = context.scene.MeshProp

        try:
            obj       = context.object
            armobj    = obj.find_armature()
            
            boneNames = get_bones_from_armature(armobj, allVisibleBones, allHiddenBones)
            omode     = util.ensure_mode_is('EDIT')
            sources = util.get_animated_meshes(context, armobj)
            copyBoneWeightsToSelectedBones(obj, sources, boneNames, submeshInterpolation, allVerts=not onlySelectedVerts, clearTargetWeights=cleanVerts)
            return 'FINISHED'
        except Exception as e:
            util.ErrorDialog.exception(e)
            return 'CANCELLED'


    def invoke(self, context, event):

        self.onlySelectedVerts    = True
        self.cleanVerts           = True
        self.submeshInterpolation = True
        self.allVisibleBones      = True
        self.allHiddenBones       = True
        return self.execute(context)


    def execute(self, context):
        meshProps = context.scene.MeshProp
        status = ButtonWeldWeightsFromRigged.weld_weights_from_rigged(
            context,
            self.onlySelectedVerts,
            self.cleanVerts,
            self.submeshInterpolation,
            self.allVisibleBones,
            self.allHiddenBones
        )
       
        if status == 'FINISHED':
            msg = create_message(self, context, "Copied%sweights from visible siblings and %s Weight Groups")
            self.report({'INFO'}, msg)
        
        return {status}



class ButtonEnsureMirrorGroups(bpy.types.Operator):
    bl_idname = "avastar.ensure_mirrored_groups"
    bl_label = "Add missing Mirror Groups"
    bl_description = "Create empty mirror Vertex Groups if they not yet exist"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        count = util.add_missing_mirror_groups(context)
        name = context.object.name
        if count == -1:
            msg = "Could not create Symmetry Groups for %s" % name
        elif count == 0:
            msg = "%s has all necessary groups" % name
        else:
            msg = "Added %d Symmetry groups to %s" % (count, name)

        self.report({'INFO'}, msg)
        return{'CANCELLED'} if count < 0 else {'FINISHED'}


class ButtonRemoveGroups(bpy.types.Operator):
    bl_idname = "avastar.remove_empty_groups"
    bl_label = "Remove Groups"
    bl_description = "Remove all Groups with no weights assigned"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        obj      = context.object
        scene    = context.scene
        groups   = {}
        me       = obj.to_mesh(preserve_all_data_layers=True)
        vertices = me.vertices


        for v in vertices:
            for group in v.groups:
                if not group.group in groups:
                    groups[group.group] = group


        for group in [ group for group in obj.vertex_groups if group.index not in groups.keys()]:
            obj.vertex_groups.active_index=group.index
            bpy.ops.object.vertex_group_remove()

        return{'FINISHED'}


def get_weight_distribution(v, from_group, to_group):
    fg = None
    tg = None

    for g in v.groups:
        if g.group == from_group.index:
            fg = g
        elif g.group == to_group.index:
            tg = g

    fw = fg.weight if fg else 0
    tw = tg.weight if tg else 0

    return fw, tw

def set_weight(v, fg, fw, tg, tw):
    if fg: fg.add([v.index], fw, 'REPLACE')
    if tg: tg.add([v.index], tw, 'REPLACE')


def distribute_weight(v, fg, tg, percent, threshold, pgroup=None, dbg=""):
    if percent < 0 or percent > 1:
        log.warning("Fitting can not adjust vert %d (%s - %s) out of range:(%g) msg:%s " % (v.index, fg.name, tg.name, percent, dbg))
        percent=max(0,percent)
        percent=min(1,percent)
    fw, tw = get_weight_distribution(v, fg, tg)
    sum = fw + tw


    if  sum > threshold:
        fw = sum * percent
        tw = sum - fw


        set_weight(v, fg, fw, tg, tw)
        if pgroup is not None:
            pgroup[str(v.index)] = fw

    return fw, tw

def set_shapekey_mute(tgt, mute, only_active=False):
    mute_state = {}
    if only_active:
        sk = tgt.active_shape_key
        if sk:
            mute_state[sk.name]=sk.mute
            sk.mute=mute
    else:
        for index, sk in enumerate(tgt.data.shape_keys.key_blocks):
            if index > 0 and sk.name not in ["neutral_shape","bone_morph"]:
                mute_state[sk.name]=sk.mute
                sk.mute=mute
    return mute_state

def restore_shapekey_mute(tgt, keys):
    for key in keys.keys():
        kb, is_new = get_key_block_by_name(tgt, key, readonly=True)
        if kb:
            kb.mute = keys[key]

def get_shapekey_data(obj,block):
    block_data  = [0.0]*3*len(obj.data.vertices)
    block.data.foreach_get('co',block_data)
    return block_data

def rebase_shapekey(obj, key_name, relative_name):
    skeys = obj.data.shape_keys
    blocks = skeys.key_blocks
    sk = blocks[key_name]
    rk = blocks[relative_name]
    from_data   = get_shapekey_data(obj, sk.relative_key)
    to_data     = get_shapekey_data(obj, rk)
    block_data  = get_shapekey_data(obj, sk)

    print("Rebase %s from %s to %s" % (sk.name, sk.relative_key.name, rk.name) )

    for i in range(len(obj.data.vertices)):
        for c in range(3):
            ii = 3*i+c
            block_data[ii] += to_data[ii] - from_data[ii]
    sk.data.foreach_set('co',block_data)
    sk.relative_key = rk

def rebase_shapekeys(obj, from_name, to_name):
    try:
        skeys = obj.data.shape_keys
        blocks = skeys.key_blocks
        from_relative = blocks[from_name]
        to_relative   = blocks[to_name]
    except:
        return None

    from_data     = get_shapekey_data(obj, from_relative)
    to_data       = get_shapekey_data(obj, to_relative)

    keys = []
    for index, sk in enumerate(blocks):
         if index > 0 and sk.relative_key == from_relative and sk != to_relative:
            rebase_shapekey(obj, sk.name, to_name)
            keys.append(sk.name)
    return keys

def get_key_block_by_name(tgt, key_block_name, readonly=False):
    skeys = tgt.data.shape_keys
    if skeys and skeys.key_blocks and key_block_name in skeys.key_blocks:
        sk = skeys.key_blocks[key_block_name]
        is_new = False
    elif readonly:
        sk = None
        is_new = True
    else:
        sk = tgt.shape_key_add(key_block_name)
        is_new = True
    return sk, is_new

def get_corrective_key_edit_state(ob):
    editing = False
    if 'editing_corrective_shapekey' in ob:
        try:
            dict  = ob['editing_corrective_shapekey']
            name  = dict["name"]
            index = dict["index"]
            ak    = ob.active_shape_key
            ai    = ob.active_shape_key_index

            kb, is_new = shapekeys.get_key_block_by_name(ob, name, readonly=True)
            if kb or ai == index or key==ak:
                editing = True
        except:
            pass
    return editing

def get_closest_point_of_path(obj, p, p0, p1, stepcount=50):
    loc = None
    nor = None
    i   = -1

    path    = p1-p0

    mindist = None
    minloc  = None
    mini    = -1

    close_to_shape_dist = None
    close_to_shape_loc  = None
    close_to_shape_mini = -1

    for f in range(stepcount+1):
        probe = p0+(f/stepcount) * path
        status, loc, nor, i = util.closest_point_on_mesh(obj, probe)
        if i != -1:
            dist    = (probe-loc).magnitude
            cs_dist = (p-loc).magnitude
            if mindist == None or dist < mindist:
                mindist = dist
                minloc  = probe
                mini    = i

            if close_to_shape_dist == None or cs_dist < close_to_shape_dist:
                close_to_shape_dist = cs_dist
                close_to_shape_loc  = probe
                close_to_shape_mini = i

    return minloc, mini, close_to_shape_loc, close_to_shape_mini

def smooth_weights(context, obj, bm, from_group, to_group, count=1, factor=0.5, threshold=0.00001, all_verts=True, rendertype='RAW'):
    arm = obj.find_armature()
    OM = obj.matrix_world


    shaped_mesh = util.getMesh(context, obj, rendertype, apply_mesh_rotscale=False, apply_armature=True, msg="S Shape ")
    shaped_mesh.name = "T_shaped"
    
    original_weights = {}

    shape_cos = {}
    for v in [v for v in shaped_mesh.vertices if all_verts or v.select]:
        fw, tw = get_weight_distribution(v, from_group, to_group)
        original_weights[v.index]=[fw,tw]
        if  fw+tw > threshold:
            shape_cos[v.index] = v.co.copy()
            distribute_weight(v, from_group, to_group, 0, threshold, dbg="1")


    shape.refresh_shape(context, arm, obj, graceful=True, only_weights=True)
    start_mesh = util.getMesh(context, obj, rendertype, apply_mesh_rotscale=False, apply_armature=True, msg="S Start ")
    start_mesh.name="T_start"
    start_cos = {}
    for index in shape_cos.keys():
        v = start_mesh.vertices[index]
        start_cos[v.index] = v.co.copy()
        distribute_weight(v, from_group, to_group, 1, threshold, dbg="2")


    shape.refresh_shape(context, arm, obj, graceful=True, only_weights=True)
    end_mesh = util.getMesh(context, obj, rendertype, apply_mesh_rotscale=False, apply_armature=True,   msg="S End   ")
    end_cos = {}
    for index in shape_cos.keys():
        v = end_mesh.vertices[index]
        end_cos[v.index] = v.co.copy()
        fw, tw = original_weights[v.index]
        set_weight(v, from_group, fw, to_group, tw)


    shape.refresh_shape(context, arm, obj, graceful=True, only_weights=True)
    bm.from_mesh(shaped_mesh)
    verts = [v for v in bm.verts if all_verts or v.select]

    for d in range(count):
        bmesh.ops.smooth_vert(bm, verts=verts, factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    target_cos   = {v.index:v.co.copy() for v in verts}

    util.update_view_layer(bpy.context)
    unsolved_verts = []
    pgroup = get_pgroup(obj, to_group.name, create=True)
    for index, co in shape_cos.items():
        v  = start_mesh.vertices[index]

        p  = Vector(target_cos[index]) # wanted location
        p0 = Vector(start_cos[index]) # fully classic
        p1 = Vector(end_cos[index]) # fully fitted
        l  = (p1-p0).magnitude

        if l > 0.001:
            fr       = (p-p0).project(p1-p0)
            fraction = fr.magnitude/l # Vector projection


            fraction = util.clamp_range(0,fraction,1)
            fw, tw = distribute_weight(v, from_group, to_group, fraction, threshold, pgroup=pgroup, dbg="3")
        else:
            unsolved_verts.append(index)


    shape.refresh_shape(context, arm, obj, graceful=True, only_weights=True)
    bpy.data.meshes.remove(start_mesh)
    bpy.data.meshes.remove(end_mesh)
    bpy.data.meshes.remove(shaped_mesh)

    return unsolved_verts


def distribute_weights(context, obj, from_group, to_group, threshold=0.00001, all_verts=True, rendertype='RAW'):
    arm = obj.find_armature()





    shaped_mesh = util.getMesh(context, obj, rendertype, apply_mesh_rotscale=False, msg="D Shape ")
    shaped_mesh.name = "T_shaped"



    



    shape_cos = {}
    original_weights = {}
    for v in [v for v in shaped_mesh.vertices if all_verts or v.select]:
        fw, tw = get_weight_distribution(v, from_group, to_group)
        original_weights[v.index]=[fw,tw]



        if  fw+tw > threshold:
            shape_cos[v.index] = v.co.copy()
            distribute_weight(v, from_group, to_group, 0, threshold, dbg="1")




    shape.refresh_shape(context, arm, obj, graceful=True)

    start_mesh = util.getMesh(context, obj, rendertype, apply_mesh_rotscale=False, msg="D Start ")
    start_mesh.name="T_start"
    start_cos = {}
    for index in shape_cos.keys():
        v = start_mesh.vertices[index]
        start_cos[v.index] = v.co.copy()

        distribute_weight(v, from_group, to_group, 1, threshold, dbg="2")




    shape.refresh_shape(context, arm, obj, graceful=True)

    end_mesh = util.getMesh(context, obj, rendertype, apply_mesh_rotscale=False, msg="D End   ")
    end_mesh.name="T_end"
    end_cos = {}
    for index in shape_cos.keys():
        v = end_mesh.vertices[index]
        end_cos[v.index] = v.co.copy()
        fw, tw = original_weights[v.index]
        set_weight(v, from_group, fw, to_group, tw)











    
    shape.refresh_shape(context, arm, obj, graceful=True)

    unsolved_verts = []
    pgroup = get_pgroup(obj, to_group.name, create=True)

    for index, co in shape_cos.items():
        v = start_mesh.vertices[index]
        p  = Vector(shape_cos[index])
        p0 = Vector(start_cos[index])
        p1 = Vector(end_cos[index])





        l = (p1-p0).magnitude
        if l > 0.001:
            status, loc, nor, i = util.ray_cast(obj, p0, p1)






            if i > -1:
                f = (loc-p0).magnitude
                fraction = f/l
                fw, tw = distribute_weight(v, from_group, to_group, fraction, threshold, pgroup=pgroup, dbg="3")




            else:
                print("no solution for vertex %d not fitted l:%f" % (index, l))

        else:
            unsolved_verts.append(index)
            print("vertex %d not fitted" % index)















    shape.refresh_shape(context, arm, obj, graceful=True)



    return unsolved_verts

def prepare_physics_weights(obj, bone_names):
    if not "physics" in obj:
        obj['physics'] = {}
    physics = obj['physics']
    for name in bone_names:
        vgroup = get_bone_group(obj, name, create=True)
        if not name in physics:
            physics[name]= get_weight_set(obj, vgroup, clear=True)

def scale_level(obj, strength, bone_names):
    scale = strength+1
    prepare_physics_weights(obj, bone_names)
    physics = obj['physics']
    pinch = 1
    if scale > 1:
        pinch = scale*scale
        scale = 1

    omode = util.ensure_mode_is("OBJECT", object=obj)
    for name in bone_names:
        vgroup = get_bone_group(obj, name, create=True)
        ggroup = physics[name]
        pgroup = get_weight_set(obj, vgroup, clear=False)
        keys = pgroup.keys() if len(pgroup)>0 else ggroup.keys()
        for index in keys:

            try:
                gw = ggroup[index]
            except:
                ggroup[index]=0
                gw = 0
            try:
                pw = pgroup[index]
            except:
                pgroup[index]=0
                pw = 0

            w = gw + pw
            pw = min(max((scale*w)**pinch,0),1)
            gw = min(max(w - pw, 0),1)
            vgroup.add([int(index)], pw, 'REPLACE')
            ggroup[index] = gw




    if scale == 0:
        util.removeWeightGroups(obj, bone_names)

    util.ensure_mode_is(omode, object=obj)

def get_weight_set(ob, vgroup, clear=False):
    weights = {}
    if vgroup:
        for index, vert in enumerate(ob.data.vertices):
            for group in vert.groups:
                if group.group == vgroup.index:
                    weights[str(index)] = group.weight if not clear else 0
    return weights

def get_pgroup(obj, cgroup_name, create=False):
    if not "fitting" in obj:
        if not create: return None
        obj['fitting'] = {}
    fitting = obj['fitting']
    if not cgroup_name in fitting:
        if not create: return None
        fitting[cgroup_name] = {}
    pgroup = fitting[cgroup_name]
    return pgroup

def set_fitted_strength(context, obj, cgroup_name, percent, only_selected, omode):

    selected_verts = obj.mode=='EDIT'
    cgroup       = get_bone_group(obj, cgroup_name, create=False)
    mgroup       = get_bone_partner_group(obj, cgroup_name, create=False)
    pgroup       = get_pgroup(obj, cgroup_name, create=True)
    active_group = obj.vertex_groups.active

    if active_group not in [mgroup,cgroup]:
        active_group  = cgroup
        
    mgroup_set  = get_weight_set(obj, mgroup)
    cgroup_set  = get_weight_set(obj, cgroup)


    vertices = obj.data.vertices
    for index, cw in cgroup_set.items():
        mw = mgroup_set[index] if index in mgroup_set else 0
        pw = pgroup[index]     if index in pgroup else 0
        sum = min(cw + mw,1)
        v = vertices[int(index)]


        mgroup_set[index] = sum

        if only_selected and v.select:
            pgroup[index]     = (1-percent) * sum






    if percent != 0 and cgroup == None:
        cgroup = get_bone_group(obj, cgroup_name, create=True)
    if percent != 1 and mgroup == None:
        mgroup = get_bone_partner_group(obj, cgroup_name, create=True)

    mg_counter = 0
    for index, w in mgroup_set.items():
        v = vertices[int(index)]
        if v.select or not only_selected:
            cw = w * percent
            mw = w - cw
            pw = pgroup[index] if index in pgroup else 0
            if pw != 0:

                cw = percent*(w - pw)
                mw = w - cw
                mg_counter += 1




            set_weight(v, mgroup, mw, cgroup, cw)


    
    if only_selected:
        if omode != 'OBJECT':
            obj.update_from_editmode()
    else:
        if percent == 0 and cgroup and len(pgroup) == 0:
            obj.vertex_groups.active_index=cgroup.index
            bpy.ops.object.vertex_group_remove()
        elif percent == 1 and mgroup and len(pgroup) == 0:
            obj.vertex_groups.active_index=mgroup.index
            bpy.ops.object.vertex_group_remove()
    return active_group



def setDeformingBones(armobj, bone_names, replace=False):
    print("setDeformingBones")
    bones = util.get_modify_bones(armobj)
    for bone in bones:
        if replace or bone.name in bone_names:
            bone.use_deform = bone.name in bone_names
        bone.layers[B_LAYER_DEFORM] = bone.use_deform


def disableDeformingBones(armobj, bone_names, replace=False):
    bones = util.get_modify_bones(armobj)
    for bone in bones:
        if replace or bone.name in bone_names:
            bone.use_deform = False
        bone.layers[B_LAYER_DEFORM] = bone.use_deform

def setDeformingBoneLayer(armobj, final_set, initial_set, context):

    bones = util.get_modify_bones(armobj)
    for name in initial_set:
        bone = bones.get(name)
        if bone:
            bone.layers[B_LAYER_DEFORM] =False
    for bone in bones:
        bone.layers[B_LAYER_DEFORM] = bone.name in final_set
    context.view_layer.update()

def update_fitting_panel(obj, vidx):
    print("Update fitting panel for %s:%s" % (obj.name, vidx) )

def find_active_vertex(bm):
    return None
    elem = bm.select_history.active
    print("elem is:",elem)
    if elem and isinstance(elem, bmesh.types.BMVert):
        return elem
    return None

edited_object       = None
active_vertex_index = None
active_group_index  = None

@persistent
def edit_object_change_handler(scene):

    global edited_object
    global active_vertex_index
    global active_group_index

    if util.handler_can_run(scene, check_ticker=True):
        log.debug("handler [%s] started" % "edit_object_change_handler")
    else:
        return

    context = bpy.context



    try:
        obj=context.edit_object
        if obj and obj.type=="MESH" and context.mode=="EDIT_MESH":
            me = obj.data








            #








            if obj.is_updated_data:
                bpy.context.object.update_from_editmode()
        else:
            edited_object       = None
            active_vertex_index = None
            active_group_index  = None
    except:
        pass

BONE_CATEGORIES = ['Head', 'Arm', 'Torso', 'Leg']        
SORTED_BASIC_BONE_CATEGORIES = {
    'Head' :[['HEAD','NECK']],
    'Arm'  :[['L_CLAVICLE', 'L_UPPER_ARM', 'L_LOWER_ARM', 'L_HAND'],['R_CLAVICLE', 'R_UPPER_ARM', 'R_LOWER_ARM', 'R_HAND']],
    'Torso':[['PELVIS', 'BELLY', 'CHEST']],
    'Leg'  :[['L_UPPER_LEG', 'L_LOWER_LEG', 'L_FOOT'],['R_UPPER_LEG', 'R_LOWER_LEG', 'R_FOOT']]
    }

MESH_TO_WITH_WEIGHT_MAP = {
    'hairMesh' : ['with_hair', 'hair'],
    'headMesh' : ['with_head', 'head'],
    'eyelashMesh' : [ 'with_eyelashes', 'eyelashes'],
    'eyeBallLeftMesh' : [ 'with_eyes', 'eyes'],
    'eyeBallRightMesh' : [ 'with_eyes', 'eyes'],
    'upperBodyMesh' : ['with_upper_body', 'upper body'],
    'lowerBodyMesh' : ['with_lower_body', 'lower body'],
    'skirtMesh' : ['with_skirt', 'skirt']
}
    
def get_prop_meta(obj):
    id = obj.get('mesh_id')
    return MESH_TO_WITH_WEIGHT_MAP.get(id) if id else None
 
class ButtonGenerateWeights(bpy.types.Operator):
    bl_idname = "avastar.generate_weights"
    bl_label = "Update Weight Maps"
    bl_description = "Create/Update Weight Maps\n\n"\
                   + "You must specify for which bones you want to get weights(above)\n"\
                   + "and from which sources you want to copy weights(below, if applicable)\n"
    bl_options = {'REGISTER', 'UNDO'}  

    focus  : FloatProperty(name="Focus", min=0.0, max=1.5, default=1.0, description="Bone influence offset (very experimental)")
    gain   : FloatProperty(name="Gain", min=0, max=10, default=1, description="Pinch Factor (level gain)")
    clean  : FloatProperty(name="Clean", min=0, max=1.0, description="remove weights < this value")
    limit  : BoolProperty(name="Limit to 4", default=True, description = "Limit Weights per vert to 4 (recommended)" )
    weightBoneSelection: g_weightBoneSelection    
    use_mirror_x : g_use_mirror_x
    clearTargetWeights : g_clearTargetWeights
    copyWeightsToSelectedVerts : g_copyWeightsToSelectedVerts
    keep_groups : g_keep_groups

    suppress_implode : BoolProperty(name="Suppress Implode", default=False, description = "Do not move the Bones back after weighting (for demonstration purposes only, please dont use!)" )

    weight_base_bones : g_weight_base_bones
    weight_eye_bones : g_weight_eye_bones
    weight_alt_eye_bones : g_weight_alt_eye_bones
    weight_face_bones : g_weight_face_bones
    weight_groin : g_weight_groin
    weight_visible : g_weight_visible
    weight_tale : g_weight_tale
    weight_wings : g_weight_wings
    weight_hinds : g_weight_hinds
    weight_hands : g_weight_hands
    weight_volumes : g_weight_volumes

    submeshInterpolation : g_submeshInterpolation
    with_hidden_avastar_meshes : g_with_hidden_avastar_meshes
    with_listed_avastar_meshes : g_with_listed_avastar_meshes
    with_hair : g_with_hair
    with_head : g_with_head
    with_eyes : g_with_eyes
    with_eyelashes : g_with_eyelashes
    with_upper_body : g_with_upper_body
    with_lower_body : g_with_lower_body
    with_skirt : g_with_skirt
    
    def draw(self, context):
        props = context.scene.MeshProp
        skelProp = context.scene.SkeletonProp
        type = props.weightSourceSelection
        layout = self.layout

        if type == 'FACEGEN':
            box = layout.box()
            box.label(text="Facegen Parameters")
            col = box.column(align=True)
            col.prop(self,"focus", text='Focus')
            col.prop(self,"gain",  text='Gain')
            col.prop(self,"clean", text='Clean')
            col.separator()
            col.prop(self, 'limit')
            col.prop(self, 'use_mirror_x')
            col.prop(self,'weightBoneSelection')

            armobj = util.get_armature_from_context(context)
            rig_sections, excludes = assign_extended_section(skelProp, weight_sources=props.weightSourceSelection)
            selected_count = get_selected_bone_count(armobj, self.weightBoneSelection, rig_sections, excludes)
            enabled_count = get_enabled_bone_count(armobj, rig_sections, excludes)
            ButtonGenerateWeights.add_bone_counter(col, selected_count, "face", "deform bone", "selected")

            if util.get_ui_level() > UI_ADVANCED:
                col.prop(self, 'suppress_implode')

    @classmethod
    def poll(self, context):
        val = context.object and context.object.type in ['MESH', 'ARMATURE']
        if not val:
            val=False

        return val

    @staticmethod
    def draw_fitting_section(context, layout):
        obj = context.object
        if not (obj and obj.type=='MESH') :
            return

        col = layout.column(align=True)
        armobj = obj.find_armature()
        if not armobj:
            return

        if not "avastar" in armobj:
            col.label(text="Object Not rigged to Avastar", icon=ICON_INFO)
            return

        if "avastar-mesh" in obj:
            col.operator("avastar.convert_to_custom", icon=ICON_FREEZE)
            return

        if  obj.mode not in ['WEIGHT_PAINT', 'EDIT']:
            box=col.box()
            col=box.column(align=True)
            col.alert=True
            col.label(text='This panel can only be used')
            col.label(text='in Weight Paint Mode and')
            col.label(text='in Edit Mode')
            col.separator()
            col.alert=False
            col.enabled=True
            col.operator("avastar.bone_preset_fit", text="Adjust Viewport", icon = ICON_MODIFIER )
            return

        if not obj.ObjectProp.fitting:
            if has_collision_volumes(obj.vertex_groups.keys()):
                box = col.box()
                ccol = box.column(align=True)
                ccol.label(text="This mesh has Fitted Mesh Data.")
                ccol.label(text="Initialising this panel will")
                ccol.label(text="alter the weight distribution!")
                ccol.prop(obj.ObjectProp, 'fitting', text="Confirm Initialisation")
                return

        bones = armobj.data.bones        

        last_select = bpy.types.AVASTAR_MT_fitting_presets_menu.bl_label
        row = col.row(align=True)
        row.menu("AVASTAR_MT_fitting_presets_menu", text=last_select )
        row.operator("avastar.fitting_presets_add", text="", icon=ICON_ADD)
        if last_select not in ["Fitting Presets", "Presets"]:
            row.operator("avastar.fitting_presets_update", text="", icon=ICON_FILE_REFRESH)
            row.operator("avastar.fitting_presets_remove", text="", icon=ICON_REMOVE).remove_active = True

        
        if not context.scene.SceneProp.panel_appearance_enabled:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="To see the Fitting Sliders")
            col.label(text="you need to enable")
            col.label(text="'SL Avatar Shape'")
            col.label(text="in the Skinning Panel")
            return

        col = layout.column(align=True)
        col.prop(obj.FittingValues, "auto_update", text='Apply immediately', toggle=False)

        col = layout.column(align=True)
        col.label(text="Physics Strength:")
        col = layout.column(align=True)

        physics = obj['physics'] if 'physics' in obj else None

        row = col.row(align=True)
        row.operator("avastar.generate_physics")
        if not physics:
            row = col.row(align=True)
            row.operator("avastar.enable_physics")
        else:
            row.operator("avastar.delete_physics", text="", icon=ICON_X)

            row = col.row(align=True)
            row.prop(obj.FittingValues, "butt_strength"  , slider=True)
            selected = bones['BUTT'].select
            icon = ICON_LAYER_ACTIVE if selected else ICON_CHECKBOX_DEHLT
            p=row.operator("avastar.fitting_bone_selected_hint", text="", icon=icon)
            p.bone ='BUTT'
            p.bone2=''
            row.enabled = 'BUTT' in physics

            row = col.row(align=True)
            row.prop(obj.FittingValues, "pec_strength"   , slider=True)
            selected = bones['LEFT_PEC'].select or bones['RIGHT_PEC'].select
            bone = context.active_pose_bone
            if bone:
                if bone.name == 'RIGHT_PEC':
                    icon_value = get_icon("rightside")
                elif bone.name == 'LEFT_PEC':
                    icon_value = get_icon("leftside")
                else:
                    icon_value = get_icon(ICON_CHECKBOX_DEHLT)
            else:
                icon_value = get_icon(ICON_CHECKBOX_DEHLT)
            p = row.operator("avastar.fitting_bone_selected_hint", text="", icon_value=icon_value)
            p.bone ='RIGHT_PEC'
            p.bone2='LEFT_PEC'
            row.enabled = 'RIGHT_PEC' in physics or 'LEFT_PEC' in physics

            row = col.row(align=True)
            row.prop(obj.FittingValues, "back_strength"  , slider=True)
            selected = bones['LOWER_BACK'].select or bones['UPPER_BACK'].select
            icon = ICON_LAYER_ACTIVE if selected else ICON_CHECKBOX_DEHLT
            p=row.operator("avastar.fitting_bone_selected_hint", text="", icon=icon)
            p.bone ='UPPER_BACK'
            p.bone2='LOWER_BACK'
            row.enabled = 'UPPER_BACK' in physics or 'LOWER_BACK' in physics

            row = col.row(align=True)
            row.prop(obj.FittingValues, "handle_strength", slider=True)
            selected = bones['LEFT_HANDLE'].select or bones['RIGHT_HANDLE'].select
            bone = context.active_pose_bone
            if bone:
                if bone.name == 'RIGHT_HANDLE':
                    icon_value = get_icon("rightside")
                elif bone.name == 'LEFT_HANDLE':
                    icon_value = get_icon("leftside")
                else:
                    icon_value = get_icon(ICON_CHECKBOX_DEHLT)
            else:
                    icon_value = get_icon(ICON_CHECKBOX_DEHLT)

            p=row.operator("avastar.fitting_bone_selected_hint", text="", icon_value=icon_value)
            p.bone ='RIGHT_HANDLE'
            p.bone2='LEFT_HANDLE'
            row.enabled = 'RIGHT_HANDLE' in physics or ICON_LEFT_HANDLE in physics

        col = layout.column(align=True)
        label = "Bone Fitting Strength:"
        if (context.scene.SceneProp.panel_preset!='FIT'):
            col.separator()
            row = col.row(align=True)
            row.label(text=label)
            row.operator("avastar.bone_preset_fit", text="Adjust Viewport", icon = ICON_MODIFIER )
        else:
            col.label(text=label)

        col = layout.column(align=True)

        row = col.row(align=True)
        row.prop(obj.FittingValues,"boneSelection", expand=True)

        active_group = obj.vertex_groups.active
        for key in BONE_CATEGORIES:
            bone_sets = SORTED_BASIC_BONE_CATEGORIES[key]
            for set in bone_sets:

                for bname in set:
                    pname = get_bone_partner(bname)
                    display = obj.FittingValues.boneSelection == 'ALL'
                    selected = bones[bname].select or bones[pname].select
                    active   = bones[bname] == bones.active or bones[pname] == bones.active
                    ansel    = active and selected
                    icon = ICON_LAYER_ACTIVE if ansel else ICON_LAYER_USED if selected else ICON_BLANK1

                    if (not display) and (obj.FittingValues.boneSelection == 'SELECTED'):
                        display = selected
                    if (not display) and (obj.FittingValues.boneSelection == 'WEIGHTED'):
                        display = bname in obj.vertex_groups or pname in obj.vertex_groups
                    if (not display) and active_group:
                        display = (bname == active_group.name or bname == get_bone_partner(active_group.name))
                    if display:
                        display_name = bname if bones[bname].select else pname
                        label = get_bone_label(bname)
                        bone_type = ICON_CHECKBOX_DEHLT if not selected else 'mbone' if display_name[0]=='m' else 'vbone'
                        icon_value = get_icon(bone_type) 
                        row = col.row(align=True)
                        row.prop(obj.FittingValues, bname, slider=True, text=label)
                        p       = row.operator("avastar.fitting_bone_selected_hint", text="", icon_value=icon_value)
                        p.bone  = bname
                        p.bone2 = ''
                        
                        pgroup = get_pgroup(obj, bname)
                        count  = len(pgroup) if pgroup != None else 0
                        icon   = ICON_LOAD_FACTORY if count > 0 else ICON_BLANK1
                        p      = row.operator("avastar.fitting_bone_delete_pgroup", text="", icon=icon)
                        p.bname = bname


        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("avastar.distribute_weights", icon=ICON_SHAPEKEY_DATA)
        row.operator("avastar.smooth_weights", icon=ICON_MOD_SMOOTH)


    @staticmethod
    def display_weights_from_meshes(context, armobj, prop, layout, weight_source_type, is_redo=False):
        altprop = context.scene.MeshProp
        with_hidden_avastar_meshes = get_property_from('with_hidden_avastar_meshes', prop, altprop, default=None)
        with_listed_avastar_meshes = get_property_from('with_listed_avastar_meshes', prop, altprop, default=None)
        box = layout
        box.label(text="Copy Weight from ...", icon=ICON_GROUP_VERTEX)
        col = box.column(align=True)

        only_visible = not with_hidden_avastar_meshes
        meshes = util.get_animated_meshes(context, armobj, only_visible=only_visible)
        if weight_source_type == 'COPY':
            available_meshes = [ob for ob in meshes if ob!=context.object]
        else:
            available_meshes = {}
            for obj in meshes:
                meta = get_prop_meta(obj)
                if meta:
                    if available_meshes.get(meta[0]):
                        continue
                    available_meshes[meta[0]]=obj
            available_meshes = available_meshes.values()

        if len(available_meshes) > 0:
            mesh_list = context.window_manager.MeshesPropList
            mesh_list.clear()

            selected_mesh_count = 0
            for ob in available_meshes:
                lprop = mesh_list.add()
                lprop.select= util.object_select_get(ob)
                lprop.name=ob.name
                if ob.ObjectProp.is_selected:
                    selected_mesh_count += 1

            col.template_list('AVASTAR_UL_MeshesPropVarList',
                              'MeshesPropList',
                               bpy.context.window_manager,
                              'MeshesPropList',
                               bpy.context.window_manager.MeshesIndexProp,
                              'index',
                              rows=4)
            col.enabled = not is_redo
            bpy.context.window_manager.MeshesIndexProp.index=-1
            can_run = selected_mesh_count > 0 or with_listed_avastar_meshes
        else:
            col.alert=True
            col.label(text="No %s Weight Sources in Rig" % ("visible " if only_visible else ""))
            col.alert=False
            can_run=False

        col.separator()
        col.prop(prop, 'with_listed_avastar_meshes', toggle=False)
        col.prop(prop, 'with_hidden_avastar_meshes', toggle=False)
        col = box.column(align=True)
        col.label(text="Note: All listed sources influence")
        col.label(text="the final weights even when not selected!")

        return can_run

    @staticmethod
    def add_bone_counter(col, count, destination, type, marked):
        col.alignment='RIGHT'
        if count > 0:
            col.label(text="%d %s %s %s" % (count, destination, util.pluralize(type, count=count), marked))
        else:
            col.alert=True
            col.label(text="No %s %s %s" % (destination, type, marked), icon=ICON_HAND)
            col.alert=False
    
    @staticmethod
    def weightmap_copy_panel_draw(armobj, context, box, op=None, with_opcall=True):
        
        def get_label_from_selection(selection):
            if selection == 'SELECTED':
                return 'selected'
            if selection == 'VISIBLE':
                return "visible"
            return "enabled"

        if not op:
            op = context.scene.MeshProp
        can_run = True
        skelProp = context.scene.SkeletonProp

        weightBoneSelection = get_property_from('weightBoneSelection', op, context.scene.MeshProp, default=None)
        weightSourceSelection = get_property_from('weightSourceSelection', op, context.scene.MeshProp, default=None)
        weight_mapping = get_property_from('weight_mapping', op, context.scene.MeshProp, default=None)

        rig_sections, excludes = assign_extended_section(skelProp, weight_sources=weightSourceSelection)
        selected_count = get_selected_bone_count(armobj, weightBoneSelection, rig_sections, excludes)
        enabled_count = get_enabled_bone_count(armobj, rig_sections, excludes)

        strategy_box = box.box()
        col = strategy_box.column(align=True)
        col.prop(op, "weightSourceSelection", toggle=True)
        if weightSourceSelection in ['COPY']:
            col.prop(op, "weight_mapping")
            col.enabled=True

        selection_box = box.box()
        if weightSourceSelection != 'COPY':
            col = selection_box.column(align=True)
            col.prop(op, "weightBoneSelection", toggle=False)
            if weightSourceSelection == 'FACEGEN':
                ButtonGenerateWeights.add_bone_counter(col, selected_count, "face", "deform bone", "selected")
            else:
                if selected_count > -1:
                    status= get_label_from_selection(weightBoneSelection)
                    ButtonGenerateWeights.add_bone_counter(col, selected_count, status, "bone", "used")
                if enabled_count > -1:
                    ButtonGenerateWeights.add_bone_counter(col, enabled_count, "deform", "bone", "enabled")
            
            if weightSourceSelection in ['EMPTY','AUTOMATIC']:
                draw_include_binding(selection_box, skelProp, weightBoneSelection, armobj.RigProp.RigType)
            can_run = (enabled_count != 0 and selected_count != 0)

        if weightSourceSelection in ['COPY', 'AVASTAR', 'EXTENDED']:
            can_run = ButtonGenerateWeights.display_weights_from_meshes(context, armobj, op, selection_box, weightSourceSelection)

        if True:#weightSourceSelection != 'COPY' or weight_mapping != 'POLYINTERP_AVASTAR':
            option_box = box.box()
            option_box.label(text="Options")
            col = option_box.column(align=True)
            if weightSourceSelection != 'COPY':
                col.prop(op, 'use_mirror_x')
            
            if weightSourceSelection not in ['EMPTY']:
                col.prop(op, "keep_groups", toggle=False)
                col = option_box.column(align=True)
                col.prop(op, "clearTargetWeights", toggle=False)
                col.enabled = not op.copyWeightsToSelectedVerts
                col = option_box.column(align=True)
                col.prop(op, "copyWeightsToSelectedVerts", toggle=False)

        col = box.column(align=True)
        col.enabled = can_run
        col.alert = not can_run
        txt = "Update Weights" if can_run else "No valid source selected"
        col.operator(ButtonGenerateWeights.bl_idname, text=txt, icon=ICON_PREFERENCES)
    

    def weightmap_bind_panel_draw(armobj, context, box, op=None, is_redo=False):
        if not op:
            op = context.scene.MeshProp

        can_run = True
        skelProp = context.scene.SkeletonProp
    
        weightBoneSelection = get_property_from('weightBoneSelection', op, context.scene.MeshProp, default=None)
        rig_sections, excludes = assign_extended_section(skelProp)
        selected_count = get_selected_bone_count(armobj, weightBoneSelection, rig_sections, excludes)
        enabled_count = get_enabled_bone_count(armobj, rig_sections, excludes)

        strategy_box = box.box()
        col = strategy_box.column(align=True)
        col.prop(op, "bindSourceSelection", toggle=True)
        col.enabled = not is_redo
        col = strategy_box.column(align=True)

        if op.bindSourceSelection in ['COPY']:
            col.prop(op, "weight_mapping")
            col.enabled=True
            can_run = ButtonGenerateWeights.display_weights_from_meshes(context, armobj, op, box, op.bindSourceSelection, is_redo=is_redo)

        if op.bindSourceSelection not in ['EMPTY', 'NONE']:
            option_box = box.box()
            option_box.label(text="Options")
            col = option_box.column()
            if op.bindSourceSelection in ["AUTOMATIC"]:
                col.prop(skelProp, "weight_visible", text="Only Visible Bones", toggle=False)
                col.prop(skelProp, "weight_groin", text="Include Groin", toggle=False)
            col.prop(op, "keep_groups", toggle=False)
            col.prop(op, "clearTargetWeights", toggle=False)

        return can_run


    def assign_avastar_meshes(self, context):
        props = context.scene.MeshProp
        self.with_hair = props.with_hair
        self.with_eyes = props.with_eyes
        self.with_eyelashes = props.with_eyelashes
        self.with_head = props.with_head
        self.with_lower_body = props.with_lower_body
        self.with_upper_body = props.with_upper_body
        self.with_skirt = props.with_skirt
        self.with_hidden_avastar_meshes = props.with_hidden_avastar_meshes
        self.with_listed_avastar_meshes = props.with_listed_avastar_meshes
        
    def invoke(self, context, event):
        meshobj = context.object
        armobj = util.get_armature(meshobj)
        props = context.scene.MeshProp
        skelProps = context.scene.SkeletonProp
        self.use_mirror_x = props.use_mirror_x
        self.clearTargetWeights = props.clearTargetWeights
        self.copyWeightsToSelectedVerts = props.copyWeightsToSelectedVerts
        self.keep_groups = props.keep_groups
        self.weightBoneSelection = props.weightBoneSelection


        assign_weight_properties(self, skelProps)

        if armobj:
            shape.ensure_drivers_initialized(armobj)
            if props.weightSourceSelection == 'FACEGEN':
                pbone = armobj.data.bones.active
                if pbone:
                    self.focus  = pbone['focus'] if 'focus' in pbone else 1.0
                    self.gain   = pbone['gain']  if 'gain'  in pbone else 1.0
                    self.clean  = pbone['clean'] if 'clean' in pbone else 0.0

        return self.execute(context)

    def execute(self, context):

        failcount=0
        donecount=0
        props = context.scene.MeshProp
        active = context.object
        amode = active.mode if active else None

        props.weightBoneSelection = self.weightBoneSelection
        store_handlers_disabled_state = util.set_disable_handlers(context.scene, True)

        for target in [ ob for ob in context.selected_objects if ob.type=='MESH']:
            
            armobj = util.get_armature(target)

            if not armobj:
                self.report({'ERROR'},'"%s" is not rigged' % context.object.name)
                failcount += 1
                continue

            if not util.object_visible_get(armobj, context=context):
                self.report({'ERROR'},'Make Armature "%s" visible and try again' % armobj.name)
                failcount += 1
                continue

            util.set_active_object(context, target)
            if props.weightSourceSelection != 'FACEGEN':
                done = self.copy_weightmaps(context, armobj, target)
            else:
                done = rig.AvastarFaceWeightGenerator.generate(context, self.use_mirror_x, self.focus, self.gain, self.clean, self.limit, self.suppress_implode, self.weightBoneSelection)
                pbone = armobj.data.bones.active
                if pbone:
                    pbone['focus']  = self.focus
                    pbone['gain']   = self.gain
                    pbone['clean']  = self.clean
            if done:
                donecount += 1
            else:
                failcount+=1

        util.set_disable_handlers(context.scene, store_handlers_disabled_state)
        if  props.weightSourceSelection == 'FACEGEN':
            util.set_active_object(context, target if target else active)
        elif active:
            util.set_active_object(context, active)
            util.set_object_mode(amode)

        util.update_view_layer(context)
        return {'FINISHED'}

    def copy_weightmaps(self, context, armobj, target):

        def clean_vertex_weights(target, armobj):

            animation_groups = [g for g in target.vertex_groups if g.name in armobj.data.bones]
            if target.vertex_groups.active:
                active_group_name = target.vertex_groups.active.name 
            else:
                active_group_name = None

            for g in animation_groups:
                bpy.ops.object.vertex_group_set_active(group=g.name)
                bpy.ops.object.vertex_group_remove_from()

            if active_group_name:
                bpy.ops.object.vertex_group_set_active(group=active_group_name)
            
        meshProps = context.scene.MeshProp
        skeletonProps = context.scene.SkeletonProp
        use_selected_bones = meshProps.weightBoneSelection == 'SELECTED'
        use_visible_bones = meshProps.weightBoneSelection == 'VISIBLE'

        active=context.object
        copyWeightsToSelectedVerts = meshProps.copyWeightsToSelectedVerts and target.mode in ['EDIT', 'WEIGHT_PAINT']
        clearTargetWeights = meshProps.clearTargetWeights
        if active == target and (copyWeightsToSelectedVerts or clearTargetWeights):

            selected_vert_indices = [v.index for v in active.data.vertices if v.select]

            mx=active.data.use_mirror_x
            my=active.data.use_mirror_y
            mz=active.data.use_mirror_z

            omode = util.ensure_mode_is('EDIT')
            if clearTargetWeights:
                for v in target.data.vertices:
                    v.select=True

            armobj = util.get_armature(target)
            clean_vertex_weights(target, armobj)

            for v in target.data.vertices:
                v.select=False

            for index in selected_vert_indices:
                target.data.vertices[index].select=True

            active.update_from_editmode()
            util.ensure_mode_is(omode)

            active.data.use_mirror_x=mx
            active.data.use_mirror_y=my
            active.data.use_mirror_z=mz

        cactive, cmode = util.change_active_object(context, armobj, new_mode="POSE", msg="copy weightMaps 1:")

        active_bone = armobj.data.bones.active
        arm_original_mode = util.ensure_mode_is("POSE", object=armobj)
        odata_layers = [armobj.data.layers[B_LAYER_VOLUME], armobj.data.layers[B_LAYER_SL], armobj.data.layers[B_LAYER_EXTENDED]]

        original_pose = armobj.data.pose_position
        armobj.data.pose_position="REST"
        util.ensure_mode_is("OBJECT", object=armobj)
        util.ensure_mode_is("POSE", object=armobj)

        rig_sections, excludes = assign_extended_section(self)
        weighted_bones = data.get_deform_bones(
            armobj,
            rig_sections,
            excludes,
            use_visible_bones,
            use_selected_bones,
            self.use_mirror_x
            )
        log.warning("+- Copy Weight Maps ----------------------------------")
        log.warning("|  Weight target is %s:%s" % (armobj.name, target.name) )
        bone_select_info = util.get_pose_bone_select(armobj, weighted_bones)
        original_mode = util.ensure_mode_is('WEIGHT_PAINT', object=target)

        wcontext = setup_weight_context(self, context, armobj, copyWeightsToSelectedVerts=copyWeightsToSelectedVerts)
        wcontext.target = target
        wcontext.weighted_bones = weighted_bones
        wcontext.rig_sections = rig_sections
        wcontext.excludes = excludes
        wcontext.weightSourceSelection = meshProps.weightSourceSelection
        wcontext.clearTargetWeights = clearTargetWeights
        create_weight_groups(wcontext, for_bind=False)

        if not meshProps.weightSourceSelection in ["EMPTY", "NONE"] and not meshProps.keep_groups:
            util.removeEmptyWeightGroups(target)

        util.ensure_mode_is(original_mode, object=target)
        bpy.ops.avastar.reparent_mesh(object_name=target.name) #to pass in the generated weights

        util.setSelectOption(armobj,[])
        armobj.data.pose_position = original_pose
        util.set_active_object(context, armobj)

        util.ensure_mode_is("OBJECT", object=armobj)
        util.ensure_mode_is("POSE", object=armobj)
        util.ensure_mode_is(arm_original_mode, object=armobj)

        armobj.data.layers[B_LAYER_VOLUME]   = odata_layers[0]
        armobj.data.layers[B_LAYER_SL]       = odata_layers[1]
        armobj.data.layers[B_LAYER_EXTENDED] = odata_layers[2]
        if active_bone:
            armobj.data.bones.active = active_bone

        util.restore_pose_bone_select(armobj, bone_select_info)
        util.change_active_object(context, cactive, new_mode=cmode, msg="copy weightMaps 2:")
        log.warning("+-----------------------------------------------------")
        return True

class MeshesIndexPropGroup(bpy.types.PropertyGroup):
    index : IntProperty(name="index")

class MeshesProp(bpy.types.PropertyGroup):
    select : BoolProperty()
    name : StringProperty()

class AVASTAR_UL_MeshesPropVarList(bpy.types.UIList):

    def draw_item(self,
                  context,
                  layout,
                  data,
                  item,
                  icon,
                  active_data,
                  active_propname
                  ):
        ob=context.scene.objects[item.name]
        col = layout.column(align=True)
        row=col.row(align=True)
        row.prop(ob.ObjectProp,"is_hidden", text='', icon = ICON_HIDE_ON if ob.ObjectProp.is_hidden else ICON_HIDE_OFF, emboss=False)
        row.prop(ob,"hide_select", text='', emboss=False)
        if ob.hide_select:
            row.label(text=item.name, icon=ICON_BLANK1)
        else:
            row.prop(ob.ObjectProp,"is_selected", text=item.name)



class weight_context:
    def __init__(self, operator, context, target):
        self.operator = operator
        self.context = context
        self.target = target
        self.set_bone_options()
        self.set_copy_options(operator, context)

    def set_copy_options(self, op, context):
        props = context.scene.MeshProp
        self.weightSourceSelection = get_property_from('weightSourceSelection', op, props)
        self.bindSourceSelection = get_property_from('bindSourceSelection', op, props)
        self.copyWeightsToSelectedVerts = get_property_from('copyWeightsToSelectedVerts', op, props)
        self.keep_groups = get_property_from('keep_groups', op, props)
        self.clearTargetWeights = get_property_from('clearTargetWeights', op, props)
        self.weight_mapping =get_property_from('weight_mapping', op,  props)
        self.with_hidden_avastar_meshes = get_property_from('with_hidden_avastar_meshes', op, props)
        self.with_listed_avastar_meshes = get_property_from('with_listed_avastar_meshes', op, props)
        self.weight_sources = []

    def set_bone_options(self, bone_names=None, rig_sections=None, excludes=None):
        self.bone_names = bone_names
        self.rig_sections = rig_sections
        self.excludes = excludes

def get_property_from(key, group, altgroup, default=None):
    try:
        return getattr(group, key)
    except:
        try:
            return getattr(altgroup,key)
        except:
            return default

def setup_weight_context(self, context, armature, copyWeightsToSelectedVerts=None):
    meshProps = context.scene.MeshProp
    if copyWeightsToSelectedVerts == None:
        copyWeightsToSelectedVerts = get_property_from('copyWeightsToSelectedVerts', self, meshProps) 

    wcontext = weight_context(self, context, armature)
    wcontext.weightSourceSelection = get_property_from('weightSourceSelection', self, meshProps)
    wcontext.bindSourceSelection = get_property_from('bindSourceSelection', self, meshProps)
    wcontext.copyWeightsToSelectedVerts = copyWeightsToSelectedVerts 
    
    with_hidden_sources = wcontext.with_hidden_avastar_meshes
    with_listed_sources = wcontext.with_listed_avastar_meshes
    only_selected_sources = not(with_listed_sources if with_listed_sources != None else False)
    wcontext.weight_sources = setup_weight_sources(self, wcontext, context, armature)

    return wcontext

def setup_weight_sources(self, wcontext, context, armature):
    with_hidden_sources = wcontext.with_hidden_avastar_meshes
    with_listed_sources = wcontext.with_listed_avastar_meshes
    only_selected_sources = not(with_listed_sources if with_listed_sources != None else False)

    weight_sources = util.get_animated_meshes(
            context,
            armature,
            with_avastar=True,
            return_names=False,
            only_visible=not with_hidden_sources,
            only_selected=only_selected_sources,
            use_object_selector=True)

    return weight_sources
    

def do_smart_copy(
            operator,
            context,
            armobj,
            target,
            weight_sources,
            copy_type,
            bone_names,
            with_invisible_sources):

    copy_mesh_weights(
                operator,
                context,
                armobj,
                target,
                weight_sources,
                clearTargetWeights=True,
                weight_mapping='POLYINTERP_NEAREST',
                copy_type = copy_type,
                bone_names=bone_names,
                with_invisible_sources=with_invisible_sources,
                copyWeightsToSelectedVerts=False)

    copy_mesh_weights(
                operator,
                context,
                armobj,
                target,
                weight_sources,
                clearTargetWeights=False,
                weight_mapping='POLYINTERP_VNORPROJ',
                copy_type = copy_type,
                bone_names=bone_names,
                with_invisible_sources=with_invisible_sources,
                copyWeightsToSelectedVerts=False)

    omode=util.ensure_mode_is('WEIGHT_PAINT')
    try:
        bpy.ops.object.vertex_group_smooth(group_select_mode='BONE_DEFORM', factor=1, repeat=5)
    except:
        bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=1, repeat=5)
    util.ensure_mode_is(omode)


def create_weight_groups(wcontext, for_bind):
    
    operator = wcontext.operator
    context = wcontext.context
    target = wcontext.target
    bone_names = wcontext.weighted_bones
    rig_sections = wcontext.rig_sections
    excludes = wcontext.excludes
    copy_type = wcontext.weightSourceSelection if for_bind else wcontext.weightSourceSelection
    copyWeightsToSelectedVerts = wcontext.copyWeightsToSelectedVerts
    keep_empty_groups = wcontext.keep_groups
    clearTargetWeights = False if copyWeightsToSelectedVerts else wcontext.clearTargetWeights
    weight_mapping = wcontext.weight_mapping
    with_hidden_sources = wcontext.with_hidden_avastar_meshes
    with_listed_sources = wcontext.with_listed_avastar_meshes

    def sections_as_string(sections):
       result = []
       for section in sections:
           result.append(LAYER_NAMES.get(section,"%s"%section))
       return result








    active = util.get_active_object(context)
    util.set_active_object(context, target)
    original_mode = util.ensure_mode_is("OBJECT")
    with_invisible_sources = with_hidden_sources if with_hidden_sources != None else False
    only_selected_sources = not(with_listed_sources if with_listed_sources != None else False)



    
    if copy_type == 'EMPTY':
        util.createEmptyGroups(target, bone_names)

    elif copy_type in ['AUTOMATIC','ENVELOPES']:


        weightBoneSelection = context.scene.MeshProp.weightBoneSelection
        generateWeightsFromBoneSet(target, bone_names, copy_type, clearTargetWeights, copyWeightsToSelectedVerts, rig_sections, excludes, weightBoneSelection=weightBoneSelection)

        if not keep_empty_groups:

            c = util.removeEmptyWeightGroups(target)


    elif copy_type in ['COPY', 'AVASTAR']:

        armobj = util.get_armature(target)
        weight_sources = wcontext.weight_sources
        invisible_sources = [ob for ob in weight_sources if util.object_select_get(ob) and not util.object_visible_get(ob, context=context)]

        for ob in invisible_sources:
           util.set_object_hide(ob, False)



        if weight_mapping == 'POLYINTERP_AVASTAR':
            do_smart_copy(
                operator,
                context,
                armobj,
                target,
                weight_sources,
                copy_type,
                bone_names,
                with_invisible_sources)
        else:
            copy_mesh_weights(
                operator,
                context,
                armobj,
                target,
                weight_sources,
                clearTargetWeights,
                weight_mapping,
                copy_type = copy_type,
                bone_names=bone_names,
                with_invisible_sources=with_invisible_sources,
                copyWeightsToSelectedVerts=copyWeightsToSelectedVerts)

        for ob in invisible_sources:
           util.set_object_hide(ob, True)







    
    elif copy_type == 'SWAP':
        swapCollision2Deform(target, keep_groups=keep_empty_groups)

    util.ensure_mode_is(original_mode)
    util.set_active_object(context, active)



def copy_mesh_weights(operator,
        context,
        armobj,
        target,
        weight_sources,
        clearTargetWeights,
        weight_mapping,
        copy_type=None,
        bone_names=None,
        with_invisible_sources=False,
        copyWeightsToSelectedVerts=False):

    def backup_vertex_groups(obj):
        for group in obj.vertex_groups:
            group.name = "backup_%s"%group.name


    def restore_vertex_groups(obj):
        obsolete_vgroups = []
        for group in obj.vertex_groups:
            if not group.name.startswith("backup_"):
                obsolete_vgroups.append(group)

        for vgroup in obsolete_vgroups:
            obj.vertex_groups.remove(vgroup)

        for group in obj.vertex_groups:
            group.name = group.name.split("_")[1]

    def transfer_weights_to_selected(obj, arm):
        vgroups = obj.vertex_groups
        for v in [v for v in obj.data.vertices if v.select]:
            for source_vgroup in v.groups:
                source_index = source_vgroup.group
                try:
                    source_group = vgroups[source_index]
                except:
                    raise
                source_name = source_group.name
                if source_name.startswith("backup_"):
                    continue # this is not a source
                target_name = "backup_%s" % source_name
                if source_name not in arm.pose.bones:
                    continue # this is not a weight map
                target_group = vgroups.get(target_name)
                if not target_group:
                     target_group = obj.vertex_groups.new(name=target_name)
                target_index = target_group.index
                target_group.add([v.index], source_vgroup.weight, 'REPLACE')


    CHILD_ORIGINAL = 1
    CHILD_COPY = 0

    VS_DISTANCE = 0
    VS_DATA = 1
    VS_SOURCE = 2

    def is_enabled_source(obj, copy_type):
        return obj != target and is_visible(obj) and is_regular_mesh(obj) #and is_in_scene_layer(obj)

    def is_valid_source(obj, copy_type):
        return obj != target and (copy_type != 'AVASTAR' or "avastar-mesh" in obj)

    def is_visible(obj):
        return not util.object_hide_get(obj)

    def is_regular_mesh(obj):
        return not obj.name.startswith('CustomShape_')




    active = util.get_active_object(context)

    enabled_sources = [ob for ob in weight_sources if ob!=target and (is_visible(ob) or with_invisible_sources) ]
    log.warning("+- copy bone weights -----------------------------------------------------")
    log.warning("| Copy_type: %s" % (copy_type))
    log.warning("| enabled sources: %s" % ([s.name for s in enabled_sources]) )
    log.warning("| visible sources: %s" % ([s.name for s in enabled_sources if not util.object_visible_get(s, context=context)]) )
    log.warning("| target: %s" % target.name )
    log.warning("| armature: %s" % armobj.name )
    log.warning("| using %d bones" % (len(bone_names)) )
    log.warning("+-------------------------------------------------------------------------")

    if not armobj:
        operator.report({'WARNING'},"%s is not a Mesh target" % target.name)
        log.warning("+ no armature selected (abort)")
        return




    valid_sources = []
    tempobj = []
    other_mesh_count = 0
    for childobj in enabled_sources:

        other_mesh_count += 1

        if is_valid_source(childobj, copy_type):



            if len(childobj.data.vertices) == 0:
                operator.report({'WARNING'},"Mesh %s with 0 vertices can't be used as weight source"%(childobj.name))
                continue

            if copy_type == 'EXTENDED':
                part = childobj.name.split('.')[0]
                nob = get_extended_mesh(context, part)
                if nob:
                    print("Get extended weights from %s" % (nob.name) )
                    tempobj.append(nob)
                    childobj = nob
                else:
                    continue

            log.warning("| Add Weight Source Mesh: %s" % childobj.name)
            valid_sources.append(childobj)


    if len(valid_sources) == 0:
        if target:
            obname="[%s]"%target.name
        else:
            obname="your current Selection"

        if other_mesh_count == 0:
            if copy_type == 'AVASTAR':
                msg = msg_no_avastar_meshes_to_copy_from
            else:
                msg = msg_no_objects_to_copy_from
        else:
            msg = msg_no_weights_to_copy_from

        bpy.ops.avastar.generic_info_operator(
            msg=msg  % (obname, armobj.name),
            type=SEVERITY_WARNING
        )

        log.warning("+ "+msg + "(abort)")
        return

    util.update_view_layer(context)

    bpy.ops.object.select_all(action='DESELECT')
    for ob in valid_sources:
        util.object_select_set(ob, True)
    util.object_select_set(target, True)
    omode = util.ensure_mode_is('WEIGHT_PAINT', context=context)

    face_paint_mask = target.data.use_paint_mask
    vert_paint_mask = target.data.use_paint_mask_vertex

    target.data.use_paint_mask = False
    if copyWeightsToSelectedVerts:
        backup_vertex_groups(target)
        target.data.use_paint_mask_vertex = True

    bpy.ops.object.data_transfer(use_reverse_transfer=True,
                                    use_freeze=False,
                                    data_type='VGROUP_WEIGHTS',
                                    use_create=True,
                                    vert_mapping=weight_mapping,
                                    use_object_transform=True,
                                    ray_radius=0,
                                    layers_select_src='NAME',
                                    layers_select_dst='ALL',
                                    mix_mode='REPLACE',
                                    mix_factor=1 )

    if copyWeightsToSelectedVerts:
        transfer_weights_to_selected(target, armobj)
        restore_vertex_groups(target)

    try:

        bpy.ops.object.vertex_group_clean(group_select_mode='BONE_DEFORM', limit=1e-05, keep_single=True)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='BONE_DEFORM', limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='BONE_DEFORM', lock_active=False)
    except:

        bpy.ops.object.vertex_group_clean(group_select_mode='ALL', limit=1e-05, keep_single=True)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)

    target.data.use_paint_mask_vertex = vert_paint_mask
    target.data.use_paint_mask = face_paint_mask

    util.ensure_mode_is(omode, context=context)
    bpy.ops.avastar.clear_bone_weight_groups(all_selected=False)
    bpy.ops.object.select_all(action='DESELECT')

    util.set_active_object(context, active)

def generateWeightsFromBoneSet(obj, bone_names, type, clear, copyWeightsToSelectedVerts, rig_sections, excludes, weightBoneSelection):
    tic = time.time()
    if obj.type!='MESH':
        log.warning("|  Do not generate weights for Object %s of type %s" % (obj.name,obj.type))
        return


    armobj = obj.find_armature()
    if not armobj:
        log.warning("| No Armature assigned to Object", obj)
        return time.time() - tic

    all_deform_bone_names = data.get_deform_bones_for_sections(armobj, rig_sections, excludes)
    log.warning("|  Generate weights consider %d deform bones in armature %s" % (
        len(all_deform_bone_names),
        armobj.name)
    )

    log.warning("|  Generate weights for %d %sbones" % (
        len(bone_names) if bone_names else 0,
        "selected " if copyWeightsToSelectedVerts else "")
    )

    active = util.get_active_object(bpy.context)
    if bone_names==None or len(bone_names) == 0:
        bone_names = [bone.name for bone in armobj.data.bones if bone.use_deform]
        if len(bone_names) == 0:
            bone_names = all_deform_bone_names
    if clear and not copyWeightsToSelectedVerts:
        util.removeWeightGroups(obj,bone_names)







    layer_visibility = {i:layer for i,layer in enumerate(armobj.data.layers) if i in [B_LAYER_SL, B_LAYER_VOLUME, B_LAYER_DEFORM, B_LAYER_EXTENDED]}
    armobj.data.layers[B_LAYER_SL]       = True #ensure the deform bone are visible
    armobj.data.layers[B_LAYER_EXTENDED] = True #ensure the deform bone are visible
    armobj.data.layers[B_LAYER_VOLUME]   = True #ensure the deform bone are visible
    armobj.data.layers[B_LAYER_DEFORM]   = True #ensure the deform bone are visible

    util.setSelectOption(armobj, bone_names)
    util.set_active_object(bpy.context, obj)
    original_mode = util.ensure_mode_is("WEIGHT_PAINT")
    deform_backup = util.setDeformOption(armobj, all_deform_bone_names)
    if copyWeightsToSelectedVerts:
        obj.data.use_paint_mask=True
        obj.data.use_paint_mask_vertex=True

    else:
        obj.data.use_paint_mask=False
        obj.data.use_paint_mask_vertex=False


    log.warning("Create weight maps from %s bones" % type)
    bpy.ops.paint.weight_from_bones(type=type)
    toc = time.time()
    log.warning("Generate weight from bones in %.4f seconds" % (toc-tic))

    unweighted = [v.index for v in obj.data.vertices if len(v.groups)==0]



    for layer in layer_visibility.keys():
        armobj.data.layers[layer] = layer_visibility[layer]




    util.restoreDeformOption(armobj, deform_backup)
    util.ensure_mode_is(original_mode)
    util.set_active_object(bpy.context, active)

    toc = time.time() - tic
    log.warning ("|  generateWeightsFromBoneSet total runtime: %.4f seconds" % toc) 
    return toc

def get_enabled_bone_count(armobj, rig_sections, excludes):
    bone_names = data.get_deform_bones_for_sections(armobj, rig_sections, excludes, visible=None)
    return len(bone_names)

def get_selected_bone_count(armobj, weightBoneSelection, rig_sections, excludes):
    bone_set = data.get_selected_bones(armobj, weightBoneSelection, rig_sections, excludes)
    return len(bone_set)


def assign_extended_section(op, all_sections=False, discard_volumes=False, weight_sources=None):
    excludes = []
    if weight_sources == 'FACEGEN':
        rig_sections = [B_LAYER_DEFORM_FACE]
    elif all_sections:
        rig_sections = [B_EXTENDED_LAYER_ALL]
    else:
        rig_sections = []
        if op.weight_base_bones:
            rig_sections.append(B_LAYER_SL)
        if op.weight_groin:
            rig_sections.append(B_LAYER_DEFORM_GROIN)
        if op.weight_tale:
            rig_sections.append(B_LAYER_DEFORM_TAIL)
        if op.weight_wings:
            rig_sections.append(B_LAYER_DEFORM_WING)
        if op.weight_hinds:
            rig_sections.append(B_LAYER_DEFORM_LIMB)
        if op.weight_hands:
            rig_sections.append(B_LAYER_DEFORM_HAND)
        if op.weight_face_bones:
            rig_sections.append(B_LAYER_DEFORM_FACE)
        if op.weight_volumes:
            rig_sections.append(B_LAYER_VOLUME)

    if discard_volumes:
        excludes = [B_LAYER_VOLUME]

    if not op.weight_eye_bones or all_sections:
        excludes.append(B_EXTENDED_LAYER_SL_EYES)
    if not op.weight_alt_eye_bones or all_sections:
        excludes.append(B_EXTENDED_LAYER_ALT_EYES)

    return rig_sections, excludes

def assign_weight_properties(op, skeletonProps):
    op.weight_base_bones = skeletonProps.weight_base_bones
    op.weight_eye_bones = skeletonProps.weight_eye_bones
    op.weight_alt_eye_bones = skeletonProps.weight_alt_eye_bones
    op.weight_face_bones = skeletonProps.weight_face_bones
    op.weight_groin = skeletonProps.weight_groin
    op.weight_tale = skeletonProps.weight_tale
    op.weight_wings = skeletonProps.weight_wings
    op.weight_hinds = skeletonProps.weight_hinds
    op.weight_hands = skeletonProps.weight_hands
    op.weight_volumes = skeletonProps.weight_volumes

def draw_include_binding(layout, skelProp, scope, rigtype):
    col = layout.column(align=True)
    row = col.row(align=True)
    op = row.operator("avastar.generic_info_operator", text="", icon=ICON_INFO, emboss=False)
    op.msg = messages.section_info_deform_bone_groups

    row.label(text="Enabled Deform Bone Groups")

    col = layout.column(align=True)
    if rigtype == 'EXTENDED':
        row = col.row(align=True)
        row.prop(skelProp, "weight_base_bones", toggle=True, icon_value=get_eye_icon('meye', skelProp.weight_base_bones))
        row.prop(skelProp, "weight_volumes", toggle=True, icon_value=get_eye_icon('meye', skelProp.weight_volumes))
        row.prop(skelProp, "weight_alt_eye_bones", toggle=True, icon_value=get_eye_icon('meye', skelProp.weight_alt_eye_bones))
        row.prop(skelProp, "weight_eye_bones", toggle=True, icon_value=get_eye_icon('meye', skelProp.weight_eye_bones))
        row=col.row(align=True)
        row.prop(skelProp, "weight_hands", toggle=True)
        row.prop(skelProp, "weight_face_bones", toggle=True)
        row.prop(skelProp, "weight_wings", toggle=True)
        row=col.row(align=True)
        row.prop(skelProp, "weight_tale", toggle=True)
        row.prop(skelProp, "weight_hinds", toggle=True)
        row.prop(skelProp, "weight_groin", toggle=True)
    else:
        col.prop(skelProp, "weight_base_bones", toggle=True, icon_value=get_eye_icon('meye', skelProp.weight_base_bones))
        row.prop(skelProp, "weight_volumes", toggle=True, icon_value=get_eye_icon('meye', skelProp.weight_volumes))
        col.prop(skelProp, "weight_eye_bones", toggle=True, icon_value=get_eye_icon('meye', skelProp.weight_eye_bones))

class DisplayWeightsPerVert(bpy.types.Operator):
    bl_idname = "sparkles.show_weights_per_vert"
    bl_label = "Weights per Vert"
    bl_description = "Display weight counts on a vertex paint layer\n\n"\
                   + " count/vert - Colorcode\n"\
                   + " 0 weights - Black\n"\
                   + " 1 Weights - White\n"\
                   + " 2 weights - Green\n"\
                   + " 3 weights - Yellow\n"\
                   + " 4 weights - Orange\n"\
                   + ">4 weights - Red\n\n"\
                   + "Note: SL supports 4 weights max"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        ob = context.active_object
        if ob and ob.type == 'MESH':
            return ob.find_armature() is not None
        return True
        
    @staticmethod
    def draw_generic(context, layout):
        col=layout.column(align=True)
        col.operator(DisplayWeightsPerVert.bl_idname, text="Show Weightcount map")

    def execute(self, context):
        show_weights_per_vert(context.active_object)
        return {'FINISHED'}

SPK_WEIGHTS_PER_WEIGHT= 'spk_weights_per_weight'

COLORS = [
        Vector((0.0, 0.0, 0.0, 1.0)), #black  (no weights)
        Vector((1.0, 1.0, 1.0, 1.0)), #white  ( 1 weight )
        Vector((0.0, 1.0, 0.0, 1.0)), #green  ( 2 weights)
        Vector((1.0, 1.0, 0.0, 1.0)), #yellow ( 3 weights)
        Vector((1.0, 0.5, 0.0, 1.0)), #orange ( 4 weights)
        Vector((1.0, 0.0, 0.0, 1.0))  #red    (>4 weights)
        ]

def show_weights_per_vert(obj):
    util.set_object_mode("OBJECT",       object=obj)
    util.set_object_mode("VERTEX_PAINT", object=obj)
    me = obj.data
    vcol_layers = me.vertex_colors
    if SPK_WEIGHTS_PER_WEIGHT in vcol_layers:
        vcol_layer = vcol_layers[SPK_WEIGHTS_PER_WEIGHT]
    else:
        vcol_layer = vcol_layers.new(name=SPK_WEIGHTS_PER_WEIGHT)
    vcol_layers.active = vcol_layer
        
    data = vcol_layer.data
    arm  = obj.find_armature()
    deform_groups = {}
    for i,group in enumerate(obj.vertex_groups):
        if group.name in arm.data.bones and arm.data.bones[group.name].use_deform:
            deform_groups[i] = arm.data.bones[group.name]
    

    for loop in me.loops:
        vi = loop.vertex_index
        v = me.vertices[vi]
        ngroups = 0
        for g in v.groups:
            if g.group in deform_groups:
                ngroups +=1
                
        if ngroups > 4:
            ngroups = 5
            
        data[loop.index].color=COLORS[ngroups] 
    me.update()



def add_missing_mirror_groups(context):
    return util.add_missing_mirror_groups(context)

classes = (
    FittingValues,
    ButtonDeletePhysics,
    ButtonRebaseShapekey,
    ButtonRegeneratePhysics,
    ButtonEnablePhysics,
    ButtonGeneratePhysics,
    AVASTAR_MT_fitting_presets_menu,
    AvastarAddPresetFitting,
    AvastarUpdatePresetFitting,
    AvastarRemovePresetFitting,
    ButtonCopyBoneWeights,
    ButtonClearBoneWeightGroups,
    ButtonClearBoneWeights,
    ButtonSwapWeights,
    ButtonMirrorBoneWeights,
    ButtonCopyWeightsFromRigged,
    ButtonCopyWeightsFromSelected,
    ButtonWeldWeightsFromRigged,
    ButtonEnsureMirrorGroups,
    ButtonRemoveGroups,
    ButtonGenerateWeights,
    MeshesIndexPropGroup,
    MeshesProp,
    AVASTAR_UL_MeshesPropVarList,
    DisplayWeightsPerVert,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        registerlog.info("Register class %s" % cls)
        register_class(cls)
        registerlog.info("Registered weights:%s" % cls)

    bpy.types.Object.FittingValues = PointerProperty(type = FittingValues)
    register_FittingValues_attributes()


def unregister():
    from bpy.utils import unregister_class
    unregister_FittingValues_attributes()
    
    del bpy.types.Object.FittingValues

    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered weights:%s" % cls)
