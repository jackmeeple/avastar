### Copyright 2011, Magus Freston, Domino Marama, and Gaia Clary
### Modifications 2013-2015 Gaia Clary
### Modifications 2015      Matrice Laville
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

from collections import namedtuple
import logging, traceback
import bpy, sys, os, gettext
from math import radians, sqrt, pi
from mathutils import Vector, Matrix, Quaternion,Euler, Color
import bmesh
from bpy.app.handlers import persistent
from bpy.props import *
from . import bl_info, const, messages
from .const import *
import time, shutil, io

from mathutils import geometry

LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')
TMP_DIR    = os.path.join(os.path.dirname(__file__), 'tmp')
DATAFILESDIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)),'lib')

log = logging.getLogger("avastar.util")
timerlog = logging.getLogger("avastar.timer")
visitlog = logging.getLogger('avastar.visit')
registerlog = logging.getLogger("avastar.register")





def get_context_copy(context):
    return context.copy()


def object_get_collections(context, obj):
    collections={}
    for collection in bpy.data.collections:

        if obj.name in collection.objects:
            collections[collection.name] = [collection, collection.hide_viewport]
    return collections

def copy_collection_visibility(context, tgt, src):
    old_set = set()
    oactive = set_active_object(context, tgt)
    collections = object_get_collections(context, src)
    log.debug("Found %d collections from source %s" % (len(collections), src.name) )
    try:

        for collection_data in collections.values():
            bpy.ops.object.collection_link(collection=collection_data[INDEX_COLLECTION_OBJECT].name)
    except:
        pass

    set_active_object(context,oactive)
    return old_set

def set_active_collection_of(context, obj):
    view_layer = context.view_layer
    colls = [c for c in view_layer.layer_collection.children if obj.name in c.collection.objects]
    if colls:

        view_layer.active_layer_collection = colls[0]

def mulmat(a,*argv):
    result = a
    for b in argv:
        result = result @ b
    return result

def get_cursor(context):
    return context.scene.cursor.location.copy()

def set_cursor(context, loc):
    context.scene.cursor.location = loc

def object_show_in_front(obj, val=None):
    old_val = obj.show_in_front
    if val:
        obj.show_in_front = val
    return old_val

def add_uv_layer(mesh, name='UVMap'):
    uv = mesh.uv_layers.new(name=name)
    return uv

def get_uv_index_for_layer(mesh, name):
    index = mesh.uv_layers.keys().index(name)
    return index

def get_uv_layers(mesh):
    return mesh.uv_layers

def get_active_uv_layer(mesh):
    return mesh.uv_layers.active

def set_active_uv_layer(mesh, uv_layer):
    mesh.uv_layers.active = uv_layer

def get_uv_layer(mesh, index):
    return mesh.uv_layers[index]


def update_view_layer(context):
    context.view_layer.update()


def update_depsgraph(context):
    depsgraph = context.evaluated_depsgraph_get()
    depsgraph.update()

def update_full():



    mode_set(mode='EDIT', toggle=True)
    mode_set(mode='EDIT', toggle=True)

def set_mod_axis(mod, axis_id, val):
    try:
        mod.use_axis[axis_id]=val
    except:
        log.error("illegal axis_id %d for modifier %s" % (axis_id, mod.name))
        raise

def set_con_axis(con, axis_id, val):
    if axis_id == 0:
        con.use_x = val
    elif axis_id == 1:
        con.use_y = val
    elif axis_id == 2:
        con.use_z = val
    else:
        log.error("illegal axis_id %d for constraint %s" % (axis_id, con.name))
        raise

def link_object(context, obj):
    context.collection.objects.link(obj)
    return obj


def unlink_object(context, obj):
    collections = [c for c in bpy.data.collections if obj.name in c.objects]
    for collection in collections:
        collection.objects.unlink(obj)

def get_active_object(context):
    view_layer = get_value_from(context, 'view_layer')
    if view_layer:
        active = view_layer.objects.active 
    else:
        active = get_value_from(context, 'active')
    return active


def get_value_from(container, key):
    if not container:
        return None

    try:
        val = getattr(container, key)
    except:
        try:
            val = container.get(key)
        except:
            log.warning("Failed to get %s from container of type %s" % (key, type(container)))
            val = None
    return val


def set_active_object(context, new_active):
    old_active = get_active_object(context)
    if new_active and new_active != old_active:
        context.view_layer.objects.active = new_active
        new_active.select_set(True)
    return old_active


def object_hide_get(obj, context=None):
    return obj.hide_get()

def object_hide_set(obj, hide, context=None):
    old_hide = object_hide_get(obj, context=context)
    obj.hide_set(hide)
    return old_hide

def object_select_get(obj):
    return obj.select_get()

def object_select_set(obj, select):
    old_select = object_select_get(obj)
    obj.select_set(select)
    return old_select

def object_visible_get(obj, context=None):
    if context:
        return obj.visible_get(view_layer=context.view_layer)
    return obj.visible_get()

def debug_show_childset(obj, indent=0, msg=''):
    log.warning("%s%s: o:%s p:%s" % (indent*" ", msg, obj.name, obj.parent.name if obj.parent else ''))
    for child in obj.children:
        debug_show_childset(child, indent+2)




def get_checksum(array, seed=815, limit=1000000):
    result = 0
    for item in array:
        result += item
        result *= seed
        result %= limit
    return result


def calc_vertex_sum(vertices):
    cs= fast_get_verts(vertices)
    sum = get_checksum(cs)
    return sum


def calc_weight_sum(ob):

    return 0


def calc_shapekey_sum(shape_keys):
    sum = 0

    if not shape_keys:
        return sum

    key_blocks = shape_keys.key_blocks
    if not key_blocks:
        return sum

    for index, block in enumerate(key_blocks):
        if index == 0:
            continue

        co = fast_get_verts(block.data)
        sum += get_checksum(co)

    return sum


def calc_object_checksum(ob):
    sum = calc_vertex_sum(ob.data.vertices)
    sum += calc_weight_sum(ob)
    sum += calc_shapekey_sum(ob.data.shape_keys)
    return sum



IN_USER_MODE = True
def set_operate_in_user_mode(mode):
    global IN_USER_MODE
    omode = IN_USER_MODE
    if IN_USER_MODE != mode:

        IN_USER_MODE = mode
    return omode

def is_in_user_mode():
    global IN_USER_MODE
    return IN_USER_MODE

tic = time.time()
toc = tic
def tprint(s):
    global tic, toc
    toc = time.time()
    print( "%0.6f | %s" % (toc-tic, s))
    tic = toc
    return toc

def draw_info_header(layout, link, msg="panel|the awesome message", emboss=False, icon=ICON_INFO, op=None, is_enabled=None):
    preferences = getAddonPreferences()
    if preferences.verbose:
        prop = layout.operator("avastar.generic_info_operator", text="", icon=icon, emboss=emboss)
        prop.url=link
        prop.msg=msg
        prop.type=SEVERITY_INFO
        
        if op and is_enabled:
            layout.prop(op, is_enabled, text="")

class GenericInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.generic_info_operator"
    bl_label       = "Infobox"
    bl_description = "Click icon to open extended tooltip"
    bl_options = {'REGISTER', 'UNDO'}
    msg        : StringProperty(default="brief|long|link")
    url        : StringProperty(default=DOCUMENTATION)
    type       : StringProperty(default=SEVERITY_INFO)

    def execute(self, context):
        ErrorDialog.dialog(self.msg+"|"+self.url, self.type)
        return {"FINISHED"}

class WeightmapInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.weightmap_info_operator"
    bl_label       = "weightmap info"
    bl_description = "Number of accepted/denied Bone deforming weightmaps (click icon for details)"

    msg        : StringProperty()
    icon       : StringProperty()

    def execute(self, context):
        ErrorDialog.dialog(self.msg, self.icon)
        return {"FINISHED"}

class TrisInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.tris_info_operator"
    bl_label       = "Tricount info"
    bl_description = "Number of used Tris (click icon for details)"

    msg        : StringProperty()
    icon       : StringProperty()
    
    def execute(self, context):
        ErrorDialog.dialog(self.msg, self.icon)
        return {"FINISHED"}

class BaketoolInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.baketool_info_operator"
    bl_label       = "Baketool info"
    bl_description = "Object has all its material textures baked"

    msg        : StringProperty()
    icon       : StringProperty()

    def execute(self, context):
        ErrorDialog.dialog(self.msg, self.icon)
        return {"FINISHED"}

class Baketool2InfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.baketool2_info_operator"
    bl_label       = "Baketool info"
    bl_description = "Material without baked textures"

    msg        : StringProperty()
    icon       : StringProperty()

    def execute(self, context):
        ErrorDialog.dialog(self.msg, self.icon)
        return {"FINISHED"}

class SliderInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.slider_info_operator"
    bl_label       = "Slider info"
    bl_description = "\nIf Context object is a Mesh:\n"\
                   + "This Bone has weights on the active Mesh\n\n"\
                   + "If context is Armature\n"\
                   + "This Bone has weights on at least one mesh\n"

    msg        : StringProperty()
    icon       : StringProperty()

    def execute(self, context):
        ErrorDialog.dialog(self.msg, self.icon)
        return {"FINISHED"}

class MaterialInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.material_info_operator"
    bl_label       = "Material info"
    bl_description = "Material Bake tool (Click for info)"
    icon       : StringProperty(default=ICON_INFO)

    def execute(self, context):
        msg = "The Material Bake tool\n"\
            + "\n"\
            + "Note:\n"\
            + "When you see this message, then your Rig contains Custom meshes.\n"\
            + "In that case you can not assign Avastar Materials from here.\n"\
            + "For Avastar meshes this info box will be replaced by a selection box\n"\
            + "from where you assign predefined materials to your character.\n"

        ErrorDialog.dialog(msg, self.icon)
        return {"FINISHED"}


class ShaderInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.shader_info_operator"
    bl_label       = "Shader info"
    bl_description = "Avatar Material Presets\n"\
                   + "The presets are only available in\n\n"\
                   + "- Material Preview\n"\
                   + "- Render View\n\n"\
                   + "You can change the Shading type in the\n"\
                   + "Viewport Shading Selector (see top row)\n"
    icon       : StringProperty(default=ICON_INFO)

    def execute(self, context):
        msg = self.bl_description
        ErrorDialog.dialog(msg, self.icon)
        return {"FINISHED"}


def missing_uv_map_text(targets):
    nwo   = ""
    no_uv_layers = 0
    for obj in [o for o in targets if o.data.uv_layers.active == None]:
        no_uv_layers += 1
        nwo += "* " + obj.name+"\n"
    msg= messages.msg_missing_uvmaps % (no_uv_layers, pluralize("Mesh", no_uv_layers), nwo)
    return msg
        
class UVmapInfoOperator(bpy.types.Operator):
    bl_idname      = "avastar.uvmap_info_operator"
    bl_label       = "UVmap info"
    bl_description = "Number of missing UV maps (click icon for details)"

    msg        : StringProperty()
    icon       : StringProperty()
    
    def execute(self, context):
        ErrorDialog.dialog(self.msg, self.icon)
        return {"FINISHED"}

class Ticker:
    def __init__(self, fire = 10):
        self._fire   = fire
        self._ticker = 0

    @property
    def tick(self):
        self._ticker += 1

    @property
    def fire(self):
        return (self._ticker % self._fire) == 0

bpy.types.Scene.ticker = Ticker()


def set_disable_handlers(scene, new_state):
    old_state = scene.SceneProp.armature_suppress_all_handlers
    scene.SceneProp.armature_suppress_all_handlers = new_state
    return old_state


def handler_can_run(scene, check_ticker=True):
    if not scene:
        return False

    if scene.SceneProp.armature_suppress_all_handlers:
        return False
    if check_ticker:
        return scene.ticker.fire
    return True


class OperatorCallContext():
    def __enter__(self):
        scene = bpy.context.scene
        prefs = getPreferences()


        self.curact = get_active_object(bpy.context)
        self.cursel = { ob : ob.select for ob in scene.objects }
        


        self.use_global_undo = prefs.edit.use_global_undo
        prefs.edit.use_global_undo = False

        return (self.curact, self.cursel)
    
    def __exit__(self, exc_type, exc_value, traceback):
        context = bpy.context
        scene = context.scene
        prefs = getPreferences()


        set_active_object(context, self.curact)
        for ob in scene.objects:
            object_select_set(ob, self.cursel.get(ob, False))

        prefs.edit.use_global_undo = self.use_global_undo

def select_single_object(ob):
    context = bpy.context
    scene = context.scene
    
    set_active_object(context, ob)
    for tob in scene.objects:
        object_select_set(tob, (tob == ob))
        
def unselect_all_objects(scene):
    for tob in scene.objects:
        object_select_set(tob, False)

def select_set_edit_bones(armobj, select=True):
    for b in armobj.data.edit_bones:
        b.select=select

def is_child_of(parent,child):
    while child and parent:
        if child.parent == parent:
            return True
        child = child.parent
    return False


class Error(Exception):
    pass


class MeshError(Error):
    pass


class ColladaExportError(Error):
    pass


class ColladaExportWarning(Warning):
    pass


class ArmatureError(Error):
    pass

class Warning(Exception):
    pass


def generate_dialog(messages, template):
    texts = [message[0] for message in messages]
    msg = template % (len(texts), ''.join(texts))
    return msg



class ErrorDialog(bpy.types.Operator):
    bl_idname = "avastar.error"
    bl_label = ""
    
    msg=""
    sysinfo=""
    error_list = None
    label = None

    msg_template = \
'''Unfortunately Avastar-%s detected a program error.
%sIf you need further help, then create a ticket and report this error to:

https://support.machinimatrix.org/tickets

The Error Context (needed for tickets):
%s'''

    sysinfo_template = \
