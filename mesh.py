### Copyright 2011, Magus Freston, Domino Marama, and Gaia Clary
### Modifications 2013-2015 Gaia Clary
###
### This file is part of Avastar.
### coo lo si chi ni coaso!
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
from mathutils.kdtree import KDTree
import  xml.etree.ElementTree as et
import xmlrpc.client
from bpy_extras.io_utils import ExportHelper
from bpy.props import *
import logging, gettext, os, time, re, shutil, threading
from math import pi, exp, degrees

from . import animation, armature_util, bind, const, create, data, messages, util, rig, shape, bl_info, weights, propgroups
from bpy.app.handlers import persistent
from .const import *
from .context_util import set_context
from .util import logtime, mulmat
from .data import Skeleton

WEIGHTS_OK       = 0
NO_ARMATURE      = 1
MISSING_WEIGHTS  = 2

POLYLIST_VCOUNT = 0
POLYLIST_P = 1
POLYLIST_COUNT =2
POLYLIST_IS_TRIS=3

BoneDisplayDetails        = True
SkinningDisplayDetails    = False
ColladaDisplayAdvanced    = False
ColladaDisplayUnsupported = False
ColladaDisplayTextures    = False

log_export = logging.getLogger('avastar.export')
log = logging.getLogger('avastar.mesh')
registerlog = logging.getLogger("avastar.register")


g_purge_data_on_unbind = BoolProperty(
            default     = False,
            name        = "Cleanup",
            description = '''Remove Avastar custom properties.
This cleans up the meshes from all Avastar related data (Weights are preserved).

Important: only if you have generated weightmaps with the fitting panel:
when you intend to rebind the mesh to another Avastar Rig, 
then please do not cleanup the data!
''')


def current_selection_can_export(context):
    try:
        if context.mode == 'OBJECT':
            for obj in [o for o in context.scene.objects if util.object_select_get(o)]:
                if obj.type == 'MESH':
                    return True
    except (TypeError, AttributeError):
        pass
    return False

def create_devkit_layout(context, layout):
    if not context.active_object:
        return

def create_collada_layout(context, layout, attached, targets, on_toolshelf=False):
    if not context.active_object:
        return

    ui_level = util.get_ui_level()
    sceneProps = context.scene.SceneProp
    meshProps = context.scene.MeshProp

    armobj = util.get_armature(context.active_object)
    hierarchy_report, error_count, info_count = rig.check_bone_hierarchy(armobj)
    obox = layout.box()
    obox.enabled = len(targets) > 0 and error_count == 0
    obox.label(text="Export to Secondlife", icon=ICON_FILE_BLANK)
    
    use_sliders = False
    in_restpose = False
    has_meshes = current_selection_can_export(context) and len(targets) > 0
    can_export = has_meshes and error_count == 0

    if armobj:
        use_sliders = util.use_sliders(context)
        in_restpose = armobj.RigProp.restpose_mode
        
        if use_sliders and sceneProps.panel_appearance_enabled and not sceneProps.collada_export_with_joints:
            jol = armobj.data.JointOffsetList
            can_export = has_meshes and (in_restpose or (jol == None or len(jol) == 0)) and error_count == 0

    if ui_level == UI_SIMPLE:
        col = obox.column(align=True)
        col.label(text="Using Default Settings")
        row=col.row(align=True)
        row.operator("avastar.expert_preset", text='', icon=ICON_LIGHT_DATA)
        row.operator("avastar.expert_preset", text="Enable Advanced mode")
    else:

        if ui_level > UI_ADVANCED:
            col = obox.column(align=True)
            col.prop(meshProps, "apply_modifier_stack")


        icon = util.get_collapse_icon(ColladaDisplayTextures)
        box = obox.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.operator(ButtonColladaDisplayTextures.bl_idname, text="", icon=icon)
        row.operator(ButtonColladaDisplayTextures.bl_idname, text="Textures", icon=ICON_TEXTURE)


        d = util.getAddonPreferences()
        if ColladaDisplayTextures:
            col = box.column(align=True)
            col.prop(meshProps, "exportTextures", toggle=False)
            col.separator()
            if meshProps.exportTextures:
                col.prop(d, "exportImagetypeSelection", text='', toggle=False, icon=ICON_IMAGE_DATA)
                t = "Use %s for all images" % d.exportImagetypeSelection
                col.prop(d, "forceImageType", text=t, toggle=False)
                col.prop(d, "useImageAlpha", text="Use RGBA", toggle=False)
                col.separator()

        icon = util.get_collapse_icon(ColladaDisplayAdvanced)
        box = obox.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.operator(ButtonColladaDisplayAdvanced.bl_idname, text="", icon=icon)
        row.operator(ButtonColladaDisplayAdvanced.bl_idname, text="Advanced", icon=ICON_MODIFIER)
        row.operator(ButtonColladaResetAdvanced.bl_idname, text="", icon=ICON_X)

        if ColladaDisplayAdvanced and ui_level > UI_SIMPLE:
            
            if use_sliders:
                col = box.column(align=True)
                col.prop(armobj.RigProp,"rig_use_bind_pose")
                if armobj.RigProp.rig_use_bind_pose:
                    bbox = col.box()
                    col=bbox.column()
                    if ui_level > UI_STANDARD:
                        if ui_level > UI_ADVANCED:
                            col.prop(armobj.RigProp,"rig_export_visual_matrix")
                        col.prop(armobj.RigProp,"export_pose_reset_anim")
                        col.prop(armobj.RigProp,"export_pose_reset_script")
                col.prop(armobj.RigProp,"rig_export_in_sl_restpose")

            if ui_level > UI_SIMPLE:
                col = box.column(align=True)
                col.prop(meshProps, "apply_armature_scale", toggle=False)
                col.prop(meshProps, "apply_mesh_rotscale", toggle=False)
                col.prop(sceneProps,"collada_export_rotated")
                col.separator()
                col.prop(meshProps, "export_triangles", toggle=False)
                col.prop(meshProps, "weld_normals", toggle=False)
                col.prop(meshProps, "weld_to_all_visible", toggle=False)
                col.separator()
                col.prop(sceneProps,"collada_export_shape")
                col.prop(sceneProps,"use_export_limits")

                if ui_level > UI_STANDARD:
                    fbox = obox.box()
                    fbox.label(text="Bone filters")
                    col = fbox.column()
                    if sceneProps.panel_appearance_enabled:
                        row = col.row(align=True)
                        row.prop(sceneProps,"collada_export_with_joints")
                        if ui_level > UI_ADVANCED:
                            row.prop(sceneProps,"collada_assume_pos_rig", text='', icon=ICON_ARMATURE_DATA, toggle=True)
                        col.enabled = sceneProps.target_system != 'RAWDATA'

                    col = fbox.column()
                    col.prop(sceneProps,"collada_complete_rig")
                    if not sceneProps.collada_complete_rig:
                        col = fbox.box().column()
                        col.prop(sceneProps,"collada_only_weighted")
                        col.prop(sceneProps,"collada_only_deform")
                        col.prop(sceneProps,"accept_attachment_weights")
                        col.prop(sceneProps,"collada_full_hierarchy")

                    fbox = obox.box()
                    fbox.label(text="Collada Options")
                    col = fbox.column()
                    col.prop(sceneProps,"collada_export_boneroll")
                    col.prop(sceneProps,"collada_export_layers")
                    col.prop(sceneProps,"collada_blender_profile")



        if d.enable_unsupported:
            icon = util.get_collapse_icon(ColladaDisplayUnsupported)
            box = obox#.box()
            col = obox.column(align=True)
            row = col.row(align=True)
            row.operator(ButtonColladaDisplayUnsupported.bl_idname, text="", icon=icon)
            row.operator(ButtonColladaDisplayUnsupported.bl_idname, text="Unsupported", icon=ICON_ERROR)
            if ColladaDisplayUnsupported:   
                col = box.column(align=True)
                col.prop(meshProps, "max_weight_per_vertex")
            
                col = box.column(align=True)

                if len(attached) == 1 and len(targets) == 1:
                    col.prop(meshProps, "exportDeformerShape", toggle=False)

    txt = "Export to" if ui_level > UI_STANDARD else "Export"
    if on_toolshelf:
        if can_export:
            row = obox.row(align=True)
            row.operator(ButtonExportSLCollada.bl_idname, text=txt, icon=ICON_LIBRARY_DATA_DIRECT)
            txt = ''
            if ui_level > UI_STANDARD:
                row.prop(sceneProps,"target_system", text=txt)
        else:
            ibox = obox.box()
            ibox.alert=True            
            ibox.label(text="Export blocked", icon=ICON_ERROR)
            col = ibox.column(align=True)
            if not has_meshes:
                col.label(text="No meshes selected", icon=ICON_INFO)

    if error_count > 0:
        col.label(text="Unsupported Bone Hierarchy:", icon=ICON_INFO)
        col.separator()
        for icon, msg in hierarchy_report:
            if icn == 'ERROR':
                row    = col.row(align=True)
                row.label(text=msg, icon=ICON_BLANK1)
        col.separator()
        col.label(text="Your rig does not", icon=ICON_INFO)
        col.label(text="match the SL Bone Hierarchy", icon=ICON_BLANK1)

    col.separator()

    if armobj and armobj.get('has_bind_data'):
        use_bind_pose = armobj.RigProp.rig_use_bind_pose
        is_in_restpose = armobj.get('is_in_restpose')
        if not is_in_restpose and not use_bind_pose:
            ibox = obox.box()
            icol = ibox.column()
            icol.alert=True
            icol.label(text="ATTENTION:")
            icol.label(text="You must export in")
            icol.label(text="Neutral Shape,")
            icol.label(text="Otherwise you may get")
            icol.label(text="unexpected results")

            icol=ibox.column()
            icol.alert=True
            icol.operator("avastar.reset_to_restpose", text='Set Neutral Shape')







def displayShowBones(context, layout, active, armobj, with_bone_gui=False, collapsible=True):
    box = layout
    ui_level = util.get_ui_level()

    if ui_level > UI_SIMPLE:
        box.label(text="Bone Display Style", icon=ICON_BONE_DATA)
        row = box.row(align=True)
        
        row.prop(armobj.RigProp,"display_type", expand=True, toggle=False)

        row = box.row(align=True)
        row.alignment = 'LEFT'
        row.prop(armobj,"show_in_front", text="In front", toggle=True)

        row.prop(armobj.data,"show_bone_custom_shapes", text="Shape", toggle=True)
        row.prop(context.space_data.overlay, "show_relationship_lines", text="Limit", toggle=True)
        
        if active != armobj:
            row.prop(active.ObjectProp,"edge_display", text="Edges", toggle=True)

    col = box.column()
    col.label(text="Visibility", icon=ICON_BONE_DATA)

    displayBoneDetails(context, box, armobj, ui_level)

class ButtonRigdisplaySpecialBoneGroups(bpy.types.Operator):
    bl_idname = "avastar.rig_display_special_bone_groups"
    bl_label = ""
    bl_description = "Hide/Unhide Deform Bone Groups"

    visible = False
    toggle_details_display : BoolProperty(default=False, name="Toggle Details",
        description="Toggle Details Display")

    def execute(self, context):
        ButtonRigdisplaySpecialBoneGroups.visible = not ButtonRigdisplaySpecialBoneGroups.visible
        return{'FINISHED'}

class ButtonRigdisplayDeformBoneGroups(bpy.types.Operator):
    bl_idname = "avastar.rig_display_deform_bone_groups"
    bl_label = ""
    bl_description = "Hide/Unhide Deform Bone Groups"

    visible = False
    toggle_details_display : BoolProperty(default=False, name="Toggle Details",
        description="Toggle Details Display")

    def execute(self, context):
        ButtonRigdisplayDeformBoneGroups.visible = not ButtonRigdisplayDeformBoneGroups.visible
        return{'FINISHED'}

class ButtonRigdisplayAnimationBoneGroups(bpy.types.Operator):
    bl_idname = "avastar.rig_display_animation_bone_groups"
    bl_label = ""
    bl_description = "Hide/Unhide Animation Bone Groups"

    visible = True
    toggle_details_display : BoolProperty(default=False, name="Toggle Details",
        description="Toggle Details Display")

    def execute(self, context):
        ButtonRigdisplayAnimationBoneGroups.visible = not ButtonRigdisplayAnimationBoneGroups.visible
        return{'FINISHED'}

def displayBoneDetails(context, box, armobj, ui_level):


    def do_display_animation_bone_groups(context, armobj, ui_level, layout):
        col = layout
        props     = util.getAddonPreferences()
        sceneProps = context.scene.SceneProp
        if armobj.RigProp.RigType == 'EXTENDED':
            row = col.row(align=True)
            row.prop(armobj.data, "layers", index=B_LAYER_HAND, toggle=True, text="Hands",   icon_value=visIcon(armobj, B_LAYER_HAND, type='animation'))
            rig.create_ik_button(row, armobj, B_LAYER_IK_HAND)

        row = col.row(align=True)
        row.prop(armobj.data, "layers", index=B_LAYER_ARMS, toggle=True, text="Arms",       icon_value=visIcon(armobj, B_LAYER_ARMS, type='animation'))
        rig.create_ik_button(row, armobj, B_LAYER_IK_ARMS)

        row = col.row(align=True)
        row.prop(armobj.data, "layers", index=B_LAYER_LEGS, toggle=True, text="Legs", icon_value=visIcon(armobj, B_LAYER_LEGS, type='animation'))
        rig.create_ik_button(row, armobj, B_LAYER_IK_LEGS)

        if armobj.RigProp.RigType != 'BASIC':
            row = col.row(align=True)
            row.prop(armobj.data, "layers", index=B_LAYER_LIMB, toggle=True, text="Hinds", icon_value=visIcon(armobj, B_LAYER_LIMB, type='animation'))
            rig.create_ik_button(row, armobj, B_LAYER_IK_LIMBS)


        col = col.column(align=True)
        row = col.row(align=True)
        row.prop(armobj.data, "layers", index=B_LAYER_FACE, toggle=True, text="Face",    icon_value=visIcon(armobj, B_LAYER_FACE, type='animation'))

        if armobj.RigProp.RigType != 'BASIC':
            rig.create_ik_button(row, armobj, B_LAYER_IK_FACE)
            row = col.row(align=True)
            row.prop(armobj.data, "layers", index=B_LAYER_WING, toggle=True, text="Wings",  icon_value=visIcon(armobj, B_LAYER_WING, type='animation'))

            row = col.row(align=True)
            row.prop(armobj.RigProp, "spine_is_visible", toggle=True, text="Spine",  icon_value=visIcon(armobj, B_LAYER_SPINE, type='animation'))
            row.prop(armobj.data, "layers", index=B_LAYER_TAIL, toggle=True, text="Tail",   icon_value=visIcon(armobj, B_LAYER_TAIL, type='animation'))
            row.prop(armobj.data, "layers", index=B_LAYER_GROIN, toggle=True, text="Groin", icon_value=visIcon(armobj, B_LAYER_GROIN, type='animation'))

        try:
            if armobj.pose.bones["EyeTarget"].bone.layers[B_LAYER_EYE_TARGET]:
                row = col.row(align=True)
                row.prop(armobj.data, "layers", index=B_LAYER_EYE_TARGET,     toggle=True, text="Eye Focus", icon_value=visIcon(armobj, B_LAYER_EYE_TARGET, type='animation'))
                row.prop(armobj.IKSwitchesProp, "Enable_Eyes", text='', icon =ICON_CHECKMARK if armobj.IKSwitchesProp.Enable_Eyes else 'BLANK1')
                if armobj.pose.bones["FaceEyeAltTarget"].bone.layers[B_LAYER_EYE_ALT_TARGET]:
                    row.prop(armobj.data, "layers", index=B_LAYER_EYE_ALT_TARGET, toggle=True, text="Alt Focus", icon_value=visIcon(armobj, B_LAYER_EYE_ALT_TARGET, type='animation'))
                    row.prop(armobj.IKSwitchesProp, "Enable_AltEyes", text='', icon =ICON_CHECKMARK if armobj.IKSwitchesProp.Enable_AltEyes else 'BLANK1')
        except:
            pass







    display_animation_bone_groups = ButtonRigdisplayAnimationBoneGroups.visible
    display_deform_bone_groups = ButtonRigdisplayDeformBoneGroups.visible
    display_special_bone_groups = ButtonRigdisplaySpecialBoneGroups.visible
    
    col = box.column(align=True)
    row=col.row(align=True)
    row.operator("avastar.rig_display_animation_bone_groups", icon = util.get_collapse_icon(display_animation_bone_groups))
    row.operator("avastar.rig_display_animation_bone_groups", text="Animation Bone Groups")

    if display_animation_bone_groups:
        row = col.row(align=True)
        if armobj.RigProp.RigType != 'REFERENCE':
            row.prop(armobj.data, "layers", index=B_LAYER_TORSO, toggle=True, text="Torso", icon_value=visIcon(armobj, B_LAYER_TORSO, type='animation'))
        row.prop(armobj.data, "layers", index=B_LAYER_ORIGIN, toggle=True, text="Origin", icon_value=visIcon(armobj, B_LAYER_ORIGIN, type='animation'))

        if armobj.RigProp.RigType != 'REFERENCE':
            do_display_animation_bone_groups(context, armobj, ui_level, col)






    excludes = []
    rig_sections = [B_EXTENDED_LAYER_ALL]
    
    deformbone_count = len(data.get_deform_bones(armobj, rig_sections, excludes))

    col.separator()
    col = box.column(align=True)
    row=col.row(align=True)
    row.operator("avastar.rig_display_deform_bone_groups", icon = util.get_collapse_icon(display_deform_bone_groups))
    row.operator("avastar.rig_display_deform_bone_groups", text="Deform Bone Groups")

    if display_deform_bone_groups:
        row = col.row(align=True)
        row.prop(armobj.data, "layers", index=B_LAYER_SL,          toggle=True, text="SL Base", icon_value=visIcon(armobj, B_LAYER_SL, type='deform'))
        row.prop(armobj.data, "layers", index=B_LAYER_VOLUME,      toggle=True, text="Volume",  icon_value=visIcon(armobj, B_LAYER_VOLUME, type='volume'))
        
        if armobj.RigProp.RigType != 'BASIC':
            row = col.row(align=True)
            row.prop(armobj.data, "layers", index=B_LAYER_DEFORM_HAND, toggle=True, text="Hands",   icon_value=visIcon(armobj, B_LAYER_DEFORM_HAND, type='extended'))
            row.prop(armobj.data, "layers", index=B_LAYER_DEFORM_LIMB,  toggle=True, text="Hinds",   icon_value=visIcon(armobj, B_LAYER_DEFORM_LIMB, type='extended'))

            row = col.row(align=True)
            row.prop(armobj.data, "layers", index=B_LAYER_DEFORM_FACE, toggle=True, text="Face",    icon_value=visIcon(armobj, B_LAYER_DEFORM_FACE, type='extended'))
            row.prop(armobj.data, "layers", index=B_LAYER_DEFORM_WING, toggle=True, text="Wings",   icon_value=visIcon(armobj, B_LAYER_DEFORM_WING, type='extended'))

            row = col.row(align=True)
            row.prop(armobj.data, "layers", index=B_LAYER_DEFORM_SPINE, toggle=True, text="Spine",   icon_value=visIcon(armobj, B_LAYER_DEFORM_SPINE, type='extended'))
            row.prop(armobj.data, "layers", index=B_LAYER_DEFORM_TAIL, toggle=True, text="Tail",    icon_value=visIcon(armobj, B_LAYER_DEFORM_TAIL, type='extended'))
            row.prop(armobj.data, "layers", index=B_LAYER_DEFORM_GROIN, toggle=True, text="Groin",  icon_value=visIcon(armobj, B_LAYER_DEFORM_GROIN, type='extended'))

    if ui_level > UI_SIMPLE:
        col.separator()
        col = box.column(align=True)
        row=col.row(align=True)
        row.operator("avastar.rig_display_special_bone_groups", icon = util.get_collapse_icon(display_special_bone_groups))
        row.operator("avastar.rig_display_special_bone_groups", text="Special Bone Groups")

        if display_special_bone_groups:
            col.prop(armobj.data, "layers", index=B_LAYER_ATTACHMENT, toggle=True, text="Attachment", icon_value=visIcon(armobj, B_LAYER_ATTACHMENT, type='animation'))
            if armobj.RigProp.RigType != 'REFERENCE':
                col.prop(armobj.data, "layers", index=B_LAYER_EXTRA, toggle=True, text="Extra", icon_value=visIcon(armobj, B_LAYER_EXTRA, type='animation'))
                col.prop(armobj.data, "layers", index=B_LAYER_STRUCTURE, toggle=True, text="Structure", icon_value=visIcon(armobj, B_LAYER_STRUCTURE, type='animation'))


    if ui_level == UI_SIMPLE:
        row = col.row(align=True)
        row.prop(armobj.data, "layers", index=B_LAYER_DEFORM, toggle=True, text="Deform Bones", icon_value=visIcon(armobj, B_LAYER_DEFORM, type='deform'))
    else:
        filter_type = armobj.ObjectProp.rig_display_type
        nc = box.column(align=True)
        text="Deform Bones (%d)" % deformbone_count
        nc.label(text="Active Deform Bones")
        row = nc.row(align=True)
        row.prop(armobj.data, "layers", index=B_LAYER_DEFORM, toggle=True, text=text, icon_value=visIcon(armobj, B_LAYER_DEFORM, type=filter_type))



        row.prop(armobj.ObjectProp, "filter_deform_bones", index=B_LAYER_DEFORM, toggle=True, text="", icon=ICON_FILTER)

        row = nc.row(align=True)
        row.prop(armobj.ObjectProp, "rig_display_type", expand=True, toggle=False)
        row.enabled = armobj.data.layers[B_LAYER_DEFORM] and armobj.ObjectProp.filter_deform_bones

    if deformbone_count == 0:
        ibox = box.box()
        ibox.label(text="All Deform Bones Disabled", icon=ICON_ERROR)




            

class PanelAvatarShapeIO(bpy.types.Panel):
    '''
    Control the avatar shape using SL drivers
    '''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_category    = "Skinning"

    bl_label = "Avatar Shape IO"
    bl_idname = "AVASTAR_PT_avatar_shape_io"
    bl_context = 'object'

    @classmethod
    def poll(self, context):
        '''
        This panel will only appear if the object has a
        Custom Property called "avastar" (value doesn't matter)
        '''
        obj = context.active_object
        return obj and obj.type=='ARMATURE' and "avastar" in obj

    @staticmethod
    def draw_generic(op, context, arm, layout):
        meshProp = context.scene.MeshProp
        box = layout.box()
        col = box.column(align=True)
        col.alignment='LEFT'
        col.operator("avastar.load_props", icon=ICON_IMPORT)
        split = col.split(factor=0.6, align=True)
        split.operator("avastar.save_props",text="Export Shape to", icon=ICON_EXPORT).destination=meshProp.save_shape_selection
        split.prop(meshProp, "save_shape_selection", text="", toggle=False)
        col.operator("avastar.refresh_character_shape", icon=ICON_FILE_REFRESH)
        col.operator("avastar.manage_all_shapes", icon=ICON_X, text="Manage System Meshes")

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_SHAPE_IO, msg=panel_info_appearance)

    def draw(self, context):
        PanelAvatarShapeIO.draw_generic(self, context, context.active_object, self.layout)

CORRECTIVE_KEY_MAP = {
    "body_fat_637":"fat_torso_634",
    "squash_stretch_head_647":"squash_stretch_head_187",
    "torso_muscles_649":"muscular_torso_106",
    "breast_size_105":"big_chest_626",
    "love_handles_676":"love_handles_855",
    "belly_size_157":"big_belly_torso_104",
    "leg_muscles_652":"muscular_legs_152",
    "butt_size_795":"big_butt_legs_151",
    "saddlebags_753":"saddlebags_854",
    "bowed_legs_841":"bowed_legs_853"
    }
    
def get_corrective_key_name_for(pid):
    if pid in CORRECTIVE_KEY_MAP:
        return CORRECTIVE_KEY_MAP[pid]
    else:
        return pid


class ButtonBoneDisplayDetails(bpy.types.Operator):
    bl_idname = "avastar.bone_display_details"
    bl_label = ""
    bl_description = "Hide/Unhide advanced bone display"

    toggle_details_display : BoolProperty(default=True, name="Toggle Details",
        description="Toggle Details Display")

    def execute(self, context):
        global BoneDisplayDetails
        BoneDisplayDetails = not BoneDisplayDetails
        return{'FINISHED'}


class ButtonColladaDisplayTextures(bpy.types.Operator):
    bl_idname = "avastar.collada_display_textures"
    bl_label = ""
    bl_description = "Hide/Unhide textures panel"

    toggle_details_display : BoolProperty(default=False, name="Toggle Details",
        description="Toggle Details Display")

    def execute(self, context):
        global ColladaDisplayTextures
        ColladaDisplayTextures = not ColladaDisplayTextures
        return{'FINISHED'}


class ButtonColladaDisplayAdvanced(bpy.types.Operator):
    bl_idname = "avastar.collada_display_advanced"
    bl_label = ""
    bl_description = \
'''Hide/Unhide advanced panel

This panel contains options which are not supported by Second Life
However these options may be useful when you export for other virtual worlds'''

    def execute(self, context):
        global ColladaDisplayAdvanced
        ColladaDisplayAdvanced = not ColladaDisplayAdvanced
        return{'FINISHED'}


class ButtonColladaResetAdvanced(bpy.types.Operator):
    bl_idname = "avastar.collada_reset_advanced"
    bl_label = ""
    bl_description = "reset panel values to Avastar defaults"

    def execute(self, context):
        arm = util.get_armature(context.object)
        if not arm:
            return{'FINISHED'}

        prop = context.scene.MeshProp
        prop.property_unset("apply_armature_scale")
        prop.property_unset("apply_mesh_rotscale")
        prop.property_unset("weld_normals")
        prop.property_unset("weld_to_all_visible")
        prop.property_unset("export_triangles")

        prop = context.scene.SceneProp
        prop.property_unset("collada_export_with_joints")
        prop.property_unset("collada_assume_pos_rig")
        prop.property_unset("collada_only_weighted")
        prop.property_unset("collada_only_deform")
        prop.property_unset("accept_attachment_weights")
        prop.property_unset("collada_full_hierarchy")
        prop.property_unset("collada_complete_rig")
        prop.property_unset("collada_export_boneroll")
        prop.property_unset("collada_export_layers")
        prop.property_unset("collada_export_shape")
        prop.property_unset("collada_blender_profile")
        prop.property_unset("collada_export_rotated")
        prop.property_unset("use_export_limits")

        prop = arm.RigProp
        prop.property_unset("rig_use_bind_pose")

        return{'FINISHED'}


class ButtonColladaDisplayUnsupported(bpy.types.Operator):
    bl_idname = "avastar.collada_display_unsupported"
    bl_label = ""
    bl_description = "Hide/Unhide unsupported panel. WARNING: Second Life does not support these Options!"

    def execute(self, context):
        global ColladaDisplayUnsupported
        ColladaDisplayUnsupported = not ColladaDisplayUnsupported
        return{'FINISHED'}



