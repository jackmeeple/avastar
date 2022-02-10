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

    util.set_active_object(context, obj)
    obj.FittingValues.R_FOOT=0.5
    obj.FittingValues.R_LOWER_LEG=0.5
    obj.FittingValues.R_LOWER_ARM=0.5
    obj.FittingValues.PELVIS=0.5
    obj.FittingValues.R_CLAVICLE=0.5
    obj.FittingValues.L_UPPER_LEG=0.5
    obj.FittingValues.L_LOWER_ARM=0.5
    obj.FittingValues.L_UPPER_ARM=0.5
    obj.FittingValues.NECK=0.5
    obj.FittingValues.L_FOOT=0.5
    obj.FittingValues.L_LOWER_LEG=0.5
    obj.FittingValues.L_HAND=0.5
    obj.FittingValues.HEAD=0.5
    obj.FittingValues.R_UPPER_ARM=0.5
    obj.FittingValues.BELLY=0.5
    obj.FittingValues.R_HAND=0.5
    obj.FittingValues.R_UPPER_LEG=0.5
    obj.FittingValues.L_CLAVICLE=0.5
    obj.FittingValues.CHEST=0.5
    obj.FittingValues.butt_strength=-1.0
    obj.FittingValues.pec_strength=0.75
    obj.FittingValues.back_strength=-1.0
    obj.FittingValues.handle_strength=-1.0

    bone_names = [b.name for b in arm.data.bones if b.use_deform]
    weights.removeBoneWeightGroupsFromSelectedBones(context, obj, only_remove_empty=True, bone_names=bone_names) #remove empty groups
    util.add_missing_mirror_groups(context)

    arm.ObjectProp.slider_selector=selector if selector != 'NONE' else 'SL'

    weights.setUpdateFitting(True)
    shape.refresh_shape(context, arm, obj, graceful=True)

util.set_active_object(context, active)
util.ensure_mode_is(amode)