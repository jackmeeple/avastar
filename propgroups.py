### Copyright 2019 Machinimatrix
###
### This file is part of Avastar.
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

import bpy, logging, time
from bpy.props import *
from .import animation, armature_util, bind, const, create, data, mesh, messages, shape, util, rig, weights
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty, FloatProperty

from .const import *
from .messages import *
from bpy.app.handlers import persistent

log = logging.getLogger('avastar.propgroups')
updatelog = logging.getLogger('avastar.update')
visitlog = logging.getLogger('avastar.visit')
registerlog = logging.getLogger("avastar.register")






def loopUpdate(self, context):
    if self.Loop:


        self.Loop_In = context.scene.frame_start
        self.Loop_Out = context.scene.frame_end

update_scene_data_on = True

def set_update_scene_data(state):
    global update_scene_data_on
    update_scene_data_on = state

def update_scene_data(self, context):
    global update_scene_data_on
    if not update_scene_data_on:
        return
    
    scene=context.scene
    active = util.get_active_object(context)
    if not ( active and active.type =='ARMATURE' and 'avastar' in active):

        return
    if not active.animation_data:
        return

    action = active.animation_data.action
    if not action:
        return

    props = action.AnimProp
    try:
        set_update_scene_data(False)

        if props.frame_start == -2:

            props.frame_start = scene.frame_start
            props.frame_end = scene.frame_end

        if props.fps == -2:
            props.fps = scene.render.fps

        if context.scene.SceneProp.loc_timeline:

            scene.frame_start = props.frame_start
            scene.frame_end = props.frame_end
            scene.render.fps = props.fps
    finally:
        set_update_scene_data(True)

def update_toggle_select(self, context):
    for action in bpy.data.actions:
        action.AnimProp.select = self.toggle_select

def update_animation(self, context):

    obj = context.active_object
         
    shape.setHands(obj, context.scene)

def weightCopyAlgorithmsCallback(scene, context):

    items=[
        ('VERTEX',   'Vertex', "Copy weights to opposite Vertices (needs exact X symmetry)"),
        ('TOPOLOGY', 'Topology', "Copy weights to mirrored Topology (needs topology symmetry, does not work for simple mesh topology)"),
        ]

    if 'toolset_pro' in dir(bpy.ops.sparkles):
        items.append(
        ('SMART',   'Shape', "Copy weights to mirrored Shape (only depends on Shape, works always but is not exact)")
        )

    return items

def update_sync_influence(context, val, symmetry):
    obj = util.get_active_object(context)
    if not obj:
        return

    pbones = obj.pose.bones
    for part in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
        name = "ik%sTarget%s" % (part, symmetry) 
        bone = pbones[name]
        if bone.sync_influence:
            name = "ik%sSolver%s" % (part, symmetry)
            bone = pbones[name] 
            con  = bone.constraints['Grab']
            con.influence = val

def update_sync_influence_left(pbone, context):
    obj = util.get_active_object(context)
    if not obj:
        return

    val = obj.RigProp.IKHandInfluenceLeft
    update_sync_influence(context, val, "Left")

def update_sync_influence_right(pbone, context):
    obj = util.get_active_object(context)
    if not obj:
        return

    val = obj.RigProp.IKHandInfluenceRight
    update_sync_influence(context, val, "Right")

def update_affect_all_joints(self, context):
    obj    = util.get_active_object(context)
    armobj = util.get_armature(obj)
    if armobj:
        joints = armobj.get('sl_joints')
        if joints:
            bones = util.get_modify_bones(armobj)
            for key, joint in joints.items():
                b=bones.get(key, None)
                if b:
                    b.select = b.select_head = b.select_tail = self.affect_all_joints

def update_rig_pose_type(self, context):
    if util.is_use_bind_pose_update_in_progress():
        return

    obj = util.get_active_object(context)
    armobj = util.get_armature(obj)
    if armobj and 'avastar' in armobj:
        shape.refreshAvastarShape(context, refresh=True)

def update_rig_lock_scale(self, context):
    obj = util.get_active_object(context)
    armobj = util.get_armature(obj)
    if armobj and 'avastar' in armobj:
        shape.refreshAvastarShape(context, refresh=True)


def update_bone_type(self, context):
    obj = util.get_active_object(context)
    arm = util.get_armature(obj)
    if arm and  len(self.display_type) > 0:
        armature_util.set_display_type(arm, self.display_type.pop())

def check_unique_snail_callback(self, context):

    return

def slider_options(self, context):
    ob = util.get_active_object(context)
    obtype = ob.type if ob else 'NONE'
    
    if obtype=='ARMATURE':
        items=[
                ('NONE',  "No Sliders", "Disable Avastar Sliders from all of Armature's Custom Meshes "),
                ('SL',    "Avatar Shape", "Use Avastar Sliders to simulate the SL Avatar shape on all of Armature's Custom Meshes")
              ]
    else:
        items=[
                ('NONE',  "No Sliders", 'Disable Avastar Sliders from Selected Meshes'),
                ('SL',    "Avatar Shape", 'Use Avastar Sliders to simulate the SL Avatar shape on Selected Meshes')
              ]
    return items


def update_sliders(context, arms=None, objs=None):
    if not context.scene.SceneProp.panel_appearance_enabled:
        return

    oss = util.get_disable_update_slider_selector()
    if oss:

        return
    else:
        active = util.get_active_object(context)
        if arms==None and objs==None:
            arms,objs = util.getSelectedArmsAndObjs(context)
        
        try:
            util.set_disable_update_slider_selector(True)

            if arms:
                for arm in arms:
                    shape_filename = arm.name
                    if context.object == arm and not context.scene.SceneProp.panel_appearance_enabled :

                        updatelog.debug("Search shape file %s" % (shape_filename) )
                        if shape_filename in bpy.data.texts:
                            updatelog.warning("Load existing shape file %s" % (shape_filename) )
                            omode = util.ensure_mode_is("OBJECT")
                            shape.ensure_drivers_initialized(arm)
                            try:
                                shape.loadProps(context, arm, shape_filename, pack=True)
                            except:
                                updatelog.warning("Could not load original shape into Mesh")
                                updatelog.warning("probable cause: The Mesh was edited while sliders where enabled.")
                                updatelog.warning("Discarding the Shape %s" % shape_filename)

                            util.ensure_mode_is(omode)
                            if arm == context.object:
                                text = bpy.data.texts[shape_filename]
                                util.remove_text(text, do_unlink=True)
                                updatelog.warning("update slider type: Removed shape for Armature %s in textblock:%s" % (arm.name, shape_filename) )
                    else:
                        if not shape_filename in bpy.data.texts:
                            shape.saveProperties(arm, shape_filename, normalize=False, pack=True)
                            updatelog.debug("update slider type: Stored initial shape for Armature %s in textblock:%s" % (arm.name, shape_filename) )



            need_attach = True
            attached_objects=[]
            if objs:
                try:
                    armobj = None
                    for obj in objs:
                        util.tag_addon_revision(obj)
                        if DIRTY_MESH in obj:
                            util.reset_dirty_mesh(context, obj)
                            shape.reset_weight_groups(obj)

                        util.set_active_object(context, obj)
                        updatelog.debug("Update Object %s" % (obj.name) )

                        armature = obj.find_armature()
                        if armature:
                            if armobj != armature:
                                armobj = armature
                                util.set_active_object(context, armature)

                            shape.attachShapeSlider(context, armature, obj)

                except Exception as e:
                    print("update slider type(objs): Runtime error:", e)
                    raise e
        finally:
            util.set_disable_update_slider_selector(oss)
            util.set_active_object(context, active)




def add_material_for(armature_name, part_name, onlyMainCharacter, type, isUnique):

    type_abb = type[0].lower()
    if type_abb == 'n':
        mat_name="Material"
    else:
        if part_name in ["eyeBallLeftMesh", "eyeBallRightMesh"]:
            mat_name="eyeBalls"
        elif part_name in ["eyelashMesh","headMesh"]:
            mat_name="head"
        elif onlyMainCharacter==True and part_name == "hairMesh":
            return None
        else:
            mat_name= part_name[0:part_name.find("Mesh")]

        prep = "avastar"
        if isUnique == True:
          prep = armature_name
        mat_name = prep + ":mat:" + type_abb+ ':' + mat_name

    try:
        mat = bpy.data.materials[mat_name]
    except:
        mat = bpy.data.materials.new(mat_name)
    return mat

def set_avastar_materials(context):
    obj = context.active_object
    material_type = obj.avastarMaterialProp.material_type
    unique = obj.avastarMaterialProp.unique

    print("Set materials for", obj.name)    
    print("New material type is", material_type)
    print("unique material   is", unique)

    util.ensure_avastar_repository_is_loaded()
    parts = util.findAvastarMeshes(obj) if obj.type=='ARMATURE' else {obj.name: obj for obj in context.selected_objects}
    for name in parts:
        part = parts[name]

        mat = add_material_for(obj.name, name, True, material_type, unique)
        if mat:
            part.active_material= mat
            part.avastarMaterialProp.material_type = material_type
            part.avastarMaterialProp.unique = unique

            print ("Set material(", name,")", mat.name)