class ButtonSmoothWeights(bpy.types.Operator):
    bl_idname = "avastar.smooth_weights"
    bl_label = "Smooth Weights"
    bl_description = "Smooth mesh by adjusting weights of selected bones"
    bl_options = {'REGISTER', 'UNDO'}

    count     = 1
    factor    = 0.5
    omode     = None
    all_verts = True
    workset   = None

    @classmethod
    def poll(self, context):
        obj = context.object
        if obj == None or obj.type != 'MESH': return False
        arm = obj.find_armature()
        if arm == None or not 'avastar' in arm: return False
        if len([b for b in arm.data.bones if b.select]) < 1:      
            return False
        return True

    def invoke(self, context, event):
        obj = context.object
        log.debug("Smooth %s:%s" % (obj.type, obj.name))
        if obj.type == 'ARMATURE':
            log.warning("Can not smooth an Armature. Need to select an object")
            return {'CANCELLED'}
        arm = util.get_armature(obj)
        if not arm:
            log.warning("Can not smooth this Object (not bound to an Armature)")
            return {'CANCELLED'}

        active_vertex_group = obj.vertex_groups.active if obj.type == 'MESH' else None
        active_vgroup_name = active_vertex_group.name if active_vertex_group else None

        self.omode = util.ensure_mode_is("OBJECT") if obj.mode == 'EDIT' else obj.mode

        selected_bone_names  = [b.name for b in arm.data.bones if b.select and b.use_deform]        
        groups = [weights.get_bone_group(obj, n) for n in selected_bone_names if weights.get_bone_partner(n)]
        self.workset = []
        for g in groups:
            name = g.name
            if weights.get_bone_partner_group(obj, name) not in self.workset:
                self.workset.append(g)

        if len(self.workset) == 0:
            bone_s = util.pluralize("bone", len(selected_bone_names))
            self.report({'ERROR'}, "Selected %s [%s] can not be smoothed by weights" % (bone_s, ", ".join(selected_bone_names)))
            return {'CANCELLED'}

        self.all_verts = util.update_all_verts(obj, omode=self.omode)
        opstate = self.execute(context)
        if active_vgroup_name:
            log.warning("Smooth weight: Set active vgroup back to %s" % active_vgroup_name)
            obj.vertex_groups.active = obj.vertex_groups.get(active_vgroup_name)

        return opstate


    def execute(self, context):
        obj   = context.object
        arm   = obj.find_armature()
        unsolved_weights = []
        bm = bmesh.new()

        for vgroup in self.workset:
            name    = vgroup.name
            partner = weights.get_bone_partner_group(obj, name)
            if not name.startswith('m'):
                vgroup, partner = partner, vgroup

            windices = weights.smooth_weights(context, obj, bm, vgroup, partner, all_verts=self.all_verts, count=self.count, factor=self.factor)
            unsolved_weights.extend(windices)
            bm.clear()

        misses = len(unsolved_weights)
        gcount = len(self.workset)
        bone_s = "bone "+ util.pluralize("pair", gcount)
        if misses != 0:
            self.report({'WARNING'}, "Adjusted %d %s (ignored %d verts)" % (gcount, bone_s, misses))

        bm.free()
        util.ensure_mode_is(self.omode)
        return{'FINISHED'}
        


class ButtonDistributeWeights(bpy.types.Operator):
    bl_idname = "avastar.distribute_weights"
    bl_label = "Adjust Shape"
    bl_description = "Optimize weights of selected Bones to match custom shape as good as possible (Needs at least one custom shapekey to define the target shape)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        obj = context.object
        if obj == None or obj.type != 'MESH': return False
        arm = obj.find_armature()
        if arm == None or not 'avastar' in arm: return False
        if len([b for b in arm.data.bones if b.select]) < 1:     
            return False

        sks = obj.data.shape_keys
        if sks and sks.key_blocks:
            for index, block in enumerate(sks.key_blocks.keys()):
                if index > 0 and not block in [REFERENCE_SHAPE, MORPH_SHAPE]:
                    return True
        return False

    def execute(self, context):
        obj = context.object
        print("Distribute in %s:%s" % (obj.type,obj.name))
        if obj.type == 'ARMATURE':
            print("Need to select an object")
            return {'CANCELLED'}
        arm = util.get_armature(obj)
        if not arm:
            print("Need to be bound to an Armature")
            return {'CANCELLED'}

        omode = util.ensure_mode_is("OBJECT") if obj.mode=='EDIT' else obj.mode

        selected_bone_names  = [b.name for b in arm.data.bones if b.select and b.use_deform]        
        groups = [weights.get_bone_group(obj, n) for n in selected_bone_names if weights.get_bone_partner(n)]
        workset = []
        for g in groups:
            if weights.get_bone_partner_group(obj, g.name) not in workset:
                workset.append(g)

        bone_s = util.pluralize("bone", len(selected_bone_names))
        if len(workset) == 0:
            self.report({'ERROR'}, "Selected %s can not be adjusted to Shape" % (bone_s))
            return {'CANCELLED'}

        unsolved_weights = []
        all_verts = util.update_all_verts(obj, omode)
        for vgroup in workset:
            partner = weights.get_bone_partner_group(obj, vgroup.name)
            if not vgroup.name.startswith('m'):
                vgroup, partner = partner, vgroup
            windices = weights.distribute_weights(context, obj, vgroup, partner, all_verts=all_verts)
            unsolved_weights.extend(windices)

        if len(unsolved_weights) == 0:
            self.report({'INFO'}, "Adjusted %d %s to Shape" % (len(workset), bone_s))
        else:
            for index in unsolved_weights:
                obj.data.vertices[index].select=True

            misses = len(unsolved_weights)
            self.report({'WARNING'}, "Adjusted %d %s (ignored %d verts)" % (len(workset), bone_s, misses))

        util.ensure_mode_is(omode)
        return{'FINISHED'}
        


class ButtonBasicPreset(bpy.types.Operator):
    bl_idname = "avastar.basic_preset"
    bl_label = "Basic Features"
    bl_description = '''Show only the Basic features:

Most advanced features are hidden and the user interface
looks less cluttered with features and buttons.
Use this mode when you use Avastar only occasionally
for simple tasks'''
    
    bl_options = {'REGISTER', 'UNDO'}  

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        return self.execute(context)
    
    def execute(self, context):
        preferences = util.getAddonPreferences()
        preferences.ui_complexity='0'
        context.scene.SceneProp.skill_level = 'BASIC'
        return{'FINISHED'}    



class ButtonAdvancedPreset(bpy.types.Operator):
    bl_idname = "avastar.expert_preset"
    bl_label = "All Features"
    bl_description = '''Show All production ready features:

This mode enables all major and well tested features
of Avastar. However you must have a good understanding
about how to use the expert features. Our documentation
at https://avastar.guru tries to help'''
    
    bl_options = {'REGISTER', 'UNDO'}  

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        return self.execute(context)
    
    def execute(self, context):
        preferences = util.getAddonPreferences()
        preferences.ui_complexity='2'
        context.scene.SceneProp.skill_level = 'EXPERT'
        return{'FINISHED'}    



class ButtonAllPreset(bpy.types.Operator):
    bl_idname = "avastar.all_preset"
    bl_label = "Experimental"
    bl_description = '''Show all Avastar features.

This mode enables also experimental functionality.
In most cases you should not need to use this mode,
unless you are trying to work above all limits'''

    bl_options = {'REGISTER', 'UNDO'}  

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        return self.execute(context)
    
    def execute(self, context):
        preferences = util.getAddonPreferences()
        preferences.ui_complexity='3'
        context.scene.SceneProp.skill_level = 'ALL'
        return{'FINISHED'}    



class ButtonBonePresetSkin(bpy.types.Operator):
    bl_idname = "avastar.bone_preset_skin"
    bl_label = "Skin & Weight"
    bl_description = '''Prepare Rig for Skinning:

- Sets Armature to Pose Mode
- Display SL Bones (blue)
- If Active object is a Mesh and not in edit mode:
  Set Weight Paint Mode

Note: Use this Preset only for weighting tasks!
'''

    bl_options = {'REGISTER', 'UNDO'}

    set_rotation_limits  : BoolProperty(
                           name = "Rotation Limits",
                           description = "Enable rotation limits on selected bones",
                           default=False)

    set_in_front         : BoolProperty(

                           name = "X-Ray",
                           description = "Enable X-Ray Mode",
                           default=True)
    adjust_bone_display  : BoolProperty(
                           name = "Adjust Bone Display",
                           description = "Adjust Display to show the weight bones",
                           default=True)
    synchronize_bones    : BoolProperty(name="Sync Deform Bones",
                           description = "Make sure that the Deform Bones are posed like the Animation bones",
                           default=True)
    @classmethod
    def poll(cls, context):
        if not context:
            return False
        active = context.active_object
        if not active:
            return False
        armobj = util.get_armature(active)
        return armobj != None

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.prop(self,"set_in_front")
        col.prop(self,"set_rotation_limits")
        col.prop(self,"synchronize_bones")
        col.prop(self,"adjust_bone_display")

    def invoke(self, context, event):
        armobj = util.get_armature(context.object)
        if armobj and DIRTY_RIG in armobj:
            log.warning("Skin&Weight: Automatic store jointpos edits")
            bind.ArmatureJointPosStore.exec_imp(context)
        return self.execute(context)
    
    def execute(self, context):
        active = context.object
        amode = util.ensure_mode_is("OBJECT", context=context)
        armobj = util.get_armature(active)

        util.object_show_in_front(armobj, self.set_in_front)
        if self.adjust_bone_display:
            rig.guess_deform_layers(armobj)

        rig.setSLBoneRotationMute(self, context, True, 'ALL', with_synchronize=self.synchronize_bones)


        util.set_active_object(context, armobj)
        util.mode_set(mode="POSE")
        util.set_active_object(context, active)
        if active == armobj:
            pass

        else:

            mode = 'WEIGHT_PAINT' if amode != 'EDIT' else amode
            util.mode_set(mode=mode)

            try:
                view = context.space_data
                view.viewport_shade      = ICON_SHADING_SOLID
                view.show_textured_solid = False
            except:
                pass


        context.scene.SceneProp.panel_preset = 'SKIN'
        preferences = util.getAddonPreferences()
        if int(preferences.ui_complexity) < 2:
            preferences.ui_complexity='2'
            context.scene.SceneProp.skill_level  = 'EXPERT'

        return{'FINISHED'}    



guse_default_locks    = BoolProperty(name="Default Locks", description="Set Avastar default constraints and Bone connects", default=False)

class ButtonBonePresetAnimate(bpy.types.Operator):
    bl_idname = "avastar.bone_preset_animate"
    bl_label = "Pose & Animate"
    bl_description = '''Prepare rig for Posing and Animation
    Sets Armature to Pose Mode
    displays green control bones'''

    bl_options = {'REGISTER', 'UNDO'}

    set_rotation_limits  : BoolProperty(
                           name = "Rotation Limits",
                           description = "Enable rotation limits on selected bones",
                           default = False)

    set_in_front         : BoolProperty(
                           name = "X-Ray",
                           description = "Enable X-Ray Mode",
                           default = True)
    adjust_bone_display  : BoolProperty(
                           name = "Adjust Bone Display",
                           description = "Adjust Display to show the Animation Bones",
                           default = True)
    synchronize_bones    : BoolProperty(
                           name = "Sync Anim Bones",
                           description = "Make sure that the Animation Bones are posed like the Deform bones",
                           default = True)

    use_default_locks    : guse_default_locks

    @classmethod
    def poll(cls, context):
        if not context:
            return False
        active = context.active_object
        if not active:
            return False
        armobj = util.get_armature(active)
        return armobj != None

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.prop(self,"set_in_front")
        col.prop(self,"set_rotation_limits")
        col.prop(self,"synchronize_bones")
        col.prop(self,"adjust_bone_display")
        col.prop(self,"use_default_locks")

    def invoke(self, context, event):
        armobj = util.get_armature(context.object)
        if armobj and DIRTY_RIG in armobj:
            log.warning("Pose&Animate: Automatic store jointpos edits")
            bind.ArmatureJointPosStore.exec_imp(context)
        
        return self.execute(context)

    def execute(self, context):
        active = context.object
        armobj = util.get_armature(active)

        util.ensure_mode_is("OBJECT", context=context)
        util.object_show_in_front(armobj, self.set_in_front)
        if self.set_rotation_limits:
            rig.set_bone_rotation_limit_state(armobj, True, 'ALL')

        rig.setSLBoneRotationMute(self, context, False, 'ALL', with_reconnect=self.use_default_locks, with_synchronize=self.synchronize_bones)
        if self.adjust_bone_display:
            rig.guess_pose_layers(armobj)


        util.set_active_object(context, armobj)
        util.mode_set(mode="POSE")
        context.scene.SceneProp.panel_preset = 'POSE'
        preferences = util.getAddonPreferences()
        if int(preferences.ui_complexity) < 1:
            preferences.ui_complexity='1'
            context.scene.SceneProp.skill_level  = 'EXPERT'
        return{'FINISHED'}



class ButtonBonePresetScrub(bpy.types.Operator):
    bl_idname = "avastar.bone_preset_scrub"
    bl_label = "Pose & Weight"
    bl_description = '''Prepare rig for Posing and weighting
    Sets Armature to Pose Mode
    displays blue deform bones
    enable but hide green animation bones
    good for using an animation for testing the deform bones'''

    bl_options = {'REGISTER', 'UNDO'}

    set_rotation_limits  : BoolProperty(
                           name = "Rotation Limits",
                           description = "Enable rotation limits on selected bones",
                           default = False)

    set_in_front         : BoolProperty(
                           name = "X-Ray",
                           description = "Enable X-Ray Mode",
                           default = True)
    adjust_bone_display  : BoolProperty(
                           name = "Adjust Bone Display",
                           description = "Adjust Display to show the Animation Bones",
                           default = True)
    synchronize_bones    : BoolProperty(
                           name = "Sync Anim Bones",
                           description = "Make sure that the Animation Bones are posed like the Deform bones",
                           default = True)

    use_default_locks    : guse_default_locks

    @classmethod
    def poll(cls, context):
        if not context:
            return False
        active = context.active_object
        if not active:
            return False
        armobj = util.get_armature(active)
        return armobj != None

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.prop(self,"set_in_front")
        col.prop(self,"set_rotation_limits")
        col.prop(self,"synchronize_bones")
        col.prop(self,"adjust_bone_display")
        col.prop(self,"use_default_locks")

    def invoke(self, context, event):
        armobj = util.get_armature(context.object)
        if armobj and DIRTY_RIG in armobj:
            log.warning("Pose&Animate: Automatic store jointpos edits")
            bind.ArmatureJointPosStore.exec_imp(context)
        
        return self.execute(context)

    def execute(self, context):
        active = context.object
        armobj = util.get_armature(active)

        util.ensure_mode_is("OBJECT", context=context)
        util.object_show_in_front(armobj, self.set_in_front)
        if self.set_rotation_limits:
            rig.set_bone_rotation_limit_state(armobj, True, 'ALL')

        rig.setSLBoneRotationMute(self, context, False, 'ALL', with_reconnect=self.use_default_locks, with_synchronize=self.synchronize_bones)
        if self.adjust_bone_display:
            rig.guess_pose_layers(armobj)
            rig.guess_deform_layers(armobj, replace=False)


        util.set_active_object(context, armobj)
        util.mode_set(mode="POSE")
        context.scene.SceneProp.panel_preset = 'SCRUB'
        preferences = util.getAddonPreferences()
        if int(preferences.ui_complexity) < 1:
            preferences.ui_complexity='1'
            context.scene.SceneProp.skill_level  = 'EXPERT'
        return{'FINISHED'}


class ButtonBonePresetRetarget(bpy.types.Operator):
    bl_idname = "avastar.bone_preset_retarget"
    bl_label = "Motion Transfer"
    bl_description = '''Prepare rig for for transfering a pose or animation (Retargetting)
    Sets Armature to Object Mode'''
    
    bl_options : {'REGISTER', 'UNDO'}  

    preset               : StringProperty()
    set_rotation_limits  : BoolProperty(name="Rotation Limits", description="Enable rotation limits on selected bones", default=False)
    set_in_front         : BoolProperty(name="X-Ray", description="Enable X-Ray Mode", default=False)
    use_default_locks    : guse_default_locks


    @classmethod
    def poll(cls, context):
        if not context:
            return
        active = context.active_object
        if not active:
            return False
        armobj = util.get_armature(active)
        return armobj != None

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.prop(self,"set_in_front")
        col.prop(self,"use_default_locks")
    
    def invoke(self, context, event):
        armobj = util.get_armature(context.object)
        if armobj and DIRTY_RIG in armobj:
            log.warning("Retarget: Automatic store jointpos edits")
            bind.ArmatureJointPosStore.exec_imp(context)

        self.set_in_front = True
        return self.execute(context)
        
    def execute(self, context):
        active = context.object
        amode = util.ensure_mode_is("OBJECT", context=context)
        armobj = util.get_armature(active)
            
        util.object_show_in_front(armobj, self.set_in_front)
        armobj.data.show_bone_custom_shapes = False


        if self.set_rotation_limits:
            rig.set_bone_rotation_limit_state(armobj, True, 'ALL')

        rig.setSLBoneRotationMute(self, context, False, 'ALL', with_reconnect=self.use_default_locks)
        util.set_armature_layers(armobj, [B_LAYER_TORSO, B_LAYER_ARMS, B_LAYER_LEGS, B_LAYER_ORIGIN])

        bones = armobj.pose.bones
        for b in bones:
            for c in b.constraints:
                if c.type =='LIMIT_ROTATION':
                    c.influence = 0 
                    b.use_ik_limit_x = False
                    b.use_ik_limit_y = False
                    b.use_ik_limit_z = False

                
    

        util.set_active_object(context, armobj)
        util.mode_set(mode="OBJECT")
        util.set_active_object(context, active)
        if active != armobj:
            util.ensure_mode_is(amode, context=context)
        context.scene.SceneProp.panel_preset = 'RETARGET'
        preferences = util.getAddonPreferences()
        if int(preferences.ui_complexity) < 2:
            preferences.ui_complexity='2'
            context.scene.SceneProp.skill_level  = 'EXPERT'
        return{'FINISHED'}


class ButtonBonePresetEdit(bpy.types.Operator):
    bl_idname = "avastar.bone_preset_edit"
    bl_label = "Joint Edit"
    bl_description = '''Prepare rig for Editing
    Sets armature to Edit mode
    enables select of structure Bones'''
    
    bl_options = {'REGISTER', 'UNDO'}  

    preset : StringProperty()
    set_rotation_limits  : BoolProperty(name="Rotation Limits", description="Enable rotation limits on selected bones", default=False)
    set_in_front         : BoolProperty(name="X-Ray", description="Enable X-Ray Mode", default=False)

    @classmethod
    def poll(cls, context):
        if not context:
            return
        active = context.active_object
        if not active:
            return
        armobj = util.get_armature(active)
        return armobj != None


    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.prop(self,"set_in_front")
    
    def invoke(self, context, event):
        self.set_in_front = True
        return self.execute(context)
        
    def execute(self, context):
        active = context.object
        amode = util.ensure_mode_is("OBJECT", context=context)
        armobj = util.get_armature(active)
            
        util.set_active_object(context, armobj)
        util.mode_set(mode="EDIT")
        util.object_show_in_front(armobj, self.set_in_front)        
        rig.setSLBoneStructureRestrictSelect(armobj, False)
        util.set_armature_layers(armobj, [B_LAYER_TORSO, B_LAYER_ARMS, B_LAYER_LEGS, B_LAYER_ORIGIN, B_LAYER_STRUCTURE, B_LAYER_EYE_TARGET, B_LAYER_EXTRA, B_LAYER_SPINE])

        context.scene.SceneProp.panel_preset = 'EDIT'
        preferences = util.getAddonPreferences()
        if int(preferences.ui_complexity) < 2:
            preferences.ui_complexity='2'
            context.scene.SceneProp.skill_level  = 'EXPERT'
        
        return{'FINISHED'}    


class ButtonBonePresetFit(bpy.types.Operator):
    bl_idname = "avastar.bone_preset_fit"
    bl_label = "Fitted Mesh"
    bl_description = '''Prepare Viewport for use with Fitted Mesh pannel:
    - Enable Viewport Solid Shading
    - Set armature to POSE mode
    - Set Mesh to Weight Paint mode
    - Display Basic SL mBones and Volume Bones'''
    
    bl_options = {'REGISTER', 'UNDO'}  

    @classmethod
    def poll(cls, context):
        if not context:
            return
        active = context.active_object
        if not active:
            return
        armobj = util.get_armature(active)
        return armobj != None


    def draw(self, context):
        layout = self.layout
    
    def invoke(self, context, event):
        return self.execute(context)
        
    def execute(self, context):
        active = context.object
        armobj = util.get_armature(active)

        obj_mode = active.mode
        arm_mode = 'POSE'
        util.ensure_mode_is("OBJECT", context=context)
        util.set_active_object(context, armobj)
        util.set_object_mode('POSE', object=armobj)
        if active.type=='MESH' and active.mode=='OBJECT':
            obj_mode = 'WEIGHT_PAINT'

        util.set_armature_layers(armobj, [B_LAYER_VOLUME, B_LAYER_SL])

        context.scene.SceneProp.panel_preset = 'FIT'
        preferences = util.getAddonPreferences()
        if int(preferences.ui_complexity) < 2:
            preferences.ui_complexity='2'
            context.scene.SceneProp.skill_level  = 'EXPERT'

        util.set_active_object(context, active)
        util.ensure_mode_is(obj_mode, object=active, context=context)
        util.ensure_mode_is(arm_mode, object=armobj, context=context)

        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'SOLID'

        return{'FINISHED'}    


def set_active_shape_key(obj,shape_key_name):
    active_index = obj.active_shape_key_index
    index = 0
    try:
        while True:
            obj.active_shape_key_index = index
            if obj.active_shape_key.name == shape_key_name:
                print("Found shape key index", index)
                return
            index += 1
    except:
        obj.active_shape_key_index = active_index
        pass


def prepare_rebake_uv(context, obj):
    me=obj.data
    uv_layers = util.get_uv_layers(me)
    if len(uv_layers) == 0:
        return
    

    active_uv_layer = util.get_active_uv_layer(me)
    if not active_uv_layer.name.endswith("_rebake"):
        active_uv_name = active_uv_layer.name
        copy = util.add_uv_layer(me, name=active_uv_name+"_rebake")
        copy.active_render = True
        util.set_active_uv_layer(me, copy)

    seamed_edges = [edge.index for edge in me.edges if edge.use_seam]
        

    util.ensure_mode_is("EDIT")
    bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold(extend=True)
    util.select_edges(me, seamed_edges, seam=True, select=True)
    bpy.ops.mesh.mark_seam(clear=False)
    
    util.ensure_mode_is("OBJECT")
    for loop in me.loops:
        edge = me.edges[loop.edge_index]
        if edge.use_seam:
            me.uv_layers.active.data[loop.index].pin_uv=True

class ButtonRebakeUV(bpy.types.Operator):
    bl_idname = "avastar.rebake_uv"
    bl_label = "Rebake UV Layout"
    bl_description = 'Constrained unwrap. For Avastar meshes: Similar to "Rebake textures" in world'
    bl_options = {'REGISTER', 'UNDO'}  

    @classmethod
    def poll(self, context):
        obj = context.object
        if obj and obj.type == 'MESH':
            me = obj.data
            uv_layers = util.get_uv_layers(me)
            if len(uv_layers) > 0:
                return True
        return False
        
    def execute(self, context):
        try:
            active_shape_key       = context.object.active_shape_key
            active_shape_key_index = context.object.active_shape_key_index
            mix_shape_key          = None
            obj = context.active_object
            original_mode = util.ensure_mode_is("OBJECT")
                        
            if active_shape_key:

                mix_shape_key = obj.shape_key_add(name="avastar_mix", from_mix=True)
                set_active_shape_key(obj,mix_shape_key.name)
                
            prepare_rebake_uv(context, obj)
            util.ensure_mode_is("EDIT")


            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.unwrap()
            
            if active_shape_key:
                util.ensure_mode_is("OBJECT")

                bpy.ops.object.shape_key_remove()
                context.object.active_shape_key_index = active_shape_key_index

            util.ensure_mode_is(original_mode, "OBJECT")
                        
            return{'FINISHED'}    
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}    






#

#







#




#

class ButtonFindDoubles(bpy.types.Operator):
    bl_idname = "avastar.find_doubles"
    bl_label = "Doubles"
    bl_description = "Find all double vertices in Mesh"
    bl_options = {'REGISTER', 'UNDO'}  
    
    distance : FloatProperty(  
       name="distance",  
       default=0.0001,  
       subtype='DISTANCE',  
       unit='LENGTH',
       soft_min=0.0000001,
       soft_max=0.01,
       precision=4,
       description="distance"  
       )

    @classmethod
    def poll(self, context):
        return context and context.object and context.object.type=='MESH'
        
    def execute(self, context):
        try:
            original_mode = util.ensure_mode_is("EDIT")
            count = util.select_all_doubles(context.object.data, dist=self.distance)
            util.ensure_mode_is(original_mode)
            if count > 0:
                self.report({'WARNING'},"Object %s has %d duplicate Verts." % (context.object.name,count))
            else:
                self.report({'INFO'},"Object %s has no duplicate verts." % context.object.name)
            return{'FINISHED'}    
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonFindUnweighted_old(bpy.types.Operator):
    bl_idname = "avastar.find_unweighted_old"
    bl_label = "Find Unweighted"
    bl_description = "Find any unweighted vertices in active mesh"

    def execute(self, context):
        try:
            obj = context.active_object
    
            unweighted, status = findUnweightedVertices(context, obj, use_sl_list=False)
            if status == NO_ARMATURE:
                raise util.Warning(msg_no_armature + 'find_unweighted'%obj.name)
            elif status == MISSING_WEIGHTS:
                self.report({'WARNING'},"%d unweighted verts on %s"%(len(unweighted),obj.name))

                if len(unweighted)>0:

                    obj.data.use_paint_mask_vertex = True
                    bpy.ops.paint.vert_select_all(action='DESELECT')

                    for vidx in unweighted:
                        obj.data.vertices[vidx].select = True

            else:
                self.report({'INFO'},"Object %s has all verts weighted."%obj.name)

            return{'FINISHED'}    
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}    




class ButtonFindUnweighted(bpy.types.Operator):
    bl_idname = "avastar.find_unweighted"
    bl_label = "Unweighted verts"
    bl_description = "Find vertices not assigned to any deforming weightgroups"

    def execute(self, context):
        try:
            error_counter = 0
            weightpaint_candidate = None
            for obj in context.selected_objects:
                if obj.type != "MESH":
                    continue


                report = findWeightProblemVertices(context, obj, use_sl_list=False, find_selected_armature=True)
                
                if 'no_armature' in report['status']:
                    raise util.Warning(msg_no_armature + 'find_unweighted'%obj.name)
                
                elif 'unweighted' in report['status']:
                    error_counter += 1
                    weightpaint_candidate = obj
                    unweighted = report['unweighted']
                    self.report({'WARNING'},"%d unweighted verts on %s"%(len(unweighted),obj.name))
                else:
                    self.report({'INFO'},"Object %s has all verts weighted."%obj.name)

            if error_counter == 1:

                util.set_active_object(context, weightpaint_candidate)
                original_mode = util.ensure_mode_is('WEIGHT_PAINT')
                obj.data.use_paint_mask_vertex = True
                bpy.ops.paint.vert_select_all(action='DESELECT')
                
                for vidx in unweighted:
                    obj.data.vertices[vidx].select = True
                    
                util.ensure_mode_is(original_mode)
                    
            elif error_counter > 1:
                self.report({'WARNING'},"%d of the selected Meshes have unweighted verts!"%(error_counter))

            return{'FINISHED'}    
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}    
        

class ButtonFindZeroWeights(bpy.types.Operator):
    bl_idname = "avastar.find_zeroweights"
    bl_label = "Zero weights"
    bl_description = "Find vertices with deforming weight_sum == 0"
    bl_options = {'REGISTER', 'UNDO'}
    
    min_weight : FloatProperty(
        name = "Min weight",
        min = 0.0,
        max = 1.0,
        default = 0)

    def draw(self, context):
            layout = self.layout
            scn = context.scene
            col = layout.column(align=True)
            col.prop(self, "min_weight")
        
    def execute(self, context):
        try:
            error_counter = 0
            weightpaint_candidate = None
            for obj in context.selected_objects:
            
                if obj.type != "MESH":
                    continue
       

                report = findWeightProblemVertices(context, obj, use_sl_list=False, find_selected_armature=True, minweight=self.min_weight)
                
                if 'no_armature' in report['status']:
                    raise util.Warning(msg_no_armature + 'find_zeroweights'%obj.name)
                
                elif 'zero_weights' in report['status']:
                    error_counter += 1
                    weightpaint_candidate = obj
                    problems = report['zero_weights']
                    self.report({'WARNING'},"%d zero-weight verts on %s"%(len(problems),obj.name))
                else:
                    self.report({'INFO'},"Object %s: All verts properly weighted"%obj.name)
              
            if error_counter == 1:
                util.set_active_object(context, weightpaint_candidate)
                original_mode = context.object.mode
                util.mode_set(mode='WEIGHT_PAINT')
                obj.data.use_paint_mask_vertex = True
                bpy.ops.paint.vert_select_all(action='DESELECT')

                for vidx in problems:
                    obj.data.vertices[vidx].select = True
                    
                util.mode_set(mode=original_mode)
                
            elif error_counter > 1:
                self.report({'WARNING'},"%d of the selected Meshes have zero-weight verts!"%(error_counter))

            return{'FINISHED'}    
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}    
        

