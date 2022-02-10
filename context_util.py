### Copyright 2016 Gaia Clary (Machinimatrix)
###
### This file is part of Avastar
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

import bpy, logging
from . import util

log = logging.getLogger('avastar.context')
registerlog = logging.getLogger("avastar.register")

class set_context:
    def __init__(self, context, obj, mode):

        self.context = context
        self.active = self.context.active_object if context else None
        self.amode = self.active.mode if self.active else None
        self.asel = util.object_select_get(self.active) if self.active else None
        
        self.obj = obj
        self.nmode = mode
        self.omode = self.obj.mode if self.obj else None
        self.osel = util.object_select_get(self.obj) if self.obj else None

    def __enter__(self):
        if self.active:

            util.ensure_mode_is('OBJECT')

        if self.obj:

            if util.get_active_object(self.context) != self.obj:
                util.set_active_object(self.context, self.obj)
            util.ensure_mode_is(self.nmode)

        return self.obj

    def __exit__(self, type, value, traceback):
        if type or value or traceback:
            log.error("Exception type: %s" % type )
            log.error("Exception value: %s" % value)
            log.error("traceback: %s" % traceback)
            raise

        if self.obj:

            util.ensure_mode_is(self.omode)
            util.object_select_set(self.obj, self.osel)

        if self.active:

            if util.get_active_object(self.context) != self.active:
                util.set_active_object(self.context, self.active)
            util.ensure_mode_is(self.amode)
            util.object_select_set(self.active, self.asel)

        return True

classes = (

)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered context_util:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered context_util:%s" % cls)