RigTypeItems=(
    ('BASIC', 'Basic' , 'This Rig type Defines the Legacy Rig:\nThe basic Avatar with 26 Base bones and 26 Collision Volumes.\nGood for Main grid and other Online Worlds like OpenSim, etc'),
    ('EXTENDED', 'Extended'  , 'This Rig type Defines the extended Rig:\nNew bones for Face, Hands, Tail, Wings, ... (the Bento rig)'),
    ('REFERENCE', 'Reference' , 'The Reference Rig contains only the Bones defined within the avatar_skeleton.xml file.\nGood for testing purposes, please never use for production'),
)


class AnimPropGroup(bpy.types.PropertyGroup):
    Loop : BoolProperty(name="Loop", default = False, description="Loop part of the animation", update=loopUpdate)
    Loop_In : IntProperty(name="Loop In", description="Frame to start looping animation")
    Loop_Out : IntProperty(name="Loop Out", description="Frame to stop looping, rest will play when animation is stopped")
    Priority : IntProperty(name="Priority", default = 3, min=MIN_PRIORITY, max=MAX_PRIORITY, description="Priority at which to play the animation")
    Ease_In : FloatProperty(name="Ease In", default=0.8, min=0, description="Fade in the influence of the animation at the beginning [s]")
    Ease_Out : FloatProperty(name="Ease Out", default=0.8, min=0, description="Fade out the influence of the animation at the end [s]")

    frame_start : IntProperty(
                  name="Start Frame",
                  description="First frame to be exported",
                  default = -2,
                  update = update_scene_data
                  )

    frame_end   : IntProperty(
                  name="End Frame",
                  description="Last frame to be exported",
                  default = -2,
                  update = update_scene_data
                  )

    fps         : IntProperty(
                  name="Frame Rate",
                  description="Frame rate to be exported",
                  default = -2,
                  update = update_scene_data
                  )

    Translations : BoolProperty(
                   name = "With Bone translation",
                   default = False,
                   description = AnimProp_Translation_description
                   )

    selected_actions : BoolProperty(
                  name="Bulk Export",
                  default = False,
                  description = AnimProp_selected_actions_description
                  )

    select : BoolProperty(
                  name="select",
                  default = False,
                  description = "Select this action for exporting"
                  )

    toggle_select : BoolProperty(
                  name="All",
                  default = False,
                  description = "Select/Deselkct All",
                  update=update_toggle_select
                  )

    with_reference_frame : BoolProperty(
                  name="Add Reference Frame",
                  default = True,
                  description = "Prepend a generated BVH reference frame before the first animation frame.\n\n"\
                              + "Hint: If the Animation was imported from a Secondlife BVH file,\n"\
                              + "then it already contains a reference frame! In that case we recommend\n"\
                              + "that you delete the first frame in the animation, and enable this option to let\n"\
                              + "Avastar generate a reference frame as needed.\n"\
                              + "Note: The reference frame is not played in the SL animation"
                  )

    with_bone_lock : BoolProperty(
                  name="With Bone Lock",
                  default = False,
                  description = "Ensures that all keyframed bones are contained in the animation.\n\n"\
                              + "Explain: If you keyframe a bone but actually do not animate it,\n"\
                              + "the bone does not move (is locked), so normally such\n"\
                              + "keyframes are removed during import to SL.\n\n"\
                              + "When this option is enabled, the bone-locking animations\n"\
                              + "are kept and uploaded. Note: you must enable this option\n"\
                              + "for static poses."
                  )

    modeitems = [
        ('bvh', 'BVH', 'BVH'),
        ('anim', 'Anim', 'Anim'),
        ]
    Mode : EnumProperty(items=modeitems, name='Mode', default='anim')

    Basename : StringProperty(
        name="name",
        maxlen=100,
        default= "$action",
        description=
'''filename with optional substitutions:

    $action  : Action name
    $avatar  : Armature name
    $fps     : Frame per Second
    $start   : start frame
    $end     : end frame

additionally for .anim format:

    $prio    : priority
    $easein  : ease in (msec)
    $easeout : ease out (msec)
    $loopin  : loop in
    $loopout : loop out

The default template name is "$action" '''
    )

    handitems = []

    HANDS = shape.HANDS

    for key in range(len(HANDS.keys())):
        handitems.append((str(HANDS[key]['id']),HANDS[key]['label'],HANDS[key]['label'] ))

    Hand_Posture : EnumProperty( items=handitems, name='Hands', default=HAND_POSTURE_DEFAULT,
            update=update_animation, description="Hand posture to use in the animation" )

    with_pelvis_offset : BoolProperty(
                  name="With Pelvis Offset",
                  default = False,
                  description = "Experimental: Add the distance from Pelvis to Origin as Root Offset.\n"\
                              + "The offset is actually added to all pose bones in all frames\n"\
                              + "Note: The SL animations all have zero offset")

    used_restpose_bone_items = [
        ('VISIBLE', 'Visible bones', 'Include all currently visible Deform Bones'),
        ('ANIMATED', 'Animated bones', 'Include all deform bones weighted in any of the visible Meshes'),
        ('ALL', 'All bones', 'Include all Deform bones (not recommended)'),
        ]
    used_restpose_bones : EnumProperty(items=used_restpose_bone_items, name='Subset', default='ALL')

    only_visible_pose_bones : BoolProperty(
                  name="Only Visible",
                  default = False,
                  description = "Restrict the set of bones for the Rig Reset pose to only visible Bones.\n"\
                              + "You may want to use this when your Mesh is a rigged attachment")


    RigType : EnumProperty(
        items       = RigTypeItems,
        name        = "Rig Type",
        description = "Basic: Old Avatar Skeleton, Extended: Bento Bones",
        default     = 'EXTENDED')

class SkeletonPropGroup(bpy.types.PropertyGroup):

    use_strict_bone_hierarchy : BoolProperty(
        name = "Strict Hierarchy",
        default = False,
        description = "Disabled: Only check Deform Bone Rig for Strict SL Hierarchy\n"\
                    + "Enabled: Also check Control Rig for Strict SL Hierarchy"
        )

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

