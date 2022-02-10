import bpy
import avastar
from avastar import shape, util

arm    = util.get_armature(bpy.context.object)

dict={'butt_size_795': 36.0, 'head_size_682': 60.0, 'neck_thickness_683': 60.0, 'saddlebags_753': 29.0, 'squash_stretch_head_647': 51.0, 'leg_length_692': 67.0, 'leg_muscles_652': 40.0, 'shoulders_36': 49.0, 'torso_muscles_649': 43.0, 'neck_length_756': 70.0, 'torso_length_38': 90.0, 'breast_gravity_507': 69.0, 'hip_width_37': 49.0, 'love_handles_676': 31.0, 'arm_length_693': 100.0, 'hip_length_842': 11.0, 'thickness_34': 57.0, 'height_33': 55.0}
shape.resetToDefault(arm)
shape.fromDictionary(arm,dict)
