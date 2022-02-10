import bpy
import avastar
from avastar import shape, util

arm    = util.get_armature(bpy.context.object)

dict={'torso_length_38': 79.0, 'leg_length_692': 57.0, 'arm_length_693': 93.0, 'eye_spacing_196': 72.0, 'neck_length_756': 13.0, 'height_33': 54.0}
shape.resetToDefault(arm)
shape.fromDictionary(arm,dict)