class ScenePropGroup(bpy.types.PropertyGroup):

    avastarMeshType : EnumProperty(
        items=(
            ('NONE',    'Rig only'  , 'Create only the Rig (without the Second Life character meshes)'),
            ('TRIS',    'with Tris' , 'Create Rig and Meshes using Triangles'),
            ('QUADS',   'with Quads', 'Create Rig and Meshes mostly with Quads')),
        name="Create Avatar",
        description="Create a new Avastar character",
        default='TRIS')

    avastarRigType : EnumProperty(
        items=RigTypeItems,
        name="Rig Type",
        description= "The set of used Bones",
        default='EXTENDED')

    avastarJointType : EnumProperty(
        items=(
            ('POS',   'Pos' ,    'Create a rig based on the pos values from the avatar skeleton definition\nFor making Cloth Textures for the System Character (for the paranoid user)'),
            ('PIVOT', 'Pivot'  , 'Create a rig based on the pivot values from the avatar skeleton definition\nFor Creating Mesh items (usually the correct choice)')
        ),
        name="Joint Type",
        description= "SL supports 2 Skeleton Defintions.\n\n- The POS definition is used for the System Avatar (to make cloth).\n- The PIVOT definition is used for mesh characters\n\nAttention: You need to use POS if your Devkit was made with POS\nor when you make cloth for the System Avatar",
        default='PIVOT')

    skeleton_file   : StringProperty( name = "Skeleton File", default = "avatar_skeleton.xml",
                                      description = "This file defines the Deform Skeleton\n"
                                                  + "This file is also used in your SL viewer. You find this file in:\n\n"
                                                  + "{Viewer Installation folder}/character/avatar_skeleton.xml\n\n"
                                                  + "You must make sure that the Definition file used in Avastar matches\n"
                                                  + "with the file used in your Viewer.\n\n"
                                                  + "When you enter a simple file name then Avastar reads the data its own lib subfolder\n"
                                    )
    lad_file        : StringProperty( name = "Lad File",      default = "avatar_lad.xml",
                                      description = "This file defines the Avatar shape\n"
                                                  + "This file is also used in your SL viewer. You find this file in:\n\n"
                                                  + "{Viewer Installation folder}/character/avatar_lad.xml\n\n"
                                                  + "You must make sure that the Definition file used in Avastar matches\n"
                                                  + "with the file used in your Viewer.\n\n"
                                                  + "When you enter a simple file name then Avastar reads the data its own lib subfolder\n"
                                    )        

    target_system   : EnumProperty(
        items=(
            ('EXTENDED', 'SL Main',  "Export items for the Second Life Main Grid.\n"
                           +  "This setting takes care that your creations are working with all \n"
                           +  "officially supported Bones. (Note: This includes the new Bento Bones as well)"),
            ('BASIC', 'SL Legacy', "Export items using only the SL legacy bones.\n"
                           +  "This setting takes care that your creations only use\n"
                           +  "the Basic Boneset (26 bones and 26 Collision Vollumes).\n"
                           +  "Note: You probably must use this option for creating items for other worlds."),
            ('RAWDATA', 'Tool exchange',  "Export items for usage in other tools.\n"
                           +  "This setting exports the skeleton as is\n"
                           +  "without any considerations regarding the target system (experimental)"),
        ),
        name="Target System",
        description = "The System for which the items are created.\n",
        default     = 'EXTENDED'
    )

    collada_only_weighted : BoolProperty(
                    default=True,
                    name= "Only Weighted Bones",
                    description=SceneProp_collada_only_weighted
                    )

    collada_only_deform : BoolProperty(
                    default=True,
                    name= "Only Deform Bones",
                    description=SceneProp_collada_only_deform
                    )

    collada_full_hierarchy : BoolProperty(
                    default=True,
                    name= "Enforce Parent Hierarchy",
                    description=SceneProp_collada_full_hierarchy
                    )

    collada_complete_rig : BoolProperty(
                    default=False,
                    name= "Export all Bones",
                    description=SceneProp_collada_complete_rig
                    )

    collada_export_boneroll : BoolProperty(default=False, name= "Export Bone Roll",
                            description="Export with Avastar Bone Roll values (Experimental)"
                           )
    collada_export_layers : BoolProperty(default=False, name= "Export Bone Layers",
                            description="Export with Avastar Bone Layers"
                           )
    collada_blender_profile : BoolProperty(default=False, name= "Export with Blender Profile",
                            description="Add extra Blender data to the export by using the Blender Collada profile\nThe additional information can only be read from Collada importers which support the blender Collada profile as well.\nThe Blender profile is supported since blender 2.77a\n\nNote:It should be safe to export with the blender profile enabled because\nother tools should ignore the extra data if they do not support it"
                           )
    collada_export_rotated : BoolProperty(default=True, name= "Export SL rotation",
                            description="Rotate armature by 90 degree for SL (Experimental)"
                           )
    collada_export_shape : BoolProperty(default=False, name= "Export Shape",
                            description = "Export the current shape into a file\n"
                                        + "with same name and extension '.shape'\n\n"
                                        + "Note: The Shape file is mainly used to support\n"
                                        + "Developer kit creators. For more information\n"
                                        + "Please refer to the Avastar documentation (developerkits)"
                           )
    collada_export_with_joints : BoolProperty(
                    default=True, 
                    name= "Export with Joints",
                    description=SceneProp_collada_export_with_joints_description
                    )

    collada_assume_pos_rig : BoolProperty(
                    default=False,
                    name= "Assume POS Rig",
                    description=SceneProp_collada_assume_pos_rig_description
                    )

    accept_attachment_weights : BoolProperty(default=False, name= "Allow weighted Attachments",
                            description="Allow attachment bones to also have weights.\n\nNote: Enable this option only when your target system\nallows attachment bone weighting.\nWe recommend to keep this option disabled"
                           )
    use_export_limits     : BoolProperty(default=True, name="Sanity Checks",
                            description="Enable all checks which ensure the exported data is compatible to Second Life"
                           )
    armature_preset_apply_as_Restpose  : BoolProperty(
                           name="Apply as Restpose",
                           description = "- DISABLED: Apply Preset as Pose and keep the current Restpose intact\n  Avoids joint offsets, but is experimental and \n  needs to be supported by the Collada Exporter\n\n- ENABLED: Apply the Preset as Restpose\n  needs joint offsets, otherwise safe to use",
                           default     = False
                           )
    armature_preset_apply_all_bones  : BoolProperty(
                           name="all",
                           description = "Apply all bones",
                           default     = True
                           )
    armature_preset_adjust_tails  : BoolProperty(
                           name="Match Tail",
                           description = "Match parent tails to bone heads\nThis function compensates pose presets where\nthe bone lengths do not match to the joint distances.\nHint: You usually want this feature to be turned on",
                           default     = True
                           )
    panel_appearance_enabled : BoolProperty(
                     name = "Enable Avatar Shape",
                     default = True
                     )

    panel_appearance_editable : BoolProperty(
                     name = "Lock Avatar Shape",
                     default = True,
                     description= "Used to lock the Avatar shape in their current state.\n\n"\
                                + "Note:\n"
                                + "When you select the Animesh Preset (White Stickman)\n"
                                + "the Avatar shape are automatically locked\n"
                                + "However you always can unlock even when you selected Animesh mode"
                     )

    loc_timeline : BoolProperty(
                   name = "Synchronize",
                   default = False,
                   update=update_scene_data,
                   description = "Update timeline (Startframe, Endframe, fps) automatically\nto reflect changes in the related settings of the active Action\n\nNote: For NLA exports the parameters are taken from the timeline and this option is not effective"
                   )

    panel_preset : EnumProperty(
                    name = "Workflow Presets",
                    items=(
                            ('SKIN',     'Skin & Weight'  , 'Prepare the Panels for Skinning and Weighting (good for weighting the deform bones one by one)'),
                            ('SCRUB',    'Pose & Weight'  , 'Prepare the Panels for Posing and Weighting (good for using an animation to test the weights)'),
                            ('POSE',     'Pose & Animate' , 'Prepare the Panels for posing & Animating (good for creating poses and Animations'),
                            ('FIT',      'Fitted Mesh'    , 'Prepare the Panels for Fitted Mesh (good for weighting with Fittedt mesh Bones)'),
                            ('RETARGET', 'Motion Transfer', 'Prepare the Panels for Motion Transfer (Retarget, transform Animations from foreign Rigs to Avastar)'),
                            ('EDIT',     'Edit Joints'    , 'Prepare the Panels for Editing Bone locations (Create Joint Edits to reuse the SL Skeleton for Cratures)'),
                          ),
                   )

    skill_level : EnumProperty(
                    name = "Skill Levels",
                    items=(
                            ('BASIC',    'Basic Features' , 'Show only Basic features'),
                            ('EXPERT',   'Expert'         , 'Show features for experts'),
                            ('ALL',      'All Features'   , 'Show all Features (includes experimental usage)'),
                            ('AUTO',     'Workflow'       , 'Show features needed for selected workflow'),
                          ),
                   )

    snap_control_to_rig : const.g_snap_control_to_rig
    store_as_bind_pose : const.g_store_as_bind_pose

    list_baked_objects : BoolProperty(
        name="Show Objects",
        default=False,
        description='Show objects for which the bake tool will generate baked textures'
    )

    baked_image_width : IntProperty(name="Texture Width", description="Image width for automatically baked textures", default = 128)
    baked_image_height : IntProperty(name="Texture Height", description="Image width for automatically baked textures", default = 128)
    with_image_bake : BoolProperty(
                   name = "Create Baked textures",
                   default = False,
                   description = "Bake Materials into Textures\n"
                               + "\n"
                               + "\n"
                               + "CAUTION: This option can take a very long time\n"
                               + "- in the order of minutes - when used the first time\n"
                               + "Hower, Avastar uses a cache here, hence follow up exports\n"
                               + "are performed significantly faster\n"
                   )
    force_rebake : BoolProperty(
                    name = "Force Rebake",
                    default = False,
                    description = "Enforce Texture rebake\n"
                                + "\n"
                                + "\n"
                                + "Make sure all baked textures are recreated before export\n"
                                + "CAUTION: This option can take a very long time\n"
                                + "- in the order of minutes - when enabled\n"
                   )

    armature_suppress_auto_bone_fixes : BoolProperty(
        name = "Suppress Bone Fixes",
        default = False
    )

    armature_suppress_all_handlers : BoolProperty(
        name = "Suppress Handlers",
        default = False
    )

    armature_suppress_update_shape : BoolProperty(
        name = "Suppress Shape Update",
        default = False
    )

    apply_as_bindshape : g_apply_as_bindshape