class ButtonFindTooManyWeights(bpy.types.Operator):
    bl_idname      = "avastar.find_toomanyweights"
    bl_label       = "> Weight limit"
    bl_description = "Find verts with too many assigned weightgroups\n By default flag verts with > 4 weights assigned\nYou can change the parameters in the Redo Panel\nSee Bottom of the Tool Shelf after calling the Operator"
    bl_options     = {'REGISTER', 'UNDO'}

    max_weight  : IntProperty(default=4, min=0, name="Weight Limit", description="Report verts with more than this number of weights" )
    only_deform : BoolProperty(default=True, name="Deforming", description = "Take only deforming groups into account (mesh needs to be bound to an armature)" )

    def execute(self, context):
        try:
            error_counter = 0
            wp_obj = None
            for obj in context.selected_objects:
            
                if obj.type != "MESH":
                    continue
   

                report = findWeightProblemVertices(context, obj, 
                         use_sl_list=False,
                         find_selected_armature=True,
                         max_weight=self.max_weight,
                         only_deform=self.only_deform )
                


                
                if 'too_many' in report['status']:
                    error_counter += 1
                    wp_obj = obj
                    problems = report['too_many']
                    self.report({'WARNING'},"%d verts with more than %d%s weightgroups on %s"%(len(problems), self.max_weight, " deforming" if self.only_deform else " ", obj.name))

                else:
                    self.report({'INFO'},"Object %s has no vertices with more than %d deforming weight groups."% (obj.name, self.max_weight))

            if error_counter == 1:
                util.set_active_object(context, wp_obj)
                original_mode = util.ensure_mode_is('WEIGHT_PAINT')
                wp_obj.data.use_paint_mask_vertex = True
                bpy.ops.paint.vert_select_all(action='DESELECT')

                for vidx in problems:
                    wp_obj.data.vertices[vidx].select = True

                util.set_active_object(context, wp_obj)
                util.ensure_mode_is(original_mode)
            elif error_counter > 1:
                self.report({'WARNING'},"%d of the selected Meshes have verts with too many deforming weight groups!"%(error_counter))

            return{'FINISHED'}    
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}    


class ButtonFixTooManyWeights(bpy.types.Operator):
    bl_idname      = "avastar.fix_toomanyweights"
    bl_label       = "Limit Weight Map Count"
    bl_description = \
'''limit the number of bones which affect the location of vertices to 4
Hint: You find the Bone Weight Maps in the
Vertex Group list (having same names as the bones)
Note: vertex groups unrelated to bones are not touched by the limitation'''

    bl_options     = {'REGISTER', 'UNDO'}

    max_weight  : IntProperty(default=4, min=0, name="Weight Limit", description="Report verts with more than this number of weights" )

    def execute(self, context):
        active = util.get_active_object(context)
        amode  = active.mode

        object_count = 0
        vertex_count = 0
        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue            

            arm=obj.find_armature()
            if not obj or not arm:
                continue

            candidates = [[v.index,sorted([g for g in v.groups if obj.vertex_groups[g.group].name in arm.data.bones], key=lambda g:g.weight)] for v in obj.data.vertices if len([g for g in v.groups if obj.vertex_groups[g.group].name in arm.data.bones]) > self.max_weight]

            if len(candidates) == 0:
                continue

            util.set_active_object(context, obj)
            omode = util.ensure_mode_is('OBJECT')

            object_count += 1
            vertex_count += len(candidates)
            for vindex, groups in candidates:
                gindex=0
                while gindex < len(groups)-self.max_weight:
                    obj.vertex_groups[groups[gindex].group].remove([vindex])
                    gindex += 1

            util.ensure_mode_is(omode)

        util.set_active_object(context, active)
        util.ensure_mode_is(amode)

        msg = "Fixed %d verts with too many deforming weight groups%s"\
            % (vertex_count, "" if object_count < 2 else "in %d objects" % object_count)\
            if vertex_count > 0 else "All verts are clean, no fix needed"

        self.report({'INFO'}, msg)
        return {'FINISHED'}
  



class ButtonFindAsymmetries(bpy.types.Operator):
    bl_idname = "avastar.find_asymmetries"
    bl_label = "Asymmetries"
    bl_options     = {'REGISTER', 'UNDO'}    
    bl_description = '''Find asymmetric vertices/edges/faces
Marks all elements for which no symmetry partner was found
This operator works on vertices, edges, or faces 
depending on the selection mode'''

    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def execute(self, context):

        omode = util.ensure_mode_is('EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.select_mirror()
        bpy.context.object.update_from_editmode()
        bpy.ops.mesh.select_all(action='INVERT')
        util.ensure_mode_is('OBJECT')
        me = bpy.context.object.data
        selcount = len([v for v in me.vertices if v.select and not v.hide])
        util.ensure_mode_is(omode)
        
        if selcount == 0:
            self.report({'INFO'}, "Object is symmetric")
        else:
            self.report({'WARNING'}, "Found %d asymmetric elements" % selcount)

        return{'FINISHED'}    


class ButtonFixAsymmetries(bpy.types.Operator):
    bl_idname = "avastar.fix_asymmetries"
    bl_label = "Fix Asymmetries"
    bl_options     = {'REGISTER', 'UNDO'}    
    bl_description = '''Fix symmetry for selected vertex pairs
Copy the mirrored location of each selected vertex'''

    symmetry_axis : EnumProperty(
        items=(
            ('0', 'X', 'Use global X axis symmetry'),
            ('1', 'Y', 'Use global Y axis symmetry'),
            ('2', 'Z', 'Use global Z axis symmetry'),
        ),
        name="Symmetry Axis",
        description="Symmetry axis to be used (in Object Space)",
        default='0')

    toggle_direction : BoolProperty(
            name        = "Reverse",
            description = "exchange source and destination",
            default     = False)

    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type == "MESH"

    def find_active_vertex_index(self, obj):
        bm=bmesh.from_edit_mesh(obj.data)
        elem = util.bmesh_vert_active(bm)
        return elem.index if elem else None

    def execute(self, context):
        obj = context.object

        omode = util.ensure_mode_is('EDIT')
        bpy.context.object.update_from_editmode()
        pair = [v.index for v in obj.data.vertices if v.select and not v.hide]
        if len(pair) != 2:
            self.report({'WARNING'}, "Select 2 verts and try again")
            return {'CANCELLED'}

        active_index = self.find_active_vertex_index(obj)
        if active_index and pair[0] != active_index:
            pair.reverse()
        
        util.ensure_mode_is('OBJECT')
        fr = 1 if self.toggle_direction else 0
        to = 0 if fr else 1
        axis = int(self.symmetry_axis)

        me = obj.data
        verts = me.vertices
        oldval = Vector(verts[pair[to]].co)
        newval = Vector(verts[pair[fr]].co)
        newval[axis] = -newval[axis]

        log.warning("Fixed symmetry on %s from %s to %s" % (self.symmetry_axis, oldval, newval) )
        bpy.context.object.update_from_editmode()
        verts[pair[to]].co = newval
        util.ensure_mode_is(omode)

        return{'FINISHED'}    

def findWeightProblemVertices(context, obj, use_sl_list=True, armature=None, find_selected_armature=False, max_weight=4, only_deform=True, minweight=0):
    
    def add_non_deforming_group(groupset, bonename):
        if bonename not in groupset:
            groupset[bonename] = 1
        else:
            groupset[bonename] = groupset[bonename] + 1


    #





    #



    if obj.mode=='EDIT':
        obj.update_from_editmode()

    report = {'status':[], 'unweighted':[], 'zero_weights':[], 'too_many':[]}
    

    if only_deform and armature is None:
        armature = util.getArmature(obj)
        

        if armature is None and find_selected_armature:
            for tmp in context.selected_objects:
                if tmp.type == 'ARMATURE':
                    armature = tmp
                    break

        if armature is None:



            report['status'].extend(('no_armature','unweighted'))


    report['undeformable'] = {}
    for v in obj.data.vertices:
        deforming = 0
        zero = 0  # :)
        if len(v.groups) == 0:
            report['unweighted'].append(v.index)
        else:
            for g in v.groups:
                try:
                    bonename = obj.vertex_groups[g.group].name
                    if armature == None or (bonename in armature.data.bones and armature.data.bones[bonename].use_deform):
                        deforming += 1 # count Number of deform bones for this vertex
                        if g.weight <= minweight:
                            zero += 1 # Count numberof zero weights for this vertex
                    elif armature and (bonename in armature.data.bones and not armature.data.bones[bonename].use_deform):
                        add_non_deforming_group(report['undeformable'] , bonename) 
                except:

                    pass
                    
            if deforming == 0:
                report['unweighted'].append(v.index)
            if deforming > max_weight:
                report['too_many'].append(v.index)
            if zero == deforming:

                report['zero_weights'].append(v.index)

    if len(report['undeformable']) > 0:
        report['status'].append('undeformable')
    if len(report['unweighted']) > 0:
        report['status'].append('unweighted')
    if len(report['zero_weights']) > 0:
        report['status'].append('zero_weights')
    if len(report['too_many']) > 0:
        report['status'].append('too_many')
        
    return report


def findUnweightedVertices(context, obj, use_sl_list=True, arm=None):



    if arm is None:
        arm = util.getArmature(obj)


    if arm is None:
        return [v.index for v in obj.data.vertices], NO_ARMATURE 
    
    unweighted = []

    excludes = []
    rig_sections = [B_EXTENDED_LAYER_ALL]
    
    deform_bones = data.get_deform_bones(arm, rig_sections, excludes) if use_sl_list else []
    
    status = WEIGHTS_OK
    for v in obj.data.vertices:
        tot = 0.0
        for g in v.groups:
            bonename = obj.vertex_groups[g.group].name

            if bonename in arm.data.bones and arm.data.bones[bonename].use_deform:
                if use_sl_list:
                    if bonename in deform_bones:
                        tot += g.weight
                else:
                    tot += g.weight

        if tot==0:
            unweighted.append(v.index)
            status = MISSING_WEIGHTS

    return unweighted, status


class ButtonFreezeShape(bpy.types.Operator):
    bl_idname = "avastar.freeze_shape"
    bl_label = "Freeze Selected"
    bl_description = "Create a copy of selected mesh Objects with shapekeys and pose applied"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        freeze_selection(context, self)
        return{'FINISHED'}

def freeze_selection(context, operator=None, targets=None):
    osuppress_handlers = util.set_disable_handlers(context.scene, True)
    try:
        armature = util.get_armature(context.object)
        result = freezeSelectedMeshes(context, operator, targets=targets)
        props = context.scene.MeshProp
        if armature:
            if  props.standalonePosed and props.removeArmature:
                util.remove_object(context, armature, do_unlink=True, recursive=True)
            else:
                for obj in result:
                    shape.reset_weight_groups(obj)
                    shape.init_custom_bones(obj, armature)
    finally:
        util.set_disable_handlers(context.scene, osuppress_handlers)


class ButtonConvertShapeToCustom(bpy.types.Operator):
    bl_idname = "avastar.convert_to_custom"
    bl_label = "Convert to Custom"
    bl_description = "Convert Selected Avastar Meshes to editable and fittable Custom Meshes (undo: CTRL-z)\n\nNotes:\nSelected Avastar Meshes are copied\nAvastar Originals are Deleted\nSliders are attached\nShape keys are removed"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            freezeSelectedMeshes(context, self, apply_pose=False, remove_weights=False, join_parts=False, appearance_enabled=True, handle_source='HIDE')
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}



def bake_t_pose(self, context, arm):

    M = None
    bname = None
    M_pose = None
    M_data = None
    print("bake_t_pose: Start a t-pose bake")
    try:
        scn = context.scene
    
        currentSelection = util.getCurrentSelection(context)
        avastars         = currentSelection['avastars']
        targets          = currentSelection['targets']
        detached         = currentSelection['detached']
        others           = currentSelection['others']
        active           = currentSelection['active']

        print("bake_t_pose: Armature is in %s_Position" % arm.data.pose_position)

        AMW  = arm.matrix_world
        AMWI = AMW.inverted()


        for target in detached:

            report = findWeightProblemVertices(context, target, use_sl_list=False, find_selected_armature=True)                
            if 'unweighted' in report['status']:
                print("bake_t_pose: Found unweighted verts in %s" % target.name)
                unweighted = report['unweighted']
                raise util.MeshError(msg_unweighted_verts%(len(unweighted), target.name))
            if 'zero_weights' in report['status']:
                print("bake_t_pose: Found zero weights in %s" % target.name)
                zero_weights = report['zero_weights']
                raise util.MeshError(msg_zero_verts%(len(zero_weights), target.name))        

        rig_sections = [B_EXTENDED_LAYER_ALL]
        excludes = [B_LAYER_VOLUME, B_EXTENDED_LAYER_SL_EYES, B_EXTENDED_LAYER_ALT_EYES]
        deform_bones = data.get_deform_bones(arm, rig_sections, excludes)

        for target in detached:
            print("bake_t_pose: Alter [%s] to Rest Pose" % (target.name) )
            
            TMW  = target.matrix_world
            TMWI = TMW.inverted()


            failed_vert_transforms = 0
            for v in target.data.vertices:

                totw = 0
                for g in v.groups:
                    bname = target.vertex_groups[g.group].name
                    if bname in deform_bones:
                        totw+=g.weight

                M = Matrix(((0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)))
                matrix_populated = False
                if totw > 0:
                    for g in v.groups:
                        bname = target.vertex_groups[g.group].name
                        if bname in deform_bones:
                            w = g.weight


                            M_pose = arm.pose.bones[bname].matrix
                            M_data = arm.data.bones[bname].matrix_local

                            M = M + mulmat(w/totw, TMWI, AMW, M_pose, M_data.inverted(), AMWI, TMW)
                            matrix_populated = True
                if matrix_populated:
                    v.co = M.inverted()*v.co
                else:
                    failed_vert_transforms += 1                
            if failed_vert_transforms > 0:
                print("Failed to convert %d  of %d vertices in Object %s" % (failed_vert_transforms, len(target.data.vertices), target.name ))
            else:
                print("Converted all %d vertices in Object %s" % (len(target.data.vertices), target.name ))



        print("bake_t_pose: reparenting targets...")
        excludes = []
        rig_sections = [B_EXTENDED_LAYER_ALL]
        bind_to_armature(self, context, arm, rig_sections, excludes)


        util.set_active_object(context, active)
        print("bake_t_pose: Alter to restpose finished.")
        
    except Exception as e:
        print ("Exception in bake_t_pose")
        print ("bone was:", bname)
        print ("M:", M)
        print ("M_pose:", M_pose)
        print ("M_data:", M_data)
        util.ErrorDialog.exception(e)

def get_keyblock_values(ob):
    print("Get keyblock values for [",ob,"]")
    if ob.data.shape_keys and ob.data.shape_keys.key_blocks:
        key_values = [b.value for b in ob.data.shape_keys.key_blocks]
    else:
        key_values = []
    return key_values
    


def revertShapeSlider(context, obj):
    success_armature_name = None

    if obj.ObjectProp.slider_selector!='NONE':
        arm=obj.find_armature()
        if arm and "avastar" in arm:

            shape_filename = arm.name #util.get_shape_filename(name)
            if shape_filename in bpy.data.texts:
                shape.ensure_drivers_initialized(arm)
                shape.loadProps(context, arm, shape_filename, pack=True)
                success_armature_name = arm.name
            shape.detachShapeSlider(obj)

    return success_armature_name



class ButtonApplyShapeSliders(bpy.types.Operator):
    bl_idname = "avastar.apply_shape_sliders"
    bl_label = "Detach"
    bl_description = messages.Operator_apply_shape_sliders
    bl_options = {'REGISTER', 'UNDO'}

    @staticmethod
    def exec_imp(context, arms, objs):
        active_name = context.object.name
        amode = context.object.mode
        oselector = util.set_disable_update_slider_selector(True)
        frozen_obs=objs







        for arm in arms:
            if arm.name in bpy.data.texts:
                objs = [child for child in util.getCustomChildren(arm, type='MESH')]
                if len(objs) == 0:
                    text = bpy.data.texts[arm.name]
                    util.remove_text(text, do_unlink=True)
        util.set_disable_update_slider_selector(False)

        for arm in arms:
            util.set_active_object(context, arm)
            arm.ObjectProp.slider_selector='SL'

        propgroups.update_sliders(context, arms=arms, objs=frozen_obs)

        util.set_disable_update_slider_selector(oselector)
        util.set_active_object(context, context.scene.objects.get(active_name))
        util.ensure_mode_is(amode)
        return frozen_obs

    def execute(self, context):
        active_name = context.object.name
        amode = context.object.mode

        arms, objs = util.getSelectedArmsAndObjs(context)
        ButtonApplyShapeSliders.exec_imp(context, arms, objs)

        util.set_active_object(context, context.scene.objects.get(active_name))
        util.ensure_mode_is(amode)

        return{'FINISHED'}


class CleanupCustomProps(bpy.types.Operator):
    bl_idname      = "avastar.cleanup_custom_props"
    bl_label       = "Cleanup"
    bl_description = '''Remove Avastar internal data.
This cleans up the meshes from all Avastar related information.

Important (applies when you have generated weightmaps with the fitting panel):

When you intend to rebind the mesh to another Avastar Rig, 
then please do not cleanup the data!
'''
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context and context.object and context.object.type=='MESH'

    def execute(self, context):
        for ob in [ o for o in context.scene.objects if o.select_get()]:
            omode=util.ensure_mode_is("OBJECT")
            cleanupAvastarData(ob, purge=True, restore=False)
        util.update_view_layer(context)
        util.ensure_mode_is(omode)

        return{'FINISHED'}
        

class ButtonUnParentArmature(bpy.types.Operator):
    bl_idname = "avastar.unparent_armature"
    bl_label = "Unbind"
    bl_description = \
'''Convenience method to remove armature modifier (and parenting) from selected

Tip: This operator preserves the Weights of your meshes,
     when you bind again, then use the keep weights option'''

    bl_options = {'REGISTER', 'UNDO'}

    apply_armature_on_unbind : g_apply_armature_on_unbind 

    all : BoolProperty(
             default     = False,
             name        = "All Meshes",
             description = "Unbind also hidden Meshes")
             
    purge_data_on_unbind : g_purge_data_on_unbind
    break_parenting_on_unbind : g_break_parenting_on_unbind

    def execute(self, context):
        arms = util.getSelectedArms(context)
        active_name = util.get_active_object(context).name
        amode = util.ensure_mode_is("OBJECT")

        select = None if self.all else True
        visible = None if self.all else True
        type = 'MESH'

        selected_object_names = [ob.name for ob in context.selected_objects]

        for armobj in arms:
            util.set_active_object(context, armobj)

            selection = util.get_animated_meshes(context, armobj, only_selected=select, only_visible=select)
            if not selection:
                selection = util.getChildren(armobj, type, None, visible)

            unbind_from_armature(self,
                                 context,
                                 attached=selection,
                                 freeze=self.apply_armature_on_unbind,
                                 purge=self.purge_data_on_unbind,
                                 break_parenting_on_unbind=self.break_parenting_on_unbind)
        for ob in context.scene.objects:
            util.object_select_set(ob, ob.name in selected_object_names)

        active = context.scene.objects.get(active_name)
        if active:
            util.set_active_object(context, active)
        util.ensure_mode_is(amode)

        return{'FINISHED'}


def unbind_from_armature(operator, context, attached, freeze=False, purge=False, keep_avastar_properties=False, break_parenting_on_unbind=True):
    if len(attached) == 0:
        return None 


    active_name = util.get_active_object(context).name
    amode = util.ensure_mode_is("OBJECT")

    bpy.ops.object.select_all(action='DESELECT')
    backup = util.get_select_and_hide(attached, False, False, False)    

    if freeze:
        for target in attached:
            util.object_select_set(target, True)
        result = freezeSelectedMeshes(context, operator, apply_pose=True, remove_weights=False, join_parts=False, handle_source='DELETE', purge=purge)
    else:    




        for target in attached:
            util.set_active_object(context, target)
            util.object_select_set(target, True)
            omode = util.ensure_mode_is("OBJECT")

            parent = target.parent
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            log.debug("unbind from armature:unparented %s" % (target.name) )

            for mod in [ mod for mod in target.modifiers if mod.type=='ARMATURE']:
                bpy.ops.object.modifier_remove(modifier=mod.name)
 
            if parent and not break_parenting_on_unbind:
                util.set_active_object(context, parent)
                bpy.ops.object.parent_set()

            util.object_select_set(target, False)
            log.debug("unbind from armature:removed armature modifiers from %s" % (target.name) )
            
            if keep_avastar_properties and util.is_avastar_mesh(target):
                pass
            else:
                cleanupAvastarData(target, purge, restore=False)
                log.debug("unbind from armature: cleaned avastar data from %s" % (target.name) )

            util.ensure_mode_is(omode)



        result = attached

    util.set_select_and_hide(context, backup)
    active = context.scene.objects.get(active_name)
    if active:
        util.set_active_object(context, active)
        util.object_select_set(active, True)
    util.ensure_mode_is(amode)

    operator.report({'INFO'},"Unparented %d meshes from Armature"% len(attached))
    
    return result

def bind_to_armature(self,
                     context,
                     armature,
                     rig_sections,
                     excludes,
                     keep_empty_groups=False,
                     enforce_meshes=None,
                     bindSourceSelection=None,
                     attach_set = None):

    def adjust_deform_flag(bone_names, section, deform_state):

        bones = armature.data.bones
        for bone_name in bone_names:
            if bone_name in bones:
                deform_state[bone_name] = bones[bone_name].use_deform
                bones[bone_name].use_deform = not section in excludes



    def setup_armature_modifier(armature, target, preserve_volume):

        amc = 0
        for mod in [ mod for mod in target.modifiers if mod.type=='ARMATURE' and mod.object==armature]:
            mod.use_vertex_groups  = True
            mod.use_bone_envelopes = False
            amc += 1

        if amc == 0:



            mod = util.create_armature_modifier(target, armature, name=armature.name, preserve_volume=preserve_volume)

    wcontext = weights.setup_weight_context(self, context, armature, copyWeightsToSelectedVerts=False)
    if bindSourceSelection:
        wcontext.weightSourceSelection = bindSourceSelection #not sure here
        wcontext.bindSourceSelection = bindSourceSelection



    currentSelection = util.getCurrentSelection(context)

    if not attach_set:
        attach_set = currentSelection['detached']
    if not attach_set:
        print("No Objects selected for binding to Armature %s" % armature.name)
        return

    avastars         = currentSelection['avastars']
    targets          = currentSelection['targets']
    others           = currentSelection['others']
    active           = currentSelection['active']
    amode = util.ensure_mode_is("OBJECT")


    util.set_active_object(context, armature)
    omode = util.ensure_mode_is("OBJECT")
    bpy.ops.object.select_all(action='DESELECT')
    util.object_select_set(armature, True)


    parented_count = 0

    if wcontext.bindSourceSelection == None or wcontext.bindSourceSelection == 'NONE':
        for target in attach_set:
            print("Checking fitted mesh for %s to %s" % (target.name, armature.name) )
            if target.vertex_groups:
                vnames = [g.name for g in target.vertex_groups if g.name in SLVOLBONES]
                if len(vnames) > 0:
                    print("Target %s uses fitted mesh maps" % (target.name) )
                    weights.setDeformingBones(armature, data.get_volume_bones(only_deforming=False), replace=False)
                    if B_LAYER_VOLUME in excludes:
                        excludes.remove(B_LAYER_VOLUME)
                    break

    for target in attach_set:
        parented_count += 1
        shape.reset_weight_groups(target)
        util.object_select_set(target, True)
        util.transform_origins_to_target(context, armature, [target])
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

        preserve_volume = target.get('use_deform_preserve_volume', False)
        if preserve_volume:
            mods = [mod for mod in target.modifiers if mod.type=='ARMATURE']
            for mod in mods:
                mod.use_deform_preserve_volume = preserve_volume
                print("restored %s.mod.use_deform_preserve_volume = %s" % ( target.name, target['use_deform_preserve_volume']))

        setup_armature_modifier(armature, target, preserve_volume)
        util.tag_addon_revision(target)



        weighted_bones = data.get_deform_bones(target, rig_sections, excludes)
        deform_state={}
        adjust_deform_flag(SL_EYE_BONES, B_EXTENDED_LAYER_SL_EYES, deform_state)
        adjust_deform_flag(SL_ALT_EYE_BONES, B_EXTENDED_LAYER_ALT_EYES, deform_state)
        adjust_deform_flag(SL_SPINE_LOWER_BONES, B_EXTENDED_LAYER_SPINE_LOWER, deform_state)
        adjust_deform_flag(SL_SPINE_UPPER_BONES, B_EXTENDED_LAYER_SPINE_UPPER, deform_state)

        wcontext.target = target
        wcontext.weighted_bones = weighted_bones
        wcontext.rig_sections = rig_sections
        wcontext.excludes = excludes
        wcontext.copyWeightsToSelectedVerts = False
        weights.create_weight_groups(wcontext, for_bind=True)

        for bone_name in deform_state:
            armature.data.bones[bone_name].use_deform = deform_state[bone_name]

        if not target.get('FittingValues'):


            weights.classic_fitting_preset(target)

        target.ObjectProp.fitting = not weights.has_collision_volumes(target.vertex_groups.keys())
        util.object_select_set(target, False)

        hover = shape.get_floor_hover(armature, use_cache=False)
        if not util.is_avastar_mesh(target):
            shape.init_custom_bones(target, armature, hover=hover)

        shape.copy_shape_to_object(target, armature)




    for o in targets + others:
        util.object_select_set(o, True)

    util.ensure_mode_is(omode)
    util.set_active_object(context, active)
    util.ensure_mode_is(amode)

    if parented_count == 0:
        raise util.Warning("All Meshes already parented.|ACTION: If you want to reparent a Mesh, then do:\n  1.) Remove the armature modifer (from the modifier stack)\n  2.) Unparent the armature: Object -> Parent -> Clear.\nThen try again.|parent_armature")
    else:
        log.info("Parented %d Objects to Armature %s" % (parented_count, armature.name))



class ButtonParentArmature(bpy.types.Operator):
    bl_idname = "avastar.parent_armature"
    bl_label = "Bind to Armature"
    bl_description = \
