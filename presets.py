### Copyright 2015, Gaia Clary
### Modifications 2015 Gaia Clary
###
### This file is part of Avastar 1.
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
import logging, gettext, os, time, re, shutil
import bpy, bmesh, sys
from bpy.props import *
from bpy.types import Menu, Operator, PropertyGroup
from . import data, shape, util
from .const import *

log = logging.getLogger('avastar.presets')
registerlog = logging.getLogger("avastar.register")




from bl_operators.presets import AddPresetBase



#



def shapekey_presets(self, context):
    AVASTAR_MT_shapekey_presets_menu.draw_generic(context, self.layout)

def shapekeysFromDictionary(obj, dict, update=True):

    if obj.data.shape_keys == None or obj.data.shape_keys.key_blocks == None:
        log.warning("Object has no Shape keys, can't import settings")
        return

    log.info("|- Paste shapekeys from dictionary to [%s]" % (obj.name) )

    blockcount = 0
    for name, data in dict.items():
        block = obj.data.shape_keys.key_blocks.get(name)
        if not block:
            continue

        block.mute       = data[0]
        block.value      = data[1]
        block.slider_min = data[2]
        block.slider_max = data[3]
        blockcount += 1

    log.info("|- Updated %d shapekeys in [%s]" % (blockcount, obj.name) )


def shapekeysAsDictionary(obj):
    dict = {}
    
    if obj.data.shape_keys == None or obj.data.shape_keys.key_blocks == None:
        log.warning("Object has no Shape keys, can't import settings")
        return

    log.info("|- Copy shape from [%s] to dictionary" % (obj.name) )
    
    key_blocks = obj.data.shape_keys.key_blocks
    for block in key_blocks:
        data = [
            block.mute,
            block.value,
            block.slider_min,
            block.slider_max
            ]
        dict[block.name] = data
    
    log.info("|- Added %d shapekeys to dictionary of [%s]" % (len(dict), obj.name) )
    return dict







def add_shapekey_preset(context, filepath):
    obj = context.object
 
    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "import avastar\n"
    "from avastar import presets, util\n"
    "\n"
    "obj = bpy.context.object\n"
    "\n"
    )
    dict = shapekeysAsDictionary(obj)
    file_preset.write("dict=" + str(dict) + "\n")
    file_preset.write("presets.shapekeysFromDictionary(obj,dict)\n")
    file_preset.close()


class AVASTAR_MT_shapekey_presets_menu(Menu):
    bl_label  = "Shapekey Presets"
    bl_description = "Shapekey Presets for the Avastar Rig"
    preset_subdir = os.path.join("avastar","shapekeys")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset
    
    @staticmethod
    def draw_generic(context, layout):

        if util.get_ui_level() < UI_EXPERIMENTAL:
            return

        row  = layout.row(align=True)
        row.menu("AVASTAR_MT_shapekey_presets_menu")
        row.operator("avastar.shapekey_presets_add", text="", icon=ICON_ADD)

        last_select = bpy.types.AVASTAR_MT_shapekey_presets_menu.bl_label
        if last_select not in ["Presets", "Shapekey Presets"]:
            row  = layout.row(align=True)
            row.alignment='RIGHT'
            row.label(text="Last selected Preset:")
            row.label(text=last_select)
            row.operator("avastar.shapekey_presets_remove", text="", icon=ICON_REMOVE).remove_active = True

        row = layout.row(align=False)

class AvastarAddPresetShapekey(AddPresetBase, Operator):
    bl_idname = "avastar.shapekey_presets_add"
    bl_label = "Add Shapekey Preset"
    bl_description = "Create new Preset from current Shapekey settings"
    preset_menu = "AVASTAR_MT_shapekey_presets_menu"

    preset_subdir = os.path.join("avastar","shapekeys")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_shapekey_preset(context, filepath)

class AvastarUpdatePresetShapekey(AddPresetBase, Operator):
    bl_idname = "avastar.shapekey_presets_update"
    bl_label = "Update Shapekey Preset"
    bl_description = "Store current Shapekey settings in last selected Preset"
    preset_menu = "AVASTAR_MT_shapekey_presets_menu"
    preset_subdir = os.path.join("avastar","shapekeys")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_shapekey_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_shapekey_preset(context, filepath)

class AvastarRemovePresetShapekey(AddPresetBase, Operator):
    bl_idname = "avastar.shapekey_presets_remove"
    bl_label = "Remove Shapekey Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_shapekey_presets_menu"
    preset_subdir = os.path.join("avastar","shapekeys")