class MeshPropGroup(bpy.types.PropertyGroup):

    weightCopyAlgorithm : EnumProperty(
        items=weightCopyAlgorithmsCallback,
        name="Algorithm",
        description="Used Mirror Algoritm for mirror weight copy"
    )

    handleOriginalMeshSelection : EnumProperty(
        items=(
            ('KEEP',   'Keep', 'Keep both Meshes'),
            ('HIDE',   'Hide', 'Hide Original mesh'),
            ('DELETE', 'Delete', 'Delete original mesh')),
        name="Original",
        description="How to proceed with the Original Mesh after freeze",
        default='DELETE')

    hideOriginalMesh   : BoolProperty(
        default=False,
        name="Hide Original Mesh")

    deleteOriginalMesh : BoolProperty(
        default=False,
        name="Delete Original Mesh")

    handleBakeRestPoseSelection : EnumProperty(
        items=(
            ('SELECTED','Selected', 'Bake selected Bones'),
            ('VISIBLE', 'Visible',  'Bake visible Bones'),
            ('ALL',     'All',      'Bake all Bones')),
        name="Scope",
        description="Which bones are affected by the Bake",
        default='SELECTED')

    standalonePosed : BoolProperty(
        default=False,
        name="as static Mesh",
        description="Create a static copy in the current posture, not parented to armature")

    removeWeights : BoolProperty(
        default=False,
        name="Remove Weight Groups",
        description="Remove all vertex groups from the copy")

    removeArmature : BoolProperty(
        default=False,
        name="Remove Armature",
        description="Remove the Armature and all its attached Children.\nThis is helpful when you want to keep only the frozen Object\nand use it as a static not rigged Mesh")

    joinParts : BoolProperty(
        default=False,
        name="Join Parts",
        description="Join all selected parts into one singlemesh object')")

    removeDoubles : BoolProperty(
        default=False,name="Weld Parts",
        description="Remove duplicate verts from adjacent edges of joined parts")

    toTPose : BoolProperty(
        default=False,
        name="Alter to Rest Pose (deprecated)",
        description="Alter selected meshes into the Armature's rest pose.\n\n"\
                   +"Special Notes:\n"\
                   +"* This feature is disabled when the selected Meshes contain Shape Keys!\n"\
                   +"* CAUTION: Your mesh models will be permanently modified!")

    submeshInterpolation : weights.g_submeshInterpolation

    exportArmature : BoolProperty(
        default=True,
        name="Include joint positions",
        description="Use if modifying the bone locations. You need to import them in the viewer also to have an effect")

    exportOnlyActiveUVLayer : BoolProperty(
        default=True,
        name="Only Active UV layer",
        description="Default: export all UV Layers. if set, only export the active UV Layer"
    )

    exportCopy : BoolProperty(
        default=True,
        name="Copy",
        description="Copy textures to the same folder where the .dae file is exported")

    exportTextures : BoolProperty(
        default=True,
        name="Export with Textures",
        description="Export textures along with the .dae file")

    exportDeformerShape : BoolProperty(
        default=False,
        name="Include Deformer Shape",
        description="Mesh Deformer support(experimental):\n"\
                   +"Export the Normalized version of the current Shape as XML.\n"\
                   +"Use this XML file for your custom Mesh deformer upload")

    apply_armature_scale : BoolProperty(
        default=True,name="Apply Armature Scale",
        description="Apply the armature's object Scale to the Animation channels\n\n"\
                   +"Enable this option when your armature is scaled in Object mode\n"\
                   +"and your animation contains translation components.\n"\
                   +"Then Scale is applied on the fly (only for the export)\n\n"\
                   +"Typically needed when Armature is scaled in Object mode to create tinies or giants")

    apply_mesh_rotscale : BoolProperty(
        default=True,
        name="Apply Rotation & scale",
        description="Apply the Mesh object's Rotation & Scale, should always be used")

    weld_normals : BoolProperty(
        default=True,
        name="Weld Edge Normals",
        description="Adjust normals at matching object boundaries (to avoid visual seams)")

    weld_to_all_visible : BoolProperty(
        default=False,
        name="Weld to all visible",
        description="If enabled, then take all visible mesh objects into account for welding the normals, otherwise weld only with selected objects" 
        )

    export_triangles : BoolProperty(
        default=False,
        name="Triangulate",
        description= "Triangulate before exporting\n\n"
                   + "Note:\n"
                   + "The SL Importer will triangulate anyways.\n"
                   + "But we found that when we triangulate on export\n"
                   + "then we can avoid odd issues with the SL uploaded\n"
                   + "mostly to avoid 'missing LOD levels' during import to SL"
    )

    max_weight_per_vertex : IntProperty(
        name="Limit weight count",
        default = 4,
        min     = 0,
        description="Define how many weights are allowed per vertex (set to 0 to allow arbitrary weight count)")


    apply_modifier_stack : BoolProperty(
        default=True,
        name="Apply Modifiers",
        description="Apply all Modifiers before export"
    )

    selectedBonesOnly : BoolProperty(
        default=False,
        name="Restrict to same Bones",
        description="Copy only those weights from other Meshes, which are assigned to the selected Bones")

    mirrorWeights : BoolProperty(
        default=False,
        name="Mirror from opposite Bones",
        description="Copy weights from Bones opposite to selection (merge with current weights!)")

    allBoneConstraints : BoolProperty(
        default=False,
        name="Set All",
        description="Set all bone constraints of skeleton")

    adjustPoleAngle : BoolProperty(
        default=True,
        name="Sync Pole Angles",
        description="Automatically adjust pole angles of IK Pole Targets when entering Pose Mode")

    weightCopyType : EnumProperty(
        items=(
            ('ATTACHMENT', "from Attachments", 'Copy bone weights from same bones of other attachments'),
            ('MIRROR', 'froom Opposite Bones', 'Copy bone Weights from opposite bones of same object'),
            ('BONES', 'selected to active', 'Copy bone weights from selected bone to active bone (needs exactly 2 selected bones) ')),
        name="Copy",
        description="Method for Bone Weight transfer",
        default='ATTACHMENT')

    useBlenderTopologyMirror : BoolProperty(
        default=False,
        name="Use Topology Mirror",
        description="Use Blender's Topology weight mirror copy. Caution: Does only work when mesh is NOT symmetric (handle with care)!!!")

    weight_type_selection : EnumProperty(
        items=(
            ('NONE',        "No weights", 'Create with empty Vertex groups'),
            ('COPYWEIGHTS', 'Copy weights', 'Copy weights from all visible armature children'),
            ('AUTOMATIC',   'Automatic weights', 'Calculate weights from Bones'),
            ('ENVELOPES',   'Envelope weights', 'Calculate weights from Bone envelopes')),
        name="Weighting",
        description="Method to be used for creatin initial weights",
        default='NONE')

    deform_type_selection : EnumProperty(
        items=(
            ('BONES', "Deform", 'Only edit weight Groups used for Pose bones'),
            ('OTHER', 'Other', 'Only edit weight Groups used for non pose bones'),
            ('ALL',   'All', 'Edit all weight Groups')),
        name="Subset",
        description="Selection depending on usage of the Weight Groups",
        default='ALL')

    save_shape_selection : g_save_shape_selection 

    weight_mapping : g_weight_mapping
    weightSourceSelection : g_weightSourceSelection
    bindSourceSelection : g_bindSourceSelection
    weightBoneSelection : g_weightBoneSelection
        
    use_mirror_x : weights.g_use_mirror_x
    clearTargetWeights : weights.g_clearTargetWeights
    copyWeightsToSelectedVerts : weights.g_copyWeightsToSelectedVerts
    keep_groups : weights.g_keep_groups
    with_hidden_avastar_meshes : weights.g_with_hidden_avastar_meshes
    with_listed_avastar_meshes : weights.g_with_listed_avastar_meshes

    attachSliders : BoolProperty(
        name="Attach Sliders",
        default=True,
        description="Attach the Avatar shape after binding"
        )

    enable_unsupported : BoolProperty(
        name="Attach Sliders",
        default=True,
        description="Attach the Avatar shape after binding")
        

    all_selected : BoolProperty(
        name = "Apply to Selected",
        default = False, 
        description = "Apply this Operator to all selected Objects\n\n"\
                    + "If this property is disabled, apply only to active Object"
        )

    generate_weights : BoolProperty(
        default=False,
        name="Generate Weights",
        description="For Fitted Mesh: Create weights 'automatic from bone' for BUTT, HANDLES, PECS and BACK")

    butt_strength   : FloatProperty(name = "Butt Strength",   min = 0.0, max = 1.0, default = 0.5)
    pec_strength    : FloatProperty(name = "Pec Strength",    min = 0.0, max = 1.0, default = 0.5)
    back_strength   : FloatProperty(name = "Back Strength",   min = 0.0, max = 1.0, default = 0.5)
    handle_strength : FloatProperty(name = "Handle Strength", min = 0.0, max = 1.0, default = 0.5)

    with_hair : weights.g_with_hair
    with_eyelashes : weights.g_with_eyelashes
    with_head : weights.g_with_head
    with_eyes : weights.g_with_eyes
    with_upper_body : weights.g_with_upper_body
    with_lower_body : weights.g_with_lower_body
    with_skirt : weights.g_with_skirt

    copy_pose_begin : IntProperty(
        default=0,
        min=0,
        name="Begin",
        description="First source frame for a timeline copy")

    copy_pose_end : IntProperty(
        default=0,
        min=0,
        name="End",
        description="Last source frame for a timeline copy")

    copy_pose_to : IntProperty(
        default=0,
        min=0,
        name="To",
        description="First target frame for a timeline copy")

    copy_pose_loop_at_end : BoolProperty(
        default=False,
        name="Create endframe",
        description="Terminate target range with copy of first source frame (only if first source frame has keyframes)")

    copy_pose_loop_at_start : BoolProperty(\
        default=False,
        name="Create startframe",
        description="Generate keyframes for first source key (if it has no keyframes yet)")

    copy_pose_clean_target_range : BoolProperty(
        default=False,
        name="Replace",
        description="Cleanup target range before copy (removes keyframes)")

    copy_pose_x_mirror : BoolProperty(
        default=False,
        name="x-mirror",
        description="Does an x-mirror copy (for walk cycles)")

    apply_shrinkwrap_to_mesh : BoolProperty(
        default=True,
        name="Apply Shrinkwrap",
        description="Apply Shrinkwrap modifier while Baking Shape to Mesh")

    auto_refresh_mesh_stat : BoolProperty(
        default = False,
        name = "Auto Refresh Mesh Stat",
        description = "Keep the mesh statistic always up to date.\n"\
                    + "Important: This can slow down the user interface significantly\n"\
                    + "depending on the size of the Selected meshes.\n"\
                    + "Please handle with care!"
    )


    auto_rebind_mesh : BoolProperty(
        name = "Automatic Rebind",
        description = "Automatic Rebind after Editing a mesh\n\n"
                    + "Note: When this option is enabled and when you work\n"
                    + "with High Polygon Meshes, then switching from\n"
                    + "Edit mode to Object mode may take a long time.\n\n"
                    + "However, when you disable this option then you need\n"
                    + "to take care by yourself to Rebind after Editing",
        default = True
    )


