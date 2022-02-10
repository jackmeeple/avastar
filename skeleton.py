### Copyright 2018, Machinimatrix
### Modifications 2018 None
###
### This file is part of Avastar 2.
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

import logging
import bpy
from mathutils import Vector, Matrix
from . import bl_info, const, util, data
from .const import *
from .util import *

log = logging.getLogger("avastar.skeleton")
registerlog = logging.getLogger("avastar.register")

class Skeleton:

    @staticmethod
    def store_bind_data(arm):
        arm['binddata'] = Skeleton.get_bind_data(arm)

    @staticmethod
    def get_bind_data(arm):

        bones = Skeleton.get_bone_hierarchy(arm)
        binding = {}
        for b in bones:
           binding[b.name] = b.matrix_local.copy()
        
        if not hasattr(arm.ShapeDrivers, 'DRIVERS'):
            Skeleton.load_drivers(arm)

        bind_data = {
            SHAPE_BINDING:binding,
            'sliders':arm.ShapeDrivers.get_attributes(),
            'values':arm.ShapeValues.get_attributes()
        }
        return bind_data

    @staticmethod
    def load_drivers(arm):
        rigType = arm.RigProp.RigType
        DRIVERS = data.loadDrivers()
        Skeleton.createShapeDrivers(DRIVERS)

    @staticmethod
    def get_bone_hierarchy(arm):
        bones = []
        root_bones = [b for b in arm.data.bones if not b.parent]
        for dbone in root_bones:
            Skeleton.parse_bone_hierarchy([dbone], bones)

        return bones

    @staticmethod
    def parse_bone_hierarchy(dbones, bones):
        for dbone in dbones:
            bones.append(dbone)
            if dbone.children:
                Skeleton.parse_bone_hierarchy(dbone.children, bones)

        return bones

    @staticmethod
    def createShapeDrivers(DRIVERS):
        
        log.info("Create Shape UI...")

        sectionitems = []
        for section in SHAPEUI.keys():
            sectionitems.append((section, section, section))
        for section in SHAPE_FILTER.keys():
            sectionitems.append((section, section, section))
            
        sectionitems.reverse()
        ShapeDrivers.Sections = EnumProperty( items=sectionitems, name='Sections', default='Body' )    
        

        ShapeDrivers.DRIVERS = DRIVERS
        
        
        target = ShapeDrivers
        values = ShapeValues
        
        for pids in SHAPEUI.values():
            for pid in pids:
                P = DRIVERS.get(pid,None)
                if not P:
                    continue
                D = P[0]

                if pid=="male_80":

                    setattr(target, pid,  
                            BoolProperty(name = D['label'], 

                                        update=eval("lambda a,b:updateShape(a,b,'%s')"%pid),
                                        description = "Gender switch\ndisabled:Female\nenabled:Male",
                                        default = False))
                    
                else:

                    default = rescale(D['value_default'], D['value_min'], D['value_max'], 0, 100)
                    description = "%s - %s"%(D['label_min'], D['label_max'])
                    setattr(target, pid,  
                            IntProperty(name = D['label'], 

                                        update=eval("lambda a,b:updateShape(a,b,'%s')"%pid),
                                        description = description,
                                        min      = 0, max      = 100,
                                        soft_min = 0, soft_max = 100,


                                        default = int(round(default))))

                    setattr(values, pid,  
                            FloatProperty(name = D['label'], 
                                        min      = 0, max      = 100,
                                        soft_min = 0, soft_max = 100,
                                        default = default))

classes = (

)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered skeleton:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered skeleton:%s" % cls)
