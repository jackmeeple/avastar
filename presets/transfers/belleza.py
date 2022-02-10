import bpy
import avastar
from avastar import shape, util

context = bpy.context
scene = context.scene
armobj = context.object
updateRigProp = scene.UpdateRigProp
sceneProps  = scene.SceneProp

armobj.data.pose_position = 'POSE'
updateRigProp.srcRigType = 'SL'
updateRigProp.tgtRigType = 'BASIC'
updateRigProp.handleTargetMeshSelection = 'DELETE'
updateRigProp.transferJoints = True
updateRigProp.JointType = 'POS'
updateRigProp.rig_use_bind_pose = True
updateRigProp.sl_bone_ends = True
updateRigProp.sl_bone_rolls = True
updateRigProp.show_offsets = False
updateRigProp.attachSliders = True
updateRigProp.applyRotation = True
updateRigProp.use_male_shape = False
updateRigProp.use_male_skeleton = False
updateRigProp.apply_pose = False
