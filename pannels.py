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
import logging, gettext, os, time, re, shutil
import addon_utils

from . import animation, const, copyrig, create, data, mesh, messages, rig, shape, util, weights
from .const import *
from bpy.props import *
from .util import logtime, mulmat
from .util  import rescale
from .shape import get_shapekeys, is_set_to_default

log = logging.getLogger('avastar.pannels')
registerlog = logging.getLogger("avastar.register")

def warn_if_camera_locked_to_layers(view, layout):
    return True # discard for 2.80
    if view and not view.lock_camera:
        col = layout.box()
        col.alert=True
        col.label(text="Scene Layers disabled",icon=ICON_ERROR)
        col.label(text="Tools might fail")
        row=col.row(align=True)
        row.label(text="Enable Scene Layers here:")
        row.prop(view,"lock_camera", text="")





class PanelWorkflow(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Workflows"
    bl_idname      = "AVASTAR_PT_workflow"
    bl_options     = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_WORKFLOW, msg=panel_info_workflow)

    def draw(self, context):

        def draw_preset_row(col, op, is_active, icon_key):
            icon_value = get_icon(icon_key)
            row=col.row(align=True)
            row.operator(op, text='', icon_value=icon_value)
            row.operator(op)
            if is_active:
                row.operator(op, icon=ICON_LAYER_ACTIVE, text='')


        layout = self.layout
        scn    = context.scene
        active = context.object
        armobj = util.get_armature(active)
        box = layout
        preferences = util.getAddonPreferences()
        last_preset = context.scene.SceneProp.panel_preset
        last_skill  = context.scene.SceneProp.skill_level

        ui_level = util.get_ui_level()

        col = box.column(align=True)

        draw_preset_row(col, "avastar.basic_preset", last_skill == 'BASIC', ICON_MONKEY)
        draw_preset_row(col, "avastar.expert_preset", last_skill == 'EXPERT', ICON_LIGHT_DATA)
        draw_preset_row(col, "avastar.all_preset", last_skill == 'ALL', ICON_RADIOBUT_ON)

        col.separator()
        col.label(text="Workflow Presets")

        col = box.column(align=True)

        draw_preset_row(col, "avastar.bone_preset_skin", last_preset == 'SKIN', "mbones")
        draw_preset_row(col, "avastar.bone_preset_scrub", last_preset == 'SCRUB', "xbones")
        draw_preset_row(col, "avastar.bone_preset_animate", last_preset == 'POSE', "cbones")
        draw_preset_row(col, "avastar.bone_preset_fit", last_preset == 'FIT', "fbones")
        draw_preset_row(col, "avastar.bone_preset_retarget", last_preset == 'RETARGET', "retarget")
        draw_preset_row(col, "avastar.bone_preset_edit", last_preset == 'EDIT', ICON_OUTLINER_OB_ARMATURE)

        workspace_sl_animation = bpy.data.workspaces.get(WORKSPACE_SL_ANIMATION)
        label = 'SL Animation Workspace loaded' if workspace_sl_animation else 'Load SL Animation Workspace'
        col.separator()
        col = box.column(align=True)
        col.label(text='Workspaces')
        col.operator("avastar.load_sl_animation_workspace", text= label)
        col.enabled = not workspace_sl_animation

        col.separator()
        col = box.column(align=True)
        col.operator('avastar.pref_show')

class ButtonLoadWorkspace(bpy.types.Operator):
    bl_idname = "avastar.load_sl_animation_workspace"
    bl_label  = "Load SL Animation workspace"
    bl_description = "The SL-Animation workspace has been optimized for SL Users.\nAfter loading the workspace you find it in the\nWorkspace list in the top bar of the Blender screen"

    def execute(self, context):
        util.load_workspace(context, WORKSPACE_SL_ANIMATION, STARTUP_BLEND)
        return {'FINISHED'}





