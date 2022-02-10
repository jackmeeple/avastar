### Copyright 2016, Matrice Laville
### Modifications: None
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

import bpy, bmesh, sys, logging, os, mathutils
from bpy.props import *
from bpy.types import Menu, Operator
from bl_operators.presets import AddPresetBase
from bpy_extras.io_utils import ImportHelper
from bpy.app.handlers import persistent
from . import armature_util, context_util, const, propgroups, bind, create, data, mesh, messages, rig, shape, util
from .const import *
from .context_util import *
from .util import ArmatureError, PVector, mulmat
from .data import Skeleton

log=logging.getLogger("avastar.updaterig")
registerlog = logging.getLogger("avastar.register")

class UpdateAvastarRig(bpy.types.Operator):
    '''
    Convert/Update/Cleanup Rigs
    '''
    bl_idname = "avastar.update_rig"
    bl_label  = "Update Rig"
    bl_description = "Check Rig for compatibility issues with current Avastar version\n"\
                   + "Optional: Fix issues where necessary to make sure Avastar works as intended."


    def need_tinker_fix(self, bones):
        if 'Tinker' in bones:
            log.warning("Tinker Bone exists, no need to fix")
            return False
        if 'PelvisInv' in bones:
            log.warning("Need to replace PelvisInv by Tinker bone")
            return True
        raise ArmatureError

    def fix_tinker_bone(self, armobj):
        util.ensure_mode_is('EDIT')
        bone = armobj.data.bones.get('PelvisInv')
        bone.name = 'Tinker'
        self.replace_constraint_targets(armobj, 'PelvisInv', 'Tinker')

    def replace_constraint_targets(self, armobj, old_name, new_name):
        util.ensure_mode_is('POSE')
        for pbone in armobj.pose.bones:
            for con in [con for con in pbone.constraints if hasattr(con,"subtarget")]:
                subtarget = con.subtarget
                if con.subtarget == old_name:
                    con.subtarget = new_name



    def need_animation_fix(self, bones):
        mbones = [b for b in bones if b.name[0]=='m']
        for bone in mbones:
            animation_bone = bones.get('bone.name[1:]')
            if not animation_bone:
                log.warning("Missing Animation bones, need to add them")
                return True
        return False

    def fix_animation_bones(self, armobj):
        pass


    def need_constraints_fix(self, bones):
        return True

    def fix_constraints(self, armobj):
        pass


    def execute(self, context):
        armobj = util.get_armature_from_context(context)
        if not armobj:
            log.warning("No armature in current context (Update Rig aborted)")
            return {'CANCELLED'}

        bones = armobj.data.bones

        fix_tinker = self.need_tinker_fix(bones)
        fix_animation = self.need_animation_fix(bones)
        fix_constraints = self.need_constraints_fix(bones)

        if not (fix_tinker or fix_animation or fix_constraints):
            return {'FINISHED'}

        active = util.set_active_object(context, armobj)
        amode = active.mode

        if fix_tinker:
            self.fix_tinker_bone(armobj)
        if fix_animation:
            self.fix_animation_bones(armobj)
        if fix_constraints:
            self.fix_constraints(armobj)

        util.set_active_object(context, active)
        util.ensure_mode_is(amode)
        return {'FINISHED'}

classes = (
    UpdateAvastarRig,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered updaterig:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered updaterig:%s" % cls)
