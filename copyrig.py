### Copyright 2016, Matrice Laville
### Modifications: None
###
### This file is part of Avastar 2.
### 

###
### should have received a copy of the license together with Avastar.
### The license can also be obtained from http://www.machinimatrix.org/

import bpy, bmesh, sys, logging, os, mathutils
from bpy.props import *
from bpy.types import Menu, Operator
from bl_operators.presets import AddPresetBase
from bpy_extras.io_utils import ImportHelper
from bpy.app.handlers import persistent
from . import armature_util, context_util, const, propgroups, bind, create, data, mesh, messages, rig, shape, util
from .const import *
from .context_util import *
from .util import PVector, mulmat
from .data import Skeleton

CONST_NAMES_MAP = {}
CONST_NAMES_MAP['TrackTo']='Track To'

BONE_DATA_NAME   = 0 # "name"
BONE_DATA_HEAD   = 1 # "data head"
BONE_DATA_TAIL   = 2 # "data tail"
BONE_DATA_SELECT = 3 # "select"
BONE_DATA_DEFORM = 4 # "deform"
BONE_DATA_ROLL   = 5 # "roll"
BONE_DATA_MATRIX = 6 # "matrix"
BONE_DATA_PARENT = 7 # Parent name, or None if no parent
BONE_POSE_GROUP  = 8 # Name of associated bone group, or None if no group assigned to Bone
BONE_POSE_COLORSET   = 9 # Name of associated colorset, or None if no color set assigned to Bone group
BONE_DATA_CONNECT    = 10 # Bone Connect state
BONE_DATA_CONSTRAINT = 11 # Bone Constraint data [type,influence,mute]
BONE_DATA_IKLIMITS   = 12 # Bone IK Limits: bone.use_ik_limit_x/y/z
BONE_POSE_ROTATION_MODE = 13
BONE_DATA_HIDE     = 14
BONE_DATA_COUNT    = 15

log=logging.getLogger("avastar.copyrig")
registerlog = logging.getLogger("avastar.register")

def is_animated_mesh(obj, src_armature):

    if obj.type != 'MESH': return False
    has_modifier=False
    for mod in [mod for mod in obj.modifiers if mod.type=='ARMATURE']:

        if mod.object == src_armature:

            return True

    return False

def get_joint_data(armobj):
    joint_data = [armobj.get('sl_joints'),
                  armobj.data.JointOffsetList
                 ]
    return joint_data

def copy_collection(toCollection, fromCollection):
    toCollection.clear()
    for elem in fromCollection:
        item = toCollection.add()
        for k, v in elem.items():
            item[k] = v

def set_joint_data(armobj, joint_data):
    sl_joints = joint_data[0]
    JointOffsetList = joint_data[1]
    
    if sl_joints:
        armobj['sl_joints'] = sl_joints
    if JointOffsetList:
        copy_collection(armobj.data.JointOffsetList, JointOffsetList)

def copy_avastar(self,
        context,
        tgt_rig_type,
        active_obj,
        src_armature,
        bone_repair,
        mesh_repair
        ):

    log.info("+=========================================================================")
    log.info("| copy: Starting a %s Avastar copy from \"%s\"" % (tgt_rig_type, src_armature.name))
    log.info("+=========================================================================")

    no_mesh = not mesh_repair
    jointType = src_armature.RigProp.JointType
    src_scale = src_armature.scale.copy()
    src_rig_type = self.srcRigType
    active_is_arm = active_obj == src_armature
    selected_object_names = util.get_selected_object_names(context)
    actsel = util.object_select_get(active_obj)
    scene = context.scene
    util.set_active_object(context, src_armature)
    util.ensure_mode_is('OBJECT')
    
    action = src_armature.animation_data.action
    shape_data = shape.copy_to_scene(scene, src_armature).copy()
    shape.reset_to_restpose(context, src_armature)
    joint_data = get_joint_data(src_armature)

    if self.applyRotation:
        log.info("|  Apply Rot&Scale on [%s]" % util.get_active_object(context).name)
        log.info("|  copy: Apply Visual transforms, Rotation and Scale to %s" % src_armature.name)
        old_state = util.select_hierarchy(src_armature) # All of them!
        bpy.ops.object.visual_transform_apply() #To get around some oddities with the apply tool (possible blender bug?)

        util.restore_hierarchy(context, old_state)
        util.update_view_layer(context)

    util.ensure_mode_is("POSE")
    use_restpose = src_armature.data.pose_position
    src_armature.data.pose_position = 'POSE'
    bpy.ops.pose.select_all(action="SELECT")
    log.info("|  copy pose from %s to pose buffer" % (src_armature.name) )
    bpy.ops.pose.copy()
    src_armature.data.pose_position = 'REST'
    util.ensure_mode_is('OBJECT')








    for arm in self.targets:
        util.set_active_object(context, arm)
        shape.reset_to_restpose(context, arm)

    util.set_active_object(context, src_armature)
    log.info("+=========================================================================")
    self.copy_skeletons(context, src_armature, self.targets, src_rig_type, tgt_rig_type, transfer_joints=True, sync=False)
    log.info("+=========================================================================")
    shape.fromDictionary(src_armature, shape_data)
    if active_is_arm:
        active_obj = self.targets[0]

    util.restore_object_select_states(context, selected_object_names)


    oselector = util.set_disable_update_slider_selector(True)

    tgt_armatures=[]


    for arm in self.targets:
        log.info("|  Post actions on armature [%s]" % (arm.name) )
        util.set_active_object(context, arm)

        if arm.RigProp.rig_use_bind_pose != src_armature.RigProp.rig_use_bind_pose:
            log.info("| Set use bind pose to %s" % src_armature.RigProp.rig_use_bind_pose)
            arm.RigProp.rig_use_bind_pose = src_armature.RigProp.rig_use_bind_pose

        shape.fromDictionary(arm, shape_data)

        set_joint_data(arm, joint_data)
        arm.scale = src_scale

        if self.transferMeshes:
            log.info("| Copy Meshes from [%s] to [%s]" % (src_armature.name, arm.name) )
            self.move_objects_to_target(context, self.sources, arm, self.srcRigType)  # copy from Avastar to Avastar

        if self.appearance_enabled:
            log.info("| Attach Sliders to Armature [%s]" % (arm.name) )
            arm.ObjectProp.slider_selector = 'SL'











        util.set_active_object(context, arm)
        util.enforce_armature_update(context,arm)
        tgt_armatures.append(arm)

    util.set_disable_update_slider_selector(oselector)
    util.set_active_object(context, active_obj)
    util.object_select_set(active_obj, actsel)

    if action:
        active_obj.animation_data.action = action
        log.info("| Assigned Action %s to %s" % (action.name, active_obj.name) )

    log.info("+=========================================================================")
    util.ensure_mode_is(self.active_mode)
    return tgt_armatures

def convert_to_avastar(self,
        context,
        tgt_rig_type,
        active_obj,
        src_armature,
        inplace_transfer,
        bone_repair,
        mesh_repair,
        transfer_joints=True
        ):

    log.info("+=========================================================================")
    log.info("| convert: Starting a %s Avastar conversion from \"%s\"" % (tgt_rig_type, src_armature.name))
    log.info("+=========================================================================")

    no_mesh = not mesh_repair
    jointType = src_armature.RigProp.JointType
    src_rig_type = self.srcRigType
    active_is_arm = active_obj == src_armature
    selected_object_names = util.get_selected_object_names(context)
    actsel = util.object_select_get(active_obj)
    scene = context.scene
    util.set_active_object(context, src_armature)
    util.ensure_mode_is('OBJECT')
    action = src_armature.animation_data.action

    if inplace_transfer:
        if self.applyRotation:
            log.warning("convert_to_avastar: Apply Visual transforms, Rotation and Scale to %s" % src_armature.name)
            old_state = util.select_hierarchy(src_armature) # All of them!
            bpy.ops.object.visual_transform_apply() #To get around some oddities with the apply tool (possible blender bug?)

            try:
                bpy.ops.object.transform_apply(rotation=True, scale=True)
            except Exception as e:
                log.error("Can not apply Object transformations to linked objects (Ignoring)")

            util.restore_hierarchy(context, old_state)
            util.update_view_layer(bpy.context)

        util.ensure_mode_is("POSE")
        use_restpose = src_armature.data.pose_position
        src_armature.data.pose_position = 'POSE'
        bpy.ops.pose.select_all(action="SELECT")
        bpy.ops.pose.copy()
        log.warning("copyrig-convert-avastar: copy pose from %s to pose buffer" % (src_armature.name) )
        src_armature.data.pose_position = 'REST'
        util.ensure_mode_is('OBJECT')

        tgt_armature = create.createAvatar(context, quads=True, use_restpose=use_restpose, rigType=tgt_rig_type, jointType=jointType, no_mesh=no_mesh)
        propgroups.gender_update(tgt_armature, self.use_male_shape)
        self.targets.append(tgt_armature)

    self.copy_skeletons(context, src_armature, self.targets, src_rig_type, tgt_rig_type, transfer_joints, sync=False)
    if active_is_arm:
        active_obj = self.targets[0]

    util.restore_object_select_states(context, selected_object_names)

    is_fitted=False
    oselector = util.set_disable_update_slider_selector(True)

    for arm in self.targets:
        log.debug("3:target_armature has %d bones" % len(arm.data.bones))
        util.set_active_object(context, arm)
        if self.sl_bone_rolls:
            rig.restore_source_bone_rolls(arm)
        arm.RigProp.rig_use_bind_pose = util.use_sliders(context) and src_armature.RigProp.rig_use_bind_pose

        self.move_objects_to_target(context, self.sources, arm, self.srcRigType) # Convert to avastar


        if self.appearance_enabled:

            arm.ObjectProp.slider_selector = 'SL'

        for child in util.get_animated_meshes(context, arm, with_avastar=False):

            if self.appearance_enabled:

                util.set_active_object(context, child)
                child.ObjectProp.slider_selector = 'SL'
            if not is_fitted:
                for key in child.vertex_groups.keys():
                    if key in data.get_volume_bones():
                        is_fitted = True
                        util.object_select_set(arm, True)
                        util.set_active_object(context, arm)
                        bpy.ops.avastar.armature_deform_enable(set='VOL')
                        break

        if not inplace_transfer:
            util.set_active_object(context, arm)

            bpy.ops.avastar.apply_shape_sliders()

            util.enforce_armature_update(context,arm)






    util.set_disable_update_slider_selector(oselector)
    util.set_active_object(context, active_obj)
    util.object_select_set(active_obj, actsel)
    if action:
        active_obj.animation_data.action = action
        log.warning("copyrig-convert-avastar: Assigned Action %s to %s" % (action.name, active_obj.name) )

    util.ensure_mode_is('POSE')
    bpy.ops.pose.select_all(action="SELECT")
    src_armature.data.pose_position = 'POSE'
    bpy.ops.pose.paste()  
    log.warning("copyrig-convert-avastar: paste pose from pose buffer to %s" % (active_obj.name) )

    util.ensure_mode_is(self.active_mode)
    return active_obj

def update_avastar(self,
        context,
        tgt_rig_type,
        active_obj,
        src_armature,
        structure_repair,
        mesh_repair,
        transfer_joints=True
        ):

    def adjust_shape_keys(child, src_armature, tgt_armature):
        skeys = child.data.shape_keys
        if not skeys:
            return
        


        animdata = skeys.animation_data
        if not animdata:
            return

        for driver in animdata.drivers:
            dr = driver.driver
            vars = None
            try:
                vars = dr.variables
            except:
                pass
            if not vars:
                continue

            for var in vars:
                log.info("adjusting var %s : %s" % (child.name, var.name) )
                for target in var.targets:
                    if target.id_type == 'OBJECT' and target.id == src_armature:
                        target.id = tgt_armature

    def check_container_exists(armobj, msg=""):
        for child in armobj.children:
            if '_meshes' in child.name and child.type =='Empty':
                return True
        log.warning("%s: Avatar_meshes is gone from %s" % (msg, armobj.name) )
        return False

    def apply_scale_and_rotation(context, src_armature, sources):

        scene = context.scene
        oactive = util.get_active_object(context)
        omode = util.ensure_mode_is('OBJECT')

        apply_set = []
        for obj in sources:
            if not util.is_identity(obj.matrix_local):
                apply_set.append(obj)
        if not apply_set:
            log.info("| update avastar: Apply Rot&Scale not necessary (All children of %s are clean)" % oactive)
            return

        log.info("| update avastar: Apply Visual transforms, Rotation and Scale to %s" % oactive.name)
        select_states = util.get_select_and_hide(context.scene.objects, False, False, False)
        util.set_select(apply_set, reset=False)

        log.info("| update avastar: Apply Rot&Scale to %d children of [%s]" % (len(apply_set), oactive.name))
        bpy.ops.object.visual_transform_apply() #To get around some oddities with the apply tool (possible blender bug?)
        try:
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        except Exception as e:
            log.error("| update avastar: Can not apply Object transformations to linked objects (Ignoring)")

        util.set_active_object(context, oactive)
        util.object_select_set(oactive, True)
        util.ensure_mode_is(omode)
        util.set_select_and_hide(context, select_states)
        util.update_view_layer(context)


    src_rig_type = self.srcRigType
    selected_object_names = util.get_selected_object_names(context)
    armature_name = src_armature.name
    jointType = self.JointType

    log.warning("+========================================================================")
    log.warning("| update     : %s Rig Update for Armature \"%s\"" % (tgt_rig_type, armature_name))
    log.warning("| joint type : %s" % (jointType) )
    if self.must_rebind():
        log.warning("| rebinding  : %d rebind candidates" % len(self.sources))
    log.warning("+========================================================================")

    no_mesh = not mesh_repair
    active_is_arm = active_obj == src_armature
    actsel = util.object_select_get(active_obj)
    scene = context.scene
    util.set_active_object(context, src_armature)
    util.ensure_mode_is('OBJECT')
    if not src_armature.animation_data:
        src_armature.animation_data_create()
    action = src_armature.animation_data.action

    if self.must_rebind():

        objects_to_rebind = [o for o in src_armature.children]
        log.warning("Unparent sources: %s" % [ob.name for ob in self.sources] )
        util.unparent_selection(context, objects_to_rebind, type='CLEAR_KEEP_TRANSFORM', clear_armature=True)
    else:
        objects_to_rebind = []

    if self.applyRotation:
        apply_scale_and_rotation(context, src_armature, self.sources)

    shape_data = shape.asDictionary(src_armature, full=True)
    shape.reset_to_restpose(context, src_armature)

    util.ensure_mode_is("POSE")
    bone_store = initialise_bone_setup(context, src_armature)
    use_restpose = src_armature.data.pose_position
    src_armature.data.pose_position = 'POSE'
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.copy()
    log.info("update: copy pose from %s to pose buffer" % (src_armature.name) )
    src_armature.data.pose_position = 'REST'
    util.ensure_mode_is('OBJECT')

    if mesh_repair:
        self.sources = [s for s in self.sources if not 'avastar-mesh' in s]
        container = find_avatar_mesh_container(context, src_armature, msg="")
        if container:
            util.remove_object(context, container, recursive=True)
        else:
            shape.manage_avastar_shapes(context, src_armature, [])

    log.warning("| Creating the new Avastar Rig")
    tgt_armature = create.createAvatar(context, quads=True, use_restpose=True, rigType=tgt_rig_type, jointType=jointType, no_mesh=no_mesh)
    util.copy_collection_visibility(context, tgt_armature, src_armature)

    if tgt_armature.ShapeDrivers.male_80 != self.use_male_shape:
        ofreeze = tgt_armature.ShapeDrivers.Freeze
        tgt_armature.ShapeDrivers.Freeze = True
        propgroups.gender_update(tgt_armature, self.use_male_shape)
        tgt_armature.ShapeDrivers.Freeze = ofreeze

    self.targets.append(tgt_armature)

    log.debug("| Copy the Rig info")
    self.copy_skeletons(context, src_armature, [tgt_armature], src_rig_type, tgt_rig_type, transfer_joints, sync=False, bone_store=bone_store)
    Skeleton.get_toe_hover(tgt_armature, reset=True, bind=True)

    tgt_armature.scale = src_armature.scale.copy()
    tgt_armature.RigProp.rig_use_bind_pose = src_armature.RigProp.rig_use_bind_pose
    if shape_data:

        shape.fromDictionary(src_armature, shape_data, update=True, init=True)

    util.ensure_mode_is('OBJECT')
    log.debug("| Restore Object Select states")
    util.restore_object_select_states(context, selected_object_names)

    util.set_active_object(context, tgt_armature)
    util.ensure_mode_is('OBJECT')




    src_armature.name = 'del_' + armature_name
    tgt_armature.name = armature_name

    is_fitted=False
    oselector = util.set_disable_update_slider_selector(True)
    log.debug("update: target_armature has %d bones" % len(tgt_armature.data.bones))

    arm = tgt_armature
    if True:
        if self.sl_bone_rolls:
            rig.restore_source_bone_rolls(arm)

        use_bind_pose = util.use_sliders(context) and src_armature.RigProp.rig_use_bind_pose
        if arm.RigProp.rig_use_bind_pose != use_bind_pose:
            arm.RigProp.rig_use_bind_pose = use_bind_pose

        util.object_show_in_front(arm, util.object_show_in_front(src_armature))
        arm.data.show_bone_custom_shapes = src_armature.data.show_bone_custom_shapes

        log.debug("| move objects to target")
        self.move_objects_to_target(context, self.sources, arm, self.srcRigType, src_armature) # update avastar


        if self.appearance_enabled:

            arm.ObjectProp.slider_selector = 'SL'
            shape.destroy_shape_info(context, arm)
            log.debug("| update: Checking Custom meshes of %s" % arm.name)


        log.debug("| adjust shape keys...")
        for child in util.get_animated_meshes(context, arm, with_avastar=False):
            adjust_shape_keys(child, src_armature, arm)
            log.info("update: Checking Mesh %s" % child.name)
            if not is_fitted:
                for key in child.vertex_groups.keys():
                    if key in data.get_volume_bones():
                        is_fitted = True
                        util.object_select_set(arm, True)
                        util.set_active_object(context, arm)
                        bpy.ops.avastar.armature_deform_enable(set='VOL')
                        break
        log.debug("| adjust shape keys done.")

    util.set_disable_update_slider_selector(oselector)

    util.set_active_object(context, tgt_armature)

    util.object_select_set(tgt_armature, actsel)
    if action:
        tgt_armature.animation_data.action = action
        log.info("update: Assigned Action %s to %s" % (action.name, tgt_armature.name) )









    log.debug("| adjust support rig")
    util.ensure_mode_is('EDIT')
    shape.adjustSupportRig(context)
    util.ensure_mode_is('OBJECT')
    util.restore_object_select_states(context, selected_object_names)
    util.ensure_mode_is('POSE')

    bpy.ops.pose.select_all(action="SELECT")
    tgt_armature.data.pose_position = 'POSE'
    bpy.ops.pose.paste()
    log.info("update: paste pose from pose buffer to %s" % (tgt_armature.name) )
    if not active_is_arm:
        util.set_active_object(context, active_obj)
        util.object_select_set(active_obj, actsel)
        util.ensure_mode_is(self.active_mode)

    tgt_armature.ObjectProp.filter_deform_bones = src_armature.ObjectProp.filter_deform_bones
    tgt_armature.ObjectProp.rig_display_type = src_armature.ObjectProp.rig_display_type

    if shape_data:

        shape.fromDictionary(tgt_armature, shape_data, update=True, init=True)

    return tgt_armature