class PanelShaping(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Avatar Shape"
    bl_idname      = "AVASTAR_PT_shaping"
    bl_options     = {'DEFAULT_CLOSED'}
    
    @staticmethod
    def recalculate_bone_usage(context, arm, pids):
        isCollisionRig = rig.is_collision_rig(context.object)
        
        for pid in pids:
            P = arm.ShapeDrivers.DRIVERS.get(pid)
            if not P:
                continue        
            D = P[0]
            if arm.RigProp.RigType != 'BASIC' and pid in shape.SHAPE_FILTER['Extended']:
                D['icon'] = get_cust_icon('ebone')
                D['hint'] = "avastar.shape_type_extended_hint"
            elif arm.RigProp.RigType != 'BASIC' and pid in shape.SHAPE_FILTER['Skeleton']:
                D['icon'] = get_cust_icon('mbone')
                D['hint'] = "avastar.shape_type_bone_hint"
            elif arm.RigProp.RigType == 'BASIC' and pid not in shape.SHAPE_FILTER['Extended'] and pid not in shape.SHAPE_FILTER['Fitted']:
                D['icon'] = get_cust_icon('mbone')
                D['hint'] = "avastar.shape_type_bone_hint"
            else:
                if pid in shape.SHAPE_FILTER['Fitted'] and (context.object == arm or 'avastar-mesh' not in context.object):
                    D['icon'] = get_cust_icon('vbone') if isCollisionRig else get_sys_icon('SNAP_OFF')
                    D['hint'] =  "avastar.shape_type_fitted_hint"
                else:
                    D['icon'] = get_sys_icon('BLANK1')
                    D['hint'] = "avastar.shape_type_system_morph_hint" if 'avastar-mesh' in context.object else "avastar.shape_type_morph_hint"
    @staticmethod
    def draw_generic(op, context, armobj, layout):

        def get_icon_for_slider(armobj, pid):
            state = get_slider_state(armobj, pid)
            if state == 'cached':
                icon = ICON_KEYTYPE_BREAKDOWN_VEC
            elif state == 'default':
                icon = ICON_BLANK1
            else:
                icon = ICON_LOAD_FACTORY
            return icon

        scn = context.scene
        obj = context.active_object
        sceneProps = context.scene.SceneProp
        if not util.use_sliders(context):
            box = layout.box()
            box.alert=True
            box.label(text="Sliders disabled")
            return

        if DIRTY_RIG in armobj:
            if sceneProps.panel_appearance_enabled:

                col = layout.row(align=True)
                col.label(text="Dirty Rig!", icon=ICON_ERROR)
                
                row=layout.row(align=True)
                op = row.operator("avastar.armature_jointpos_store", text="Recalculate Sliders",  icon=ICON_FILE)
                row.prop(sceneProps, "snap_control_to_rig", text='', icon=ICON_ARROW_LEFTRIGHT)
                op.sync = False
                op.snap_control_to_rig = sceneProps.snap_control_to_rig

                layout = layout.box()
                layout.enabled=False

            layout.alert=True
        else:
            currentSelection = util.getCurrentSelection(context)
            targets = currentSelection['targets']
            to_fix = check_repair_mesh(context, armobj, targets, layout)
            if to_fix:
                col = layout.column(align=True)
                add_repair_mesh_button(to_fix, layout)
                layout = layout.box()

        if not hasattr(armobj.ShapeDrivers, 'DRIVERS'):

            layout.operator("avastar.load_shape_ui")
        else:
            P = armobj.ShapeDrivers.DRIVERS.get("male_80")
            supports_shapes   = sceneProps.panel_appearance_enabled
            supports_sparkles = 'toolset_pro' in dir(bpy.ops.sparkles)

            last_select = bpy.types.AVASTAR_MT_shape_presets_menu.bl_label
            row = layout.row(align=True)

            subrow = row.row(align=True)
            icon = ICON_UNLOCKED if rig.appearance_editable(context) else ICON_LOCKED
            subrow.prop(armobj.RigProp,"rig_appearance_editable",icon=icon, text='')

            subrow = row.row(align=True)
            subrow.enabled = rig.appearance_editable(context)
            if rig.appearance_editable(context):
                if armobj.ShapeDrivers.male_80:
                    default_icon_value = get_cust_icon('defaultmale')
                    base_icon_value = get_cust_icon('basemale')
                    bind_icon_value = get_cust_icon('bindshapemale')
                else:
                    default_icon_value = get_cust_icon('defaultshape')
                    base_icon_value = get_cust_icon('baseshape')
                    bind_icon_value = get_cust_icon('bindshape')

                subrow.operator("avastar.reset_to_default", text="", icon_value=default_icon_value, emboss=rig.appearance_editable(context))
                subrow.operator("avastar.reset_to_restpose", text="", icon_value=base_icon_value, emboss=rig.appearance_editable(context))
                if 'shape_buffer' in obj:
                    subrow.operator("avastar.reset_to_bindshape", text="", icon_value=bind_icon_value, emboss=rig.appearance_editable(context))

                if rig.appearance_editable(context):

                    subrow.operator("avastar.save_props", text="", icon=ICON_EXPORT).destination='FILE'
                    subrow.operator("avastar.load_props", text="", icon=ICON_IMPORT).source='FILE'

                subrow.menu("AVASTAR_MT_shape_presets_menu", text=last_select )
                subrow.operator("avastar.shape_presets_add", text="", icon=ICON_ADD)
                if last_select not in ["Shape Presets", "Presets"]:
                    subrow.operator("avastar.shape_presets_update", text="", icon=ICON_FILE_REFRESH)
                    subrow.operator("avastar.shape_presets_remove", text="", icon=ICON_REMOVE).remove_active = True
            else:
                subrow.label(text='Unlock for editing')

            col = layout.column(align=True)
            row = col.row(align=True)
            col.prop(armobj.RigProp,"rig_use_bind_pose")
            col.prop(armobj.RigProp,"rig_lock_scales")
            col.enabled = rig.appearance_editable(context)

            bones = armobj.data.bones
            mSkull = bones.get('mSkull', None)
            Origin = bones.get('Origin', None)
            if mSkull and Origin:
                height = mulmat(armobj.matrix_world, (mSkull.head_local- Origin.head_local)).z
                label  = "%.2fm"%height
            else:
                label  = ""

            if P:

                col = layout.column(align=True)
                row=col.row(align=False)
                row.prop(armobj.RigProp, "gender", text='',expand=False)
                row.label(text=label)
                col.enabled = rig.appearance_editable(context)

            ui_level = util.get_ui_level()
            if ui_level >= UI_ADVANCED:
                if obj.type=='MESH' and obj.data.shape_keys and obj.data.shape_keys.key_blocks and not 'avastar-mesh' in obj:


                    animation_data = obj.data.shape_keys.animation_data
                    if animation_data:
                        drivers = animation_data.drivers
                        if drivers and len(drivers) > 0:
                            preferences = util.getPreferences()
                            col = layout.column(align=True)
                            col.enabled = rig.appearance_editable(context)
                            col.prop(preferences.system,"use_scripts_auto_execute", icon=ICON_SCRIPT, text='')

            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(armobj.ShapeDrivers, "Sections", text="")
            if not rig.appearance_editable(context):
                row=row.row(align=True)
                row.enabled=False
            row.operator("avastar.reset_shape_section", text="", icon=ICON_LOAD_FACTORY )

            try:
                male = armobj.ShapeDrivers.male_80
            except:
                male = False

            pids = get_shapekeys(context, armobj, obj)
            PanelShaping.recalculate_bone_usage(context, armobj, pids)
            joints = util.get_joint_cache(armobj)
            for pid in pids:
                P = armobj.ShapeDrivers.DRIVERS.get(pid)
                if not P:
                    continue

                D = P[0]
                s = D['sex']
                if pid=="male_80":
                    pass
                elif s is None or (s=='male' and male==True) or (s=='female' and male==False):
                    icon_value = D['icon']
                    opid = D['hint']
                    bones, joint_count = shape.get_driven_bones(armobj.data.bones, armobj.ShapeDrivers.DRIVERS, D, joints)

                    if D.get('show',False) and len(bones) > 0:
                        keys = sorted(bones.keys())
                        effective_keys = []
                        for key in keys:
                            bone = armobj.data.bones.get(key)
                            mbone = armobj.data.bones.get('m'+key)
                            if bone != None or mbone != None:
                                effective_keys.append(key)
                    else:
                        effective_keys = []


                    sliderRow = col.row(align=True)
                    if joint_count > 0:
                        sliderRow.alert = True

                    try:
                        prop=sliderRow.operator(opid, text="", icon_value=icon_value)

                    except:
                        prop=sliderRow.operator(opid, text="", icon=ICON_BLANK1)
                    prop.pid=pid

                    sliderRow.prop(armobj.ShapeDrivers, pid , slider=True, text = D['label'])

                    is_shaped_mesh = supports_shapes and obj!=armobj
                    
                    if supports_sparkles:
                        if supports_shapes and obj!=armobj:# and icon=='SNAP_ON':
                            name = mesh.get_corrective_key_name_for(pid)
                            is_driven = obj.data.shape_keys and name in obj.data.shape_keys.key_blocks
                            icon = ICON_DRIVER if is_driven else ICON_SHAPEKEY_DATA
                            prop=sliderRow.operator("sparkles.create_corrective_shape_key",text='', icon=icon)
                            prop.name     = name

                        else:
                            prop = sliderRow.operator(opid, text="", icon=ICON_BLANK1)
                            prop.pid=pid

                    icon = get_icon_for_slider(armobj, pid)
                    sliderRow.operator("avastar.reset_shape_slider", text="", icon=icon).pid=pid
                    sliderRow.enabled = rig.appearance_editable(context)

                    if len(effective_keys) > 0:
                        if len(bones) > 0:
                            irow = col.box().row(align=True)
                            lcol = irow.column(align=True)
                            mcol = irow.column(align=True)
                            rcol = irow.column(align=True)

                            for key in effective_keys:
                                bone = armobj.data.bones.get(key)
                                mbone = armobj.data.bones.get('m'+key)
                                if bone == None and mbone == None:
                                    log.warning("Key %s not found" % (key) )
                                    continue

                                icon = ICON_KEYTYPE_BREAKDOWN_VEC if obj==armobj or (is_shaped_mesh and key in obj.vertex_groups) else ICON_BLANK1
                                val = bones.get(key)
                                lrow = lcol.row(align=True)
                                mrow = mcol.row(align=True)
                                mrow.alignment='RIGHT'
                                rrow = rcol.row(align=True)
                                rrow.alignment='RIGHT'
                                trans,scale = val

                                has_offset = joints and \
                                    (util.has_head_offset(joints, bone) or \
                                     util.has_head_offset(joints, mbone))

                                if  has_offset:
                                    prop=lrow.operator("avastar.armature_jointpos_remove", text='', icon=ICON_CANCEL, emboss=False)

                                    prop.joint=key

                                elif icon==ICON_KEYTYPE_BREAKDOWN_VEC:
                                    opid = "avastar.slider_info_operator"
                                    op = lrow.operator(opid, text='', icon=icon, emboss=False)
                                    op.icon = SEVERITY_INFO
                                else:
                                    lrow.label(text='', icon=icon)

                                lrow.label(text=key)
                                mrow.label(text='Trans' if trans else '')
                                rrow.label(text='Scale' if scale else '')

            meshProps = bpy.context.scene.MeshProp
            col = layout.column(align=True)
            col.enabled = rig.appearance_editable(context)
            row = col.row(align=True)
            row.operator("avastar.bake_shape", text="Bake to Mesh", icon=ICON_PREFERENCES)
            if len(util.get_modifiers(context.object,'SHRINKWRAP')) > 0:
                row.prop    (meshProps, "apply_shrinkwrap_to_mesh", text='', toggle=False)

    @classmethod
    def poll(self, context):
        p = util.getAddonPreferences()
        if p.show_panel_shape_editor == 'PROPERTIES':
            return False
    
        obj = util.get_armature(context.active_object)
        return obj and obj.type=='ARMATURE' and "avastar" in obj

    def draw_header(self, context):
        sceneProps = context.scene.SceneProp
        row = self.layout.row(align=True)
        util.draw_info_header(row, AVASTAR_APPEARANCE, msg=panel_info_appearance, op=sceneProps, is_enabled="panel_appearance_enabled")

    def draw(self, context):
        armobj = util.get_armature(context.active_object)
        PanelShaping.draw_generic(self, context, armobj, self.layout)


def get_slider_state(armobj, pid):
    cached_target = shape.shape_store_used(pid)
    if cached_target:
        state = 'cached'
    elif is_set_to_default(armobj,pid):
        state = 'default'
    else:
        state = 'modified'
    return state






def BoneRotationLockStates(armobj, constraint):
    try:
        deformBones       = rig.get_pose_bones(armobj, armobj.RigProp.ConstraintSet, spine_check=True, deforming=True)
        constrainedBones  = [b for b in deformBones.values() if len( [c for c in b.constraints if c.type==constraint] ) > 0]
        mutedBones        = [b for b in deformBones.values() if len( [c for c in b.constraints if c.type==constraint and c.mute==True] ) > 0]
        all_count  = len(constrainedBones)
        mute_count = len(mutedBones)



        if mute_count==0:
            return 'Locked', 'Unlock'
        if mute_count == all_count:
            return 'Unlocked', 'Lock'
        return 'Partially locked', ''
    except:
        pass
    return '???', '???'

def BoneLocationLockStates(armobj):

    def is_locked(pbone):

        if pbone.bone.use_connect :

            return True

        if len( [c for c in pbone.constraints if c.type=='IK' and c.target==None and c.influence != 0] ) > 0:

            return True

        if len([c for c in pbone.constraints if c.type=='COPY_LOCATION']) > 0:

            return True


        locked = any([locked for locked in pbone.lock_location])
        return locked

    try:
        control_bones   = rig.get_pose_bones(armobj, armobj.RigProp.ConstraintSet, spine_check=True, deforming=False)

        lockedBones    = []
        unlockedBones  = []
        for b in control_bones.values():
            (lockedBones if is_locked(b) else unlockedBones).append(b)

        locked_count   = len(lockedBones)
        unlocked_count = len(unlockedBones)



        if unlocked_count   == 0:
            return 'Locked', 'Unlock'
        if locked_count == 0:
            return 'Unlocked', 'Lock'



        return 'Partially locked', ''
    except:
        raise#pass
    return '???', '???'

def BoneVolumeLockStates(armobj):
    try:
        controlBones = rig.get_pose_bones(armobj, armobj.RigProp.ConstraintSet, spine_check=True, deforming=False)
        pose_bones = armobj.pose.bones
        mutedBones = []
        unmutedBones = []
        for name in [n for n in SLVOLBONES if n in controlBones]:
            b = pose_bones.get(name)
            if not b:
                log.warning("Bone %s not in pose bones" % name)
                continue

            if b.lock_location[0] or b.lock_location[1] or b.lock_location[2]:
                unmutedBones.append(b)
            else:
                mutedBones.append(b)

        unmuted_count = len(unmutedBones)
        mute_count    = len(mutedBones)



        if mute_count   == 0:
            return 'Locked', 'Unlock'
        if unmuted_count == 0:
            return 'Unlocked', 'Lock'

        return 'Partially locked', ''
    except:
        raise#pass
    return '???', '???'






class PanelRigDisplay(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Rig Display"
    bl_idname      = "AVASTAR_PT_rig_display"
    bl_options     = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):

        try:
            if context.mode == 'OBJECT' or context.active_object is None:
                return True
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    return True
                elif 'avastar' in obj or 'Avastar' in obj:
                    return True
            return False
        except (TypeError, AttributeError):
            return False

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_RIG_DISPLAY, msg=panel_info_rigging)

    def draw(self, context):

        layout = self.layout
        scn = context.scene


        currentSelection = util.getCurrentSelection(context)
        avastars         = currentSelection['avastars']
        attached         = currentSelection['attached']
        detached         = currentSelection['detached']
        weighttargets    = currentSelection['weighttargets']
        targets          = currentSelection['targets']
        active           = currentSelection['active']

        if active:
            if active.type=="ARMATURE":
                armobj = active
            else:
                armobj = active.find_armature()
        else:
            armobj = None

        if len(targets)>0:




            if context.mode in ['OBJECT','PAINT_WEIGHT', 'PAINT_VERTEX', 'EDIT_MESH']:
                all_attached   = (len(targets) > 0 and len(attached) == len(targets))            
                if all_attached or (len(avastars)==1 and (len(attached) > 0 or len(detached) > 0)):

                    skinning_label = ""
                    custom_meshes =  util.getSelectedCustomMeshes(attached)
                    fitted  =0
                    basic   =0
                    noconfig=0
                    if len(custom_meshes) > 0:
                        for ob in custom_meshes:
                           if 'weightconfig' in ob:
                               if ob['weightconfig'] == "BASIC": basic += 1
                               else: fitted += 1
                           else:
                               noconfig +=1

                        if noconfig   == len(custom_meshes): skinning_label = " (Basic)"
                        elif basic  == len(custom_meshes): skinning_label = " (Basic)"
                        elif fitted   == len(custom_meshes): skinning_label = " (Fitted)"




        
        if armobj is not None and (context.mode in ['PAINT_WEIGHT','OBJECT', 'EDIT_MESH', 'POSE', 'EDIT_ARMATURE']):
            if util.is_avastar(armobj) > 0:
                mesh.displayShowBones(context, layout, active, armobj, with_bone_gui=True)