def gender_update_handler(self, context):

    if util.is_gender_update_in_progress():
        return

    obj = context.object
    if obj.type == 'ARMATURE':
        armobj = obj
    else:
        armobj = obj.find_armature()
    gender_shape_set(armobj, self.gender=='MALE')


def gender_update(armobj, use_male_shape, disable_handler=False):

    if disable_handler:
        update_in_progress = util.is_gender_update_in_progress()
        if not update_in_progress:
            util.set_gender_update_in_progress(True)

    armobj.RigProp.gender = 'MALE' if use_male_shape else 'FEMALE'

    if disable_handler:
        util.set_gender_update_in_progress(update_in_progress)

def gender_shape_set(armobj, use_male_shape):
    if armobj.ShapeDrivers.male_80 == use_male_shape or util.is_gender_update_in_progress():
        return

    util.set_gender_update_in_progress(True)
    armobj.ShapeDrivers.male_80 = use_male_shape
    util.set_gender_update_in_progress(False)
 

class RigPropGroup(bpy.types.PropertyGroup):    
    IKHandInfluenceLeft  : FloatProperty(name="Left Hand IK Combined", 
                           default=0.0,
                           min=0.0,
                           max=1.0,
                           update=update_sync_influence_left,
                           description="Combined Influence for all IK Controllers of the Left Hand"
                           )
                           
    IKHandInfluenceRight : FloatProperty(name="Right Hand IK Combined",
                           default=0.0,
                           min=0.0,
                           max=1.0,
                           update=update_sync_influence_right,
                           description="Combined Influence for all IK Controllers of the Right Hand"
                           )


    constraintItems = [
                ('SELECTION', 'Selected Bones', 'The Selected Pose Bones'),
                ('VISIBLE',   'Visible Bones',  'All Visible Pose Bones'),
                ('SIMILAR',   'Same Group',  'All Pose Bones in same Group'),
                ('ALL'    ,   'All Bones',      'All Pose Bones'),
    ]


    JointTypeItems = GJointTypeItems

    ConstraintSet   : EnumProperty(
        items       = constraintItems,
        name        = "Set",
        description = "Affected Bone Set",
        default     = 'SELECTION')

    handitems = []

    HANDS = shape.HANDS

    for key in range(len(HANDS.keys())):
        handitems.append((str(HANDS[key]['id']),HANDS[key]['label'],HANDS[key]['label'] ))

    Hand_Posture : EnumProperty( items=handitems, name='Hands', default=HAND_POSTURE_DEFAULT,
            update=update_animation, description="Hand posture to use in the animation" )

    RigType : EnumProperty(
        items       = RigTypeItems,
        name        = "Rig Type",
        description = "Basic: Old Avatar Skeleton, Extended: Bento Bones",
        default     = 'BASIC')
    
    JointType : GJointType
    
    affect_all_joints : BoolProperty(
               name    = "All Joints",
               default = True,
               description = "Affect all bones.\nWhen this option is cleared then only selected bones are affected",
               update      = update_affect_all_joints
               )

    keep_edit_joints : BoolProperty(
               name    = "Keep",
               default = True,
               description = RigProp_keep_edit_joints_description
               )
    restpose_mode : BoolProperty(
               name    = "SL Restpose mode",
               default = False,
               description = RigProp_restpose_mode_description
               )
    
    export_pose_reset_anim : BoolProperty(
        default     = False,
        name        = "with Reset Animation",
        description = RigProp_rig_export_pose_reset_anim
        )

    export_pose_reset_script : BoolProperty(
        default     = False,
        name        = "with Reset Script",
        description = RigProp_rig_export_pose_reset_script
        )

    rig_use_bind_pose : BoolProperty(
        default=False,
        name        = "Use Bind Pose",
        update      = update_rig_pose_type,
        description = RigProp_rig_use_bind_pose_description
        )

    rig_lock_scales : BoolProperty(
        default     = False,
        name        = "Lock Scales",
        update      = update_rig_lock_scale,
        description = RigProp_rig_lock_scales
        )

    rig_export_in_sl_restpose : BoolProperty(
        default     = False,
        name        = "Animesh Restpose",
        description = RigProp_rig_rig_export_in_sl_restpose
        )

    rig_export_visual_matrix : BoolProperty(
        default=True,
        name        = "Export Visual",
        description = RigProp_rig_export_visual_matrix_description
        )


    def make_gender_items(self, context):
        gender_items = [
                ('FEMALE', 'Female', 'Female', get_icon("female"), 0),
                ('MALE',   'Male',  'Male', get_icon("male"), 1),
        ]
        return gender_items


    gender   : EnumProperty(
        items       = make_gender_items,
        name        = "Gender",
        description = "Avatar Gender (Female or Male)",

        update = gender_update_handler
        )


    display_joint_heads : BoolProperty (
               default = True,
               name = "Heads",
               description = "List the Bones with modified Bone head location (Joint offsets)"
               )
    
    display_joint_tails : BoolProperty (
               default = False,
               name = "Tails",
               description = "List the Bones with modified Bone tail location (Bone ends)"
               )
    
    generate_joint_tails : BoolProperty (
               default = True,
               name = "Generate Tail Offsets",
               description = "Generate Joint entries also for Bone tails\nYou want to keep this enabled! (experts only)"
               )
    
    generate_joint_ik : BoolProperty (
               default = False,
               name = "Generate IK Offsets",
               description = "Generate Joint Offsets for the IK Joints\nMake IK Bones react on Sliders (experimental)"
               )
    
    display_joint_values : BoolProperty (
               default = False,
               name    = "Values [mm]",
               description = RigProp_display_joint_values_description
               )

    displaytypes = [
       ('OCTAHEDRAL', "Octahedral",  "Display bones as Octahedral shapes"),
       ('STICK',      "Stick", "Display Bones as Sticks")
    ]

    display_type : EnumProperty(
        items       = displaytypes,
        name        = "Display Type",
        description = "Set the Bone Display Type for this Rig",

        options     = {'ANIMATABLE', 'ENUM_FLAG'},
        update      = update_bone_type)
    
    spine_is_visible : BoolProperty (
               default = False,
               name    = "Use Spine Bones",
               description = msg_RigProp_spine_is_visible,
               update = rig.update_spine_hiding
               )

    spine_is_enabled : BoolProperty (
               default = True,
               name    = "Use Spine Bones",
               description = "Enable usage of Bento Spine bones (mSpine1, mSpine2, mSPine3, mSpine4)",
               update = rig.update_spine_folding
               )

    spine_unfold_upper : BoolProperty (
               default = False,
               name    = "Unfold Upper",
               description = \
'''Unfold Spine3 and Spine4 (the upper spine connecting torso with chest)

Notes:

- Unfolding the bones will make them deform bones
- Red Button indicates only one of the bones is marked as deform''',
               update = rig.update_spine_folding
               )

    spine_unfold_lower : BoolProperty (
               default = False,
               name    = "Unfold Lower",
               description = \
'''Unfold Spine1 and Spine2 (the lower spine)

Notes:

- Unfolding the bones will make them deform bones
- Red Button indicates only one of the bones is marked as deform''',
               update = rig.update_spine_folding
               )

    spine_hide_upper : BoolProperty (
               default = False,
               name    = "Hide Upper",
               description = "Hide the Spine3,Spine4 Bones (the upper spine connecting torso with chest)",
               update = rig.update_spine_hiding
               )

    spine_hide_lower : BoolProperty (
               default = False,
               name    = "Hide Lower",
               description = "Hide the Spine1,Spine2 Bones (the lower spine connecting Pelvis with Torso)",
               update = rig.update_spine_hiding
               )

    eye_configurations = [
       ('BASIC', "Basic Eyes",  "Show only Basic Eye Bones mEyeLeft and mEyeRight"),
       ('EXTENDED', "Extended Eyes", "Show only Extended Eye Bones mFaceEyeAltLeft and mFaceEyeAltRight"),
       ('BOTH',   "Basic&Extended", "Show both Sets of Eye Bones (Basic and Extended)")
    ]

    eye_setup : EnumProperty (
            items = eye_configurations,
            update = rig.update_eye_configuration
    )

    hip_compatibility :  BoolProperty (
               default = False,
               name    = "Hip Compatibility",
               description = messages.RigProp_hip_compatibility,
               update = rig.update_hip_compatibility
               )

    up_axis : g_up_axis
    reset_shape_sliders : g_reset_shape_sliders

    add_missing_bones : BoolProperty (
               default = True,
               name    = "Add Missing Bones",
               description = "Add missing bones when switching to Extended Rig"
               )

    bind_hover : FloatProperty(
        name = "bind_hover",
        description="Hover value during bind",
        default = 0
    )

    rig_appearance_enabled : BoolProperty(
                     name = "Enable Avatar Shape",
                     default = True
                     )

    rig_appearance_editable : BoolProperty(
                     name = "Lock Avatar Shape",
                     default = True,
                     description= "Used to lock the Avatar shape in their current state.\n\n"\
                                + "Note:\n"
                                + "When you select the Animesh Preset (White Stickman)\n"
                                + "the Avatar shape are automatically locked\n"
                                + "However you always can unlock even when you selected Animesh mode"
                     )