def add_retarget_preset(context, filepath):

    arm   = data.get_retarget_target(context)
    bones = arm.data.bones

    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "import avastar\n"
    "from avastar import data, util\n"
    "\n"
    "context = bpy.context\n"
    "arm_obj = data.get_retarget_target(context)\n"
    "\n"
    )
    
    dict = data.get_dict_from_mtui_bones(context)        
    file_preset.write(
    "dict=" + str(dict) + "\n"
    "#data.clear_mtui_bones(context, arm_obj)\n"
    "data.fill_mtui_bones(context, dict, arm_obj)\n"   
    )
    
    file_preset.close()


class AVASTAR_MT_retarget_presets_menu(Menu):
    bl_label  = "Retarget Presets"
    bl_description = "Retarget Presets for the Avastar Rig"
    preset_subdir = os.path.join("avastar","targetmaps")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class AvastarAddPresetRetarget(AddPresetBase, Operator):
    bl_idname = "avastar.retarget_presets_add"
    bl_label = "Add Retarget Preset"
    bl_description = "Create new Preset from current Slider settings"
    preset_menu = "AVASTAR_MT_retarget_presets_menu"
    preset_subdir = os.path.join("avastar","targetmaps")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_retarget_preset(context, filepath)


class AvastarUpdatePresetRetarget(AddPresetBase, Operator):
    bl_idname = "avastar.retarget_presets_update"
    bl_label = "Update Retarget Preset"
    bl_description = "Retarget settings in last selected Preset"
    preset_menu = "AVASTAR_MT_retarget_presets_menu"
    preset_subdir = os.path.join("avastar","targetmaps")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_retarget_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_retarget_preset(context, filepath)


class AvastarRemovePresetRetarget(AddPresetBase, Operator):
    bl_idname = "avastar.retarget_presets_remove"
    bl_label = "Remove Retarget Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_retarget_presets_menu"
    preset_subdir = os.path.join("avastar","targetmaps")







def add_shape_preset(context, filepath):
    arm    = util.get_armature(context.object)
    pbones = arm.pose.bones

    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "import avastar\n"
    "from avastar import shape, util\n"
    "\n"
    "arm    = util.get_armature(bpy.context.object)\n"
    "\n"
    )
    dict = shape.asDictionary(arm)
    file_preset.write("dict=" + str(dict) + "\n")
    file_preset.write("shape.resetToDefault(arm)\n")
    file_preset.write("shape.fromDictionary(arm,dict)\n")
    file_preset.close()


class AVASTAR_MT_shape_presets_menu(Menu):
    bl_label  = "Shape Presets"
    bl_description = "Shape Presets for the Avastar Rig"
    preset_subdir = os.path.join("avastar","shapes")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class AvastarAddPresetShape(AddPresetBase, Operator):
    bl_idname = "avastar.shape_presets_add"
    bl_label = "Add Shape Preset"
    bl_description = "Create new Preset from current Slider settings"
    preset_menu = "AVASTAR_MT_shape_presets_menu"

    preset_subdir = os.path.join("avastar","shapes")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_shape_preset(context, filepath)

class AvastarUpdatePresetShape(AddPresetBase, Operator):
    bl_idname = "avastar.shape_presets_update"
    bl_label = "Update Retarget Preset"
    bl_description = "Store current Slider settings in last selected Preset"
    preset_menu = "AVASTAR_MT_shape_presets_menu"
    preset_subdir = os.path.join("avastar","shapes")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_shape_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_shape_preset(context, filepath)

class AvastarRemovePresetShape(AddPresetBase, Operator):
    bl_idname = "avastar.shape_presets_remove"
    bl_label = "Remove Retarget Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_shape_presets_menu"
    preset_subdir = os.path.join("avastar","shapes")





classes = (
    AVASTAR_MT_shapekey_presets_menu,
    AvastarAddPresetShapekey,
    AvastarUpdatePresetShapekey,
    AvastarRemovePresetShapekey,
    AVASTAR_MT_retarget_presets_menu,
    AvastarAddPresetRetarget,
    AvastarUpdatePresetRetarget,
    AvastarRemovePresetRetarget,
    AVASTAR_MT_shape_presets_menu,
    AvastarAddPresetShape,
    AvastarUpdatePresetShape,
    AvastarRemovePresetShape,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered presets:%s" % cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered presets:%s" % cls)