class PanelRiggingConfig(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Rig Config"
    bl_idname      = "AVASTAR_PT_rig_config"
    bl_options     = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):
        ui_level = util.get_ui_level()
        try:
            if ui_level == UI_SIMPLE:
                return False
            if context.mode == 'OBJECT' or context.active_object is None:
                return True
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    return True
                elif 'avastar' in obj or 'Avastar' in obj:
                    return True
            return False
        except (TypeError, AttributeError):
            return False

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_RIG_CONFIG, msg=panel_info_rigging)

    def draw(self, context):

        def draw_vector(id, vec):
            s = "%s: % .3f % .3f % .3f" % (id, vec[0], vec[1], vec[2])
            return s

        def has_spine(armobj):
            bones=armobj.data.bones
            return bones.get('mSpine1')\
            or bones.get('mSpine2')\
            or bones.get('mSpine3')\
            or bones.get('mSpine4')\

        def add_spine_settings(layout, armobj):
            box = layout.box()
            box.label(text="Spine settings", icon=ICON_MOD_ARMATURE)

            col = box.column()
            if not has_spine(armobj):
                col.alert=True
                col.label(text='no Spine in Rig', icon=ICON_BLANK1)
                return

            row = col.row(align=True)
            row.prop(armobj.RigProp, "spine_is_visible", toggle=True, text="", icon_value=visIcon(armobj, B_LAYER_SPINE, type='animation'))
            row.operator("avastar.reset_spine_bones")

            col = box.column(align=True)
            txt, alert = rig.get_upper_folding_state(armobj)
            col.alert = alert
            col.prop(armobj.RigProp, "spine_unfold_upper", text=txt, toggle=True)

            txt, alert = rig.get_lower_folding_state(armobj)
            col.alert = alert
            col.prop(armobj.RigProp, "spine_unfold_lower", text=txt, toggle=True)

        def add_eye_settings(layout, armobj):
            box = layout.box()
            box.label(text="Eye settings", icon=ICON_HIDE_OFF)
            col = box.column()
            col.prop(armobj.RigProp, "eye_setup")


        layout = self.layout
        scn = context.scene


        currentSelection = util.getCurrentSelection(context)
        avastars         = currentSelection['avastars']
        attached         = currentSelection['attached']
        detached         = currentSelection['detached']
        weighttargets    = currentSelection['weighttargets']
        targets          = currentSelection['targets']
        active           = currentSelection['active']

        if active:
            if active.type=="ARMATURE":
                armobj = active
            else:
                armobj = active.find_armature()
        else:
            armobj = None






        if len(targets)>0:




            if context.mode in ['OBJECT','PAINT_WEIGHT', 'PAINT_VERTEX', 'EDIT_MESH']:
                all_attached   = (len(targets) > 0 and len(attached) == len(targets))            
                if all_attached or (len(avastars)==1 and (len(attached) > 0 or len(detached) > 0)):

                    skinning_label = ""
                    custom_meshes =  util.getSelectedCustomMeshes(attached)
                    fitted  =0
                    basic   =0
                    noconfig=0
                    if len(custom_meshes) > 0:
                        for ob in custom_meshes:
                           if 'weightconfig' in ob:
                               if ob['weightconfig'] == "BASIC": basic += 1
                               else: fitted += 1
                           else:
                               noconfig +=1

                        if noconfig   == len(custom_meshes): skinning_label = " (Basic)"
                        elif basic  == len(custom_meshes): skinning_label = " (Basic)"
                        elif fitted   == len(custom_meshes): skinning_label = " (Fitted)"




        ui_level = util.get_ui_level()
                
        if armobj is not None and (context.mode in ['PAINT_WEIGHT','OBJECT', 'EDIT_MESH', 'POSE', 'EDIT_ARMATURE']):




            #






            if ui_level > UI_SIMPLE and context.mode in ['EDIT_MESH', 'PAINT_WEIGHT', 'POSE', 'EDIT_ARMATURE']:

                box = layout.box()
                box.label(text="Bone Deform Settings", icon=ICON_MOD_ARMATURE)
                col = box.column()

                deform_current, deform_set = mesh.SLBoneDeformStates(armobj)
                if deform_current   == 'Enabled' : icon = ICON_POSE_HLT
                elif deform_current == 'Disabled': icon = ICON_OUTLINER_DATA_ARMATURE
                else                             : icon = ICON_BLANK1

                row = col.split(factor=0.5, align=True )
                if deform_current=='':
                    row.label(text="", icon=icon)
                else:
                    row.label(text="Deform", icon=icon)
                    if deform_set != "Disable":
                        row.operator(mesh.ButtonDeformEnable.bl_idname, text="Enable Selected").set='SELECTED'
                    if deform_set != "Enable":
                        row.operator(mesh.ButtonDeformDisable.bl_idname, text="Disable Selected").set='SELECTED'

                col = box.column(align=True)
                row = col.row(align=False)
                row.operator(mesh.ButtonDeformEnable.bl_idname, text= " SL", icon_value=get_cust_icon("mbones"), emboss=False)
                row = row.row(align=True)
                row.operator(mesh.ButtonDeformEnable.bl_idname, text="Enable").set='BASIC'
                row.operator(mesh.ButtonDeformDisable.bl_idname, text="Disable").set='BASIC'

                col = box.column(align=True)
                row = col.row(align=False)
                row.operator(mesh.ButtonDeformEnable.bl_idname, text= " Ext", icon_value=get_cust_icon("ebones"), emboss=False)
                row = row.row(align=True)
                row.operator(mesh.ButtonDeformEnable.bl_idname, text="Enable").set='EXTENDED'
                row.operator(mesh.ButtonDeformDisable.bl_idname, text="Disable").set='EXTENDED'

                col = box.column(align=True)
                row = col.row(align=False)
                row.operator(mesh.ButtonDeformEnable.bl_idname, text= " Vol", icon=ICON_SNAP_ON, emboss=False)

                row = row.row(align=True)
                row.operator(mesh.ButtonDeformEnable.bl_idname, text="Enable").set='VOL'
                row.operator(mesh.ButtonDeformDisable.bl_idname, text="Disable").set='VOL'

        if ui_level > UI_STANDARD and armobj and context.mode != 'OBJECT' and len(avastars)==1:
            if active in avastars:
                col = box.column(align=True)
                lock_state, mute_set = rig.SLBoneStructureRestrictStates(active)

                if lock_state   == 'Disabled': icon = ICON_RESTRICT_SELECT_ON
                elif lock_state == 'Enabled' : icon = ICON_RESTRICT_SELECT_OFF
                else                         : icon = ICON_BLANK1
                row = col.split(factor=0.5, align=True )

                row.label(text="Structure", icon=icon)
                if mute_set != 'Disable':
                    row.operator(mesh.ButtonArmatureAllowStructureSelect.bl_idname, text="Enable")
                if mute_set != 'Enable':
                    row.operator(mesh.ButtonArmatureRestrictStructureSelect.bl_idname, text="Disable")

                col = box.column(align=True)
                col.prop(armobj.RigProp, "hip_compatibility")

                add_spine_settings(layout, armobj)

        if ui_level > UI_STANDARD and armobj and context.mode != 'OBJECT' and len(avastars)==1:
            if active in avastars:
                add_eye_settings(layout, armobj)
 
'''




class PanelAvastarRigConvert(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label = "Rig Converter"
    bl_idname = "AVASTAR_PT_rig_convert"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return True

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_RIG_CONVERTER, msg=panel_info_tools)

    def draw(self, context):

        layout = self.layout
        scn    = context.scene


        currentSelection = util.getCurrentSelection(context)
        active           = currentSelection['active']

        if active:
            if active.type=="ARMATURE":
                armobj = active
            else:
                armobj = active.find_armature()
        else:
            armobj = None

        view = context.space_data
        warn_if_camera_locked_to_layers(view, layout)


        if armobj and util.object_visible_get(armobj, context=context) and util.object_select_get(armobj):
            is_a_repair = not copyrig.armature_needs_update(armobj)
            col = layout.column(align=True)
            ctargets = [arm for arm in bpy.context.selected_objects if arm.type=='ARMATURE' and 'avastar' in arm and arm != armobj]
            copyrig.ButtonCopyAvastar.draw_generic(None, context, layout, armobj, ctargets, repair=is_a_repair )
'''




class PanelAvastarRigImport(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label = "Developer Kits"
    bl_idname = "AVASTAR_PT_devkit_manager"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return True

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_DEVKIT_MANAGER, msg=panel_info_devkit_manager)

    def draw(self, context):

        layout = self.layout
        scn    = context.scene


        currentSelection = util.getCurrentSelection(context)
        active           = currentSelection['active']

        if active:
            if active.type=="ARMATURE":
                armobj = active
            else:
                armobj = active.find_armature()
        else:
            armobj = None

        view = context.space_data
        warn_if_camera_locked_to_layers(view, layout)


        copyrig.create_devkit_exec(layout)





class PanelRigJointOffsets(bpy.types.Panel):
    bl_space_type  = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_category    = "Avastar"

    bl_label       = "Joint Positions"
    bl_idname      = "AVASTAR_PT_rig_joint_offsets"
    bl_context     = 'data'
    bl_options     = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):
        if not util.use_sliders(context):
            return False

        ui_level = util.get_ui_level()
        try:
            if ui_level == UI_SIMPLE:
                return False

            obj = context.active_object
            if context.active_object is None:
                return False

            if obj.type != 'ARMATURE':
                return False
            return 'avastar' in obj or 'Avastar' in obj

        except (TypeError, AttributeError):
            return False

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_JOINTS, msg=panel_info_rigging)

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        armobj = context.active_object
        joint_offset_list = armobj.data.JointOffsetList
        if len(joint_offset_list) > 0:
            row = layout.row()
            row.alignment='LEFT'
            row.prop(armobj.RigProp,"display_joint_heads")
            row.prop(armobj.RigProp,"display_joint_tails")
            row.label(text='Offsets, values in [mm]')
            col = layout.column()
            col.template_list('AVASTAR_UL_JointOffsetPropVarList',
                             'JointOffsetList',
                             armobj.data,
                             'JointOffsetList',
                             armobj.data.JointOffsetIndex,
                             'index',
                             rows=5)





class PanelAvatarMaterials(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Avatar Materials"
    bl_idname      = "AVASTAR_PT_avatar_materials"

    bl_options      = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_MATERIALS, msg=panel_info_materials)

    def draw(self, context):
        arm, objects = mesh.BakeMaterialsOperator.get_animated_objects(context)
        avastar_object_count = len([o for o in objects if 'avastar-mesh' in o])
        layout = self.layout
        col = layout.column(align=True)
        material_selectable = bpy.context.space_data.shading.type in ['MATERIAL', 'RENDERED']
        if not material_selectable:
            col.alert=True
            col.operator("avastar.shader_info_operator", text="Unsupported in %s Shading" % bpy.context.space_data.shading.type, emboss=False)
            col = layout.column(align=True)
        if avastar_object_count:
            col.prop(context.object.avastarMaterialProp, "material_type", expand=True)
            col.prop(context.object.avastarMaterialProp, "unique")
            col.enabled = material_selectable
        else:
            col.operator("avastar.material_info_operator", text="Custom Material Baker", emboss=False)
            col = layout.column()


        if objects:
            sceneProps = context.scene.SceneProp
            box = layout.box()
            col = box.column()
            row=col.row(align=True)
            row.label(text="Material Baker")
            row.prop(sceneProps,"list_baked_objects")

            col = box.column()
            baked_count = 0
            missing_count = 0

            materials_object_map = {}
            for obj in objects:
                mesh.BakeMaterialsOperator.insert_material_object_relation(obj, materials_object_map)

            for material, objects in materials_object_map.items():
                if not material.node_tree:
                    continue
                image_name, index, node = mesh.BakeMaterialsOperator.material_baked_image_name_and_index(material)
                need_bake = index < 0

                explain = "Explain: Avastar expects a baked texture to be an texture node within a node based material\n"\
                        + "This texture node contains a baked version of the material, ready for export as image texture\n"\
                        + "The texture name must be <material_name>_tex\n\n"\
                        + "If material assigned to a selected object does not have a baked texture:\n"\
                        + "Fix: Mark this Material for texture baking (checkbox on the left side of this icon)\n"\
                        + "Click [Bake] to generate the baked <material_name>_tex node in the Shader Editor\n"\
                        + "Click [Cleanup] to remove baked textures from the Shader node tree\n"\

                if need_bake:
                    missing_count +=1
                    icon = ICON_RADIOBUT_OFF
                    width = height = ''
                    msg = "At least one of the Object's assigned Materials does not contain a baked texture.\n\n"\
                        + explain
                    opid = "avastar.baketool2_info_operator"
                else:
                    baked_count += 1
                    icon = ICON_CHECKMARK
                    msg = "All of the Object's assigned Materials contain a baked texture.\n\n"\
                        + explain
                    opid = "avastar.baketool_info_operator"
                    size=node.image.size
                    w = size[0]
                    h = size[1]
                    width = "w:%4d " % w
                    height= "h:%4d" % h

                row=col.row(align=True)
                row.prop(material.BakerProp,"rebake", text=material.name)
                op = row.operator(opid, text=width+height, icon=icon, emboss=False)
                op.msg  = msg
                op.icon = SEVERITY_INFO

                if sceneProps.list_baked_objects:
                    for obj in objects:
                        row=col.row(align=True)
                        row.label(text='', icon=ICON_BLANK1)
                        row.label(text=obj.name)

            if baked_count > 0 or missing_count > 0:
                col = box.column()
                col.prop(sceneProps,"baked_image_width")
                col.prop(sceneProps,"baked_image_height")

                col = box.column()
                col.operator_context = 'INVOKE_DEFAULT'
                bake_text = "%s" %( "Bake" if baked_count == 0 else "Rebake" if missing_count == 0 else "(Re) bake")
                clean_text = "Cleanup"
                row=col.row(align=True)
                row.operator("avastar.material_bake", text=bake_text)
                row.operator("avastar.material_bake_cleanup", text=clean_text)

    @classmethod
    def poll(self, context):
        '''
        This panel will only appear if the context object either:
        - is an armature and has related meshes
        - is a MESH object
        '''
        arm, currentmeshes = mesh.BakeMaterialsOperator.get_animated_objects(context)
        return len(currentmeshes)>0