'''Convenience method to add armature modifier
This Operator is mostly equivalent to

Object -> Parent -> Armature Deform -> ...

but also prepares the meshes to be used with Avatar Shape'''

    bl_options = {'REGISTER', 'UNDO'}

    weight_mapping : g_weight_mapping
    bindSourceSelection : g_bindSourceSelection
    weightBoneSelection : g_weightBoneSelection

    clearTargetWeights : BoolProperty(name="Clear weights",
        description = "Clear weightmaps for Target bones before adding new Weights",
        default=True)

    weight_base_bones : weights.g_weight_base_bones
    weight_eye_bones : weights.g_weight_eye_bones
    weight_alt_eye_bones : weights.g_weight_alt_eye_bones
    weight_face_bones : weights.g_weight_face_bones
    weight_groin : weights.g_weight_groin
    weight_visible : weights.g_weight_visible
    weight_tale : weights.g_weight_tale
    weight_wings : weights.g_weight_wings
    weight_hinds : weights.g_weight_hinds
    weight_hands : weights.g_weight_hands
    weight_volumes : weights.g_weight_volumes
    keep_groups : weights.g_keep_groups
    with_hidden_avastar_meshes : weights.g_with_hidden_avastar_meshes
    with_listed_avastar_meshes : weights.g_with_listed_avastar_meshes


    toTPose      : BoolProperty(name="Alter To Restpose (deprecated)",
                   description = "Bend and rebind the mesh into T-Pose\ndeprecated, please use bind to Pose instead",
                   default=False)

    @staticmethod
    def draw_parent_redo(op, context, currentSelection, skinning_box):
        armobj = util.guessArmature(context)
        if armobj == None:
            return

        obj = context.object
        
        if op:
            skelProp = op
            meshProp = op
        else:
            scn = context.scene
            skelProp = scn.SkeletonProp
            meshProp = scn.MeshProp


        col = skinning_box.column(align=True)
        weights.ButtonGenerateWeights.weightmap_bind_panel_draw(armobj, context, col, op=op, is_redo=True)

    def draw(self, context):
        layout = self.layout
        currentSelection = util.getCurrentSelection(context)
        ButtonParentArmature.draw_parent_redo(self, context, currentSelection, layout)

    def invoke(self, context, event):
        log.warning("Invoke parent_armature start")
        ui_level = util.get_ui_level()
        meshProps = context.scene.MeshProp
        skeletonProps = context.scene.SkeletonProp

        self.bindSourceSelection = meshProps.bindSourceSelection
        self.weight_mapping = meshProps.weight_mapping if meshProps.weight_mapping else 'POLYINTERP_NEAREST'
        self.clearTargetWeights = meshProps.clearTargetWeights
        self.weight_visible = skeletonProps.weight_visible
        self.weight_groin = skeletonProps.weight_groin

        weights.assign_weight_properties(self, skeletonProps)
        
        self.toTPose = ui_level > UI_ADVANCED and meshProps.toTPose
        log.warning("Invoke parent_armature end")
        return self.execute(context)

    def execute(self, context):

        with set_context(context, context.object, 'OBJECT'):
            currentSelection = util.getCurrentSelection(context)
            avastars         = currentSelection['avastars']
            targets          = currentSelection['targets']
            detached         = currentSelection['detached']
            others           = currentSelection['others']
            active           = currentSelection['active']

            if len(avastars)>1:
                raise util.Error("More than one armature selected.|Make sure you select a single armature.|parent_armature")

            if len(targets) == 0:
                msg = "No Meshes selected to bind to"
                log.warning(msg)
                self.report({'INFO'},(msg))
                return {'FINISHED'}
            else:
                for target in targets:

                    shape.detachShapeSlider(target, reset=False)

            meshProps = context.scene.MeshProp
            skelProps = context.scene.SkeletonProp

            if self.bindSourceSelection == 'AVASTAR':
                enforce_meshes = ["headMesh", "lowerBodyMesh", "upperBodyMesh"]
            else:
                enforce_meshes = None

            arm = avastars[0]

            rig_sections, excludes = weights.assign_extended_section(self, all_sections=True, discard_volumes=self.bindSourceSelection!='COPY')
            if arm.RigProp.spine_unfold_lower or arm.RigProp.spine_unfold_upper :

                rig_sections.append(B_LAYER_DEFORM_SPINE)
                if not arm.RigProp.spine_unfold_lower:

                    excludes.append(B_EXTENDED_LAYER_SPINE_LOWER)
                if not arm.RigProp.spine_unfold_upper:

                    excludes.append(B_EXTENDED_LAYER_SPINE_UPPER)

            if self.bindSourceSelection=='AUTOMATIC' and not self.weight_groin:
                excludes.append(B_LAYER_DEFORM_GROIN)

            if self.bindSourceSelection=='AUTOMATIC' and self.weight_visible:
                util.ensure_mode_is('POSE', object=arm)
                invisible_deform_bones = []
                for mbone in arm.data.bones:
                    cbone = arm.data.bones.get(mbone.name[1:], mbone)
                    if mbone.name == 'mGroin':
                        continue
                    if util.bone_is_visible(arm,cbone) or  util.bone_is_visible(arm,mbone):
                        continue
                    if not mbone.use_deform:
                        continue
                    invisible_deform_bones.append(mbone.name)

                for b in invisible_deform_bones :
                    arm.data.bones[b].use_deform=False
            else:
                invisible_deform_bones = []
            

            try:
                bind_to_armature(self,
                    context,
                    arm,
                    rig_sections,
                    excludes,
                    enforce_meshes=enforce_meshes,
                    bindSourceSelection = self.bindSourceSelection)
            except:
                self.report({'ERROR'}, "Bind to Armature failed")
                return {'CANCELLED'}

            for b in invisible_deform_bones :
                    arm.data.bones[b].use_deform=True

            if not 'bindpose' in arm:
                if self.toTPose:

                    unbind_from_armature(self, context, targets)
                    util.set_active_object(context, arm)
                    bake_t_pose(self, context, arm)

                arm.ObjectProp.slider_selector = 'SL'
                util.set_active_object(context, active)
                bpy.types.AVASTAR_MT_fitting_presets_menu.bl_label='Fitting Presets'

        return {'FINISHED'}


class ButtonRebindArmature(bpy.types.Operator):
    bl_idname = "avastar.rebind_armature"
    bl_label = "Rebind"
    bl_description = messages.avastar_reparent_armature_description_rebind
    bl_options = {'REGISTER', 'UNDO'}

    apply_as_bindshape : g_apply_as_bindshape

    @classmethod
    def description(cls, context, properties):
        if properties.apply_as_bindshape:
            detail = messages.avastar_reparent_armature_description_rebind
        else:
            detail = messages.avastar_reparent_armature_description_keep
        
        return messages.avastar_reparent_armature_description % detail

    @staticmethod
    def get_scope(context):
        selected = util.get_select(context)
        scope = list(selected)
        if selected:

            armatures = [a for a in selected if a.type=='ARMATURE']
            for arm_obj in armatures:
                animated_meshes = util.get_animated_meshes(context, arm_obj, only_visible=False)
                scope.extend(util.get_selection_recursive(animated_meshes))
            scope = set(scope)

        scope = [o for o in scope if o.type=='MESH' and not 'avastar-mesh' in o]


        return selected, scope

    @staticmethod
    def execute_rebind(context, apply_as_bindshape):
        ostate = util.set_disable_handlers(context.scene, True)
        try:
            selected, scope = ButtonRebindArmature.get_scope(context)
            active = util.get_active_object(context)
            amode = util.ensure_mode_is('OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            for child in scope:
                log.warning("Reset shape definitions for %s" % child.name)
                armobj = child.find_armature()

                original_shape_dict = child.get('shape_buffer')
                current_shape_dict = shape.asDictionary(armobj, full=True) if armobj else None

                util.reset_dirty_mesh(context, child)
                shape.reset_weight_groups(child)
                if armobj:
                    shape.init_custom_bones(child, armobj)
                    shape.generateMeshShapeData(child)

                if apply_as_bindshape or not original_shape_dict:
                    child['shape_buffer'] = current_shape_dict
                else:
                    child['shape_buffer'] = original_shape_dict
                    shape.fromDictionary(armobj, original_shape_dict)
                    shape.init_custom_bones(child, armobj)
                    shape.generateMeshShapeData(child)
                    shape.fromDictionary(armobj, current_shape_dict, update=True, init=False)

            util.set_select(selected, reset=True)
            util.set_active_object(context, active)
            util.ensure_mode_is(amode)

        finally:
            util.set_disable_handlers(context.scene, ostate)

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        ButtonRebindArmature.execute_rebind(context, self.apply_as_bindshape)
        return {'FINISHED'}

class ButtonReparentArmature(bpy.types.Operator):
    bl_idname = "avastar.reparent_armature"
    bl_label = "Rebind"
    bl_description = messages.avastar_reparent_armature_description_rebind
    bl_options = {'REGISTER', 'UNDO'}

    include_children : BoolProperty(name="Include Children",
                   description = "Also reparent all children of current selection (recursively)",
                   default=False)
    
    def execute(self, context):
        def get_target_armature(context, avastars):
            ob = context.object
            if ob and ob.type == 'ARMATURE' and 'avastar' in ob:
                arm_obj = ob
            elif avastars:
                arm_obj = avastars[0]
            else:
                arm_obj = util.get_armature(ob)
            return arm_obj

        def get_scope(context, targets):
            selected = util.get_select(context)
            if targets:
                scope = list(targets)
            else:
                scope = list(selected)
                if selected:

                    armatures = [a for a in selected if a.type=='ARMATURE']
                    for arm_obj in armatures:
                        animated_meshes = util.get_animated_meshes(context, arm_obj, only_visible=False)
                        scope.extend(util.get_selection_recursive(animated_meshes))
                    scope = set(scope)

            scope = [o for o in scope if o.type=='MESH' and not 'avastar-mesh' in o]


            return selected, scope

        o_slider_state = util.get_disable_update_slider_selector()
        currentSelection = util.getCurrentSelection(context)
        avastars         = currentSelection['avastars']
        targets          = currentSelection['targets']
        detached         = currentSelection['detached']
        others           = currentSelection['others']
        active = util.get_active_object(context)
        active_name      = active.name if active else None
        amode            = util.ensure_mode_is('OBJECT')

        try:
            arm_obj = get_target_armature(context, avastars)
            if not arm_obj:
                msg = "reparent_armature: No Meshes selected to rebind"
                log.warning(msg)
                self.report({'INFO'},(msg))
                return {'FINISHED'}

            need_parenting = False
            selected, scope = get_scope(context, targets)                 
            bpy.ops.object.select_all(action='DESELECT')
            util.set_disable_update_slider_selector(True)

            log.debug("scope is: %s" % scope)
            for target in scope:
                log.warning("Delete shape definitions from %s" % target.name)
                shape.detachShapeSlider(target, reset=True)
                if not util.is_child_of(arm_obj, target):
                    util.object_select_set(target, True)
                    need_parenting = True
                    log.warning("Make %s child of %s" % (target.name, arm_obj.name) )

            if need_parenting:
                util.object_select_set(arm_obj, True)
                util.set_active_object(context, arm_obj)
                omode = util.ensure_mode_is("OBJECT")
                bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

            bpy.ops.object.select_all(action='DESELECT')
            util.set_select(selected)

            arm_obj.ObjectProp.slider_selector = 'NONE'

            if not 'bindpose' in arm_obj:

                arm_obj.ObjectProp.slider_selector = 'SL'
                util.set_active_object(context, active)
                bpy.types.AVASTAR_MT_fitting_presets_menu.bl_label='Fitting Presets'

            scope = ButtonApplyShapeSliders.exec_imp(context, [arm_obj], scope)
            active = context.scene.objects.get(active_name)

        finally:
            if active_name:
                active = context.scene.objects.get(active_name)
                util.set_active_object(context, active)
                util.ensure_mode_is(amode)
            util.set_disable_update_slider_selector(o_slider_state)

        return {'FINISHED'}

class ButtonReparentMesh(bpy.types.Operator):

    object_name : StringProperty()

    bl_idname = "avastar.reparent_mesh"
    bl_label = "Rebind Mesh to Armature"
    bl_description = messages.avastar_reparent_mesh_description
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target = context.scene.objects.get(self.object_name)
        if not target:
            log.warning("Could not find Mesh %s for rebind" % (object_name))
            return {'CANCELLED'}

        armobj = util.get_armature(target)
        cactive = util.get_active_object(context)
        cmode = cactive.mode

        if armobj:
            try:
                util.change_active_object(context, armobj, new_mode='OBJECT', msg="reparent1:")
                if not util.is_child_of(armobj, target):
                    selected = util.get_select(context)
                    active = util.get_active_object(context)
                    amode = active.mode
                    util.set_active_object(context, armobj)
                    omode = util.ensure_mode_is("OBJECT")
                    bpy.ops.object.select_all(action='DESELECT')
                    util.object_select_set(target, True)
                    util.object_select_set(armobj, True)
                    bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
                    bpy.ops.object.select_all(action='DESELECT')
                    util.set_select(selected)
                    util.ensure_mode_is(omode)

                updateBindpose(context, target, armobj) 
            finally:
                util.change_active_object(context, cactive, new_mode=cmode, msg="reparent2:")
        else:
            log.warning("Object %s marked as dirty_mesh but is not assigned to Armature" % target.name)
        util.reset_dirty_mesh(context, target)
        shape.reset_weight_groups(target)

        return {'FINISHED'}

def updateBindpose(context, obj, armobj):
    shape_buffer = shape.asDictionary(armobj, full=True)
    shape.resetToBindpose(armobj, context)
    shape.init_custom_bones(obj, armobj, all_verts=True)
    shape.fromDictionary(armobj, shape_buffer, update=True)






#

#
#




#




#













#

#












#







def SLBoneDeformStates(armobj):
    try:
        selected_bones = util.getVisibleSelectedBones(armobj)
        if len(selected_bones) == 0:
            return '', ''
        deform_count = len([b for b in selected_bones if b.use_deform == True])
        all_count  = len(selected_bones)
        if deform_count==0:
            return 'Disabled', 'Enable'
        if deform_count == all_count:
            return 'Enabled', 'Disable'
        return 'Partial', ''
    except:
        pass
    return "", ""


class ButtonArmatureAllowStructureSelect(bpy.types.Operator):
    bl_idname = "avastar.armature_allow_structure_select"
    bl_label = "Allow Structure Bone Select"
    bl_description = "Allow Selecting Structure bones"

    def execute(self, context):
    
        active, armobj = rig.getActiveArmature(context)
        if armobj is None:
            self.report({'WARNING'},"Active Object %s is not attached to an Armature"%active.name)
        else:
            mode = active.mode
            util.mode_set(mode='POSE', toggle=True)
        
            try:
                rig.setSLBoneStructureRestrictSelect(armobj, False)
            except Exception as e:
                util.ErrorDialog.exception(e)
                
            util.mode_set(mode=mode, toggle=True)  
                
        return{'FINISHED'}    
        

class ButtonArmatureRestrictStructureSelect(bpy.types.Operator):
    bl_idname = "avastar.armature_restrict_structure_select"
    bl_label = "Restrict Structure Bone Select"
    bl_description = "Restrict Selecting Structure bones"

    def execute(self, context):

        active, armobj = rig.getActiveArmature(context)
        if armobj is None:
            self.report({'WARNING'},"Active Object %s is not attached to an Armature"%active.name)
        else:
            mode = active.mode
            util.mode_set(mode='POSE', toggle=True)

            try:
                rig.setSLBoneStructureRestrictSelect(armobj, True)
            except Exception as e:
                util.ErrorDialog.exception(e)
                
            util.mode_set(mode=mode, toggle=True)  
                
        return{'FINISHED'}

def draw_constraint_set(op, context):
        col = op.layout.column()
        col.prop(op,"ConstraintSet")


class ButtonArmatureUnlockLocation(bpy.types.Operator):
    bl_idname      = "avastar.armature_unlock_loc"
    bl_label       = "Unlock Locations"
    bl_description = '''Unlock Control Bones for unconstrained animation.
    Can be helpful for face animations.
    
    Warning: This mode overrides the Avatar shape for custom meshes!
    You might see shape changes on the Face and hands!
    '''
    bl_options = {'REGISTER', 'UNDO'}

    reset_pose : BoolProperty(
            name        = "Reset to Restpose",
            description = "Reset the pose to Restpose before locking",
            default     = False)    

    def execute(self, context):
        armobj = util.get_armature(context.object)
        try:
            omode = util.ensure_mode_is('POSE')
            rig.setSLBoneLocationMute(self, context, True, armobj.RigProp.ConstraintSet)
            if self.reset_pose:
                bpy.ops.pose.transforms_clear()
            util.ensure_mode_is(omode)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}    
        

class ButtonArmatureUnlockVolume(bpy.types.Operator):
    bl_idname = "avastar.armature_unlock_vol"
    bl_label = "Lock Volumes"
    bl_description = "Unlock Volume Bone locations for unconstrained animation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armobj = util.get_armature(context.object)
        try:
            rig.setSLBoneVolumeMute(self, context, False, armobj.RigProp.ConstraintSet)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}    
        

class ButtonArmatureUnlockRotation(bpy.types.Operator):
    bl_idname = "avastar.armature_unlock_rot"
    bl_label = "Unlock Rotations"
    bl_description = '''Unlock SL Base bone rotations from Control Bone rotations
    Helpful only for Weighting tasks.
    
    Warning: NEVER(!) use this for animating the base bones!
    Use the Pose preset (in the rigging display panel) for animating your Rig'''
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armobj = util.get_armature(context.object)
        try:
            rig.setSLBoneRotationMute(self, context, True, armobj.RigProp.ConstraintSet)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}    
        

class ButtonArmatureLockRotation(bpy.types.Operator):
    bl_idname = "avastar.armature_lock_rot"
    bl_label = "Lock Rotations"
    bl_description = "Synchronize Deform bone rotations to Control Bone rotations\nPlease use this setup for posing and animating"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armobj = util.get_armature(context.object)
        try:
            rig.setSLBoneRotationMute(self, context, False, armobj.RigProp.ConstraintSet)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}    
        

class ButtonArmatureLockLocation(bpy.types.Operator):
    bl_idname = "avastar.armature_lock_loc"
    bl_label = "Lock Locations"
    bl_description = "Lock Control Bone locations (to allow only the animation of bone rotations)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:

            armobj = util.get_armature(context.object)
            oactive, omode = util.change_active_object(context, armobj)

            util.ensure_mode_is('POSE')
            rig.setSLBoneLocationMute(self, context, False, armobj.RigProp.ConstraintSet)

            util.change_active_object(context, oactive, omode)

        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}    
        

class ButtonArmatureLockVolume(bpy.types.Operator):
    bl_idname = "avastar.armature_lock_vol"
    bl_label = "Lock Volumes"
    bl_description = "Lock Volume Bone locations (to allow only the animation of bone rotations)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armobj = util.get_armature(context.object)
        try:
            rig.setSLBoneVolumeMute(self, context, True, armobj.RigProp.ConstraintSet)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}
        


class ButtonArmatureResetPoseLSL(bpy.types.Operator):
    bl_idname = "avastar.armature_reset_pose_lsl"
    bl_label = "Generate LSL Resetter"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description =\
'''Generate Restpose Adjustment LSL Script.
   Usage:
   
   1.) Click button: script is now in paste buffer
   2.) Add new LSL script to your model in SL
   3.) In LSL Editor Paste
   4.) Save and enable the Script
   5.) Add generated restpose to Inventory
'''

    def draw(self, context):
        layout = self.layout
        col=layout.column(align=True)
        col.label(text="The script is in")
        col.label(text="your Paste Buffer.")
        col.label(text="Now open an LSL Editor")
        col.label(text="in SL and Paste the") 
        col.label(text="Script (80 lines)")
    
    def execute(self, context):
        context.window_manager.clipboard=pose_reset_script_lsl
        return{'FINISHED'}


class ButtonSupportInfo(bpy.types.Operator):
    bl_idname = "avastar.copy_support_info"
    bl_label = "Copy Support Info"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description =\
'''Copy Avastar support Information into the Paste buffer.
   Usage:
   
   1.) Click button: Support info is now in paste buffer
   2.) Go to where you want to paste the info
   4.) Press CTRL-V 
   5.) The information is pasted as Textblock
'''

    def draw(self, context):
        layout = self.layout
        col=layout.column(align=True)
        col.label(text="The data is now in")
        col.label(text="your Paste Buffer.")
        col.label(text="Please open the Application")
        col.label(text="and then Paste the Data.") 
    
    def execute(self, context):
        ob=context.object 
        if ob:
            obname = ob.name
            obmode = ob.mode
        else:
            obname='None'
            obmode=''

        last_preset = context.scene.SceneProp.panel_preset
        last_skill  = context.scene.SceneProp.skill_level

        last_preset_name = bpy.context.scene.SceneProp.bl_rna.properties['panel_preset'].enum_items[last_preset].name
        last_skill_name = bpy.context.scene.SceneProp.bl_rna.properties['skill_level'].enum_items[last_skill].name

        data = 'Avastar-%s\n' % util.get_addon_version()\
             + 'Blender-%s.%s-%s\n' % bpy.app.version\
             + 'Active : %s(%s)\n' % (obname,obmode)\
             + 'preset : %s\n' % last_preset_name\
             + 'level  : %s\n' % last_skill_name

        context.window_manager.clipboard=data
        return{'FINISHED'}


class ButtonDevkitManagerCutPreset(bpy.types.Operator):
    bl_idname = "avastar.devkit_manager_cut_preset"
    bl_label = "Copy Preset"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description =\
'''Copy the current preset into the text paste buffer
for pasting the data into a textfile'''

    def draw(self, context):
        layout = self.layout
        col=layout.column(align=True)
        col.label(text="The preset is in")
        col.label(text="your Copy Buffer.")
        col.label(text="You can paste it")
        col.label(text="into a text file")
        col.label(text="for distribution")

    def execute(self, context):
        prop = context.scene.UpdateRigProp
        text='''* Developerkit Preset

Devkit Name          = %s
Short name           = %s
Scale Factor         = %.5f

* Imported Devkit Rig:

Rig Type             = %s
Joint Type           = %s
Up Axis              = %s

* Created Avastar Rig:

Rig Type             = %s
Joint Type           = %s

* Extra options:

Use SL Head          = %s
Is Male Shape        = %s
Is Male Skeleton     = %s
Transfer Joints      = %s
Use Bind Pose        = %s
Enforce SL Bone ends = %s
Enforce SL Bone Roll = %s''' % (
        prop.devkit_brand,
        prop.devkit_snail,
        prop.devkit_scale,
        prop.srcRigType,
        prop.JointType,
        prop.up_axis,
        prop.tgtRigType,
        prop.tgtJointType,
        prop.devkit_use_sl_head,
        prop.use_male_shape,
        prop.use_male_skeleton,
        prop.transferJoints,
        prop.devkit_use_bind_pose,
        prop.sl_bone_ends,
        prop.sl_bone_rolls
        )

        context.window_manager.clipboard=text
        return{'FINISHED'}



class ButtonArmatureResetPose(bpy.types.Operator):
    bl_idname = "avastar.armature_reset_pose"
    bl_label = "Export Rest Pose"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description ='''Export Restpose '''

    action = None

    def draw(self, context):
        layout = self.layout
        col=layout.column(align=True)
        if self.action:
            col.label(text="Generated '%s'" % self.action.name)
            if self.action == context.object.animation_data.action:
                col.label(text="and set as active.")
                col.label(text="See in the Timeline")
            else:
                col.label(text="Action can now be selected")
                col.label(text="from the Dope Sheet.")
            col.separator()
            col.label(text="Next:")
            col.label(text="Please export the action")
            col.label(text="by using the .anim exporter")
            col.separator()
            col.label(text="Hint: The action has only")
            col.label(text="one keyframe and only")
            col.label(text="Animation bones (green) and")
            col.label(text="Volume bones(Orange) are keyed")
        else:
            col.label(text="No action was generated")
            col.label(text="This is unexpected!")
            col.label(text="Please report this")
    
    def execute(self, context):

        ob = context.object
        arm = util.get_armature(ob)
        if not arm:
            self.report({'WARNING'}, "No armature to generate Rest Pose from")
            return {'CANCELLED'}

        subset = arm.AnimProp.used_restpose_bones
    
        self.action, msg = create_armature_reset_action(context, subset)
        if not self.action:
            self.report({'WARNING'},msg)
            return {'CANCELLED'}
        return {'FINISHED'}

def set_action(arm, action):
    if not action:
        return None

    if not arm.animation_data:
        arm.animation_data_create()
    oaction = arm.animation_data.action 
    arm.animation_data.action = action
    return oaction

def create_armature_reset_action(context, subset):

    def get_action(arm):
        if not (arm and arm.animation_data):
            return None
        return arm.animation_data.action
    
    def cleanup(action):
        for fcurve in action.fcurves:
            action.fcurves.remove(fcurve)

    def add_parent_hierarchy(deform_bones):
        resultlist=deform_bones.copy()
        for b in deform_bones:
            while b.parent:
                b = b.parent
                if b in resultlist:
                    break
                if b.use_deform:
                    resultlist.append(b)
        return resultlist        

    def remap_deform_to_anim(dbones, deform_bones):
        anim_bones=[]
        for anim_bone in deform_bones:
            bone = None
            name = anim_bone.name
            if name.startswith('m'):
                bone = dbones.get(name[1:])
            mapped_bone = bone if bone else anim_bone

            anim_bones.append(mapped_bone)

        return list(set(anim_bones))

    ob = context.object
    arm = util.get_armature(ob)
    dbones = arm.data.bones

    if subset == 'ANIMATED':
        animated_meshes = util.get_animated_meshes(context, arm, with_avastar=True, only_selected=False)
        weight_maps = util.get_weight_group_names(animated_meshes)
        deform_bones = [b for b in dbones if b.use_deform and b.name in weight_maps]
        deform_bones = add_parent_hierarchy(deform_bones)
    elif subset == 'VISIBLE':
        deform_bones = [b for b in dbones if util.bone_is_visible(arm, b)]
        deform_bones = add_parent_hierarchy(deform_bones)
    else:
        deform_bones = [b for b in dbones if b.use_deform]

    animated_bones = remap_deform_to_anim(dbones, deform_bones)
    if (len(animated_bones) == 0):
        msg = "No bones selected. Pose not created"
        log.warning(msg)
        return None, msg
    else:
        log.warning("Remapped %d deform bones to %d anim bones" % (len(deform_bones), len(animated_bones)) )

    oposition = arm.data.pose_position
    olayers = list(arm.data.layers)
    for l in range(len(arm.data.layers)):
        arm.data.layers[l]=True

        
    for b in dbones:
        b.hide = not b in animated_bones
        b.select = b in animated_bones

    oaction = get_action(arm)
    posename = "%s-restpose" % arm.name
    log.warning("Generate %d channels in action %s" % (len(animated_bones), posename ))
    action = bpy.data.actions.get(posename)
    if action:
        cleanup(action)
    else:
        action = bpy.data.actions.new(posename)

    set_action(arm, action)

    bpy.context.object.data.pose_position = 'REST'
    bpy.ops.anim.keyframe_insert_menu(type='BUILTIN_KSI_LocRot')
    bpy.context.object.data.pose_position = oposition
    arm.data.layers = olayers

    for b in dbones:
        b.hide = False
        b.select = False

    set_action(arm, oaction)

    return action, None
    
class ButtonArmatureApplyAsRestpose(bpy.types.Operator):
    bl_idname = "avastar.apply_as_restpose"
    bl_label = "Apply as Restpose"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = messages.avastar_apply_as_restpose_text
    store_as_bind_pose : const.g_store_as_bind_pose
    
    def execute(self, context):
        tic = time.time()
        oactive = context.object
        arm_obj = util.get_armature(oactive)
        reset_shape_sliders = arm_obj.RigProp.reset_shape_sliders
        tic = logtime(tic, "bake: prepared to start", indent=0, mintime=0)
        shape_data = shape.asDictionary(arm_obj, full=True).copy()
        tic = logtime(tic, "bake: Shape is backed up", indent=0, mintime=0)
        tic = logtime(tic, "bake: Calling the Bake operator", indent=0, mintime=0)
        bpy.ops.avastar.armature_bake(
            reset_shape_sliders=reset_shape_sliders,
            handleBakeRestPoseSelection='ALL',
            store_as_bind_pose=self.store_as_bind_pose)
        tic = logtime(tic, "bake: Bake operator is finished", indent=0, mintime=0)

        if reset_shape_sliders:
            shape.resetToDefault(arm_obj, context)
        else:
            shape.fromDictionary(arm_obj, shape_data)
        tic = logtime(tic, "bake: Apply restpose done", indent=0, mintime=0)
        return {'FINISHED'}