def convert_sl(self,
        context,
        tgt_rig_type,
        jointType,
        active_obj,
        src_armature,
        inplace_transfer,
        bone_repair,
        mesh_repair,
        transfer_joints=True,
        shapefile=None
        ):

    def get_child_set(context, arm, objects_to_rebind):
        if objects_to_rebind:
            child_set = objects_to_rebind
        else:
            child_set = util.get_animated_meshes(context, arm, with_avastar=False)
        return child_set

    log.warning("+========================================================================")
    if inplace_transfer:
        log.warning("| Start an %s Inplace Rig Migration of armature:'%s'" % (tgt_rig_type, src_armature.name))
    else:
        log.warning("| Start a %s Rig Transfer Copy from armature:'%s'" % (tgt_rig_type, src_armature.name))
    log.warning("| joint type : %s" % (jointType) )
    if self.must_rebind():
        log.warning("| rebinding  : %d rebind candidates" % len(self.sources))
    log.warning("+========================================================================")


    src_rig_type = self.srcRigType
    active_is_arm = active_obj == src_armature

    selected_object_names = util.get_selected_object_names(context)
    updateRigProp = self #context.scene.UpdateRigProp
    scene  = context.scene
    util.set_active_object(context, src_armature)
    ob = util.get_active_object(context)



    no_mesh = self.srcRigType == MANUELMAP

    actsel      = util.object_select_get(active_obj)


    omode = util.ensure_mode_is("OBJECT", object=src_armature)


    objects_to_rebind = []
    if inplace_transfer:
        if self.must_rebind():
            objects_to_rebind = [o for o in src_armature.children]
            log.warning("convert sl:| Unparent sources: %s" % [ob.name for ob in self.sources] )
            util.unparent_selection(context, objects_to_rebind, type='CLEAR_KEEP_TRANSFORM')

        if self.applyRotation:

            util.set_active_object(context, src_armature)
            old_state = util.select_hierarchy(src_armature) # All of them!
            log.warning("convert sl:| Apply Visual transforms, Rotation and Scale to armature:%s" % src_armature.name)
            bpy.ops.object.visual_transform_apply() #To get around some oddities with the apply tool (possible blender bug?)
            bpy.ops.object.transform_apply(rotation=True, scale=True)
            util.restore_hierarchy(context, old_state)
            util.update_view_layer(context)


        use_restpose = self.appearance_enabled
        tgt_armature = create.createAvatar(context,
                       quads=True,
                       use_restpose=use_restpose,
                       rigType=tgt_rig_type,
                       jointType=jointType,
                       no_mesh=no_mesh,
                       mesh_ids = context.scene.get('mesh_ids')
        )

        log.warning("convert sl:| created target armature '%s'" % tgt_armature.name)

        util.set_active_object(context, tgt_armature)
        if tgt_armature.ShapeDrivers.male_80 != self.use_male_shape:
            propgroups.gender_update(tgt_armature, self.use_male_shape) # implicit call to refreshAvastarShape
        else:
            shape.refreshAvastarShape(context)

        if shapefile:
            shape.loadProps(context, tgt_armature, shapefile)
            util.enforce_armature_update(context, tgt_armature)

        self.targets.append(tgt_armature)
        log.warning("convert sl:|  Added new Armature name=[%s]" % tgt_armature.name)

        if self.srcRigType == MANUELMAP:
            util.ensure_mode_is('OBJECT')
            for obj in src_armature.children:
                util.set_active_object(context, obj)
                splitcount = rig.avastar_split_manuel(context, obj, 100)
                log.warning("Split Manuellab into %d children" % splitcount)
                self.sources = [c for c in src_armature.children if c.type=='MESH']

    else:
        for arm in self.targets:
            util.set_active_object(context, arm)
            bpy.ops.avastar.store_bind_data()


    log.warning("convert sl:| 1 self.targets[0] is '%s'" % self.targets[0].name)
    self.copy_skeletons(context, src_armature, self.targets, src_rig_type, tgt_rig_type, transfer_joints, sync=True)
    log.warning("convert sl:| 2 self.targets[0] is '%s'" % self.targets[0].name)
    if active_is_arm:
        active_obj = self.targets[0]
        log.warning("convert sl:| changed active object to '%s'" % active_obj.name)

    util.ensure_mode_is('OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    util.restore_object_select_states(context, selected_object_names)

    is_fitted=False
    oselector = util.set_disable_update_slider_selector(True)

    for arm in self.targets:
        util.set_active_object(context, arm)
        if self.sl_bone_rolls:
            rig.restore_source_bone_rolls(arm)
        arm.RigProp.rig_use_bind_pose = util.use_sliders(context) and src_armature.RigProp.rig_use_bind_pose
        child_set = get_child_set(context, arm, objects_to_rebind)
        self.move_objects_to_target(context, child_set, arm, self.srcRigType) # convert SL

        log.warning("convert sl:| Update slider settings for armature [%s]" % (arm.name) )
        if self.appearance_enabled:
            log.warning("convert sl:| Set Armature %s Slider Selector to 'SL'" % arm.name)
            arm.ObjectProp.slider_selector = 'SL'
        log.warning("convert sl:| Checking Custom meshes of armature [%s]" % arm.name)
        for child in child_set:
            log.warning("convert sl:| Checking Mesh %s" % child.name)
            if self.appearance_enabled:
                log.warning("convert sl:| Set child %s Slider Selector to 'SL'" % child.name)
                util.set_active_object(context, child)
                child.ObjectProp.slider_selector = 'SL'
            if not is_fitted:
                for key in child.vertex_groups.keys():
                    if key in data.get_volume_bones():
                        is_fitted = True
                        util.object_select_set(arm, True)
                        util.set_active_object(context, arm)
                        bpy.ops.avastar.armature_deform_enable(set='VOL')
                        break

        if not inplace_transfer:
            util.set_active_object(context, arm)

            bpy.ops.avastar.apply_shape_sliders()

            util.enforce_armature_update(context,arm)

            bpy.ops.avastar.alter_to_restpose()



    util.set_disable_update_slider_selector(oselector)
    util.set_active_object(context, active_obj)
    util.object_select_set(active_obj, actsel)
    util.ensure_mode_is(self.active_mode)
    
    if inplace_transfer:
        log.warning("convert sl:| Finish %s Inplace Rig Migration with new rig '%s'" % (tgt_rig_type, active_obj.name))
    else:
        log.warning("convert sl:| Start a %s Rig Transfer Copy from '%s' to '%s'" % (tgt_rig_type, src_armature.name, active_obj.name))
    return active_obj

def print_on_bone_tail_change(bone, msg=''):
    if '_bt' in bone:
        bt = Vector(bone['_bt'])
        t = Vector(bone.tail)
        has_changed = t != bt
    else:
        has_changed = True
    if has_changed:
        print("%s: %s head is now %s" % (msg, bone.name, bone.head) )
        print("%s: %s tail is now %s" % (msg, bone.name, bone.tail) )
        bone['_bt'] = bone.tail

def find_avatar_mesh_container(context, armobj, msg=""):
    if armobj:
        for c in armobj.children:
            if c.type == 'EMPTY' and '_meshes' in c.name:
                log.warning("%sFound mesh container %s" % (msg, c.name) )
                return c
    return None

def get_avatar_mesh_container(context, armobj, msg="", ct=None):
    c = find_avatar_mesh_container(context, armobj, msg)
    if c:
        log.warning("%sReuse Target Mesh container %s for %s" % (msg, c.name, armobj.name) )
        return c

    if ct:
        log.warning("%sReuse Source Mesh container %s for %s" % (msg, ct.name, armobj.name) )
        c = ct
    else:
        log.warning("%sGenerate missing Mesh container for %s" % (msg, armobj.name) )
        c = create.add_container(context, armobj, armobj.name + '_meshes')
    return c

def import_collada(scene, filepath):

    if not os.access(filepath, os.R_OK):
        log.warning("Collada file not found or not readable:")
        log.warning("filepath: %s" % filepath)
        return None

    before = [o for o in scene.objects]
    bpy.ops.wm.collada_import(
        filepath=filepath,
        import_units=False,
        fix_orientation=False,
        find_chains=False,
        auto_connect=False,
        min_chain_length=0,
        keep_bind_info=True)

    after = [o for o in scene.objects]
    importset = set(after) - set(before)
    return importset

def import_blend(context, filepath):
    scene = context.scene
    def link_recursive(ob, indent = 0):
        for ch in ob.children:
            log.warning("%s%s" % (indent*" ", ch.name) )
            util.link_object(context, ch)
            link_recursive(ch, indent=indent+4)
        if ob.type == 'EMPTY':
           util.object_hide_set(ob, True)

    before = [o for o in scene.objects]
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        data_to.objects = data_from.objects

    for ob in data_to.objects:
        if ob.type == 'ARMATURE':
            log.warning("%s (linking armature)" % (ob.name) )
            util.link_object(context, ob)
            link_recursive(ob, 4)
    for ob in data_to.objects:
        if ob.users == 0:
            log.warning("Remove orphan %s" % ob.name)
            util.remove_object(context, ob)

    after = [o for o in scene.objects]
    importset = set(after) - set(before)
    return importset

def import_rig_from_file(context, prop):
    scene = context.scene

    filepath = prop.devkit_filepath.replace("AVASTAR", AVASTAR_DIR)
    shapefile = os.path.splitext(filepath)[0]+".shape"
    if not os.path.exists(shapefile):
        shapefile = ""
    ext = os.path.splitext(filepath)[1]
    
    log.warning("Import Devkit from file %s with extension %s" % (filepath, ext) )

    if ext == '.dae':
        importset = import_collada(scene, filepath)
    elif ext == '.blend':
        importset = import_blend(context, filepath)
    else:
        importset = None

    if (not importset):
        return None

    arms = [ob for ob in importset if ob.type == 'ARMATURE']
    if len(arms) != 1:
        return None

    armobj = arms[0]

    util.set_active_object(context, armobj)
    
    if prop.devkit_scale != 1.0:
        armobj.scale = prop.devkit_scale*armobj.scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    if prop.srcRigType == 'AVASTAR':
        if armobj.RigProp.JointType == prop.JointType:
            return armobj

    create.smart_bone_connector(armobj, prop.srcRigType, prop.JointType)

    prop.handleTargetMeshSelection = 'HIDE'

    armobj.RigProp.JointType = prop.JointType
    armobj.RigProp.rig_use_bind_pose = prop.devkit_use_bind_pose
    use_male_shape = scene.UpdateRigProp.use_male_shape
    use_male_skeleton = scene.UpdateRigProp.use_male_skeleton
    scene.UpdateRigProp.use_male_shape=False
    scene['mesh_ids'] = ['eyeBallLeftMesh', 'eyeBallRightMesh', 'headMesh'] if prop.devkit_use_sl_head else []


    bpy.ops.avastar.copy_rig(
        use_male_shape    = False,
        use_male_skeleton = use_male_skeleton,
        JointType     = prop.tgtJointType,
        srcRigType    = prop.srcRigType,
        tgtRigType    = prop.tgtRigType,
        sl_bone_ends  = prop.sl_bone_ends,
        sl_bone_rolls = prop.sl_bone_rolls,
        handleTargetMeshSelection = prop.handleTargetMeshSelection,
        adjust_origin = 'ORIGIN_TO_ROOT',
        apply_pose    = False,
        mesh_repair   = prop.devkit_use_sl_head,
        show_offsets  = False,
        bone_repair   = False,
        devkit_shapepath = shapefile
    )

    scene['mesh_ids'] = None


    armobj = context.object
    util.set_armature_layers(armobj, B_LEGACY_POSE_LAYERS)
    showids = ['headMesh', 'eyeBallRightMesh', 'eyeBallLeftMesh']
    mesh_objs = [m for m in util.getChildren(armobj, type='MESH')]
    heads = [m for m in mesh_objs if m.get('mesh_id') in showids ]

    custom_objs = [ob for ob in mesh_objs if ob not in heads]
    rig.reset_cache(armobj, full=True)
    shape.prepare_reference_meshes(custom_objs, armobj)
    propgroups.update_sliders(context)

    for head in heads:
        util.object_hide_set(head, not prop.devkit_use_sl_head)

    if use_male_shape:
        propgroups.gender_update(armobj, True)
        scene.UpdateRigProp.use_male_shape = True

    if heads:
        mesh.freeze_selection(context, targets=heads)

    armobj.data.display_type ='STICK'
    armobj.data.show_bone_custom_shapes=True
    util.set_active_object(context, armobj)
    util.set_select([armobj], reset=True)
    preferences = util.getAddonPreferences()
    mode = preferences.initial_rig_mode

    util.set_mode(context, mode)
    return armobj


class ImportColladaDevkit(bpy.types.Operator, ImportHelper):
    bl_idname = "avastar.import_collada_devkit"
    bl_label  = "Import Collada Devkit"
    bl_description = '''
    '''

    filename_ext = '.dae'
    filter_glob : StringProperty(
            default="*.dae",
            options={'HIDDEN'},
            )

    devkit_type : StringProperty(name='devkit', default='')

    def execute(self, context):
        scene = context.scene
        prop = scene.UpdateRigProp
        armobj = import_rig_from_file(context, prop)
        return {'FINISHED'} if armobj else {'CANCELLED'}

def armature_needs_update(armobj):
    avastar_version, rig_version, rig_id, rig_type = util.get_version_info(armobj)
    if not (rig_id or rig_version):
        return True

    repair = (avastar_version == rig_version or AVASTAR_RIG_ID == rig_id)
    return not repair


class RigTransferConfigurator (util.ExpandablePannelSection):
    bl_idname = "avastar.rig_transfer_configurator"
    bl_label = "Rig Transfer"


class ButtonCopyAvastar(bpy.types.Operator):
    '''
    Convert/Update/Cleanup Rigs
    '''
    bl_idname = "avastar.copy_rig"
    bl_label  = "Copy Rig"
    bl_description = messages.avastar_copy_rig_bl_description

    is_initialized = False

    transferMeshes : BoolProperty(
        name="Transfer Meshes",
        default=False,
        description=messages.avastar_copy_rig_transferMeshes
    )

    transferJoints : BoolProperty(
        name = "Transfer Joints",
        default=True,
        description = messages.avastar_copy_rig_transferJoints,
    )

    appearance_enabled = True
    
    applyRotation : const.g_applyRotation
    use_male_shape : const.g_use_male_shape
    use_male_skeleton : const.g_use_male_skeleton
    srcRigType : const.g_srcRigType
    tgtRigType : const.g_tgtRigType
    up_axis : g_up_axis

    adjust_origin : EnumProperty(
        name="Origin",
        description=UpdateRigProp_adjust_origin,
        default='ORIGIN_TO_ROOT',
        items=(
            ('ROOT_TO_ORIGIN',   'Armature', UpdateRigProp_adjust_origin_armature),
            ('ORIGIN_TO_ROOT',   'Rootbone', UpdateRigProp_adjust_origin_rootbone)
        )
    )

    bone_repair     : BoolProperty(
        name        = "Rebuild missing Bones",
        description = UpdateRigProp_bone_repair_description,
        default     = True
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
        description = messages.avastar_copy_rig_mesh_repair,
        default     = False
    )

    show_offsets      : BoolProperty(
        name="Show Offsets",
        description = messages.avastar_copy_rig_show_offsets,
        default     = False
    )

    sl_bone_ends : BoolProperty(
        name="Enforce SL Bone ends",
        description = messages.avastar_copy_rig_sl_bone_ends,
        default     = True
    )

    sl_bone_rolls : const.sl_bone_rolls
    align_to_deform = EnumProperty(
        name="Align to",
        description = UpdateRigProp_align_to_deform_description,
        default='ANIMATION_TO_DEFORM',
        items=(
            ('DEFORM_TO_ANIMATION',   'Pelvis', 'Move mPelvis to Pelvis'),
            ('ANIMATION_TO_DEFORM',   'mPelvis', 'Move Pelvis to mPelvis')
        )        
    )

    align_to_rig : EnumProperty(
        name="Align to",
        description = UpdateRigProp_align_to_rig_description,
        default='ANIMATION_TO_DEFORM',
        items=(
            ('DEFORM_TO_ANIMATION',   'Green Animation Rig', 'Move Deform Bones to Animation Bone locations'),
            ('ANIMATION_TO_DEFORM',   'Blue Deform Rig', 'Move Animation Bones to Deform Bone Locations')
        )
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

    devkit_shapepath : StringProperty(
        name = "Path to shapefile",
        subtype = 'FILE_PATH',
        description = UpdateRigProp_devkit_shapepath
    )

    apply_pose : g_apply_pose
    handleTargetMeshSelection : g_handleTargetMeshSelection
    JointType : GJointType

    inplace_transfer = False
    src_armature     = None
    selected         = None
    targets          = None
    active           = None
    active_mode      = None
    sources          = None
    use_all_sources  = False

    def must_rebind(self):
        return (self.apply_pose or self.applyRotation) and self.sources

    def draw(self, context):
        if self.inplace_transfer == False or self.srcRigType != 'AVASTAR':
            ButtonCopyAvastar.draw_generic(self, context, self.layout, self.src_armature, self.targets)

    @staticmethod
    def sliders_allowed(context):
        scene = context.scene
        with_sliders = scene.SceneProp.panel_appearance_enabled and util.use_sliders(context)
        return with_sliders

    @staticmethod
    def draw_generic(op, context, layout, src_armature, targets, repair=False):

        def draw_selector(prop, box, opid, oplabel):
            col = box.column()
            split = col.split(factor=0.5)
            split.alignment='LEFT'
            split.label(text=oplabel)
            split.prop(prop, opid, text='')

        scene = context.scene
        all_mesh = util.get_animated_meshes(context, src_armature, with_avastar=True, only_selected=False, return_names=False)
        custom_mesh = util.get_animated_meshes(context, src_armature, with_avastar=False, only_selected=False, return_names=False)
        all_count = len(all_mesh)
        custom_count = len(custom_mesh)
        system_count = len(all_mesh) - len(custom_mesh)
        joint_count = rig.get_joint_offset_count(src_armature)
        
        is_armature = context.active_object and context.active_object.type == 'ARMATURE'
        
        if op:
            updateRigProp = op
        else:
            updateRigProp = scene.UpdateRigProp

        if "avastar"  in src_armature:
            title = "Rig Update Tool"
            srcRigType = 'AVASTAR'
            need_pelvis_fix = rig.needTinkerFix(src_armature)
            need_rig_fix = rig.needRigFix(src_armature)
        else:
            title = "Rig Transfer Tool"
            need_pelvis_fix = need_rig_fix = False
            srcRigType = updateRigProp.srcRigType


        box   = layout.box()
        RigTransferConfigurator.draw_collapsible(RigTransferConfigurator, box, label=title)
        if not RigTransferConfigurator.visible:
            return

        row = box.row(align=True)
        row.prop(src_armature.data,"pose_position", expand=True)
        box.separator()
    
        if is_armature and not "avastar" in src_armature:
                create_transfer_preset(box)
                box.separator()

        if not is_armature:
            box.label(text="Only for Armatures",icon=ICON_INFO)
            return

        avastar_version, rig_version, rig_id, rig_type = util.get_version_info(src_armature)
        
        armobj = context.active_object
        col = box.column(align=True)
        if 'avastar' in armobj:
            col.label(text="Source Rig: AVASTAR")
        else:
            row = col.row(align=True)
            row.label(text="Source Rig:")
            row.prop(updateRigProp, "srcRigType", text='')
            row.prop(updateRigProp, "up_axis", text='')

        if srcRigType =='AVASTAR' and not 'avastar' in armobj:
            col   = box.column(align=True)
            col.label(text="Source rig is not Avastar",icon=ICON_ERROR)
            col.label(text="You Reimport an Avastar?", icon=ICON_BLANK1)
            col.label(text="Then use Source Rig: SL", icon=ICON_BLANK1)
            return
        
        if len(targets) == 0:

            draw_selector(updateRigProp, box, "tgtRigType", "Target Rig")
            draw_selector(updateRigProp, box, "JointType", "Joint Type")
            col = box.column()

        if op or len(targets) > 0 or srcRigType!='AVASTAR':
        
            if True:#len(targets) == 0:

                split = col.split(factor=0.52)
                split.label(text="Dummies:")
                split.prop(updateRigProp, "handleTargetMeshSelection", text="", toggle=False)
                col  = box.column()

            if srcRigType == 'AVASTAR':
                col.prop(updateRigProp, "transferMeshes")
                col.prop(updateRigProp, "preserve_bone_colors")
                col.prop(updateRigProp, "fix_reference_meshes")
            else:
                ibox = col.box()
                bcol = ibox.column(align=True)
                brow = bcol.row(align=True)
                brow.prop(updateRigProp, "transferJoints", text="with Joints")
                brow.prop(src_armature.RigProp, "JointType", text="")

                bcol = ibox.column(align=True)
                if ButtonCopyAvastar.sliders_allowed(context):
                    bcol.prop(src_armature.RigProp,"rig_use_bind_pose")
                bcol.prop(updateRigProp, "sl_bone_ends")
                bcol.prop(updateRigProp, "sl_bone_rolls")
                bcol.enabled = updateRigProp.transferJoints
                bcol.prop(updateRigProp, "fix_reference_meshes")

                if util.get_ui_level() > UI_ADVANCED:
                    bcol = ibox.column(align=True)
                    bcol.prop(updateRigProp, "show_offsets")
                    bcol.enabled = True

                col = col.column(align=True)                

                col.prop(updateRigProp, "use_male_shape")
                col.prop(updateRigProp, "use_male_skeleton")

        if not op:
            nicon = None
            note = None
            if len(targets) == 0:
                if "avastar" in src_armature:

                    if repair:
                        label = "Replace Rig"
                        nicon = ICON_INFO
                    else:
                        label = "Migrate Rig"
                        nicon = ICON_ERROR

                    if rig_version != None:
                        note = "%s %s(%s)" %("Avastar " if repair else "Outdated Rig", rig_version, rig_id, )
                        try:
                            major, minor, update = rig_version.split('.')
                        except:
                            major = "(1,2)"
                            minor = "0,1,..."
                            update= "0,1,..."
                            rig_id= "1,2,..."

                        msg = messages.panel_info_rigversion % (major, minor, update, rig_id)
                        rig_version='%s %s' % ('Avastar', rig_version)
                    else:
                        note = None
                        rig_version='unknown'


                    bones  = util.get_modify_bones(src_armature)
                    origin = bones.get("Origin")
                    abox = None
                    if origin and Vector(origin.head).magnitude > MIN_JOINT_OFFSET:
                        if not abox:
                            abox = box.box()
                            abox.label(text="Alignment Options", icon=ICON_ALIGN)
                        col = abox.column(align=True)
                        col.alert=True
                        row=col.row(align=True)
                        row.prop(updateRigProp, "adjust_origin", expand=False )
                        op=row.operator("avastar.adjust_armature_origin", icon=ICON_FILE_REFRESH, text="")
                        op.adjust_origin = updateRigProp.adjust_origin

                    if need_pelvis_fix:
                        if not abox:
                            abox = box.box()
                            abox.label(text="Alignment Options", icon=ICON_ALIGN)
                        col = abox.column(align=True)
                        col.alert = not updateRigProp.adjust_pelvis
                        icon = ICON_CHECKBOX_HLT if updateRigProp.adjust_pelvis else ICON_CHECKBOX_DEHLT
                        row = col.row(align=True)

                        row.alert = not updateRigProp.adjust_pelvis #mark red if adjustment is disabled
                        row.prop(updateRigProp, "adjust_pelvis",text="COG Align to", icon = icon)
                        row.prop(updateRigProp, "align_to_deform", text='')
                    if need_rig_fix:
                        if not abox:
                            abox = box.box()
                            abox.label(text="Alignment Options", icon=ICON_ALIGN)
                        col = abox.column(align=True)
                        col.alert = not updateRigProp.adjust_rig
                        icon = ICON_CHECKBOX_HLT if updateRigProp.adjust_rig else ICON_CHECKBOX_DEHLT
                        row = col.row(align=True)

                        row.prop(updateRigProp, "adjust_rig",text="Rig Align to", icon = icon)
                        row.prop(updateRigProp, "align_to_rig", text='')
                        if util.get_ui_level() > UI_ADVANCED:
                            col.prop(updateRigProp, "snap_collision_volumes")
                            col.prop(updateRigProp, "snap_attachment_points")

                    if abox:
                        col  = box.column()

                    col.alert=False                    
                    col.separator()
                    col.prop(updateRigProp, "sl_bone_rolls")
                    col.prop(updateRigProp, "applyRotation")
                    col.prop(updateRigProp, "mesh_repair")
                    col.prop(updateRigProp, "structure_repair")

                    if ButtonCopyAvastar.sliders_allowed(context):
                        if joint_count == 0:
                            text = "Check for Joint edits"
                        else:
                            text = "Keep Joint Edits"

                        col = box.column(align=True)
                        col.prop(updateRigProp, "transferJoints", text=text)


                        if updateRigProp.transferJoints:
                            col = box.column(align=True)
                            row=col.row(align=True)
                            row.label(text='',icon=ICON_BLANK1)
                            row.prop(src_armature.RigProp, "generate_joint_ik")
                            row=col.row(align=True)
                            row.label(text='',icon=ICON_BLANK1)
                            row.prop(src_armature.RigProp, "generate_joint_tails")
                        
                        col = box.column(align=True)
                        col.prop(updateRigProp, "preserve_bone_colors")
                        col.prop(updateRigProp, "fix_reference_meshes")

                        if util.get_ui_level() > UI_ADVANCED:
                            col = box.column(align=True)
                            col.prop(updateRigProp, "show_offsets")
                            col.enabled = True

                else:
                    label = "Convert to Avastar Rig"
            else:
                col.prop(updateRigProp, "applyRotation")
                label="Copy to Avastar Rig"

            col = box.column(align=True)
            row = col.row(align=True)

            props = row.operator("avastar.copy_rig", text=label)
            row.prop(updateRigProp,"apply_pose", icon=ICON_FREEZE, text='')


            if "avastar" in src_armature:
                pass
            else:
                props.srcRigType    = updateRigProp.srcRigType

            props.up_axis       = updateRigProp.up_axis
            props.tgtRigType    = updateRigProp.tgtRigType
            props.JointType     = updateRigProp.JointType
            props.apply_pose    = updateRigProp.apply_pose
            props.adjust_origin = updateRigProp.adjust_origin
            props.bone_repair   = updateRigProp.bone_repair
            props.mesh_repair   = updateRigProp.mesh_repair
            props.show_offsets  = updateRigProp.show_offsets
            props.sl_bone_ends  = updateRigProp.sl_bone_ends
            props.sl_bone_rolls = updateRigProp.sl_bone_rolls
            
            if util.is_linked_hierarchy([src_armature]) or util.is_linked_hierarchy(all_mesh):
                row.enabled = False
                col = box.column(align=True)
                col.label(text="Linked parts", icon=ICON_ERROR)




            if note:
                col = box.column(align=True)
                row = col.row(align=True)
                op=row.operator("avastar.generic_info_operator", text='', icon=ICON_INFO, emboss=False)
                op.msg=msg
                op.url="/help/armature-info/"
                op=row.operator("avastar.generic_info_operator", text=note, emboss=False)
                op.msg=msg
                op.url="/help/armature-info/"

            col = box.column(align=True)
            if len(targets) > 0:

                def list_arm(context, arm, col):
                    if arm == context.object:
                        icon = ICON_OUTLINER_OB_ARMATURE
                        text = "Source: %s " % arm.name
                    else:
                        icon = ICON_ARMATURE_DATA
                        text = "Target: %s" % arm.name
                    col.label(text=text, icon=icon)

                list_arm(context, src_armature, col)
                for arm in targets:
                    list_arm(context, arm, col)

            if rig_version:
                row = col.row(align=True)
                row.label(text="Rig Version", icon=ICON_BLANK1)
                row.label(text=rig_version)

            if rig_id:
                row = col.row(align=True)
                row.label(text="Rig ID", icon=ICON_BLANK1)
                row.label(text=str(rig_id))

            if "avastar" in src_armature:
                row = col.row(align=True)
                row.label(text="Joint offsets", icon=ICON_BLANK1)
                row.label(text=str(joint_count))

            row = col.row(align=True)
            row.label(text="Custom mesh", icon=ICON_BLANK1)
            row.label(text=str(custom_count))

            row = col.row(align=True)
            row.label(text="System mesh", icon=ICON_BLANK1)
            row.label(text=str(system_count))

    def roll_neutral_rotate(self, context, arm, rot, srot):
            print("Transfer(sl): Rotate Armature: [%s] %s (preserving boneroll)" % (arm.name, srot))




            arm.matrix_world = mulmat(arm.matrix_world, rot)
            bpy.ops.object.select_all(action='DESELECT')
            util.object_select_set(arm, True)
            bpy.ops.object.transform_apply(rotation=True)




            util.ensure_mode_is("OBJECT")
            util.update_view_layer(context)

    def rig_rotate(self, context, arm, rot, srot):
            log.debug("Transfer(sl): Rotate Armature: [%s] %s " % (arm.name, srot))

            arm.matrix_world = mulmat(arm.matrix_world, rot)
            bpy.ops.object.select_all(action='DESELECT')
            util.object_select_set(arm, True)
            bpy.ops.object.transform_apply(rotation=True)

    def freeze_armature(self, context, armobj):
        log.debug("Transfer(sl): Freeze bound meshes to current pose (%s)" % armobj.name)
        objs = util.get_animated_meshes(context, armobj)
        log.info("| Freezing %d animated meshes" % len(objs))
        objs = mesh.unbind_from_armature(self, context, objs, freeze=True)
        if objs:
            log.info("| Unparented %d animated meshes" % len(objs))
        else:
            log.info("| No meshes selected for Unparent")
        log.info("| Apply Source armature pose as new restpose (%s)" % armobj.name)
        util.set_active_object(context, armobj)
        omode = util.ensure_mode_is("POSE")
        bpy.ops.pose.armature_apply()
        util.ensure_mode_is(omode)
        return objs


    def copy_skeletons(self, context, src_armature, target_armatures, src_rig_type, tgt_rig_type, transfer_joints=True, sync=True, bone_store=None):

        log.info("| Transfer from %s armature [%s] to %d target armatures" 
              % (src_armature.RigProp.RigType, src_armature.name,len(target_armatures)))

        for tgt_armature in target_armatures:
            if self.handleTargetMeshSelection in ["HIDE","DELETE"]:
                self.prepare_avastar_meshes(context, tgt_armature)
            self.copy_skeleton(context, src_armature, tgt_armature, src_rig_type, tgt_rig_type, bone_store, transfer_joints, sync)

    def prepare_avastar_meshes(self, context, tgt_armature):
        if self.handleTargetMeshSelection =='DELETE':
            log.info("| Delete children from [%s]" % (tgt_armature.name) )
            util.remove_children(tgt_armature, context)
        else:
            log.info("| Hide children in %s" % (tgt_armature.name) )
            for obj in util.getChildren(tgt_armature, type=None, visible=True):
                util.object_hide_set(obj, True)

    def cleanup_slider_info(self, context, subset, tgt_armature):
        log.info("| Cleanup slider info: processing %d objects" % (len(subset)) )
        scene = context.scene
        arms = [tgt_armature]
        objs = []
        for obj in subset:
            if not obj.data.shape_keys:
                log.info("| Object %s has no shape keys" % (obj.name) )
                continue

            keyblocks = obj.data.shape_keys.key_blocks
            if len(keyblocks) == 0:
                log.warning("| Object %s has an Empty Shape key list" % (obj.name) )
                continue

            if REFERENCE_SHAPE in keyblocks or \
               MORPH_SHAPE in keyblocks:
                objs.append(obj)

        if len(objs) > 0:
            log.info("| Apply Sliders to %d Custom objects" % (len(objs)) )
            mesh.ButtonApplyShapeSliders.exec_imp(context, arms, objs)

    def move_objects_to_target(self, context, sources, tgt_armature, source_rig_type, src_armature = None):

        if not sources:
            return



        def get_custom_set(sources, container):
            if not sources:
                return []
            return [s for s in sources if not ('avastar-mesh' in s or (container and s.parent == container))]

        def get_system_set(sources, container):
            if not sources:
                return []
            return [s for s in sources if 'avastar-mesh' in s or (container and s.parent == container)]

        src_container = find_avatar_mesh_container(context, src_armature)

        custom_set = get_custom_set(sources, src_container)
        system_set = get_system_set(sources, src_container)


        if len(custom_set) > 0:
            log.warning("|  Move %d Custom meshes to %s %s" % (len(custom_set), tgt_armature.type, tgt_armature.name) )
            self.move_subset_to_target(context, custom_set, tgt_armature, source_rig_type, tgt_armature)
            self.cleanup_slider_info(context, custom_set, tgt_armature)

        if len(system_set) > 0:
            tgt_container = get_avatar_mesh_container(context, tgt_armature, "", src_container)
            log.warning("|  Move %d Avastar meshes to %s %s" % (len(system_set), tgt_armature.type, tgt_container.name) )

            if tgt_container == src_container:
                tgt_container.parent = tgt_armature
                for obj in system_set:
                    for mod in [mod for mod in obj.modifiers if mod.type=='ARMATURE']:
                        mod.object=tgt_armature
            else:
                chide = util.object_hide_get(tgt_container)
                cselect = util.object_select_get(tgt_container)
                chselect = tgt_container.hide_select
                chrender = tgt_container.hide_render

                util.object_hide_set(tgt_container, False)
                util.object_select_set(tgt_container, False)
                tgt_container.hide_select = False
                tgt_container.hide_render = False

                self.move_subset_to_target(context, system_set, tgt_armature, source_rig_type, tgt_container)

                util.object_hide_set(tgt_container, chide)
                util.object_select_set(tgt_container, cselect)
                tgt_container.hide_select = chselect
                tgt_container.hide_render = chrender

    def move_subset_to_target(self, context, sources, tgt_armature, source_rig_type, tgt_parent):
        with set_context(context, tgt_armature, 'OBJECT'):

            scene = context.scene
            curloc = util.get_cursor(context)
            util.set_cursor(context, tgt_armature.location)

            log.warning("|  Move %d Objects to %s %s" % (len(sources), source_rig_type, tgt_parent.name) )

            bpy.ops.object.select_all(action='DESELECT')
            select_states = util.get_select_and_hide(sources+[tgt_parent], select=False, hide_select=False, hide=False, hide_viewport=False)

            newsources = []
            for obj in sources:

                src_parent = obj.parent
                if not self.inplace_transfer:
                    log.warning("|- Copy Source [%s]" % (obj.name) )


                    dupobj = obj.copy()
                    dupobj.data = obj.data.copy()

                    util.link_object(context, dupobj)
                    obj = dupobj

                for mod in [mod for mod in obj.modifiers if mod.type=='ARMATURE']:
                    mod.object=tgt_armature

                util.set_active_object(context, obj)
                util.object_select_set(obj, True)
                hidden = util.object_hide_get(obj)
                util.object_hide_set(obj, False)

                if src_parent:
                    obj.matrix_world   = mulmat(tgt_parent.matrix_local, obj.matrix_parent_inverse.inverted(), obj.matrix_local)
                    newsources.append(obj)
                    loc = obj.location
                    log.debug("|- Parenting object %s to %s at %s" % (obj.name, tgt_parent.name, loc) )

                if source_rig_type == 'SL':
                    M = obj.matrix_world
                    R = Matrix() if context.scene.UpdateRigProp.up_axis == 'Z' else Ry90I
                    M = mulmat(M, R, Rz90)
                    obj.matrix_world = M
                    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

                util.set_active_object(context, tgt_armature)
                util.object_select_set(tgt_armature, True)
                bpy.ops.object.parent_set()

                util.set_active_object(context, obj)
                util.tag_addon_revision(obj)
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                util.object_hide_set(obj, hidden)

                log.info("|- (%s) Converting Weight Groups on %s:%s" % (source_rig_type, tgt_armature.name, obj.name))
                rig.convert_weight_groups(tgt_armature, obj, armature_type=source_rig_type)

                have_armature_modifier=False
                for mod in [mod for mod in obj.modifiers if mod.type=='ARMATURE']:
                    mod.object = tgt_armature
                    have_armature_modifier = True

                if not have_armature_modifier:
                    mod = util.create_armature_modifier(obj, tgt_armature, name="Armature", preserve_volume=False)

                util.object_select_set(obj, False)

            bpy.ops.object.select_all(action='DESELECT')
            for obj in newsources:
                util.object_select_set(obj, True)
                util.object_hide_set(obj, False)
            util.object_select_set(tgt_parent, True) 
            util.set_active_object(context, tgt_parent)
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

            log.warning("|  Parented %d meshes to %s" % (len(tgt_parent.children), tgt_parent.name) )
            util.set_cursor(context, curloc)
            bpy.ops.object.select_all(action='DESELECT')
            util.set_select_and_hide(context, select_states)

    def adjust_to_manuellab_rig(self, context, src_armature, tgt_armature):

        def get_center(verts):
            xmin = xmax = verts[0].co[0]
            ymin = ymax = verts[0].co[1]
            zmin = zmax = verts[0].co[2]

            for v in verts:
                co = v.co
                xmin = min(co[0], xmin)
                xmax = max(co[0], xmax)
                ymin = min(co[1], ymin)
                ymax = max(co[1], ymax)
                zmin = min(co[2], zmin)
                zmax = max(co[2], zmax)

            x = (xmin + xmax) / 2
            y = (ymin + ymax) / 2
            z = (zmin + zmax) / 2

            return Vector((x,y,z))        

        log.warning("Adjust Manuellab Rig, context is target armature: %s : %s" % (context.mode, context.object.name) )
        try:
            context.space_data.show_relationship_lines = False
        except:
            pass
        util.ensure_mode_is("EDIT")
        bones       = tgt_armature.data.edit_bones



        pelvis      = bones['Pelvis']
        tinker   = bones['Tinker']
        torso       = bones['Torso']
        cog         = bones['COG']
        torso.head  = pelvis.tail


        cog.head    = pelvis.tail
        cog.tail[2] = pelvis.tail[2]
        tinker.head = torso.head
        log.info("Transfer(armature): Move torso head to pelvis tail!")

        try:
            hi0L = bones['HandIndex0Left']
            ht1L = bones['HandThumb1Left']
            hi0L.head = ht1L.head
            hi0R = bones['HandIndex0Right']
            ht1R = bones['HandThumb1Right']
            hi0R.head = ht1R.head
        except:
            pass

        try:
            log.info("Transfer(armature): Fixing the eyes ...")
            log.info("Transfer(armature): scanning %d children ..." % (len(src_armature.children)) )
            eyes = [c for c in src_armature.children if 340 < len(c.data.vertices) < 360]
            log.info("Found %d eye candidates" % len(eyes) )
            mal_eye = None
            for eye in eyes:
                verts = eye.data.vertices
                if verts[0].co[0] < 0: 
                    continue # Not the left eye

                log.info("Transfer(armature): Found left eye candidate %s" % eye.name)
                mal_eye = get_center(verts)
                log.info("Transfer(armature): Found left eye at %s" % mal_eye)

                ava_eye = bones['EyeLeft'].head
                diff = ava_eye - mal_eye
                scale_x = mal_eye[0] / ava_eye[0]
                trans_y = mal_eye[1] - ava_eye[1]
                trans_z = mal_eye[2] - ava_eye[2]
                flul = bones['FaceLipUpperLeft'].head
                flcl = bones['FaceLipCornerLeft'].head
                dlip = flul[2] - flcl[2]

                for bone in [b for b in bones if b.name.startswith('Face') or b.name.startswith('Eye') or b.name.startswith('ikFace')  ]:

                    bone.head[0] *= scale_x
                    bone.head[1] += trans_y
                    bone.head[2] += trans_z
                    bone.tail[0] *= scale_x
                    bone.tail[1] += trans_y
                    bone.tail[2] += trans_z
                    if bone.name.startswith('FaceLip'):
                        bone.tail[2] += dlip
                        bone.head[2] += dlip
                    if bone.name.startswith('FaceEyebrowInner'):
                        bone.head[1] -= 0.005
                        bone.tail[1] -= 0.005

                break # No need to continue the loop, face is adjusted
        
        except:
             log.info("Transfer(armature): Can not adjust eye bones")

        try:
            log.info("Transfer(armature): Fixing the face IK ...")
            fluc = bones['FaceLipUpperCenter'].head
            fllc = bones['FaceLipLowerCenter'].head
            lipik_z = 0.5*(fluc[2]+fllc[2])
            bones['ikFaceLipShapeMaster'].head[2] = lipik_z
            bones['ikFaceLipShape'      ].head[2] = lipik_z
            bones['ikFaceLipShapeMaster'].tail[2] = lipik_z
            bones['ikFaceLipShape'      ].tail[2] = lipik_z

        except:
            log.info("Transfer(armature): Can not adjust face bones")

        util.ensure_mode_is("POSE")
        try:
            log.info("Transfer(armature): Fixing the ik Hand Controllers ...")
            const.adjust_custom_shape(tgt_armature.pose.bones['ikWristRight'],   armature_type)
            const.adjust_custom_shape(tgt_armature.pose.bones['ikWristLeft'],    armature_type)
            const.adjust_custom_shape(tgt_armature.pose.bones['ikFaceLipShape'], armature_type)
            const.adjust_custom_shape(tgt_armature.pose.bones['Tinker'],      armature_type)
        except:
            log.info("Transfer(armature): Can not adjust ik Wrist control bones")

    def transfer_joint_info(self, context, src_armature, tgt_armature, src_rig_type, bone_store, sync):

        def get_avastar_bone_id(key, ebones):

            bid = key #if 'avastar' in src_armature else map_sl_to_Avastar(key, src_rig_type, all=False)
            if bid is None:
                log.debug("Transfer(armature): - Ignore source bone [%s] (not supported in Target)" % (key) )
                return None
            if not bid in ebones:
                log.debug("Transfer(armature): Miss [%s] to [%s]" % (key, bid) )
                return None
            return bid

        def copy_default_attributes(tbone, sbone):
            attributes = [JOINT_O_HEAD_ID, JOINT_OFFSET_HEAD_ID, JOINT_O_TAIL_ID, JOINT_OFFSET_TAIL_ID, 'scale']
            for attr in attributes:
                val = tbone.get(attr)
                if val:
                    continue

                val = sbone.get(attr)
                if val:
                    tbone[attr] = val

        def set_bone_parent(bid, pbid, ebones):
            if not pbid:
                return

            tgt_ebone = ebones.get(bid)
            if not tgt_ebone:
                return

            if tgt_ebone.name[0] == 'm':
                return

            tgt_pebone= ebones.get(pbid)
            if not tgt_pebone:
                return


            tgt_ebone.parent = tgt_pebone
            return

        def copy_bone_store(bone_names, ebones, pbones, bone_store, src_rig_type):
            has_bind_data = False
            for key in bone_names:
                bone_data = bone_store.get(key)
                if not bone_data:
                    if key.startswith('mSpine'):
                        log.warning("Fit bone %s into rig" % key)
                        bone_data = fit_spine_to_rig(key, ebones, pbones)
                    else:
                        log.debug("Bone %s not in source rig (ignore)" % key)
                        continue

                key = bone_data[BONE_DATA_NAME]
                can_deform = key.startswith('m') or not ebones.get('m'+key)
                can_animate = not key.startswith('m')

                bone_id  = key  if 'avastar' in src_armature else map_sl_to_Avastar(key, src_rig_type, all=False)
                if bone_id is None or not bone_id in ebones:
                    continue

                tgt_is_connected = None
                src_parent_key= bone_data[BONE_DATA_PARENT]
                if src_parent_key:
                    tgt_parent_key = src_parent_key if 'avastar' in src_armature else map_sl_to_Avastar(src_parent_key, src_rig_type, all=False)
                    parent_bone_id, tgt_is_connected = data.fixate_special_bone_parent(bone_id, tgt_parent_key)
                    if tgt_parent_key != parent_bone_id:
                        set_bone_parent(bone_id, parent_bone_id, ebones)
                else:
                    log.warning("copy bone store: key:%s bone_id:%s has no parent assigned" % (key, bone_id) )

                tgt_ebone = ebones.get(bone_id)
                tgt_pbone = pbones.get(bone_id)

                if tgt_is_connected == None:
                    tgt_is_connected = bone_data[BONE_DATA_CONNECT]

                rig.set_connect(tgt_ebone, tgt_is_connected)



                head, tail, roll, matrix = copy_bone_data(tgt_armature, bone_data, tgt_ebone, tgt_pbone)
                has_bind_data |= add_custom_bindpose(tgt_ebone, src_armature.data.bones.get(key))
                add_contraint_data(tgt_pbone, bone_data[BONE_DATA_CONSTRAINT])
                add_iklimits(tgt_pbone, bone_data[BONE_DATA_IKLIMITS])

                if key!= bone_id and key in ebones:




                    tgt_sebone = ebones[key]
                    tgt_sebone['tag']=True
                    tgt_sebone.roll   = roll
                    tgt_sebone.matrix = matrix.copy()
                    tgt_sebone.head = head.copy()
                    tgt_sebone.tail = tail.copy()
                    if tgt_sebone.use_connect and tgt_sebone.parent:
                        if (head - tgt_sebone.parent.head).magnitude < MIN_BONE_LENGTH:
                            log.error("Can not set %s.parent.tail to %s.head at %s" % (tgt_sebone.parent.name, tgt_sebone.name, head) ) 
                        else:
                            tgt_sebone.parent.tail  = head.copy()

                        if (head - tgt_ebone.parent.head).magnitude < MIN_BONE_LENGTH:
                            log.error("Can not set %s.parent.tail to %s.head at %s" % (tgt_ebone.parent.name, tgt_ebone.name, head) ) 
                        else:
                            tgt_ebone.parent.tail  = head.copy()

                    has_bind_data |= add_custom_bindpose(tgt_sebone, src_armature.data.bones.get(key))
                    log.info("Move Bone %s to Bone %s" % (key, bone_id) )


                if src_rig_type == MANUELMAP:
                    const.adjust_custom_shape(tgt_armature.pose.bones[tgt_ebone.name], src_rig_type)

                    if bone_id.startswith("Hand"):
                        sign = -1 if bone_id.endswith("Left") else 1;
                        v = Vector((0.25*sign if bone_id.startswith("HandThumb") else 0, 0, 0.5))
                        tgt_ebone.align_roll(v)


                        continue
                    if bone_id in SLARMBONES:
                        tgt_ebone.align_roll((0,0,1))
                        continue
                    if bone_id in SLLEGBONES:
                        tgt_ebone.align_roll((0,1,0))
                        continue

            copy_deform_flag(ebones, bone_store)
            return has_bind_data

        def copy_deform_flag(ebones, bone_store):
            for bone_data in bone_store.values():
                bid = bone_data[BONE_DATA_NAME]
                if bid not in ebones:
                    continue

                tgt_mbone = ebones.get(bid)
                tgt_ebone = ebones.get(bid[1:])

                if tgt_ebone:
                    tgt_ebone.use_deform = False

                tgt_mbone.use_deform = bone_data[BONE_DATA_DEFORM]
                tgt_mbone.layers[B_LAYER_DEFORM] = tgt_mbone.use_deform


        def clear_connected(ebones):
            connected = {}
            for bone in ebones:
                if bone.use_connect:
                    connected[bone.name]=bone
                    bone.use_connect=False
            return connected

        def reconnect(connected):
            for bname,bone in connected.items():
                if bone.parent:
                    bone.parent.tail = bone.head.copy()
                    bone.use_connect = True

        def adjust_bone_group(tgt_armature, bone_data, ebone, pbone):
            bgroups = tgt_armature.pose.bone_groups
            bone_group_name = bone_data[BONE_POSE_GROUP]
            bone_name = bone_data[BONE_DATA_NAME]


            if bone_group_name:
                colorset = bone_data[BONE_POSE_COLORSET]
                log.debug("Assign bone group %s with color set %s" % (bone_group_name, colorset) )
                bone_group = bgroups.get(bone_group_name)
                if not bone_group:
                    bone_group = bgroups.new(name=bone_group_name)
                pbone.bone_group = bone_group
                if colorset and self.preserve_bone_colors:
                    bone_group.color_set=colorset
            else:
                log.debug("No bone group assigned to bone %s" % (bone_name) )

            group_index = pbone.bone_group_index
            if self.show_offsets:
                restpose_head, rtail = rig.get_sl_restposition(tgt_armature, ebone, use_cache=True)
                restpose_tail = restpose_head + rtail

                util.gp_draw_line(context, restpose_head, ebone.head, pname='avastar', lname='avastar', color_index = group_index)
                util.gp_draw_line(context, restpose_tail, ebone.tail, pname='avastar', lname='avastar', color_index = group_index)

        def copy_bone_data(tgt_armature, bone_data, ebone, pbone):
            head = bone_data[BONE_DATA_HEAD]
            tail = bone_data[BONE_DATA_TAIL]
            head = PVector(head) if head else None
            tail = PVector(tail) if tail else None

            adjust_bone_group(tgt_armature, bone_data, ebone, pbone)

            ebone['tag'] = True
            if bone_data[BONE_DATA_ROLL] != None:
                ebone.roll = bone_data[BONE_DATA_ROLL]
            if bone_data[BONE_DATA_MATRIX] != None:
                ebone.matrix = bone_data[BONE_DATA_MATRIX]
            if head:
                ebone.head = head.copy() # Here we copy head and tail of the source bone
            if tail:
                ebone.tail = tail.copy() # to the target bone
            if bone_data[BONE_DATA_HIDE] != None:
                ebone.hide = bone_data[BONE_DATA_HIDE]
            if bone_data[BONE_POSE_ROTATION_MODE] != None:
                pbone.rotation_mode = bone_data[BONE_POSE_ROTATION_MODE]

            return ebone.head, ebone.tail, ebone.roll, ebone.matrix


        def update_from_bone_store(ebones, pbones, bone_store):

            connected = clear_connected(ebones)
            bone_names = Skeleton.bones_in_hierarchical_order(tgt_armature)
            has_bind_data=False
            for key in bone_names:

                bone_data = bone_store.get(key)
                if not bone_data:
                    if key.startswith('mSpine'):
                        log.warning("Fit bone %s into rig" % key)
                        bone_data = fit_spine_to_rig(key, ebones, pbones)
                    else:
                        log.debug("Bone %s not in source rig (ignore)" % key)
                        continue

                old_is_connected = bone_data[BONE_DATA_CONNECT]
                bname = bone_data[BONE_DATA_NAME]
                if not bname in ebones:
                    continue

                dbone = ebones.get(bname)
                if not dbone:
                    continue

                pbone = pbones.get(bname)
                old_parent_name = bone_data[BONE_DATA_PARENT]
                if old_parent_name:
                    old_parent = ebones.get(old_parent_name, dbone.parent)
                else:
                    old_parent=None

                if old_parent != dbone.parent:

                    def delete_connected_pair(connected, bname):
                        del connected[bname]
                        if connected.get('m'+bname):
                            del connected['m'+bname]


                    if dbone.parent:
                        if dbone.parent.get("is_structure") and dbone.parent.parent == old_parent:
                            connected[dbone.name]=dbone
                        else:
                            dbone.parent = old_parent
                            if old_is_connected:
                                connected[dbone.name]=dbone
                            elif connected.get(bname):
                                delete_connected_pair(connected, bname)

                copy_bone_data(tgt_armature, bone_data, dbone, pbone)

                has_bind_data |= add_custom_bindpose(dbone, src_armature.data.bones.get(bname))
                add_contraint_data(pbone, bone_data[BONE_DATA_CONSTRAINT])
                add_iklimits(pbone, bone_data[BONE_DATA_IKLIMITS])

            reconnect(connected)
            copy_deform_flag(ebones, bone_store)
            return has_bind_data


        def fit_spine_to_rig(key, ebones, pbones):

            if key == 'mSpine1':
                bone_data = extract_bone_info('mPelvis', ebones, pbones)
                head = ebones['mPelvis'].tail
                tail = ebones['mPelvis'].head
                reference_parent_name = 'mPelvis'
            elif key == 'mSpine2':
                bone_data = extract_bone_info('mPelvis', ebones, pbones)
                head = ebones['mPelvis'].head
                tail = ebones['mPelvis'].tail
                reference_parent_name = 'mSpine1'
            elif key == 'mSpine3':
                bone_data = extract_bone_info('mTorso', ebones, pbones)
                head = ebones['mTorso'].tail
                tail = ebones['mTorso'].head
                reference_parent_name = 'mTorso'
            elif key == 'mSpine4':
                bone_data = extract_bone_info('mTorso', ebones, pbones)
                head = ebones['mTorso'].head
                tail = ebones['mTorso'].tail
                reference_parent_name = 'mSpine3'

            bone_data[BONE_DATA_NAME] = key
            bone_data[BONE_DATA_HEAD] = head
            bone_data[BONE_DATA_TAIL] = tail
            bone_data[BONE_DATA_MATRIX] = None
            bone_data[BONE_DATA_PARENT] = reference_parent_name
            bone_data[BONE_POSE_GROUP] = 'mSpine'
            bone_data[BONE_POSE_COLORSET] = 'THEME11'
            bone_data[BONE_DATA_CONNECT] = True
            bone_data[BONE_DATA_CONSTRAINT] = None
            bone_data[BONE_POSE_ROTATION_MODE] = None
            bone_data[BONE_DATA_HIDE] = None

            return bone_data

        def add_prop(tbone, sbone, key):
            v = sbone.get(key, None )
            if v != None:
                tbone[key]=v

        def add_bind_mat(tgt_armature, tbone, sbone):
            if 'bind_mat' in sbone:
                has_bind_data = True
                add_prop(tbone, sbone, 'bind_mat')
                add_prop(tbone, sbone, 'rest_mat')
            else:
                has_bind_data = False




            return has_bind_data

        def add_channel(tbone, sbone, type):
            add_prop(tbone, sbone, "%s_%s" % (type, 'x'))
            add_prop(tbone, sbone, "%s_%s" % (type, 'y'))
            add_prop(tbone, sbone, "%s_%s" % (type, 'z'))

        def add_custom_bindpose(tbone, sbone):
            if not (sbone and tbone):
                return False


            has_bind_data = add_bind_mat(tgt_armature, tbone, sbone)


            add_channel(tbone, sbone, 'restpose_loc')
            add_channel(tbone, sbone, 'restpose_rot')
            add_channel(tbone, sbone, 'restpose_scale')

            copy_default_attributes(tbone, sbone)

            if 'bind_mat' in tbone:
                array = Vector(tbone['rest_mat'])
                M = util.matrix_from_array(array)
                scale = M.to_scale()
                scale0 = tbone.get('scale0')
                scale0 = Vector(scale0) if scale0 else "undefined"
                tbone['scale0']=scale
                log.info("Changed bone scale %s to %s for bone %s" % (scale0, scale, tbone.name) )

            return has_bind_data

        def add_iklimits(tgt_pbone, iklimits):
            if iklimits == None:
                return

            tgt_pbone.use_ik_limit_x = iklimits[0]
            tgt_pbone.use_ik_limit_y = iklimits[1]
            tgt_pbone.use_ik_limit_z = iklimits[2]
        
        def add_contraint_data(tgt_pbone,const_info):

            #



            if const_info == None:
                return

            cursor = 0
            length = len(const_info)
            for cons in [c for c in tgt_pbone.constraints if c.type=='LIMIT_ROTATION']:
                while cursor < length and const_info[cursor][0] != 'LIMIT_ROTATION':
                    cursor += 1
                if cursor >= length:
                    break
                cons.influence = const_info[cursor][1]
                cons.mute = const_info[cursor][2]

        scene = context.scene
        active = util.get_active_object(context)
        amode  = active.mode

        log.info("|- Copy joints from armature [%s] (%s)" % (src_armature.name, src_armature.RigProp.RigType))
        log.info("|- Copy joints to   armature [%s] (%s)" % (tgt_armature.name, tgt_armature.RigProp.RigType))
        util.set_active_object(context, src_armature)

        util.ensure_mode_is("POSE")
        selected_bone_names = util.getVisibleSelectedBoneNames(src_armature)
        log.debug("Found %d selected bones in Armature %s" % (len(selected_bone_names), src_armature.name))
        layers = [l for l in src_armature.data.layers]
        for i in range(32): src_armature.data.layers[i]=True
        src_armature.data.layers = layers

        log.info("|- Transfer Bone locations from [%s]" % src_armature.name)
        log.info("|- Transfer Bone locations to   [%s]" % tgt_armature.name)
        util.set_active_object(context, tgt_armature)
        omode = util.ensure_mode_is("OBJECT")

        bpy.ops.avastar.unset_rotation_limits(True)







        tgt_armature.data.show_bone_custom_shapes = src_armature.data.show_bone_custom_shapes
        util.object_show_in_front(tgt_armature, util.object_show_in_front(src_armature))
        armature_util.set_display_type(tgt_armature, armature_util.get_display_type(src_armature))




        util.ensure_mode_is("EDIT")
        pbones = tgt_armature.pose.bones
        ebones = tgt_armature.data.edit_bones
        bgroups = tgt_armature.pose.bone_groups
        rig.reset_cache(tgt_armature)
        self.untag_boneset(ebones)





        bone_names = Skeleton.bones_in_hierarchical_order(tgt_armature)
        if src_rig_type == 'AVASTAR':
            has_bind_data = update_from_bone_store(ebones, pbones, bone_store)
        else:
            has_bind_data = copy_bone_store(bone_names, ebones, pbones, bone_store, src_rig_type)

        tgt_armature['has_bind_data'] = has_bind_data





        log.info("| Adjust Avastar Bones missing from Source Rig [%s] " % (src_armature.name))
        madjust_counter = 0
        cadjust_counter = 0

        for key in bone_names:


            if not (key[0] in ['m', 'a'] or key in SLVOLBONES):
                continue



            tgt_ebone = ebones[key]
            if 'tag' in tgt_ebone:
                continue
            if True:
                madjust_counter += 1
                log.debug("- Adjust bone %s" % tgt_ebone.name)

                parent = rig.get_parent_bone(tgt_ebone, with_structure=False)
                if not parent:
                    tgt_ebone['tag'] = True
                    continue
                if key[0:6] == 'mSpine':
                    log.debug("delay processing of %s" % (key) )
                    continue

                tgt_ebone['tag']=True
                head,   tail   = rig.get_sl_restposition(tgt_armature, tgt_ebone, use_cache=True)
                prhead, prtail = rig.get_sl_restposition(tgt_armature, parent, use_cache=True)

                log.debug("- adjust head:%s of bone [%s]" % (head, key))

                p_head   = parent.head
                p_tail   = parent.tail
                p_rest_v = Vector(prtail)
                p_v      = Vector(p_tail     - p_head)
                offset   = Vector(p_head     - prhead)
                Q        = p_rest_v.rotation_difference(p_v)

                t    = tail
                dt   = mulmat(Q, t)
                h    = head - prhead
                dh   = mulmat(Q, h)
                tgt_ebone.head = p_head         + dh
                tgt_ebone.tail = tgt_ebone.head + dt
                rig.reset_cache(tgt_armature, subset=[tgt_ebone])

                if key[0] == 'm':
                    cadjust_counter += 1
                    tgt_cbone = ebones[key[1:]]
                    if tgt_cbone.get('tag'):


                        tgt_ebone.head = tgt_cbone.head
                        tgt_ebone.tail = tgt_cbone.tail
                        log.debug("Adjust Deform Bone %s to Control Bone %s" % (tgt_ebone.name, tgt_cbone.name) )
                    else:


                        tgt_cbone.head = tgt_ebone.head
                        tgt_cbone.tail = tgt_ebone.tail
                        rig.reset_cache(tgt_armature, subset=[tgt_cbone])
                        log.debug("Adjust Control Bone %s to Deform Bone %s" % (tgt_cbone.name, tgt_ebone.name) )
                        tgt_cbone['tag']=True

                if self.show_offsets:
                    group_index = pbones[key].bone_group_index
                    util.gp_draw_line(context, head, tgt_ebone.head, pname='avastar', lname='avastar', color_index = group_index)






        ebones = tgt_armature.data.edit_bones
        mPelvis = ebones.get('mPelvis')
        mTorso = ebones.get('mTorso')
        mChest = ebones.get("mChest")
        Torso  = ebones.get('Torso')
        Chest = ebones.get("Chest")

        tgt_rigtype = tgt_armature.RigProp.RigType
        for key in bone_names:

            def adjust_spine_bone(tgt_ebone, head, tail, ebones, parent_name):
                tgt_ebone.head = head.copy()
                tgt_ebone.tail = tail.copy()
                if parent_name:
                    parent_bone = ebones.get(parent_name)
                    if parent_bone:
                        tgt_ebone.parent = parent_bone

            if not (key[0:6] == 'mSpine'):







                continue


            tgt_mbone = ebones[key]
            tgt_cbone = ebones[key[1:]]

            if not 'tag' in tgt_ebone:
                log.debug("processing of %s" % (key) )
                if key == 'mSpine1':
                    parent_name = 'Pelvis' if tgt_rigtype == 'EXTENDED' else None
                    adjust_spine_bone(tgt_mbone, mPelvis.tail, mPelvis.head, ebones, 'm'+parent_name)
                    adjust_spine_bone(tgt_cbone, mPelvis.tail, mPelvis.head, ebones,     parent_name)
                elif key == 'mSpine2':
                    parent_name = 'Spine1' if tgt_rigtype == 'EXTENDED' else None
                    adjust_spine_bone(tgt_mbone, mPelvis.head, mPelvis.tail, ebones, 'm'+parent_name)
                    adjust_spine_bone(tgt_cbone, mPelvis.head, mPelvis.tail, ebones,     parent_name)
                elif key == 'mSpine3':
                    parent_name = 'Torso' if tgt_rigtype == 'EXTENDED' else None
                    adjust_spine_bone(tgt_mbone, mTorso.tail, mTorso.head, ebones, 'm'+parent_name)
                    adjust_spine_bone(tgt_cbone, mTorso.tail, mTorso.head, ebones,     parent_name)
                else:
                    parent_name = 'Spine3' if tgt_rigtype == 'EXTENDED' else None
                    adjust_spine_bone(tgt_mbone, mTorso.head, mTorso.tail, ebones, 'm'+parent_name)
                    adjust_spine_bone(tgt_cbone, mTorso.head, mTorso.tail, ebones,     parent_name)

                tgt_mbone['tag'] = True
                tgt_cbone['tag'] = True
                rig.reset_cache(tgt_armature, subset=[tgt_cbone, tgt_mbone])

        log.info("| Adjusted %d Deform  Bones in target rig [%s]" % (madjust_counter, tgt_armature.name) )
        log.info("| Adjusted %d Control Bones in target rig [%s]" % (cadjust_counter, tgt_armature.name) )

        rig.adjustIKToRig(tgt_armature) # We get issues with the restpose otherwise
        log.info("| Adjusted IK Rig of rig [%s]" % (tgt_armature.name))

        if src_rig_type == MANUELMAP:
            self.adjust_to_manuellab_rig(context, src_armature, tgt_armature)
            log.info("| Adjusted Manuellab [%s]" % (tgt_armature.name))

        for i in range(32):
            tgt_armature.data.layers[i] = layers[i]

        transfer_constraints(context, tgt_armature, src_armature)
        log.info("| Adjusted Constraints of rig [%s]" % (tgt_armature.name))

        util.set_active_object(context, tgt_armature)
        util.ensure_mode_is(omode)
        util.set_active_object(context, active)
        util.ensure_mode_is(amode)

    def untag_boneset(self, bones):
        for b in bones:
            if 'tag' in b:
               del b['tag']

    def set_ik(self, src_armature, tgt_armature):

        tgt_armature.IKSwitchesProp.hinds_ik_enabled = src_armature.IKSwitchesProp.hinds_ik_enabled
        tgt_armature.IKSwitchesProp.legs_ik_enabled = src_armature.IKSwitchesProp.legs_ik_enabled
        tgt_armature.IKSwitchesProp.arms_ik_enabled = src_armature.IKSwitchesProp.arms_ik_enabled
        tgt_armature.IKSwitchesProp.face_ik_enabled = src_armature.IKSwitchesProp.face_ik_enabled

        tgt_armature.IKSwitchesProp.Enable_AltEyes = src_armature.IKSwitchesProp.Enable_AltEyes
        tgt_armature.IKSwitchesProp.Enable_Eyes = src_armature.IKSwitchesProp.Enable_Eyes


    def copy_skeleton(self, context, src_armature, tgt_armature, src_rig_type, tgt_rig_type, bone_store, transfer_joints=True, sync=True):

        STANDALONE_POSED = 0
        REMOVE_WEIGHTS = 1
        REMOVE_ARMATURE = 2
        HANDLE_ORIGINAL_MESH_SELECTION = 3
        JOIN_PARTS = 4

        def restore_mesh_copy_attributes(meshProp, original_attributes):
            meshProp.standalonePosed = original_attributes[STANDALONE_POSED]
            meshProp.removeWeights = original_attributes[REMOVE_WEIGHTS]
            meshProp.removeArmature = original_attributes[REMOVE_ARMATURE]
            meshProp.handleOriginalMeshSelection = original_attributes[HANDLE_ORIGINAL_MESH_SELECTION]
            meshProp.joinParts = original_attributes[JOIN_PARTS]
            
        def prepare_mesh_copy_attributes(meshProp):
            original_attributes = [
                meshProp.standalonePosed,
                meshProp.removeWeights,
                meshProp.removeArmature,
                meshProp.handleOriginalMeshSelection,
                meshProp.joinParts
            ]

            meshProp.standalonePosed=False
            meshProp.removeWeights=False
            meshProp.removeArmature=False
            meshProp.handleOriginalMeshSelection="DELETE"
            meshProp.joinParts=False

            return original_attributes

        def get_visible_layers_for(src_rig_type):
            if src_rig_type in ['SL', 'GENERIC']:
                layers = [ l in B_VISIBLE_LAYERS_SL for l in range(0,32)]                
            elif src_rig_type == 'MANUELLAB':
                layers = [l in B_VISIBLE_LAYERS_MANUEL for l in range(0,32)]
            else:
                layers = [l for l in src_armature.data.layers]
            return layers

        def adjust_cog(src_armature, tgt_armature):
            SRC_COG = src_armature.data.bones.get('COG')
            if not SRC_COG:
                Bones = data.get_reference_boneset(tgt_armature, tgt_armature.RigProp.RigType, tgt_armature.RigProp.JointType)
                BCOG = Bones.get('COG')
                if not BCOG:
                    log.warning("No COG Bone found in the Bones repository")
                    return

                omode = util.ensure_mode_is('EDIT')
                TGT_COG = tgt_armature.data.edit_bones.get('COG')
                if not TGT_COG:
                    log.warning("No COG Bone found in the Target Rig")
                    return

                t = Vector(BCOG.reltail)
                TGT_COG.head = TGT_COG.tail - t
                util.ensure_mode_is(omode)

        def copy_bone_layers(tgt_armature, src_armature):
            for i,l in enumerate(src_armature.data.layers):
                tgt_armature.data.layers[i]=l

        def copy_bonegroup_data(tgt_armature, bone_store):
            bgroups = tgt_armature.pose.bone_groups
            bone_names = Skeleton.bones_in_hierarchical_order(tgt_armature)
            for key in bone_names:
                pbone = tgt_armature.pose.bones.get(key)
                if pbone:
                    bone_data = bone_store.get(key)
                    if bone_data:
                        bone_group_name = bone_data[BONE_POSE_GROUP]
                        bone_name = bone_data[BONE_DATA_NAME]


                        if bone_group_name:
                            colorset = bone_data[BONE_POSE_COLORSET]
                            bone_group = bgroups.get(bone_group_name)
                            if bone_group and colorset:
                                bone_group.color_set=colorset

        util.progress_update(10, absolute=False)
        scene = context.scene
        active = util.get_active_object(context)
        amode = active.mode

        tgt_armature.RigProp.generate_joint_ik = src_armature.RigProp.generate_joint_ik
        tgt_armature.RigProp.generate_joint_tails = src_armature.RigProp.generate_joint_tails
        self.set_ik(src_armature, tgt_armature)

        if self.inplace_transfer:
            bones  = util.get_modify_bones(src_armature)
            origin = bones.get("Origin")
            origin_mismatch = origin != None and Vector(origin.head).magnitude > MIN_JOINT_OFFSET

            if "avastar" in src_armature and self.adjust_pelvis and rig.needTinkerFix(src_armature):
                rig.matchTinkerToPelvis(context, src_armature, alignToDeform=self.align_to_deform)

            children    = util.getChildren(src_armature)
            if origin_mismatch:

                if self.adjust_origin == 'ORIGIN_TO_ROOT':
                    util.transform_origin_to_rootbone(context, src_armature)
                    log.warning("| Transformed Origin to Root Bone in source Armature [%s]" % src_armature.name)
                else:
                    util.transform_rootbone_to_origin(context, src_armature)
                    log.warning("| Transformed Root Bone to Origin in source Armature [%s]" % src_armature.name)
            else:
                log.info("Clean rig: Origin matches to Root Bone")

            if len(children) > 0:
                util.ensure_mode_is("OBJECT")
                util.transform_origins_to_target(context, src_armature, children, V0)
            else:
                log.info("| Source Armature [%s] has no children (no need to adjust Origin")

        log.info("| Transfer Skeleton from armature [%s] (%s)" % (src_armature.name, src_armature.RigProp.RigType))
        log.info("| Transfer Skeleton to   armature [%s] (%s)" % (tgt_armature.name, tgt_armature.RigProp.RigType))

        matrix_world = src_armature.matrix_world.copy()
        util.set_cursor(context, src_armature.location)
        
        util.ensure_mode_is("OBJECT")
        bpy.ops.object.select_all(action='DESELECT')

        util.progress_update(10, absolute=False)

        rot= Rz90 if src_rig_type == SLMAP else Matrix()
        bone_store = extract_bone_data(context, src_armature, bone_store, rot)

        util.progress_update(10, absolute=False)
        util.ensure_mode_is("OBJECT")
        if transfer_joints:
            self.transfer_joint_info(context, src_armature, tgt_armature, src_rig_type, bone_store, sync)
        else:
            log.info("|- Omitt joint info transfer from [%s] to [%s]" % (src_armature.name, tgt_armature.name) )

            if self.preserve_bone_colors:
                copy_bonegroup_data(tgt_armature, bone_store)

        util.ensure_mode_is("OBJECT")
        util.progress_update(10, absolute=False)

        if self.inplace_transfer:

            name = src_armature.name
            if self.active==src_armature:
                self.active = tgt_armature


            src_armature.name = "%s_del" % name
            tgt_armature.name = name
            if src_rig_type == MANUELMAP:
                tgt_armature.name = tgt_armature.name.replace("skeleton_humanoid","Avatar_")

        util.progress_update(10, absolute=False)
        util.set_active_object(context, tgt_armature)

        omode=util.ensure_mode_is('POSE')
        bpy.ops.pose.transforms_clear()
        util.ensure_mode_is('OBJECT')

        if src_rig_type == MANUELMAP:
            tgt_armature.data.layers[B_LAYER_SPINE]=True



        bpy.ops.object.select_all(action='DESELECT')

        util.update_view_layer(context)
        original_mesh_attributes = prepare_mesh_copy_attributes(scene.MeshProp)

        util.ensure_mode_is("EDIT")

        if self.inplace_transfer:
            tgt_armature.data.show_bone_custom_shapes = False
            util.object_show_in_front(tgt_armature, True)
            armature_util.set_display_type(tgt_armature, armature_util.get_display_type(src_armature))
            tgt_armature.matrix_world                 = matrix_world

            if self.sl_bone_ends:
                log.info("Adjust imported bone ends to Match the Avastar default")
                ebones = tgt_armature.data.edit_bones
                self.untag_boneset(ebones)

                for bone_data in bone_store.values():
                    key = bone_data[BONE_DATA_NAME]
                    if key in ebones:
                        tgt_ebone = ebones[key]
                        if tgt_ebone and tgt_ebone.parent and not Skeleton.has_connected_children(tgt_ebone):
                            parent = tgt_ebone.parent

                            rig.reset_cache(tgt_armature, subset=[tgt_ebone, parent])
                            d, rtail   = rig.get_sl_restposition(tgt_armature, tgt_ebone, use_cache=True)
                            cu_tail    = Vector(parent.tail) - Vector(parent.head)
                            d, sl_tail = rig.get_sl_restposition(tgt_armature, parent, use_cache=True)

                            M = sl_tail.rotation_difference(cu_tail).to_matrix()
                            dv = mulmat(M, rtail)
                            if dv.magnitude > MIN_BONE_LENGTH:
                                tgt_ebone['tag']=True
                                tgt_ebone.tail = tgt_ebone.head + dv
                                log.debug("Fixing bone tail for bone [%s]" % tgt_ebone.name)
                            else:
                                log.warning("Cant fix bone tail for bone [%s] (bone too short)" % tgt_ebone.name)

                log.info("Adjust not imported bone ends to Match imported bone ends")
                for bone_data in bone_store.values():
                    key = bone_data[BONE_DATA_NAME]
                    if key in ebones:
                        bid = key[1:] if key[0] == 'm' else 'm'+key
                        tbone = ebones.get(bid,None)
                        if tbone and not 'tag' in tbone:
                            tbone['tag'] = True
                            ebone = ebones.get(key)
                            tbone.tail = ebone.tail
                            log.debug("Adjusted bone %s to imported bone %s" % (tbone.name, ebone.name) )






            if "avastar" in src_armature and self.adjust_rig and rig.needRigFix(src_armature):

                rig.adjustAvatarCenter(tgt_armature)
                rig.adjustSLToRig(tgt_armature) if self.align_to_rig == 'DEFORM_TO_ANIMATION' else rig.adjustRigToSL(tgt_armature)
                rig.adjustIKToRig(tgt_armature)

                if self.snap_collision_volumes:
                    rig.adjustVolumeBonesToRig(tgt_armature)
                if self.snap_attachment_points:
                    rig.adjustAttachmentBonesToRig(tgt_armature)

            sync = False


            rig.fix_avastar_armature(context, tgt_armature)
            adjust_cog(src_armature, tgt_armature)
            copy_bone_layers(tgt_armature, src_armature)

            if self.transferJoints:
                with_ik = tgt_armature.RigProp.generate_joint_ik
                with_tails = tgt_armature.RigProp.generate_joint_tails
                delete_only = False#not ButtonCopyAvastar.sliders_allowed(context)
                bind.cleanup_binding(context, tgt_armature, sync, with_ik, with_tails, delete_only, only_meta=True)
            else:
                bind.remove_binding(context, tgt_armature, sync=sync)

            util.ensure_mode_is("POSE")
            log.debug("Transfer Select state of bones to Armature [%s]" % (tgt_armature.name) )
            for bone in tgt_armature.data.bones:
                bone.select_head = False
                bone.select_tail = False
                bone.select      = False

            for bone_data in  bone_store.values():
                key = bone_data[BONE_DATA_NAME]
                bid =  map_sl_to_Avastar(key, src_rig_type, all=False)
                if bid and bid in tgt_armature.data.bones:
                    bone = tgt_armature.data.bones[bid]
                    bone.select = bone_data[BONE_DATA_SELECT]
                    bone.hide = bone_data[BONE_DATA_HIDE]

        util.ensure_mode_is('OBJECT')
        if self.transferJoints and not self.inplace_transfer and not 'avastar' in src_armature:
            log.info("|- Roll neutral rotation of [%s]" % (src_armature.name) )
            roll_neutral_rotate(src_armature, Rz90I)
        util.ensure_mode_is(omode)


        util.copy_collection_visibility(context, tgt_armature, src_armature)

        restore_mesh_copy_attributes(scene.MeshProp, original_mesh_attributes)
        util.set_active_object(context, active)
        util.ensure_mode_is(amode)

    def find_transfer_sources(self, context):
        scene = context.scene
        self.sources  = [obj for obj in self.selected if util.object_visible_get(obj, context=context) and is_animated_mesh(obj, self.src_armature)]

        self.use_all_sources = (len(self.sources) == 0)
        if self.use_all_sources:
           if self.inplace_transfer:
               self.sources = [obj for obj in scene.objects if is_animated_mesh(obj, self.src_armature)]
           else:
               self.sources = [obj for obj in scene.objects if util.object_visible_get(obj, context=context) and is_animated_mesh(obj, self.src_armature)]

    def init(self, context):

        self.src_armature = util.get_armature(context.object)
        if not self.src_armature:
            return False

        scene = context.scene
        self.active = util.get_active_object(context)
        if not self.active:
            return False

        self.active_mode = self.active.mode
        self.sources = None
        self.use_all_sources = False 

        updateRigProp = scene.UpdateRigProp

        if 'avastar' in self.src_armature:
            self.srcRigType = 'AVASTAR'
        else:
            self.srcRigType = updateRigProp.srcRigType

        if 'avastar' in self.src_armature and self.src_armature['avastar'] > 2:
            self.rig_display_type = self.src_armature.ObjectProp.rig_display_type
        else:
            self.rig_display_type = 'ALL'


        if self.srcRigType == 'AVASTAR':
            shape.ensure_drivers_initialized(self.src_armature)
            self.sl_bone_ends = False
            self.pose_library = self.src_armature.pose_library
            self.use_male_shape = self.src_armature.ShapeDrivers.male_80
        else:
            self.pose_library     = None

        self.transferJoints = updateRigProp.transferJoints

        self.selected = [ob for ob in bpy.context.selected_objects]
        self.targets  = [arm for arm in self.selected if arm.type=='ARMATURE' and 'avastar' in arm and arm != self.src_armature]
        self.inplace_transfer = (len(self.targets) == 0)

        self.find_transfer_sources(context)

        return True


    def invoke(self, context, event):
        armature = context.object
        scene = context.scene
        mesh_repair = scene.UpdateRigProp.mesh_repair
        system_meshes, animated_meshes = util.get_animated_elements(context, armature, only_visible=False)
        if mesh_repair:

            animated_meshes = [m for m in animated_meshes if not m in system_meshes]
            system_meshes=[]
            for child in armature.children:
                if child.type == 'EMPTY':
                    util.remove_object(context, child, do_unlink=True, recursive=True)

        select_hide_states = util.get_select_and_hide(animated_meshes, select=None, hide_select=None, hide=False, hide_viewport=False)
        rig_sections = [B_EXTENDED_LAYER_ALL]
        excludes = []

        mesh.unbind_from_armature(self, context, animated_meshes, keep_avastar_properties=True)
        status = self.execute(context)

        if scene.UpdateRigProp.applyRotation:
            for ob in animated_meshes:
                util.apply_transform(ob, with_loc=False, with_rot=True, with_scale=True)

        armature = context.object

        if self.srcRigType == 'SL':
            armature.matrix_local = armature.matrix_local @ Rz90I

        mesh.bind_to_armature(self,
                     context,
                     armature,
                     rig_sections,
                     excludes,
                     keep_empty_groups=False,
                     enforce_meshes=None,
                     bindSourceSelection=['NONE'],
                     attach_set=animated_meshes)
        self.report({'INFO'},"Parented %d meshes to Armature"% len(animated_meshes))
        if self.srcRigType == 'SL':
            armature.matrix_local = armature.matrix_local @ Rz90

        if len(system_meshes) > 0:
            container = create.add_container(context, armature, armature.name+"_meshes", hide=True)
            for ob in system_meshes:
                ob.parent = container
                ob.matrix_parent_inverse = container.matrix_world.inverted()

        util.set_select_and_hide(context, select_hide_states)

        return status


    def initialize(self, context):

        scene                          = context.scene
        updateRigProp                  = scene.UpdateRigProp
        sceneProp                      = scene.SceneProp

        self.src_armature              = util.get_armature(context.object)

        if self.src_armature and 'avastar' in self.src_armature:
            self.srcRigType            = 'AVASTAR'
            self.use_male_shape        = self.src_armature.RigProp.gender == 'MALE'
            self.use_male_skeleton     = self.src_armature.RigProp.gender == 'MALE'

        else:
            self.srcRigType            = updateRigProp.srcRigType
            self.use_male_shape        = updateRigProp.use_male_shape
            self.use_male_skeleton     = updateRigProp.use_male_skeleton
        
        self.transferMeshes            = updateRigProp.transferMeshes
        self.appearance_enabled        = sceneProp.panel_appearance_enabled
        self.applyRotation             = updateRigProp.applyRotation
        self.handleTargetMeshSelection = updateRigProp.handleTargetMeshSelection
        self.adjust_origin             = updateRigProp.adjust_origin
        self.align_to_deform           = updateRigProp.align_to_deform
        self.adjust_pelvis             = updateRigProp.adjust_pelvis
        self.align_to_rig              = updateRigProp.align_to_rig
        self.adjust_rig                = updateRigProp.adjust_rig
        self.fix_reference_meshes      = updateRigProp.fix_reference_meshes
        self.preserve_bone_colors      = updateRigProp.preserve_bone_colors

        if util.get_ui_level() > UI_ADVANCED:
            self.snap_collision_volumes = updateRigProp.snap_collision_volumes
            self.snap_attachment_points = updateRigProp.snap_attachment_points
        else:
            self.snap_collision_volumes = False
            self.snap_attachment_points = False

        is_an_update = armature_needs_update(self.src_armature)
        self.bone_repair               = updateRigProp.bone_repair
        self.structure_repair          = updateRigProp.structure_repair

        if self.mesh_repair == None:
            self.mesh_repair           = updateRigProp.mesh_repair and not is_an_update
        self.show_offsets              = updateRigProp.show_offsets
        self.sl_bone_ends              = updateRigProp.sl_bone_ends
        self.sl_bone_rolls             = updateRigProp.sl_bone_rolls
        self.tgtRigType                = updateRigProp.tgtRigType
        self.up_axis                   = updateRigProp.up_axis
        self.is_initialized = True

    def execute(self, context):

        if not self.is_initialized:
            self.initialize(context)

        def is_extended_rig():
            has_fingers = all( bn in self.src_armature.pose.bones \
                        for bn in ['pinky00_R', 'spine03', 'upperarm_L', 'clavicle_L'] \
                       )
            return has_fingers

        def replace_armature(context, src_armature, tgt_armature):
            util.ensure_mode_is('OBJECT', object=src_armature)
            context.view_layer.objects.active = tgt_armature
            tgt_armature.select_set(True)

            log.debug("| Unlink Source armature %s" % src_armature.name)
            src_data = src_armature.data
            src_data_name = src_data.name
            src_data.name = '%s_del' % src_data_name
            tgt_armature.data.name = src_data_name

        def get_active_bone_name(src_armature):
            bone = src_armature.data.bones.active
            return bone.name if bone else None



        if not self.init(context):
            return {'CANCELLED'}

        scene=context.scene

        active_mode = util.ensure_mode_is('OBJECT')
        src_armature_mode  = self.src_armature.mode
        selected_bones = [b.name for b in self.src_armature.data.bones if b.select]
        active_bone_name = get_active_bone_name(self.src_armature)
        shape_data = shape.asDictionary(self.src_armature, full=True)
        oumode = util.set_operate_in_user_mode(False)
        tgt_rigtype = self.tgtRigType
        if is_extended_rig():

            tgt_rigtype = 'EXTENDED'

        tgt_armatures = None
        tgt_armature = None
        use_male_shape = self.use_male_shape

        util.set_active_collection_of(context, self.src_armature)

        log.warning("Copy Rig:| Convert %s Armature '%s' to %s Avastar Rig" % (self.srcRigType, self.src_armature.name, tgt_rigtype))
        if self.srcRigType != 'AVASTAR':

            tgt_armature = convert_sl(
                self,
                context,
                tgt_rigtype,
                self.JointType,
                self.active,
                self.src_armature,
                self.inplace_transfer,
                self.bone_repair,
                self.mesh_repair,
                self.transferJoints,
                shapefile=self.devkit_shapepath
                )
            log.warning("Copy Rig:| Created an Avastar - %s Armature" % tgt_armature.RigProp.JointType)

        else:
            propgroups.gender_update(self.src_armature, self.use_male_shape)

            if self.inplace_transfer:
                self.transferMeshes = True
                if self.src_armature.ShapeDrivers.male_80:
                    self.use_male_shape = False
                    propgroups.gender_update(self.src_armature, self.use_male_shape) 
                    shape.refreshAvastarShape(context)
                    log.info("| Setting rig %s male=False" % (self.src_armature.name))

                tgt_armature = update_avastar(
                    self,
                    context,
                    tgt_rigtype,
                    self.active, 
                    self.src_armature, 
                    self.structure_repair,
                    self.mesh_repair,
                    self.transferJoints
                    )




                if self.fix_reference_meshes:

                    log.info("| Fixing reference meshes...")
                    bpy.ops.avastar.reparent_armature()
            else:
            
                if self.fix_reference_meshes:

                    log.info("| Fixing reference meshes...")
                    bpy.ops.avastar.reparent_armature()
                    self.find_transfer_sources(context)

                tgt_armatures = copy_avastar(
                    self,
                    context,
                    tgt_rigtype,
                    self.active, 
                    self.src_armature, 
                    self.bone_repair,
                    self.mesh_repair
                    )

        if tgt_armature:

            replace_armature(context, self.src_armature, tgt_armature)



            if self.pose_library:
                tgt_armature.pose_library = self.pose_library

            if self.appearance_enabled:
                tgt_armature.ObjectProp.slider_selector = 'SL'
            else:
                tgt_armature.ObjectProp.slider_selector = 'NONE'

            if self.inplace_transfer:
                if use_male_shape:
                    self.use_male_shape = True
                    propgroups.gender_update(tgt_armature, self.use_male_shape)
                    shape.refreshAvastarShape(context)
                    log.info("| Setting rig %s to male=True" % (tgt_armature.name))
            else:
                util.ensure_mode_is(src_armature_mode, object=tgt_armature)
                tgt_armature.ObjectProp.filter_deform_bones = False
                util.object_select_set(util.get_active_object(context), True)

            omode = util.ensure_mode_is('OBJECT')
            util.ensure_mode_is('EDIT')
            util.select_set_edit_bones(tgt_armature, select=True)
            bpy.ops.transform.translate(value=(0, 0, 0)) # Dont ask hrmpfff
            util.select_set_edit_bones(tgt_armature, select=False)

            tgt_armature.RigProp.up_axis = self.up_axis
            for bname in selected_bones:
                bone = tgt_armature.data.edit_bones.get(bname)
                if bone:
                    bone.select=True
                    if bname == active_bone_name:
                        tgt_armature.data.edit_bones.active=bone





            for i in range(0,32):
                tgt_armature.data.layers[i] = self.src_armature.data.layers[i]

            util.ensure_mode_is('OBJECT')
            util.ensure_mode_is(omode)


        util.set_operate_in_user_mode(oumode)
        util.ensure_mode_is(active_mode)

        src_data = self.src_armature.data
        util.remove_object(context, self.src_armature, recursive=True)
        bpy.data.armatures.remove(src_data)

        return {'FINISHED'}

    @classmethod
    def poll(self, context):
        try:
            return context.active_object and context.active_object.type == 'ARMATURE'
        except (TypeError, AttributeError):
            pass
        return False

def extract_bone_info(bname, ebones, pbones):
    bone_info = [None]*BONE_DATA_COUNT
    pbone = pbones[bname]
    dbone = ebones[bname]

    constraints = [[c.type,c.influence,c.mute] for c in pbone.constraints]
    iklimits = [ pbone.use_ik_limit_x, pbone.use_ik_limit_y, pbone.use_ik_limit_z ]
    use_deform = dbone.use_deform

    bone_info[BONE_DATA_HIDE] = dbone.hide
    if bone_info[BONE_DATA_HIDE]:
        dbone.hide=False

    if 'Eye' in bname and pbone.bone_group and pbone.bone_group.name=='Extra':
        bone_group_name='Eyes'
        bone_colorset='THEME02'
    elif pbone.bone_group:
        bone_group_name = pbone.bone_group.name
        bone_colorset   = pbone.bone_group.color_set
    else:
        bone_group_name = None
        bone_colorset = None

    bone_info[BONE_DATA_NAME] = bname
    bone_info[BONE_DATA_SELECT] = pbone.bone.select
    bone_info[BONE_DATA_DEFORM] = use_deform
    bone_info[BONE_DATA_PARENT] = pbone.parent.name if pbone.parent else None
    bone_info[BONE_POSE_GROUP] = bone_group_name
    bone_info[BONE_POSE_COLORSET] = bone_colorset
    bone_info[BONE_DATA_CONNECT] = pbone.bone.use_connect
    bone_info[BONE_DATA_CONSTRAINT] = constraints
    bone_info[BONE_DATA_IKLIMITS] = iklimits
    bone_info[BONE_POSE_ROTATION_MODE] = pbone.rotation_mode
    return bone_info


def initialise_bone_setup(context, armature):
    log.debug("Transfer(sl): Extract Source bone setup")
    bone_store = {}
    bone_names = Skeleton.bones_in_hierarchical_order(armature)

    for bname in bone_names:
        bone_store[bname] = extract_bone_info(bname, armature.data.bones, armature.pose.bones)

    return bone_store

def extract_bone_data(context, armature, bone_store, rot):


    def extract_data(armature, name, bone_info, rot):
        pbone = armature.pose.bones[name]
        dbone = pbone.bone

        bone_info[BONE_DATA_HEAD] = rot @ dbone.head_local
        bone_info[BONE_DATA_TAIL] = rot @ dbone.tail_local
        bone_info[BONE_DATA_ROLL] = 0 #ebone.roll (taken from the matrix, see next line)
        bone_info[BONE_DATA_MATRIX] = pbone.matrix.copy()

    log.debug("Transfer(sl): Extract Source bone data")

    oactive = util.get_active_object(context)
    if oactive != armature:
        omode = util.ensure_mode_is("OBJECT")
        util.set_active_object(context, armature)
        amode = util.ensure_mode_is("OBJECT")
    else:
        oactive = None

    util.ensure_mode_is("POSE")
    if not bone_store:
        bone_store = initialise_bone_setup(context, armature)

    bone_names = Skeleton.bones_in_hierarchical_order(armature)

    for name in bone_names:
        extract_data(armature, name, bone_store.get(name), rot)

    if oactive:
        util.ensure_mode_is(amode)
        util.set_active_object(context, oactive)
        util.ensure_mode_is(omode)

    return bone_store
        




def create_transfer_preset(layout):
    last_select = bpy.types.AVASTAR_MT_transfer_presets_menu.bl_label
    row = layout.row(align=True)
    row.menu("AVASTAR_MT_transfer_presets_menu", text=last_select )
    row.operator("avastar.transfer_presets_add", text="", icon=ICON_ADD)
    if last_select not in ["Transfer Presets", "Presets"]:
        row.operator("avastar.transfer_presets_update", text="", icon=ICON_FILE_REFRESH)
        row.operator("avastar.transfer_presets_remove", text="", icon=ICON_REMOVE).remove_active = True

def add_transfer_preset(context, filepath):
    armobj = context.object
    log.warning("Create transfer preset for object %s" % (armobj.name) )
    scene = context.scene
    sceneProps = scene.SceneProp
    updateRigProp = scene.UpdateRigProp

    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "import avastar\n"
    "from avastar import shape, util\n"
    "\n"
    "context = bpy.context\n"
    "scene = context.scene\n"
    "armobj = context.object\n"
    "updateRigProp = scene.UpdateRigProp\n"
    "sceneProps  = scene.SceneProp\n\n"
    )

    file_preset.write("armobj.data.pose_position = '%s'\n" % armobj.data.pose_position)
    file_preset.write("updateRigProp.srcRigType = '%s'\n" % updateRigProp.srcRigType)
    file_preset.write("updateRigProp.tgtRigType = '%s'\n" % updateRigProp.tgtRigType)
    file_preset.write("updateRigProp.handleTargetMeshSelection = '%s'\n" % updateRigProp.handleTargetMeshSelection)
    file_preset.write("updateRigProp.transferJoints = %s\n" % updateRigProp.transferJoints)
    file_preset.write("armobj.RigProp.JointType = '%s'\n" % armobj.RigProp.JointType)
    file_preset.write("armobj.RigProp.rig_use_bind_pose = %s\n" % armobj.RigProp.rig_use_bind_pose)
    file_preset.write("updateRigProp.sl_bone_ends = %s\n" % updateRigProp.sl_bone_ends)
    file_preset.write("updateRigProp.sl_bone_rolls = %s\n" % updateRigProp.sl_bone_rolls)
    file_preset.write("updateRigProp.show_offsets = %s\n" % updateRigProp.show_offsets)
    file_preset.write("sceneProp.panel_appearance_enabled = %s\n" % sceneProp.panel_appearance_enabled)
    file_preset.write("updateRigProp.applyRotation = %s\n" % updateRigProp.applyRotation)
    file_preset.write("updateRigProp.use_male_shape = %s\n" % updateRigProp.use_male_shape)
    file_preset.write("updateRigProp.use_male_skeleton = %s\n" % updateRigProp.use_male_skeleton)
    file_preset.write("updateRigProp.apply_pose = %s\n" % updateRigProp.apply_pose)

    file_preset.close()

class AVASTAR_MT_transfer_presets_menu(Menu):
    bl_label  = "Transfer Presets"
    bl_description = "Transfer Presets for Avastar\nHere you define configurations for updating/importing Rigs."
    preset_subdir = os.path.join("avastar","transfers")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class AvastarAddPresetTransfer(AddPresetBase, Operator):
    bl_idname = "avastar.transfer_presets_add"
    bl_label = "Add Transfer Preset"
    bl_description = "Create new Preset from current Panel settings"
    preset_menu = "AVASTAR_MT_transfer_presets_menu"

    preset_subdir = os.path.join("avastar","transfers")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_transfer_preset(context, filepath)

class AvastarUpdatePresetTransfer(AddPresetBase, Operator):
    bl_idname = "avastar.transfer_presets_update"
    bl_label = "Update Transfer Preset"
    bl_description = "Update active Preset from current Panel settings"
    preset_menu = "AVASTAR_MT_transfer_presets_menu"
    preset_subdir = os.path.join("avastar","transfers")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_transfer_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_transfer_preset(context, filepath)

class AvastarRemovePresetTransfer(AddPresetBase, Operator):
    bl_idname = "avastar.transfer_presets_remove"
    bl_label = "Remove Transfer Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_transfer_presets_menu"
    preset_subdir = os.path.join("avastar","transfers")

#######################################################################
#
#######################################################################

def create_devkit_preset(layout):
    last_select = bpy.types.AVASTAR_MT_devkit_presets_menu.bl_label
    row = layout.row(align=True)
    prop = row.menu("AVASTAR_MT_devkit_presets_menu", text=last_select)
    

    if last_select not in ["Devkit Presets", "Presets"]:
        row.operator("avastar.devkit_presets_update", text="", icon=ICON_FILE_REFRESH)
        row.operator("avastar.devkit_presets_remove", text="", icon=ICON_REMOVE).remove_active = True

def create_devkit_exec(layout):
    last_select = bpy.types.AVASTAR_MT_devkit_preset_exec_menu.bl_label
    paths =  bpy.utils.preset_paths(bpy.types.AVASTAR_MT_devkit_presets_menu.preset_subdir)
    col = layout.column(align=True)

    has_presets = False
    for dir in paths:
        presets = os.listdir(dir)

        for preset in presets:
            if not has_presets:
                has_presets = True
                col.label(text="Add Developer kit:")
                col.separator()

            path = os.path.join(dir, preset)
            name = bpy.path.display_name(preset)
            if os.path.isfile(path) and path.endswith('.py') or path.endswith('.blend'):
                if os.access(path, os.R_OK):
                    icon  = ICON_BLANK1
                    alert = False
                else:
                    icon  = ICON_ERROR 
                    alert = True

                col.alert = alert
                prop = col.operator("avastar.execute_devkit_preset", text="%s" % (name), icon=icon)
                prop.filepath = path


    if has_presets:
        col.separator()
        col.alert = False
        col.operator("avastar.pref_show", text="Add/Edit Configuration", icon=ICON_MODIFIER)

    
    else:
        col.label(text="No Devkit Config found")
        col.label(text="Hint: You add Devkits")
        col.label(text="in the Addon Preferences")
        col.label(text="(Scroll to \"Devkit Configurations\")")




def add_devkit_preset(context, filepath, allow_overwrite):
    kitprop = context.scene.UpdateRigProp
    if not allow_overwrite and os.path.exists(filepath):
        name = "%s - %s" % (kitprop.devkit_brand, kitprop.devkit_snail)
        return "Preset for '%s' already exists and overwrite is not allowed" % name

    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "kitprop = bpy.context.scene.UpdateRigProp\n\n"
    )

    file_preset.write("kitprop.devkit_filepath=r'''%s'''\n"   % (kitprop.devkit_filepath))
    file_preset.write("kitprop.devkit_shapepath=r'''%s'''\n"   % (kitprop.devkit_shapepath))
    file_preset.write("kitprop.devkit_brand=r'%s'\n"      % (kitprop.devkit_brand))
    file_preset.write("kitprop.devkit_snail=r'%s'\n"      % (kitprop.devkit_snail))
    file_preset.write("kitprop.devkit_scale=%f\n"         % (kitprop.devkit_scale))
    file_preset.write("kitprop.srcRigType='%s'\n"         % (kitprop.srcRigType))
    file_preset.write("kitprop.tgtRigType='%s'\n"         % (kitprop.tgtRigType))
    file_preset.write("kitprop.JointType='%s'\n"          % (kitprop.JointType))
    file_preset.write("kitprop.tgtJointType='%s'\n"       % (kitprop.tgtJointType))
    file_preset.write("kitprop.devkit_use_sl_head=%s\n"   % (kitprop.devkit_use_sl_head))
    file_preset.write("kitprop.use_male_shape=%s\n"        % (kitprop.use_male_shape))
    file_preset.write("kitprop.use_male_skeleton=%s\n"     % (kitprop.use_male_skeleton))
    file_preset.write("kitprop.transferJoints=%s\n"       % (kitprop.transferJoints))
    file_preset.write("kitprop.devkit_use_bind_pose=%s\n" % (kitprop.devkit_use_bind_pose))
    file_preset.write("kitprop.sl_bone_ends=%s\n"         % (kitprop.sl_bone_ends))
    file_preset.write("kitprop.sl_bone_rolls=%s\n"        % (kitprop.sl_bone_rolls))
    file_preset.write("kitprop.fix_reference_meshes=%s\n" % (kitprop.fix_reference_meshes))
    file_preset.write("kitprop.up_axis='%s'\n"            % (kitprop.up_axis))
    file_preset.close()

    return None