class PanelSkinning(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Skinning"
    bl_idname      = "AVASTAR_PT_skinning"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):

        try:
            if context.active_object is None:
                return False
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    return True
                elif 'avastar' in obj or 'Avastar' in obj:
                    return True
            return False
        except (TypeError, AttributeError):
            return False
            
    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_SKINNING, msg=panel_info_skinning)

    def check_bindable(self, detached):
        state = 0
        for ob in detached:
            if any(s != 1 for s in ob.scale):
                state |= OB_SCALED
                if any(s<0 for s in ob.scale):
                    state |= OB_NEGSCALED
            if any(s!=0 for s in ob.rotation_euler):
                state |= OB_ROTATED
            if any(s!=0 for s in ob.rotation_euler):
                state |= OB_ROTATED
            if any(s!=0 for s in ob.location):
                state |= OB_TRANSLATED
        return state

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        sceneProps = scn.SceneProp


        currentSelection = util.getCurrentSelection(context)
        avastars         = currentSelection['avastars']
        armatures        = currentSelection['armatures']
        attached         = currentSelection['attached']
        detached         = currentSelection['detached']
        weighttargets    = currentSelection['weighttargets']
        targets          = currentSelection['targets']
        active           = currentSelection['active']
        armobj           = avastars[0] if len(avastars) > 0 else None

        if context.mode in ['OBJECT','PAINT_WEIGHT', 'PAINT_VERTEX', 'EDIT_MESH', 'POSE']:
            all_attached   = (len(targets) > 0 and len(attached) == len(targets))
            if all_attached or (len(avastars)==1 and (len(attached) > 0 or len(detached) > 0)):

                skinning_label = ""
                custom_meshes =  util.getSelectedCustomMeshes(attached)
                fitted  =0
                basic   =0
                noconfig=0
                if len(custom_meshes) > 0:
                    for ob in custom_meshes:
                       if 'weightconfig' in ob:
                           if ob['weightconfig'] == "BASIC": basic += 1
                           else: fitted += 1
                       else:
                           noconfig +=1

                    if noconfig   == len(custom_meshes): skinning_label = " (Basic)"
                    elif basic  == len(custom_meshes): skinning_label = " (Basic)"
                    elif fitted   == len(custom_meshes): skinning_label = " (Fitted)"

                binding_box = None
                skinning_box = None
                appearance_box = None

                if len(detached) > 0:
                    skinning_box = layout.box()
                    col = skinning_box.column(align=True)
                    if len(detached) == 1:
                        label = "%s"%(mesh.ButtonParentArmature.bl_label)
                    else:
                        label = "%s (%d)"%(mesh.ButtonParentArmature.bl_label, len(detached))

                    bind_state = self.check_bindable(detached)
                    accept_bind = True
                    if bind_state > 1:
                        if not binding_box:
                            binding_box = skinning_box.box()
                        col = binding_box.column(align=True)
                        if bind_state & OB_NEGSCALED:
                            row = col.row(align=True)
                            row.alert=True
                            op = row.operator("avastar.generic_info_operator", text="Negative scales", icon=ICON_ERROR, emboss=False)
                            op.msg = messages.panel_info_negative_scales
                            accept_bind = False
                            op = row.operator("object.transform_apply", text="", icon=ICON_RECOVER_AUTO, emboss=False)
                            op.location=False
                            op.rotation=False
                            op.scale=True

                        elif bind_state & OB_SCALED:
                            row = col.row(align=True)
                            row.alert=True
                            op = row.operator("avastar.generic_info_operator", text="Scaled Items", icon=ICON_INFO, emboss=False)
                            op.msg=messages.panel_info_scales
                            op = row.operator("object.transform_apply", text="", icon=ICON_RECOVER_AUTO, emboss=False)
                            op.location=False
                            op.rotation=False
                            op.scale=True

                        if bind_state & OB_ROTATED:
                            row = col.row(align=True)
                            row.alert=True
                            op = row.operator("avastar.generic_info_operator", text="Rotated Items", icon=ICON_INFO, emboss=False)
                            op.msg=messages.panel_info_rotations
                            op = row.operator("object.transform_apply", text="", icon=ICON_RECOVER_AUTO, emboss=False)
                            op.location=False
                            op.rotation=True
                            op.scale=False

                        col = skinning_box.column()

                    if not accept_bind:
                        col.enabled=False
                        col.alert=True

                    if armobj:
                        can_run = weights.ButtonGenerateWeights.weightmap_bind_panel_draw(armobj, context, col, is_redo=False)
                        col = skinning_box.column()
                    else:
                        can_run = True

                    if can_run and accept_bind:
                        text=label
                        enabled=True
                        alert=False
                    else:
                        text = "No weight source selected" if accept_bind else "check scale & rotation"
                        enabled=False
                        alert=True

                    col.alert=alert
                    col.operator(mesh.ButtonParentArmature.bl_idname, text=text)
                    col.enabled=enabled



                if len(attached) > 0:

                    meshes = util.getMeshes(attached, context, visible=True, hidden=False)
                    if len(meshes) > 0:
                        meshProps = bpy.context.scene.MeshProp
                        global nwc_effective

                        if not skinning_box:
                            skinning_box = layout.box()
                            skinning_box.label(text="Bind", icon=ICON_MODIFIER)

                        if len(meshes) == 1:
                            label = "Unbind"
                        else:
                            label = "Unbind (%d)"% len(meshes)

                        to_fix = check_repair_mesh(context, armobj, meshes, skinning_box)
                        bone_count = rig.get_max_bone_count(scn, meshes)
                        if (bone_count > 110):
                            add_cleanup_vgroup_button(active, bone_count, meshProps, skinning_box)

                        row = skinning_box.row(align=True)
                        if not util.getAddonPreferences().enable_auto_mesh_update:
                            row.alert = len(to_fix) > 0
                            prop=row.operator("avastar.rebind_armature", text='Update Binding', icon=ICON_FILE_REFRESH)
                            prop.apply_as_bindshape=sceneProps.apply_as_bindshape
                            row.alert=False
                            row.prop(meshProps,"auto_rebind_mesh", text='', icon=ICON_AUTO)
                            row = skinning_box.row(align=True)
                            row.prop(sceneProps,"apply_as_bindshape", text='Apply Bindshape')
                            skinning_box.separator()

                        unbind_box = layout.box()

                        col = unbind_box.column(align=True)
                        prop = col.operator(mesh.ButtonUnParentArmature.bl_idname, text=label)
                        prop.apply_armature_on_unbind = active.ObjectProp.apply_armature_on_unbind
                        prop.purge_data_on_unbind = active.ObjectProp.purge_data_on_unbind
                        prop.break_parenting_on_unbind = active.ObjectProp.break_parenting_on_unbind
                        col.prop(active.ObjectProp, "apply_armature_on_unbind")
                        col.prop(active.ObjectProp, "purge_data_on_unbind")
                        col.prop(active.ObjectProp, "break_parenting_on_unbind")

                if len(targets)>0:
                    if context.mode in ['OBJECT','PAINT_WEIGHT', 'PAINT_VERTEX', 'EDIT_MESH']:








                        has_shapekeys = util.selection_has_shapekeys(targets)
                        if  has_shapekeys or len(armatures) > 0 or len(avastars) == 1:

                            box = layout.box()
                            box.label(text="Freeze", icon=ICON_MODIFIER)
                            meshProps = bpy.context.scene.MeshProp
                            col = box.column(align=True)
                            split = col.split(factor=0.4)
                            split.label(text="Original:")
                            split.prop(meshProps, "handleOriginalMeshSelection", text="", toggle=False)

                            col = box.column(align=True)
                            standalone_posed_text = "As static mesh%s" % ("" if scn.MeshProp.standalonePosed else " ...")
                            join_parts_text = "Join Parts%s" % ("" if scn.MeshProp.joinParts else " ...")
                            col.prop(scn.MeshProp, "standalonePosed", text=standalone_posed_text, toggle=False)
                            col = col.column(align=True)
                            if scn.MeshProp.standalonePosed:
                                col.prop(scn.MeshProp, "removeWeights", toggle=False)
                                col.prop(scn.MeshProp, "removeArmature", toggle=False)
                                col.enabled=scn.MeshProp.standalonePosed

                            if len(targets) > 1:
                                col = box.column(align=True)
                                col.prop(scn.MeshProp, "joinParts", text=join_parts_text, toggle=False)
                                if scn.MeshProp.joinParts:
                                    col = col.column(align=True)
                                    col.prop(scn.MeshProp, "removeDoubles", toggle=False)
                                    col.enabled=scn.MeshProp.joinParts

                            col = box.column(align=True)
                            col.prop(context.object.ObjectProp,"frozen_name")
                            col.separator()
                            op = col.operator("avastar.freeze_shape", icon=ICON_FREEZE)
                            layout.separator()

            elif len(avastars) == 1:

                if util.use_sliders(context) and not 'bindpose' in avastars[0]:
                    children = util.getCustomChildren(avastars[0], type='MESH')
                    if children:
                        meshes = util.getMeshes(children, context, visible=True, hidden=False)
                        attach_count = len ( meshes )

                        if attach_count > 0:
                            appearance_box = layout.box()
                            appearance_box.label(text="Avatar Shape Control", icon=ICON_UI)

                            col = appearance_box.column(align=True)

                            if attach_count == 1:
                                label = "%s" % mesh.ButtonUnParentArmature.bl_label
                            else:
                                label = "%s (%d)"%(mesh.ButtonUnParentArmature.bl_label, attach_count)

                            prop = col.operator(mesh.ButtonUnParentArmature.bl_idname, text=label)
                            prop.apply_armature_on_unbind = active.ObjectProp.apply_armature_on_unbind
                            prop.purge_data_on_unbind = active.ObjectProp.purge_data_on_unbind
                            prop.break_parenting_on_unbind = active.ObjectProp.break_parenting_on_unbind
                            col.prop(active.ObjectProp, "apply_armature_on_unbind")
                            col.prop(active.ObjectProp, "purge_data_on_unbind")
                            col.prop(active.ObjectProp, "break_parenting_on_unbind")

            elif context.object.type=='MESH' and mesh.hasAvastarData(context.object):
                appearance_box = layout.box()
                appearance_box.label(text="Avatar Shape Control", icon=ICON_UI)
                row = appearance_box.row(align=True)
                prop = row.operator(mesh.CleanupCustomProps.bl_idname)

class PanelWeightCopy(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Weight Copy"
    bl_idname      = "AVASTAR_PT_weight_copy"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        if context.active_object is None:
            return False
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                return True
        return False

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_WEIGHT_COPY, msg=panel_info_weight_copy)

    def draw(self, context):

        layout = self.layout
        armobj = util.get_armature(context.object)
        if armobj:
            box=layout.column()
            weights.ButtonGenerateWeights.weightmap_copy_panel_draw(armobj, context, box)

def check_repair_mesh(context, armobj, meshes, layout):
    if context.mode == 'EDIT_MESH' or not util.use_sliders(context):
        to_fix = []
    else:
        to_fix = rig.need_rebinding(armobj, meshes)
    return to_fix
    
def add_repair_mesh_button(to_fix, layout):
        col= layout.column(align=True)
        row = col.row(align=True)
        text = "Rebind all Meshes"
        row.label(text=text)
        row.operator("avastar.rebind_armature", text='', icon=ICON_RECOVER_AUTO, emboss=False)

def add_cleanup_vgroup_button(active, bone_count, meshProps, layout):
    col= layout.column(align=True)
    col.alert=True
    row = col.row(align=True)
    
    if meshProps.all_selected:
        text = "MultiClean Weightmaps"
    else:
        text = "Clean %d Weightmaps" % bone_count
    
    op = row.operator("avastar.clear_bone_weight_groups", 
         icon=ICON_RECOVER_AUTO,
         text=text
         )
    if active.mode == 'OBJECT':
        row.prop(meshProps,"all_selected", text='', icon=ICON_GROUP_BONE)
        op.all_selected = meshProps.all_selected

    return