'''
Avastar version : %s
Blender version : %s
Armature version: %s
Operating system: %s
The Stack trace :

%s'''
    
    @staticmethod
    def exception(e, context=None):
        ErrorDialog.error_list = None
        if isinstance(e, MeshError):
            ErrorDialog.dialog(str(e), SEVERITY_MESH_ERROR)
        elif isinstance(e, ArmatureError):
            ErrorDialog.dialog(str(e), SEVERITY_ARMATRUE_ERROR)
        elif isinstance(e, ColladaExportError):
            msg, ErrorDialog.error_list, label = e.args
            ErrorDialog.dialog(msg, SEVERITY_EXPORT_ERROR, label=label)
        elif isinstance(e, ColladaExportWarning):
            msg, ErrorDialog.error_list, label = e.args
            ErrorDialog.dialog(msg, SEVERITY_WARNING, label=label)
        elif isinstance(e, Error):
            ErrorDialog.dialog(str(e), SEVERITY_ERROR)
        elif isinstance(e, Warning):
            ErrorDialog.dialog(str(e), SEVERITY_WARNING)
        else:
            ctx = context if context else bpy.context
            ava_ver = get_addon_revision()
            pref     = getAddonPreferences()
            pref.addonVersion
            pref.blenderVersion
            pref.operatingSystem
            rigs, obs = getSelectedArmsAndObjs(ctx)
            cause=""
            rig_versions = []
            if rigs:
                for rig in rigs:
                    version = rig.get('version')
                    if version:
                        rig_ver = get_version_number(version)
                        version = "%s.%s.%s" % (version[0], version[1], version[2])
                        log.warn("rig_ver: %s" % rig_ver)
                        log.warn("ava_ver: %s" % ava_ver)
                        if rig_ver < ava_ver:
                            cause='\nPossible cause: Outdated Rig version %s\nYour action   : Update the rig and try again\n\n' % version
                    else:
                        version = "unversioned"
                    version = ("%s (Armature: %s)" % (version, rig.name))
                    rig_versions.append(version)
            else:
                rig_versions = ["no Armature in context %s" % ctx.object]
            rig_versions = ", ".join(rig_versions)
            sysinfo = ErrorDialog.sysinfo_template % (pref.addonVersion, pref.blenderVersion, rig_versions, pref.operatingSystem, traceback.format_exc())
            msg = ErrorDialog.msg_template % (pref.addonVersion, cause, sysinfo)
            ErrorDialog.dialog(msg, SEVERITY_ERROR, sysinfo)
        
    @staticmethod
    def dialog(msg, severity, sysinfo="", label=""):
        ErrorDialog.msg = msg
        ErrorDialog.severity = severity
        ErrorDialog.sysinfo = sysinfo
        ErrorDialog.label = label
        bpy.ops.avastar.error('INVOKE_DEFAULT')

    def draw(self, context):
        ErrorDialog.draw_generic(self.layout, self.msg, ErrorDialog.severity, self.sysinfo, label=self.label)

    @staticmethod
    def draw_generic(layout, msg, severity, sysinfo='', generate_docu_link=True, label=""):

        def create_label(layout, severity, label):
            if severity != SEVERITY_HINT:
                box = layout.column() 

                if severity == SEVERITY_INFO:
                    box.label(text="Info: %s"%label, icon=ICON_INFO)
                elif severity == SEVERITY_WARNING:
                    box.label(text="Hint: %s"%label, icon=ICON_INFO)
                elif severity == SEVERITY_STRONG_WARNING:
                    box.label(text="Warning: %s"%label, icon=ICON_ERROR)
                elif severity == SEVERITY_EXPORT_ERROR:
                    box.label(text="Export errors: %s"%label, icon=ICON_ERROR)
                elif severity == SEVERITY_MESH_ERROR:
                    box.label(text="Mesh has issues: %s"%label, icon=ICON_HAND)
                elif severity == SEVERITY_ARMATURE_ERROR:
                    box.label(text="Armature has issues: %s"%label, icon=ICON_HAND)
                else:
                    box.label(text="Error: %s"%label, icon=ICON_ERROR)
                layout.separator()

        layout.active_default=False
        help_url = DOCUMENTATION if generate_docu_link else None
        help_topic = ""
        paragraphs = msg.split("|")
        footer = paragraphs[4] if len(paragraphs) > 4 else None
        if len(paragraphs) > 1:
            label = paragraphs[0]
            text  = paragraphs[1]
            if len(paragraphs) > 2:
                paragraph = paragraphs[2]
                if len(paragraph) > 0:
                    help_topic = " --> %s" % paragraphs[3] if len(paragraphs)>3 else paragraph
                    if paragraph[0] in [".","/"]:
                       help_url = DOCUMENTATION+paragraph
                    else:
                       help_url = paragraph
        else:

            text  = "\n"+msg

        box = layout.box()
        create_label(box, severity, label)
        col = box.column(align=True)

        if sysinfo != '':
            prop = col.operator("avastar.copy_to_paste_buffer", text="Copy Error context - Tip: In your Text editor Paste with CTRL-V")
            prop.msg = sysinfo
            col = box.column(align=True)

        if ErrorDialog.error_list:
            has_operator = False # use one link per line instead, see below
            for err, help_topic in ErrorDialog.error_list:
                row=col.row(align=True)
                if help_topic and help_topic != '':
                    help_url = DOCUMENTATION + help_topic
                    row.operator("wm.url_open", icon=ICON_QUESTION).url=help_url
                    help_url = None
                else:
                    row.label(text="", icon=ICON_BLANK1)
                row.label(text=err[0:-1])
                col = box.column(align=True)

        has_operator = draw_textblock(col, text, help_topic, help_url)

        if help_url and not has_operator:
            col.operator("wm.url_open", text="Avastar Online Help " + help_topic, icon=ICON_URL).url=help_url

        if footer:
            col = box.column(align=True)
            for line in footer.split('\n'):
                col.label(text=line)

    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        user_preferences = getPreferences()
        width = 500
        return context.window_manager.invoke_props_dialog(self, width=width)
 
class ButtonCopyToPastebuffer(bpy.types.Operator):
    bl_idname = "avastar.copy_to_paste_buffer"
    bl_label = "Copy message"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Copy message to paste buffer"
    
    msg : StringProperty()
    
    def draw(self, context):
        help_text = "Go to your text editor. Then\n"\
                  + "press CTRL-V to paste the text.\n\n"\
                  + "Your Copy Buffer contains:"
        col = self.layout.column()
        draw_textblock(col, help_text)
        box = self.layout.box()
        col = box.column()
        draw_textblock(col, self.msg)

    def execute(self, context):
        context.window_manager.clipboard = self.msg
        return{'FINISHED'}

def draw_textblock(col, text, help_topic="", help_url=None):
    lines = text.split("\n")
    has_operator = False
    for line in lines:
        if help_url and line.startswith('$operator'):
            col.operator("wm.url_open", text="Avastar Online Help " + help_topic, icon=ICON_URL).url=help_url
            has_operator = True
        else:
            col.label(text=line)
    return has_operator


class ExpandablePannelSection(bpy.types.Operator):
    bl_idname = "avastar.expandable_panel_section"
    bl_label = "Hide/Unhide"
    bl_description = "Hide/Unhide Section"

    visible = True
    toggle_details_display : BoolProperty(default=False, name="Toggle Details",
        description="Toggle Details Display")

    def execute(self, context):
        ExpandablePannelSection.visible = not ExpandablePannelSection.visible
        return{'FINISHED'}

    def draw_collapsible(op, layout, label=None):
        if label == None:
            label = op.bl_label

        col = layout.column(align=True)
        row=col.row(align=True)
        row.operator(op.bl_idname, text='', icon = get_collapse_icon(op.visible), emboss=False)
        row.operator(op.bl_idname, text=label, emboss=False)



def apply_armature_modifiers(context, obj, preserve_volume=False):
    ctx                  = get_context_copy(context)
    ctx['active_object'] = obj
    ctx['object']        = obj

    try:
        for mod in obj.modifiers:
            if mod.type=="ARMATURE":
                if preserve_volume is not None:
                    mod.use_deform_preserve_volume=preserve_volume
                ctx['modifier'] = mod
                obj['use_deform_preserve_volume'] = mod.use_deform_preserve_volume

                if get_blender_revision() < 290000:

                    bpy.ops.object.modifier_apply(ctx, apply_as='DATA', modifier=mod.name)
                else:

                    bpy.ops.object.modifier_apply(ctx, modifier=mod.name)


    except:
        print("apply_armature_modifiers: Failed to apply modifier on Object %s" % obj.name)
        raise

def visualCopyMesh(context, target, apply_pose=True, apply_shape_modifiers=False, remove_weights=False, preserve_volume=None, as_name=False):

    def apply_modifiers(context, dupobj):
        try:
            ctx                  = get_context_copy(context)
            ctx['active_object'] = dupobj
            ctx['object']        = dupobj

            for mod in dupobj.modifiers:
                if mod.type=="SHRINKWRAP":
                    ctx['modifier'] = mod
                    bpy.ops.object.modifier_apply(ctx, apply_as='SHAPE', modifier=mod.name)
                    key_blocks = dupobj.data.shape_keys.key_blocks
                    N = len(key_blocks)
                    sk = key_blocks[N-1]
                    if MORPH_SHAPE in key_blocks:
                        sk.relative_key = key_blocks[MORPH_SHAPE]
                    sk.value        = 1.0
        except:
            print("Unexpected error while applying modifier:", sys.exc_info()[0])
            pass

    def apply_shape_keys(context, dupobj):
        key_blocks = dupobj.data.shape_keys.key_blocks
        N = len(key_blocks)
        if N > 0:
            if True:
                sk = dupobj.shape_key_add(name="mix", from_mix=True)
                N += 1
                for ii in range (N-2, -1, -1):
                    dupobj.shape_key_remove(key_blocks[ii])
                dupobj.shape_key_clear()

    def freeze_pose(context, dupobj):
        try:

            for key in dupobj.keys():
                del dupobj[key]
        except:
            pass

        apply_armature_modifiers(context, dupobj, preserve_volume)

        if remove_weights:
            mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')

            try:
                bpy.ops.object.vertex_group_remove_from(use_all_groups=True, use_all_verts=True)
            except:

                bpy.ops.object.vertex_group_remove_from(all=True)

            mode_set(mode='OBJECT')

    def create_dupobj(context, target):

        def delete(obj,key):
            if key in obj:
                del obj[key]

        def link(context,dupobj,obj):
            collections = [c for c in bpy.data.collections if obj.name in c.objects]
            if not collections:
                context.scene.collection.objects.link(dupobj)
            else:
                for collection in collections:
                    collection.objects.link(dupobj)

        dupobj      = target.copy()
        dupobj.data = target.data.copy()
        delete(dupobj,MORPH_SHAPE)
        delete(dupobj,REFERENCE_SHAPE)
        delete(dupobj,'mesh_id')
        delete(dupobj,'avastar-mesh')

        link(context, dupobj, target)
        return dupobj


    active_object = get_active_object(context)
    amode = ensure_mode_is('OBJECT')

    dupobj = create_dupobj(context, target)
    set_active_object(context, dupobj)

    if apply_shape_modifiers:
        apply_modifiers(context, dupobj)


    if dupobj.data.shape_keys:
        apply_shape_keys(context, dupobj)


    if apply_pose:
        freeze_pose(context, dupobj)


    set_active_object(context, active_object)
    ensure_mode_is(amode)
    return dupobj.name if as_name else dupobj


def fetch_collection(context, name):

    collection = bpy.data.collections.get(name)
    if collection:
        return collection

    collection = bpy.data.collections.new(name)
    context.scene.collection.children.link(collection)
    return collection



def get_bone_scales(bone, use_custom=True):





    s0 = Vector(bone.get('scale0',(1,1,1)))
    if use_custom:

        x = bone.get('restpose_scale_y', s0[0])
        y = bone.get('restpose_scale_x', s0[1])
        z = bone.get('restpose_scale_z', s0[2])
        sc = Vector((x,y,z))
        if abs(sc.magnitude-s0.magnitude) > MIN_BONE_LENGTH and \
           abs(sc.normalized().dot(s0.normalized()) - 1) > MIN_BONE_LENGTH:
                log.debug("Custom Scale: SL: %s -> Custom: %s  Bone: %s" % (s0, sc, bone.name) )
                s0 = sc
    ds = Vector(bone.get('scale',(0,0,0)))

    return ds, s0

def add_list(alist, rlist, mask):
    return [val+delta if m else val for val, delta, m in zip(alist, rlist, mask)]

def subtract_list(alist, rlist, mask):
    return [val-delta if m else val for val, delta, m in zip(alist, rlist, mask)]

def mul(v1,v2):
    return Vector([v1[i]*v2[i] for i in range(3)])
    
def get_bone_scale_matrix(bone, f=1, inverted=False, normalized=True):
    scale = get_bone_scale(bone, f, normalized)
    M = matrixScale(scale)
    if inverted:
        M = M.inverted()
    return M

def get_bone_scale(bone, f=1, normalized=True, use_custom=True):
    ds, s0 = get_bone_scales(bone, use_custom)
    scale = f*ds+s0

    if normalized:
       scale = Vector([scale[i]/s0[i] for i in range(3)])

    return scale


def bone_can_scale(armobj, bone):
    if armobj.RigProp.rig_lock_scales:
        joints = get_joint_cache(armobj)
        allow_scaling = not has_joint_position(joints, bone, check_tail=False)
    else:
        allow_scaling = True
    return allow_scaling
    

def getBoneScaleMatrix(armobj, bone, MScale=None, normalize=True, verbose=False, use_custom=True, with_appearance=True):

    def scalemat(MScale, scale):
        for i in range(0,3):
            MScale[i][i] *= scale[i]

    def normat(MScale, scaleBasis):
        for i in range(0,3):
            if abs(scaleBasis[i]) < 0.000001:
                scaleBasis[i] = 0.000001 * ( 1 if scaleBasis[i] > 0 else -1)
            MScale[i][i] /= scaleBasis[i]

    if MScale == None:
        MScale = Matrix()

    if not bone:
        return MScale

    if bone.use_deform:
        scaleDelta, scaleBasis = get_bone_scales(bone, use_custom)
    else:
        scaleDelta = Vector((0,0,0))
        scaleBasis = Vector((1,1,1))

    allow_scaling = bone_can_scale(armobj, bone)
    if not allow_scaling and scaleDelta:
        log.warning("Bone %s scale locked" % bone.name)

    scale = (scaleBasis + scaleDelta) if (allow_scaling and with_appearance) else scaleBasis

    scalemat(MScale, scale)
    if normalize:
        normat(MScale, scaleBasis)

    if bone.name in SLVOLBONES:
        MScale, sb = getBoneScaleMatrix(armobj, bone.parent, MScale, normalize=False, verbose=verbose, use_custom=use_custom, with_appearance=with_appearance)

    return MScale, scaleBasis

def get_joint_cache(armobj, include_ik=True, copy=False):
    cache = armobj.get('sl_joints')
    if include_ik or not cache:
        if not copy:
            return cache
        result = {}
        for key,joint in cache.items():
           j= { "key":key,
                "head":Vector(joint['head']),
                "tail":Vector(joint['tail']),
                "hmag":joint['hmag'],
                "tmag":joint['tmag']
              }
           result[key]=j
        return result

    return {key:j for key,j in cache.items() if key[0:2] != 'ik'}


def get_min_joint_offset(jointtype='PIVOT'):
    return MIN_JOINT_OFFSET_RELAXED if jointtype=='PIVOT' else MIN_JOINT_OFFSET

def adjust_hand_structure(arm, scale):

    omode = ensure_mode_is('EDIT')

    bone_names = ["Wrist", ["HandPinky", "HandRing", "HandMiddle", "HandIndex"]]
    bones = arm.data.edit_bones
    for side in ["Left", "Right"]:
        wrist_name = bone_names[0]+side
        wrist = arm.data.edit_bones.get(wrist_name)
        if wrist:
            for finger_id in bone_names[1]:

                finger_name = "%s%d%s" % (finger_id,1,side)
                fingertip_name = "%s%d%s" % (finger_id,3,side)
                structure_name =  "%s%d%s" % (finger_id,0,side)
                finger =  bones.get(finger_name)
                fingertip = bones.get(fingertip_name)
                if finger:
                    structure = bones.get(structure_name)
                    if structure:
                        v = find_hand_structure_head(wrist, finger, fingertip, scale)
                        if v:
                            structure.head = v
                    else:
                        log.warning("Structure bone %s not in Rig" % structure_name)
                else:
                    log.warning("Finger %s not in Rig" % finger_name)
        else:
            log.warning("Wrist %s not in Rig" % wrist_name)
    ensure_mode_is(omode)


