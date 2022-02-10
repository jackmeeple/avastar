import bpy
import avastar
from avastar import shape, util

sceneProps  = bpy.context.scene.SceneProp
sceneProps.avastarMeshType   = 'NONE'
sceneProps.avastarRigType    = 'EXTENDED'
sceneProps.avastarJointType  = 'PIVOT'