class PanelPosing(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Posing"
    bl_idname      = "AVASTAR_PT_panel_posing"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):

        ui_level = util.get_ui_level()
        if ui_level== UI_SIMPLE:
            return False

        try:
            armobj = util.get_armature(context.object)
            return armobj!=None and context.mode in ['OBJECT','PAINT_WEIGHT', 'PAINT_VERTEX', 'EDIT_MESH', 'POSE', 'EDIT_ARMATURE']

        except (TypeError, AttributeError):
            return False

    @staticmethod
    def add_pose_bone_constraints_section(layout, armobj):
        box = layout.box()


        col = box.column(align=True)
        row=col.row()

        row.label(text="Bone Constraints", icon=ICON_MOD_ARMATURE)
        row.prop(armobj.RigProp,"ConstraintSet", text="")
        
        col = box.column(align=True)
        lock_state, mute_set = BoneRotationLockStates(armobj, COPY_ROTATION)
        if lock_state   == 'Locked'  : icon_value = get_cust_icon('mlock')
        elif lock_state == 'Unlocked': icon_value = get_cust_icon('munlock')
        else                         : icon_value = get_sys_icon('BLANK1')

        row = col.split(factor=0.5, align=True )
        row.alignment='LEFT'
        row.label(text='SL Bone Rot', icon_value=icon_value)
        if mute_set != "Lock":
            row.operator(mesh.ButtonArmatureUnlockRotation.bl_idname, text="Unlock")
        if mute_set != "Unlock":
            row.operator(mesh.ButtonArmatureLockRotation.bl_idname, text="Lock")

        col = box.column(align=True)
        lock_state, mute_set = BoneLocationLockStates(armobj)
        if lock_state   == 'Locked'  : icon_value = get_cust_icon('alock')
        elif lock_state == 'Unlocked': icon_value = get_cust_icon('aunlock')
        else                         : icon_value = get_sys_icon('BLANK1')

        row = col.split(factor=0.5, align=True )
        row.alignment='LEFT'
        row.label(text='Anim Bone Trans', icon_value=icon_value)
        if mute_set != "Lock":
            row.operator(mesh.ButtonArmatureUnlockLocation.bl_idname, text="Unlock")
        if mute_set != "Unlock":
            row.operator(mesh.ButtonArmatureLockLocation.bl_idname, text="Lock")
        
        col = box.column(align=True)
        lock_state, mute_set = BoneVolumeLockStates(armobj)
        if lock_state   == 'Locked'  : icon = ICON_LOCKED
        elif lock_state == 'Unlocked': icon = ICON_UNLOCKED
        else                         : icon = ICON_BLANK1

        row = col.split(factor=0.5, align=True )
        row.alignment='LEFT'
        row.label(text='Vol Bone Trans', icon=icon)
        if mute_set != "Lock":
            row.operator(mesh.ButtonArmatureUnlockVolume.bl_idname, text="Unlock")
        if mute_set != "Unlock":
            row.operator(mesh.ButtonArmatureLockVolume.bl_idname, text="Lock")


    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_POSING, msg=panel_info_posing)

    def draw(self, context):

        layout = self.layout
        scn    = context.scene
        active = context.object
        armobj = util.get_armature(active)

        rigtype         = armobj.RigProp.RigType
        joints          = util.get_joint_cache(armobj)
        is_in_edit_mode = context.mode in ['EDIT_ARMATURE']
        has_joints      = joints and len(joints) > 0
        ui_level        = util.get_ui_level()

        if has_joints:
            mod="edited"
            msg=panel_info_edited_joints
        else:
            mod = "unchanged"
            msg=panel_info_clean_joints
        rts = rigtype[0].upper() + rigtype[1:].lower()
        label ="%s (%s)" % (rts,mod)
        row = layout.row(align=True)
        util.draw_info_header(row, AVASTAR_TOOLS, msg=msg)
        row.label(text=label)

        if ui_level > UI_SIMPLE:
            row = layout.row(align=True)
            row.prop(armobj.data,"pose_position", expand=True)









        if ui_level > UI_ADVANCED:
            layout.separator()
            sceneProps  = scn.SceneProp
            last_select = bpy.types.AVASTAR_MT_armature_presets_menu.bl_label
            row = layout.row(align=True)
            row.prop(sceneProps, "armature_preset_apply_as_Restpose", text='', icon=ICON_FREEZE)
            row.prop(sceneProps, "armature_preset_apply_all_bones",   text='', icon=ICON_GROUP_BONE)
            if not sceneProps.armature_preset_apply_as_Restpose:
                row.prop(sceneProps, "armature_preset_adjust_tails",   text='', icon=ICON_LINKED)
            row.menu("AVASTAR_MT_armature_presets_menu", text=last_select )
            row.operator("avastar.armature_presets_add", text="", icon=ICON_ADD)
            if last_select not in ["Armature Presets", "Presets"]:
                row.operator("avastar.armature_presets_update", text="", icon=ICON_FILE_REFRESH)
                row.operator("avastar.armature_presets_remove", text="", icon=ICON_REMOVE).remove_active = True

        if util.use_sliders(context) and (ui_level >= UI_ADVANCED or has_joints):
            layout.separator()
            col = layout.column(align=True)
            col.prop(armobj.RigProp,"rig_use_bind_pose")

        if ui_level > UI_STANDARD and armobj and context.mode != 'OBJECT' and 'avastar' in armobj:
            PanelPosing.add_pose_bone_constraints_section(layout, armobj)




        if active and active.type in ['ARMATURE','MESH']:

            meshProps = scn.MeshProp
            sceneProps = scn.SceneProp
            box = layout.box()
            msg = "Rig Modify Tools"
            box.label(text=msg, icon=ICON_GROUP_BONE)

            col = box.column(align=True)

            if context.mode not in ['EDIT_ARMATURE', 'POSE']:
                col.label(text="Only available for Armatures")
                col.label(text="in POSE mode or Edit mode")
            else:

                if ui_level >= UI_ADVANCED :
                    row = col.row(align=True)

                    if context.mode == 'POSE':

                        def create_restpose_button(row, sceneProps, rigProps):
                            prop = row.operator("avastar.apply_as_restpose", text="As Bindpose")
                            prop.store_as_bind_pose=True

                            prop = row.operator("avastar.apply_as_restpose", text="With Joints")
                            prop.store_as_bind_pose=False

                            row.prop(rigProps,"generate_joint_tails", text='', icon=ICON_FORCE_CURVE)
                            row.prop(rigProps,"generate_joint_ik", text='', icon=ICON_CONSTRAINT_BONE)

                        create_restpose_button(row, sceneProps, armobj.RigProp)

                        col.operator("avastar.armature_reset_pose_lsl", text='Generate LSL')
                        row = col.row(align=True)
                        row.operator("avastar.armature_reset_pose", text='Export Restpose')
                        row.prop(armobj.AnimProp,"used_restpose_bones", text='')

                        col = box.column()
                        col.prop(armobj.ObjectProp,"apply_armature_on_snap_rig")
                        if armobj.ObjectProp.apply_armature_on_snap_rig:
                            icol = col.box().column()
                            icol.prop(armobj.ObjectProp,"apply_only_to_visible")
                            icol.prop(armobj.ObjectProp,"apply_to_avastar_meshes")

                        col = box.column()
                        col.prop(meshProps, "adjustPoleAngle")
                        box.separator()
                        col = box.column(align=True)

                    elif context.mode == 'EDIT_ARMATURE' and ui_level >= UI_EXPERIMENTAL:
                        label = "Snap Rig to Base" if scn.UpdateRigProp.base_to_rig else "Snap Base to Rig"
                        prop = row.operator(mesh.ButtonArmatureBoneSnapper.bl_idname, text=label, icon=ICON_SNAP_ON)


                        row.prop(scn.UpdateRigProp, "base_to_rig", text='', icon=ICON_ARROW_LEFTRIGHT)
                        prop.base_to_rig = scn.UpdateRigProp.base_to_rig
                        box.separator()
                        col = box.column(align=True)

                    if is_in_edit_mode and \
                        copyrig.ButtonCopyAvastar.sliders_allowed(context) and \
                        (has_joints or DIRTY_RIG in armobj or ui_level >= UI_ADVANCED):
                        col.label(text="Joint Positions", icon=ICON_MOD_ARMATURE)

                        if DIRTY_RIG in armobj or ui_level >= UI_ADVANCED:

                            def create_jointpos_store_button(col, sceneProps):
                                row=col.row(align=True)
                                op = row.operator("avastar.armature_jointpos_store",  text="As Bindpose")
                                op.sync = False
                                op.snap_control_to_rig = sceneProps.snap_control_to_rig
                                op.store_as_bind_pose = True

                                op = row.operator("avastar.armature_jointpos_store",  text="With Joints")
                                op.sync = False
                                op.snap_control_to_rig = sceneProps.snap_control_to_rig
                                op.store_as_bind_pose = False

                                row.prop(sceneProps, "snap_control_to_rig", text='', icon=ICON_ARROW_LEFTRIGHT)

                            create_jointpos_store_button(col, sceneProps)

                        if has_joints:
                            bones = util.get_modify_bones(armobj)
                            row = col.row(align=True)
                            prop = row.operator("avastar.armature_jointpos_remove", icon=ICON_X)
                            row.prop(armobj.RigProp,"keep_edit_joints", text='', icon=ICON_FREEZE)







class PanelFitting(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Fitting"
    bl_idname      = "AVASTAR_PT_panel_fitting"
    bl_options     = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):
        obj = context.object
        return obj and obj.type=='MESH' and not "avastar" in obj

    def draw(self, context):
        weights.ButtonGenerateWeights.draw_fitting_section(context, self.layout)

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_FITTING, msg=panel_info_fitting)





class PanelAvatarShape(bpy.types.Panel):
    '''
    Control the avatar shape using SL drivers
    '''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_category    = "Skinning"

    bl_label = "Avatar Shape"
    bl_idname = "AVASTAR_PT_avatar_shape"
    bl_context = 'object'
    bl_options     = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):
        '''
        This panel will only appear if the object has a
        Custom Property called "avastar" (value doesn't matter)
        '''
        p = util.getAddonPreferences()
        if p.show_panel_shape_editor == 'N-PANEL':
            return False

        obj = context.active_object
        return obj and obj.type=='ARMATURE' and "avastar" in obj and (not 'bindpose' in obj)

            
    def draw_header(self, context):
        row = self.layout.row()
        arm = context.active_object
        if DIRTY_RIG in arm:
            row.alert = DIRTY_RIG in arm
            icon = ICON_ERROR
            msg = panel_warning_appearance
        else:
            icon = ICON_NONE
            msg = panel_info_appearance
        util.draw_info_header(row, AVASTAR_APPEARANCE, msg=msg, icon=icon)

    def draw(self, context):
        PanelShaping.draw_generic(self, context, context.active_object, self.layout)


class ButtonCheckMesh(bpy.types.Operator):
    bl_idname = "avastar.check_mesh"
    bl_label = "Report"
    bl_description = "Report statistics and potential problems with selected items to Console"

    def execute(self, context):

        try:
            original_mode = context.active_object.mode
            util.mode_set(mode='OBJECT')
    
            targets = []
            for obj in context.selected_objects:
                if obj.type=='MESH':
                    targets.append(obj)
    
            report = analyseMeshes(context, targets)

            logging.warning(report)
            self.report({'INFO'},"%d Object report(s) on Console"%len(targets))

            util.mode_set(mode=original_mode)
            return{'FINISHED'}    
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}    