def find_hand_structure_head(pwrist, pfinger, pfingertip, scale):
    sphere_co = pwrist.head
    sphere_radius = (pwrist.tail - pwrist.head).magnitude * scale
    line_b = pfingertip.tail
    line_a = pfinger.head - 3*(line_b - pfingertip.head)
    intersections = geometry.intersect_line_sphere(line_a, line_b, sphere_co, sphere_radius)
    return intersections[0] if  intersections[0] else  intersections[1]


def get_highest_materialcount(targets):
    matcount = 0
    extensions = 0

    total_unassigned_polys = 0
    total_unassigned_slots = 0
    total_unassigned_mats  = 0

    for obj in targets:
        if obj.type == "MESH":
            nmat, extensions, unassigned_polys, unassigned_slots, unassigned_mats = material_extensions(obj)
            total_mat = nmat + extensions
            total_unassigned_polys += unassigned_polys
            total_unassigned_slots += unassigned_slots
            total_unassigned_mats  += unassigned_mats

            if matcount < total_mat:
                matcount = nmat

    return matcount, extensions, total_unassigned_polys, total_unassigned_slots, total_unassigned_mats

def material_extensions(obj):
    mat_polycounters = { index : [0,0] for index, slot in enumerate(obj.material_slots) if slot.material}
    unassigned_polys = 0
    unassigned_mats = 0
    unassigned_slots = len([1 for slot in obj.material_slots if not slot.material])

    for i, p in enumerate( obj.data.polygons ):
        index = p.material_index
        data = mat_polycounters.get(index)
        if data:
            data[0] = data[0] + 1
            data[1] = data[1] + p.loop_total
        else:
            unassigned_polys += 1
    extensions = 0

    for data in mat_polycounters.values():

        if data[1] == 0:
            unassigned_mats += 1
            continue #material has no faces assigned

        tricount = int(((data[1] / data[0]) - 2) * data[0] + 0.5)
        data[1] = tricount
        extensions += int(tricount / 21844)

    return len(mat_polycounters), extensions, unassigned_polys, unassigned_slots, unassigned_mats
    
def selection_has_shapekeys(targets):
    for obj in targets:
        if obj.active_shape_key:
            return True
    return False  

def get_armature_from_context(context):
    obj = get_active_object(context)
    if (not obj) or obj.type == 'ARMATURE':
        return obj
    return get_armature(obj)

def get_armature(obj):
    if not obj:
        return None

    if obj.type == "ARMATURE":
        armobj = obj
    else:
        armobj = obj.find_armature()

    return armobj

def get_armatures(selection=None, avastar_only=False):
    all_rigs = not avastar_only
    if selection==None:
        selection=bpy.context.view_layer.objects

    armobjs = set()
    for obj in selection:
        arm = get_armature(obj)
        if arm and (all_rigs or 'avastar' in arm):
            armobjs.add(arm)
    return armobjs

def getSelectedArmsAndObjs(context):
    ob = context.object
    if not ob:
       ob = context.active_object
   
    arms = {}
    objs = []
    
    if ob:
        if ob.type == 'ARMATURE':
            arms[ob.name] = ob
            objs = getCustomChildren(ob, type='MESH')

        elif context.mode=='EDIT_MESH':
            arm = ob.find_armature()
            if arm:
                objs           = [ob]
                arms[arm.name] = arm
        else:

            objs = [ob for ob in context.selected_objects if ob.type=='MESH']
            for ob in objs:
                arm = ob.find_armature()
                if arm:
                    arms[arm.name] = arm
    return list(arms.values()), objs

def getSelectedArms(context):
    ob = context.object
    arms = {}

    if ob:
        if ob.type == 'ARMATURE':
            arms[ob.name] = ob
        elif context.mode=='EDIT_MESH':
            arm = ob.find_armature()
            if arm:
                arms[arm.name] = arm
        else:
            objs = [ob for ob in context.selected_objects if ob.type=='MESH']
            for ob in objs:
                arm = ob.find_armature()
                if arm:
                    arms[arm.name] = arm
    return list(arms.values())

def getSelectedArmsAndAllObjs(context):
    ob = context.object
    arms = {}
    objs = {}
    
    if ob:
        if context.mode=='EDIT_MESH':
            arm = ob.find_armature()
            if arm:
                arms[arm.name] = arm
        else:
            for ob in context.selected_objects:

                arm = get_armature(ob)
                if arm:
                    log.debug("Add Armature %s" % ob.name)
                    arms[arm.name] = arm
                    
    for arm in arms.values():

        for obj in getCustomChildren(arm, type='MESH'):
            log.debug("Add mesh %s" % obj.name)
            objs[obj.name]=obj

    return list(arms.values()), list(objs.values())

def set_armature_layers(armobj, enabled_layers):
    for i in range(0,B_LAYER_COUNT):
        armobj.data.layers[i] = False
    for i in range(0,B_LAYER_COUNT):
        armobj.data.layers[i] = (i in enabled_layers)


def is_avastar(obj):
    arm = get_armature(obj)
    return (not arm is None and ('avastar' in arm or 'Avastar' in arm))


def is_avastar_mesh(obj):
    return 'avastar-mesh' in obj or 'ava-mesh' in obj

def getSelectedCustomMeshes(selection):
    custom_meshes = [obj for obj in selection if obj.type=='MESH' and not 'avastar-mesh' in obj and obj.find_armature() ]
    return custom_meshes

def getCustomChildren(parent, type=None, select=None, visible=None):
    children = getChildren(parent, type=type, select=select, visible=visible)
    custom_children = [obj for obj in children if not 'avastar-mesh' in obj]
    return custom_children

def getAvastarChildren(parent, type=None, select=None, visible=None):
    children = getChildren(parent, type=type, select=select, visible=visible)
    avastar_children = [obj for obj in children if 'avastar-mesh' in obj]
    return avastar_children

def getAvastarChildSet(parent, type=None, select=None, visible=None):
    children = getChildren(parent, type=type, select=select, visible=visible)
    childSet = {obj.name.rsplit('.')[0]:obj for obj in children if 'avastar-mesh' in obj or obj.type=='EMPTY'}
    return childSet

def get_meshes(context, type= None, select=None, visible=None, hidden=None):
    return getMeshes(context.scene.objects, context, type, select, visible, hidden)

def getMeshes(selection, context, type= None, select=None, visible=None, hidden=None):
    meshes = [ob for ob in selection
        if
            (select  == None or object_select_get(ob)     == select)
        and (type    == None or ob.type       == type)
        and (visible == None or object_visible_get(ob, context=context) == visible )]
    return meshes

def get_weight_group_names(selection):
    groups = []
    for ob in selection:
        groups += [group.name for group in ob.vertex_groups]
    return set(groups)

def get_animated_meshes(context, armature, with_avastar=True, only_selected=False, return_names=False, only_visible=True, filter=None, use_object_selector=False):
    system_meshes, animated_meshes = get_animated_elements(context, armature, 
                                 with_avastar=with_avastar,
                                 only_selected=only_selected,
                                 return_names=return_names,
                                 only_visible=only_visible,
                                 filter=filter,
                                 use_object_selector=use_object_selector)
    return animated_meshes

def get_animated_elements(context, armature, with_avastar=True, only_selected=False, return_names=False, only_visible=True, filter=None, use_object_selector=False):

    def is_selected(mesh, use_object_selector):
        return mesh.ObjectProp.is_selected if use_object_selector else mesh.select_get()

    animated_meshes = []
    system_meshes = []

    if only_visible:
        visible_meshes = [ob for ob in context.scene.objects
            if ob.type=='MESH'
            and object_visible_get(ob, context=context)
            ]
    else:
        visible_meshes = [ob for ob in context.scene.objects if ob.type=='MESH']

    for mesh in visible_meshes:
        if with_avastar == False:
            if "avastar-mesh" in mesh:
                continue
        if armature and mesh.parent and mesh.parent.type == 'EMPTY' and mesh.parent.parent == armature:
            system_meshes.append(mesh.name if return_names else mesh)
            if with_avastar == False:
                continue

        if filter:
            id = mesh.get('mesh_id')
            if id and not id in filter:
                continue

        if armature and any([mod for mod in mesh.modifiers if mod.type=='ARMATURE' and mod.object==armature]):
            if is_selected(mesh, use_object_selector) or not only_selected:
                animated_meshes.append(mesh.name if return_names else mesh)


           
    return system_meshes, animated_meshes


def get_animated_mesh_count(context, armature, with_avastar=True, only_selected=False):
    return len(get_animated_meshes(context, armature, with_avastar, only_selected))

def getChildren(ob, type=None, select=None, visible=None, children=None, context=None):
    if context == None:
        context=bpy.context
    if children == None:
        children = []
    if ob:
        for child in ob.children:
            getChildren(child, type=type, select=select, visible=visible, children=children, context=context)
            if (visible==None or object_visible_get(child, context=context)==visible) and (type==None or child.type==type) and (select==None or child.select==select):
                children.append(child)

    return children


def get_select_and_hide(selection, select=None, hide_select=None, hide=None, hide_viewport=None):
    backup = {}
    for obj in selection:
        backup[obj.name] = [object_select_get(obj), object_hide_get(obj), obj.hide_select, obj.hide_viewport]
        if select != None:
            object_select_set(obj, select)
        if hide != None:
            object_hide_set(obj, hide)
        if hide_select != None:
            obj.hide_select = hide_select
        if hide_viewport != None:
            obj.hide_viewport = hide_viewport
    return backup        

def select_hierarchy(obj, select=True, context=None):
    selection = getChildren(obj, context=context)
    selection.append(obj)
    backup = get_select_and_hide(selection, select, False, False)
    return backup

def set_select_and_hide(context, backup):
    for name, state in backup.items():
        ch = context.scene.objects.get(name)
        if ch:
            object_select_set(ch, state[0])
            object_hide_set(ch, state[1])
            ch.hide_select = state[2]
            ch.hide_viewport = state[3]

def restore_hierarchy(context, backup):
    set_select_and_hide(context, backup)

def getAvastarArmaturesInScene(context=None, selection=None):
    armatures = set()
    if selection:
        armatures |= getAvastarArmaturesFromSelection(selection)
    if context:
        armatures |= getAvastarArmaturesFromSelection(context.scene.objects)
    return armatures

def getSkeletonBones(bones):
    master_bones = [b for b in bones if 'm'+b.name not in bones and b.name!='Origin' and not 'Target' in b.name]
    return master_bones

def getSkeletonBoneNames(bnames):
    masterNames = [n for n in bnames if 'm'+n not in bnames and n!='Origin' and not 'Target' in n]
    return masterNames

def getMasterBoneNames(bnames):
    masterNames = [n for n in bnames if n[0] in ['m', 'a'] or n in SLVOLBONES]
    return masterNames

def getSlaveBoneNames(bnames):
    masterNames = [n for n in bnames if not (n[0] in ['m', 'a'] or n in SLVOLBONES) ]
    return masterNames

def getControlledBoneNames(bnames):
    controlNames = [n for n in bnames if n[0] == 'm']
    return controlNames

def add_bone_and_children(bone, bone_set):
    if not bone:
        return

    bone_set.add(bone.name)
    for child in bone.children:
        add_bone_and_children(child, bone_set)

def getAvastarArmaturesFromSelection(selection):
    armatures = [get_armature(obj) for obj in selection if (obj.type == 'ARMATURE' and 'avastar' in obj) or (obj.type=='MESH' and not 'avastar-mesh' in obj and obj.find_armature())]        
    armatures = set([arm for arm in armatures if 'avastar' in arm])
    return armatures

def getVisibleSelectedBoneNames(armobj):
    visible_layers = [i for i, l in enumerate(bpy.data.armatures[armobj.data.name].layers) if l]
    bones = get_modify_bones(armobj)
    selected_bones = [bone.name for bone in bones if bone.select and not bone.hide and any(bone.layers[i] for i in visible_layers)]
    return selected_bones

def getVisibleBoneNames(armobj):
    visible_layers = [i for i, l in enumerate(bpy.data.armatures[armobj.data.name].layers) if l]
    bones = get_modify_bones(armobj)
    visible_bones = [bone.name for bone in bones if not bone.hide and any(bone.layers[i] for i in visible_layers)]
    return visible_bones

def getHiddenBoneNames(armobj):
    visible_layers = [i for i, l in enumerate(bpy.data.armatures[armobj.data.name].layers) if l]
    bones = get_modify_bones(armobj)
    hidden_bones = [bone.name for bone in bones if bone.hide or not (any(bone.layers[i] for i in visible_layers))]
    return hidden_bones
    
def getVisibleSelectedBones(armobj):
    visible_layers = [i for i, l in enumerate(bpy.data.armatures[armobj.data.name].layers) if l]    
    bones = get_modify_bones(armobj)
    selected_bones = [bone for bone in bones if bone.select and not bone.hide and any(bone.layers[i] for i in visible_layers)]
    return selected_bones

def getVisibleBones(armobj):
    visible_layers = [i for i, l in enumerate(bpy.data.armatures[armobj.data.name].layers) if l]
    bones = get_modify_bones(armobj)
    visible_bones = [bone for bone in bones if not bone.hide and any(bone.layers[i] for i in visible_layers)]
    return visible_bones



def getControlBones(armobj, filter=None):
    bones = armobj.pose.bones
    control_bones = {}
    for bone in bones:
        if bone.name[0] == 'm':
            cname = bone.name[1:]
            cbone = bones.get(cname)
            if cbone:
                control_bones[cname] = cbone
        elif filter and filter in bone.name:
            control_bones[bone.name] = bone
    return control_bones



def getControlledBones(armobj, filter=None):
    bones = armobj.pose.bones
    deform_bones = {}
    for bone in bones:
        if bone.name[0] == 'm' or (filter and filter in bone.name):
            deform_bones[bone.name] = bone
    return deform_bones

def getLinkBones(armobj):
    bones = armobj.pose.bones
    link_bones = {}
    for bone in bones:
        if 'Link' in bone.name:
            link_bones[bone.name] = bone
    return link_bones

def get_deform_bone_names(armobj, only=None, visible=False, selected=False):
    return [bone.name for bone in get_deform_bones(armobj, only, visible, selected)]

def get_deform_bones(armobj, only=None, visible=False, selected=False):
    result = get_modify_bones(armobj, only, visible, selected)
    deform_bones = [b for b in result if b.use_deform]
    return deform_bones
    