class ButtonArmatureBake(bpy.types.Operator):
    bl_idname = "avastar.armature_bake"
    bl_label = "Apply as Restpose"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = messages.avastar_apply_as_restpose_text

    handleBakeRestPoseSelection : EnumProperty(
        items=(
            ('SELECTED','Selected', 'Bake selected Bones'),
            ('VISIBLE', 'Visible',  'Bake visible Bones'),
            ('ALL',     'All',      'Bake all Bones')),
        name="Scope",
        description="Which bones are affected by the Bake",
        default='VISIBLE')

    reset_shape_sliders : g_reset_shape_sliders

    apply_armature_on_snap_rig : BoolProperty(
        default     = True,
        name        = "Snap Mesh",
        description = \
'''Apply the current Pose to all bound meshes before snapping the rig to pose

The snap Rig to Pose operator modifies the Restpose of the Armature.
When this flag is enabled, the bound objects will be frozen and reparented to the new restpose

Note: When this option is enabled, the operator deletes all Shape keys on the bound objects!
Handle with Care!'''
    )

    adjust_stretch_to  : BoolProperty(
        name="Adjust IK Line Bones",
        description="Adjust IK Line Bones to the Pole Target and the coresponding Bones",
        default=True
    )

    adjust_pole_angles : BoolProperty(
        name="Adjust IK Pole Angles",
        description="Recalculate IK Pole Angle for minimal distortion",
        default=True
    )

    PV = {'USE_MODIFIER':None, 'TRUE':True, 'FALSE':False}
    preserve_volume : EnumProperty(
    items=(
        ('USE_MODIFIER', 'As is', 'Keep preserve volume as defined in the Armature modifier(s) of the selected meshes'),
        ('TRUE',         'Yes',   'Enable  Preserve Volume for all selected Meshes'),
        ('FALSE',        'No',    'Disable Preserve Volume for all selected Meshes')),
    name="Preserve Volume",
    description="Preserve the Mesh Volume while Baking meshes",
    default='USE_MODIFIER'
    )

    store_as_bind_pose : const.g_store_as_bind_pose

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        box = layout.box()
        box.label(text="Pose Bake Options:", icon=ICON_BONE_DATA)
        col = box.column()

        col.prop(self,'apply_armature_on_snap_rig')
        col.prop(self,'preserve_volume')
        col.prop(self,'handleBakeRestPoseSelection')
        col = box.column()        
        col.prop(self,"adjust_stretch_to")
        col.prop(self,"adjust_pole_angles")

    def execute(self, context):

        def apply_pose_as_restpose(arm_obj):
            eye_target_states = util.disable_eye_targets(arm_obj)
            bpy.ops.pose.armature_apply()
            util.enable_eye_targets(arm_obj, eye_target_states)

        def get_boneset(arm_obj):
            dbones = active.data.bones
            selection = []
            if self.handleBakeRestPoseSelection=="ALL":
                selection = Skeleton.bones_in_hierarchical_order(arm_obj, order='BOTTOMUP')
            else:

                for name in Skeleton.bones_in_hierarchical_order(arm_obj, order='BOTTOMUP'):
                    bone = dbones[name]
                    if not bone.hide and len([id for id,layer in enumerate(bone.layers) if bone.layers[id] and arm_obj.data.layers[id]]):
                        selection.append(name)

                if self.handleBakeRestPoseSelection=="SELECTED":
                    selection = [name for name in selection if dbones[name].select]

            return selection

        def prepare_bound_meshes(context, arm_obj):
            if self.apply_armature_on_snap_rig:
                frozen, unselectable, invisible = apply_armature_to_bound_meshes(context, arm_obj)
            else:
                frozen, unselectable, invisible = []
            return frozen, unselectable, invisible

        def apply_armature_to_bound_meshes(context, arm_obj):
            log.warning("| Apply Armature to Bound objects.")
            unselectable = util.remember_unselectable_objects(context)
            only_visible = arm_obj.ObjectProp.apply_only_to_visible
            with_avastar = arm_obj.ObjectProp.apply_to_avastar_meshes
            invisible = util.remember_invisible_objects(context)
            selection = util.get_animated_meshes(
                context,
                arm_obj,
                with_avastar=with_avastar,
                only_selected=False,
                only_visible=only_visible
                )

            for ob in context.scene.objects:
                util.object_select_set(ob, ob in selection)
            log.warning("|  Freezing %d Meshes" % (len(selection)) )
            preserve_volume = self.PV[self.preserve_volume]
            frozen = freezeSelectedMeshes(context, 
                             self, 
                             apply_pose=True, 
                             remove_weights=False, 
                             join_parts=False, 
                             appearance_enabled=False, 
                             handle_source='DELETE', 
                             preserve_volume=preserve_volume)

            return frozen, unselectable, invisible

        def finalize_bound_meshes(context, arm_obj, selected_object_names, unselectable, invisible):

            if self.apply_armature_on_snap_rig:

                util.ensure_mode_is('OBJECT')
                util.object_select_set(arm_obj, True)
                bpy.ops.avastar.parent_armature(
                    bindSourceSelection = 'NONE',
                    clearTargetWeights = False,
                    toTPose =  False)


                util.restore_object_select_states(context, selected_object_names)
                util.restore_unselectable_objects(context, unselectable)
                util.restore_invisible_objects(context, invisible)

        def prepare_workbench(context, arm_obj):
            omode  = util.ensure_mode_is('OBJECT')
            selected_object_names = util.get_selected_object_names(context)

            shape.ensure_drivers_initialized(arm_obj)
            util.set_active_object(context, arm_obj)

            log.warning("| Backup current Shape to Scene")
            shape.copy_to_scene(context.scene, arm_obj)

            use_male_shape = arm_obj.ShapeDrivers.male_80
            return selected_object_names, use_male_shape, omode

        def adjust_auto_ik_rig(arm_obj):
            util.ensure_mode_is('OBJECT')
            pbones = arm_obj.pose.bones
            boneset = get_boneset(arm_obj)

            if self.adjust_stretch_to:

                util.ensure_mode_is('EDIT')
                linebones = rig.get_line_bone_names(pbones, boneset)
                rig.fix_stretch_to(arm_obj, linebones)

            if self.adjust_pole_angles:

                polebones = rig.get_pole_bone_names(pbones, boneset)
                rig.fix_pole_angles(arm_obj, polebones)

            util.ensure_mode_is('POSE') # toggle mode to see changes

        def adjust_toe_hover(arm_obj):
            util.ensure_mode_is('OBJECT')
            Skeleton.get_toe_hover_z(arm_obj, reset=True)


        tic = time.time()
        ousermode = util.set_operate_in_user_mode(False)
        oactive = context.object
        active = util.get_armature(oactive)
        if not active:
            msg = "[%s] has no armature to bake to(Cancel)." % (context.object.name)
            self.report({'ERROR'},(msg))
            return {'CANCEL'}

        use_bind_pose = self.store_as_bind_pose #active.RigProp.rig_use_bind_pose
        selected_object_names, use_male_shape, omode = prepare_workbench(context, active)
        tic = logtime(tic, "bake: Workbench prepared", indent=4, mintime=0)

        need_rebase = False





        util.ensure_mode_is('POSE')


        posed_bones = rig.get_posed_bones(active)
        rig.set_rotation_limit(posed_bones, False)

        frozen, unselectable, invisible = prepare_bound_meshes(context, active)

        tic = logtime(tic, "bake: Bound Meshes are frozen", indent=4, mintime=0)



        if use_male_shape:
            log.warning("| Temporary reset the gender to female")
            propgroups.gender_update(active, False)

        apply_pose_as_restpose(active)
        tic = logtime(tic, "bake: pose is applied as restpose", indent=4, mintime=0)

        adjust_toe_hover(active)
        adjust_auto_ik_rig(active)

        util.update_view_layer(context)
        bind.ArmatureJointPosStore.exec_imp(
                context,
                delete_only=False,
                with_ik_bones=active.RigProp.generate_joint_ik,
                with_joint_tails=active.RigProp.generate_joint_tails,
                only_meta=False,
                vanilla_rig=False,
                snap_control_to_rig=False,
                store_as_bind_pose=use_bind_pose
        )
        util.update_view_layer(context)
        bpy.ops.avastar.armature_jointpos_store(store_as_bind_pose=use_bind_pose)
        tic = logtime(tic, "bake: Joints are stored", indent=4, mintime=0)

        if use_male_shape:
            propgroups.gender_update(active, True)
        shape.paste_from_scene(context.scene, active)

        oselector = util.set_disable_update_slider_selector(True)
        for ob in frozen:
            ob.ObjectProp.slider_selector='SL'
            util.fix_modifier_order(context, ob)
        util.set_disable_update_slider_selector(oselector)
        active.ObjectProp.slider_selector='SL'
        tic = logtime(tic, "bake: Frozen mesh modifiers are reordered", indent=4, mintime=0)

        finalize_bound_meshes(context, active, selected_object_names, unselectable, invisible)
        tic = logtime(tic, "bake: Frozen meshes are rebound", indent=4, mintime=0)


        util.set_active_object(context, oactive)
        util.ensure_mode_is(omode)
        util.set_operate_in_user_mode(ousermode)

        if need_rebase:
            shape.resetToRestpose(active, context)

        tic = logtime(tic, "bake: done", indent=4, mintime=0)
        return{'FINISHED'}

def set_spine_controlls(armobj, val):
    old = armobj.get('spine_unfold', val)
    if val == 'upper' and old in ['lower', 'all']:
        val = 'all'
    if val == 'lower' and old in ['upper', 'all']:
        val = 'all'
    armobj['spine_unfold'] = val


class ArmatureSpineUnfoldUpper(bpy.types.Operator):
    bl_idname = "avastar.armature_spine_unfold_upper"
    bl_label = "Unfold Upper"
    bl_description = "Unfold the upper Spine Bones into a linear sequence of bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj    = context.object
            arm    = util.get_armature(obj)
            set_spine_controlls(arm, 'upper')
            active = obj

            util.set_active_object(context, arm)
            omode = util.ensure_mode_is('EDIT')

            rig.armatureSpineUnfoldUpper(arm)

            util.ensure_mode_is(omode)
            util.set_active_object(context, active)
        except:
            print("Could not linearise Avatar spine")
            raise
        return{'FINISHED'}

class ArmatureSpineDisplayUpper(bpy.types.Operator):
    bl_idname = "avastar.armature_spine_display_upper"
    bl_label = "Display Upper"
    bl_description = "Display the upper Spine Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        arm    = util.get_armature(obj)
        rig.armatureSpineHideUpper(arm, False)
        return{'FINISHED'}

class ArmatureSpineDisplayLower(bpy.types.Operator):
    bl_idname = "avastar.armature_spine_display_lower"
    bl_label = "Display Lower"
    bl_description = "Display the lower Spine Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        arm    = util.get_armature(obj)
        rig.armatureSpineHideLower(arm, False)
        return{'FINISHED'}



class ArmatureSpineUnfoldLower(bpy.types.Operator):
    bl_idname = "avastar.armature_spine_unfold_lower"
    bl_label = "Unfold Lower"
    bl_description = "Unfold the lower Spine Bones into a linear sequence of bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj    = context.object
            arm    = util.get_armature(obj)
            set_spine_controlls(arm, 'lower')
            active = obj

            util.set_active_object(context, arm)
            omode  = util.ensure_mode_is('EDIT')

            rig.armatureSpineUnfoldLower(arm)

            util.ensure_mode_is(omode)
            util.set_active_object(context, active)
        except:
            print("Could not linearise Avatar spine")
            raise
        return{'FINISHED'}

class ArmatureSpineUnfold(bpy.types.Operator):
    bl_idname = "avastar.armature_spine_unfold"
    bl_label = "Unfold"
    bl_description = "Unfold all Spine Bones into a linear sequence of bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj    = context.object
            arm    = util.get_armature(obj)
            set_spine_controlls(arm, 'all')
            active = obj

            util.set_active_object(context, arm)
            omode  = util.ensure_mode_is('EDIT')

            rig.armatureSpineFold(arm)
            rig.armatureSpineUnfoldLower(arm)
            rig.armatureSpineUnfoldUpper(arm)

            util.ensure_mode_is(omode)
            util.set_active_object(context, active)
        except:
            print("Could not linearise Avatar spine")
            raise
        return{'FINISHED'}
        

class ArmatureSpinefold(bpy.types.Operator):
    bl_idname = "avastar.armature_spine_fold"
    bl_label = "Fold"
    bl_description = "Fold the Spine Bones into their default position\nThis is compatible to the SL legacy Skeleton"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj    = context.object
            arm    = util.get_armature(obj)
            set_spine_controlls(arm, 'none')
            active = obj

            util.set_active_object(context, arm)
            omode  = util.ensure_mode_is('EDIT')

            rig.armatureSpineFold(arm)

            util.ensure_mode_is(omode)
            util.set_active_object(context, active)
        except:
            print("Could not linearise Avatar spine")
            raise
        return{'FINISHED'}
        

class ButtonArmatureBoneSnapper(bpy.types.Operator):
    bl_idname = "avastar.armature_adjust_base2rig"
    bl_label = "Snap Base to Rig"
    bl_description =\
'''Propagate Control Bone edits to corresponding SL-Base-bones.

You use this function after you have edited the Control rig.
Then this function synchronizes your deform bones (SL Base Bones)
to the edited Control Rig'''

    bl_options = {'REGISTER', 'UNDO'}
    
    fix_base_bones       : BoolProperty(name="Snap SL Base",           description="Propagate changes to the SL Base Bones",      default=True)
    fix_ik_bones         : BoolProperty(name="Snap IK Bones",          description="Propagate changes to the IK Bones",           default=True)
    fix_volume_bones     : BoolProperty(name="Snap Volume Bones",      description="Propagate changes to the Volume Bones",       default=False)
    fix_attachment_bones : BoolProperty(name="Snap Attachment Points", description="Propagate changes to the Attachment Points",  default=False)
    base_to_rig          : BoolProperty(name="Reverse Snap",           description="Reverse the snapping direction: Adjust the Rig bones to the Base bones. ",  default=False)
    adjust_pelvis        : BoolProperty(name="Adjust Pelvis",             description = UpdateRigProp_adjust_pelvis_description,        default = False)
    sync                 : BoolProperty(name="Sync",                      description = "Synchronized joint store (debug)", default     = False)    

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        box = layout.box()
        box.label(text="Snap Options", icon=ICON_BONE_DATA)
        col = box.column(align=True)    
        col.prop(self,"adjust_pelvis")
        col.prop(self,"sync")
        col.prop(self,"fix_base_bones")
        col.prop(self,"fix_ik_bones")
        col.prop(self,"fix_volume_bones")
        col.prop(self,"fix_attachment_bones")
        col.prop(self,"base_to_rig")

    def execute(self, context):
        oumode = util.set_operate_in_user_mode(False)
        try:    
            active = context.active_object 
            rig.reset_cache(active, full=True)
            if "avastar" in active and self.adjust_pelvis and rig.needTinkerFix(active):
                rig.matchTinkerToPelvis(context, active, alignToDeform=False)
            
            if self.fix_base_bones:
                rig.adjustRigToSL(active) if self.base_to_rig else rig.adjustSLToRig(active)
            if self.fix_ik_bones:
                rig.adjustIKToRig(active)
            if self.fix_volume_bones:
                log.info("fix_volume_bones ...")
                rig.adjustVolumeBonesToRig(active)
            if self.fix_attachment_bones:
                log.info("adjustAttachmentBonesToRig ...")
                rig.adjustAttachmentBonesToRig(active)
                
            log.warning("Snap Base to Rig: Calculate joint offsets...")
            bpy.ops.avastar.armature_jointpos_store()
        except Exception as e:
            util.ErrorDialog.exception(e)
        finally:
            util.set_operate_in_user_mode(oumode)
        return{'FINISHED'}    






#

#


#






#




#

#


#






#





#

#


#






#

class ButtonAlphaMaskBake(bpy.types.Operator):
    bl_idname = "avastar.alphamask_bake"
    bl_label = "Bake Mask"
    bl_description = "Create an Alpha_Mask from the given weight group"

    def execute(self, context):

        try:
            active = context.active_object 
            create_bw_mask(active, active.avastarAlphaMask, "avastar_alpha_mask")
        except Exception as e:
            util.ErrorDialog.exception(e)
        return {'FINISHED'}    

def get_deform_subset(armobj, subtype, only_deforming=None):
    if subtype == 'BASIC':
        bones = data.get_base_bones(armobj, only_deforming=only_deforming)
    elif subtype == 'VOL':
        bones = data.get_volume_bones(armobj, only_deforming=only_deforming)
    elif subtype in ['EXTENDED', 'REFERENCE']:
        bones = data.get_extended_bones(armobj, only_deforming=only_deforming)
    else:
        bones = util.getVisibleSelectedBoneNames(armobj)
    return bones


class ButtonDeformUpdate(bpy.types.Operator):
    bl_idname = "avastar.armature_deform_update"
    bl_label = "Update deform"
    bl_description = "Update Deform layer for display purposes"

    @classmethod
    def poll(self, context):
        arm = util.get_armature(context.object)
        return arm is not None

    def execute(self, context):
        armobj = util.get_armature(context.object)
        bones = util.get_modify_bones(armobj)
        dbones = [b for b in bones if b.use_deform]
        log.warning("Found %d deform bones" % (len(dbones)) )
        bind.fix_bone_layers(context, context.scene, lazy=False, force=True)
        return {'FINISHED'}    

class ButtonDeformEnable(bpy.types.Operator):
    bl_idname = "avastar.armature_deform_enable"
    bl_label = "Enable deform"
    bl_description = "Enable Deform option for bones (Either Selected bones, SL Base Bones, Volume Bones, or Extended Bones)"

    set : StringProperty()
    
    def execute(self, context):

        try:
            armobj = util.get_armature(context.object)
            bones = get_deform_subset(armobj, self.set, only_deforming=False)
            weights.setDeformingBones(armobj, bones, replace=False)
            bind.fix_bone_layers(context, context.scene, lazy=False, force=True)
            log.warning("Enabled %d %s Deform Bones" % (len(bones), self.set) )

        except:
            self.report({'WARNING'},"Could not enable deform for bones in %s"%context.object.name)
            raise
        return {'FINISHED'}    

class ButtonDeformDisable(bpy.types.Operator):
    bl_idname = "avastar.armature_deform_disable"
    bl_label = "Disable deform"
    bl_description = "Disable Deform option for bones (Either Selected bones, SL Base Bones, Volume Bones, or Extended Bones)"
    bl_options = {'REGISTER', 'UNDO'}
    set : StringProperty()
    
    def execute(self, context):

        try:
            armobj = util.get_armature(context.object)
            bones = get_deform_subset(armobj, self.set, only_deforming=False)
            weights.disableDeformingBones(armobj, bones , replace=False)
            bind.fix_bone_layers(context, context.scene, lazy=False, force=True)
            log.warning("Disabled %d %s Deform Bones" % (len(bones), self.set))
            
        except:
            self.report({'WARNING'},"Could not disable deform for bones in %s"%context.object.name)
            raise
        return {'FINISHED'}    


class ButtonImportAvastarShape(bpy.types.Operator):
    bl_idname = "avastar.import_shape"  
    bl_label =  "Shape as Avastar(.xml)"
    bl_description = 'Create anAvastar character and apply the imported inworld Shape (.xml)'
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".xml"
    filepath : StringProperty(name='Shape filepath',
        subtype='FILE_PATH')

    filter_glob : StringProperty(
        default="*.xml",
        options={'HIDDEN'},
    )

    with_quads : BoolProperty(name='Use Quads',
        default = False,
        description = "If enabled: Create an Avastar with Quads, If disabled:Create a triangulated Avastar" )

    def draw(self, context):
        layout = self.layout
        obj = context.object
        if obj and util.object_select_get(obj) and obj.type == 'ARMATURE' and 'avastar' in obj:
            box = layout.box()
            col=box.column(align=True)
            col.label(text="Apply Shape to")
            col.label(text="Armature: [%s]" % obj.name)
        else:
            col = layout.column()
            col.prop(context.scene.UpdateRigProp,'tgtRigType', text="Rig Type")
            col.prop(self,'with_quads')

    def execute(self, context):
        obj = context.object

        if obj and util.object_select_get(obj) and obj.type == 'ARMATURE' and 'avastar' in obj:
            armobj = obj
        else:
            armobj = create.createAvatar(context, quads = self.with_quads, rigType=context.scene.UpdateRigProp.tgtRigType)
            util.ensure_mode_is("OBJECT")
            util.set_active_object(context, armobj)

        print("import from [%s]"%(self.filepath))
        shape.loadProps(context, armobj, self.filepath)
        return{'FINISHED'}    
    
    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}

class ButtonExportDevkitConfiguration(bpy.types.Operator):
    bl_idname = "avastar.export_devkit_configuration"  
    bl_label =  "Export to File"
    bl_description = 'Export the developerkit configuration to file'

    filename_ext = ".txt"
    filter_glob : StringProperty(
        default="*.txt",
        options={'HIDDEN'},
    )

    check_existing : BoolProperty(
                name="Check Existing",
                description="Check and warn on overwriting existing files",
                default=True,
                options={'HIDDEN'},
                )
    
    filepath : StringProperty(



                default="//",
                subtype='FILE_PATH',
                )

    def draw(self, context):
        layout = self.layout  
        create_devkit_layout(context, layout)
 

    def invoke(self, context, event):
        props = context.scene.UpdateRigProp
        self.filepath = '%s-%s%s' % (props.devkit_brand, props.devkit_snail, self.filename_ext)
        self.check_existing = not props.devkit_replace_export
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


    def execute(self, context):
        preferences = util.getAddonPreferences()
        props = context.scene.UpdateRigProp
        self.filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)

        if self.check_existing and os.path.exists(self.filepath):
            msg =  'Export file already exists and overwrite not allowed for %s' % self.filepath
            self.report({'WARNING'},msg)
            return {'CANCELLED'}

        pathbase, ext = os.path.splitext(props.devkit_filepath)
        base,filename = os.path.split(pathbase)

        brand = props.devkit_brand
        name  = props.devkit_snail

        import configparser
        config = configparser.ConfigParser()
        config['%s - %s'%(brand,name)] = {
            'filename': '%s%s' %(filename, ext),
            'brand'   : brand,
            'name'    : name,
            'scale'   : props.devkit_scale,
            'up_axis' : props.up_axis,
            'source.rigtype'   : props.srcRigType,
            'source.jointtype' : props.JointType,
            'target.rigtype'   : props.tgtRigType,
            'target.jointtype' : props.tgtJointType,
            'use_sl_head'      : props.devkit_use_sl_head,
            'use_male_shape'    : props.use_male_shape,
            'use_male_skeleton' : props.use_male_skeleton,
            'transfer_joints'  : props.transferJoints,
            'use_bind_pose'    : props.transferJoints,
            'use_sl_bone_ends' : props.sl_bone_ends,
            'use_sl_bone_rolls': props.sl_bone_rolls
        }
        with open(self.filepath, 'w') as configfile:
            config.write(configfile)

        return {'FINISHED'}


class ButtonImportDevkitConfiguration(bpy.types.Operator):
    bl_idname = "avastar.import_devkit_configuration"  
    bl_label =  "Import File"
    bl_description = 'Import a developerkit configuration from file'


    filename_ext = ".txt"
    filter_glob : StringProperty(
        default="*.txt",
        options={'HIDDEN'},
    )


    check_existing : BoolProperty(
                name="Check Existing",
                description="Check and warn on overwriting existing files",
                default=True,
                options={'HIDDEN'},
                )
    
    filepath : StringProperty(



                default="//",
                subtype='FILE_PATH',
                )

    def draw(self, context):
        layout = self.layout  
        create_devkit_layout(context, layout)
 

    def invoke(self, context, event):
        props = context.scene.UpdateRigProp
        self.filepath = self.filename_ext
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


    def execute(self, context):
        preferences = util.getAddonPreferences()
        props = context.scene.UpdateRigProp

        import configparser
        config = configparser.ConfigParser()
        config.read(self.filepath)

        for section in config.sections():
            devkit = config[section]
            filename = devkit.get('filename')

            props.devkit_brand      = devkit.get('brand')
            props.devkit_snail      = devkit.get('name')
            props.devkit_scale      = devkit.getfloat('scale')
            props.up_axis           = devkit.get('up_axis')
            props.srcRigType        = devkit.get('source.rigtype')
            props.JointType         = devkit.get('source.jointtype')
            props.tgtRigType        = devkit.get('target.rigtype')
            props.tgtJointType      = devkit.get('target.jointtype')
            props.devkit_use_sl_head= devkit.getboolean('use_sl_head')
            props.use_male_shape     = devkit.getboolean('use_male_shape')
            props.use_male_skeleton  = devkit.getboolean('use_male_skeleton')
            props.transferJoints    = devkit.getboolean('transfer_joints')
            props.transferJoints    = devkit.getboolean('use_bind_pose')
            props.sl_bone_ends      = devkit.getboolean('use_sl_bone_ends')
            props.sl_bone_rolls     = devkit.getboolean('use_sl_bone_rolls')

            try:
                bpy.ops.avastar.devkit_presets_update(name=section)
            except:
                allowed = "" if props.devkit_replace_import else "not "
                self.report({'WARNING'}, "Could not import existing Preset %s (overwrite is %sallowed)" % (section, allowed))

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout  
        create_devkit_layout(context, layout)
                