def analyseMeshes(context, targets):
    
    scn = context.scene    
    
    report = ["--------------------Mesh Check----------------------------"]
    report.append('Number of meshes to examine: %d'%len(targets))
    report.append('')
    
    for obj in targets:
        report.append("MESH: '%s'"%obj.name)

        me = obj.to_mesh(preserve_all_data_layers=True) 
        nfaces = len(obj.data.polygons)
        nfacesm = len(me.polygons)
        uvs = me.uv_layers
        
        #

        #
        report.append("\tNumber of vertices: %d, with modifiers applied: %d"%(len(obj.data.vertices),len(me.vertices))) 
        report.append("\tNumber of faces: %d, with modifiers applied: %d"%(nfaces, nfacesm)) 
        
        #

        #
        armature = util.getArmature(obj)
        if armature is not None:
            report.append("\tControlling armature: %s"%armature.name)
        else:
            report.append("\tFound no controlling armature so mesh will be static")
        
        #

        #
        groups = [group.name for group in obj.vertex_groups]
        unknowns=[]
        nondeform = []
        deform = []
        rig_sections = [B_EXTENDED_LAYER_ALL]
        excludes = []
        deform_bones = data.get_deform_bones(armature, rig_sections, excludes)
        for group in groups:
            if group not in deform_bones:
                if group not in unknowns:
                    unknowns.append(group)
            if armature is not None:
                if group in armature.data.bones:
                    if armature.data.bones[group].use_deform:
                        deform.append(group)
                    else:
                        nondeform.append(group)
        
        if len(groups) > 0:
            report.append("\tFound %d Vertex groups: {%s}" % (len(groups), ",".join(groups)))

        if len(unknowns) > 0:
            report.append("\tWARNING: unrecognized vertex groups (removed on export): {%s}"%",".join(unknowns))
            
        if armature is not None:
            if len(deform) > 0:
                report.append("\tDeforming bone weight groups: {%s}"%",".join(deform))
            else:
                report.append("\tPROBLEM: armature modifier but no deforming weight groups present")
                
            if len(nondeform) > 0:
                report.append("\tWARNING: Non-deforming bone weight groups (removed on export): {%s}"%",".join(nondeform))
                
        
        #

        #

        v_report = mesh.findWeightProblemVertices(context, obj, use_sl_list=False, find_selected_armature=True)
        
        if 'no_armature' in v_report['status']:
            report.append("\tObject %s is not rigged (weight map check omitted)"%obj.name)
        else:
            if 'unweighted' in v_report['status']:
                unweighted = v_report['unweighted']
                report.append("\tPROBLEM: Found %d vertices that have zero weight"%len(unweighted))
            if 'too_many' in v_report['status']:
                problems = v_report['too_many']
                report.append("\tWARNING: there are %d vertices with more that 4 vertex groups defined"%len(problems))            
            
        #

        #
        if len(uvs)>0:
            report.append("\tUV map present")
        else:
            report.append("\tWARNING: no UV map present")
            
        report.append('')
        
    return "\n".join(report)





class PanelAvastarTool(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label = "Tool Box"
    bl_idname = "AVASTAR_PT_tools"
    bl_options     = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):
        return True

    def initialize(self, context):
        self.scn    = context.scene
        self.meshProps    = self.scn.MeshProp
        self.skeletonProp = self.scn.SkeletonProp
        self.currentSelection = util.getCurrentSelection(context)
        self.avastars         = self.currentSelection['avastars']
        self.armatures        = self.currentSelection['armatures']
        self.attached         = self.currentSelection['attached']
        self.detached         = self.currentSelection['detached']
        self.weighttargets    = self.currentSelection['weighttargets']
        self.targets          = self.currentSelection['targets']
        self.active           = self.currentSelection['active']
        if self.active:
            if self.active.type=="ARMATURE":
                self.armobj = self.active
            else:
                self.armobj = self.active.find_armature()
        else:
            self.armobj = None

        self.meshes = util.get_animated_meshes(context, self.armobj) if self.armobj else []
        self.sourceCount = len(self.meshes)


    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_TOOLS, msg=panel_info_tools)


    def draw_operator(self, col, operator_blid, text=None, icon_left=None, icon_right=None):
        row = col.row(align=True)
        if icon_left==None:
            if text==None:
                op = row.operator(operator_blid)
            else:
                op = row.operator(operator_blid, text=text)
        else:
            if text==None:
                op = row.operator(operator_blid, icon=icon_left)
            else:
                op = row.operator(operator_blid, text=text, icon=icon_left)

        icon_value = get_icon(icon_right) if icon_right != None else None
        if icon_value != None:
            row.operator(operator_blid, text="", icon_value=icon_value)
        return op, row




    def draw_uv_tools(self, context):
        layout = self.layout
        col = None
        if len(self.targets)>0:

            col = layout.column(align=True)
            col.label(text="UV Tools", icon=ICON_GROUP_UVS)

            self.draw_operator(col, "avastar.rebake_uv", icon_right=ICON_BLANK1)
        return col



    #





    def draw_vertex_tools(self, context):

        layout = self.layout
        col = None
        if len(self.targets)>0:

            col = layout.column(align=True)
            col.label(text="Vertex Tools", icon=ICON_GROUP_VERTEX)
            col = layout.column(align=True)

            op, row = self.draw_operator(col, "avastar.find_doubles")
            row.operator("mesh.remove_doubles", text='', icon=ICON_TOOL_SETTINGS)

            op, row = self.draw_operator(col, "avastar.find_asymmetries"    )
            op = row.operator("mesh.symmetry_snap", icon=ICON_FILE_REFRESH, text='')
            op.direction='POSITIVE_X'
            op.use_center=True

            op, row = self.draw_operator(col, "avastar.snap_to_mesh", icon_right=ICON_BLANK1)

        return col



    #



    def draw_weight_tools(self, context):
        layout = self.layout
        col = layout.column(align=True)

        col.label(text="Weight Tools", icon=ICON_BRUSH_DATA)
        col = layout.column(align=True)     

        self.draw_weightmap_operators(context, col)
        self.draw_copy_operators(context, col)
        return col













    def draw_mesh_tools(self, context, col):

        op, row = self.draw_operator(col, "avastar.clear_bone_weight_groups", text="Clean Weightmaps", icon_right=ICON_BLANK1)
        if self.active.mode == 'OBJECT':
            row.prop(self.meshProps,"all_selected", text='', icon=ICON_GROUP_BONE)
            op.all_selected = self.meshProps.all_selected

        op, row = self.draw_operator(col, "avastar.find_toomanyweights")
        row.operator('avastar.fix_toomanyweights', text='', icon_value=get_icon('limit'))

        if len(self.armatures) > 0 or len(self.avastars) == 1:
            self.draw_operator(col, "avastar.find_unweighted", icon_right=ICON_BLANK1)
            self.draw_operator(col, "avastar.find_zeroweights", icon_right=ICON_BLANK1)

        self.draw_operator(col, "sparkles.show_weights_per_vert", text="Weight Count on Mesh", icon_right=ICON_BLANK1)









        return col



    #



    def draw_armature_tools(self, context):
        layout = self.layout
        col = layout.column(align=True)

        msg = "Armature Tools"
        col.label(text=msg, icon=ICON_GROUP_BONE)

        self.draw_operator(col, "avastar.manage_all_shapes",  text="Delete System Meshes", icon_right=ICON_BLANK1)
        self.draw_operator(col, "sparkles.copy_timeline",  text="Generate Walkcycle", icon_right=ICON_BLANK1)
        return col








    def draw_weightmap_operators(self, context, col):
        if self.armobj is not None and (context.mode in ['PAINT_VERTEX', 'PAINT_WEIGHT','OBJECT', 'POSE', 'EDIT_ARMATURE', 'EDIT_MESH']):

            if context.mode in ['PAINT_WEIGHT','EDIT_MESH']:

                if context.mode == 'PAINT_WEIGHT':

                    split=col.split(factor=0.7, align=True)
                    prop = split.operator(weights.ButtonMirrorBoneWeights.bl_idname, icon=ICON_MOD_MIRROR, text="Mirror opposite Bones")
                    prop.weightCopyAlgorithm = self.meshProps.weightCopyAlgorithm
                    split.prop(self.meshProps, "weightCopyAlgorithm", text="")

                    op, row = self.draw_operator(col, weights.ButtonSwapWeights.bl_idname, text="Swap Collision with Deform", icon_right=ICON_BLANK1)
                    op, row = self.draw_operator(col, weights.ButtonCopyBoneWeights.bl_idname, text="Selected to Active Bone", icon_right=ICON_BLANK1)
                    op.weightCopyType="BONES"

                if self.active and self.active.type == 'MESH':
                    self.draw_operator(col, "avastar.weld_weights_from_rigged", icon_right=ICON_BLANK1, text="Weld to rigged")
                    if util.get_ui_level() > UI_ADVANCED:
                        self.draw_operator(col, "avastar.shape_debug", icon_right=ICON_BLANK1)

                self.draw_operator(col, "avastar.ensure_mirrored_groups", text="Add missing Mirror Groups", icon_right=ICON_BLANK1)


        return col

 



    def draw_copy_operators(self, context, col):
        return col

                
    def draw(self, context):
        self.initialize(context)
        layout = self.layout
        
        view = context.space_data
        warn_if_camera_locked_to_layers(view, layout)

        if self.active and self.active.type == 'MESH':
            self.draw_uv_tools(context)
            self.draw_vertex_tools(context)
            col = self.draw_weight_tools(context)
            self.draw_mesh_tools(context, col)
        if self.active and self.active.type == 'ARMATURE':
            self.draw_armature_tools(context)





class PanelCustomExport(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Collada"
    bl_idname      = "AVASTAR_PT_custom_collada"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        p = util.getAddonPreferences()
        if not p.show_panel_collada:
            return False
        try:
            if context.mode == 'OBJECT':
                return True
            return False
        except (TypeError, AttributeError):
            return False

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_COLLADA, msg=panel_info_collada)

    def draw(self, context):
        layout = self.layout
        scn = context.scene


        currentSelection = util.getCurrentSelection(context)
        attached         = currentSelection['attached']
        targets          = currentSelection['targets']
        mesh.create_collada_layout(context, layout, attached, targets, on_toolshelf=True)





class ArmatureInfo(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Rig Inspector"
    bl_idname      = "AVASTAR_PT_armature_maintenance"
    bl_options     = {'DEFAULT_CLOSED'}


    @classmethod
    def poll(self, context):
        armobj = context.object
        try:
            result = armobj.type=='ARMATURE'
        except:
            result = False
        return result


    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_RIG_CONVERTER, msg=panel_info_tools)


    def draw(self, context):
        self.draw_info(context)
        self.draw_copyrig(context)

    def draw_hierarchy_check(self, context, layout):
        rig.AvastarCheckHierarchy.draw_boneset(self, context, layout)

    def draw_copyrig(self, context):

        layout = self.layout
        scn    = context.scene


        currentSelection = util.getCurrentSelection(context)
        active           = currentSelection['active']

        if active:
            if active.type=="ARMATURE":
                armobj = active
            else:
                armobj = active.find_armature()
        else:
            armobj = None

        view = context.space_data
        warn_if_camera_locked_to_layers(view, layout)

        if armobj and util.object_visible_get(armobj, context=context) and util.object_select_get(armobj):
            is_a_repair = not copyrig.armature_needs_update(armobj)
            col = layout.column(align=True)
            ctargets = [arm for arm in bpy.context.selected_objects if arm.type=='ARMATURE' and 'avastar' in arm and arm != armobj]
            copyrig.ButtonCopyAvastar.draw_generic(None, context, layout, armobj, ctargets, repair=is_a_repair )


    def draw_info(self, context):

        layout = self.layout
        scn    = context.scene
        armobj = context.object
        box    = layout.box()
        joint_count = rig.get_joint_offset_count(armobj)
        box.label(text="Rig Inspector", icon=ICON_ARMATURE_DATA)

        col = box.column(align=True)
        col.label(text="Name: %s" % armobj.name)
        
        if 'avastar' in armobj:
            col = box.column(align=True)
            col.label(text="Rig type   : %s" % (armobj.RigProp.RigType))
            col.label(text="Joint type : %s" % (armobj.RigProp.JointType))
            if joint_count > 0 and DIRTY_RIG in armobj and util.use_sliders(context):
                col.label(text="Unsaved Joint Offsets", icon=ICON_ERROR)



            avastar_version, rig_version, rig_id, rig_type = util.get_version_info(armobj)

            col    = box.column(align=True)
            row    = col.row(align=True)
            row.operator("avastar.display_version_operator", text="Avastar", emboss=False)
            row.operator("avastar.display_version_operator", text="%s(%s)" %(avastar_version, AVASTAR_RIG_ID), emboss=False)

            if rig_version != None:
                row    = col.row(align=True)
                row.operator("avastar.display_rigversion_operator", text="Rig", emboss=False)
                row.operator("avastar.display_rigversion_operator", text="%s(%s)" %(rig_version, rig_id), emboss=False)
            elif rig_id != None:
                row    = col.row(align=True)
                row.operator("avastar.display_rigversion_operator", text="Rig", emboss=False)
                row.operator("avastar.display_rigversion_operator", text="unknown (%s)" %(rig_id), emboss=False)

            if rig_version != avastar_version and rig_id != AVASTAR_RIG_ID:
                row    = col.row(align=True)
                row.operator("avastar.version_mismatch", text='Outdated Rig', icon=ICON_ERROR, emboss=False)
        else:
            col.label(text="Not an Avastar Rig")

        self.draw_hierarchy_check(context, box)



        if 'avastar' in armobj:
            custom_meshes = util.getCustomChildren(armobj, type='MESH')
            if len(custom_meshes) > 0:
                bbox = box.box()
                col = bbox.column(align=True)
                col.label(text="Custom Mesh table")
                for cm in custom_meshes:
                    col = col.column(align=True)
                    op = col.operator("avastar.object_select_operator", text=cm.name, icon=ICON_OBJECT_DATA)
                    op.name=cm.name
            else:
                col = box.column(align=True)
                col.label(text="no Custom Mesh")

            col    = box.column(align=True)
            row    = col.row(align=True)








            row    = col.row(align=True)
            bone_count = len(animation.find_animated_bones(armobj))
            if bone_count == 0:
                row.label(text="No Animation")
            else:
                row.label(text="", icon=ICON_CHECKMARK)
                row.label(text="%d Animated Bones" % bone_count)