def get_bone_type(bone, bones):
    name = bone.name
    if name[0]=="m" and name[1:] not in bones:
        return BONE_UNSUPPORTED
    if 'm'+name in armobj.data.edit_bones:
        return BONE_CONTROL
    if name[0] == 'm':
        return BONE_SL
    if name[0] == 'a':
        return BONE_ATTACHMENT
    if dbone_name in SLVOLBONES:
        return BONE_VOLUME
    return 'META' #IKBone or other stuff

def get_modify_bones(armobj, only=None, visible=False, selected=False):
    result = armobj.data.edit_bones if armobj.mode == 'EDIT' else armobj.data.bones
    if only:
        result = [b for b in result if b.name in only]

    if selected:
        result = [b for b in result if b.select]
    
    if visible:
        result = [b for b in result if bone_is_visible(armobj, b)]

    return result

def get_bone_head(armobj, bone):
    return bone.head_local if hasattr(bone, 'head_local') else bone.head

def get_bone_tail(armobj, bone):
    return bone.tail_local if hasattr(bone, 'tail_local') else bone.tail

def get_bone_location(armobj, bname):
    bones = get_modify_bones(armobj)
    bone = bones.get(bname)
    if not bone:
        return None, None
    head = get_bone_head(armobj, bone)
    tail = get_bone_tail(armobj, bone)
    return head, tail

def getCurrentSelection(context, verbose=False):
    avastars      = []  # Avastar Armatures
    armatures     = []  # Referenced Armatures
    attached      = []  # Custom Meshes attached to an armature
    detached      = []  # Custom Meshes not attached to an armature
    weighttargets = []  # Meshes which are allowed to receive weights
    targets       = []  # Meshes
    others        = []  # all other selected
    active = get_active_object(context)
    shapekeys     = False

    def is_an_avastar(obj):
        return is_an_armature(obj) and ('avastar' in obj or 'Avastar' in obj)

    def is_an_armature(obj):
        return obj != None and obj.type=='ARMATURE'

    for obj in [o for o in context.scene.objects if object_select_get(o)]:

        if is_an_avastar(obj):
            avastars.append(obj)
            if verbose: print("Append Avastar %s" % obj.name)
        elif obj.type=='MESH':
            targets.insert(0,obj) if obj==active else targets.append(obj) #active obj first in list
            if verbose: print("Append Target %s" % obj.name)
            armobj = getArmature(obj)
            
            if not ('weight' in obj and obj['weight']=='locked'):
                weighttargets.append(obj)

            if is_an_armature(armobj):
                armatures.append(armobj)
                attached.append(obj)
                if verbose: print("Append related Armature %s:%s" % (obj.name,armobj.name))
                if is_an_avastar(armobj):
                    avastars.append(armobj)
                    if verbose: print("Append Avastar %s" % armobj.name)
            else:
                if verbose: print("Append %s also to Detached" % obj.name)
                detached.append(obj)
                if obj.data.shape_keys:
                    shapekeys = True
        elif obj.type=='ARMATURE':
            if verbose: print("Append selected Armature %s" % obj.name)
            armatures.append(obj)
        else:
            others.append(obj)

    currentSelection = {}
    currentSelection['avastars']      = list(set(avastars))
    currentSelection['armatures']     = list(set(armatures))
    currentSelection['targets']       = targets
    currentSelection['attached']      = attached
    currentSelection['detached']      = detached
    currentSelection['weighttargets'] = weighttargets
    currentSelection['others']        = others
    currentSelection['active']        = active
    currentSelection['shapekeys']     = shapekeys

    return currentSelection
 
def set_mesh_select_mode(select_modes):
    mesh_select_mode = bpy.context.scene.tool_settings.mesh_select_mode
    bpy.context.scene.tool_settings.mesh_select_mode = select_modes
    return mesh_select_mode
        
def set_object_mode(new_mode, def_mode=None, object=None):
    if new_mode is None:
        if def_mode is None:
            return None
        new_mode = def_mode
    
    try:
        if object == None:
            object = get_active_object(bpy.context)
            
        if object == None:
            return None

        if object.mode == new_mode:
            return new_mode
    except:
        pass
        
    original_mode = object.mode
    try:
        mode_set(mode=new_mode)
    except:
        print("Can't set object %s of type %s to mode %s" % (object.name, object.type, new_mode) )
        raise Exception("Wrong mode setting")
    return original_mode

def change_active_object(context, new_active_object, new_mode=None, msg=""):
    if not new_active_object:
        raise Exception("change_active_object: object None is not allowed here")

    old_active_object = get_active_object(context)
    old_active_mode = old_active_object.mode if old_active_object else None

    if old_active_object and old_active_object != new_active_object:
        if old_active_mode != 'OBJECT':
            mode_set(mode='OBJECT')
    
        set_active_object(context, new_active_object)
    
    if new_mode and new_mode != new_active_object.mode:
        mode_set(mode=new_mode)

    return old_active_object, old_active_mode


def set_mode(context, new_mode):
    if not (context and context.object):
        return None
    return mode_set(context=context, mode=new_mode)


def mode_set(context=None, mode=None, toggle=False):
    if context == None and (bpy.context == None or bpy.context.object == None):
        return None

    if mode == None and context == None:
        mode = bpy.context.object.mode
        toggle = True

    old_mode = bpy.context.object.mode if context==None else None
    if mode and old_mode != mode:
        if context == None or context==bpy.context:
            bpy.ops.object.mode_set(mode=mode, toggle=toggle)
        else:
            bpy.ops.object.mode_set(context, mode=mode, toggle=toggle)

    return old_mode


def ensure_mode_is(new_mode, def_mode=None, object=None, toggle_mode=None, context=None):
    if new_mode is None:
        if def_mode is None:
            return None
        new_mode = def_mode

    if context == None:
        context = bpy.context

    active_object = getattr(context, "active_object", None)

    try:
        if object == None and active_object:

            object = active_object

        if object == None:

            return None

        if object.mode == new_mode:
            if toggle_mode != None:
                new_mode = toggle_mode
            else:

                return new_mode
    except:
        print ("Failed to get [%s]" % object )
        return None

    original_mode = object.mode
    if active_object == object:
        set_mode(context, new_mode)
    else:

        set_active_object(context, object)
        mode_set(mode=new_mode)
        set_active_object(context, active_object)



    return original_mode

def update_all_verts(obj, omode=None):
    return not update_only_selected_verts(obj, omode=omode)

def update_only_selected_verts(obj, omode=None):
    if omode is None:
        omode = obj.mode

    if omode == 'EDIT':
        only_selected = True
    else:
        only_selected = omode=='WEIGHT_PAINT' and (obj.data.use_paint_mask_vertex or obj.data.use_paint_mask)


    return only_selected


def select_all_doubles(me, dist=0.0001):
    
    bpy.ops.mesh.select_all(action='DESELECT')
    bm  = bmesh.from_edit_mesh(me)
    map = bmesh.ops.find_doubles(bm,verts=bm.verts, dist=dist)['targetmap']
    count = 0
    
    try:
        bm.verts.ensure_lookup_table()
    except:
        pass
        
    for key in map:
        bm.verts[key.index].select=True
        bm.verts[map[key].index].select=True
        count +=1

    bmesh.update_edit_mesh(me)
    return count
    
def select_edges(me, edges, seam=None, select=None):
    bm  = bmesh.from_edit_mesh(me)
    
    try:
        bm.edges.ensure_lookup_table()
    except:
        pass
        
    for i in edges:
        if not seam is None:   bm.edges[i].seam   = seam
        if not select is None: bm.edges[i].select = select
    bmesh.update_edit_mesh(me)

def get_vertex_coordinates(ob):    
    me = ob.data
    vcount = len(me.vertices)
    coords  = [0]*vcount*3

    for index in range(vcount):
        co = me.vertices[index].co
        coords[3*index+0] = co[0]
        coords[3*index+1] = co[1]
        coords[3*index+2] = co[2]
   
    return coords
    
def get_weights(ob, vgroup):
    weights = []
    for index, vert in enumerate(ob.data.vertices):
        for group in vert.groups:
            if group.group == vgroup.index:
                weights.append([index, group.weight])
                break
    return weights

def get_weight_set(ob, vgroup):
    weights = {}
    for index, vert in enumerate(ob.data.vertices):
        for group in vert.groups:
            if group.group == vgroup.index:
                weights[index] = group.weight
                break
    return weights

def merge_weights(ob, source_group, target_group):
    source_weights = get_weight_set(ob, source_group)
    target_weights = get_weight_set(ob, target_group)

    for key, val in source_weights.items():
        if key in target_weights:
            target_weights[key] = target_weights[key] + val
        else:
            target_weights[key] = val

    for key, val in target_weights.items():
        target_group.add([key], min(val,1), 'REPLACE')


def rescale(value1, vmin1, vmax1, vmin2, vmax2):
    '''
    rescale value1 from range vmin1-vmax1 to vmin2-vmax2
    '''
    range1 = float(vmax1-vmin1)
    range2 = float(vmax2-vmin2)
    value2 = (value1-vmin1)*range2/range1+vmin2

    value2 = max(min(value2, vmax2), vmin2)
    return value2
    

def clamp_range(smallest,val,biggest):
    return max(min(val, biggest), smallest)


def s2bo(p):

    return Vector((p[1],p[0],p[2]))

def s2b(p):
    return Vector((p[1],-p[0],p[2]))
    
def b2s(p):
    return Vector((-p[1],p[0],p[2]))


def bone_category_keys(boneset, category_name):
    subset_keys = [ key for key in boneset.keys() if key.startswith(category_name) ]
    return subset_keys


def get_addon_version():
    version = "%s.%s.%s" % (bl_info['version'])
    return version

def tag_addon_revision(obj):
    revision = get_addon_revision()
    obj['version'] = revision

def get_addon_revision():
    V=Vector(bl_info['version'])
    return get_version_number(V)

def get_version_number(v):
    V=Vector(v)
    V[0] = int(V[0]) * 10000
    V[1] = int(V[1]) * 100
    V[2] = int(V[2]) * 1
    return int(sum(V))


def reset_dirty_mesh(context, obj):
    if CHECKSUM in obj:
        del obj[CHECKSUM]
    if DIRTY_MESH in obj:
        del obj[DIRTY_MESH]
        stats = create_mesh_stats(context.scene, obj)
        obj[MESH_STATS] = stats

    object_rev = obj.get('version', 0)
    if object_rev < 20420:
        tag_addon_revision(obj)

def create_mesh_stats(scene, meshobj):

    if meshobj.mode == 'EDIT':
        meshobj.update_from_editmode()

    stats = {}

    arm = meshobj.find_armature()
    deforming_bones = []
    discarded_bones = []

    if arm and len(meshobj.vertex_groups) > 0 :
        weighted_bones = [v for v in meshobj.vertex_groups if v.name in arm.data.bones]
        for bone in weighted_bones:
            wbl = "%s : %s" % (meshobj.name, bone.name)
            if arm.data.bones[bone.name].use_deform:
                deforming_bones.append(wbl)
            else:
                discarded_bones.append(wbl)

    stats[STATS_DEFORMING_BONES] = deforming_bones
    stats[STATS_DISCARDED_BONES] = discarded_bones
    stats[STATS_BONE_COUNT] = len ( deforming_bones )

    me = meshobj.to_mesh(preserve_all_data_layers=True)
    stats[STATS_VERTEX_COUNT] = len(me.vertices)
    stats[STATS_LOOP_COUNT] = len(me.loops)
    stats[STATS_FACE_COUNT] = len(me.polygons)
    loops    = len(me.loops)
    flat_face_normals   = [poly.loop_total for poly in me.polygons if not poly.use_smooth]
    smooth_face_normals = [poly.loop_total for poly in me.polygons if poly.use_smooth]
    stats[STATS_NORMAL_COUNT] =  max(sum(flat_face_normals),stats[STATS_VERTEX_COUNT])

    uv_count = None
    uv_active=me.uv_layers.active
    if uv_active:
        uv_count = get_uv_vert_count(me)



    if uv_count is None:
        uv_count = 0
    stats[STATS_UV_COUNT] = uv_count

    if stats[STATS_FACE_COUNT] > 0:
        stats[STATS_TRI_COUNT] = int(((loops / stats[STATS_FACE_COUNT]) - 2) * stats[STATS_FACE_COUNT] + 0.5)
    else:
        stats[STATS_TRI_COUNT] = get_tri_count(stats[STATS_FACE_COUNT], loops)

    matcount, extensions, total_unassigned_polys, total_unassigned_slots, total_unassigned_mats = get_highest_materialcount([meshobj])
    stats[STATS_MAT_COUNT] = matcount
    stats[STATS_EXTENDED_MAT_COUNT] = extensions
    stats[STATS_UNASSIGNED_POLYS] = total_unassigned_polys
    stats[STATS_UNASSIGNED_SLOTS] = total_unassigned_slots
    stats[STATS_UNASSIGNED_MATS] = total_unassigned_mats

    radius, vc_lowest, vc_low, vc_mid, vc_high = get_approximate_lods(
        meshobj,
        stats[STATS_VERTEX_COUNT],
        stats[STATS_NORMAL_COUNT],
        stats[STATS_UV_COUNT],
        stats[STATS_TRI_COUNT])

    stats[STATS_RADIUS] = radius
    stats[STATS_VC_LOWEST] = vc_lowest
    stats[STATS_VC_LOW] = vc_low
    stats[STATS_VC_MID] = vc_mid
    stats[STATS_VC_HIGH] = vc_high

    return stats

def get_collapse_icon(state):
    return "TRIA_DOWN" if state else "TRIA_RIGHT"


progress = 0
def progress_begin(min=0,max=9999):
    global progress
    try:
        bpy.context.window_manager.progress_begin(min,max)
        progress = 0
    except:
        pass    
        
def progress_update(val, absolute=True):
    global progress
    if absolute:
        progress = val
    else:
        progress += val
        
    try:
        bpy.context.window_manager.progress_update(progress)
    except:
        pass    

def progress_end():
    try:
        bpy.context.window_manager.progress_end()
    except:
        pass






def fast_get_verts(verts):
    co = [0.0]*3*len(verts)
    verts.foreach_get('co',co)
    return co






def fast_set_verts(me, co):
    verts = me.vertices
    verts.foreach_set('co', co)






def getMesh(context,
    obj,
    apply_modifier_stack,
    apply_mesh_rotscale = True,
    apply_armature_scale= False,
    apply_armature=False,
    msg="",
    shape_data=None,
    sl_rotation=True):

    evaluated_object, evaluated_data = getEvaluatedMesh(context,
    obj,
    apply_modifier_stack,
    apply_mesh_rotscale = apply_mesh_rotscale,
    apply_armature_scale= apply_armature_scale,
    apply_armature=apply_armature,
    msg=msg,
    shape_data=None,
    sl_rotation=sl_rotation)

    return evaluated_data


