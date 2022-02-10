### Copyright 2019 Machinimatrix
###
### This file is part of Avastar.
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
import bpy, sys
import logging, gettext

from . import const
from .const import *

log = logging.getLogger('avastar.bind')
registerlog = logging.getLogger("avastar.register")

def get_display_type(armobj):
    return armobj.data.display_type

def set_display_type(armobj, display_type):
    old_type = armobj.data.display_type
    armobj.data.display_type = display_type
    return old_type

classes = (

)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered armnture_util:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered armature_util:%s" % cls)