MIN_MESH_INFO_DELAY = 0.5
MIN_SIZE  = 2

last_object = None
last_mode = None
last_timestamp = time.time()
meshstat_info = None

def init_mesh_info_panel(context):

    global last_object
    global last_mode
    global last_timestamp
    global meshstat_info

    if context.scene.MeshProp.auto_refresh_mesh_stat:
        if context.object == last_object and context.mode == last_mode and time.time() - last_timestamp < MIN_MESH_INFO_DELAY:
            return None

    meshstat_info = {
    STATS_VERTEX_COUNT :   0,
    STATS_NORMAL_COUNT :   0,
    STATS_FACE_COUNT :     0,
    STATS_MAT_COUNT :      0,
    STATS_TRI_COUNT :      0,
    STATS_UV_COUNT :       0,
    STATS_UV_LAYER_COUNT : 0,
    STATS_TRI_COUNT_MAX :  0,
    STATS_UNASSIGNED_POLYS:0,
    STATS_UNASSIGNED_SLOTS:0,
    STATS_UNASSIGNED_MATS: 0,

    STATS_RADIUS :    0,
    STATS_VC_LOWEST : 0,
    STATS_VC_LOW :    0,
    STATS_VC_MID :    0,
    STATS_VC_HIGH :   0,

    STATS_NWC_EFFECTIVE : [],
    STATS_NWC_DISCARDED : [],
    }
    return meshstat_info

class PanelMeshInfo(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label       = "Mesh Inspector"
    bl_idname      = "AVASTAR_PT_mesh_inspector"
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        for obj in context.selected_objects:
           if obj.type=='MESH':
               return True
        return False
        
    
    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_MESH_INFO, msg=panel_info_mesh)

    def draw(self, context):
    
        layout = self.layout
        scn = context.scene

        try:
            if len ([obj for obj in context.selected_objects if obj.type == 'MESH']) == 0:
                row = layout.row()
                row.label(text="No Mesh selected", icon=ICON_INFO)
                return
        except (TypeError, AttributeError):
            return
        

        currentSelection = util.getCurrentSelection(context)
        targets          = currentSelection['targets']
        active           = currentSelection['active']

        if len(targets) > 0:

            def add_mat_error(col, icon, msg, label, text='Materials:'):
                row = col.row(align=True)
                row.alignment='LEFT'
                op=row.operator("avastar.generic_info_operator", text=text, icon=icon, emboss=False)
                op.msg=msg
                row.label(text=label)




            need_update = False
            stat_info = init_mesh_info_panel(context)
            weightmaps_per_meshobj = {}
            if stat_info != None:

                for meshobj in targets:
                    if context.scene.MeshProp.auto_refresh_mesh_stat:
                        stats = util.create_mesh_stats(context.scene, meshobj)
                    else:
                        stats = meshobj.get(MESH_STATS)

                    if not stats:
                        need_update = True
                        continue

                    weightmaps = stats.get(STATS_DEFORMING_BONES, [])
                    weightmaps_per_meshobj[meshobj.name] = len(weightmaps)
                    stat_info[STATS_NWC_EFFECTIVE].extend(weightmaps)
                    stat_info[STATS_NWC_DISCARDED].extend(stats.get(STATS_DISCARDED_BONES, 0))

                    uv_count = stats.get(STATS_UV_COUNT, 0)
                    if uv_count == 0:
                        stat_info[STATS_UV_LAYER_COUNT] += 1
                    else:
                        stat_info[STATS_UV_COUNT]

                    stat_info[STATS_NORMAL_COUNT] += stats.get(STATS_NORMAL_COUNT, 0)
                    stat_info[STATS_FACE_COUNT] += stats.get(STATS_FACE_COUNT, 0)
                    stat_info[STATS_VERTEX_COUNT] += stats.get(STATS_VERTEX_COUNT, 0)
                    stat_info[STATS_TRI_COUNT] += stats.get(STATS_TRI_COUNT, 0);
              
                    mat = stats.get(STATS_MAT_COUNT, 0)
                    mate = stats.get(STATS_EXTENDED_MAT_COUNT, 0)
                    if mat + mate  > stat_info[STATS_MAT_COUNT]:
                        stat_info[STATS_MAT_COUNT] = mat
                        stat_info[STATS_EXTENDED_MAT_COUNT] = mate
                    if stats.get(STATS_TRI_COUNT, 0) > stat_info[STATS_TRI_COUNT_MAX]:
                        stat_info[STATS_TRI_COUNT_MAX] = stats.get(STATS_TRI_COUNT, 0)

                    stat_info[STATS_UNASSIGNED_POLYS] += stats.get(STATS_UNASSIGNED_POLYS, 0)
                    stat_info[STATS_UNASSIGNED_SLOTS] += stats.get(STATS_UNASSIGNED_SLOTS, 0)
                    stat_info[STATS_UNASSIGNED_MATS] += stats.get(STATS_UNASSIGNED_MATS, 0)

                    stat_info[STATS_VC_LOWEST] += stats.get(STATS_VC_LOWEST, 0)
                    stat_info[STATS_VC_LOW]    += stats.get(STATS_VC_LOW, 0)
                    stat_info[STATS_VC_MID]    += stats.get(STATS_VC_MID, 0)
                    stat_info[STATS_VC_HIGH]   += stats.get(STATS_VC_HIGH, 0)

            box = layout.box()
            box.label(text="Mesh Inspector", icon=ICON_OBJECT_DATAMODE)
            col = box.column(align=True)
            row = col.row(align=True)
            row.operator("avastar.update_mesh_stats")
            row.prop(context.scene.MeshProp, "auto_refresh_mesh_stat", text='', icon=ICON_AUTO)

            if need_update:
                return

            col = box.column(align=True)
            meshsize_icon     = "FILE_TICK"
            high_tricount_msg = None

            if stat_info[STATS_TRI_COUNT_MAX] > 174752: #http://wiki.secondlife.com/wiki/Limits
                meshsize_icon="ERROR"
                high_tricount_msg = messages.msg_mesh_tricount % stat_info[STATS_TRI_COUNT_MAX]
            elif stat_info[STATS_TRI_COUNT_MAX] > 21844:
                meshsize_icon = ICON_INFO
                high_tricount_msg = messages.msg_face_tricount % stat_info[STATS_TRI_COUNT_MAX]

            row = col.row(align=True)
            if len(targets) == 1 and context.active_object == targets[0]:
                row.label(text="%s:"%targets[0].name)
            else:
                row.label(text="Meshes:")
                row.label(text="%d"%len(targets))

            row = col.row(align=True)
            row.alignment='LEFT'
            op=row.operator("avastar.generic_info_operator", text=" Verts:", icon=ICON_BLANK1, emboss=False)
            op.msg="Sum of all vertices in All selected meshes"
            row.label(text="%d"%stat_info[STATS_VERTEX_COUNT])

            row = col.row(align=True)
            row.alignment='LEFT'
            op=row.operator("avastar.generic_info_operator", text="Faces:", icon=ICON_BLANK1, emboss=False)
            op.msg="Sum of all faces in All selected meshes"
            row.label(text="%d"%stat_info[STATS_FACE_COUNT])

            if stat_info[STATS_TRI_COUNT_MAX] > 21844:
                row = col.row(align=True)
                row.alert = stat_info[STATS_TRI_COUNT_MAX] > 174752
                row.alignment='LEFT'
                op = row.operator("avastar.tris_info_operator", text="   Tris:", icon=meshsize_icon, emboss=False)
                op.msg  = high_tricount_msg
                op.icon = meshsize_icon
                row.label(text="%d"%stat_info[STATS_TRI_COUNT])
            else:
                row = col.row(align=True)
                row.alignment='LEFT'
                op=row.operator("avastar.generic_info_operator", text="   Tris:", icon=meshsize_icon, emboss=False)
                op.msg="Sum of all Triangles in All selected meshes"
                row.label(text="%d"%stat_info[STATS_TRI_COUNT])
            
            if stat_info[STATS_UV_COUNT] > 0:
                row = col.row(align=True)
                row.alignment='LEFT'
                op=row.operator("avastar.generic_info_operator", text="   UVs:", icon=ICON_BLANK1, emboss=False)
                op.msg="Sum of all UV Faces in All selected meshes"
                row.label(text="%d"%stat_info[STATS_UV_COUNT])

            if stat_info[STATS_MAT_COUNT] == 0:
                icon = ICON_ERROR
                label = "No Materials"
                msg = messages.msg_zero_materials
                add_mat_error(col, icon, msg, label)
            else:
                col.separator()
                if stat_info[STATS_EXTENDED_MAT_COUNT] > 0:
                    icon = ICON_INFO
                    msg = "Detected Material Split (triangle count on texture face > 21844)"
                    label = "%d + %d" % (stat_info[STATS_MAT_COUNT], stat_info[STATS_EXTENDED_MAT_COUNT])
                else:
                    icon = ICON_CHECKMARK
                    msg = "Material Count of Mesh with most defined Materials"
                    label = "%d" % stat_info[STATS_MAT_COUNT]
                add_mat_error(col, icon, msg, label)
                
                if stat_info[STATS_UNASSIGNED_POLYS] > 0:
                    icon = ICON_ERROR
                    msg = "Total number of polygons not assigned to any material"
                    label = "%d polys without material" % stat_info[STATS_UNASSIGNED_POLYS]
                    add_mat_error(col, icon, msg, label, text='')

                if stat_info[STATS_UNASSIGNED_SLOTS] > 0:
                    icon = ICON_INFO
                    msg = "Total Number of empty Material slots (Slots not assigned to any material)"
                    label = "%d unassigned material slots" % stat_info[STATS_UNASSIGNED_SLOTS]
                    add_mat_error(col, icon, msg, label, text='')

                if stat_info[STATS_UNASSIGNED_MATS] > 0:
                    icon = ICON_INFO
                    msg = "Number of Materials which have no polygon assigned"
                    label = "%d unused material slots" % stat_info[STATS_UNASSIGNED_MATS]
                    add_mat_error(col, icon, msg, label, text='')

            ld = len(stat_info[STATS_NWC_DISCARDED]) 
            le = len(stat_info[STATS_NWC_EFFECTIVE])

            if ld + le > 0:        
                
                ibox = box.box()
                icol = ibox.column()
                if le > 0:
                    row = icol.row(align=True)
                    op = row.operator("avastar.weightmap_info_operator", text="", icon=ICON_INFO, emboss=False)
                    msg= messages.msg_identified_weightgroups % len(stat_info[STATS_NWC_EFFECTIVE])
                    for v in stat_info[STATS_NWC_EFFECTIVE]:
                        msg += v+"\n"
                    op.msg=msg
                    op.icon="INFO"
                    row.label(text="Using %d Weight Maps"%le)

                    for key,val in weightmaps_per_meshobj.items():
                        row = icol.row(align=True)
                        row.label(text='', icon='BLANK1')
                        row.label(text=key)
                        row.label(text=str(val))

                if ld > 0:
                    col = box.column(align=True)
                    col.label(text="Deforming Weight Maps")
                
                    row = col.row(align=True)
                    op = row.operator("avastar.weightmap_info_operator", text="", icon=ICON_ERROR, emboss=False)
                    msg= messages.msg_discarded_weightgroups % len(stat_info[STATS_NWC_DISCARDED])
                    for v in stat_info[STATS_NWC_DISCARDED]:
                        msg += v+"\n"
                    op.msg=msg
                    op.icon="WARNING"
                    row.label(text="ignored %d Weight Maps"%ld)

            if stat_info[STATS_UV_LAYER_COUNT] > 0:
                label = "Missing %d %s" % (stat_info[STATS_UV_LAYER_COUNT], util.pluralize("UV-Map",stat_info[STATS_UV_LAYER_COUNT] ))
                msg = util.missing_uv_map_text(targets)
                col    = box.column(align=True)
                row    = col.row(align=True)
                op     = row.operator("avastar.uvmap_info_operator", text="", icon=ICON_ERROR, emboss=False)
                op.msg = msg
                op.icon="WARNING"
                row.label(text=label)

            if len(targets)>0:
                icol = box.column()
                icol.label(text="Estimates:")
                ibox = box.box()
                icol = ibox.column(align=True)
                
                row = icol.row(align=True)
                row.label(text="LOD")
                row.label(text="Tris")
                row.label(text="Verts")

                row = icol.row(align=True)
                row.label(text="High")
                row.label(text="%d"%stat_info[STATS_TRI_COUNT])
                row.label(text="%d"%stat_info[STATS_VC_HIGH])
 
                row = icol.row(align=True)
                row.label(text="Medium")
                row.label(text="%d"%max(MIN_SIZE, int(stat_info[STATS_TRI_COUNT]/4)))
                row.label(text="%d"%int(stat_info[STATS_VC_MID]))
                                       
                row = icol.row(align=True)
                row.label(text="Low")
                row.label(text="%d"%max(MIN_SIZE, int(stat_info[STATS_TRI_COUNT]/16)))
                row.label(text="%d"%int(stat_info[STATS_VC_LOW]))

                row = icol.row(align=True)
                row.label(text="Lowest")
                row.label(text="%d"%max(MIN_SIZE, int(stat_info[STATS_TRI_COUNT]/32)))
                row.label(text="%d"%int(stat_info[STATS_VC_LOWEST]))

                icol = ibox.column(align=True)
                
                row = icol.row(align=True)
                row.label(text="Server Costs")
                row.label(text="%.1f"%(0.5*len(targets)))
                        
            col = box.column(align=True)
            col.operator(ButtonCheckMesh.bl_idname, icon=ICON_QUESTION)