class UpdateRigPropGroup(bpy.types.PropertyGroup):
    transferMeshes : BoolProperty(
        name = "Transfer Meshes",
        default = False,
        description = "Migrate Child Meshes from Source armature to target Armature"
    )

    transferJoints : BoolProperty(
        name = "Transfer Joints",
        default=True,
        description = messages.UpdateRigProp_transferJoints_text,
    )

    attachSliders : BoolProperty(default=True, name="Attach Sliders",
        description="Attach the Avatar shape after binding")

    applyRotation : const.g_applyRotation
    use_male_shape : const.g_use_male_shape
    use_male_skeleton : const.g_use_male_skeleton
    
    srcRigType : const.g_srcRigType
    tgtRigType : const.g_tgtRigType
    up_axis : g_up_axis
    handleTargetMeshSelection : g_handleTargetMeshSelection
    apply_pose : g_apply_pose

    base_to_rig     : BoolProperty(
        name="Reverse Snap",
        description = "Reverse the snapping direction: Adjust the Rig bones to the Base bones",
        default     = False
    )

    adjust_origin : EnumProperty(
        items=(
            ('ROOT_TO_ORIGIN',   'Armature', 'Move the Root Bone to the Armature Origin Location.\nThe location of the Armature in the scene is not affected'),
            ('ORIGIN_TO_ROOT',   'Rootbone', 'Move the Armature Origin Location to the Root Bone.\nThe location of the Armature in the scene is not affected')
        ),
        name="Origin",
        description="Matches the Avastar Root Bone with the Avastar Origin location.\nThis must be done to keep the Sliders working correct",
        default='ORIGIN_TO_ROOT'
    )


    structure_repair: BoolProperty(
        name        = "Adjust Structure bones",
        description = "Automatically adjust structure bone locations.\n"\
                    + "Please disable this option when your rig uses\n"\
                    + "the hand bones for other purposes or when the\n"\
                    + "Hand bones have been rearranged to non human hands",
        default     = True
    )


    bone_repair     : BoolProperty(
        name        = "Rebuild missing Bones",
        description = "Reconstruct all missing bones.\n"\
                    + "This applies when bones have been removed from the original rig\n\n"\
                    + "IMPORTANT: when you convert a Basic Rig to an Extended Rig\n"\
                    + "then you should enable this option\n"\
                    + "Otherwise the extended (Bento) bones are not generated",
        default     = False
    )

    adjust_pelvis   : BoolProperty(
        name        = "Adjust Pelvis",
        description = UpdateRigProp_adjust_pelvis_description,
        default     = True
    )

    adjust_rig   : BoolProperty(
        name        = "Synchronize Rig",
        description = UpdateRigProp_adjust_rig_description,
        default     = True
    )

    mesh_repair     : BoolProperty(
        name        = "Rebuild Avastar Meshes",
        description = "Reconstruct all missing Avastar Meshes.\nThis applies when Avastar meshes have been removed from the original rig\n\nCAUTION: If your character has modified joints then the regenerated Avastar meshes may become distorted!",
        default     = False
    )

    show_offsets      : BoolProperty(
        name="Show Offsets",
        description = "Draw the offset vectors by using the Grease pencil.\nThe line colors are derived from the related Avastar Bone group colors\nThis option is only good for testing when something goes wrong during the conversion",
        default     = False
    )

    sl_bone_ends : BoolProperty(
        name="Enforce SL Bone ends",
        description = "Ensure that the bone ends are defined according to the SL Skeleton Specification.\nYou probably need this when you import a Collada devkit\nbecause Collada does not maintain Bone ends (tricky thing)\n\nHint: \nDisable this option\n- when you transfer a non human character\n- or when you know you want to use Joint Positions",
        default     = True
    )
    sl_bone_rolls : const.sl_bone_rolls

    align_to_deform : EnumProperty(
        items=(
            ('DEFORM_TO_ANIMATION', 'Pelvis', 'Move mPelvis to Pelvis'),
            ('ANIMATION_TO_DEFORM', 'mPelvis', 'Move Pelvis to mPelvis')
        ),
        name="Align to",
        description = UpdateRigProp_align_to_deform_description,
        default='ANIMATION_TO_DEFORM'
    )

    align_to_rig : EnumProperty(
        items=(
            ('DEFORM_TO_ANIMATION', 'Green Animation Rig', 'Move Deform Bones to Animation Bone locations'),
            ('ANIMATION_TO_DEFORM', 'Blue Deform Rig', 'Move Animation Bones to Deform Bone Locations')
        ),
        name="Align to",
        description = UpdateRigProp_align_to_rig_description,
        default='ANIMATION_TO_DEFORM'
    )

    snap_collision_volumes : BoolProperty(
        name        = "Snap Volume Bones",
        description = UpdateRigProp_snap_collision_volumes_description,
        default     = True
    )

    snap_attachment_points : BoolProperty(
        name        = "Snap Attachment Bones",
        description = UpdateRigProp_snap_attachment_points_description,
        default     = True
    )
    
    fix_reference_meshes : BoolProperty(
        name        = "Fix Reference meshes",
        description = UpdateRigProp_fix_reference_meshes_description,
        default     = True
    )

    preserve_bone_colors : BoolProperty(
        name        = "Preserve Bone Colors",
        description = UpdateRigProp_preserve_bone_colors_description,
        default     = True
    )

    devkit_use_sl_head : BoolProperty(
        name        = "Headless devkit",
        description = "Developer kit has no head defined.\nEnable when you want to reuse the Default SL Head",
        default     = True
    )
    
    devkit_use_bind_pose : BoolProperty(
        default=False,
        name        = "Use Bind Pose",
        description = RigProp_rig_use_bind_pose_description
        )
        
    devkit_filepath : StringProperty(
        name = "Path to Kit",
        subtype = 'FILE_PATH',
        description = UpdateRigProp_devkit_filepath
    )

    devkit_shapepath : StringProperty(
        name = "Path to shapefile",
        subtype = 'FILE_PATH',
        description = UpdateRigProp_devkit_shapepath
    )

    devkit_snail : StringProperty(
        name = "Model",
        description = "Short name for your Developer kit character",
        update = check_unique_snail_callback,
        default = "")

    devkit_brand : StringProperty(
        name = "Brand",
        description = "The Brand of the Developer kit (optional)",
        default = "")

    devkit_scale : FloatProperty(
        name = "Scale",
        description="Scale Factor typically this is either 0.01, 1.0 or 100 for Maya and 3DS",
        min=0.000001,
        default = 1.0
    )

    devkit_replace_import :  BoolProperty(
        default=False,
        name        = "Replace",
        description = '''Allow replacing existing configurations:

Explain: If the imported file contains a configuration
that already exists in your setup, then allow Avastar
to replace your configuration by the one imported from file'''
        )

    devkit_replace_export :  BoolProperty(
        default=False,
        name        = "Replace",
        description = '''Allow replacing existing configuration file

Explain: If the destination file already exists,
then allow Avastar to replace the content of the file
by your exported Configuration'''
        )

    JointType : GJointType
    tgtJointType : GJointType

@persistent
def update_rebake_settings(self, context):
    for obj in context.selected_objects:
        missing_image_names = mesh.BakeMaterialsOperator.object_material_bake_image_names(context, obj)
        obj.ObjectProp.has_baked_materials = len(missing_image_names) == 0

class BakerPropGroup(bpy.types.PropertyGroup):
    rebake : BoolProperty(
        default = False,
        name = "Rebake Materials",
        description = "Mark the material for rebaking its textures",
        update = update_rebake_settings
    )


is_locked=False
def type_changed(self, context):
    global is_locked
    if is_locked:
        return
    is_locked=True

    set_avastar_materials(context)

    is_locked=False


class MaterialPropGroup(bpy.types.PropertyGroup):

    material_types = [
            ('NONE',     'None',     'Default Material'),
            ('FEMALE',   'Female',   'Female Materials'),
            ('MALE',     'Male',     'Male Materials'),
            ('CUSTOM',   'Custom',   'Custom Materials'),
            ('TEMPLATE', 'Template', 'Template Materials'),
            ]

    material_type : EnumProperty(
        items       = material_types,
        name        = 'type',
        description = 'Material type',
        default     = 'NONE',
        update      = type_changed
    )

    unique : BoolProperty(
             name        = "unique",
             default     = False,
             description = "Make material unique",
             update      = type_changed)

def rig_display_type_items(self, context):
    items = [
            ('SL',     'SL' , 'Display all deforming SL Base Bones defined for this Skeleton'),
            ('EXT', 'Ext', 'Display all deforming SL Extended Bones defined for this Skeleton (Hands, Face, Wings, Tail)'),
            ('VOL',    'Vol', 'Display all deforming Collision Volumes defined for this Skeleton (Fitted mesh)'),
            ('POS', 'Joint', 'Display bones having Joint Offsets\n\nNote: Joint offsets are defined by modifying the Skeleton in edit mode\nPlease remember to set the joint positions:\n\nAvastar -> Rigging Panel\nConfig Section\nJointpos Settings -> Store Joint Pos'),
            ('MAP', 'Map', 'Display all Weighted Deforming Bones used by the current selection of Mesh Objects\nNote: There may be a small delay of ~1 second before the filter applies')
            ]
    return items


