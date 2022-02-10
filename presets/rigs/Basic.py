import bpy
import avastar
from avastar import shape, util

sceneProps  = bpy.context.scene.SceneProp
sceneProps.avastarMeshType   = 'QUADS'
sceneProps.avastarRigType    = 'BASIC'
sceneProps.avastarJointType  = 'PIVOT'