def getEvaluatedMesh(context,
    obj,
    apply_modifier_stack,
    apply_mesh_rotscale = True,
    apply_armature_scale= False,
    apply_armature=False,
    msg="",
    shape_data=None,
    sl_rotation=True):





    #




    #




    log.debug("get Mesh: + begin ++++++++++++++++++++++++++++++++++++++++++++")
    log.debug("get Mesh: Get Mesh for %s" % (obj.name) )

    disabled_modifiers, armature_modifiers = prepare_modifiers(obj, apply_modifier_stack, apply_armature)

    depsgraph = context.evaluated_depsgraph_get()
    evaluated_object = obj.evaluated_get(depsgraph)
    evaluated_data = evaluated_object.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    mdc= evaluated_data.copy()
    evaluated_object.to_mesh_clear()
    evaluated_data = mdc

    if shape_data:

        fast_set_verts(evaluated_data, shape_data)


    for m in disabled_modifiers:

        if apply_modifier_stack:
            m.show_viewport = True

    for val in armature_modifiers:
        m = val[0]
        m.use_deform_preserve_volume = val[1]

    M_arm = Matrix()
    if apply_armature_scale:
        armobj = getArmature(evaluated_object)
        if armobj:
            M_arm = armobj.matrix_local.copy()
            M_arm[0][3] = M_arm[1][3] = M_arm[2][3] = 0

    M_obj = Matrix()
    if apply_mesh_rotscale:
        M_obj = evaluated_object.matrix_local.copy()
        M_obj[0][3] = M_obj[1][3] = M_obj[2][3] = 0

    M = mulmat(M_arm, M_obj)




    if sl_rotation:
        evaluated_data.transform(mulmat(Rz90I, M))

    evaluated_data.calc_normals()
    log.info("get Mesh: Calculating normals here will destroy custom normals!" )
    log.debug("get Mesh: - end ----------------------------------------------")

    return evaluated_object, evaluated_data


def prepare_modifiers(obj, apply_modifier_stack, apply_armature):

    disabled_modifiers = []
    armature_modifiers = []

    for m in obj.modifiers:
        log.debug("get Mesh: Examine modifier %s %s %s" % (m.name, m.show_viewport, m.show_render))
        if not apply_modifier_stack:

            if m.show_viewport == True:
                disabled_modifiers.append(m)
                m.show_viewport=False
                log.debug("get Mesh: Disabled PREVIEW modifier %s" % m.name)
        elif m.type == 'ARMATURE':
            if apply_armature:
                armature_modifiers.append([m,m.use_deform_preserve_volume])

                log.debug("get Mesh: Apply ARMATURE modifier %s" % m.name)
            else:

                if apply_modifier_stack:
                    m.show_viewport=False
                    disabled_modifiers.append(m)
                    log.debug("get Mesh: Disabled modifier %s" % (m.name))
                else:
                    log.debug("get Mesh: Enabled modifier %s" % (m.name))
        else:
            log.debug("get Mesh: Use modifier %s for viewport:%s render:%s" % \
                     (m.name, m.show_viewport, m.show_render))

    return disabled_modifiers, armature_modifiers



def get_uv_vert_count(me):
    edge_count = len([e.use_seam for e in me.edges if e.use_seam])
    return edge_count + len(me.vertices)
    

def get_nearest_vertex_normal(source_verts, target_vert):
    solution = None
    for source_vert in source_verts:
        dist = (target_vert.co - source_vert.co).magnitude
        if dist < 0.001:
            if not solution or solution[0] > dist :
                solution = [dist, source_vert.normal]
    return solution[1] if solution else None

def get_boundary_verts(bmsrc, context, obj, apply_modifier_stack=False, apply_mesh_rotscale = True):
    evaluated_object, evaluated_data = getEvaluatedMesh(context, obj, apply_modifier_stack, apply_mesh_rotscale)
    bmsrc.from_mesh(evaluated_data)
    evaluated_object.to_mesh_clear()
    
    invalidverts = []
    boundaryvert = False
    for edge in bmsrc.edges:

        if len(edge.link_faces) > 1:
            for vert in edge.verts:
                for edge in vert.link_edges:
                    if len(edge.link_faces) < 2:
                        boundaryvert = True
                if boundaryvert:
                    boundaryvert = False
                    continue
                else:
                    invalidverts.append(vert)
                    
    for vert in invalidverts:
        if vert.is_valid:
            bmsrc.verts.remove(vert)
            
    return bmsrc.verts

def select_boundary_verts(bmsrc, context, obj, apply_mesh_rotscale = True):
    bmsrc.from_mesh(obj.data)
    bmsrc.select_mode = {'VERT'}

    invalidverts = []
    for edge in bmsrc.edges:

        if len(edge.link_faces) > 1:
            for vert in edge.verts:
                boundaryvert = False
                for edge in vert.link_edges:
                    if len(edge.link_faces) < 2:
                        boundaryvert = True
                vert.select = boundaryvert    


def get_adjusted_vertex_normals(context, sources, apply_modifier_stack, apply_mesh_rotscale):
    bm_source  = bmesh.new()
    bm_target  = bmesh.new()
    
    targets = sources.copy()
    source_normals    = {}
    
    for obj in sources:
        try:
            bm_target.verts.ensure_lookup_table()
            bm_source.verts.ensure_lookup_table()
        except:
            pass
            
        target_verts = get_boundary_verts(bm_target, context, obj, apply_modifier_stack, apply_mesh_rotscale)
        targets.remove(obj)
        for otherobj in sources:
            if otherobj == obj:
                continue
            source_verts = get_boundary_verts(bm_source, context, otherobj, apply_modifier_stack, apply_mesh_rotscale)
            if not obj.name in source_normals:
                source_normals[obj.name]={}
            normals = source_normals[obj.name]
            fixcount = 0

            log.info("Weld %s(%d verts) with %s(%d verts)" % (obj.name, len(target_verts), otherobj.name, len(source_verts)) )

            for vert in target_verts:
                near = get_nearest_vertex_normal(source_verts, vert)
                if near:
                    vert.normal = (vert.normal + near) * 0.5
                    vert.normal.normalize()
                    normals[vert.index] = vert.normal.copy()
                    fixcount +=1
                    
            if fixcount > 0:
                print("merged %d normals from %s with target %s" % (fixcount, otherobj.name, obj.name) )
            bm_source.clear()
        bm_target.clear()
        
    bm_source.free()        
    bm_target.free()
    return source_normals
        

ABERRANT_PLURAL_MAP = {
    'appendix': 'appendices',
    'child': 'children',
    'criterion': 'criteria',
    'focus': 'foci',
    'index': 'indices',
    'knife': 'knives',
    'leaf': 'leaves',
    'mouse': 'mice',
    'self': 'selves'
    }

VOWELS = set('aeiou')

def pluralize(singular, count=2, plural=None):
    '''
    singular : singular form of word
    count    : if count > 1 return plural form of word 
               otherwise returns word as is
    plural   : for irregular words
    '''

    if not singular or count < 2:
        return singular
    if plural:
        return plural

    plural = ABERRANT_PLURAL_MAP.get(singular)
    if plural:
        return plural
        
    root = singular
    try:
        if singular[-1] == 'y' and singular[-2] not in VOWELS:
            root = singular[:-1]
            suffix = 'ies'
        elif singular[-1] == 's':
            if singular[-2] in VOWELS:
                if singular[-3:] == 'ius':
                    root = singular[:-2]
                    suffix = 'i'
                else:
                    root = singular[:-1]
                    suffix = 'ses'
            else:
                suffix = 'es'
        elif singular[-2:] in ('ch', 'sh'):
            suffix = 'es'
        else:
            suffix = 's'
    except IndexError:
        suffix = 's'
    plural = root + suffix
    return plural

class PVector(Vector):
    def __init__(self, val, prec=4):
        self.prec = prec

    def __str__(self):
        return 'Vector(('+', '.join([str(round(self[n], self.prec)) for n in range(0,3)])+'))'

class V(Vector):
    pass

class V_ORG(namedtuple('V', 'x, y, z')):
    '''
    Simple vector class
    '''
    
    def __new__(_cls, *args):
        'Create new instance of Q(x, y, z)'
        if len(args)==1:
            x,y,z = args[0]
        else:
            x,y,z = args
        return super().__new__(_cls, x, y, z) 
    def __add__(self, other):
        if type(other) == V:
            return V( *(s+o for s,o in zip(self, other)) )
        try:
            f = float(other)
        except:
            return NotImplemented
        return V(self.x+f, self.y+f, self.z+f)

    __radd__ = __add__

    def __neg__(self):
        return V(-self.x, -self.y, -self.z)
 
    def __sub__(self, other):
        if type(other) == V:
            return V( *(s-o for s,o in zip(self, other)) )
        try:
            f = float(other)
        except:
            return NotImplemented
        return V(self.x-f, self.y-f, self.z-f)

    def __mul__(self, other):
        try:
            f = float(other)
        except:
            return NotImplemented
        return V(self.x * f, self.y * f, self.z * f)
    
    def __truediv__(self, other):
        try:
            f = float(other)
        except:
            return NotImplemented
        return V(self.x / f, self.y / f, self.z / f)
    
    def copy(self):
        return V(self.x, self.y, self.z)
        
    def magnitude(self):
        v = Vector((self.x, self.y, self.z))
        return v.magnitude
    
    __rmul__ = __mul__
    

def findAvastarMeshes(parent, meshobjs=None, armature_version=None):



    if meshobjs == None:
        meshobjs = {}


    if armature_version == None:
        try:
            armature_version = parent['avastar']
        except:
            armature_version = 0

        
    for child in parent.children:
        findAvastarMeshes(child, meshobjs, armature_version)
        if child.type=='MESH':
            name = child.name.split(".")[0] 
            if name in ['headMesh','hairMesh','upperBodyMesh','lowerBodyMesh','skirtMesh','eyelashMesh','eyeBallLeftMesh','eyeBallRightMesh']:
                if armature_version == 2 and not 'avastar-mesh' in child:
                    continue
                    
                if name in meshobjs:



                    try:
                        if len(child.data.shape_keys.key_blocks) > 1:
                            meshobjs[name] = child
                    except AttributeError:

                        pass
                else:
                    meshobjs[name] = child

    return meshobjs



def ensure_shadow_exists(key, arm, obj, me = None):
    context = bpy.context
    shadow_name = 'avastar_reference_' + key
    try:
        shadow = bpy.data.objects[shadow_name]
        if me:
            oldme, shadow.data = shadow.data, me
            bpy.data.meshes.remove(oldme)
    except:
        print("Create missing shadow for", obj)
        shadow             = visualCopyMesh(context, obj)
        shadow.name        = shadow_name







        object_hide_set(shadow, False)
        object_select_set(shadow, False)
        shadow.hide_select = False
        shadow.hide_render = True
        shadow.parent      = arm


        if 'avastar-mesh' in shadow: del shadow['avastar-mesh'] 
        if 'mesh_id'      in shadow: del shadow['mesh_id']      

        unlink_object(context, shadow)

    if me:
        me.name = shadow_name

        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(shadow.data)
        bm.clear()

        shadow.data.name = me.name
        print("Updated Shadow object key:[%s] name:[%s:%s]" % (key, shadow.name, shadow.data.name))

    return shadow


def guessArmature(context):

    arm = getArmature(context.object)
    if arm:
        return arm

    selected_armatures = [o for o in bpy.data.objects if object_select_get(o) and o.type=='ARMATURE']
    if len(selected_armatures) != 1:
        return None # Can not guess which armature shall be used for binding

    return selected_armatures[0]


def getArmature(obj):



    if obj.type == 'ARMATURE':
        return obj

    for mod in obj.modifiers:
        if mod.type=="ARMATURE":
            return mod.object


    if obj.parent_type == 'ARMATURE':
        return obj.parent

    return None


def create_armature_modifier(target, armobj, name=None, preserve_volume=False):
    if not name:
        name=armobj.name
    mod = target.modifiers.new(name, 'ARMATURE')
    mod.use_vertex_groups  = True
    mod.use_bone_envelopes = False
    mod.show_in_editmode = True
    mod.show_on_cage = True
    mod.object = armobj
    mod.use_deform_preserve_volume = preserve_volume
    return mod


def flipName(name):

    if "Left" in name:
        fname = name.replace("Left","Right")
    elif "Right" in name:
        fname = name.replace("Right","Left")
    elif "left" in name:
        fname = name.replace("left","right")
    elif "right" in name:
        fname = name.replace("right","left")
    elif name.endswith(".R") or name.endswith("_R"):
        fname = name[0:-1]+"L"
    elif name.endswith(".L") or name.endswith("_L"):
        fname = name[0:-1]+"R"
    elif name.startswith("l"):
        fname = "r" + name[1:]
    elif name.startswith("r"):
        fname = "l" + name[1:]
    else:
        fname = ""

    return fname
    
class BindBone:

    def __init__(self,bone):

        self.name      = bone.name
        self.head      = bone.head
        self.tail      = bone.tail
        self.parent    = bone.parent.name if bone.parent else None

        self.matrix    = bone.matrix_basis.copy()
        
        if bone.name=="CollarRight":
            print("matrix:", self.matrix)
        



class AlterToRestPose(bpy.types.Operator):
    bl_idname = "avastar.alter_to_reference_pose"
    bl_label = "Alter To Reference Pose"
    bl_description ="Alter pose to Reference Pose"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(self, context):
        obj = context.active_object
        if obj:
            arm = get_armature(obj)
            return arm and arm.type=='ARMATURE'
        return False

    @classmethod
    def resetBinding(self, arm):
        reference = ArmatureBinding.get_binding(arm)
        if not reference:
            print("Can not alter to rest pose. No reference pose found")
            return False
        
        pbones = arm.pose.bones
        bbones = reference.bbones
            
        omode = ensure_mode_is('POSE', object=arm)
        for key in bbones:
            rbone  = bbones[key]
            pbones[key].matrix_basis = rbone.matrix.inverted()

        ensure_mode_is(omode, object=arm)
        return True

    def execute(self, context):
        obj = context.active_object
        arm = get_armature(obj)
        if AlterToRestPose.resetBinding(arm):
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class ArmatureBinding:

    armature_bindings={}
    
    def __init__(self, arm, reference):
        self.reference = reference
        ArmatureBinding.armature_bindings[arm.name]=self

    @staticmethod
    def get_binding(arm):
        ref = ArmatureBinding.armature_bindings[arm.name].reference if arm.name in ArmatureBinding.armature_bindings else None
        return ref

class BindSkeleton:

    def __init__(self, arm):
        self.bbones = {}
        omode = ensure_mode_is('POSE', object=arm)
        for bone in arm.pose.bones:
           bbone = BindBone(bone)
           self.bbones[bbone.name] = bbone

        ensure_mode_is(omode, object=arm)


        
class BindToCurrentPose(bpy.types.Operator):
    bl_idname = "avastar.bind_to_pose"
    bl_label = "Bind To Pose"
    bl_description ="Bind to current pose"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        if context.active_object:
            active = context.active_object
            return active and active.type=='ARMATURE'
        return False
        
    @classmethod
    def createBinding(self,arm, context):

        omode = ensure_mode_is('POSE')
        arm.data.pose_position='REST'
        enforce_armature_update(context.scene, arm)
        reference = BindSkeleton(arm)
        arm.data.pose_position='POSE'
        bpy.ops.pose.armature_apply()

        ArmatureBinding(arm, reference)
        ensure_mode_is(omode)
        print("Done")

    def execute(self, context):
        arm = context.active_object
        BindToCurrentPose.createBinding(arm, context)
        return {'FINISHED'}