class ButtonExportSLCollada(bpy.types.Operator):
    bl_idname = "avastar.export_sl_collada"  
    bl_label =  "Collada (Avastar) (.dae)"
    bl_description = 'Export the selection as Collada-1.4.1 (.dae) with compatibility with SL, OpenSim and similar worlds'

    filename_ext = ".dae"
    filter_glob : StringProperty(
        default="*.dae",
        options={'HIDDEN'},
    )
    
    check_existing : BoolProperty(
                name="Check Existing",
                description="Check and warn on overwriting existing files",
                default=True,
                options={'HIDDEN'},
                )
    
    filepath : StringProperty(



                default="//",
                subtype='FILE_PATH',
                )    

    def draw(self, context):
        layout = self.layout  
        currentSelection = util.getCurrentSelection(context)
        attached         = currentSelection['attached']
        targets          = currentSelection['targets']
        create_collada_layout(context, layout, attached, targets)

    @classmethod
    def poll(cls, context):
        if not context:
            return False
        if context.mode != 'OBJECT':
            return False

        ob = context.object
        if not ob:
            return False

        armobj = util.get_armature(ob)
        if armobj:
            visible = util.object_visible_get(armobj, context=context)
            log.debug("Armature %s is visible? %s" % (armobj.name, visible))

            return visible# and is_safe_to_export

        return True

    def invoke(self, context, event):
        export_errors = []
        selected_objects = util.get_selected_objects(context, types=['MESH'])
        if selected_objects:
            matcount, extensions, total_unassigned_polys, total_unassigned_slots, total_unassigned_mats = util.get_highest_materialcount(selected_objects)
        else:
            msg = M014_msg_empty_selection % ['MESH']
            help_page = get_help_page("REBIND_ARMATURE")
            export_errors.append([msg, help_page])

        try:
            arms = []
            for obj in selected_objects:
                arm = util.getArmature(obj)
                if arm is not None:

                    if not 'avastar' in arm:
                        continue

                    if util.use_sliders(context) and rig.need_rebinding(arm, [obj]):
                        msg = M009_outdated_reference % obj.name
                        help_page = get_help_page("REBIND_ARMATURE")
                        export_errors.append([msg, help_page])

                    report = findWeightProblemVertices(context, obj, use_sl_list=False, find_selected_armature=True)
                    if 'undeformable' in report['status']:
                        undeformable = report['undeformable']
                        msg = M011_msg_undeform_bones % (len(undeformable), obj.name)
                        help_page = get_help_page("FIND_UNDEFORMABLE")
                        export_errors.append([msg, help_page])
                        export_errors.append(["             %s " % ([k for k in undeformable.keys()]), ""])

                    if 'unweighted' in report['status']:
                        unweighted = report['unweighted']
                        msg = M012_msg_unweighted_verts % (len(unweighted), obj.name)
                        help_page = get_help_page("FIND_UNWEIGHTED")
                        export_errors.append([msg, help_page])

                    if 'zero_weights' in report['status']:
                        zero_weights = report['zero_weights']
                        msg = M013_msg_zero_verts % (len(zero_weights), obj.name)
                        help_page = get_help_page("FIND_ZEROWEIGHTS")
                        export_errors.append([msg, help_page])

                    report, error_count, info_count = rig.check_bone_hierarchy(arm)
                    if error_count > 0:
                        msg = "Unsupported Bone Hierarchy detected:\n\n"
                        self.report({'WARNING'},msg)
                        for icon, message in report:
                            self.report({'WARNING'},message)
                            msg += "    " + message + " " + icon + "\n"
                        msg += "\nAction: Ensure your Skeleton matches to the SL Hierarchy"
                        help_page = get_help_page("CHECK_HIERARCHY")
                        export_errors.append([msg, help_page])

            if export_errors:
                e = util.ColladaExportError(msg_export_error_note, export_errors, "Fixes on model needed,  read below")
                self.report({'WARNING'}, "%d issues in export selection" % (len(export_errors)))
                util.ErrorDialog.exception(e)
                return {'CANCELLED'}
            
            meshProps = context.scene.MeshProp

            self.filepath = bpy.path.ensure_ext(bpy.data.filepath, self.filename_ext)
            self.filepath = self.filepath.replace(".blend","")

            currentSelection = util.getCurrentSelection(context)
            attached         = currentSelection['attached']
            targets          = currentSelection['targets']

            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'RUNNING_MODAL'}

    def execute(self, context):
        preferences = util.getAddonPreferences()
        sceneProps = context.scene.SceneProp
        meshProps = context.scene.MeshProp
        active = util.get_active_object(context)
        omode = active.mode
        good = False

        self.filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)
        try:
            print("+===================================================")
            print("| Avastar: Collada export to file [",self.filepath,"]")
            use_bind_pose = False
            export_restpose = False
            export_lsl = False
            armobjs = util.get_armatures(context.selected_objects)
            if len(armobjs) > 0:
                print("| Avastar: Found %d armatures" % len(armobjs))
                armobj=list(armobjs)[0]
            else:
                print("| Avastar: No armatures in Export")
                armobj = None

            if armobj:
                target_system = armobj.RigProp.RigType
                if util.use_sliders(context):
                    ui_level = util.get_ui_level()
                    use_bind_pose = armobj.RigProp.rig_use_bind_pose
                    export_restpose = ui_level > UI_STANDARD and armobj.RigProp.export_pose_reset_anim
                    export_lsl = ui_level > UI_STANDARD and armobj.RigProp.export_pose_reset_script
            else:
                target_system = sceneProps.target_system




            if util.get_ui_level() > UI_ADVANCED:
                apply_modifier_stack = meshProps.apply_modifier_stack
            else:
                apply_modifier_stack = 'PREVIEW'

            print("| Avastar: Enter main export loop")

            good, mesh_count, export_warnings = exportCollada(context, 
                self.filepath,
                apply_modifier_stack,
                target_system,
                use_bind_pose,
                sceneProps.panel_appearance_enabled and sceneProps.collada_export_with_joints
                )

            util.update_view_layer(context)


            if good:
                if len(export_warnings) > 0:
                    e = util.ColladaExportWarning(msg_export_warning_note, export_warnings, "Your Export is OK, but it can be improved")
                    self.report({'WARNING'}, "%d Errors in export selection" % (len(export_warnings)))
                    util.ErrorDialog.exception(e)
                self.report({'INFO'},"Exported %d %s"% (mesh_count, util.pluralize("Mesh", 1)))
                status = {'FINISHED'}
            else:
                print("| Avastar: Export returned with errors(See log)")
                status = {'CANCELLED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            status = {'CANCELLED'}

        if good:
            if export_restpose:
                reset_anim = get_script_name(self.filepath, self.filename_ext, "reset", "anim")
                log.warning("| Create reset anim %s" % reset_anim)
                generate_anim(context, reset_anim)

            if export_lsl:
                lsl_script = get_script_name(self.filepath, self.filename_ext, "reset", "lsl")
                log.warning("| Create LSL script %s" % lsl_script)
                generate_script(lsl_script)

        util.set_active_object(context, active)
        util.ensure_mode_is(omode)
        print("+===================================================")
        return status

def generate_script(filepath):
    with open(filepath, "w") as script:
        script.write(messages.pose_reset_script_lsl)

def generate_anim(context, filepath):
    scn = context.scene
    ob = context.object
    arm=util.get_armature(ob)
    if not arm:
        return

    util.set_active_object(context, arm)
    omode = util.ensure_mode_is('POSE')
    action, msg = create_armature_reset_action(context, 'ANIMATED')
    util.ensure_mode_is(omode)

    props = action.AnimProp
    props.Mode='anim'
    props.Ease_In  = 0
    props.Ease_Out = 0
    props.Priority = 0
    props.Loop = True
    props.Loop_In = props.frame_start
    props.Loop_out= props.frame_start
    props.Translations = True

    scn.MeshProp.apply_armature_scale = True
    scn.frame_start = props.frame_start
    scn.frame_end = props.frame_start

    oaction = arm.animation_data.action
    arm.animation_data.action = action
    animation.exportAnimation(context, action, filepath, 'anim')
    if oaction:
        arm.animation_data.action = oaction

def get_script_name(path, ext, type, postfix):
    path = "%s_%s.%s" % (path[:-len(ext)], type, postfix)
    return path
    

class DummyOp(bpy.types.Operator):
    bl_idname = "avastar.dop"
    bl_label = "-"
    bl_description = "Please Update this Armature before usage.\nSee N-Panel > Avastar > Rig Inspector > Rig Update Tool"

    def execute(self, context):
        return{'FINISHED'}

class UpdateAvastarPopup(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "avastar.update_avastar"
    bl_label = "Avastar Rig Version Mismatch"
    bl_options = {'REGISTER', 'UNDO'}

    armature_name : StringProperty()
    executing = False

    def check(self, context):
        return not self.executing
    
    def invoke(self, context, event):
        self.executing = True
        preferences = util.getPreferences()
        width = 400

        status = context.window_manager.invoke_props_dialog(self, width=width)


        return status

    def draw(self, context):
        obj     = context.object
        if not obj:
            print("UpdateAvastarPopup: No Context Object set (aborting)")
            return

        layout = self.layout
        armatures = util.getAvastarArmaturesInScene(context=context)

        if len(armatures) == 0:
            print("Avastar popup: No Armature found for %s" % (context.object.name) )
            return

        props = util.getAddonPreferences()
        col   = layout.column(align=True)

        row=col.row(align=True)
        row.alignment='LEFT'
        col_arm  = row.column(align=True)
        col_vers = row.column(align=True)
        col_rig  = row.column(align=True)
        col_bone = row.column(align=True)
        col_stat = row.column(align=True)
        col_stat.alignment='LEFT'

        col_arm.label(text="Armature")
        col_vers.label(text="Version")
        col_rig.label(text="Rig ID")
        col_bone.label(text="Joint Edits")
        col_stat.label(text="Hint")
        
        sep = layout.separator()
        for armobj in armatures:

            avastar_version, rig_version, rig_id, rig_type = util.get_version_info(armobj)
            joints = util.get_joint_cache(armobj)
            joint_count = len(joints) if joints else "no info"
            update = rig_id != AVASTAR_RIG_ID and avastar_version != rig_version
            icon = ICON_ERROR if update else ICON_CHECKMARK
            if rig_version == None:
                rig_version = "unknown"

            col_arm.column().label(text=armobj.name)
            col_vers.column().label(text=rig_version)
            col_rig.column().label(text=str(rig_id))
            col_bone.column().label(text="%s" % joint_count)
            if update:
                col_stat.column().operator("avastar.dop", text='',icon=icon, emboss=False)
            else:
                col_stat.column().label(text='',icon=icon)

        sep = layout.separator()
        col = layout.column(align=True)
        col.label(text="Please update the reported rigs before you do any further")
        col.label(text="editing in this blend file. The Avastar Rig Update Tool is here:")
        col.label(text="")
        col.label(text="  N-Panel -> Avastar -> Rig Inspector -> Rig Update Tool")
        col.label(text="")
        col.label(text="Hint: The Update tool can only update one Rig at a time")
        col.label(text="Tip : You can update the Rigs in Object mode or in Pose mode")
        col = layout.column()
        col.operator("wm.url_open", text="How to use the tool ...", icon=ICON_URL).url=AVASTAR_RIG_CONVERTER

    def execute(self, context):
        self.executing = True

        return {'FINISHED'}











#




#





#

#











#


#



#






#










#



class BakeShapeOperator(bpy.types.Operator):
    bl_idname      = "avastar.bake_shape"
    bl_label       = "Bake Shape"
    bl_description = "Apply visual shape to active Mesh:\n\n- applies and removes all shape keys\n- conserves all mesh edits \n\nTip: You can undo with CTRL Z"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context and context.object and context.object.type=='MESH'

    def execute(self, context):
        ob = context.object
        omode=util.ensure_mode_is("OBJECT", object=ob)
        slider_type = str(ob.ObjectProp.slider_selector)

        if slider_type != 'NONE':
            meshProps = context.scene.MeshProp
            dupobj = freezeMeshObject(context, ob, apply_shape_modifiers=meshProps.apply_shrinkwrap_to_mesh)
            dupobj.ObjectProp.slider_selector = 'SL'
            util.ensure_mode_is(omode, object=dupobj)

        return{'FINISHED'}

class BakeCleanupMaterialsOperator(bpy.types.Operator):
    bl_idname      = "avastar.material_bake_cleanup"
    bl_label       = "Reset Baked Materials"
    bl_description = "Remove baked texture nodes from selected Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        materials_object_map = BakeMaterialsOperator.get_material_object_map(context)
        for material, objects in materials_object_map.items():
            if material.BakerProp.rebake:
                image_name = "%s_tex" % material.name
                node = material.node_tree.nodes.get(image_name)
                if node:
                    material.node_tree.nodes.remove(node)
                else:
                    log.warning("Texture not found: %s" % image_name)

        return {'FINISHED'}

class AVAMaterial:
    material : bpy.types.Material
    nodes : bpy.types.bpy_prop_collection

    def __init__(self, aMaterial):
        self.material = aMaterial
        self.nodes = aMaterial.node_tree.nodes if aMaterial.node_tree else None
    
    def get_nodes_by_type(self, type):
       if not self.nodes:
           return None
       return [node for node in self.nodes if node.type==type]

    def get_node_by_name(self, name):
       if not self.nodes:
           return None
       return self.nodes.find(name)

    def get_texture(self):
        texture = get_node_by_name("%s_tex" % self.material)
        if texture:
            return texture.image
        return None

    def get_alpha(self):
        vec = self.material.diffuse_color
        shaders = self.get_nodes_by_type('BSDF_PRINCIPLED')
        if shaders:
            shader = shaders[0]
            input = shader.inputs['Alpha']
            if input:
                return input.default_value
        return vec[3] if len(vec)>3 else 1.0

    def get_diffuse(self):
        vec = self.material.diffuse_color
        shaders = self.get_nodes_by_type('BSDF_PRINCIPLED')
        if shaders:
            shader = shaders[0]
            input = shader.inputs['Base Color']
            if input:
                vec = Vector(input.default_value)
        return Vector((vec[0], vec[1], vec[2]))

class BakeMaterialsOperator(bpy.types.Operator):
    bl_idname      = "avastar.material_bake"
    bl_label       = "Bake Materials"
    bl_description = "Bake Selected Material Textures\n\nThe generated textures are created as new texture nodes within the material node trees"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        materials_object_map = BakeMaterialsOperator.get_material_object_map(context)
        if materials_object_map:
            selection = []
            sceneProps = context.scene.SceneProp
            img_w = sceneProps.baked_image_width
            img_h = sceneProps.baked_image_height
            mat_images = {}

            for material, objects in materials_object_map.items():
                if material.BakerProp.rebake:
                    for o in [o for o in objects if not o in selection]:
                        selection.append(o)
                        get_material_image_assoc(context, o, mat_images, with_image_bake=True, force_rebake=True, width=img_w, height=img_h)
                        o.ObjectProp.has_baked_materials = True
                        log.warning("Adding %s to selection" % o.name)

            if selection:
                oob, omode = util.change_active_object(context, selection[0], new_mode='OBJECT')
                execute_material_bake(context, context.scene, selection)
                util.change_active_object(context, oob, new_mode=omode)

        return {'FINISHED'}

    @staticmethod
    def get_animated_objects(context):
        obj = util.get_active_object(context)
        meshes = []
        if not obj:
            return obj, meshes

        arm = util.get_armature(obj)
        if obj.type == 'MESH':
            meshes = [o for o in context.selected_objects if o.type=='MESH']
        else:
            meshes = util.get_animated_meshes(context, arm, only_visible=False)
        return arm, meshes

    @staticmethod
    def object_material_bake_image_names(context, obj):
        bake_image_names = []
        for slot_index, material_slot in enumerate(obj.material_slots):
            material = material_slot.material
            if material and material.node_tree:
                image_name, index, node = BakeMaterialsOperator.material_baked_image_name_and_index(material)
                if index == -1:
                    bake_image_names.append(image_name)
        return bake_image_names

    @staticmethod
    def material_baked_image_name_and_index(material):
        if not material.node_tree:
            return None, None, None

        nodes = material.node_tree.nodes
        image_name = '%s_tex' % material.name
        index = nodes.find(image_name)
        node = nodes[index] if index > -1 else None
        return image_name, index, node

    @staticmethod
    def insert_material_object_relation(obj, materials_object_map=None):
        if materials_object_map == None:
            materials_object_map = {}

        for slot_index, material_slot in enumerate(obj.material_slots):
            material = material_slot.material
            if not material in materials_object_map:
                materials_object_map[material]=[]
            entries = materials_object_map[material]
            entries.append(obj)
        return materials_object_map

    @staticmethod
    def get_material_object_map(context):
        materials_object_map = {}
        arm, objects = BakeMaterialsOperator.get_animated_objects(context)
        arm_is_selected = arm and util.object_select_get(arm)
        if objects:
            for obj in [o for o in objects if arm_is_selected or util.object_select_get(o)]:
                BakeMaterialsOperator.insert_material_object_relation(obj, materials_object_map=materials_object_map)
        return materials_object_map



def freezeMeshObject(context, obj, apply_shape_modifiers=False):
    final_active = context.active_object
    name         = obj.name

    dupobj = util.visualCopyMesh(context,
            obj,
            apply_pose           = False,
            remove_weights       = False,
            apply_shape_modifiers= apply_shape_modifiers,
            preserve_volume      = None)

    util.object_hide_set(dupobj, util.object_hide_get(obj))


    arm = obj.find_armature()
    if arm is not None and dupobj.parent != arm:
        dupobj.parent = arm

    util.object_select_set(dupobj, util.object_select_get(obj))
    util.object_select_set(obj, False)
    if final_active == obj:
        final_active = dupobj

    mode=util.ensure_mode_is("OBJECT", object=obj)
    obj.name = "del_"+name
    util.remove_object(context, obj)
    dupobj.name = name
    util.ensure_mode_is(mode, object=dupobj)

    if final_active is not None:
        util.set_active_object(context, final_active)

    return dupobj




def hasAvastarData(obj):
    clean_data = ['avastar-mesh', 'weight', 'ShapeDrivers', 'ObjectProp', 'RigProp', 'use_deform_preserve_volume']
    for prop in clean_data:
        if prop in obj: 
            return True
    
    props = [DIRTY_MESH, CHECKSUM, MORPH_SHAPE, NEUTRAL_SHAPE, MESH_STATS, 'original']
    for prop in props:
        if prop in obj:
            return True
    
    if REFERENCE_SHAPE in obj:
        return True

    purge_data = ['physics', 'fitting', 'FittingValues', SHAPE_BINDING, 'version']
    for prop in purge_data:
        if prop in obj:
            return True

    return False


def cleanupAvastarData(obj, purge, restore=False):
    clean_data = ['avastar-mesh', 'weight', 'ShapeDrivers', 'ObjectProp', 'RigProp', 'use_deform_preserve_volume']
    for prop in clean_data:
        if prop in obj: 
            del obj[prop]
    shape.detachShapeSlider(obj, reset=restore)
    
    if purge:
        purge_data = ['physics', 'fitting', 'FittingValues', SHAPE_BINDING, 'version']
        for prop in purge_data:
            if prop in obj:
                del obj[prop]


def freezeSelectedMeshes(context, operator=None, apply_pose=None, remove_weights=None, join_parts=None, appearance_enabled=None, handle_source=None, preserve_volume=None, purge=False, targets=None):

    def objectify_result(result):
        objs = []
        for name in result:
            obj = bpy.data.objects.get(name)
            if obj:
                objs.append(obj)
        return objs

    def set_desired_active_object(context, desired, fallback):
        active_obj = None
        if desired:
            active_obj = bpy.data.objects.get(desired)
        if not active_obj:
            active_obj = bpy.data.objects.get(fallback)
        if active_obj:
            util.set_active_object(context, active_obj)
        return active_obj

    def create_name(obj, final_name, part_number):
        if not final_name:
            return obj.name
        if part_number < 1:
            return final_name

        return "%s_part-%d" % (final_name,part_number+1)


    scn = context.scene
    if targets == None:
        currentSelection = util.getCurrentSelection(context)
        targets          = currentSelection['targets']
    if apply_pose == None:
        apply_pose = scn.MeshProp.standalonePosed
    if remove_weights == None:
        remove_weights = scn.MeshProp.removeWeights
    if join_parts == None:
        join_parts = scn.MeshProp.joinParts
    if appearance_enabled == None:
        appearance_enabled = scn.SceneProp.panel_appearance_enabled
    if handle_source == None:
        handle_source = scn.MeshProp.handleOriginalMeshSelection

    active           = context.active_object

    dupobj = None
    active_name = active.name
    active_mesh_name = active_name if active.type == 'MESH' else None
    final_name = active.ObjectProp.frozen_name

    frozen = {}
    arms = set()
    for target in reversed(targets):
        current_mesh_name = target.name

        dupname = util.visualCopyMesh(context,
                target,
                apply_pose = apply_pose,
                remove_weights = remove_weights,
                preserve_volume=preserve_volume, 
                as_name=True)
        dupobj = bpy.data.objects[dupname]

        cleanupAvastarData(dupobj, purge, restore=False)
         
        if apply_pose:

            dupobj.parent_type = 'OBJECT'

            try:
                del dupobj['avastar-mesh']
            except:
                pass
                



            dupobj.parent = None
            dupobj.matrix_world = target.matrix_world.copy()

        if handle_source == 'HIDE':
            util.object_hide_set(target, True)

        if not apply_pose:
            arm = util.get_armature(target)
            if arm:

                arm_hide = util.object_hide_get(arm)
                util.object_hide_set(arm, False)
                util.ensure_mode_is('OBJECT')
                util.parent_selection(context, arm, [dupobj], keep_transform=True)
                arms.add(arm)
                util.object_hide_set(arm, arm_hide)

        if not active_mesh_name:
            active_mesh_name = current_mesh_name


        util.object_select_set(target, False)
        util.object_select_set(dupobj, True)

        frozen[current_mesh_name]=[target,dupobj]


    result = []

    if len(frozen) > 0: 
        if len(arms) > 0:
            arm = next(iter(arms)) #to have an existing context object
            util.set_active_object(context, arm)
        omode = util.ensure_mode_is("OBJECT")

        for target,dupobj in frozen.values():
            for mod in dupobj.modifiers:
                ob = getattr(mod,"object", None)
                if ob and ob.name in frozen:
                    mod.object = frozen[ob.name][1]


        bpy.ops.object.select_all(action='DESELECT')
        result = []
        part_number = 0
        for obj,dupobj in reversed(list(frozen.values())):
            new_name = create_name(obj, final_name, part_number)
            part_number += 1

            if handle_source == 'DELETE':
                name = obj.name
                obj.name = "%s_del" % obj.name
                util.ensure_mode_is('OBJECT', object=obj)
                util.remove_object(context, obj, do_unlink=True)

            util.object_select_set(dupobj, True)
            active_mesh_name = new_name
            dupobj.name = active_mesh_name
            result.append(dupobj.name)

        del frozen
        util.ensure_mode_is(omode)

        tc = len(targets)






        if join_parts:
            active_object = bpy.data.objects.get(active_mesh_name)
            util.set_active_object(context, active_object)
            bpy.ops.object.join()

            active_object = bpy.data.objects.get(active_mesh_name)
            active_object.parent = util.get_armature(active_object)
            
            tc = 1

            if final_name:
                active_mesh_name = final_name
                active_object.name = final_name

            if scn.MeshProp.removeDoubles:
                original_mode = util.ensure_mode_is("OBJECT")
                bm=bmesh.new()
                util.select_boundary_verts(bm, context, active_object)

                bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v.select], dist=0.00001)
                bm.to_mesh(active_object.data)

                util.ensure_mode_is(original_mode)
                bm.clear()
                bm.free()
                result = [active_mesh_name]

        result = objectify_result(result)

        if appearance_enabled:
            propgroups.update_sliders(context, arms=arms, objs=result)

        set_desired_active_object(context, desired=final_name, fallback=active_name)

        if operator:
            meshes = util.pluralize("mesh", tc)
            operator.report({'INFO'},"Created %d frozen %s"%(tc, meshes))


    return result

