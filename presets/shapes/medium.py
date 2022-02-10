import bpy
import avastar
from avastar import shape, util

arm    = util.get_armature(bpy.context.object)

dict={'belly_size_157': 50.0, 'body_fat_637': 50.0}
shape.resetToDefault(arm)
shape.fromDictionary(arm,dict)