class PanelAvastarUpdate(bpy.types.Panel):
    from . import bl_info
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category = "Avastar"

    bl_label    = "Maintenance"
    bl_idname   = "AVASTAR_PT_update_migrate"
    bl_options  = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return True

    def draw_header(self, context):
        util.draw_info_header(self.layout.row(), AVASTAR_MAINTENANCE, msg=panel_info_register)

    def draw(self, context):

        layout = self.layout
        addonProps     = util.getAddonPreferences()

        url = RELEASE_INFO + "?myversion=" + util.get_addon_version() + "&myblender=" + str(get_blender_revision())
        box   = layout.box()
        box.label(text="My Products")
        col = box.column(align=True)
        if addon_utils.check("avastar")[0]:
            import avastar
            info = avastar.bl_info
            row = col.row()



            text="%s %s" % (info['name'], str(info['version']))
            row.operator("avastar.copy_support_info", icon=ICON_EYEDROPPER, text=text)

        if addon_utils.check("sparkles")[0]:
            import sparkles
            info = sparkles.bl_info
            row = col.row()
            row.label(text=info['name']    )
            row.label(text=str(info['version']) )

        if addon_utils.check("primstar")[0]:
            import primstar
            info = primstar.bl_info
            row = col.row()
            row.label(text=info['name']    )
            row.label(text=str(info['version']) )

        can_report   = True
        is_logged_in = True
        if addonProps.update_status=='CANUPDATE':
            opn   = 'avastar.check_for_updates'
            label = 'Login to Get %s' % addonProps.version
            can_report   = False
            is_logged_in = False
        elif addonProps.update_status=='UPDATE':
            opn   = 'avastar.download_update'
            label = 'Download Avastar-%s' % addonProps.version
        elif addonProps.update_status=='ONLINE':
            opn   = 'avastar.check_for_updates'
            label = 'Redo Check for updates'
        elif addonProps.update_status=='READY_TO_INSTALL':
            opn   = 'avastar.download_install'
            label = 'Install Avastar-%s' % addonProps.version
        elif addonProps.update_status=='ACTIVATE':
            opn   = 'avastar.download_reload'
            label = 'Reload Addon to Activate'
        else:
            opn   = 'avastar.check_for_updates'
            label = 'Check for updates' if addonProps.username == '' or addonProps.password == '' else 'Login at Machinimatrix'
            can_report   = False
            is_logged_in = False
        

        if can_report:
            box   = layout.box()
            box.label(text="Support Request")

            col = box.column(align=True)
            col.prop(addonProps, "ticketTypeSelection")
            col = box.column(align=True)
            col.prop(addonProps, "productName" )

            col = box.column(align=True)
            col.prop(addonProps, "addonVersion")
            col.prop(addonProps, "blenderVersion")
            col.prop(addonProps, "operatingSystem")
            col.enabled = False
            col = box.column(align=True)
            col.operator('avastar.send_report', text="Create Report", icon=ICON_RADIOBUT_ON)
        


        
        box   = layout.box()
        box.label(text="My account")
        col = box.column(align=True)
        row = col.row(align=True)
        
        wlabel = "Welcome, %s" % addonProps.user.replace("+"," ") if addonProps.user != '' else "My Machinimatrix Account"
        
        row.operator("wm.url_open", text=wlabel, icon=ICON_NONE, emboss=False).url=AVASTAR_DOWNLOAD
        row.operator("wm.url_open", text="",icon=ICON_INFO,emboss=False).url=AVASTAR_DOWNLOAD
        
        col = box.column(align=True)
        col.prop(addonProps,"username",  text= "Logged in as" if is_logged_in else "User", emboss = not is_logged_in)
        
        if not is_logged_in:
            col.prop(addonProps,"password",  emboss = not is_logged_in)
            row = box.row(align=True)
            row.alignment='RIGHT'
            row.prop(addonProps,"keep_cred", emboss = not is_logged_in)

        row=box.row(align=True)
        row.operator(opn, text=label, icon=ICON_URL)
        row.operator("avastar.download_reset", text='', icon=ICON_X)

        col = box.column(align=True)
        if addonProps.update_status=='CANUPDATE':
            col.label(text="Update available after login", icon=ICON_ERROR)
        elif addonProps.update_status=='UPDATE':
            split = col.split(factor=0.2)
            split.label(text="Server:")

            split.alignment='RIGHT'
            split.label(text=addonProps.server)









        else:
            split = col.split(factor=0.2, align=True)
            split.label(text="Status:")
            split.alignment='RIGHT'
            label = addonProps.update_status
            if label == 'ONLINE':
                label = "You are up to date"
                split.label(text=label)
            else:
                split.prop(addonProps, "update_status", text='', emboss=False)
                split.alignment='RIGHT'
                split.enabled=False
        
class PanelRiggingInfo(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Rigging"

    bl_label ="Rigging"
    bl_idname = "AVASTAR_PT_animation_rigging_info"

    @classmethod
    def poll(self, context):

        if not (context and context.active_object): 
            show_tab = True
        else:
            armobj = util.get_armature_from_context(context)
            show_tab = not (armobj and "avastar" in armobj and context.mode=='POSE')
        return show_tab

    def draw(self, context):

        armobj = util.get_armature_from_context(context)
        is_avastar = armobj and "avastar" in armobj
        has_avastars = util.get_armatures(avastar_only=True)
        layout = self.layout
        box = layout.box()
        if has_avastars or is_avastar:
            box.label(text='This panel is empty')
        else:
            box.label(text='This panel is inactive')

        col=box.column(align=True)
        col.label(text='wake up as follows:')
        col.separator()
        if not has_avastars:
            col.label(text='- Add an Avastar')
        if not is_avastar:
            col.label(text='- Select the Avastar')
        col.label(text='- Switch to Pose mode')            

        col.separator()
        bbox=box.box()
        bbox.label(text='Info For newbies:', icon=ICON_INFO)
        col=bbox.column(align=True)
        col.label(text='- Open Avastar vertical tab')
        col.label(text='- Open Workflows panel')
        col.separator()
        col.label(text='- From Workflow Presets:')
        col.label(text='- Select Pose&Animate')
        col.separator()
        col.label(text='- Read the Avastar docs')
        col.separator()
        col.operator("wm.url_open", text='Avastar Documentation').url=DOCUMENTATION+'/reference/usermanual/'







class PanelRigLayers(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_category    = "Rigging"

    bl_label ="Mesh display"
    bl_idname = "AVASTAR_PT_rig_layers"
    bl_context = 'data'

    @classmethod
    def poll(self, context):
        try:
            return "avastar" in context.active_object
        except TypeError:
            return None

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        armobj = util.get_armature(obj)

        box = layout.box()
        box.label(text="Hide Mesh:", icon=ICON_MESH_DATA)
        col = box.column(align=True)

        meshes = util.findAvastarMeshes(obj)
        if "hairMesh" in meshes: col.prop(meshes["hairMesh"], "hide_viewport", toggle=True, text="Hair")
        if "headMesh" in meshes: col.prop(meshes["headMesh"], "hide_viewport", toggle=True, text="Head")
        if "eyelashMesh" in meshes: col.prop(meshes["eyelashMesh"], "hide_viewport", toggle=True, text="Eyelashes")
        row = col.row(align=True)
        if "eyeBallLeftMesh" in meshes: row.prop(meshes["eyeBallLeftMesh"], "hide_viewport", toggle=True, text="Eye L")
        if "eyeBallRightMesh" in meshes: row.prop(meshes["eyeBallRightMesh"], "hide_viewport", toggle=True, text="Eye R")
        if "upperBodyMesh" in meshes: col.prop(meshes["upperBodyMesh"], "hide_viewport", toggle=True, text="Upper Body")
        if "lowerBodyMesh" in meshes: col.prop(meshes["lowerBodyMesh"], "hide_viewport", toggle=True, text="Lower Body")
        if "skirtMesh" in meshes: col.prop(meshes["skirtMesh"], "hide_viewport", toggle=True, text="Skirt")

classes = (
    PanelRiggingInfo,
    PanelWorkflow,
    PanelShaping,
    PanelRigDisplay,
    PanelRiggingConfig,

    PanelRigJointOffsets,
    PanelAvatarMaterials,
    PanelSkinning,
    PanelWeightCopy,
    PanelPosing,
    PanelFitting,
    PanelAvatarShape,
    ButtonCheckMesh,
    PanelAvastarRigImport,
    PanelAvastarTool,
    PanelCustomExport,
    ArmatureInfo,
    PanelMeshInfo,
    PanelAvastarUpdate,
    PanelRigLayers,
    ButtonLoadWorkspace
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered pannels:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered pannels:%s" % cls)