class ObjectPropGroup(bpy.types.PropertyGroup):

    slider_selector : EnumProperty(
        items=slider_options,
        name="Slider Type",
        description="How to use Sliders"
        )

    rig_display_type : EnumProperty(
        items   = rig_display_type_items,
        name    = "Display Type",
        update  = bind.configure_rig_display,
        description="Deform Bone Display Filter"
        )

    filter_deform_bones : BoolProperty(
        default=False,
        update      = bind.configure_rig_display,
        name        ="Filter Deform Bones",
        description ="Display only the deforming Bones from selected Group:\n\nSL  : SL Base Skeleton\nVol : Collision Volume Bones\nExt: SL Extended Skeleton\nPos: Bones which have stored Joint offsets \nMap: Bones weighted to one or more Meshes of the current selection"
        )








    edge_display   : BoolProperty(
       default     = False,
       update      = bind.configure_edge_display,
       name        = "Edge Display",
       description = "Enable visibility of edges in Object Mode and Weight Paint Mode"
    )

    apply_armature_on_unbind : g_apply_armature_on_unbind 

    purge_data_on_unbind : mesh.g_purge_data_on_unbind

    apply_armature_on_snap_rig : BoolProperty(
       default     = True,
       name        = "Apply Pose to Mesh",
       description = ObjectProp_apply_armature_on_snap_rig_description
    )

    apply_only_to_visible : BoolProperty(
        default = False,
        name="Only Visible Meshes",
        description='''enabled: Apply only to visible Meshes.\nDisabled: apply to all bound meshes'''
    )

    apply_to_avastar_meshes : BoolProperty(
        default = True,
        name="Also Avastar Meshes",
        description='''enabled: Apply also to Avastar Meshes.\nDisabled: apply only to Custom Meshes'''
    )

    break_parenting_on_unbind : g_break_parenting_on_unbind

    fitting : BoolProperty(
        default = False,
        name = "Allow Fitting",
        description = "Allow the Fitting Sliders to be used for this Mesh\n"\
                    + "Warning: To use fitting Sliders on meshes we must \n"\
                    + "reset the weightmaps of the Collision Volumes.\n"\
                    + "Pre existing Collision Volume Weights will be removed!"
    )

    has_baked_materials: BoolProperty(
        default = False,
        name = "Baked Materials",
        description = "All Materials used by object have baked textures"
    )

    def update_is_hidden(self, context):
        armobj = util.get_armature_from_context(context)
        childset = util.get_animated_meshes(context, armobj, only_visible=False)
        for child in [child for child in childset if child.ObjectProp == self and child!=context.object]:
            child.hide_set(child.ObjectProp.is_hidden)

    is_hidden: BoolProperty(
        update = update_is_hidden,
        default = False,
        name = "Hide",
        description = "hide this object from current operation.\n\n"\
                    + "Note: Hiding the object lets the tool behave\n"\
                    + "as if the object would not exist at all.\n"\
                    + "This has an impact on the result!"
    )


    is_selected: BoolProperty(
        default = False,
        name = "Select",
        description = "Include Data from this Object.\n\n"\
                    + "Note: Data from all selected Objects is combined"
    )

    frozen_name: StringProperty(
        name = "Name",
        description = "Set name for frozen Object"
    )

class SparkleTimelinePropGroup(bpy.types.PropertyGroup):

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


def eyeTargetConstraintCallback(self, context):
    obj = context.object
    arm = util.get_armature(obj)
    if arm:
        rig.setEyeTargetInfluence(arm, 'Eye')

def altEyeTargetConstraintCallback(self, context):
    obj = context.object
    arm = util.get_armature(obj)
    if arm:
        rig.setEyeTargetInfluence(arm, 'FaceEyeAlt')

def set_hand_fk_contraints_status(pbones, part, symmetry, mute):

    for index in range (1,4):
        name = "Hand%s%d%s" % (part,index,symmetry)

        pbone = pbones[name] if name in pbones else None
        if pbone:
            for con in pbone.constraints:
               if con.type in ["LIMIT_ROTATION", "COPY_ROTATION"]:
                   con.mute=mute

def update_hand_ik_type(self, context):
    try:
        state = self.Enable_Hands

        active = context.active_object
        arm    = util.get_armature(active)
        pbones = arm.pose.bones

        for part in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:

            for symmetry in ["Right","Left"]:

                bone_name = "ik%sSolver%s" % (part,symmetry)
                solver    = pbones.get(bone_name)
                if state in ['NONE', 'FK']:
                    arm.data.layers[B_LAYER_IK_HAND] = False
                    set_hand_fk_contraints_status(pbones, part, symmetry, mute = state == 'NONE')
                    if solver:
                        solver.constraints['Grab'].mute = True
                        if part in ["Thumb", "Index"]:
                            solver.constraints['Pinch'].mute = True
                else:
                    arm.data.layers[B_LAYER_IK_HAND] = True
                    set_hand_fk_contraints_status(pbones, part, symmetry, mute=True)
                    if solver:
                        solver.constraints['Grab'].mute = False
                        if part in ["Thumb", "Index"]:
                            solver.constraints['Pinch'].mute = False
    except:
        pass # probably no Hand ik defined for this rig

