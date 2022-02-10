### Copyright 2014 Gaia Clary
###
### This file is part of Avat=star-2.
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

import os, pickle
import bpy
import bmesh
from bpy.props import *
from . import util
from .const import *
from mathutils import Vector

import gettext
registerlog = logging.getLogger("avastar.register")





obsolete_edges = None
def sl_initialize_obsolete_edges():
    edges_file = os.path.join(DATAFILESDIR,'edges.pickle')
    with open(edges_file, 'rb') as f:
        obsolete_edges = pickle.load(f)
            
    return obsolete_edges

class SLQuadifyAvatarMesh(bpy.types.Operator):
    bl_idname = "avastar.quadify_avatar_mesh"
    bl_label = "Quadify Avatar"
    bl_description = "Convert triangulated SL Avatar to quads"

    mesh_id     : StringProperty()    
    object_name : StringProperty()
    
    def execute(self, context):
        active = util.get_active_object(context)
        obj = context.scene.objects[self.object_name]
        util.set_active_object(bpy.context, obj        )
        self.sl_quadify_avatar_mesh(context, obj, self.mesh_id)
        util.set_active_object(bpy.context, active)
        return{'FINISHED'}    

    def get_hash(self, edge, active_layer):
        loop = edge.link_loops[0]
        uv=[]
        while len(uv) != 2:
            if loop.vert in edge.verts:
                uv.append(loop[active_layer].uv.copy())
            loop = loop.link_loop_next
        
        for i in range(2):
            for j in range(2):
                uv[i][j] = int(round(1000*uv[i][j]))
    
        if uv[0][0] > uv[1][0]:
            uv[0],uv[1] = uv[1],uv[0]
        elif uv[0][0] == uv[1][0]:
            if uv[0][1] > uv[1][1]:
                uv[0],uv[1] = uv[1],uv[0]
    
        hash = "%03d-%03d-%03d-%03d" % (uv[0][0], uv[0][1], uv[1][0], uv[1][1])    
        return hash
    
    def is_edge(self, edge, hash, active_layer):

        lhash = self.get_hash(edge, active_layer)
        state = (hash == lhash)
    

        return state
        
    def find_obsolete_edge(self, edges, index, hash, active_layer):
        edge  = edges[index]
    
        if self.is_edge(edge, hash, active_layer):
            return edge.index
    
        for edge in edges:
            if self.is_edge(edge, hash, active_layer):
                rindex = edge.index
                print("Remapped obsolete edge",index,"to",rindex)
                return rindex

        print("Remap obsolete edge",index,"failed")      
        return None
    
    def sl_quadify_avatar_mesh(self, context, obj, mesh_id):
        global obsolete_edges
        if obsolete_edges == None:
            obsolete_edges = sl_initialize_obsolete_edges()
        
        if mesh_id in obsolete_edges:
            mesh_select_mode = util.set_mesh_select_mode((False,True,False))

            
            util.set_object_mode('OBJECT', object=obj)



            bm = bmesh.new()
            bm.clear()
            bm.from_object(obj, context.view_layer.depsgraph)
            try:
                bm.edges.ensure_lookup_table()
            except:
                pass
                
            layer_index  = obj.data.uv_layers.active_index
            active_layer = bm.loops.layers.uv[layer_index]                
            
            for edge in bm.edges:
                hash = self.get_hash(edge, active_layer)
                if hash in obsolete_edges[mesh_id]:
                    edge.select=True
                
            bm.to_mesh(obj.data)
            bm.clear()
            bm.free()

            util.set_object_mode('EDIT', object=obj)
            bpy.ops.mesh.dissolve_edges(use_verts=False)
            util.set_object_mode('OBJECT', object=obj)
            

            util.set_mesh_select_mode(mesh_select_mode)

classes = (
    SLQuadifyAvatarMesh,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered quadify:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered quadify:%s" % cls)