def remove_verts_from_all_vgroups(obj, index_list):
    print("remove verts from groups", *index_list)
    util.ensure_mode_is('EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    util.ensure_mode_is('OBJECT')
    me = obj.data
    for i in index_list:
        me.vertices[i].select=True

    util.ensure_mode_is('EDIT')
    bpy.ops.object.vertex_group_remove_from(use_all_groups=True)
    bpy.ops.mesh.select_all(action='DESELECT')
        
def add_verts_to_vgroup(obj, index_list, group_name):
    print("add verts to group", group_name, ":", *index_list)
    util.ensure_mode_is('EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    util.ensure_mode_is('OBJECT')
    me = obj.data
    for i in index_list:
        me.vertices[i].select=True
    obj.vertex_groups.active_index=obj.vertex_groups[group_name].index

    util.ensure_mode_is('EDIT')
    bpy.ops.object.vertex_group_assign()
    bpy.ops.mesh.select_all(action='DESELECT')

def weld_vertex_weights(context, obj, index_list):
    print("weld seam weights:", *index_list)
    util.ensure_mode_is('EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    util.ensure_mode_is('OBJECT')
    me = obj.data
    for i in index_list:
        me.vertices[i].select=True    
    util.ensure_mode_is('EDIT')
    status = weights.ButtonWeldWeightsFromRigged.weld_weights_from_rigged(
            context,
            onlySelectedVerts=True,
            cleanVerts=True,
            submeshInterpolation=True,
            allVisibleBones=True,
            allHiddenBones=True
        )    

def generate_face_weights(context, arm, obj):
    print("Generate face weights for %s:%s" % (arm.name, obj.name) )
    dbones = arm.data.bones
    for b in dbones:
        b.select=False
 
    bones = [b for b in dbones if b.name.startswith('mFace') or b.name.startswith('mHead')]
    for b in bones:
        b.select=True
        if b.name in SL_ALL_EYE_BONES:
            b.use_deform = False

    print("Weighting %d Face bones" % (len(bones)) )
    util.set_active_object(context, obj)
    util.ensure_mode_is('WEIGHT_PAINT')
    bpy.ops.paint.weight_from_bones(type='AUTOMATIC')

    seam        = [0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 106, 107, 110, 111, 112, 114, 336, 338]
    weld_vertex_weights(context, obj, seam)

    for b in bones:
        b.select=False
        if b.name in SL_ALL_EYE_BONES:
            b.use_deform = True

    upper_teeth = [42, 45, 46, 47, 86, 87, 201, 300, 395, 413, 665, 666, 720, 748]
    lower_teeth = [37, 38, 39, 79, 81, 139, 203, 210, 298, 394, 396, 661, 662, 664]
    
    util.ensure_mode_is('OBJECT')
    remove_verts_from_all_vgroups(obj, upper_teeth+lower_teeth)
    add_verts_to_vgroup(obj, lower_teeth, 'mFaceJaw')
    add_verts_to_vgroup(obj, upper_teeth, 'mHead')
    util.ensure_mode_is('OBJECT')



def get_extended_mesh(context, part, copy=True):
    extended_name = "%s_extended" % part

    ob = bpy.data.objects.get(extended_name, None)
    if ob and copy:
        me = ob.data.copy()
        ob = ob.copy()
        ob.data = me
        util.link_object(context, ob)

    return ob

def copy_weights(armobj, src, tgt, vert_mapping):
    util.ensure_mode_is('OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    util.object_select_set(src, True)
    util.object_select_set(tgt, True)
    util.set_active_object(bpy.context, tgt)

    limit = vert_mapping != 'TOPOLOGY'

    try:
        bpy.ops.object.data_transfer(
            use_reverse_transfer=True,
            use_create=True,
            vert_mapping=vert_mapping,
            data_type='VGROUP_WEIGHTS',
            layers_select_src='NAME',
            layers_select_dst='ALL',
            mix_mode='REPLACE')
    except:
        try:
            bpy.ops.object.data_transfer(
                use_reverse_transfer=True,
                use_create=True,
                vert_mapping=vert_mapping,
                data_type='VGROUP_WEIGHTS',
                layers_select_dst='NAME',
                layers_select_src='ALL',
                mix_mode='REPLACE')
        except:

            selectedBoneNames = weights.get_bones_from_armature(armobj, True, True)
            weights.copyBoneWeightsToSelectedBones(tgt, [src], selectedBoneNames, submeshInterpolation=False, allVerts=True, clearTargetWeights=True)
            limit = True

    if limit:
        bpy.ops.object.vertex_group_limit_total(group_select_mode='BONE_SELECT')

def generate_hand_weights(context, arm, obj):

    dbones = arm.data.bones
    for b in dbones:
        b.select=False
    
    bones = [b for b in dbones if b.name.startswith('mHand') or b.name.startswith('mWrist')]
    for b in bones:
        b.select=True

    print("Create Hand Rig            : Generate Weights for %d Hand bones (automatic from Bones)" % (len(bones)) )
    util.set_active_object(context, obj)
    util.ensure_mode_is('WEIGHT_PAINT')
    bpy.ops.paint.weight_from_bones(type='AUTOMATIC')
    util.ensure_mode_is('OBJECT')

    for b in bones:
        b.select=False

def get_extended_weights(context, armobj, tgt, part, vert_mapping='TOPOLOGY'):
    extended_src = get_extended_mesh(context, part)
    if extended_src:

        copy_weights(armobj, extended_src, tgt, vert_mapping)

        try:

            bpy.ops.object.vertex_group_clean(group_select_mode='BONE_DEFORM') # to remove zero entries in weight maps
        except:

            bpy.ops.object.vertex_group_clean(group_select_mode='ALL')         # to remove zero entries in weight maps

        print("Create Rig                : Transfered %d Weight Maps from Avastar template %s" % (len(extended_src.vertex_groups), extended_src.name ))

        util.remove_object(context, extended_src)
    else:
        print("No extended Weight source defined for part [%s]" % (part) )
        if part == 'upperBodyMesh':
            generate_hand_weights(context, armobj, tgt)
            return
        elif part == 'headMesh':
            generate_face_weights(context, armobj, tgt)
            return
        print("No Weight Generator defined for part %s" % (part) )










def get_material_bake_context(scene):
    ctx = []
    ctx.append(scene.render.engine)
    ctx.append(scene.render.bake.use_pass_direct)
    ctx.append(scene.render.bake.use_pass_indirect)
    ctx.append(scene.render.bake.use_pass_color)
    ctx.append(scene.cycles.bake_type)
    return ctx

def set_material_bake_context(scene, ctx):
    scene.render.engine = ctx[0]
    scene.render.bake.use_pass_direct = ctx[1]
    scene.render.bake.use_pass_indirect = ctx[2]
    scene.render.bake.use_pass_color = ctx[3]
    scene.cycles.bake_type = ctx[4]

def prepare_material_bake(context, mat, slot_index, mat_images, force_rebake, width=256, height=256):

    def get_bake_node(mat, width, height):
        image_name = '%s_tex' % mat.name
        node_tree = mat.node_tree
        image_node = node_tree.nodes.get(image_name)
        active_node = node_tree.nodes.active

        is_new = force_rebake
        if not image_node:
            image_node = create_bake_node(mat, width, height)
            is_new = True
        if not image_node.image or force_rebake:
            assign_image_to_node(image_node, image_name, width, height)
            is_new = True

        return active_node, image_node, is_new

    def create_bake_node(mat, width, height):
        image_name = '%s_tex' % mat.name
        node_tree = mat.node_tree
        image_node = node_tree.nodes.new("ShaderNodeTexImage")
        image_node.name = image_name
        image_node.location = Vector((10,-350)) #below the shader node
        assign_image_to_node(image_node, image_name, width, height)
        return image_node

    def assign_image_to_node(image_node, image_name, width, height):
        img = bpy.data.images.get(image_name)
        if img:
            bpy.data.images.remove(img, do_unlink=True)
        img = bpy.data.images.new(image_name,width,height)
        image_node.image = img
        image_node.select = True

    use_nodes = mat.use_nodes
    mat.use_nodes = True
    active_node, image_node, is_new = get_bake_node(mat, width, height)
    if is_new:
        log.warning("Prepare automatic bake for Mat:%s to img:%s(w:%d,h:%d)" % (mat.name, image_node.image.name, width, height))
    else:
        log.warning("Reuse existing texture for Mat:%s to img:%s(w:%d,h:%d)" % (mat.name, image_node.image.name, width, height))

    mat.node_tree.nodes.active = image_node
    mat_images[image_node.image] = [mat, image_node.image, is_new, use_nodes]
    return is_new

def execute_material_bake(context, scene, selection):
    previous_selection = util.get_select_from_scene(scene)
    log.warning("Baking for objects: %s" % ([o.name for o in selection]))
    nctx = ['CYCLES', False, False, True, 'DIFFUSE']
    octx = get_material_bake_context(scene)

    util.set_select(selection, reset=True)
    set_material_bake_context(scene, nctx)
    bpy.ops.object.bake(type='DIFFUSE', use_clear=True)
    set_material_bake_context(scene, octx)
    util.set_select(previous_selection, reset=True)
    log.warning("Bake finished")
    return False

def add_images_from_material(context, material, slot_index, mat_images, with_image_bake, force_rebake, width=128, height=128):
    if with_image_bake:
        is_new = prepare_material_bake(context, material, slot_index, mat_images, force_rebake, width=width, height=height)
    else:
        is_new = False
        
    return is_new

def get_material_image_assoc(context, obj, mat_images, with_image_bake, force_rebake, width=128, height=128):
    mat_slots = obj.material_slots
    has_new_slots = False
    for slot_index, material_slot in enumerate(mat_slots):
        material = material_slot.material
        if material:
            is_new = add_images_from_material(context, material, slot_index, mat_images, with_image_bake, force_rebake, width=width, height=height)
            has_new_slots = has_new_slots or is_new
    return has_new_slots



#
def get_images_for_material(mat_images, material):
    images=[]
    for key in mat_images:
        if mat_images[key] == material:
            images.append(key)
    return images
    


def create_libimages(root, base, mat_images, exportCopy, preferred_image_format, force_image_format, useImageAlpha, warnings):

    libimages = subx(root, 'library_images')
    saved    = []

    original_color_mode = bpy.context.scene.render.image_settings.color_mode
    if useImageAlpha:
       cm = 'RGBA'
    else:
       cm = 'RGB'
    bpy.context.scene.render.image_settings.color_mode = cm
    
    for image in mat_images:
        material = mat_images[image]
        
        if image in saved: #Take care to process each image only once.
            continue
        saved.append(image)

        original_format     = image.file_format
        
        if image.source == 'GENERATED' or force_image_format:
            format = preferred_image_format
        else:
            format = original_format
            
        file_extension = format.lower()
        if file_extension == "jpeg":
            file_extension = "jpg"
        if file_extension == "targa":
            file_extension = "tga"
        file_extension = '.' + file_extension
        try:
            image.file_format = format
        except:
            msg = _("The image [%s] has an unsupported file fromat [%s].|\n\n" \
                  "YOUR ACTION:\nPlease disable export of UV tectures or switch \n"\
                  "to another file format and try again." % (image.name,format))
            logging.error(msg)
            raise util.Warning(msg)            
        collada_key = colladaKey(image.name) 
        imgx = subx(libimages, 'image', id=collada_key, name=collada_key)
        

        collada_path = bpy.path.ensure_ext(collada_key, file_extension )

        image_on_disk = True
        if image.is_dirty or image.packed_file or image.source == 'GENERATED':


            dest = os.path.join(base,collada_path)
            dest = os.path.abspath(dest)
            image.save_render(dest)
            logging.info("Generated image %s", collada_path)
        elif exportCopy:


            dest   = os.path.join(base,collada_path)
            dest   = os.path.abspath(dest)
            if image.filepath_raw is None or "":
                logging.warn("Source Image [%s] is not available on disk. (Please check!) "%(image.name))
                warnings.append(("> " + messages.M006_image_not_found + "\n")%
                    (
                        util.shorten_text(image.name),
                        util.shorten_text(material.name)
                    )
                )
                image_on_disk = False
            else:
                source = bpy.path.abspath(image.filepath_raw)
                source = os.path.abspath(source)
                
                if source == dest:
                    logging.info("Image %s Reason: Image already in place."%(collada_path))
                else:
                    try:
                        shutil.copyfile(source, dest)
                        logging.info("Copied image %s", collada_path)
                    except Exception as e:
                        print(e)
                        print("image   :",image.name)
                        print("filename: [",image.filepath_raw,"]")
                        print("source  :", source)
                        print("dest    :", dest)
                        logging.warn('Can not copy Image from [%s] to [%s]'%(source, dest))
                        warnings.append("> " + messages.M007_image_copy_failed + ":\n")
                        warnings.append("  Image: %s\n" % image.name)
                        warnings.append("  File : %s\n" % source)
                        warnings.append("  Mat  : %s\n" % material.name)
                        image_on_disk = False
                        
        else:



            if image.filepath_raw is None or "":
                logging.warn("Image %s is not available on disk. (Please check!) "%(image.name))
                warnings.append(("> " + messages.M006_image_not_found + "\n") %
                    (
                        util.shorten_text(image.name),
                        util.shorten_text(material.name)
                    )
                )
                image_on_disk = False
            else:
                source = bpy.path.abspath(image.filepath_raw)
                source = os.path.abspath(source)
                collada_path = source
                logging.info("Refer to image %s", source)
        if image_on_disk:
            subx(imgx,'init_from', text=collada_path)
        
        image.file_format = original_format
        
    bpy.context.scene.render.image_settings.color_mode = original_color_mode
    return libimages
    








def get_normal_index(n, normals, normalsd):
    def add(normal):
        nidx = len(normals)
        normals.append(normal)
        normalsd[normal]=nidx
        return nidx

    normal = Vector(n)
    normal.normalize()
    normal = Vector((round(normal.x,6), round(normal.y,6), round(normal.z,6)))
    normal = normal.freeze()
    nidx = normalsd.get(normal, -1)
    if nidx < 0:
        nidx = add(normal)
    return nidx

def create_polylists(mesh, welded_normals, progress):
    dae_precision = util.get_precision()
    current_time = time.time()
    begin_time   = current_time
    
    def get_uv(uv_data, p, vidx, precision):
        uv = uv_data[p.loop_indices[vidx]].uv
        result = [util.sanitize_f(uv[0], precision),
              util.sanitize_f(uv[1], precision)
             ]
        return result

    #

    #

    polygons = mesh.polygons
    uvexists = len(mesh.uv_layers)>0
    if uvexists:
        uv_data = mesh.uv_layers.active.data

            
    polylists= {}
    normals  = []
    normalsd = {}
    uv_array = []
    uvidx = 0
    
    last_mat_index = -1
    vcount = []
    ps     = []
    lc     = 0    
    is_triangle = True
    pcounter = 0
    
    for p in polygons:
        corner_count=len(p.vertices)
        is_triangle = is_triangle and corner_count==3
        pcounter += 1
        if pcounter % 1000 == 0:
            util.progress_update(1, absolute=False)            

        mat_index = p.material_index
        if mat_index != last_mat_index:

            if last_mat_index != -1:

                polylists[last_mat_index]=(vcount, ps, lc, is_triangle)

            last_mat_index = mat_index
            try:
                vcount = polylists[mat_index][POLYLIST_VCOUNT]
                ps     = polylists[mat_index][POLYLIST_P]
                lc     = polylists[mat_index][POLYLIST_COUNT]
                is_triangle = is_triangle or polylists[mat_index][POLYLIST_IS_TRIS]

            except:
                vcount = []
                ps     = []
                lc     = 0
                polylists[mat_index]=(vcount, ps, lc, is_triangle)



        vcount.append(str(corner_count))
        lc += corner_count
        
        if p.use_smooth:

            fixcount = 0
            for vidx,v in enumerate(p.vertices):
                x=0
                if welded_normals and v in welded_normals:
                    n = welded_normals[v]
                    fixcount +=1
                else:
                    n = mesh.loops[p.loop_indices[vidx]].normal
                
                nidx = get_normal_index(n, normals, normalsd)
                if uvexists:
                    ps.extend((str(v),str(nidx),str(uvidx)+" "))
                    


                    uv = get_uv(uv_data, p, vidx, dae_precision)
                    uv_array.extend(("%g"%uv[0], "%g  "%uv[1]))
                    uvidx +=1
                else:
                    ps.extend((str(v),str(nidx)+" "))


        else:

            n = p.normal
            nidx = get_normal_index(n, normals, normalsd)
            
            for vidx, v in enumerate(p.vertices):
                if uvexists:
                    ps.extend((str(v),str(nidx),str(uvidx)+" "))



                    uv = get_uv(uv_data, p, vidx, dae_precision)
                    uv_array.extend(("%g"%uv[0], "%g  "%uv[1]))
                    uvidx +=1
                else:
                    ps.extend((str(v),str(nidx)+" "))
                
        ps.append("  ")

    if last_mat_index != -1:
        polylists[last_mat_index]=(vcount, ps, lc, is_triangle)


    print("| UV faces  : %d" % uvidx)
    print("| Polylists : %d" % len(polylists))
    print("| Runtime   : %.0f milliseconds" % (1000*(time.time()-begin_time)))
    return polylists, normals, uv_array

def triangulate_mesh(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(me)
    bm.free()


def colladaKey(key):

    result = re.sub("[^\w-]","_",key)
    return result


def add_material_list(tech, obj, uv_count):
    materials = obj.data.materials
    mesh = obj.data
    has_uv_layout = uv_count > 0
    for material in materials:
        if material is None:

            continue
            
        collada_material = colladaKey(material.name + "-material")
        inst = subx(tech, "instance_material", symbol=collada_material, target="#"+collada_material)
        if has_uv_layout:
            uv_layer = util.get_active_uv_layer(mesh)
            semantic = uv_layer.name
            subx(inst, "bind_vertex_input", semantic=semantic, input_semantic="TEXCOORD", input_set="0")

def attachment_name(bone_name, with_structure=False):
    if with_structure:
        return bone_name.replace(" ", "_")
    else:
        return bone_name[1:].replace(" ", "_")


def exportCollada(context,
                  path,
                  apply_modifier_stack,
                  target_system,
                  use_bind_pose,
                  with_joints
                  ):

    preferences = util.getAddonPreferences()
    preferred_image_format = preferences.exportImagetypeSelection
    force_image_format = preferences.forceImageType
    useImageAlpha = preferences.useImageAlpha

    meshProps = context.scene.MeshProp
    export_armature = meshProps.exportArmature
    export_deformer_shape = meshProps.exportDeformerShape
    exportTextures = meshProps.exportTextures
    exportOnlyActiveUVLayer = meshProps.exportOnlyActiveUVLayer
    exportCopy = meshProps.exportCopy
    apply_armature_scale = meshProps.apply_armature_scale
    apply_mesh_rotscale = meshProps.apply_mesh_rotscale
    weld_normals = meshProps.weld_normals
    weld_to_all_visible = meshProps.weld_to_all_visible
    max_weight_per_vertex = meshProps.max_weight_per_vertex

    dae_precision = util.get_precision()

    def get_bind_joint_array(array, rcount):
        indent = "\n          "
        text = indent.join([" ".join(array[i:i + rcount]) for i in range(0, len(array), rcount)])
        return indent + text + indent




    def prepare_armature_for_export(armobj):
        shape.ensure_drivers_initialized(armobj)
        gender = armobj.ShapeDrivers.male_80
        propgroups.gender_update(armobj, False)

        if armobj.RigProp.rig_export_in_sl_restpose or armobj.RigProp.rig_use_bind_pose:
            shape_dict = shape.asDictionary(armobj, full=True)
            shape.resetToRestpose(armobj, context)
        else:
            shape_dict = None

        armobj['shape_info'] = {'dict':shape_dict, 'gender':gender}

    def restore_armature_after_export(armobj):
        shape_info = armobj.get('shape_info')
        if shape_info:
            shape_dict = shape_info['dict']
            gender     = shape_info['gender']
            if shape_dict:
                shape.fromDictionary(armobj, shape_dict, update=False)
            propgroups.gender_update(armobj, gender)
            del armobj['shape_info']

    def get_exported_bone_candidates(context, arm, only_deform, only_weighted, with_attachments):
        if only_deform:
            deform_bones = (b.name for b in arm.data.bones if b.use_deform)
        else:
            deform_bones = set(arm.data.bones.keys())

        if only_weighted:
            selection = util.get_animated_meshes(context, arm, only_selected=True)
            weighted_bones = set(util.get_weight_group_names(selection))
        else:
            weighted_bones = set(arm.data.bones.keys())

        common_names = weighted_bones.intersection(deform_bones)
        
        if not with_attachments:
            common_names = (n for n in common_names if n[0] != 'a')

        return list(common_names)

    def get_armature_bone_set(context, arm):
        sceneProp  = context.scene.SceneProp
        only_deform   = context.scene.SceneProp.collada_only_deform and not context.scene.SceneProp.collada_complete_rig
        only_weighted = context.scene.SceneProp.collada_only_weighted and not context.scene.SceneProp.collada_complete_rig
        with_attachments = context.scene.SceneProp.accept_attachment_weights or context.scene.SceneProp.collada_complete_rig
        dbones = get_exported_bone_candidates(context, arm, only_deform, only_weighted, with_attachments)
        print("| Only deform bones  : %s " % only_deform)
        print("| Only weighted bones: %s " % only_weighted)
        print("| Weight group size  : %d " % len(dbones))
        print("| with attachments   : %s " % with_attachments)
        print("| complete Rig       : %s " % context.scene.SceneProp.collada_complete_rig)
        with_hierarchy = sceneProp.collada_full_hierarchy
        bset = get_collada_boneset(context, arm, dbones, with_hierarchy)
        print("| Armature bone set size: %d" % len(bset))
        return bset

    def get_collada_boneset(context, arm, dbones, with_hierarchy):
        sceneProp  = context.scene.SceneProp
        only_deform = sceneProp.collada_only_deform and not sceneProp.collada_complete_rig
        export_bones = get_final_export_bone_set(arm, sceneProp, dbones, with_hierarchy, only_deform)
        return export_bones

    def get_final_export_bone_set(arm, sceneProps, dbones, with_hierarchy=True, only_deform=True):
        export_bones = []
        joints = util.get_joint_cache(arm)
        for bone_name in dbones:
            if bone_name in export_bones:


                continue


            if bone_name in arm.data.bones:
                b=arm.data.bones[bone_name]

                if only_deform and not b.use_deform:
                    log.warning("%s is Not a deform bone (ignored)" % (b.name) )
                    continue

                export_bones.append(bone_name)
                log_export.info("export_bone_set: Appended bone [%s]" % bone_name)

                if not with_hierarchy:
                    continue

                p = b.parent
                if not p:
                    continue

                while p.parent: # do not proceed to Origin
                    if p.name not in export_bones:
                        if util.has_head_offset(joints, p) or sceneProps.collada_full_hierarchy:
                            export_bones.append(p.name)
                            log_export.info("export_bone_set: Appended parent bone [%s]" % p.name)
                        p = p.parent
                    else:
                        break
            else:
                log_export.warning("export_bone_set: Bone %s is missing in the armature. (ignore)" % (bone_name) )

        return export_bones



    sceneProps = context.scene.SceneProp
    meshProps = context.scene.MeshProp
    with_sl_rot = sceneProps.collada_export_rotated
    with_appearance = sceneProps.panel_appearance_enabled
    with_structure = sceneProps.collada_complete_rig
    img_w = sceneProps.baked_image_width
    img_h = sceneProps.baked_image_height
    force_rebake = sceneProps.force_rebake

    log_export.info("Export Avastar Collada for Target system[%s]" % (target_system) )
    pathbase, ext = os.path.splitext(path)
    base,filename = os.path.split(pathbase)

    armatures = []
    mesh_objects = []
    mat_images = {}
    materials_object_map = BakeMaterialsOperator.get_material_object_map(context)
    if exportTextures:
        for material, objects in materials_object_map.items():
            if not (material and material.node_tree):
                continue
            image_name, index, image_node = BakeMaterialsOperator.material_baked_image_name_and_index(material)
            if image_node  and image_node.image:
                mat_images[image_node.image] = material

    complexity_warnings = []
    help_page = get_help_page("AVASTAR_EXPORT_TROUBLE")



    util.progress_begin(0,10000)
    progress = 0
    util.progress_update(progress)

    selected_objects = util.get_meshes(context, type='MESH', select=True, visible=True, hidden=False)
    enumerated_objects = []

    for index, obj in enumerate(selected_objects):

        if export_armature:

            arm = util.getArmature(obj)

            if arm is not None and arm not in armatures:
                if 'avastar' in arm:
                    armatures.append(arm)
                else:
                    msg = ("> " + M008_not_an_avastar + "\n") % (
                            util.shorten_text(arm.name),
                            util.shorten_text(obj.name)
                        )
                    complexity_warnings.append([msg, help_page])
                    print("Warning: %s" % msg )
                    continue


        enumerated_objects.append((index, obj.name))
        mesh_objects.append(obj)


    enumerated_objects.sort(key=lambda name: name[1])

    if weld_normals:
        if weld_to_all_visible:
            mobs = [ob for ob in context.visible_objects if util.object_visible_get(ob, context=context) and ob.type=="MESH"]
        else:
            mobs = mesh_objects
        try:
            adjusted_normals = util.get_adjusted_vertex_normals(context, mobs, apply_modifier_stack, apply_mesh_rotscale)
        except:
            adjusted_normals = None
            log.error("Welding failed")

    else:
        log.warning("Export Welding is disabled")
        adjusted_normals = None
    #

    #
    root = et.Element('COLLADA', attrib={'xmlns':'http://www.collada.org/2005/11/COLLADASchema', 'version':'1.4.1'})  
    root.tail = os.linesep
    xml = et.ElementTree(root)
    
    asset = subx(root, 'asset')

    contributor = subx(asset, 'contributor')
    subx(contributor, 'author', text = "Avastar User")    
    avastar_version = "%d-%s-%d"%bl_info['version']
    subx(contributor, 'authoring_tool', text = 'Avastar %s on Blender %s'%(avastar_version,bpy.app.version_string))    
    tstamp = time.strftime("%Y-%m-%dT%H:%M:%S")



    subx(asset, 'created',  text=tstamp)    
    subx(asset, 'modified', text=tstamp)    
    subx(asset, 'unit',     name='meter', meter='1')    
    subx(asset, 'up_axis',  text="Z_UP")    
    
    subx(root, 'library_cameras')    
    subx(root, 'library_lights')

    if len(mat_images) > 0:

        libimages = create_libimages(
                                     root,
                                     base,
                                     mat_images,
                                     exportCopy,
                                     preferred_image_format,
                                     force_image_format,
                                     useImageAlpha,
                                     complexity_warnings)

    libeffects   = subx(root, 'library_effects')
    libmaterials = subx(root, 'library_materials')

    libgeo = subx(root, 'library_geometries')
    libcon = subx(root, 'library_controllers')
    libvis = subx(root, 'library_visual_scenes')
    visual_scene = subx(libvis, 'visual_scene', id='Scene', name='Scene')   
    arm_roots = {}

    active = context.object
    omode  = util.ensure_mode_is("OBJECT", context=context)
    root_bone_name = "Origin" if sceneProps.collada_complete_rig else "mPelvis"

    for arm in armatures:
        if with_appearance:
            prepare_armature_for_export(arm)    
    
        logging.debug("Export armature %s", arm.name)
        aid = colladaKey(arm.name)
        node = subx(visual_scene, 'node', id=aid, name=aid, type='NODE')
        subx(node, 'translate', sid='location', text='0 0 0')
        subx(node, 'rotate', sid='rotationZ', text='0 0 1 0')
        subx(node, 'rotate', sid='rotationY', text='0 1 0 0')
        subx(node, 'rotate', sid='rotationX', text='1 0 0 0')
        subx(node, 'scale', sid='scale', text='1 1 1')

        export_bone_set = get_armature_bone_set(context, arm)

        rigstates = {}
        util.set_active_object(context, arm)
        ohide = util.object_hide_get(arm)
        util.object_hide_set(arm, False)
        amode = util.ensure_mode_is("EDIT", context=context)
        export_joint_type = 'POS' if sceneProps.collada_assume_pos_rig else arm.RigProp.JointType
        Bones = data.get_reference_boneset(arm, arm.RigProp.RigType, export_joint_type)

        arm_roots[arm.name] = bonetoxml(arm, node, root_bone_name, apply_armature_scale, target_system, export_bone_set, rigstates, sceneProps, is_root=True, with_joints=with_joints, Bones=Bones)
        util.ensure_mode_is(amode, context=context)

        print("+-----------------------------------------------")
        print("| Exporting Armature  : %s" % arm.name )
        print("| Skeleton type       : %s" % target_system )
        print("| Joint type          : %s" % arm.RigProp.JointType )
        print("| Export Pose type    : %s-pose " % ("Bind" if use_bind_pose else "T") )
        print("| Export with Joints  : %s" % ("Enabled" if with_joints else "disabled") )
        print("| Apply Armature scale: %s" % apply_armature_scale )
        print("| Apply mesh scale    : %s" % apply_mesh_rotscale )
        print("+-----------------------------------------------")
        print("| Exporting Root bones:")
        roots = arm_roots[arm.name]
        for key in roots:
            print("|    %s" % (key) )
        print("| export bones (count): %d" % len(export_bone_set) )
        print("| Exported child bones:")
        for key, val in rigstates.items():
            if len(val) > 0:
                if key in ['avatar_pos']:
                    print("|    %3d %s bones" % (len(val), key))
                else:
                    print("|    %3d %s bones:" % (len(val), key))
                    for vkey, m in val.items():
                        t = m.translation
                        print("|        [% .6f % .6f % .6f] (%s)" % (t[0], t[1], t[2], vkey) )

        if export_deformer_shape:
            shape_file_path = pathbase + '.xml'
            shape.saveProperties(arm, shape_file_path, normalize=True)
        util.object_hide_set(arm, ohide)

    util.set_active_object(context, active)
    util.ensure_mode_is(omode, context=context)

    created_materials = {}

    geometry_name = None
    for index, obj_name in (enumerated_objects):
        meshobj = selected_objects[index]

        progress += 100
        util.progress_update(progress)

        try:
            assert ( obj_name == meshobj.name )
        except:
            logging.error("Error in ordering the selection by object name.")





        neutral_shape = None


        mesh_data_copy = util.getMesh(
                              context,
                              meshobj,
                              apply_modifier_stack,
                              apply_mesh_rotscale=apply_mesh_rotscale,
                              apply_armature_scale=apply_armature_scale,
                              apply_armature=False,
                              shape_data=neutral_shape,
                              sl_rotation = with_sl_rot)

        if meshProps.export_triangles:
            polygons = mesh_data_copy.polygons
            is_triangulated = True
            for p in polygons:
                if len(p.vertices) != 3:
                    is_triangulated = False
                    break

            if is_triangulated:
                print("| %s already fully triangulated (no need to perform triangulation)" % meshobj.name)
            else:
                triangulate_mesh(mesh_data_copy)
                print("| triangulated %s (Quad method:Beauty, Polygon method: Beauty)" % meshobj.name)

        log.info("Export: recalculate normals after getMesh()")

        logging.debug("Export mesh %s", meshobj.name)





        geometry_name = meshobj.name
        mid = colladaKey(meshobj.name)
        geo = subx(libgeo, 'geometry', id=mid+'-mesh', name=geometry_name)
        mx = subx(geo, 'mesh')

        #

        #

        for midx, mat in enumerate(meshobj.data.materials):
            if mat is None:

                continue

            avamat = AVAMaterial(mat)
            material_name = colladaKey(mat.name)


            if created_materials.get(material_name) is not None:
                continue
            created_materials[material_name]=material_name
            
            effect_id     = material_name+"-effect"
            material_id   = material_name+"-material"
            
            effect = subx(libeffects, "effect", id=effect_id)
            prof = subx(effect, "profile_COMMON")
            
            images = get_images_for_material(mat_images, mat)
            if len(images) > 0:
                image=images[0]
                if len(images) > 1:
                    print("| %d images assigned to material %s, take only %s" % (len(images), material_name, image.name))
            else:
                image = None

            if image is not None:
                collada_name = colladaKey(image.name)

                newparam = subx(prof, "newparam", sid=collada_name+'-surface')
                surface = subx(newparam, "surface", type="2D")
                initfrom = subx(surface, "init_from", text=collada_name)
           
                newparam = subx(prof, "newparam", sid=collada_name+'-sampler')
                sampler2d = subx(newparam, "sampler2D")
                source = subx(sampler2d, "source", text=collada_name+"-surface")

            tech = subx(prof, "technique", sid="common")
            phong = subx(tech, "phong")










            wrap = subx(phong, "ambient")
            col = subx(wrap, "color", sid="ambient", text="0 0 0 1")

            wrap = subx(phong, "diffuse")
            if image is not None:
                uv_layers = meshobj.data.uv_layers
                if not uv_layers:
                    log.warning("meshobj %s has no UV layers" % meshobj.name)
                active_layer = uv_layers.active
                if not active_layer:
                    log.warning("meshobj %s has no active UV layer" % meshobj.name)
                semantic = active_layer.name
                texture = subx(wrap, "texture", texture=collada_name+'-sampler', texcoord=semantic)
            else:
                diffuse_color = avamat.get_diffuse()
                alpha = avamat.get_alpha()
                c = ["%g"%(j) for j in diffuse_color]

                c.append("%g"%alpha) 
                col = subx(wrap, "color", sid="diffuse", text=" ".join(c))

            wrap = subx(phong, "specular")
            i = mat.specular_intensity
            c = ["%g"%(j*i) for j in mat.specular_color]
            if False:#mat.use_transparency:
                c.append("%g"%mat.specular_alpha)
            else:
                c.append("1")
            col = subx(wrap, "color", sid="specular", text=" ".join(c))




            if False:#mat.raytrace_mirror.use:
                wrap = subx(phong, "reflective")
                c = ["%g"%j for j in mat.mirror_color]
                c.append("1")
                col = subx(wrap, "color", sid="reflective", text=" ".join(c))

                wrap = subx(phong, "reflectivity")
                col = subx(wrap, "float", sid="reflectivity", text="%g"%mat.raytrace_mirror.reflect_factor)

            if False:#mat.use_transparency:
                wrap = subx(phong, "transparency")
                col = subx(wrap, "float", sid="transparency", text="%g"%mat.alpha)

            wrap = subx(phong, "index_of_refraction")
            col = subx(wrap, "float", sid="index_of_refraction", text="1.0")

            material = subx(libmaterials, "material", id=material_id, name=mat.name)
            subx(material, "instance_effect", url="#"+effect_id)

        #

        #

        source = subx(mx, 'source', id=mid+'-mesh-positions')
        positions = []

        for v in mesh_data_copy.vertices:
            p = util.sanitize_v(v.co, dae_precision)
            positions.append("%g"%p.x)
            positions.append("%g"%p.y)
            positions.append("%g  "%p.z)
            
        pos = subx(source, 'float_array', id=mid+'-mesh-positions-array', 
                   count=str(len(positions)))
        pos.text = " ".join(positions)
        
        tech = subx(source, 'technique_common')
        accessor = subx(tech, 'accessor', source='#'+mid+'-mesh-positions-array',
                            stride='3', count=str(int(len(positions)/3)))
        subx(accessor, 'param', name='X', type='float') 
        subx(accessor, 'param', name='Y', type='float') 
        subx(accessor, 'param', name='Z', type='float') 
    
        welded_normals = None
        if adjusted_normals and meshobj.name in adjusted_normals:
            welded_normals = adjusted_normals[meshobj.name]
        try:

            mesh_data_copy.calc_normals_split()
            log.info("Export: Recalculate Vertex Normals.")
        except:
            log.warning("Export: This Blender release does not support Custom Normals.")

        polylists, normals, uv_array = create_polylists(mesh_data_copy, welded_normals, progress)
        
        #

        #
        

        normals_array = []        
        for n in normals:
            san = util.sanitize_v(n, dae_precision)
            normals_array.append("%g"% san[0])
            normals_array.append("%g"%san[1])
            normals_array.append("%g  "%san[2])
                        
        source = subx(mx, 'source', id=mid+'-mesh-normals') 
        pos = subx(source, 'float_array', id=mid+'-mesh-normals-array',
                            count=str(len(normals_array))) 
        pos.text = " ".join(normals_array)
            
        tech = subx(source, 'technique_common')
        accessor = subx(tech, 'accessor', source='#'+mid+'-mesh-normals-array',
                            stride='3', count=str(int(len(normals_array)/3)))
        subx(accessor, 'param', name='X', type='float') 
        subx(accessor, 'param', name='Y', type='float') 
        subx(accessor, 'param', name='Z', type='float') 
            
        #

        #

        if len(uv_array) > 0:
            source = subx(mx, 'source', id=mid+'-mesh-map-0') 
            pos = subx(source, 'float_array', id=mid+'-mesh-map-0-array',
                                count=str(len(uv_array))) 
            pos.text = " ".join(uv_array)
                
            tech = subx(source, 'technique_common')
            accessor = subx(tech, 'accessor', source='#'+mid+'-mesh-map-0-array',
                                stride='2', count=str(int(len(uv_array)/2)))
            subx(accessor, 'param', name='S', type='float') 
            subx(accessor, 'param', name='T', type='float') 
        
        #

        #
        vert = subx(mx, 'vertices', id=mid+'-mesh-vertices')
        subx(vert, 'input', semantic='POSITION', source='#'+mid+'-mesh-positions')

        for mat_index in polylists:
            vcount = polylists[mat_index][POLYLIST_VCOUNT]
            ps     = polylists[mat_index][POLYLIST_P]
            lc     = polylists[mat_index][POLYLIST_COUNT]
            is_tris= polylists[mat_index][POLYLIST_IS_TRIS]
            try:
                material = meshobj.data.materials[mat_index]
                collada_material = colladaKey(material.name+"-material")
            except:
                material = None
            
            face_count = util.get_tri_count(len(vcount), lc)
            list_type = 'triangles' if is_tris else 'polylist'

            if material is not None:
                mat_name = material.name
                polylist = subx(mx, list_type, count=str(face_count), material=collada_material)
            else:
                mat_name = "Default Material"
                polylist = subx(mx, list_type, count=str(face_count))


            prefs=util.getAddonPreferences()
            if 0 < prefs.maxFacePerMaterial < face_count:
                msg = ("> " + messages.M005_high_tricount + "\n") % (face_count, mat_name, meshobj.name)
                complexity_warnings.append([msg, help_page])
                print("| Warning: %s" % msg )
                
            subx(polylist, 'input', source='#'+mid+'-mesh-vertices', 
                                    semantic='VERTEX', offset='0') 
            subx(polylist, 'input', source='#'+mid+'-mesh-normals', 
                                    semantic='NORMAL', offset='1') 


            if len(uv_array) > 0:
                subx(polylist, 'input', source='#'+mid+'-mesh-map-0', 
                                        semantic='TEXCOORD', offset='2', set='0') 
            if not is_tris:
                subx(polylist, 'vcount', text=' '.join(vcount))
            subx(polylist, 'p', text=' '.join(ps))
           
        extra = subx(geo, 'extra')
        tech = subx(extra, 'technique', profile='MAYA')
        subx(tech, 'double_sided', text='1')
           
        node = subx(visual_scene, 'node', id=mid, name=mid, type='NODE')
        
        #

        #

        arm = util.getArmature(meshobj)
        if arm is not None:
            util.set_active_object(context, arm)
            aid = colladaKey(arm.name)
            controler = subx(libcon, 'controller', name=aid, id=aid+"_"+mid+'-skin')
            skin = subx(controler, 'skin', source='#'+mid+'-mesh')  

            bsm = rig.calculate_bind_shape_matrix(arm, meshobj)
            bsm = " ".join(["%g"%bsm[ii][jj] for ii in range(4) for jj in range(4)])
            subx(skin, 'bind_shape_matrix', text=bsm)

            #

            #
            source = subx(skin, 'source', id=aid+"_"+mid+"-skin-joints") 
            dbones = [g.name for g in meshobj.vertex_groups] if sceneProps.collada_only_weighted else arm.data.bones.keys()
            indices= [g.index for g in meshobj.vertex_groups] #need this to "fix" corrupt vgroup info

            with_hierarchy = sceneProps.collada_full_hierarchy
            export_bones = get_collada_boneset(context, arm, dbones, with_hierarchy=with_hierarchy)

            renamed_groups = []
            for bone_name in export_bones:
                if bone_name[0] == 'a':
                    fname = attachment_name(bone_name, with_structure)
                    renamed_groups.append(fname)
                else:
                    renamed_groups.append(bone_name)
            bone_count = rig.get_max_bone_count(context.scene, [meshobj])
            if bone_count> MAX_EXPORT_BONES and sceneProps.use_export_limits:
                    msg = ("> " + messages.M004_weight_limit_exceed + "\n")%(meshobj.name, bone_count, MAX_EXPORT_BONES)
                    complexity_warnings.append([msg, help_page])
            
            subx(source, 'Name_array', id=aid+"_"+mid+'-skin-joints-array',
                                    count=str(len(export_bones)), 
                                    text = get_bind_joint_array(renamed_groups, 10))
            tech = subx(source, 'technique_common')
            accessor = subx(tech, 'accessor', 
                                source='#'+aid+'_'+mid+'-skin-joints-array',
                                stride='1',
                                count=str(len(export_bones)))
            subx(accessor, 'param', name='JOINT', type='name') 
            
            #

            #
            source = subx(skin, 'source', id=aid+"_"+mid+"-skin-bind_poses") 
            poses = []
            rig.reset_cache(arm)
            counter = 0
            ohide = util.object_hide_get(arm)
            util.object_hide_set(arm, False)
            omode = util.ensure_mode_is('POSE', context=context)
            log_export.debug("Export inverse bind pose matrix (use bind pose)")

            for bone_name in export_bones:

                dbone = arm.data.bones.get(bone_name)
                if not dbone:
                    log.warning("Bone %s not found in Armature %s (ignore)" % (bone_name, arm.name) )
                    continue

                counter += 1
                Minv = rig.calculate_inverse_bind_matrix(arm, dbone, apply_armature_scale, with_sl_rot, use_bind_pose, with_appearance)
                mat  = rig.matrixToStringArray(Minv, precision=dae_precision)
                if not (counter % 10):
                    mat[-1] = mat[-1]+"\n\n\n"
                poses.extend(mat)
            util.ensure_mode_is(omode, context=context)
            util.object_hide_set(arm, ohide)

            subx(source, 'float_array', id=aid+"_"+mid+'-skin-bind_poses-array',
                                        count=str(len(poses)),
                                        text = "\n"+" ".join(poses))
            tech = subx(source, 'technique_common')
            accessor = subx(tech, 'accessor', 
                                source='#'+aid+'_'+mid+'-skin-bind_poses-array',
                                stride='16',
                                count=str(int(len(poses)/16)))
            subx(accessor, 'param', name='TRANSFORM', type='float4x4') 
                
            #

            #
            ws = []
            vcount = []
            vs = []
            source = subx(skin, 'source', id=aid+"_"+mid+"-skin-weights")
            truncated_vcount = 0
            zero_weight_count = 0
            vcounter = 0
            ignored_groups = {}
            for v in mesh_data_copy.vertices:
                vcounter += 1
                if vcounter % 1000 == 0:
                    progress += 1
                    util.progress_update(progress)         
            
                weights = []
                for g in v.groups:

                    bonename = const.get_export_bonename(meshobj.vertex_groups, g.group, target_system)
                    if bonename and bonename in arm.data.bones:
                        b = arm.data.bones[bonename]
                        if b.use_deform:

                            if bonename in export_bones:
                                gidx = export_bones.index(bonename)
                                weights.append([g.weight, gidx])
                            else:
                                count = ignored_groups.get(bonename)
                                if count is None:
                                    count = 0
                                count += 1
                                ignored_groups[bonename]=count


                weights.sort(key=lambda x: x[0], reverse=True)
                
                if max_weight_per_vertex > 0 and len(weights)>max_weight_per_vertex:
                    if truncated_vcount < 10:
                        logging.warn("found vertex with %d deform weights in %s. Truncating to %d."%(len(weights), meshobj.name, max_weight_per_vertex))
                    weights = weights[:max_weight_per_vertex]
                    truncated_vcount += 1 
                

                tot = 0
                for w,g in weights:
                    tot+=w
                if tot > 0:
                    for wg in weights:
                        wg[0]=wg[0]/float(tot)
                else:
                    zero_weight_count += 1                    
                    
                for weight,group in weights:
                    widx = len(ws)
                    w = util.sanitize_f(weight, dae_precision)
                    ws.append("%g"%w)
                    vs.append(str(group)) 
                    vs.append(str(widx)+" ")
                vs.append(" ")
                vcount.append(str(len(weights)))
            
            for key,val in ignored_groups.items():
                msg = ("> " + messages.M003_undefined_weightmap + "\n")%(key,val)
                complexity_warnings.append([msg, help_page])
                logging.warn(msg)

            if zero_weight_count > 0:
                msg = ("> " + messages.M002_zero_weights + "\n")%(zero_weight_count, meshobj.name)
                complexity_warnings.append([msg, help_page])
                logging.warn(msg)

            if truncated_vcount > 0:
                msg = ("> " + messages.M001_limited_weightcount + "\n")%(truncated_vcount, meshobj.name)
                complexity_warnings.append([msg, help_page])
                logging.warn(msg)
                
            subx(source, 'float_array', id=aid+"_"+mid+'-skin-weights-array',
                                        count=str(len(ws)),
                                        text = " ".join(ws))
            tech = subx(source, 'technique_common')
            accessor = subx(tech, 'accessor', 
                                source='#'+aid+'_'+mid+'-skin-weights-array',
                                stride='1',
                                count=str(len(ws)))
            subx(accessor, 'param', name='WEIGHT', type='float') 
            joints = subx(skin, 'joints')
            subx(joints, 'input', semantic='JOINT', source='#'+aid+'_'+mid+'-skin-joints')
            subx(joints, 'input', semantic='INV_BIND_MATRIX', 
                                source='#'+aid+'_'+mid+'-skin-bind_poses')
            vweights = subx(skin, 'vertex_weights', count=str(len(vcount)))
            subx(vweights, 'input', semantic='JOINT',
                                    source='#'+aid+'_'+mid+'-skin-joints',
                                    offset='0') 
            subx(vweights, 'input', semantic='WEIGHT',
                                    source='#'+aid+'_'+mid+'-skin-weights',
                                    offset='1') 
            subx(vweights, 'vcount', text=" ".join(vcount))
            subx(vweights, 'v', text=" ".join(vs))
            
            #

            #
            subx(node, 'translate', sid='location', text='0 0 0')   
            subx(node, 'rotate', sid='rotationZ', text='0 0 1 0')   
            subx(node, 'rotate', sid='rotationY', text='0 1 0 0')   
            subx(node, 'rotate', sid='rotationX', text='1 0 0 0')   
            subx(node, 'scale', sid='scale', text='1 1 1')   
   
            con = subx(node, 'instance_controller', url='#'+aid+'_'+mid+'-skin')   
            
            if arm in armatures:
                rootnames = arm_roots.get(arm.name,None)
                if rootnames:
                    for rootname in rootnames:
                        subx(con, 'skeleton', text= "#%s" % rootname) 
                else:
                    subx(con, 'skeleton', text='#%s' % root_bone_name)

            else:

                subx(con, 'skeleton', text='#Origin') 
                
            if len(meshobj.data.materials) > 0:
                bind = subx(con, "bind_material")
                tech = subx(bind, "technique_common")
                add_material_list(tech, meshobj, len(uv_array) )









        else:






            if apply_mesh_rotscale:
                loc = '%g %g %g'%tuple(meshobj.location)
                subx(node, 'translate', sid='location', text=loc)
                subx(node, 'rotate', sid='rotationZ', text='0 0 1 0')
                subx(node, 'rotate', sid='rotationY', text='0 1 0 0')
                subx(node, 'rotate', sid='rotationX', text='1 0 0 0')
                subx(node, 'scale', sid='scale', text='1 1 1')
            else:
                mat = ["\n    %f %f %f %f"% (v[0], v[1], v[2], v[3]) for v in meshobj.matrix_world]
                subx(node, 'matrix', sid='transform', text=" ".join(mat)+"\n")





            con = subx(node, 'instance_geometry', url='#'+mid+'-mesh')   

            if len(meshobj.data.materials) > 0:
                bind = subx(con, "bind_material")
                tech = subx(bind, "technique_common")
                add_material_list(tech, meshobj, len(uv_array) )


        bpy.data.meshes.remove(mesh_data_copy)

    if with_appearance:
        for armobj in armatures:
            restore_armature_after_export(armobj)

    scene = subx(root, 'scene')
    subx(scene, 'instance_visual_scene', url='#Scene')

    indentxml(root)

    status = False
    try:
        xml.write(path, xml_declaration=True, encoding="utf-8")
        logging.info("Exported model to: %s", path)
        status = True
        if sceneProps.collada_export_shape:
            if armatures:
                file_path = os.path.splitext(path)[0]
                for arm in armatures:
                    name = '_' + arm.name if len(armatures) > 1 else ""
                    shape_file_path = file_path+name+".shape"
                    shape.saveProperties(arm, shape_file_path)
                    log.warning("Exported shape to [%s]" % file_path)

    except Exception as e:
        msg = _("The file %s could not be written to the specified location.|\n" \
              "This is the reported error: %s\n" \
              "Please check the file permissions and try again." % (path,e))
        logging.error(msg)
        raise util.Warning(msg)
    finally:
        util.progress_end()

    return status, len(enumerated_objects), complexity_warnings

def subx(parent, tag, **attrib):


    attrib2 = {}
    for key,value in attrib.items():
        if key!='text':
            attrib2[key]=value
    sub = et.SubElement(parent, tag, attrib=attrib2)
    if 'text' in attrib:
        sub.text = attrib['text']
    return sub    

def bonetoxml(arm, parent, bonename, apply_armature_scale, target_system, export_bone_set, rigstates, sceneProps, is_root=False, with_joints=False, Bones=None):
    dae_precision = util.get_precision()

    def is_in_export_hierarchy(bname, export_bone_set):
        return (not export_bone_set) or bname in export_bone_set

    node          = parent #preset
    with_structure = sceneProps.collada_complete_rig
    only_deform   = sceneProps.collada_only_deform and not with_structure
    only_weighted = sceneProps.collada_only_weighted and not with_structure
    with_roll     = sceneProps.collada_export_boneroll
    with_layers   = sceneProps.collada_export_layers
    with_attachments = sceneProps.accept_attachment_weights or with_structure
    use_blender   = sceneProps.collada_blender_profile
    with_sl_rot   = sceneProps.collada_export_rotated
    jointtype     = 'POS'
    bones         = util.get_modify_bones(arm)

    roots = set()


    bone = bones.get(bonename, None)
    if bone == None:
        log.warning("bone_to_xml: Bone %s not in armature %s" % (bonename, arm.name))
        return roots

    fbonename = bonename
    in_export_hierarchy = is_in_export_hierarchy(bonename, export_bone_set)

    if in_export_hierarchy:#bone.use_deform or not only_deform:
        if bonename[0] == 'a':
            if sceneProps.accept_attachment_weights or with_structure:
                fbonename = attachment_name(bonename, with_structure)
            else:


                return roots




        if in_export_hierarchy:
            if with_layers:
                layers = [str(e) for e,l in enumerate(bone.layers) if e < 31 and l]
                node = subx(parent, 'node', id=fbonename, name=fbonename, sid=fbonename, type='JOINT', layer=" ".join(layers))
            else:
                node = subx(parent, 'node', id=fbonename, name=fbonename, sid=fbonename, type='JOINT')

            if is_root:
                roots.add(bonename)
                is_root = False

            M, p, bone_type = rig.calculate_pivot_matrix(bpy.context, arm, bone, bones, with_sl_rot, with_joints, Bones=Bones, apply_armature_scale=apply_armature_scale, with_structure=with_structure)
            mat = rig.matrixToStringArray(M, precision=dae_precision)

            subx(node, 'matrix', sid='transform', text=" ".join(mat))

            if use_blender: #export with blender profile
                extra = subx(node, 'extra')
                tech  = subx(extra, 'technique', profile='blender')
                if with_layers:
                    layer = subx(tech, 'layer', text=" ".join(layers))

                conn = subx(tech, 'connect', text="1" if bone.use_connect else "0" )

                ebone = arm.data.edit_bones[bonename]
                if with_roll:
                    if ebone.roll != 0:
                        subx(tech, 'roll', text="%f"%ebone.roll)

                if True or not Skeleton.has_connected_children(bone):
                    tail = ebone.tail - ebone.head
                    if with_sl_rot:

                        tail = [-tail[1], tail[0], tail[2]]

                    x = subx(tech, 'tip_x', text="%f"%tail[0])
                    y = subx(tech, 'tip_y', text="%f"%tail[1])
                    z = subx(tech, 'tip_z', text="%f"%tail[2])

            subset = rigstates.get(bone_type, None)
            if not subset:
                subset = {}
                rigstates[bone_type] = subset
                print("| Using subset %s" % bone_type)
            subset[bone.name] = M
    else:
        log.info("bone_to_xml: Bone %s is not in export set" % (bonename) )

    for b in bone.children:

        r = bonetoxml(arm, node, b.name, apply_armature_scale, target_system, export_bone_set, rigstates,  sceneProps, is_root, with_joints, Bones)
        if len(r) > 0:
            roots |= r

    return roots


def indentxml(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indentxml(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def create_bw_mask(obj, vgroup, mask_name):
    me         = obj.data
    polygons   = me.polygons
    vertices   = me.vertices
    groupIndex = obj.vertex_groups[vgroup].index
    
    try:

        vcol = me.vertex_colors[mask_name]
    except:
        vcol = me.vertex_colors.new(name=mask_name)
 

    for p in polygons:
        for index in p.loop_indices:
            v = vertices[me.loops[index].vertex_index]
            vcol.data[index].color=(0,0,0)
            for g in v.groups:
                if g.group == groupIndex:
                    vcol.data[index].color=(1,1,1)
                    break

    original_mode = obj.mode
    bpy.ops.object.editmode_toggle()
    util.mode_set(mode=original_mode)

def get_mesh_stats(scene, meshobj):
    stats = meshobj.get(MESH_STATS)
    if not stats:
        stats = util.create_mesh_stats(scene, meshobj)
    return stats


class UpdateMeshStatistic(bpy.types.Operator):
    '''
    Collect mesh information for selected mesh objects
    '''
    bl_idname = "avastar.update_mesh_stats"
    bl_label = "Refresh statistic"
    bl_description = "Collect mesh information.\n"\
                   + "Please Refresh when you want to be sure\n"\
                   + "that you see the most recent statistic.\n"\
                   + "Or enable auto update(*)\n"\
                   + "\n"\
                   + "(*)When auto update is enabled, the UI slows down with increasing mesh size"

    @classmethod
    def poll(self, context):
        return not context.scene.MeshProp.auto_refresh_mesh_stat

    def execute(self, context):

        if context.mode == 'EDIT_MESH':
            bpy.context.object.update_from_editmode()

        meshobjs = [ob for ob in context.selected_objects if ob.type == 'MESH']
        for obj in meshobjs:
            obj[MESH_STATS] = util.create_mesh_stats(context.scene, obj)
        return {'FINISHED'}

class ClosestPoint:

    def __init__(self, refloc=None, obj=None, loc=None, index=None, distance=None):
        self.mindist = distance if distance else None
        self.delta = loc - refloc if loc and refloc else None
        self.minobj = obj
        self.minloc = loc
        self.source_co = refloc
        self.index = index

    def get_object(self):
        return self.minobj

    def is_defined(self):
        return self.mindist != None

    def is_close(self):
        return self.mindist < 0.0000001

    def is_in_range(self, maxrange):
        return self.mindist < maxrange

    def get_distance_vector(self):
        return self.delta

    def get_closest_location(self):
        return self.source_co

class KDTreeSet:

    trees = {}

    def add(self, obj):
        mesh = obj.data
        size = len(mesh.vertices)
        kd = KDTree(size)
        for i, v in enumerate(mesh.vertices):
            co = mulmat(obj.matrix_world, v.co)
            kd.insert(co, i)
        kd.balance()
        self.trees[obj] = kd

    def find(self, refco):

        obj = None
        loc = None
        index = None
        distance = None

        for ob, kd in self.trees.items():

            _loc, _index, _distance = kd.find(refco)
            if distance == None or distance > _distance:
                distance = _distance
                index = _index
                loc = _loc
                obj = ob

        if obj:

            point = ClosestPoint(refco, obj, loc, index, distance)
        else:
            point = ClosestPoint()
        return point

def snap_to_mesh(context, maxrange=0.001, mark_out_of_range=True, mark_snapped=False, snap=True):
    scene = context.scene

    GOOD  = "ignored vertex %d (not snapped to %s shift=[%f,%f,%f]) (already snapped)"
    RANGE = "ignored vertex %d (not snapped to %s shift=[%f,%f,%f]) (target out of range)"
    SNAP  = "snapped vertex %d to object %s (shift=[%f,%f,%f])"

    omode = bpy.context.object.mode
    util.mode_set(mode='OBJECT')

    edit_obj = context.active_object
    me = edit_obj.data
    mesh_objects = [o for o in scene.objects if o.type == 'MESH' and util.object_visible_get(o, context=context)]

    kdtrees = KDTreeSet()
    for obj in [ o for o in mesh_objects if o != edit_obj]:
        kdtrees.add(obj)

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    mesh_has_changed = False
    out_of_range = []
    snapped = []
    
    max_offset = 0

    for vert in [v for v in bm.verts if v.select]:

        target_co = mulmat(edit_obj.matrix_world, vert.co) # convert to global space
        point = kdtrees.find(target_co)

        if point.is_defined():
            delta = point.get_distance_vector()
            if delta.magnitude > max_offset:
                max_offset = delta.magnitude

            if point.is_close():

                pass
            elif point.is_in_range(maxrange):
                snapped.append(vert.index)
                minobj = point.get_object()

                if snap:
                    vert.co += delta
                mesh_has_changed = True
            else:
                out_of_range.append(vert.index)
                source_co = point.get_closest_location()


    if mesh_has_changed:
        bm.to_mesh(me)
    bm.clear()

    if mark_out_of_range or mark_snapped:
        util.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        util.mode_set(mode='OBJECT')

        for vert in edit_obj.data.vertices:
           vert.select = (mark_out_of_range and vert.index in out_of_range) \
                      or (mark_snapped and vert.index in snapped)

        edit_obj.update_from_editmode()
    util.mode_set(mode=omode)

    return len(snapped), len(out_of_range), max_offset

class AvastarSnapToMesh(bpy.types.Operator):
    bl_idname = "avastar.snap_to_mesh"
    bl_label = "Snap to Mesh"
    bl_description = "Snap selected vertices to closest point on other meshes\n\n"\
                     "Note: This function works only in Edit mode"
    bl_options = {'REGISTER', 'UNDO'}

    maxrange : FloatProperty(
        name = "snap range",
        min = 0.0,
        max = 100,
        default = 0.001,
        description = '''Maximum distance to the nearest point.
If a vertex is not close enough to any vertex
on another mesh, it is not snapped'''
        )

    mark_out_of_range : BoolProperty(
        name="Mark Out of Range",
        default=True,
        description = "Keep out of range verts selected" )

    mark_snapped : BoolProperty(
        name="Mark Snapped",
        default=False,
        description = "Keep snapped verts selected" )

    snap : BoolProperty(
        name="Snap Selected",
        default=True,
        description = "Snap Selected verts to Target location if nearest point was found" )

    snapped = None
    out_of_range = None
    max_offset = 0

    def draw(self, context):
        layout = self.layout
        col   = layout.column()
        col.prop(self, "maxrange")
        col.prop(self, "snap")
        col.prop(self, "mark_out_of_range")
        col.prop(self, "mark_snapped")

        if self.snapped != None or out_of_range != None:
            col.separator()
            box = col.box()
            col = box.column(align=True)
            col.label(text="%d verts snapped" % self.snapped)
            col.label(text="%d verts out of range" % self.out_of_range)
            col.label(text="max offset  %g" % self.max_offset)

    @classmethod
    def poll(self, context):
        obj = context.object
        if not obj:
            return False
        return obj.type == 'MESH' and obj.mode=='EDIT'

    def execute(self, context):
        self.snapped, self.out_of_range, self.max_offset = snap_to_mesh(context, self.maxrange, self.mark_out_of_range, self.mark_snapped, self.snap)
        return {'FINISHED'}

classes = (
    PanelAvatarShapeIO,
    ButtonBoneDisplayDetails,
    ButtonColladaDisplayTextures,
    ButtonColladaDisplayAdvanced,
    ButtonRigdisplayAnimationBoneGroups,
    ButtonRigdisplayDeformBoneGroups,
    ButtonRigdisplaySpecialBoneGroups,
    ButtonColladaResetAdvanced,
    ButtonColladaDisplayUnsupported,
    ButtonSmoothWeights,
    ButtonDistributeWeights,
    ButtonBasicPreset,
    ButtonAdvancedPreset,
    ButtonAllPreset,
    ButtonBonePresetSkin,
    ButtonBonePresetScrub,
    ButtonBonePresetAnimate,
    ButtonBonePresetRetarget,
    ButtonBonePresetEdit,
    ButtonBonePresetFit,
    ButtonRebakeUV,
    ButtonFindDoubles,
    ButtonFindUnweighted_old,
    ButtonFindUnweighted,
    ButtonFindZeroWeights,
    ButtonFindTooManyWeights,
    ButtonFixTooManyWeights,
    ButtonFindAsymmetries,
    ButtonFixAsymmetries,
    ButtonFreezeShape,
    ButtonConvertShapeToCustom,
    ButtonApplyShapeSliders,
    CleanupCustomProps,
    ButtonUnParentArmature,
    ButtonParentArmature,
    ButtonReparentArmature,
    ButtonRebindArmature,
    ButtonReparentMesh,
    ButtonArmatureAllowStructureSelect,
    ButtonArmatureRestrictStructureSelect,
    ButtonArmatureUnlockLocation,
    ButtonArmatureUnlockVolume,
    ButtonArmatureUnlockRotation,
    ButtonArmatureLockRotation,
    ButtonArmatureLockLocation,
    ButtonArmatureLockVolume,
    ButtonArmatureResetPoseLSL,
    ButtonDevkitManagerCutPreset,
    ButtonArmatureResetPose,
    ButtonArmatureApplyAsRestpose,
    ButtonArmatureBake,
    ButtonSupportInfo,
    ArmatureSpineUnfoldUpper,
    ArmatureSpineDisplayUpper,
    ArmatureSpineDisplayLower,
    ArmatureSpineUnfoldLower,
    ArmatureSpineUnfold,
    ArmatureSpinefold,
    ButtonArmatureBoneSnapper,
    ButtonAlphaMaskBake,
    ButtonDeformUpdate,
    ButtonDeformEnable,
    ButtonDeformDisable,
    ButtonImportAvastarShape,
    ButtonExportSLCollada,
    ButtonExportDevkitConfiguration,
    ButtonImportDevkitConfiguration,
    DummyOp,
    UpdateAvastarPopup,
    BakeShapeOperator,
    BakeMaterialsOperator,
    BakeCleanupMaterialsOperator,
    UpdateMeshStatistic,
    AvastarSnapToMesh
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered mesh:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered mesh:%s" % cls)