def get_mirror_name(name):

    if name.find("Left") > -1:
        mirrorName = name.replace("Left", "Right")
    elif name.find("Right") > -1:
        mirrorName = name.replace("Right", "Left")
    elif name.find("RIGHT") > -1:
        mirrorName = name.replace("RIGHT", "LEFT")
    elif name.find("LEFT") > -1:
        mirrorName = name.replace("LEFT", "RIGHT")

    elif name[0:2] == "R_":
        mirrorName = "L_" + name[2:]
    elif name[0:2] == "L_":
        mirrorName = "R_" + name[2:]
    elif name[0:2] == "r_":
        mirrorName = "l_" + name[2:]
    elif name[0:2] == "l_":
        mirrorName = "r_" + name[2:]
    else:
        mirrorName = None

    return mirrorName


RF_LOWEST = 0.03
RF_LOW    = 0.06
RF_MID    = 0.24

MIN_AREA  = 1
MAX_AREA  = 102932

MAX_DISTANCE = 512


DISCOUNT      = 10
MIN_SIZE      = 2
FAKTOR        = 0.046

def limit_vertex_count(vertex_count, triangle_count):
    while vertex_count > triangle_count:
        vertex_count /= 2
    return vertex_count

def get_approximate_lods(ob, vertex_count, normals_count, uv_count, triangle_count):
    vcount = max(normals_count,uv_count)
    extra_normals = vcount - vertex_count
    rx = ob.dimensions[0] * ob.scale[0] / 2
    ry = ob.dimensions[1] * ob.scale[1] / 2
    rz = ob.dimensions[2] * ob.scale[2] / 2
    radius = max(rx,ry,rz)# sqrt(rx*rx + ry*ry + rz*rz) 
    
    if triangle_count == 0:
        correction=1
    else:
        correction = 4-(vcount*vcount)/(4*triangle_count*triangle_count)
    lowest_lod = max(limit_vertex_count(vcount/(6*correction), triangle_count/32) + extra_normals/42, MIN_SIZE)
    low_lod    = max(limit_vertex_count(vcount/(3*correction), triangle_count/16) + extra_normals/24, MIN_SIZE)
    medium_lod = max(limit_vertex_count(vcount/correction    , triangle_count/4)  + extra_normals/6 , MIN_SIZE)
    high_lod   = vcount
    
    return radius, lowest_lod, low_lod, medium_lod, high_lod

def get_streaming_costs(radius, vc_lowest, vc_low, vc_mid, vc_high, triangle_count):




    dlowest = min(radius/RF_LOWEST, MAX_DISTANCE)
    dlow    = min(radius/RF_LOW   , MAX_DISTANCE)
    dmid    = min(radius/RF_MID   , MAX_DISTANCE)





    
    trilowest = max(vc_lowest - DISCOUNT,MIN_SIZE)
    trilow    = max(vc_low    - DISCOUNT,MIN_SIZE)
    trimid    = max(vc_mid    - DISCOUNT,MIN_SIZE)
    trihigh   = max(vc_high   - DISCOUNT,MIN_SIZE)

    ahigh   = min(pi * dmid*dmid,       MAX_AREA)
    amid    = min(pi * dlow*dlow,       MAX_AREA)
    alow    = min(pi * dlowest*dlowest, MAX_AREA)
    alowest = MAX_AREA
    
    alowest -= alow
    alow    -= amid
    amid    -= ahigh

    atot = ahigh + amid + alow + alowest
    
    wahigh   = ahigh/atot
    wamid    = amid/atot
    walow    = alow/atot
    walowest = alowest/atot

    wavg = trihigh   * wahigh + \
           trimid    * wamid  + \
           trilow    * walow  + \
           trilowest * walowest
           
    cost = (wavg * FAKTOR)
    return cost





if __name__ == '__main__':
    pass

def unparent_selection(context, selection, type='CLEAR_KEEP_TRANSFORM', clear_armature=False):
    bpy.ops.object.select_all(action='DESELECT')
    if clear_armature:
        for ob in selection:
            for mod in [mod for mod in ob.modifiers if mod.type=='ARMATURE']:
                 ob.modifiers.remove(mod)
    set_select(selection)
    bpy.ops.object.parent_clear(type=type)


def parent_selection(context, tgt, selection, keep_transform=False):
    bpy.ops.object.select_all(action='DESELECT')
    set_select(selection)
    object_select_set(tgt, True)
    set_active_object(context, tgt)
    
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=keep_transform)

def get_selection_recursive(selection, include=True):
    result=list(selection) if include else []
    for ob in selection:
        result.extend(get_selection_recursive(ob.children, include=True))
    return result

def get_select(context):
    return get_select_from_scene(context.scene)

def get_select_from_scene(scene):
    return [o for o in scene.objects if object_select_get(o)]

def set_select(selection, reset=False):
    if reset:
        bpy.ops.object.select_all(action='DESELECT')
    
    for ob in selection:
        object_select_set(ob, True)

def move_children(context, src, tgt, root, ignore):
    sources=[]
    for obj in src.children:

        if ignore and ignore in obj:
            continue
        if obj.parent == src:
            sources.append(obj)

    unparent_selection(context, sources)

    for obj in sources:
        obj.parent=tgt
        for mod in [mod for mod in obj.modifiers if mod.type=='ARMATURE']:
            mod.object=root
        sources.extend(move_children(context, obj, obj, tgt, ignore))            


    return sources

def reparent_selection(context, src, tgt, ignore):
    sources=[]
    for obj in src.children:

        if ignore and ignore in obj:
            continue

        sources.append(obj)

    unparent_selection(context, sources)
    set_active_object(context, tgt)
    bpy.ops.object.parent_set(type='OBJECT')

    for obj in sources:
        for mod in [mod for mod in obj.modifiers if mod.type=='ARMATURE']:
            if mod.object == src:
               mod.object = tgt


    return sources

def fix_modifier_order(context, ob):
    mod_arm_index = -1
    for index, mod in enumerate(ob.modifiers):
        if mod.type=='ARMATURE':
            mod_arm_index = index
            print("fix_modifier_order: %s has armature modifier %s at position %d" % (ob.name, mod.name, index))

    mod_data_index = -1
    mod_data_name  = None
    for index, mod in enumerate(ob.modifiers):
        if mod.type=='DATA_TRANSFER':
            print("fix_modifier_order: %s has datatransfer modifier %s at position %d" % (ob.name, mod.name, index))
            mod_data_index = index
            mod_data_name = mod.name
            break

    if mod_arm_index > mod_data_index > -1:
       print("Need to move weld higher up by",  mod_arm_index - mod_data_index, "slots")

       active = get_active_object(context)
       set_active_object(context, ob)
       while mod_arm_index > mod_data_index:
          mod_data_index +=1
          bpy.ops.object.modifier_move_down(modifier=mod_data_name)
       set_active_object(context, active)

def copy_object_attributes(context, src_armature, tgt_armature, tgt, src):
    print("copy_object_attributes...")
    object_select_set(tgt, object_select_get(src))
    object_hide_set(tgt, object_hide_get(src))


    if tgt.type=='MESH':
        tgt.data.materials.clear() # ensure the target material slots are clean
        if src.type=='MESH':
            for mat in src.data.materials:
                tgt.data.materials.append(mat)

            mod_arm_index = -1
            for index, mod in enumerate([mod for mod in tgt.modifiers if mod.type=='ARMATURE']):
                print("mod   orig", mod.type, mod.name, mod.object.name)
                if mod.object==src_armature:
                    print("mod change", mod.type, mod.name, mod.object.name)
                    mod.object = tgt_armature

def copy_attributes(context, src_armature, tgt_armature, sources, target_set):

    for src in sources:
        tgt  = target_set.get(src.name.rsplit('.')[0], None)

        if tgt:
            copy_object_attributes(context, src_armature, tgt_armature, tgt, src)



def remove_selection(selected, src):
    for obj in selected:
        if obj.parent == src or any([mod for mod in obj.modifiers if mod.type=='ARMATURE' and mod.object == src]):
            remove_children(obj, context)
            remove_object(context, obj)            

def remove_object(context, obj, do_unlink=True, recursive=False):

        if recursive and obj.children:
            for child in obj.children:
                remove_object(context, child, do_unlink=do_unlink, recursive=recursive)


        bpy.data.objects.remove(obj, do_unlink=do_unlink)


def remove_text(text, do_unlink=True):
        bpy.data.texts.remove(text, do_unlink=do_unlink)

def remove_action(action, do_unlink=True):
        bpy.data.actions.remove(action, do_unlink=do_unlink)


def remove_children(src, context):
    for obj in src.children:
        name = obj.name
        remove_children(obj, context)
        try:
            remove_object(context, obj)
            log.warning("Removed child %s from its parent %s" % (name, src.name))
        except:
            log.error("Removing of child %s from its parent %s failed" % (name, src.name))


def setSelectOption(armobj, bone_names, exclusive=True):
    backup = {}
    for bone in armobj.data.bones:
        if bone.name in bone_names:
            if not bone.select:
                backup[bone.name] = bone.select
                bone.select = True
        else:
            if exclusive and bone.select:
                backup[bone.name] = bone.select
                bone.select = False
    return backup
        
def setDeformOption(armobj, bone_names, exclusive=True):
    backup = {}
    bones = get_modify_bones(armobj)
    for bone in bones:
        if bone.name in bone_names:
            if not bone.use_deform:
                backup[bone.name] = bone.use_deform
                bone.use_deform = True
        else:
            if exclusive and bone.use_deform:
                backup[bone.name] = bone.use_deform
                bone.use_deform = False
    return backup
    
def restoreDeformOption(armobj, backup):
    bones = get_modify_bones(armobj)
    for key, val in backup.items():
        bones[key].use_deform = val
        
def restoreSelectOption(armobj, backup):
    bones = get_modify_bones(armobj)
    for key, val in backup.items():
        bones[key].select = val
        

def remove_weights_from_deform_bones(obj, use_all_verts=False):
    arm = get_armature(obj)
    if not arm:
        return 0

    weight_group_names = [b.name for b in arm.data.bones if b.use_deform]
    return remove_weights_from_selected_groups(obj, weight_group_names, use_all_verts=use_all_verts)


def remove_weights_from_selected_groups(obj, weight_group_names, use_all_verts=False):
    active = get_active_object(bpy.context)
    set_active_object(bpy.context, obj)
    original_mode = ensure_mode_is("EDIT") 
    removed_groups_counter=0
    for gname in [ name for name in weight_group_names if name in obj.vertex_groups]:
        bpy.ops.object.vertex_group_set_active(group=gname) 
        bpy.ops.object.vertex_group_remove_from(use_all_verts=use_all_verts)
        print("Removed selected from vgroup %s" % gname)
        removed_groups_counter += 1
    ensure_mode_is(original_mode)
    set_active_object(bpy.context, active)
    return removed_groups_counter
    
def remove_weights_from_all_groups(obj):
    active = get_active_object(bpy.context)
    set_active_object(bpy.context, obj)
    original_mode = ensure_mode_is("EDIT")
    bpy.ops.object.vertex_group_set_active(group=gname) 
    bpy.ops.object.vertex_group_remove_from(all=True)
    log.warning("|  Removed selected verts from all vgroups in Mesh %s" % obj.name)
    ensure_mode_is(original_mode)
    set_active_object(bpy.context, active)

def removeWeightGroups(obj, weight_group_names): 
    for gname in [ name for name in weight_group_names if name in obj.vertex_groups]:
        vgroup = obj.vertex_groups.get(gname)
        if vgroup:

            obj.vertex_groups.remove(vgroup)
        else:
            log.warning("Tried to remove not existing vertex group %s" % gname)


def removeEmptyWeightGroups(obj):

    def get_empty_groups(bm, obj):
        empty_groups = []
        dvert_lay = bm.verts.layers.deform.active
        for g in obj.vertex_groups:
            if not any(v for v in bm.verts if obj.vertex_groups[g.name].index in v[dvert_lay]):
                empty_groups.append(g.name)
        return empty_groups

    if obj and obj.type=='MESH':
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        try:
            bm.verts.ensure_lookup_table()
        except:
            pass
            
        dvert_lay = bm.verts.layers.deform.active
        empty_groups = get_empty_groups(bm, obj)
        if len(empty_groups) > 0:
            removeWeightGroups(obj, empty_groups)
        return len(empty_groups)
    else:
        if obj:
            name= obj.name
        else:
            name= "None"
        print("WARN: can not remove weightgroups from Object %s" % name)
        return 0
        
def createEmptyGroups(obj, names=None):
    arm = obj.find_armature()
    if names == None:
        names = [bone.name for bone in get_modify_bones(arm) if bone.use_deform]
    if arm:
        for gname in [name for name in names if not name in obj.vertex_groups]:
            obj.vertex_groups.new(name=gname)

def get_ui_level():
    preferences = getAddonPreferences()
    ui_level = preferences.ui_complexity
    return int(ui_level)

def get_precision():
    pref = getAddonPreferences()
    return pref.precision

def getPreferences():
    return bpy.context.preferences

def getAddonPreferences():
    user_preferences = getPreferences()
    d = user_preferences.addons[__package__].preferences
    return d

def always_alter_to_restpose():
    props = getAddonPreferences()
    return props.always_alter_restpose

def get_rig_type(rigType=None):
    if rigType == None:
        sceneProps = context.scene.SceneProp
        rigType    = sceneProps.avastarRigType
    return rigType

def get_joint_type(jointType=None):
    if jointType == None:
        sceneProps = context.scene.SceneProp
        jointType  = sceneProps.avastarJointType
    return jointType

def resolve_definition_file(file):
    if os.path.exists(file):
        result = file
    else:
        file = os.path.join(DATAFILESDIR, file)
        result = file if os.path.exists(file) else None
    return file

def get_default_skeleton_definition(filename):
    definition_file = "avatar_%s.xml" % filename
    definition_file = resolve_definition_file(definition_file)
    return definition_file

def get_skeleton_file():
    return get_default_skeleton_definition("skeleton")

def get_lad_file():
    return get_default_skeleton_definition("lad")

def get_shape_filename(name):
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
    return os.path.join(TMP_DIR, name+'.xml')

Identity = Matrix()    
def print_mat(msg, Mat):
    if Mat == Identity:
        print(msg,"Identity")
    else:
        print(msg,Mat)

def is_identity(M):
   M4=M.copy()
   sanitize(M4, 6)
   M3 = M.to_3x3()
   return M3 == M3.inverted()