class IKSwitchesPropGroup(bpy.types.PropertyGroup):
    Show_All : BoolProperty(name = "Show all controls", default = False)
    Enable_Face : BoolProperty(name = "Enable Face Controllers", default = False)
    Enable_Limbs : BoolProperty(name = "Enable IK Limbs", default = False)
    Enable_Legs : BoolProperty(name = "Enable IK Legs", default = False)
    Enable_Arms : BoolProperty(name = "Enable IK Arms", default = False)
    Enable_Eyes : BoolProperty(name = "Enable Eyes",
                  default = False,
                  update=eyeTargetConstraintCallback,
                  description = "Let the eyes follow the eye target when enabled"
    )

    Enable_AltEyes : BoolProperty(name = "Enable Alt Eyes",
                  default = False,
                  update=altEyeTargetConstraintCallback,
                  description = "Let the Alt Eyes eyes follow the Alt Eye target when enabled"
    )

    hand_ik_type = [
        ('NONE', 'Simple Fingers', 'Use the simple finger Rig, fingers can be freely rotated'),
        ('FK', 'Constrained Fingers', 'Use the constrained finger Rig, fingers can only be rotated like human fingers'),
        ('GRAB', 'Hand Grab (IK)', 'Use the hand Grab IK Rig, (in preparation)')
        ]
    Enable_Hands : EnumProperty(items=hand_ik_type, name = "Enable IK Hands", default = 'NONE', update=update_hand_ik_type)

    IK_Wrist_Hinge_L : FloatProperty(name = "Left Wrist", min = 0.0, max = 1.0, default = 1.0)
    IK_Wrist_Hinge_R : FloatProperty(name = "Right Wrist", min = 0.0, max = 1.0, default = 1.0)

    IK_Ankle_Hinge_L : FloatProperty(name = "Left Ankle", min = 0.0, max = 1.0, default = 1.0)
    IK_Ankle_Hinge_R : FloatProperty(name = "Right Ankle", min = 0.0, max = 1.0, default = 1.0)
    IK_Foot_Pivot_L  : FloatProperty(name = "Left Foot Pivot", min = -0.4, max = 1.0, default = 0.0, update=shape.pivotLeftUpdate)
    IK_Foot_Pivot_R  : FloatProperty(name = "Right Foot Pivot", min = -0.4, max = 1.0, default = 0.0, update=shape.pivotRightUpdate)

    IK_HindLimb3_Hinge_L : FloatProperty(name = "Left Hind Ankle", min = 0.0, max = 1.0, default = 1.0)
    IK_HindLimb3_Hinge_R : FloatProperty(name = "Right Hind Ankle", min = 0.0, max = 1.0, default = 1.0)
    IK_HindLimb3_Pivot_L : FloatProperty(name = "Left Hind Foot Pivot", min = -0.4, max = 1.0, default = 0.0, update=shape.pivotLeftUpdate)
    IK_HindLimb3_Pivot_R : FloatProperty(name = "Right Hind Foot Pivot", min = -0.4, max = 1.0, default = 0.0, update=shape.pivotRightUpdate)






    snap_on_switch  : BoolProperty(name = "Auto Align", default = False,
    description='Automatic alignment between FK and IK:\n\n'\
                'When turning ON IK: Make sure the IK Targets are aligned to the FK bones\n'\
                'When turning OFF IK: Apply the IK Pose to corresponding FK Pose\n\n'\
                'NOTE: The alignment for the legs may cause small jumps and unwanted extra rotations\n'\
                'this is a known issue caused by an unfortunate bone topology.'
                )

    def update_face_ik(self, context):
        if  self.face_ik_value != 1.0 and self.face_ik_enabled:
            self.face_ik_value = 1.0
        elif self.face_ik_value != 0.0 and not self.face_ik_enabled:
            self.face_ik_value = 0.0
        active = context.active_object
        arm = util.get_armature(active)
        self.Enable_Limbs = rig.ButtonEnableIK.set_ik_status(context, self.hinds_ik_enabled, 'Face', self.Enable_Limbs)


    def update_hinds_ik(self, context):
        val = 1.0 if self.hinds_ik_enabled else 0.0
        if self.hind_ik_value_left != val:
            self.hind_ik_value_left = val
        if self.hind_ik_value_right != val:
            self.hind_ik_value_right = val
        active = context.active_object
        arm = util.get_armature(active)        
        arm.IKSwitchesProp.Enable_Limbs = rig.ButtonEnableIK.set_ik_status(context, arm.IKSwitchesProp.hinds_ik_enabled, 'HindLimb3', arm.IKSwitchesProp.Enable_Limbs)


    def update_legs_ik(self, context):
        val = 1.0 if self.legs_ik_enabled else 0.0
        if self.leg_ik_value_left != val:
            self.leg_ik_value_left = val
        if self.leg_ik_value_right != val:
            self.leg_ik_value_right = val
        active = context.active_object
        arm = util.get_armature(active)
        arm.IKSwitchesProp.Enable_Legs = rig.ButtonEnableIK.set_ik_status(context, arm.IKSwitchesProp.legs_ik_enabled, 'Ankle', arm.IKSwitchesProp.Enable_Legs)


    def update_arms_ik(self, context):
        val = 1.0 if self.arms_ik_enabled else 0.0
        if self.arm_ik_value_left != val:
            self.arm_ik_value_left = val
        if self.arm_ik_value_right != val:
            self.arm_ik_value_right = val
        active = context.active_object
        arm = util.get_armature(active)
        arm.IKSwitchesProp.Enable_Arms = rig.ButtonEnableIK.set_ik_status(context, arm.IKSwitchesProp.arms_ik_enabled, 'Wrist', arm.IKSwitchesProp.Enable_Arms)


    face_ik_enabled : BoolProperty(name = "Enable Face Controllers", default = False, update=update_face_ik)
    hinds_ik_enabled: BoolProperty(name = "Enable IK Limbs", default = False, update=update_hinds_ik)
    legs_ik_enabled : BoolProperty(name = "Enable IK Legs", default = False, update=update_legs_ik)
    arms_ik_enabled : BoolProperty(name = "Enable IK Arms", default = False, update=update_arms_ik)

    def update_arm_ik_value_left(self, context):
        enabled = (self.arm_ik_value_left + self.arm_ik_value_right) == 2
        disabled = (self.arm_ik_value_left + self.arm_ik_value_right) == 0
        if enabled and not self.arm_ik_enabled:
            self.arms_ik_enabled = True
        elif disabled and self.arm_ik_enabled:
            self.arms_ik_enabled = False

    def update_arm_ik_value_right(self, context):
        enabled = (self.arm_ik_value_left + self.arm_ik_value_right) == 2
        disabled = (self.arm_ik_value_left + self.arm_ik_value_right) == 0
        if self.arms_ik_enabled and disabled:
            self.arms_ik_enabled = False
        elif enabled and not self.arms_ik_enabled:
            self.arms_ik_enabled = True


    def update_hind_ik_value_left(self, context):
        enabled = (self.hind_ik_value_left + self.hind_ik_value_right) == 2
        disabled = (self.hind_ik_value_left + self.hind_ik_value_right) == 0
        if enabled and not self.hind_ik_enabled:
            self.hinds_ik_enabled = True
        elif disabled and self.hinds_ik_enabled:
            self.hinds_ik_enabled = False

    def update_hind_ik_value_right(self, context):
        enabled = (self.hind_ik_value_left + self.hind_ik_value_right) == 2
        disabled = (self.hind_ik_value_left + self.hind_ik_value_right) == 0
        if self.hinds_ik_enabled and disabled:
            self.hinds_ik_enabled = False
        elif enabled and not self.hinds_ik_enabled:
            self.hinds_ik_enabled = True
   
    def update_leg_ik_value_left(self, context):
        enabled = (self.leg_ik_value_left + self.leg_ik_value_right) == 2
        disabled = (self.leg_ik_value_left + self.leg_ik_value_right) == 0
        if enabled and not self.legs_ik_enabled:
            self.legs_ik_enabled = True
        elif disabled and self.legs_ik_enabled:
            self.legs_ik_enabled = False

    def update_leg_ik_value_right(self, context):
        enabled = (self.leg_ik_value_left + self.leg_ik_value_right) == 2
        disabled = (self.leg_ik_value_left + self.leg_ik_value_right) == 0
        if self.legs_ik_enabled and disabled:
            self.legs_ik_enabled = False
        elif enabled and not self.legs_ik_enabled:
            self.legs_ik_enabled = True

    def update_face_ik_value(self, context):
        enabled = self.face_ik_value == 1
        disabled = self.face_ik_value == 0
        if self.face_ik_enabled and disabled:
            self.face_ik_enabled = False
        elif enabled and not self.face_ik_enabled:
            self.face_ik_enabled = True
        
    arm_ik_value_left  : FloatProperty(name="Left Hand FK-IK distribution", min=0.0, max=1.0, default=0.0, update=update_arm_ik_value_left)
    arm_ik_value_right : FloatProperty(name="Right Hand FK-IK distribution", min=0.0, max=1.0, default=0.0, update=update_arm_ik_value_right)
    hind_ik_value_left  : FloatProperty(name="Left Hind FK-IK distribution", min=0.0, max=1.0, default=0.0, update=update_hind_ik_value_left)
    hind_ik_value_right : FloatProperty(name="Right Hind FK-IK distribution", min=0.0, max=1.0, default=0.0, update=update_hind_ik_value_right)
    leg_ik_value_left  : FloatProperty(name="Left Leg FK-IK distribution", min=0.0, max=1.0, default=0.0, update=update_leg_ik_value_left)
    leg_ik_value_right : FloatProperty(name="Right Leg FK-IK distribution", min=0.0, max=1.0, default=0.0, update=update_leg_ik_value_right)
    face_ik_value      : FloatProperty(name="Face FK-IK distribution", min=0.0, max=1.0, default=0.0, update=update_face_ik_value)



classes = (
    AnimPropGroup,
    SkeletonPropGroup,
    ScenePropGroup,
    MeshPropGroup,
    RigPropGroup,
    UpdateRigPropGroup,
    BakerPropGroup,
    MaterialPropGroup,
    ObjectPropGroup,
    SparkleTimelinePropGroup,
    IKSwitchesPropGroup,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered propgroups:%s" % cls)

    bpy.types.Object.IKSwitchesProp = PointerProperty(type = IKSwitchesPropGroup)
    bpy.types.Scene.SparkleTimelineProp = PointerProperty(type = SparkleTimelinePropGroup)
    bpy.types.Object.ObjectProp     = PointerProperty(type = ObjectPropGroup)
    bpy.types.Object.AnimProp       = PointerProperty(type = AnimPropGroup)
    bpy.types.Action.AnimProp       = PointerProperty(type = AnimPropGroup)
    bpy.types.Object.RigProp        = PointerProperty(type = RigPropGroup)
    bpy.types.Scene.AnimProp        = PointerProperty(type = AnimPropGroup)
    bpy.types.Scene.SkeletonProp    = PointerProperty(type = SkeletonPropGroup)
    bpy.types.Scene.SceneProp       = PointerProperty(type = ScenePropGroup)
    bpy.types.Scene.MeshProp        = PointerProperty(type = MeshPropGroup)
    bpy.types.Scene.UpdateRigProp   = PointerProperty(type = UpdateRigPropGroup)
    bpy.types.Object.avastarMaterialProp = PointerProperty(type = MaterialPropGroup)
    bpy.types.Material.BakerProp    = PointerProperty(type = BakerPropGroup)

def unregister():
    from bpy.utils import unregister_class   




    if hasattr(bpy.types.Material,'BakerProp'): del bpy.types.Material.BakerProp
    if hasattr(bpy.types.Object,'avastarMaterialProp'): del bpy.types.Object.avastarMaterialProp
    if hasattr(bpy.types.Scene,'UpdateRigProp'): del bpy.types.Scene.UpdateRigProp
    if hasattr(bpy.types.Scene,'MeshProp'): del bpy.types.Scene.MeshProp
    if hasattr(bpy.types.Scene,'SceneProp'): del bpy.types.Scene.SceneProp
    if hasattr(bpy.types.Scene,'SkeletonProp'): del bpy.types.Scene.SkeletonProp
    if hasattr(bpy.types.Scene,'AnimProp'): del bpy.types.Scene.AnimProp
    if hasattr(bpy.types.Object,'RigProp'): del bpy.types.Object.RigProp
    if hasattr(bpy.types.Action,'AnimProp'): del bpy.types.Action.AnimProp
    if hasattr(bpy.types.Object,'AnimProp'): del bpy.types.Object.AnimProp
    if hasattr(bpy.types.Object,'ObjectProp'): del bpy.types.Object.ObjectProp
    if hasattr(bpy.types.Scene,'SparkleTimelineProp'): del bpy.types.Scene.SparkleTimelineProp
    if hasattr(bpy.types.Object,'IKSwitchesProp'): del bpy.types.Object.IKSwitchesProp

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered propgroups:%s" % cls)