class AVASTAR_MT_devkit_presets_menu(Menu):
    bl_idname = "AVASTAR_MT_devkit_presets_menu"
    bl_label  = "Devkit Presets"
    bl_description = "Devkit Presets for Avastar\nHere you define configurations for updating/importing Rigs."
    preset_subdir = os.path.join("avastar","devkits")
    preset_operator = "avastar.load_devkit_preset"
    draw = Menu.draw_preset
    
class AVASTAR_MT_devkit_preset_exec_menu(Menu):
    bl_label  = "Devkit Presets"
    bl_description = "Devkit Presets for Avastar\nHere you define configurations for updating/importing Rigs."
    preset_subdir = os.path.join("avastar","devkits")
    preset_operator = "avastar.execute_devkit_preset"
    draw = Menu.draw_preset
    
class ExecuteDevkitPreset(Operator):
    """Add a character from a development kit"""
    bl_idname = "avastar.execute_devkit_preset"
    bl_label = "Add Devkit"
    bl_options = {'REGISTER','UNDO'}

    filepath : StringProperty(
            subtype='FILE_PATH',
            options={'SKIP_SAVE'},
            )
    menu_idname : StringProperty(
            name="Menu ID Name",
            description="ID name of the menu this was called from",
            options={'SKIP_SAVE'},
            )

    def execute(self, context):
        prop = context.scene.UpdateRigProp

        log.warning("Execute devkit preset %s" % self.filepath)
        prop.devkit_scale=1.0 #reset the scale for old preset definitions
        prop.up_axis = 'Z'


        try :
            status = bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname=AVASTAR_MT_devkit_presets_menu.bl_idname)
            if not 'FINISHED' in status:
                return status

            if import_rig_from_file(context, prop):
                return {'FINISHED'}     

            self.report({'ERROR'}, "Import of Developerkit failed.\nPlease open the developerkit configuration\nand check if the Developerkit file exists")
            return {'CANCELLED'}
        except:
            self.report({'ERROR'}, "Import of Developerkit failed with severe error.")
            raise