def get_version_info(obj):
    ''' Return Version information:
        if obj is not an armature, return version of bound armature
        if obj is an armature, return version info of obj
        
        avastarversion : textstring, 3 parts: "2.0.50"
        rigversion     : textstring, 3 parts: "2.0.45" or None
        rigid          : integer identify rigversion: 5 or None
        RigType        : "EXTENDED" or "BASIC" or None'''

    avastarversion = "%s.%s.%s" % (bl_info['version'])
    if obj and obj.type != 'ARMATURE':
        armobj = get_armature(obj)
    else:
        armobj = obj

    if not armobj:
        rigid = rigType = rigversion = None
    else:
        rigid   = armobj.get('avastar', None)
        rigType = armobj.RigProp.RigType
        if 'version' in armobj:
            rigversion = "%s.%s.%s" % (armobj['version'][0],armobj['version'][1],armobj['version'][2], )
        else:
            rigversion = None

    return avastarversion, rigversion, rigid, rigType
    
def copydir(src,dst, overwrite=False):
    for root, dirs, files in os.walk(src):
        srcdir=root
        folder=srcdir[len(src):]
        dstdir=dst+folder
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
            
        for file in files:
            dstfile = os.path.join(dstdir,file)
            if overwrite or not os.path.exists(dstfile):
                srcfile = os.path.join(srcdir,file)
                shutil.copyfile(srcfile, dstfile)

def copyblend(src, dst, overwrite=False):


    counter = 0
    for root, dirs, files in os.walk(src):
        srcdir = root
        folder = srcdir[len(src)+1:]

        for file in files:

            if file == 'startup.blend':
                filename = folder+'.blend'
                log.debug("copyblend: dst folder : %s" % dst)
                log.debug("copyblend: dst file   : %s" % filename)
                tofile = os.path.join(dst,filename)

                if overwrite or not os.path.exists(tofile):
                    if not os.path.exists(dst):
                        os.makedirs(dst)
                    srcfile = os.path.join(srcdir,file)
                    log.debug("copyblend: copy %s to %s" % (srcfile, tofile) )
                    shutil.copyfile(srcfile, tofile)
                    counter += 1

    log.warning("  Copied %d template files to" % counter)
    log.warning("  %s" % dst)

class slider_context():

    was_disabled = False

    def __init__(self):
        pass

    def __enter__(self):
        self.was_disabled = get_disable_update_slider_selector()
        if self.was_disabled:

            return True
        
        visitlog.debug("Enter slider_context. (Disable slider updates)")
        set_disable_update_slider_selector(True)
        return False

    def __exit__(self, type, value, traceback):
        set_disable_update_slider_selector(self.was_disabled)
        if type or value or traceback:
            log.error("Exception type: %s" % type )
            log.error("Exception value: %s" % value)
            log.error("traceback: %s" % traceback)
            raise

        if not self.was_disabled:
            visitlog.debug("Exit slider_context. (Enable slider updates)")


disable_update_slider_selector=False
def set_disable_update_slider_selector(state):
    global disable_update_slider_selector
    oldstate = disable_update_slider_selector
    disable_update_slider_selector=state
    return oldstate

def get_disable_update_slider_selector():
    global disable_update_slider_selector
    return disable_update_slider_selector

shapeUpdateIsActive = False
def set_shape_update_in_progres(updating):
    global shapeUpdateIsActive
    org =  shapeUpdateIsActive
    shapeUpdateIsActive = updating
    return org


def get_shape_update_in_progres():
    global shapeUpdateIsActive
    return shapeUpdateIsActive

def enforce_armature_update(context, armobj):
    global shapeUpdateIsActive

    try:
        shapeUpdateIsActive = True
        omode = ensure_mode_is('EDIT', object=armobj, toggle_mode='POSE')
        ensure_mode_is(omode, object=armobj)
        shapeUpdateIsActive = False
        update_view_layer(context)
    except:
        pass





gender_update_in_progress=False
def set_gender_update_in_progress(is_active):
    global gender_update_in_progress
    oactive = gender_update_in_progress
    gender_update_in_progress = is_active
    return oactive


def is_gender_update_in_progress():
    global gender_update_in_progress
    return gender_update_in_progress


use_bind_pose_update_in_progress = True
def set_use_bind_pose_update_in_progress(state):
    global use_bind_pose_update_in_progress
    old_state = use_bind_pose_update_in_progress
    use_bind_pose_update_in_progress = state
    return old_state


def is_use_bind_pose_update_in_progress():
    global use_bind_pose_update_in_progress
    return use_bind_pose_update_in_progress


def get_modifiers(ob, type):
    return [mod for mod in ob.modifiers if mod.type==type]
    
def get_tri_count(faces, loops):
    tris = 0
    if faces > 0:
        tris = int(((loops / faces) - 2) * faces + 0.5)
    return tris

