### Copyright 2016, Matrice Laville
### Modifications 2016 None
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

import logging, traceback
import bpy, sys, os, gettext
from mathutils import Vector, Matrix, Color

from . import const, data, util, rig, shape

from .const import *
from .util import *
from . import bl_info
import bmesh
from bpy.app.handlers import persistent
from bpy.props import *
from .data import Skeleton

log = logging.getLogger("avastar.debug")
registerlog = logging.getLogger("avastar.register")

CENTER = (0,0,0)

def get_scaled_position(bone):

    def get_parent(bone):
        parent = bone.parent
        if parent and parent.get('is_structure',False):
            parent = get_parent(parent)
        return parent

    pos = Vector(bone.get(JOINT_BASE_HEAD_ID, (0,0,0)))
    off = Vector(bone.get('offset',  (0,0,0)))
 
    parent = get_parent(bone) 
    if parent:
        scale = util.get_bone_scale(parent)
    else:
        scale = Vector((1,1,1))

    pos   = pos + off
    
    if parent:
        pos  = Vector([scale[0]*pos[0], scale[1]*pos[1], scale[2]*pos[2]])
        pos += get_scaled_position(parent)
    return pos

def get_restposition(rbone):

    def get_rparent(bone):
        parent = bone.parent
        if parent and parent.is_structure:
            parent = get_rparent(parent)
        return parent

    parent = get_rparent(rbone)
    pos = Vector(rbone.relhead) if not rbone.is_structure else Vector((0, 0, 0))
    if parent:
        h = get_restposition(parent)
        format = "(% 0.6f % 0.6f % 0.6f)"
        spos = format % (pos[0], pos[1], pos[2])
        sh   = format % (h[0],   h[1],   h[2])
        spoh = format % (pos[0]+h[0], pos[1]+h[1], pos[2]+h[2])        

        pos += h
    return pos

def test_active_head_matrix(context=None, bind=True, with_joints=True, boneset=None, magnitude=0.0000001):
    if not context:
        context = bpy.context
    armobj = util.get_armature(context.object)
    bones  = util.get_modify_bones(armobj)
    Bones  = data.get_reference_boneset(armobj)

    active = context.object
    util.set_active_object(context, armobj)
    omode = util.ensure_mode_is('EDIT')

    mismatch_counter = 0
    test_counter     = 0
    hover = Skeleton.get_toe_hover_z(armobj, reset=True)
    for bone in bones:
        if boneset and not bone.name in boneset:
            continue

        test_counter += 1
        rbone = Bones[bone.name]
        M = Skeleton.headMatrix(context, bone, bones, bind, with_joints, hover)
        translation = M.translation

        restpos   = Vector(bone.head) if with_joints else get_restposition(rbone) if not bind else get_scaled_position(bone)
        bmag = (translation - restpos).magnitude
        if bmag > magnitude:
            mismatch_counter += 1
            print("test head matrix: mag:%f trans:[%s] | pos:[%s] [%s]" % (bmag, translation, restpos, bone.name))
        util.set_cursor(context, translation)

    if mismatch_counter == 0:
        print("test head matrix: %d bones passed" % (test_counter))
    else:
        print("test head matrix: found %d mismatches in %d tested bones" % (mismatch_counter, test_counter))
        
    util.ensure_mode_is(omode)
    util.set_active_object(context, active)

def test_restpose(context=None):

    EXCEPTIONS = ['head_length_773', 'male_skeleton_32']
    
    if not context: context = bpy.context
    armobj = util.get_armature(context.object)
    
    active = context.object
    util.set_active_object(context, armobj)
    omode = util.ensure_mode_is('EDIT')
    shape.ensure_drivers_initialized(armobj)

    driver_map = {}
    for D in armobj.ShapeDrivers.DRIVERS.values():
        for P in D:
            if P['type'] == 'driven' and len(P['driven']) > 0:
                driver = P['driven'][-1]['pid']
                driven = P['pid']
                driver_map[driver]=driven
                print("driver: %s  driven:%s" % (driver, driven) )

    print("RESTPOSE_FEMALE={")
    for D in armobj.ShapeDrivers.DRIVERS.values():
        for P in D:
            if P['type'] == 'bones':
                pid = driver_map.get(P['pid'], P['pid'])
                s = pid.rsplit('_', 1)
                if int(s[1]) < 1000:

                    if pid not in EXCEPTIONS:
                        min = P.get('value_min')
                        max = P.get('value_max')
                        val = P.get('value_default', 0)
                        fv = 100 * (val - min) / (max - min)
                        f0 = 100 * (0 - min) / (max - min) if min<=0 and max >=0 else fv
                        print("    '%s' : %f," % (pid, f0))    
    print("}")
    
    util.ensure_mode_is(omode)
    util.set_active_object(context, active    )
    
def test_control_rig(context=None, magnitude=0.0000001):

    if not context: context = bpy.context
    armobj = util.get_armature(context.object)
    
    active = context.object
    util.set_active_object(context, armobj)
    omode = util.ensure_mode_is('EDIT')
    
    bs = rig.get_all_deform_bones(armobj, sort=True, order='TOPDOWN')
    mbones = [b for b in bs if b.name[0]=='m']
    bones = util.get_modify_bones(armobj)
    
    for mbone in mbones:
        mname = mbone.name
        cname = mbone.name[1:]
        cbone = bones[cname]
        diff = (mbone.head - cbone.head) 
        mag = diff.magnitude
        if mag > magnitude:
            print("test joint bones: diff mbone/cbone. mag:%f bone:%s" % (mag, mbone.name) )
            print("     mbone head : %s" % mbone.head)
            print("     cbone head : %s" % cbone.head)
            
    util.ensure_mode_is(omode)
    util.set_active_object(context, active)
    
classes = (

)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered debug:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered debug:%s" % cls)