class LoadDevkitPreset(Operator):
    """Add a character from a development kit"""
    bl_idname = "avastar.load_devkit_preset"
    bl_label = "Add Devkit"

    filepath : StringProperty(
            subtype='FILE_PATH',
            options={'SKIP_SAVE'},
            )
    menu_idname : StringProperty(
            name="Menu ID Name",
            description="ID name of the menu this was called from",
            options={'SKIP_SAVE'},
            )

    def execute(self, context):
        log.warning("Load devkit preset %s" % self.filepath)
        context.scene.UpdateRigProp.shapepath = ''
        context.scene.UpdateRigProp.devkit_scale=1.0 #reset the scale for old preset definitions
        context.scene.UpdateRigProp.up_axis = 'Z'

        status = bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname=AVASTAR_MT_devkit_presets_menu.bl_idname)

        return status


class AvastarAddPresetDevkit(AddPresetBase, Operator):
    bl_idname = "avastar.devkit_presets_add"
    bl_label = "Add Devkit Preset"
    bl_description = "Create new Preset from current Panel settings"
    preset_menu = "AVASTAR_MT_devkit_presets_menu"

    preset_subdir = os.path.join("avastar","devkits")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        kitprop = context.scene.UpdateRigProp
        allow_overwrite = kitprop.devkit_replace_export
        msg = add_devkit_preset(context, filepath, True)
        if msg:
            self.report({'ERROR'}, msg)