def merge_dicts(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy.'''
    z = x.copy()
    z.update(y)
    return z

def shorten_text(text, maxlen=24, cutbegin=False, cutend=False):
    if len(text) <= maxlen: return text

    if cutbegin:
        newtext = '...' + text[-maxlen:]
    elif cutend:
        newtext = text[0:maxlen] + '...'
    else:
        splitlen = int((maxlen-2)/2)
        newtext = text[0:splitlen] + "..." + text[-splitlen:]
    return newtext

def closest_point_on_mesh(ob,co):
    status, co, no, index = ob.closest_point_on_mesh(co)
    return status, co, no, index

def ray_cast(ob, co, nor):
    status, co, no, index = ob.ray_cast(co, nor)
    return status, co, no, index

def get_center(context, ob):

    active = get_active_object(context)    
    set_active_object(context, ob)
    cursor_location = get_cursor(context)
    
    omode = ensure_mode_is('EDIT')

    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.view3d.snap_cursor_to_selected()
    loc = get_cursor(context)

    set_cursor(context, cursor_location)
    ensure_mode_is(omode)
    set_active_object(context, active)
    return loc

def get_selected_object_names(context):
    return get_selected_objects(context, use_names=True)

def get_selected_objects(context, use_names=False, types=None):
    return [o.name if use_names else o for o in context.scene.objects if object_select_get(o) and (types==None or o.type in types)]

def remember_unselectable_objects(context):
    unselectable = []
    for ob in context.scene.objects:
        if ob.hide_select:
            unselectable.append(ob.name)
            ob.hide_select = False
    return unselectable

def remember_invisible_objects(context):
    invisible = []
    for ob in context.scene.objects:
        if object_hide_get(ob):
            invisible.append(ob.name)
            object_hide_set(ob, False)
    return invisible

def restore_object_select_states(context, selected_object_names):
    bpy.ops.object.select_all(action='DESELECT')
    scene = context.scene
    for name in selected_object_names:
        ob = scene.objects.get(name)
        if ob:
            object_select_set(ob, True)

def restore_unselectable_objects(context, unselectable):
    scene = context.scene
    for name in unselectable:
        ob = scene.objects.get(name)
        if ob:
            ob.hide_select=True

def restore_invisible_objects(context, invisible):
    scene = context.scene
    for name in invisible:
        ob = scene.objects.get(name)
        if ob:
            object_hide_set(ob, True)

def check_selected_change(context, oselected, msg=''):
    selected = get_selected_object_names(context)
    if len(set(selected) - set(oselected)) > 0 or len(set(oselected) - set(selected)) > 0:
        print("Selection changed:", msg)
        print ( "Original "  , *oselected )
        print ( "Changed to ", *selected )

avastar_repository = None
def ensure_avastar_repository_is_loaded():
    global avastar_repository
    if avastar_repository:
        repo_keys = avastar_repository.keys()
        keycount = len(repo_keys)
        if keycount > 0:
            repo_key = list(repo_keys)[0]
            if repo_key in bpy.data.objects:
                log.warning("Repo already loaded (%d keys)" % keycount)
                return avastar_repository

    preferences = getAddonPreferences()
    use_asset_library_link = preferences.use_asset_library_link
    filepath = ASSETS

    with bpy.data.libraries.load(filepath, link=use_asset_library_link) as (data_from, data_to):
        data_to.objects = data_from.objects

    avastar_repository = {ob.name:ob for ob in data_to.objects}
    log.warning("Repo loaded %s" % (avastar_repository.keys()))
    return avastar_repository


def load_from_library(filepath, section, item_name):
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        setattr(data_to, section, [item_name])


def find_view_context(context, obj=None):
    ctx = get_context_copy(context)
    areas  = [area for area in context.screen.areas if area.type == 'VIEW_3D']
    if areas:
        regions = [region for region in areas[0].regions if region.type == 'WINDOW']
        if regions:
            ctx['region']        = regions[0]
            ctx['area']          = areas[0]
            if obj:
                ctx['active_object'] = obj
    return ctx

def matrixScale(scale, M=None, replace=False):
    if M == None:
        M = Matrix()

    if replace:
        M[0][0] = scale[0]
        M[1][1] = scale[1]
        M[2][2] = scale[2]
   
    else:
        M[0][0] *= scale[0]
        M[1][1] *= scale[1]
        M[2][2] *= scale[2]

    return M

def matrixLocation(loc, M=None, replace=False):
    if M == None:
        M = Matrix()

    if replace:
        M[0][3] = loc[0]
        M[1][3] = loc[1]
        M[2][3] = loc[2]
    else:
        M[0][3] += loc[0]
        M[1][3] += loc[1]
        M[2][3] += loc[2]

    return M


def apply_transform(ob, with_loc=True, with_rot=True, with_scale=True):

    loc, rot, scale = ob.matrix_world.decompose()
    M = Matrix()
    if with_scale:
        M = matrixScale(scale,M)
    if with_rot:
        M = M @ rot.to_matrix().to_4x4()
    if with_loc:
        M = matrixLocation(loc, M)
    
    ob.data.transform(M)
    ob.matrix_world = ob.matrix_world @ M.inverted()
    ob.rotation_euler = Euler()
    ob.scale = (1,1,1)


def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

def is_at_same_location(vec1, vec2, rel_tol=1e-09, abs_tol=0.0):
    return all([isclose(a,b, rel_tol, abs_tol) for a,b in zip(vec1,vec2)])

def is_unity_matrix(M, has_rotation=None):
    if has_rotation == None:
        has_rotation = is_rotation_matrix(M)

    return (not has_rotation) and isclose(M[0][0],1) and isclose(M[1][1],1) and isclose(M[2][2],1)


def is_rotation_matrix(M):
    return not (isclose(M[0][1],0) and isclose(M[0][2],0) and \
                isclose(M[1][0],0) and isclose(M[1][2],0) and \
                isclose(M[2][0],0) and isclose(M[2][1],0) )


def sanitize_f(f, precision=6):
    val = round(f, precision) if precision else f
    result = 0 if precision and abs(val) <= 10**-precision else val
    return result

def sanitize_v(vec, precision=6):
    result = [sanitize_f(f, precision) for f in vec]
    return Vector(result)

def sanitize(mat, precision):
    if not precision:
        return mat

    for i in range(0,4):
        for j in range(0,4):
            val = round(mat[i][j], precision)
            mat[i][j] = val
    return mat

def similar_quaternion(A, B, abs_tol=0.001):
    for i in range(4):
        if not isclose(A[i], B[i], abs_tol=abs_tol):
            return False
    return True


def similar_matrix(A,B):
    cols = len(A.row)
    rows = len(A.col)
    for i in range(0,cols):
        for j in range(0,rows):
            if not isclose(A[i][j], B[i][j], rel_tol=1e-06):
                return False
    return True

def clear_transforms(context, srcobjs):
    old_parents = {}
    bpy.ops.object.select_all(action='DESELECT')
    
    for ob in srcobjs:
        old_parents[ob.name]=ob.parent
        object_select_set(ob, True)

    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    return old_parents

def transform_origins_to_location(context, srcobjs, loc):

    scene = context.scene
    selected_object_names = get_selected_object_names(context)
    cloc = get_cursor(context)
    set_cursor(context, loc.copy())

    bpy.ops.object.select_all(action='DESELECT')
    for ob in srcobjs:
        object_select_set(ob, True)
        log.debug("transform_origins: Add [%s %s] to set" % (ob.type, ob.name) )

    log.info("transform_origins_to_location: Move %d Origins to %s" % (len(srcobjs), get_cursor(context)))
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    restore_object_select_states(context, selected_object_names)
    set_cursor(context, cloc)


def transform_objects_to_location(context, srcobjs, loc):

    for ob in srcobjs:

        ob.location = loc.copy()
        log.info("transform_location: moved [%s %s] to %s" % (ob.type, ob.name, loc) )

def transform_empty_to_target(ob, delta):
    ob.matrix_world.translation -= delta
    for ch in ob.children:
        ch.matrix_world.translation += delta
        
def transform_origins_to_target(context, tgtobj, srcobjs, delta=V0):

    scene = context.scene
    active = get_active_object(context)
    if tgtobj != active:
        set_active_object(context, tgtobj)
        
    cloc = get_cursor(context)
    tloc = tgtobj.location.copy()
    set_cursor(context, tloc)

    selected_object_names = get_selected_object_names(context)
    bpy.ops.object.select_all(action='DESELECT')

    object_select_set(tgtobj, True)
    for ob in srcobjs:
        if ob.type == 'EMPTY':
            transform_empty_to_target(ob,delta)
        else:
            object_select_set(ob, True)
            log.debug("transform origins to target: Add [%s %s] to set" % (ob.type, ob.name) )

    log.info("transform origins to target: Move %d Origins to %s" % (len(srcobjs), get_cursor(context)))
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    restore_object_select_states(context, selected_object_names)
    
    set_cursor(context, cloc)
    if tgtobj != active:
        set_active_object(context, active)

def transform_matrices_to_target(srcobjs, delta):


    for ob in srcobjs:
        if ob.type == 'EMPTY':
            transform_empty_to_target(ob,delta)
        else:
            ob.matrix_world.translation -= delta

    
def transform_rootbone_to_origin(context, armobj):
    log.info("Transform Root Bone to Origin for [%s]" % context.object.name)
    active = context.object
    amode = ensure_mode_is("OBJECT", context=context)

    set_active_object(context, armobj)
    omode = ensure_mode_is("EDIT", context=context)
    bones  = armobj.data.edit_bones
    origin_bone = bones.get('Origin')
    diff = origin_bone.head.copy()

    origin_bone.tail -= diff
    origin_bone.head  = Vector((0,0,0))
    log.info("Transform Root Bone has been reset to match Origin for [%s]" % context.object.name)
    ensure_mode_is(omode, context=context)

    set_active_object(context, active)
    ensure_mode_is(amode, context=context)

    return diff

def transform_origin_to_rootbone(context, armobj):
    log.info("Transform Origin to Root Bone for [%s]" % armobj.name)
    active = context.object
    cloc   = get_cursor(context)
    origin_head, origin_tail = get_bone_location(armobj, 'Origin')
    if not origin_head or origin_head.magnitude < MIN_JOINT_OFFSET_STRICT:
        return # Origin is already at root bone

    amode = ensure_mode_is("OBJECT")
    set_active_object(context, armobj)
    omode = ensure_mode_is("OBJECT")
    selected_object_names = get_selected_object_names(context)
    bpy.ops.object.select_all(action='DESELECT')
    object_select_set(armobj, True)

    origin_loc =  mulmat(armobj.matrix_world, Vector(origin_head))
    set_cursor(context, origin_loc)

    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    ensure_mode_is(omode)
    restore_object_select_states(context, selected_object_names)
    set_cursor(context, cloc)
    set_active_object(context, active)
    ensure_mode_is(amode)
    return origin_loc
    
def set_bone_select_mode(armobj, state, boneset=None, additive=True):
    bones = get_modify_bones(armobj)
    if boneset == None:
        boneset = bones

    store = {}
    for bone in bones:
        newstate = state if bone.name in boneset else bone.select if additive else not state
        if newstate:
            print("set_bone_select_mode: set bone", bone.name, newstate)
        store[bone.name]=bone.select
        bone.select = bone.select_head = bone.select_tail = newstate
    return store

def get_pose_bone_select(armobj, bone_names=None):
    if bone_names == None:
        bone_names=armobj.pose.bones.keys()
    store = {}

    for name in bone_names:
        bone = armobj.data.bones.get(name)
        if bone:
            store[name]=[bone.select, bone.select_head, bone.select_tail]
    return store

def restore_pose_bone_select(armobj, store):
    for key, entry in store.items():
        bone = armobj.data.bones.get(key)
        bone.select, bone.select_head, bone.select_tail = entry

def set_bone_select_restore(armobj, store):
    bones = get_modify_bones(armobj)
    for name in store.keys():
        bone = bones.get(name,None)
        if bone:
            bone.select = bone.select_head = bone.select_tail = store.get(name)

def bone_is_visible(armobj, bone, check_paired_bone=False):

    is_visible=False
    if bone.hide:
        is_visible=False

    for layer in range(32):
        if armobj.data.layers[layer] and bone.layers[layer]:
            is_visible=True
            break

    if not is_visible and check_paired_bone:
        if bone.name[0]=='m':
            cbone = armobj.data.bones.get(bone.name[1:])
            if cbone:
                is_visible = bone_is_visible(armobj, cbone)
        else:
            mbone = armobj.data.bones.get('m'+bone.name)
            if mbone:
                is_visible = bone_is_visible(armobj, mbone)

    return is_visible

def match_armature_scales(source, target):
    tlocs = [v for bone in target.data.bones if bone.use_deform for v in (bone.head_local, bone.tail_local)]
    slocs = [v for bone in source.data.bones if bone.use_deform for v in (bone.head_local, bone.tail_local)]
    source_size = source.scale[2] * (max([location[2] for location in slocs]) - min([location[2] for location in slocs]))
    target_size = target.scale[2] * (max([location[2] for location in tlocs]) - min([location[2] for location in tlocs]))
    source.scale *=  target_size / source_size
    print("Source size:", source.scale[2]*source_size, "Target size:", target.scale[2]*target_size)





def get_gp(context, gname='gp'):
    gp = context.scene.objects.get(GP_NAME)
    if not gp:
        bpy.ops.object.gpencil_add()
        gp = bpy.context.scene.objects[-1]
        gp.name = GP_NAME
        print("Added Grease Pencil %s to current scene" % (gp.name) )
    return gp

def gp_init_callback(context, gp, palette):
    if palette:
        ob=context.object
        colcount = 0
        if ob:
            armobj = ob if ob.type=='ARMATURE' else ob.find_armature()
            if armobj:
                for bgroup in armobj.pose.bone_groups:
                    col = bgroup.colors.normal
                    color = palette.colors.new()
                    color.color = bgroup.colors.normal
                    color.name  = bgroup.name
                colcount = len(palette.colors)
                print("Added %d colors from Armature %s to palette %s" % (colcount, armobj.name, palette.name) )
        if colcount == 0:
            color = palette.colors.new()
            color.color=(1,0,1)
            print("Added default color to palette", palette.name)
    return
    
def get_gp_palette(context, gname='gp', pname='gp', callback=gp_init_callback):
    gp = get_gp(context, gname)
    palette = gp.palettes.get(pname)
    if not palette:
        palette = gp.palettes.new(pname, set_active=True)
        print("Added new Grease Pencil palette", palette.name)
        if callback:
            callback(context, gp, palette)
        else:
            color = palette.colors.new()
            color.color=(1,1,1)
            print("Added default color to palette", palette.name)
    return palette

def get_gp_color(palette, color_index=0 ):
    ccount = len(palette.colors)

    if color_index >= ccount:
        missingCount = color_index + 1 - ccount
        for i in range(missingCount):
            palette.colors.new()
        print("Added %d Pencil color slots" % (missingCount))
    color = palette.colors[color_index]
    return color

def get_gp_layer(context, gname='gp', lname='gp'):
    gp = get_gp(context, gname)
    if lname in gp.layers:
        layer = gp.layers[lname]
    else:
        layer = gp.layers.new(lname, set_active=True)
        print("Added new Grease Pencil layer", layer.info)
    return layer

def get_gp_frame(context, gname='gp', lname='gp'):
    layer = get_gp_layer(context, gname, lname)
    if len(layer.frames) == 0:
        frame = layer.frames.new(context.scene.frame_current)
    else:
        frame = layer.frames[0]
    return frame

def get_gp_stroke(context, gname='gp', lname='gp', pname='gp', color_index=0, callback=gp_init_callback):
    palette = get_gp_palette(context, gname=gname, pname=pname, callback=callback)
    color   = get_gp_color(palette, color_index)
    frame   = get_gp_frame(context, gname, lname)
    stroke  = frame.strokes.new(colorname=color.name)
    stroke.draw_mode = '3DSPACE'
    return stroke

def gp_draw_cross(context, locVector, sizeVector=Vector((0.01, 0.01, 0.01)), gname='gp', lname='gp', pname='gp', color_index=0, callback=gp_init_callback, dots=0):
    lines = [Vector((sizeVector[0],0,0)), Vector((0,sizeVector[1],0)), Vector((0,0,sizeVector[2]))]

    for line in lines:
        from_vector = locVector + line
        to_vector = locVector - line
        gp_draw_line(context, from_vector, to_vector, gname, lname, pname, color_index, callback, dots)

def gp_draw_line(context, from_vector, to_vector, gname='gp', lname='gp', pname='gp', color_index=0, callback=gp_init_callback, dots=0):
    dotcount=dots+1
    substroke = (to_vector - from_vector) / dotcount
    f = from_vector.copy()

    for i in range (ceil(dotcount/2)):
        t = f+substroke
        stroke = get_gp_stroke(context, gname, lname, pname, color_index, callback=callback)
        stroke.points.add(2)
        stroke.points.foreach_set("co", f.to_tuple() + t.to_tuple() )
        f += 2*substroke

def matrix_from_array(array):
    M = Matrix()
    for i in range(0,4):
        for j in range(0,4):
            M[i][j] = array[4*j + i]
    return M

def matrix_to_array(M):
    array = [0.0]*16
    for i in range(0,4):
        for j in range(0,4):
            array[4*j + i] = M[i][j]
    return array

def matrix_as_string(M):
    sm="\n"
    for i in range(0,4):
        sm += "Matrix((({: 6f}, {: 6f}, {: 6f}, {: 6f}),\n".format  (*M[i])
    return sm

def float_array_from_string(s):
    val = [0.0, 0.0, 0.0] if not s else [float(v) for v in s.split()]
    return val


def vector_from_string(s):
    val = Vector(float_array_from_string(s))
    return val

def is_linked_hierarchy(selection):
    if not selection:
        return False

    for ob in selection:
        if is_linked_item(ob):
            log.warning("Found linked object %s" % ob.name)
            return True
        
        if is_linked_hierarchy(ob.children):
            log.warning("Found linked childlist in %s" % ob.name)
            return True
    return False

def is_linked_item(obj):
    if obj.library != None:
        return True
    if obj.instance_collection and obj.instance_collection.library != None:
        return True
    if obj.proxy and obj.proxy.library != None:
        return True
    return False

def use_sliders(context):
    return context.scene.SceneProp.panel_appearance_enabled

def remove_key(item, key):
    if key in item:
        del item[key]


def get_head_tail(arm_obj, bname, msg=""):
    bones = get_modify_bones(arm_obj)
    dbone = bones.get(bname)
    head=V0.copy()
    tail=V0.copy()
    mag=0
    if dbone:
        head = dbone.head if arm_obj.mode=='EDIT' else dbone.head_local
        tail = dbone.tail if arm_obj.mode=='EDIT' else dbone.tail_local
        mag = (tail-head).magnitude
        log.warning("%s h:%s t:%s m:%f" % (msg, head, tail, mag))
    else:
        log.warning("Bone %s does not exist" % bname)
    return mag
        

def has_joint_position(joints, dbone, check_tail=True):
    if not joints:
        return False

    joint = joints.get(dbone.name)
    if joint and joint['enabled']:
        has_joint = joint['hmag'] > MIN_JOINT_OFFSET
        if check_tail:
            has_joint |= joint['tmag'] > MIN_JOINT_OFFSET
    else:
        has_joint = False

    return has_joint

def get_joint_position(joints, dbone):
    if joints:
        joint = joints.get(dbone.name)
        if joint and joint['enabled']:
            dh = Vector(joint['head']) if joint['hmag'] > MIN_JOINT_OFFSET else V0.copy()
            dt = Vector(joint['tail']) if joint['tmag'] > MIN_JOINT_OFFSET else V0.copy()
            return dh, dt
    return V0.copy(), V0.copy()

def has_head_offset(joints, bone):
    if not bone:
        return False
    if not joints:
        return False
 
    joint = joints.get(bone.name)
    if not joint or not joint['enabled']:
        return False

    return joint.get('hmag') > MIN_JOINT_OFFSET_STRICT









#







#







#





def remove_head_offset(bone):
    if bone and JOINT_O_HEAD_ID in bone:
        del bone[JOINT_O_HEAD_ID]

def remove_tail_offset(bone):
    if bone and JOINT_O_TAIL_ID in bone:
        del bone[JOINT_O_TAIL_ID]

def logtime(tic, msg, indent=0, mintime=20):
    toc = time.time()
    d = (toc - tic) * 1000
    if d >= mintime:
        timerlog.debug("%s% 5.0f millis - %s" % ('_'*indent, d, msg))
    return toc

def short_obname(name):
    import re
    result = re.sub('\(.*\)', '', name)
    return result

def clean_name(filename):

    preferences = getAddonPreferences()
    use_safe_names = preferences.use_safe_names

    if use_safe_names:
        output = bpy.path.clean_name(filename)
        log.debug(" Using safe name [%s] -> [%s]" % (filename, output) )
    else:
        keepcharacters = (' ','.','_')
        output = "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()
        log.debug(" Using relaxed name [%s] -> [%s]" % (filename, output) )

    return output

last_context_object = None
last_context_mode = None

def context_or_mode_changed(obj):
    global last_context_object
    global last_context_mode
    mode= obj.mode if obj else None

    if last_context_object != None or last_context_mode != None:
        is_same = (obj == last_context_object and mode == last_context_mode)
    else:
        is_same = True
    
    last_context_object = obj
    last_context_mode = mode

    return not is_same

def bmesh_vert_active(bm):
    if bm.select_history:
        elem = bm.select_history[-1]
        if isinstance(elem, bmesh.types.BMVert):
            return elem
    return None

def toVector(prop):
    if not prop:
        return Vector((0,0,0))

    vec3d = [prop[i] for i in range(3)]
    return Vector(vec3d)
    
def get_local_matrix(armobj, dbone):
    if armobj.mode == 'EDIT':
        return dbone.matrix
    return dbone.matrix_local

def add_missing_mirror_groups(context, ob=None):

    active_object = get_active_object(context)
    if ob:
        set_active_object(context, ob)
        obj = ob
    else:
        obj = active_object

    scene = context.scene
    if obj.type != 'MESH':
        log.error("Can not add vertex groups to ob:%s of type :%s" % (obj.name, obj.type) )
        return -1

    bone_set = []
    for group in obj.vertex_groups:
        bone_set.append(group.name)

    missing_groups = get_missing_mirror_bone_names(bone_set)
    for key in missing_groups:
        obj.vertex_groups.new(name=key)

    missing_group_count = len(missing_groups)
    if missing_group_count > 0:
        print("Added %d missing Mirrored groups" % missing_group_count)

    original_mode = ensure_mode_is('OBJECT')
    bpy.ops.object.editmode_toggle()
    ensure_mode_is(original_mode)
    if ob:
        set_active_object(context, active_object)
    return missing_group_count

def get_missing_mirror_bone_names(bone_set):
    missing_mirror_bone_names = []
    for key in bone_set:
        mkey = get_mirror_name(key)
        if mkey and not mkey in bone_set:
            missing_mirror_bone_names.append(mkey)
    return missing_mirror_bone_names

def get_tracedump():
    tb=traceback.format_stack()
    result = ''
    for i in range(0,len(tb)-2):
        result += tb[i]
    return result

def disable_eye_targets(arm_obj):
    states = [
        arm_obj.IKSwitchesProp.Enable_Eyes,
        arm_obj.IKSwitchesProp.Enable_AltEyes
    ]
    arm_obj.IKSwitchesProp.Enable_Eyes = False
    arm_obj.IKSwitchesProp.Enable_AltEyes  = False
    return states

def enable_eye_targets(arm_obj, states):
    arm_obj.IKSwitchesProp.Enable_Eyes = states[0]
    arm_obj.IKSwitchesProp.Enable_AltEyes = states[1]


def adjust_eye_target_distance(armobj, factor, eye):

    bones=armobj.data.edit_bones
    lb=bones.get('%sLeft'%eye)
    rb=bones.get('%sRight'%eye)
    tb=bones.get('%sTarget'%eye)
    if lb and rb and tb:
        center = (lb.head+rb.head)/2
        dist = (lb.head-rb.head).magnitude
        loc = Vector((0,-factor*dist,0))+center
        tail = (tb.tail-tb.head).normalized()*dist
        tb.head = loc
        tb.tail = loc+tail


def load_workspace(context, WORKSPACE, BLENDFILE):
    workspace = bpy.data.workspaces.get(WORKSPACE)
    if not workspace:
        with bpy.data.libraries.load(BLENDFILE, link=False) as (data_from, data_to):
            data_to.workspaces = [WORKSPACE]
    return


def start_profiler():
    import cProfile
    pr = cProfile.Profile()
    pr.enable()
    return pr


def end_profiler(pr):
    import cProfile, pstats
    pr.disable()
    pr.dump_stats("D://blendergit/addon_development/avastar-1/tmp/test.profile")
    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())


classes = (
    GenericInfoOperator,
    WeightmapInfoOperator,
    TrisInfoOperator,
    BaketoolInfoOperator,
    Baketool2InfoOperator,
    SliderInfoOperator,
    UVmapInfoOperator,
    MaterialInfoOperator,
    ShaderInfoOperator,
    ErrorDialog,
    ButtonCopyToPastebuffer,
    AlterToRestPose,
    BindToCurrentPose,
    ExpandablePannelSection
)

def register():

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        registerlog.info("Registered util:%s" % cls)

def unregister():

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered util:%s" % cls)