class AvastarUpdatePresetDevkit(AddPresetBase, Operator):
    bl_idname = "avastar.devkit_presets_update"
    bl_label = "Update Devkit Preset"
    bl_description = "Update active Preset from current Panel settings"
    preset_menu = "AVASTAR_MT_devkit_presets_menu"
    preset_subdir = os.path.join("avastar","devkits")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_devkit_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        kitprop = context.scene.UpdateRigProp
        allow_overwrite = kitprop.devkit_replace_export
        msg = add_devkit_preset(context, filepath, allow_overwrite)
        if msg:
            self.report({'ERROR'}, msg)

class AvastarRemovePresetDevkit(AddPresetBase, Operator):
    bl_idname = "avastar.devkit_presets_remove"
    bl_label = "Remove Devkit Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_devkit_presets_menu"
    preset_subdir = os.path.join("avastar","devkits")

#######################################################################

#######################################################################


def transfer_constraints(context, tgt_armature, src_armature):
    pbones = tgt_armature.pose.bones
    ebones = tgt_armature.data.edit_bones
    sbones = src_armature.pose.bones

    def get_constraints(bone, type):
        cons = [ con for con in bone.constraints if con.type == type]
        return cons

    def copycons(tbone, sbone, type, tcbone=None, tcpbone=None):

        scons = get_constraints(sbone, type)
        tcons = get_constraints(tbone, type)

        for scon, tcon in zip(scons, tcons):
            tcon.mute = scon.mute

            tcon.target_space = scon.target_space
            tcon.owner_space = scon.owner_space

            if tcbone:


                targetless_iks = [c for c in tcpbone.constraints if c.type=='IK' and c.target==None]
                for ikc in targetless_iks:
                    ikc.influence = 0.0 if tcon.mute else 1.0

    def copylock(tbone, sbone):
        for n in range(0,3):
            tbone.lock_location[n] = sbone.lock_location[n]

    def get_control_bone(tbone, ebones, pbones):
        cname = tbone.name[1:]
        return ebones.get(cname), pbones.get(cname)

    for tbone in pbones:
        sbone = sbones.get(tbone.name)
        if not sbone:

            continue

        copycons(tbone, sbone, 'COPY_ROTATION')
        tcbone, tcpbone = get_control_bone(tbone, ebones, pbones) 

        copycons(tbone, sbone, 'COPY_LOCATION', tcbone, tcpbone)
        if tbone.name == 'Torso':
            tbone.lock_location[0] = False
            tbone.lock_location[1] = False
            tbone.lock_location[2] = False
        else:
             copylock(tbone, sbone)

        if not src_armature.data.bones[tbone.name].use_connect:
            rig.set_connect(ebones[tbone.name], False) # uhuuu

def roll_neutral_rotate(armobj, rot):
        log.debug("roll_neutral_rotate: Rotate Armature: [%s] (preserving boneroll)" % armobj.name)





        util.ensure_mode_is("OBJECT")
        armobj.matrix_world = mulmat(armobj.matrix_world, rot)
        bpy.ops.object.select_all(action='DESELECT')
        util.object_select_set(armobj, True)
        bpy.ops.object.transform_apply(rotation=True)







        util.ensure_mode_is("OBJECT")



#



#



def move_rigged(context, from_rig, to_rig):
    pass

classes = (
    ImportColladaDevkit,
    ButtonCopyAvastar,
    AVASTAR_MT_transfer_presets_menu,
    AvastarAddPresetTransfer,
    AvastarUpdatePresetTransfer,
    AvastarRemovePresetTransfer,
    AVASTAR_MT_devkit_presets_menu,
    AVASTAR_MT_devkit_preset_exec_menu,
    ExecuteDevkitPreset,
    LoadDevkitPreset,
    AvastarAddPresetDevkit,
    AvastarUpdatePresetDevkit,
    AvastarRemovePresetDevkit,
    RigTransferConfigurator,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered copyrig:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered copyrig:%s" % cls)
