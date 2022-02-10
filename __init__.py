### Copyright     2011-2013 Magus Freston, Domino Marama, and Gaia Clary
### Modifications 2014-2015 Gaia Clary
### Modification  2015      Matrice Laville
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

bl_info = {
    "name": "Avastar",
    "author": "Machinimatrix",
    "version": (2, 91, 66),
    "blender": (2, 81, 0),
    "api": 36147,
    "location": "Add Menu, 3D View Properties, Property sections and Tools",
    "description": "Character creation & animation for SL and OpenSim",
    "show_expanded": True,
    "wiki_url":  "https://avastar.online/",
    "tracker_url": "https://support.machinimatrix.org/tickets/",
    "category": "Object"}

if "bpy" in locals():
    import imp
    if "const" in locals():
        imp.reload(const)
    if "init" in locals():
        imp.reload(init)
    if "propgroups" in locals():
        imp.reload(propgroups)
    if "animation" in locals():
        imp.reload(animation)
    if "armature_util" in locals():
        imp.reload(armature_util)
    if "create" in locals():
        imp.reload(create)
    if "context_util" in locals():
        imp.reload(context_util)
    if "data" in locals():
        imp.reload(data)
    if "bind" in locals():
        imp.reload(bind)
    if "debug" in locals():
        imp.reload(debug)
    if "generate" in locals():
        imp.reload(generate)
    if "copyrig" in locals():
        imp.reload(copyrig)
    if "updaterig" in locals():
        imp.reload(updaterig)
    if "mesh" in locals():
        imp.reload(mesh)
    if "messages" in locals():
        imp.reload(messages)
    if "pannels" in locals():
        imp.reload(pannels)
    if "presets" in locals():
        imp.reload(presets)
    if "quadify" in locals():
        imp.reload(quadify)
    if "rig" in locals():
        imp.reload(rig)
    if "shape" in locals():
        imp.reload(shape)
    if "skeleton" in locals():
        imp.reload(skeleton)
    if "util" in locals():
        imp.reload(util)
    if "math" in locals():
        imp.reload(math)
    if "weights" in locals():
        imp.reload(weights)
    if "www" in locals():
        imp.reload(www)
else:
    import bpy
    from . import propgroups
    from . import animation
    from . import armature_util
    from . import context_util
    from . import const
    from . import init
    from . import create
    from . import data
    from . import bind
    from . import debug
    from . import generate
    from . import copyrig
    from . import updaterig
    from . import mesh
    from . import messages
    from . import pannels
    from . import presets
    from . import quadify
    from . import rig
    from . import shape
    from . import skeleton
    from . import util
    from . import math
    from . import weights
    from . import www


import os, sys, glob, string, gettext, re
import bmesh, addon_utils
from bpy.types import Menu, Operator, PropertyGroup, Operator, AddonPreferences
from bpy.props import *
from bpy.utils import previews
from bl_operators.presets import AddPresetBase
from bpy.app.handlers import persistent
from bpy_extras.io_utils import ExportHelper

from mathutils import Quaternion, Matrix, Vector
from math import sin, asin
import logging, importlib

from .pannels import PanelAvastarTool
from .data   import Skeleton
from .const  import *

try:
    import xml
    import xmlrpc.client
except:
    print("xmlrpc: i can not configure the remote call to machinimatrix.")
    print("Sorry, we can not provide this feature on your computer")

BLENDER_VERSION = 10000 * bpy.app.version[0] + 100 * bpy.app.version[1] +  bpy.app.version[2]

log = logging.getLogger('avastar.main')
updatelog = logging.getLogger('avastar.update')
visitlog = logging.getLogger('avastar.visit')
registerlog = logging.getLogger("avastar.register")


def copypaste_pose(self, context):
    ob = context.object
    if ob and ob.type=='ARMATURE' and ob.mode=='POSE':
        self.layout.separator()
        self.layout.operator("avastar.pose_copy", text='', icon='COPYDOWN')
        self.layout.operator("avastar.pose_paste", text='', icon='PASTEDOWN')
        self.layout.operator("avastar.pose_mirror_paste", text='', icon="PASTEFLIPDOWN")
        self.layout.operator("avastar.key_pose_changes", text='', icon=ICON_KEY_HLT)

class PoseCopy(bpy.types.Operator):
    bl_idname = "avastar.pose_copy"
    bl_label  = "Copy Pose"
    bl_description = "Copies the current pose to the copy/paste buffer\n\nNote:Only selected bones are copied"

    def execute(self, context):
        return bpy.ops.pose.copy()

class PosePaste(bpy.types.Operator):
    bl_idname = "avastar.pose_paste"
    bl_label  = "Paste Pose"
    bl_description = "Applies the pose from the copy Paste buffer back to the Armature\n\nNote: You need to Copy Pose before you can paste"

    def execute(self, context):
        return bpy.ops.pose.paste(flipped=False)

class PoseMirrorPaste(bpy.types.Operator):
    bl_idname = "avastar.pose_mirror_paste"
    bl_label  = "Paste Mirror Pose"
    bl_description = "Applies the mirrored pose from the copy Paste buffer back to the Armature\n\nNote: You need to Copy Pose before you can paste"

    def execute(self, context):
        return bpy.ops.pose.paste(flipped=True)




global in_config
in_config = False
def init_log_level(context):
    global in_config
    in_config = True


    logger_list = context.window_manager.LoggerPropList
    logger_names = logging.Logger.manager.loggerDict.keys()
    logger_list.clear()

    prop = logger_list.add()
    prop.name = "root"
    prop.log_level = str(logging.getLogger().getEffectiveLevel())

    for name in logger_names:
        prop = logger_list.add()
        prop.name = name
        prop.log_level = str(logging.getLogger(name).getEffectiveLevel())

    in_config=False

def configure_log_level(self, context):
    global in_config
    if in_config:
        return

    logger = logging.getLogger() if self.name == 'root' else logging.getLogger(self.name)
    logger.setLevel(int(self.log_level))
    init_log_level(context)

class LoggerIndexPropGroup(bpy.types.PropertyGroup):
    index : IntProperty(name="index")

class LoggerPropListGroup(bpy.types.PropertyGroup):
    log_level : EnumProperty(
    items=(
        (str(logging.DEBUG),    'Debug',    'Detailed Programmer Information\nEnable when requested by Support team'),
        (str(logging.INFO),     'Info',     'Detailed User Information to Console\nEnable when in need to see more details'),
        (str(logging.WARNING),  'Warning',  '(Default) Events which may or may not indicate an Issue\nUsually this is all you need'),
        (str(logging.ERROR),    'Error',    'Events which very likely need to be fixed by User'),
        (str(logging.CRITICAL), 'Critical', 'Events which certainly need care taking by the Support team')),
    name="Log Level",
    description="Log Level Settings",
    default=str(logging.WARNING),
    update = configure_log_level)


class AVASTAR_UL_LoggerPropVarList(bpy.types.UIList):

    def draw_item(self,
                  context,
                  layout,
                  data,
                  item,
                  icon,
                  active_data,
                  active_propname
                  ):

        row = layout.row(align=True)
        row.alignment='LEFT'
        row.prop(item,"log_level", text='')
        row.label(text=item.name)





class WeightsPropGroup(bpy.types.PropertyGroup):
    pass

class StringListProp(bpy.types.PropertyGroup):
    name : StringProperty()






#


#




#


#
















def installedAddonsCallback(scene, context):
    items=[]
    if addon_utils.check("avastar")[0]:
        items.append(('Avastar',   'Avastar', "Avastar Addon for Blender"))
        
    if addon_utils.check("sparkles")[0]:
        items.append(('Sparkles',   'Sparkles', "Sparkles Addon for Blender"))
        
    if addon_utils.check("primstar")[0]:
        items.append(('Primstar',   'Primstar', "Primstar Addon for Blender"))
    return items

def ui_complexity_callback(self, context):
    obj = context.active_object
    arm = util.get_armature(obj)
    complexity = int(self.ui_complexity)
    if complexity == UI_SIMPLE:
        pass #coming soon

def selectedAddonCallback(self, context):
    preferences = util.getAddonPreferences()
    info = preferences.addonVersion
    if preferences.productName   == 'Avastar':
        info = bl_info['version']
    elif preferences.productName == 'Sparkles':
        import sparkles
        info = sparkles.bl_info['version']
    elif preferences.productName == 'Primstar':
        import primstar
        info = primstar.bl_info['version']
    else:
        return
    version_string = "%s.%s.%s" % (info)
    preferences.addonVersion = version_string


class Avastar(AddonPreferences):


    bl_idname = __name__

    exportImagetypeSelection : EnumProperty(
        items=(
            ('PNG', 'PNG', 'Use PNG image file format for GENERATED images'),
            ('TARGA', 'TGA', 'Use TARGA image file format for GENERATED images'),
            ('JPEG', 'JPG', 'Use JPEG image file format for GENERATED images'),
            ('BMP', 'BMP', 'Use BMP image file format for GENERATED images')),
        name="Format",
        description="Image File type",
        default='PNG')

    import configparser
    config_file = os.path.join(CONFIG_DIR,"credentials.conf")
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):

        config.add_section('credentials')
        if not os.path.exists(CONFIG_DIR):
            print("Create Avastar configuration folder")
            os.makedirs(CONFIG_DIR)
    else:
        print("Read the Addon credentials")
        config.read(config_file)

    log_level : EnumProperty(
        items=(
            ('DEBUG',    'Debug',    'Detailed Programmer Information\nEnable when requested by Support team'),
            ('INFO',     'Info',     'Detailed User Information to Console\nEnable when in need to see more details'),
            ('WARNING',  'Warning',  '(Default) Events which may or may not indicate an Issue\nUsually this is all you need'),
            ('ERROR',    'Error',    'Events which very likely need to be fixed by User'),
            ('CRITICAL', 'Critical', 'Events which certainly need care taking by the Support team')),
        name="Log Level",
        description="Log Level Settings",
        default='WARNING',
        update = configure_log_level)
        
    _username = config.get("credentials","user", fallback="")
    _password = config.get("credentials","pwd",  fallback="")

    username       : StringProperty(
        name       = 'User',
        description="Your Username on the Machinimatrix Website\n\nImportant: This is not your Secondlife User!\nWe recommend that your Machinimatrix account name\nis different from your Avatar name in Secondlife!",
        default    =_username)

    password       : StringProperty(
        name       = 'Pwd',
        subtype='PASSWORD',
        description="Your Password on the Machinimatrix Website\n\nImportant: This is not your Secondlife Password!\nWe recommend that your Machinimatrix account password\nis different from your Password in Secondlife!\nAlso note that the Machinimatrix team will never(!) ask you for any password!",
        default    =_password)
        
    keep_cred       : BoolProperty(
        name        = "Keep Credentials",
        description = "Keep login Credentials on local file for reuse on next start of Blender",
        default     = _username != '')

    server       : StringProperty(
        description="Server")
    page       : StringProperty(
        description="Page")

    user       : StringProperty(
        description="User")
    purchase       :  StringProperty(
        description="Your Account name on the Machininmatrix website")
    version       :  StringProperty(
        description="Version")

    update_status  : EnumProperty(
        items=(
            ('BROKEN', 'Broken', 'We could not setup the Remote caller on your system.\nPlease visit the Machinimatrix website and\ncheck manually for new updates.'),
            ('UNKNOWN', 'Unknown', 'You need to Login at Machinimatrix\nor at least Check for Updates to see your update status'),
            ('UPTODATE', 'Up to date', 'You seem to have already installed the newest product version'),
            ('ONLINE', 'Up to date', 'You have already installed the newest product version'),
            ('CANUPDATE', 'Can Update', 'A newer product version is available (Please login to get the download)'),
            ('UPDATE', 'Update available', 'A newer product version is available for Download'),
            ('ACTIVATE', 'Restart to Activate', 'A new update has been installed, Press F8 or restart Blender to activate'),
            ('READY_TO_INSTALL', 'Update Ready to Install', 'A new update has been downloaded and can now be installed')),
        name="Update Status",
        description="Update Status of your Product",
        default='UNKNOWN')

    ui_complexity  : EnumProperty(
        items=(
            ('0', 'Basic', 'Show the most basic Avastar functions'),
            ('1', 'Advanced', 'Show the most useful Avastar functions'),
            ('2', 'Expert', 'Show expert features'),
            ('3', 'Experimental', 'Show New features, work in progress')),
            name="Addon Complexity",
        description="User Interface Complexity",
        default='2',
        update = ui_complexity_callback)

    initial_rig_mode : EnumProperty(
        items=(
            ('OBJECT', 'Object', 'Create Rig in Object Mode'),
            ('POSE', 'Pose', 'Create Rig in Pose Mode (use Pose&Animation Workflow)'),
            ('EDIT', 'Edit', 'Create Rig in Edit Mode (use Joint Edit Workflow)')),
            name="Initial Rig Mode",
        description="Initial Rig Interaction Mode after creating a new Avastar Rig",
        default='POSE')
        
    update_path : StringProperty(
        description="Path to updated Addon zip file")

    forceImageType : BoolProperty(default=False, name="All",
        description="Enforce selected image format on all exported images")
    useImageAlpha  : BoolProperty(default=False, name="Use RGBA",
        description="Use Alpha Channel if supported by selected image Format")

    precision : IntProperty(
        default=0,
        min=0,
        max=12,
        name="Precision",
        description="Numeric precision used for exporting Collada data\n0: unlimitted precision(default setting)"
    )

    adaptive_iterations : IntProperty(default=10, min=0, max=100, name="Iteration Count",
        description="Number of iterations used at maximum to adapt the sliders to the model's shape" )
    adaptive_tolerance : FloatProperty(name = "Slider Precision %",   min = 0, max = 100, default = 0.0001,
        description="Maximum tolerance for adaptive sliders [0.001-100] %")
    adaptive_stepsize : FloatProperty(name = "Correction Stepsize %", min = 1, max = 100, default = 20,
        description="Stepsize for corrections [0.001-100] %")

    verbose  : BoolProperty(default=True, name="Display additional Help",
        description="Enable display of help links in Panel headers")

    rig_version_check  : BoolProperty(default=True, name="Rig Update Dialog",
        description="Avastar should always be used with the newest rig.\nBy default Avastar checks if all rigs in a Blend file are up to date.\nDisable this option to permanently suppress this check.\nNote: We recommend you keep this option enabled!")

    rig_edit_check  : BoolProperty(default=True, name="System Mesh Check",
        description=Avastar_rig_edit_check_description)

    rig_cache_data : BoolProperty(default=False, name="Cache Rig Data",
        description=Avastar_rig_cache_data_description)

    fix_data_on_upload: BoolProperty(default=True, name="Fix After Load",
        description=Avastar_fix_after_load_description)

    default_attach  : BoolProperty(default=True, name="Attach Sliders by Default",
        description="if set, then sliders get attached by default, when binding a Custom Mesh")

    enable_unsupported  : BoolProperty(default=False, name="Display Unsupported Export Options",
        description="Show Export Options which are not (no longer) supported by Second Life")

    use_asset_library_link : BoolProperty(default=False, name="Link Assets",
        description = "When this option is enabled,\n"
                    + "then the textures and meshes from Avastar's\n"
                    + "Assets library are linked and not attached\n\n"
                    + "Pro: the blend files become much smaller\n"
                    + "Con: You may get errors when sharing the blend files with others\n"
    )

    auto_lock_sl_restpose : BoolProperty(default=True, name="Autolock SL Restpose",
        description = "Automatically lock the Avatar shape\n"
                    + "whenever you select the SL Animesh Restpose (white stickman)\n"
                    + "Note: You can manually unlock the sliders again at any time"
    )

    maxFacePerMaterial : IntProperty(default=21844, min=0, name="Max tri-count per Material",
        description= "Reject export of meshes when the number of triangles\nin any material face (texture face) exceeds this number\n\nNote: The SL Importer starts behaving extremely odd\nwhen this count goes above 21844.\nSet to 0 for disabling the check (not recommended)")

    ticketTypeSelection : EnumProperty( name='Ticket Type', default='bug', items =
        [
        ('bug', 'Bug', 'Bug'),
        ('help', 'Help', 'Help'),
        ('feedback', 'Feedback', 'Feedback'),
        ('feature', 'Feature Request', 'Feature Request'),
        ('refund', 'Refund', 'Refund'),
        ]
    )

    productName     : EnumProperty( name = "Product", items = installedAddonsCallback, update = selectedAddonCallback )

    addonVersion    : StringProperty( name = "Addon",    default = "%s.%s.%s" % (bl_info['version']))
    blenderVersion  : StringProperty( name = "Blender",  default = (bpy.app.version_string))
    operatingSystem : StringProperty( name = "Plattform",default = (bpy.app.build_platform.decode("utf-8")))
    auto_adjust_ik_targets : BoolProperty(
        name = "Adjust IK Targets",
        default = True,
        description = "Automatically adjust the IK targets for Arms, legs and hinds when in Edit mode"
    )

    always_alter_restpose : BoolProperty(
        name="Bind to Visual Pose",
        default=False,
        description="Avastar binds to the T-Pose by default (recommended).\n"\
                    +"Setting this option enforces a Bind to the visual pose.\n"\
                    +"Note: Bind to visual pose disables the Avastar shape\n"\
                    +"until you call the 'Alter to Rest Pose' operator (See documentation)"
    )

    skeleton_file : StringProperty(
        name="Skeleton File",
        default="avatar_skeleton.xml",
        description = "This file defines the Deform Skeleton\n"
                    + "This file is also used in your SL viewer. You find this file in:\n\n"
                    + "{Viewer Installation folder}/character/avatar_skeleton.xml\n\n"
                    + "You must make sure that the Definition file used in Avastar matches\n"
                    + "with the file used in your Viewer.\n\n"
                    + "When you enter a simple file name then Avastar reads the data its own lib subfolder\n"
    )

    lad_file : StringProperty(
        name="Lad File",
        default="avatar_lad.xml",
        description = "This file defines the Avatar shape\n"
                    + "This file is also used in your SL viewer. You find this file in:\n\n"
                    + "{Viewer Installation folder}/character/avatar_lad.xml\n\n"
                    + "You must make sure that the Definition file used in Avastar matches\n"
                    + "with the file used in your Viewer.\n\n"
                    + "When you enter a simple file name then Avastar reads the data its own lib subfolder\n"
    )

    target_system   : EnumProperty(
        items=(
            ('EXTENDED',
                'Extended',
                "Create items for the Second Life Main Grid.\n"
                + "This setting takes care that your creations are working with all \n"
                + "officially supported Bones. (Note: This includes the new Bento Bones as well)"),
            ('BASIC',
                'Basic',
                "Create items using only the SL legacy bones.\n"
                + "This setting takes care that your creations only use\n"
                + "the Basic Boneset (26 bones and 26 Collision Vollumes).\n"
                + "Note: You probably must use this option for creating items for other worlds."),
        ),
        name="Default Target",
        description = "The Rig type that is used by default.\n",
        default     = 'EXTENDED'
    )

    RigType : EnumProperty(
        items=(
            ('BASIC', 'Basic' , 'The Basic Rig supports only the old Bones.\nGood for Main grid and other Online Worlds like OpenSim, etc."'),
            ('EXTENDED', 'Extended'  , 'The Extended Rig supports new Bones for Face, Hands, Wings, and Tail.')),
        name="Rig Type",
        description= "The set of used Bones",
        default='BASIC')

    JointType : EnumProperty(
        items=(
        ('POS',   'Pos' ,    'Create a rig based on the pos values from the avatar skeleton definition\nFor making Cloth Textures for the System Character (for the paranoid user)'),
        ('PIVOT', 'Pivot'  , 'Create a rig based on the pivot values from the avatar skeleton definition\nFor Creating Mesh items (usually the correct choice)')
        ),
        name="Joint Type",
        description= "SL supports 2 Skeleton Defintions.\n\n- The POS definition is used for the System Avatar (to make cloth).\n- The PIVOT definition is used for mesh characters\n\nAttention: You need to use POS if your Devkit was made with POS\nor when you make cloth for the System Avatar",
        default='PIVOT')

    show_panel_collada : BoolProperty(
        default=False,
        name="Collada Panel",
        description="Show the Collada Export Panel in the Tool Shelf"
        )

    show_panel_shape_editor : EnumProperty(
        items =(
        ('N-PANEL',    'N-PANEL' ,           'Show the Shape Editor within the N-Panel'),
        ('PROPERTIES', 'Object Properties' , 'Show the Shape Editor within the Object Proprties Editor'),
        ('BOTH',       'Both' ,              'Show the Shape Editor in N-Panel and in Object properties'),
       ),
        default='N-PANEL',
        name="Avatar Shape",
        description="Define where the Avatar Shape Editor shall be displayed"
        )

    use_safe_names : BoolProperty(
        default=True,
        name="Use Safe Names",
        description="Make safe names for Presets, Action names, Files, etc\n"\
                    +"When disabled: Keep Alphanumeric characters, whitespace, dots and underscores (more user friendly)\n"\
                    +"When enabled : Make cross operating system safe names"
        )

    enable_auto_rig_update : BoolProperty(
        default=True,
        name="Auto Update Rig",
        description="recalculate Avatar Shape Parameters.\n"\
                    +"Detail:\n"\
                    +"Avastar must adjust Avatar shape to the Rig\n"\
                    +"whenever the rig has been edited.\n\n"\
                    +"Enabled: The Slider data gets automatically recalculated.\n"\
                    +"Disabled: You need to use 'Store Joint Edits' (in Posing Panel - Expert mode)"
        )

    enable_auto_mesh_update : BoolProperty(
        default=False,
        name="Auto Repair Mesh",
        description="recalculate reference Mesh for dirty Rig.\n"\
                    +"Detail:\n"\
                    +"Avastar must adjust Reference Meshes to the sliders\n"\
                    +"whenever the mesh has been edited.\n\n"\
                    +"Enabled: The reference Mesh gets automatically recalculated.\n"\
                    +"Disabled: You need to use 'Adjust Reference Mesh' (in skinning Panel)"
        )

    def store_credentials(self):
        print("Storing configuration")
        cp = self.config
        print("Set credentials")

        if self.keep_cred:
            cp.set("credentials","user", self.username)
            cp.set("credentials","pwd", self.password)
        else:
            cp.remove_option("credentials","user")
            cp.remove_option("credentials","pwd")

        print("store credentials")
        with open(self.config_file, 'w+') as configfile:
            print("user:", cp.get("credentials","user", fallback="none"))
            cp.write(configfile)
            print("Done")
            
            
    def draw_create_panel(self, context, box):
    
        sceneProps = context.scene.SceneProp
        last_select = bpy.types.AVASTAR_MT_rig_presets_menu.bl_label
        row = box.row(align=True)

        row.menu("AVASTAR_MT_rig_presets_menu", text=last_select )
        row.operator("avastar.rig_presets_add", text="", icon=ICON_ADD)
        if last_select not in ["Rig Presets", "Presets"]:
            row.operator("avastar.rig_presets_update", text="", icon=ICON_FILE_REFRESH)
            row.operator("avastar.rig_presets_remove", text="", icon=ICON_REMOVE).remove_active = True

        col = box.column(align=True)
        row = col.row(align=True)
        row.label(text='avastarMeshType')#text=propgroups.ScenePropGroup.avastarMeshType[1]['name'])
        row.prop(sceneProps, "avastarMeshType",   text='')

        row = col.row(align=True)
        row.label(text='avastarRigType')#text=propgroups.ScenePropGroup.avastarRigType[1]['name'])
        row.prop(sceneProps, "avastarRigType",   text='')

        row = col.row(align=True)
        row.label(text='avastarJointType')#text=propgroups.ScenePropGroup.avastarJointType[1]['name'])
        row.prop(sceneProps, "avastarJointType",   text='')

    def draw(self, context):
        layout = self.layout

        def create_section_layout(layout, draw_section, box_label, box_icon=None, help_label=None, help_icon=None):

            def draw_label(box, label, icon):
                if icon:
                    box.label(text=label, icon=icon)
                else:
                    box.label(text=label)

            split = layout.split(factor=0.5)
            section_box=split.box()
            draw_label(section_box, box_label, box_icon)
            section_box.alignment='RIGHT'

            help_box=split.box()
            if help_label:
                draw_label(help_box, help_label, help_icon)

            layout.separator()

            draw_section(section_box)
            return section_box, help_box

        def draw_link_section(box):
            col = box.column(align=True)
            col.operator("wm.url_open", text="Avastar Release Info ...", icon=ICON_URL).url=RELEASE_INFO
            col.operator("wm.url_open", text="Reference Guides ...", icon=ICON_URL).url=REFERENCE_GUIDES
            col.operator("wm.url_open", text="Ticket System...", icon=ICON_URL).url=TICKETS

        def draw_general_section(box):
            col = box.column(align=True)
            col.label(text="Initial Rig Mode after create")
            row = col.row(align=True)
            row.prop(self, "initial_rig_mode", expand=True)
            col = box.column(align=True)
            col.prop(self, "verbose")
            col.prop(self, "default_attach")
            col.prop(self, "enable_unsupported")
            col.prop(self, "rig_version_check")
            col.prop(self, "use_safe_names")
            col.prop(self, "rig_edit_check")
            col.prop(self, "enable_auto_rig_update")
            col.prop(self, "enable_auto_mesh_update")

            col.prop(self, "auto_adjust_ik_targets")
            col.prop(self, "use_asset_library_link")
            col.prop(self, "auto_lock_sl_restpose")

            row=col.row(align=True)
            row.alignment='RIGHT'
            row.label(text="Max Tris per Material", icon=ICON_MESH_DATA)
            row.alignment='LEFT'
            row.prop(self, "maxFacePerMaterial", text='')


        def draw_debug_section(box):
            col = box.column(align=True)
            col.prop(self, "rig_cache_data")
            col.prop(self, "fix_data_on_upload")


        def draw_character_section(box):
            self.draw_create_panel(context, box)





        def draw_devkit_section(box):
            scene = context.scene
            kitprop = scene.UpdateRigProp
            brand = kitprop.devkit_brand
            model = kitprop.devkit_snail
            preset_name = "%s - %s" % (brand, model)


            ibox = box.box()
            col = ibox.column()

            row=col.row(align=True)
            row.operator("avastar.import_devkit_configuration", text = "Import Preset(s)", icon=ICON_IMPORT)
            row.prop(kitprop, "devkit_replace_import", toggle=True, text='', icon=ICON_DECORATE_OVERRIDE)

            row=col.row(align=True)
            oprop = row.operator("avastar.export_devkit_configuration", text='Export %s Config'%preset_name, icon = ICON_EXPORT)
            row.prop(kitprop, "devkit_replace_export", toggle=True, text='', icon=ICON_DECORATE_OVERRIDE)

            col = box.column()
            DevkitConfigurationEditor.draw_collapsible(DevkitConfigurationEditor, col)
            if  DevkitConfigurationEditor.visible:
                copyrig.create_devkit_preset(box)
                col.separator()
                draw_devkit_editor(box, kitprop)

        def draw_devkit_editor(layout, kitprop):

            col = layout.column(align=True)
            can_save = os.access(kitprop.devkit_filepath, os.R_OK)
            col.alert = not can_save
            col.label(text="General Info:", icon=ICON_PREFERENCES)
            col.separator()

            col.prop(kitprop, "devkit_filepath", text='filepath')

            col.prop(kitprop, "devkit_brand")
            col.prop(kitprop, "devkit_snail")

            col.separator()
            col.label(text="Rig Configuration:", icon=ICON_BONE_DATA)
            col = layout.column(align=True)
            sp = col.split(factor=0.5)
            sbox = sp.box()
            tbox = sp.box()

            scol = sbox.column()
            scol.label(text="Kit Config")
            scol.prop(kitprop, "srcRigType", text="Rig")
            scol.prop(kitprop, "JointType" , text="Joint")
            scol.prop(kitprop, "up_axis")
            lsplit=scol.split(factor=0.5)
            lsplit.label(text="Scale")
            lsplit.prop(kitprop, "devkit_scale", text='')

            tcol = tbox.column()
            tcol.label(text="Avastar Config:")
            tcol.prop(kitprop, "tgtRigType",   text="Rig")
            tcol.prop(kitprop, "tgtJointType", text="Joint")
            tcol.label(text='Up axis     Z')
            tcol.label(text='Scale     1.0')

            col.separator()
            col.label(text="Rig Options:", icon=ICON_POSE_DATA)
            col.separator()

            split = col.split(factor=0.6)
            cols = split.column()
            cols.prop(kitprop, "devkit_use_sl_head", text="Use SL Head")
            cols.prop(kitprop, "use_male_shape",    text="Use Male Shape")
            cols.prop(kitprop, "use_male_skeleton", text="Use Male Skeleton")
            cols.prop(kitprop, "transferJoints")
            cols.prop(kitprop, "devkit_use_bind_pose")
            cols.prop(kitprop, "sl_bone_ends")
            cols.prop(kitprop, "sl_bone_rolls")
            if kitprop.srcRigType == 'AVASTAR':
                cols.prop(kitprop, "fix_reference_meshes")

            col = layout.column()
            col.enabled = can_save
            row = col.row(align=True)
            prop = row.operator("avastar.devkit_presets_add", text="Add/Replace Devkit Preset")
            row.operator("avastar.devkit_manager_cut_preset", text='', icon=ICON_FREEZE)
            if kitprop.devkit_brand:
                prop.name = "%s - %s" % (kitprop.devkit_brand, kitprop.devkit_snail)
            else:
                prop.name = "%s" % (kitprop.devkit_snail)

        def draw_credentials_section(box):
            irow = box.row(align=False)
            irow.alignment='RIGHT'
            irow.operator("wm.url_open", text="My Machinimatrix Account",icon=ICON_BLANK1,emboss=False).url=AVASTAR_DOWNLOAD
            irow.operator("wm.url_open", text='',icon=ICON_INFO).url=AVASTAR_DOWNLOAD

            col = box.column(align=True)

            col.prop(self,"username", text="user")
            col.prop(self,"password", text="password")
            col.label(text="")

        def draw_panel_visibility_section(box):
            col = box.column()
            col.prop(self, "show_panel_collada", text="Show the Collada Panel")
            row = col.row(align=True)
            row.label(text="Avatar Shape")
            row.prop(self, "show_panel_shape_editor", text="")
            row = col.row(align=True)
            row.label(text="UI Complexity")
            row.prop(self, "ui_complexity", text='')

        def draw_collada_section(box):
            col = box.column()
            col.prop(self, "exportImagetypeSelection", text='Image type', toggle=False, icon=ICON_IMAGE_DATA)
            t = "Use %s for all images" % self.exportImagetypeSelection
            col.prop(self, "forceImageType", text=t, toggle=False)
            col.prop(self, "useImageAlpha", toggle=False)
            col.prop(self, "precision")

        def draw_adaptive_sliders_section(box):
            col = box.column(align=True)
            col.prop(self,"adaptive_tolerance",  slider=True, toggle=False)
            col.prop(self,"adaptive_iterations", slider=True, toggle=False)
            col.prop(self,"adaptive_stepsize",   slider=True, toggle=False)

        def draw_logging_section(box):
            col=box.column(align=True)
            col.template_list('AVASTAR_UL_LoggerPropVarList',
                                    'LoggerPropList',
                                    bpy.context.window_manager,
                                    'LoggerPropList',
                                    bpy.context.window_manager.LoggerIndexProp,
                                    'index',
                                    rows=5)




        section_box, help_box = create_section_layout(
            layout,
            draw_link_section,
            box_label="Links",
            help_label="Links information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_weblinks, SEVERITY_HINT, generate_docu_link=False)




        section_box, help_box = create_section_layout(
            layout,
            draw_general_section,
            box_label="General Settings",
            box_icon=ICON_PREFERENCES,
            help_label="General settings information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_general_settings, SEVERITY_HINT, generate_docu_link=False)





        section_box, help_box = create_section_layout(
            layout,
            draw_debug_section,
            box_label="Debug Settings",
            box_icon=ICON_PREFERENCES,
            help_label="Debug settings information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_debug_settings, SEVERITY_HINT, generate_docu_link=False)





        section_box, help_box = create_section_layout(
            layout,
            draw_character_section,
            box_label="Character definitions",
            box_icon=ICON_PREFERENCES,
            help_label="Character definitions information",
            help_icon='INFO')

        col = help_box.column(align=True)
        prop = col.operator("avastar.rig_presets_reset", text="Reset to Factory Setting")
        prop.category = "rigs"
        util.ErrorDialog.draw_generic(help_box, messages.panel_info_character_presets, SEVERITY_HINT, generate_docu_link=False)





        section_box, help_box = create_section_layout(
            layout,
            draw_devkit_section,
            box_label="Devkit Configurations",
            box_icon=ICON_PREFERENCES,
            help_label="Developerkit information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(
            help_box,
            messages.panel_info_devkit_presets,
            SEVERITY_HINT,
            generate_docu_link=False)




        section_box, help_box = create_section_layout(
            layout,
            draw_credentials_section,
            box_label="User Credentials",
            help_label="Credentials information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_credentials, SEVERITY_HINT, generate_docu_link=False)




        section_box, help_box = create_section_layout(
            layout,
            draw_panel_visibility_section,
            box_label="Panel Visibility",
            box_icon=ICON_HIDE_OFF,
            help_label="Panel Visibility information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_visibility, SEVERITY_HINT, generate_docu_link=False)




        section_box, help_box = create_section_layout(
            layout,
            draw_collada_section,
            box_label="Collada Export Options",
            box_icon='FILE_BLANK',
            help_label="Collada information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_collada, SEVERITY_HINT, generate_docu_link=False)




        section_box, help_box = create_section_layout(
            layout,
            draw_adaptive_sliders_section,
            box_label="Adaptive Sliders Control parameters",
            box_icon=ICON_PREFERENCES,
            help_label="Adaptive Sliders information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_adaptive_sliders, SEVERITY_HINT, generate_docu_link=False)




        section_box, help_box = create_section_layout(
            layout,
            draw_logging_section,
            box_label="Logging Configuration",
            box_icon='TEXT',
            help_label="Logging information",
            help_icon='INFO')

        util.ErrorDialog.draw_generic(help_box, messages.panel_info_logging, SEVERITY_HINT, generate_docu_link=False)


        if bpy.app.version_cycle != 'release':
            box = layout.box()
            box.label(text="Unsupported Blender release type '%s'" % (bpy.app.version_cycle), icon=ICON_ERROR)
            col = box.column(align=True)
            col.label(text = "Your Blender instance is in state '%s'." % (bpy.app.version_cycle), icon=ICON_BLANK1)
            col = col.column(align=True)
            col.label(text = "This Addon might not work in this context.", icon=ICON_BLANK1)
            col = col.column(align=True)
            col.label(text="We recommend to use an official release from Blender.org instead.", icon=ICON_BLANK1)

class AvastarShowPrefs(Operator):
    bl_idname = "avastar.pref_show"
    bl_description = 'Open Avastar addon preferences for customization'
    bl_label = "Avastar Preferences"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        wm = context.window_manager

        mod = importlib.import_module(__package__)
        if mod is None:
            print("Avastar seems to be not enabled or broken in some way")
            return {'CANCELLED'}
        bl_info = getattr(mod, "bl_info", {})
        mod.bl_info['show_expanded'] = True
        preferences = util.getPreferences()
        preferences.active_section = 'ADDONS'
        wm.addon_search = bl_info.get("name", __package__)
        wm.addon_filter = bl_info.get("category", 'ALL')
        wm.addon_support = wm.addon_support.union({bl_info.get("support", 'COMMUNITY')})


        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        return {'FINISHED'}


class DevkitConfigurationEditor (util.ExpandablePannelSection):
    bl_idname = "avastar.devkit_configuration_editor"
    bl_label = "Create/Modify Configuration"


class DownloadReload(bpy.types.Operator):
    bl_idname = "avastar.download_reload"
    bl_label  = "Reload Scripts"
    bl_description = "Reset Blender Python Modules (Like Pressing F8 or restarting Blender)"

    def execute(self, context):
        bpy.ops.preferences.addon_enable(module=__package__)
        addonProps = util.getAddonPreferences()
        addonProps.update_status = 'UNKNOWN'
        return {'FINISHED'}


class DownloadInstall(bpy.types.Operator):
    bl_idname = "avastar.download_install"
    bl_label  = "Install Download"
    bl_description = "Install the just downloaded Avastar Update"

    reset : BoolProperty(default=False, name="Reset",
        description="Reset to not logged in")

    filename_pattern  = re.compile('.*filename.*=\\s*([^;]*);?.*', re.IGNORECASE)
    extension_pattern = re.compile('.*\\.(zip|py)', re.IGNORECASE)

    def install(self, src):
        error_count = 0
        try:
            print ("Install from file",src)

            bpy.ops.preferences.addon_install( overwrite=True,
                    target='DEFAULT',
                    filepath=src,
                    filter_folder=True,
                    filter_python=True,
                    filter_glob="*.py;*.zip")

        except:
            print("Can not install ", src )
            self.report({'ERROR'},("Install to File was interrupted."))
            error_count += 1
            raise

        return error_count

    def execute(self, context):
        props = util.getAddonPreferences()
        if self.reset:
            props.update_status='UNKNOWN'
            return {'FINISHED'}

        if props.update_status != 'READY_TO_INSTALL':
            return {'CANCELLED'}

        if not props.update_path:
            return {'CANCELLED'}

        errcount = 0
        if props.update_path:
            errcount = self.install(props.update_path)
        if errcount == 0:
            props.update_status='ACTIVATE'
            return {'FINISHED'}
        return {'CANCELLED'}

class DownloadReset(bpy.types.Operator):
    bl_idname = "avastar.download_reset"
    bl_label  = "Reset Download"
    bl_description = "Reset this panel to start over again"

    def execute(self, context):
        props = util.getAddonPreferences()
        props.update_status='UNKNOWN'
        return {'FINISHED'}

class DownloadUpdate(bpy.types.Operator):
    bl_idname = "avastar.download_update"
    bl_label  = "Download Update"
    bl_description = "Download Avastar Update from Machinimatrix (Freezes Blender for ~1 minute, depending on your internet)"

    reset : BoolProperty(default=False, name="Reset",
        description="Reset to not logged in")

    filename_pattern  = re.compile('.*filename.*=\\s*([^;]*);?.*', re.IGNORECASE)
    extension_pattern = re.compile('.*\\.(zip|py)', re.IGNORECASE)

    def download(self, props):
        url = "https://"+props.server+props.page
        log.debug("Getting data from server [%s] on page [%s]..." % (props.server,props.page))
        log.debug("Calling URL [%s]" %  url)
        response, extension, filename, code = www.call_url(self, url)

        if response is None:
            log.error("Error while downloading: No valid Response from Server (code %s)" % code )
            return None
        elif filename is None or extension is None:
            log.warning("Got a response but something went wrong with the filename (code %s)" % code )
        else:
            log.debug("Got the download for file [%s] with extension [%s]" % (filename, extension) )

        path = None
        try:

            destination_folder = bpy.app.tempdir
            print("Write to [%s]" % destination_folder)


            path= os.path.join(destination_folder, filename)
            basedir = os.path.dirname(path)
            if not os.path.exists(basedir):
                os.makedirs(basedir)
            f = open(path, "wb")
            b = bytearray(10000)
            util.progress_begin(0,10000)
            while response.readinto(b) > 0:
                f.write(b)
                util.progress_update(1, absolute=False)
            util.progress_end()

            f.close()
        except:
            print("Can not store download to:", path)
            print("system info:", sys.exc_info())
            self.report({'ERROR'},("Download to File was interrupted."))
            path = None
        return path

    def execute(self, context):
        props = util.getAddonPreferences()
        if props.update_status != 'UPDATE':
            return {'CANCELLED'}

        path = self.download(props)
        if path:
            props.update_path = path
            props.update_status = 'READY_TO_INSTALL'
            return {'FINISHED'}
        return {'CANCELLED'}

product_id_map = {
    "Avastar": 759,
    "Primstar": 760,
    "Sparkles": 763
}
        
class CreateReport(bpy.types.Operator):
    bl_idname = "avastar.send_report"
    bl_label  = "Create Report"
    bl_description = "Create a Report and send the data to the Machinimatrix website"

    def execute(self, context):
        import webbrowser
        addonProps = util.getAddonPreferences()
        user             = addonProps.username
        pwd              = addonProps.password

        product_name     = product_id_map[addonProps.productName]
        addon_version    = addonProps.addonVersion
        blender_version  = addonProps.blenderVersion
        ticket_type      = addonProps.ticketTypeSelection
        operating_system = addonProps.operatingSystem
        avatar_name      = addonProps.user if addonProps.user else ""
        title            = ""

        import urllib
        ptmpl = "/avastar/tickets/"\
              + "?wpas_product=%s"\
              + "&wpas_mama_version_number=%s"\
              + "&wpas_mama_blender_version=%s"\
              + "&wpas_mama_ticket_type=%s"\
              + "&wpas_mama_operating_system=%s"\
              + "&wpas_mama_avatar_name=%s"

 
        page = ptmpl % (
               product_name, 
               addon_version,
               blender_version, 
               ticket_type,
               operating_system,
               avatar_name,

        )
        page = urllib.parse.quote_plus('page:%s'%page)

        url = ("https://support.machinimatrix.org/wp-login.php?log=%s&pwd=%s&%s" % (user, pwd, page)).replace("page%3A","page=")
        new = 2

        print("Open page [%s]" % url )
        webbrowser.open(url,new=new)
        return {'FINISHED'}

class CheckForUpdates(bpy.types.Operator):
    bl_idname = "avastar.check_for_updates"
    bl_label  = "Check for Updates"
    bl_description = "Check the Machinimatrix Website for Avastar Update s\n\nNote: The Update Tool does not work for\nDevelopment Releases and Release Candidates"

    def execute(self, context):
        addonProps = util.getAddonPreferences()
        try:
            import xml
            import xmlrpc.client
        except:
            print("xmlrpc: i can not configure the remote call to machinimatrix.")
            print("Sorry, we can not provide this feature on your computer")
            addonProps.update_status = 'BROKEN'
            return {'CANCELLED'}

        ssl_context = www.install_certificates()
        service = xmlrpc.client.ServerProxy(
                      XMLRPC_SERVICE,
                      context= ssl_context,
                      verbose=True )

        user            = addonProps.username
        pwd             = addonProps.password

        addon_version   = util.get_addon_version()
        blender_version = str(get_blender_revision())
        product         = 'Avastar'








        dld = None
        try:
            dld=service.avastar.getPlugin(1,user, pwd, addon_version, blender_version, product)
            if dld[0] in  ['UPDATE','ONLINE']:
                addonProps.update_status = dld[0]
                addonProps.server        = dld[1]
                addonProps.page          = dld[2]
                addonProps.user          = dld[3]
                addonProps.purchase      = dld[4]
                addonProps.version       = dld[5]
                
                addonProps.store_credentials()

            else:
                addonProps.server        = ''
                addonProps.page          = ''
                addonProps.user          = ''
                addonProps.purchase      = ''
                addonProps.version       = ''

        except xml.parsers.expat.ExpatError as err:
            log.error("A Parser Error occured:")
            log.error(err)
        except xmlrpc.client.ProtocolError as err:
            log.error("A protocol error occurred")
            log.error("URL: %s" % err.url)
            log.error("HTTP/HTTPS headers: %s" % err.headers)
            log.error("Error code: %d" % err.errcode)
            log.error("Error message: %s" % err.errmsg)
            dld = None
    
        if dld:
            if dld[0] in ['UNKNOWN','UPTODATE','CANUPDATE', 'UPDATE', 'ONLINE']:
                addonProps.update_status = dld[0]
                addonProps.version       = dld[5]
                return {'FINISHED'}
            else:
                addonProps.update_status = 'UNKNOWN'
                log.error("CheckForUpdates: unknown status [",dld[0],"]")
                return {'CANCELLED'}
        else:
            log.info("heck for Updates cancelled")
            return {'CANCELLED'}


''' class PanelAvastarInfo(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Avastar"

    bl_label = "Avastar %s.%s.%s" % (bl_info['version'])
    bl_idname = "AVASTAR_PT_custom_info"
    bl_options      = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        url = RELEASE_INFO + "?myversion=" + util.get_addon_version() + "&myblender=" + str(get_blender_revision())
        col = layout.column(align=True)
        col.operator("wm.url_open", text="Check for updates", icon=ICON_URL).url=url
'''





def add_rig_preset(context, filepath):
    sceneProps  = context.scene.SceneProp
    file_preset = open(filepath, 'w')
    file_preset.write(
    "import bpy\n"
    "import avastar\n"
    "from avastar import shape, util\n"
    "\n"
    "sceneProps  = bpy.context.scene.SceneProp\n"
    )
    
    file_preset.write("sceneProps.avastarMeshType   = '%s'\n" % sceneProps.avastarMeshType)
    file_preset.write("sceneProps.avastarRigType    = '%s'\n" % sceneProps.avastarRigType)
    file_preset.write("sceneProps.avastarJointType  = '%s'\n" % sceneProps.avastarJointType)
    file_preset.close()


class AVASTAR_MT_rig_presets_menu(Menu):
    bl_label  = "Rig Presets"
    bl_description = "Rig Presets for the Avastar Rig\nHere you define configurations for creating Avastar Rigs.\nYou call your configurations from the the Footer of the 3DView\nNavigate to: Add -> Avastar -> ..."
    preset_subdir = os.path.join("avastar","rigs")
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class AvastarAddPresetRig(AddPresetBase, Operator):
    bl_idname = "avastar.rig_presets_add"
    bl_label = "Add Rig Preset"
    bl_description = "Create new Preset from current Panel settings"
    preset_menu = "AVASTAR_MT_rig_presets_menu"

    preset_subdir = os.path.join("avastar","rigs")

    def invoke(self, context, event):
        print("Create new Preset...")
        return AddPresetBase.invoke(self, context, event)

    def add(self, context, filepath):
        add_rig_preset(context, filepath)

class AvastarUpdatePresetRig(AddPresetBase, Operator):
    bl_idname = "avastar.rig_presets_update"
    bl_label = "Update Rig Preset"
    bl_description = "Update active Preset from current Panel settings"
    preset_menu = "AVASTAR_MT_rig_presets_menu"
    preset_subdir = os.path.join("avastar","rigs")

    def invoke(self, context, event):
        self.name = bpy.types.AVASTAR_MT_rig_presets_menu.bl_label
        print("Updating Preset", self.name)
        return self.execute(context)

    def add(self, context, filepath):
        add_rig_preset(context, filepath)

class AvastarRemovePresetRig(AddPresetBase, Operator):
    bl_idname = "avastar.rig_presets_remove"
    bl_label = "Remove Rig Preset"
    bl_description = "Remove last selected Preset from the list"
    preset_menu = "AVASTAR_MT_rig_presets_menu"
    preset_subdir = os.path.join("avastar","rigs")



class ObjectSelectOperator(bpy.types.Operator):
    bl_idname      = "avastar.object_select_operator"
    bl_label       = "select"
    bl_description = "Select this object as active Object"
    name : StringProperty()

    def execute(self, context):
        if self.name:
           ob = bpy.data.objects[self.name]
           if ob:
               util.object_select_set(bpy.context.object, False)
               util.set_active_object(context, ob)
               util.object_select_set(ob, True)
               util.object_hide_set(ob, False)

        return{'FINISHED'}


class DisplayAvastarVersionOperator(bpy.types.Operator):
    bl_idname      = "avastar.display_version_operator"
    bl_label       = "Avastar"
    bl_description = '''Avastar version used to create this Rig
    
read as Avastar - Version.Minor.Update(Rig ID)

Notes
- The Rig ID can be the same over several Avastar releases.
- Some older rigs display "unknown" for the Version String'''

    name : StringProperty()

    def execute(self, context):
        return{'FINISHED'}


class DisplayAvastarVersionMismatchOperator(bpy.types.Operator):
    bl_idname      = "avastar.version_mismatch"
    bl_label       = "Version Mismatch"
    bl_description = "You probably use a rig from an older Avastar. Click for details"
    msg = 'Version Mismatch|'\
        +  'YOUR ACTION:\n'\
        +  'Upgrade your rig to the current Avastar version.|%s|Rig Migrate ...|'\
        +  '\nDETAIL:\n'\
        +  'Your Rig has been made with a different version of Avastar.\n\n'\
        +  'Please note that a version mismatch could lead to broken functionality.\n'\
        +  'There is a good chance that your rig works, but to keep on the safe side\n'\
        +  'you may want to consider upgrading your rig'

    def execute(self, context):
        txt = self.msg % get_help_page('RIG_MIGRATE')
        util.ErrorDialog.dialog(txt, "INFO")
        return{'FINISHED'}


class DisplayAvastarRigVersionOperator(bpy.types.Operator):
    bl_idname      = "avastar.display_rigversion_operator"
    bl_label       = "Avastar"
    bl_description = '''Rig Version Information
    
Read as: Version.Minor.Update(Rig ID)

Notes
- The Rig ID can be the same over several Avastar releases.
- Some older rigs display "unknown" for the Version String'''

    def execute(self, context):
        return{'FINISHED'}


class WeightAcceptedHint(bpy.types.Operator):
    bl_idname      = "avastar.weight_accept_hint"
    bl_label       = "accepted"
    bl_description = "This is the number of Vertex groups which will be exported as bone weightmaps"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        return{'FINISHED'}

class WeightIgnoredHint(bpy.types.Operator):
    bl_idname      = "avastar.weight_ignore_hint"
    bl_label       = "ignored"
    bl_description = "This is the number of Vertex groups which are associated to non deform Bones. these groups will not be used as weight maps!"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        return{'FINISHED'}

class ShapeTypeMorphHint(bpy.types.Operator):
    bl_idname      = "avastar.shape_type_morph_hint"
    bl_label       = "Shape Type"
    bl_description = '''This is a Morph slider
Affects Morph shapes (Shape keys) of the System Avatar.

Has no effect on Custom Meshes.
Red background indicates edited joints -> changed slider behavior'''

    bl_options = {'REGISTER', 'UNDO'}
    pid : StringProperty()

    def execute(self, context):
        arm=util.get_armature(context.object)
        D = arm.ShapeDrivers.DRIVERS.get(self.pid)[0]
        D['show'] = not D.get('show',False)
        return{'FINISHED'}

class ShapeTypeSystemMorphHint(bpy.types.Operator):
    bl_idname      = "avastar.shape_type_system_morph_hint"
    bl_label       = "Shape Type"
    bl_description = "This is a Morph slider\n"\
                   + "It controls only the Morph shapes (Shape keys) of the System Avatar"
    bl_options = {'REGISTER', 'UNDO'}
    pid : StringProperty()

    def execute(self, context):
        arm=util.get_armature(context.object)
        D = arm.ShapeDrivers.DRIVERS.get(self.pid)[0]
        D['show'] = not D.get('show',False)
        return{'FINISHED'}

class ShapeTypeBoneHint(bpy.types.Operator):
    bl_idname      = "avastar.shape_type_bone_hint"
    bl_label       = "Shape Type"
    bl_description = '''This is a Bone Slider.
Affects Bone length on the System Avatar.
Affects Bone length on Custom Meshes.

Expect equal results for System Avatar and Custom Meshes.
Red background indicates edited joints -> changed slider behavior'''

    bl_options = {'REGISTER', 'UNDO'}
    pid : StringProperty()

    def execute(self, context):
        arm=util.get_armature(context.object)
        D = arm.ShapeDrivers.DRIVERS.get(self.pid)[0]
        D['show'] = not D.get('show',False)
        return{'FINISHED'}

class ShapeTypeExtendedHint(bpy.types.Operator):
    bl_idname      = "avastar.shape_type_extended_hint"
    bl_label       = "Shape Type"
    bl_description = '''This is an Extended Morph Slider
Affects Morph shapes (Shape keys) fn the System Avatar.
Affects Extended Bones on Custom Meshes.

Important: Expect different results for System Avatar and Custom Meshes!
Red background indicates edited joints -> changed slider behavior'''

    bl_options = {'REGISTER', 'UNDO'}
    pid : StringProperty()

    def execute(self, context):
        arm=util.get_armature(context.object)
        D = arm.ShapeDrivers.DRIVERS.get(self.pid)[0]
        D['show'] = not D.get('show',False)
        return{'FINISHED'}

class ShapeTypeFittedHint(bpy.types.Operator):
    bl_idname      = "avastar.shape_type_fitted_hint"
    bl_label       = "Shape Type"
    bl_description = '''This is a Fitted Mesh Slider
Affects Morph shapes on the System Avatar.
Affects Collision Volumes (Fitted Mesh bones) on Custom Meshes.

Important: Expect different results for System Avatar and Custom Meshes.
Red background indicates edited joints -> changed slider behavior'''

    bl_options = {'REGISTER', 'UNDO'}
    pid : StringProperty()

    def execute(self, context):
        arm=util.get_armature(context.object)
        D = arm.ShapeDrivers.DRIVERS.get(self.pid)[0]
        D['show'] = not D.get('show',False)
        return{'FINISHED'}


class FittingTypeHint(bpy.types.Operator):
    bl_idname      = "avastar.fitting_type_hint"
    bl_label       = "Tip: use Slider in Weight Paint mode"
    bl_description = "\n"\
                   + "Bone color:\n"\
                   + "blue  : show mBone weights\n"\
                   + "orange: show Volume Bone Weights\n"\
                   + "\n"\
                   + "Slider value:\n"\
                   + "0.0: Weights on mBone\n"\
                   + "1.0: Weights on Volume Bone\n"\
                   + "\n"\
                   + "Note: Fitted Mesh works best on Custom Bodies.\n"\
                   + "It does not match exactly with the System character"

    def execute(self, context):
        return{'FINISHED'}


class FittingBoneDeletePgroup(bpy.types.Operator):
    bl_idname      = "avastar.fitting_bone_delete_pgroup"
    bl_label       = "Cleanup PGroup"
    bl_description = "Delete Edited Weight distribution"
    
    bname  : StringProperty()

    def execute(self, context):
        obj = context.object
        armobj = obj.find_armature()
        omode = obj.mode if obj.mode != 'EDIT' else util.ensure_mode_is('OBJECT', object=obj)
        if not ( armobj and self.bname in armobj.data.bones):
            print("%s has no armature object using bone %s" % (obj.name, self.bname))
            return {'CANCELLED'}

        active_vertex_group = obj.vertex_groups.active if obj.type == 'MESH' else None
        active_vgroup_name = active_vertex_group.name if active_vertex_group else None

        pgroup = weights.get_pgroup(obj, self.bname)
        if pgroup:
            pgroup.clear()
        
        percent = getattr(obj.FittingValues, self.bname)
        only_selected = False
        weights.set_fitted_strength(context, obj, self.bname, percent, only_selected, omode)
        util.enforce_armature_update(context,armobj)
        util.ensure_mode_is(omode, object=obj)

        if active_vgroup_name:
            log.warning("Set active vgroup to %s" % active_vgroup_name)
            obj.vertex_groups.active = obj.vertex_groups.get(active_vgroup_name)

        return{'FINISHED'}


class FittingBoneSelectedHint(bpy.types.Operator):
    bl_idname      = "avastar.fitting_bone_selected_hint"
    bl_label       = "Distribute Weights"
    bl_description = "Toggle weightmap Display"

    bone  : StringProperty()
    bone2 : StringProperty()
    add   = False

    def invoke(self, context, event):
        self.add = event.shift #SHIFT key is pressed
        return self.execute(context)

    @classmethod
    def description(cls, context, properties):
        bone = properties.bone
        partner = weights.get_bone_partner(bone)

        msg = "\n"\
            + "Click to make this slider ative for distributing\n"\
            + " the weight between these 2 bones:\n\n"\
            + "0.0: all Weight on %s\n" % partner\
            + "1.0: all Weight on %s\n" % bone\
            + "\n"\
            + "Hints:\n"\
            + "- The icon bone color hints which map is currently displayed\n"\
            + "- Click to toggle the weight maps of the bones\n"\
            + "- A pink mesh indicates the weightmap is currently empty\n"\
            + "- ! To see any changes on the model use the Avatar Shape Panel\n"\
            + "- The Fitting panel is best used in Weight Paint Mode"

        return msg

    def execute(self, context):
        obj = context.object
        obj_mode = obj.mode
        armobj = obj.find_armature()
        if not ( armobj and self.bone in armobj.data.bones):
            print("%s has no armature object using bone %s" % (obj.name, self.bone))
            return {'CANCELLED'}
        arm_mode = armobj.mode

        partner_name = self.bone2 if self.bone2 else weights.get_bone_partner(self.bone)
        dbone = armobj.data.bones.get(self.bone)
        pbone = armobj.data.bones.get(partner_name, None) if partner_name else dbone

        if self.add:
            dbone.select = not dbone.select #toggle primary bone
            pbone.select = not dbone.select
        else:
            dselect = not dbone.select
            pselect = not pbone.select
            for db in armobj.data.bones:
                db.select=False
            dbone.select = dselect
            if pbone != dbone:
                pbone.select = not dselect

        ab = pbone if pbone.select else dbone if dbone.select else None
        if ab:
            armobj.data.bones.active = ab
            if ab.name in obj.vertex_groups:
                obj.vertex_groups.active_index=obj.vertex_groups[ab.name].index
            else:
                obj.vertex_groups.active_index=-1
        else:
            obj.vertex_groups.active_index=-1

        selected_bones = [b for b in armobj.data.bones if b.select]
        return{'FINISHED'}


class SynchronizeShapekeyData(bpy.types.Operator):
    bl_idname = "avastar.sync_shapekeys"
    bl_label = "Sync dirty Shapekeys"
    bl_description = '''Manually sync Shape keys with Avatar shape. 
Use when you:
   - changed Avatar shape while editing a shape key
   - renamed your shape keys or modified their order
Tip: Set sliders to white stickman before editing shape keys'''

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        obj = context.object
        return obj is not None and obj.type=='MESH' and util.get_armature(obj)

    def execute(self, context):
        active = context.active_object
        shape.generateMeshShapeData(active)
        return{'FINISHED'}



class ResetShapeSectionOperator(bpy.types.Operator):
    bl_idname      = "avastar.reset_shape_section"
    bl_label       = "Reset Section"
    bl_description = "Reset Section values to SL Default"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        shape.recurse_call = True # Needed to avoid automatic rounding
        active = context.active_object
        omode = util.ensure_mode_is("OBJECT")
        try:
            armobj = util.get_armature(active)
            for pid in shape.get_shapekeys(context, armobj, active):
                if pid != "male_80":
                    D = armobj.ShapeDrivers.DRIVERS[pid][0]
                    shape.setShapeValue(armobj,pid,D['value_default'], D['value_min'], D['value_max'])
            shape.refreshAvastarShape(context)
            util.enforce_armature_update(context, armobj)
        finally:
            shape.recurse_call = False
            util.set_active_object(context, active)
            util.ensure_mode_is(omode)
        return{'FINISHED'}


class ResetShapeValueOperator(bpy.types.Operator):
    bl_idname      = "avastar.reset_shape_slider"
    bl_label       = "Reset Shape"
    bl_description = "Reset Avatar Shape to SL Default"
    bl_options = {'REGISTER', 'UNDO'}

    pid : StringProperty()

    @classmethod
    def description(cls, context, properties):
        armobj = util.get_armature_from_context(context)
        state = pannels.get_slider_state(armobj, properties.pid)

        if state == 'default':
            msg = 'This Slider is at its Default Value (SL Default Shape)'
        elif state == 'cached':
            msg = "This Slider is modified and Cached.\n"\
                + "Click to reset Slider to its Default Value"
        else:
            msg = "This Slider is modified.\n"\
                + "Click to reset Slider to its Default Value"
        return msg

    def execute(self, context):
        shape.recurse_call = True # Needed to avoid automatic rounding
        arms = {}
        active = context.active_object
        omode = util.ensure_mode_is("OBJECT")
        try:
            armobj = util.get_armature(active)
            for pid in shape.get_shapekeys(context, armobj, active):
                if self.pid==pid:
                    D = armobj.ShapeDrivers.DRIVERS[pid][0]
                    shape.setShapeValue(armobj,pid,D['value_default'], D['value_min'], D['value_max'])

            shape.refreshAvastarShape(context, refresh=True)
            util.enforce_armature_update(context, armobj)
        finally:
            shape.recurse_call = False
            util.set_active_object(context, active)
            util.ensure_mode_is(omode)
        return{'FINISHED'}


class ButtonLoadShapeUI(bpy.types.Operator):
    bl_idname = "avastar.load_shape_ui"
    bl_label = "Load Avatar Shape Editor"
    bl_description = "Load the Avastar Shape User Interface (Avatar Shape)"

    def execute(self, context):
        try:
            arm = util.get_armature(context.object)
            rigType = arm.RigProp.RigType
            log.warning("Shape init")
            shape.initialize(rigType)

            if arm:
                use_male_shape = arm.ShapeDrivers.male_80
                propgroups.gender_update(arm, use_male_shape, disable_handler=True)

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonPrintProps(bpy.types.Operator):
    '''
    Write out all the driver values. Currently there is no way to
    import a shape into OpenSim (or similar online worlds) other than manually setting the values
    '''
    bl_idname = "avastar.print_props"
    bl_label = "Write Shape"
    bl_description = "Write shape values into textblock"

    def execute(self, context):
        try:
            obj = util.get_armature(context.active_object)
            name = shape.printProperties(obj)
            self.report({'INFO'}, "See %s textblock"%name)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonSaveProps(bpy.types.Operator):
    '''
    Write out all the driver values. Currently there is no way to
    import a shape into OpenSim (or similar online worlds) other than manually setting the values
    '''
    bl_idname = "avastar.save_props"
    bl_label = "Export Shape"
    bl_description = "Write Shape to file (as xml) or textblock (as txt)"

    filepath : bpy.props.StringProperty(subtype="FILE_PATH", default="")

    check_existing : BoolProperty(name="Check Existing", description="Check and warn on overwriting existing files", default=True)

    destination : g_save_shape_selection 

    filter_glob : StringProperty(
                default="*.xml",
                options={'HIDDEN'},
                )

    def invoke(self, context, event):

        if self.destination=='DATA':
            return self.execute(context)

        try:
            avatarname = context.active_object.name
            name = util.clean_name(avatarname)
            name = util.clean_name(name)

            dirname = os.path.dirname(bpy.data.filepath)
            self.filepath = bpy.path.ensure_ext(os.path.join(dirname,name),".xml")


            wm = context.window_manager
            wm.fileselect_add(self) # will run self.execute()

        except Exception as e:
            util.ErrorDialog.exception(e)

        return {'RUNNING_MODAL'}


    def execute(self, context):
        try:
            obj = util.get_armature(context.active_object)
            if self.destination=='DATA':
                name = shape.printProperties(obj)
                self.report({'INFO'}, "Shape saved to textblock %s"%name)
            else:
                name = shape.saveProperties(obj, self.filepath)
                self.report({'INFO'}, "Shape saved to file %s"%name)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonLoadProps(bpy.types.Operator):
    '''
    Load the shape from the xml file produced for debugging
    (usually: Advanced/Character/Character Tests/Avatar Shape To XML)
    '''
    bl_idname = "avastar.load_props"
    bl_label ="Import Shape"
    bl_description ="Import Shape from file (xml)"

    filepath : StringProperty(name="File Path", description="File path used for importing shape from xml", maxlen=1024, default= "")

    source : g_save_shape_selection 

    def invoke(self, context, event):

        if self.source == 'DATA':
            return self.execute(context)

        try:
            wm = context.window_manager

            wm.fileselect_add(self) # will run self.execute()
            return {'RUNNING_MODAL'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'RUNNING_MODAL'}

    def execute(self, context):
        try:
            armobj = util.get_armature(context.active_object)
            if self.source=='FILE':
                shape.loadProps(context, armobj, self.filepath)
            else:
                blockname = "Shape for: '%s'"%armobj.name 
                shape.loadProps(context, armobj, blockname, pack=True)

            util.enforce_armature_update(context, armobj)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonResetToSLRestPose(bpy.types.Operator):
    '''
    Reset all shape parameters to Second Life Restpose.
    '''
    bl_idname = "avastar.reset_to_restpose"
    bl_label ="Neutral Shape"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description=\
'''Reset Sliders to the SL Neutral Shape

Notes: 
- Please use this option when you create Animesh objects
- This mode is often needed for importing a foreign Devkit'''

    def execute(self, context):
        try:
            context_mode = util.ensure_mode_is("OBJECT")
            context_obj  = context.active_object
            arm = util.get_armature(context.active_object)
            arm.RigProp.Hand_Posture = HAND_POSTURE_DEFAULT
            
            preferences = util.getAddonPreferences()
            auto_lock_sl_restpose = preferences.auto_lock_sl_restpose

            if auto_lock_sl_restpose:
                rig.set_appearance_editable(context, False)


            shape.resetToRestpose(arm, context)

            util.change_active_object(context, context_obj, new_mode=context_mode)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}



class ButtonResetToDefault(bpy.types.Operator):
    '''
    Reset all shape parameters to default values.
    '''
    bl_idname = "avastar.reset_to_default"
    bl_label = "Default Shape"
    bl_description = \
'''Reset Mesh to the SL Default Shape

Use this as the default Shape for making (and animating) characters
Note: This is not Ruth but it is exactly the same as the Default Shape in SL'''

    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            active = context.active_object
            omode = util.ensure_mode_is("OBJECT")
            armobj = util.get_armature(context.active_object)
            util.set_active_object(context, armobj)
            amode = util.ensure_mode_is("OBJECT")

            armobj.RigProp.Hand_Posture = HAND_POSTURE_DEFAULT
            shape.reset_to_default(context)

            util.ensure_mode_is(amode)
            util.set_active_object(context, active)
            util.ensure_mode_is(omode)

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}



class ButtonResetToBindshape(bpy.types.Operator):
    '''
    Reset all shape parameters to bindshape values.
    '''
    bl_idname = "avastar.reset_to_bindshape"
    bl_label = "Bind Shape"
    bl_description = \
'''Reset Mesh to its Bind Shape

The Bindshape is the slider setting that was 
used when you bound your mesh to the armature.

Note: Each mesh has its own bind shape.
We recommend to use the same bindshape
for all bound meshes'''

    bl_options = {'REGISTER', 'UNDO'}

    revert_to_bindshape  : BoolProperty(default=True, name="Revert",
        description="Return back to the original bind shape after cleaning up")

    def draw(self, context):
        box = self.layout.box()
        col = box.column()
        col.label(text="If you want to return to the Bind Shape")
        col.label(text="then enable the Revert option")
        col.separator()
        col.prop(self, "revert_to_bindshape")

    
    def execute(self, context):
        return bind.reset_to_bindshape(context, self.revert_to_bindshape)



class ButtonDeleteAllShapes(bpy.types.Operator):
    '''
    Delete Avastar default shapes.
    '''
    bl_idname = "avastar.manage_all_shapes"
    bl_label ="Manage Avastar Meshes"
    bl_description = "Delete System meshes from the Rig. Use the Redo Panel\n"\
                     "to select which meshes you want to remove"
    bl_options = {'REGISTER', 'UNDO'}

    keep_eyes  : BoolProperty(name="Eyes", default=False, description = 'Keep the Eyes')
    keep_brows : BoolProperty(name="Eye Brows", default=False, description = 'Keep the Eye Brows')
    keep_head  : BoolProperty(name="Head", default=False, description = 'Keep the Head')
    keep_lower : BoolProperty(name="Lower Body", default=False, description = 'Keep the Lower Body')
    keep_upper : BoolProperty(name="Upper Body", default=False, description = 'Keep the Upper Body')
    keep_skirt : BoolProperty(name="Skirt", default=False, description = 'Keep the Skirt')
    keep_hair  : BoolProperty(name="Hair", default=False, description = 'Keep the Hair')

    enable_eyes  : BoolProperty(name="Eyes", default=False, description = 'Enable the Eyes')
    enable_brows : BoolProperty(name="Eye Brows", default=False, description = 'Enable the Eye Brows')
    enable_head  : BoolProperty(name="Head", default=False, description = 'Enable the Head')
    enable_lower : BoolProperty(name="Lower Body", default=False, description = 'Enable the Lower Body')
    enable_upper : BoolProperty(name="Upper Body", default=False, description = 'Enable the Upper Body')
    enable_skirt : BoolProperty(name="Skirt", default=False, description = 'Enable the Skirt')
    enable_hair  : BoolProperty(name="Hair", default=False, description = 'Enable the Hair')

    def draw(self, context):

        layout = self.layout
        box = layout.box()
        box.label(text="Mesh Manager")
        col = box.column(align=True)

        if self.enable_eyes:
            col.prop(self,"keep_eyes")
        if self.enable_brows:
            col.prop(self,"keep_brows")
        if self.enable_head:
            col.prop(self,"keep_head")
        if self.enable_lower:
            col.prop(self,"keep_lower")
        if self.enable_upper:
            col.prop(self,"keep_upper")
        if self.enable_skirt:
            col.prop(self,"keep_skirt")
        if self.enable_hair:
            col.prop(self,"keep_hair")


    def get_mesh_ids(self):
        ids = []
        if self.keep_eyes:
            ids.append('eyeBallRightMesh')
            ids.append('eyeBallLeftMesh')
        if self.keep_brows:
            ids.append('eyelashMesh')
        if self.keep_head:
            ids.append('headMesh')
        if self.keep_lower:
            ids.append('lowerBodyMesh')
        if self.keep_upper:
            ids.append('upperBodyMesh')
        if self.keep_skirt:
            ids.append('skirtMesh')
        if self.keep_hair:
            ids.append('hairMesh')
        return ids

    def has_id(self, arm, key):
        shapes = util.getChildren(arm, type="MESH")
        for child in (child for child in shapes if util.is_avastar_mesh(child)):
            mesh_id = child.get('mesh_id')
            if mesh_id and mesh_id.startswith(key):
                return True
        return False

    def invoke(self, context, event):
        arm=context.object
        self.enable_eyes = self.has_id(arm, 'eyeBall')
        self.enable_brows = self.has_id(arm, 'eyelashMesh')
        self.enable_head = self.has_id(arm, 'headMesh')
        self.enable_lower = self.has_id(arm, 'lowerBodyMesh')
        self.enable_upper = self.has_id(arm, 'upperBodyMesh')
        self.enable_skirt = self.has_id(arm, 'skirtMesh')
        self.enable_hair = self.has_id(arm, 'hairMesh')

        return self.execute(context)

    def execute(self, context):
        try:
            armobj = util.get_armature(context.active_object)
            ids = self.get_mesh_ids()
            shape.manage_avastar_shapes(context, armobj, ids)
        except Exception as e:
            util.ErrorDialog.exception(e)
        return {'FINISHED'}



class ButtonRefreshShape(bpy.types.Operator):
    '''
    Refresh all shape parameters.
    '''
    bl_idname = "avastar.refresh_character_shape"
    bl_label ="Refresh Shape"
    bl_description ="Recalculate Shape of active mesh after modifying weights for Collision Volume Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):    

        arms, objs = util.getSelectedArmsAndObjs(context)

        oselect = util.set_disable_update_slider_selector(True)
        for obj in objs:
            arm = util.get_armature(obj)
            mode = obj.mode
            if context.scene.SceneProp.panel_appearance_enabled:

                shape.refresh_shape(context, arm, obj, graceful=True, only_weights=True)

        util.set_disable_update_slider_selector(oselect)
        
        return{'FINISHED'}







IKMatchDetails = False
class ButtonIKMatchDetails(bpy.types.Operator):
    bl_idname = "avastar.ikmatch_display_details"
    bl_label = ""
    bl_description = "advanced: Hide/Unhide ik bone Rotations display"

    toggle_details_display : BoolProperty(default=False, name="Toggle Details",
        description="Toggle Details Display")

    def execute(self, context):
        global IKMatchDetails
        IKMatchDetails = not IKMatchDetails
        return{'FINISHED'}

class ButtonIKMatchAll(bpy.types.Operator):
    bl_idname = "avastar.ik_match_all"
    bl_label = "Align IK to Pose"
    bl_description = "Align IK bone Rotations of selected Limbs to the current Pose"
    bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(self, context):
        if context == None:
            msg = "avastar.ik_match_all: No context available while polling"
            return False

        ob = context.object
        if ob == None:
            msg = "avastar.ik_match_all: No context object available while polling"
            return False

        if ob.mode != 'POSE':
            msg = "avastar.ik_match_all: Context object [%s] is in[%s] mode (where POSE was needed)" % (ob.name, ob.mode)
            return False

        try:
            if "avastar" in context.active_object:
                return True
        except TypeError:
            msg = "Issues with context object: [%s]" % context.active_object
            return False

    def execute(self, context):
        armobj = context.object
        rig.apply_ik_orientation(context, armobj)
        return{'FINISHED'}


class PanelIKUI(bpy.types.Panel):
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "Rigging"

    bl_label       ="IK Controls"
    bl_idname      = "AVASTAR_PT_ik_ui"

    @classmethod
    def poll(self, context):
        if context.mode != 'POSE':
            return False
        else:
            try:
                if "avastar" in context.active_object:
                    return True
            except TypeError:
                return None

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        active = context.active_object
        arm    = util.get_armature(active) 
        col.prop(active.IKSwitchesProp, "Show_All")

        bones = set([b.name for b in bpy.context.object.pose.bones if b.bone.select or b.sync_influence])


        box = layout.box()
        box.label(text="Target Controls", icon=ICON_OUTLINER_DATA_ARMATURE)

        col = box.column(align=True)
        rig.create_ik_button(col.row(align=True), arm, B_LAYER_IK_HAND)
        rig.create_ik_button(col.row(align=True), arm, B_LAYER_IK_FACE)
        rig.create_ik_button(col.row(align=True), arm, B_LAYER_IK_ARMS)
        rig.create_ik_button(col.row(align=True), arm, B_LAYER_IK_LEGS)
        rig.create_ik_button(col.row(align=True), arm, B_LAYER_IK_LIMBS)
        col.separator()
        col.prop(active.IKSwitchesProp,'snap_on_switch')
        col.separator()

        if active.IKSwitchesProp.Show_All or not bones.isdisjoint(ALL_IK_BONES):
            col = box.column(align=True)
            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(LArmBones):
                try:
                    row = col.row(align=True)
                    con = rig.get_ik_constraint(active.pose.bones, 'ElbowLeft', "ikWristLeft")
                    if con:
                        row.prop(con, "influence", text = 'Left Arm', slider=True)
                        props = row.operator("avastar.ik_apply", text='', icon=ICON_POSE_DATA)
                        props.limb='ARM'
                        props.symmetry='Left'
                except KeyError: pass
            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(RArmBones):
                try:
                    row = col.row(align=True)
                    con = rig.get_ik_constraint(active.pose.bones, 'ElbowRight', "ikWristRight")
                    if con:
                        row.prop(con, "influence", text = 'Right Arm', slider=True)
                        props = row.operator("avastar.ik_apply", text='', icon=ICON_POSE_DATA)
                        props.limb='ARM'
                        props.symmetry='Right'
                except KeyError: pass
            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(LLegBones):
                try:
                    row = col.row(align=True)
                    con = rig.get_ik_constraint(active.pose.bones, 'KneeLeft', "ikAnkleLeft")
                    if con:
                        row.prop(con, "influence", text = 'Left Leg', slider=True)
                        props = row.operator("avastar.ik_apply", text='', icon=ICON_POSE_DATA)
                        props.limb='LEG'
                        props.symmetry='Left'
                except KeyError: pass
            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(RLegBones):
                try:
                    row = col.row(align=True)
                    con = rig.get_ik_constraint(active.pose.bones, 'KneeRight', "ikAnkleRight")
                    if con:
                        row.prop(con, "influence", text = 'Right Leg', slider=True)
                        props = row.operator("avastar.ik_apply", text='', icon=ICON_POSE_DATA)
                        props.limb='LEG'
                        props.symmetry='Right'
                except KeyError: pass

            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(LHindBones):
                try:
                    row = col.row(align=True)
                    con = rig.get_ik_constraint(active.pose.bones, 'HindLimb2Left', "ikHindLimb3Left")
                    if con:
                        row.prop(con, "influence", text = 'Left Hind', slider=True)
                        props = row.operator("avastar.ik_apply", text='', icon=ICON_POSE_DATA)
                        props.limb='HIND'
                        props.symmetry='Left'
                except KeyError: pass

            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(RHindBones):
                try:
                    row = col.row(align=True)
                    con = rig.get_ik_constraint(active.pose.bones, 'HindLimb2Right', "ikHindLimb3Right")
                    if con:
                        row.prop(con, "influence", text = 'Right Hind', slider=True)
                        props = row.operator("avastar.ik_apply", text='', icon=ICON_POSE_DATA)
                        props.limb='HIND'
                        props.symmetry='Right'
                except KeyError: pass

            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(RPinchBones):
                try:

                    col.prop(active.pose.bones['ikThumbSolverRight'],"pinch_influence", text = 'Right Pinch', slider=True)
                except KeyError: pass
            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(LPinchBones):
                try:

                    col.prop(active.pose.bones['ikThumbSolverLeft'],"pinch_influence", text = 'Left Pinch', slider=True)
                except KeyError: pass
            
            if active.IKSwitchesProp.Show_All or not bones.isdisjoint(GrabBones):
                for symmetry in ["Right", "Left"]:
                    col.separator()
                    counter = 0
                    synced  = 0
                    for bone in [bone for bone in bones if bone in GrabBones and bone.endswith(symmetry)]:
                        row = col.row(align=True)
                        i = bone.index("Target")
                        part = bone[2:i]

                        solver = 'ik%sSolver%s' % (part, symmetry)
                        try:
                            bsolver = active.pose.bones[solver]
                            bbone   = active.pose.bones[bone]
                            con  = bsolver.constraints['Grab']
                            txt  = '%s %s' % (symmetry, part)
                            if bbone.sync_influence:
                                lock_icon = ICON_LOCKED
                                synced += 1
                            else:
                                lock_icon = ICON_UNLOCKED
            
                            row.prop(con, "influence", text = txt, slider=True)
                            row.prop(bbone, "sync_influence", text = '', icon = lock_icon, slider=True)
                            counter += 1
                        except KeyError:
                            raise
                            pass
                    if counter > 1 or synced > 1:
                       row=col.row(align=True)
                       row.prop(arm.RigProp,"IKHandInfluence%s" % symmetry, text="Combined", slider=True)

            row = col.row()
            row.label(text="FK")
            row=row.row()
            row.alignment = "RIGHT"
            row.label(text="IK")

        hasLLegBones = not bones.isdisjoint(LLegBones)
        hasRLegBones = not bones.isdisjoint(RLegBones)
        hasLegBones  = hasLLegBones or hasRLegBones

        hasRHindBones = not bones.isdisjoint(RHindBones)
        hasLHindBones = not bones.isdisjoint(LHindBones)
        hasHindBones = hasLHindBones or hasRHindBones

        hasLArmBones = not bones.isdisjoint(LArmBones)
        hasRArmBones = not bones.isdisjoint(RArmBones)
        hasArmBones  = hasLArmBones or hasRArmBones

        hasLPinchBones = not bones.isdisjoint(LPinchBones)
        hasRPinchBones = not bones.isdisjoint(RPinchBones)
        hasGrabBones   = not bones.isdisjoint(GrabBones)
        hasPinchBones  = hasLPinchBones or hasRPinchBones
        hasBones     = hasLegBones or hasArmBones or hasHindBones or hasPinchBones or hasGrabBones

        if active.IKSwitchesProp.Show_All or hasLegBones:
            col = box.column(align=True)
            col.label(text="Foot Pivot:")
            if active.IKSwitchesProp.Show_All or hasLLegBones:
                try:
                    col.prop(active.IKSwitchesProp, "IK_Foot_Pivot_L", text = 'Left Pivot', slider=True)
                except KeyError: pass
            if active.IKSwitchesProp.Show_All or hasRLegBones:
                try:
                    col.prop(active.IKSwitchesProp, "IK_Foot_Pivot_R", text = 'Right Pivot', slider=True)
                except KeyError: pass
            row = col.row()
            row.label(text="Heel")
            row=row.row()
            row.alignment = "RIGHT"
            row.label(text="Toe")

        if active.IKSwitchesProp.Show_All or hasHindBones:
            col = box.column(align=True)
            col.label(text="Hind Foot Pivot:")
            if active.IKSwitchesProp.Show_All or hasLHindBones:
                try:
                    col.prop(active.IKSwitchesProp, "IK_HindLimb3_Pivot_L", text = 'Left Hind Pivot', slider=True)
                except KeyError: pass
            if active.IKSwitchesProp.Show_All or hasRHindBones:
                try:
                    col.prop(active.IKSwitchesProp, "IK_HindLimb3_Pivot_R", text = 'Right Hind Pivot', slider=True)
                except KeyError: pass
            row = col.row()
            row.label(text="Heel")
            row=row.row()
            row.alignment = "RIGHT"
            row.label(text="Toe")

        if active.IKSwitchesProp.Show_All or hasBones:
            icon = util.get_collapse_icon(IKMatchDetails)

            box = layout.box()
            box.label(text="Target align", icon=ICON_MOD_ARMATURE)
            row=box.row(align=True)
            row.operator(ButtonIKMatchDetails.bl_idname, text="", icon=icon)
            row.operator(ButtonIKMatchAll.bl_idname)
            if IKMatchDetails:
                if active.IKSwitchesProp.Show_All or hasArmBones:
                    col = box.column(align=True)
                    col.label(text="IK Wrist Rotation:")
                    if active.IKSwitchesProp.Show_All or hasLArmBones:
                        try:
                            col2 = col.column(align=True)
                            col2.prop(active.IKSwitchesProp, "IK_Wrist_Hinge_L", text = 'Hinge Left', slider=True)
                            row = col2.row(align=True)
                            row.operator(ButtonIKWristLOrient.bl_idname)
                            row.operator(ButtonIKElbowTargetLOrient.bl_idname)
                        except KeyError: pass
                    if active.IKSwitchesProp.Show_All or hasRArmBones:
                        try:
                            col2 = col.column(align=True)
                            col2.prop(active.IKSwitchesProp, "IK_Wrist_Hinge_R", text = 'Hinge Right', slider=True)
                            row = col2.row(align=True)
                            row.operator(ButtonIKWristROrient.bl_idname)
                            row.operator(ButtonIKElbowTargetROrient.bl_idname)
                        except KeyError: pass

                if active.IKSwitchesProp.Show_All or hasLegBones:
                    col = box.column(align=True)
                    col.label(text="IK Ankle Rotation:")
                    if active.IKSwitchesProp.Show_All or hasLLegBones:
                        try:
                            col2 = col.column(align=True)
                            col2.prop(active.IKSwitchesProp, "IK_Ankle_Hinge_L", text = 'Hinge Left', slider=True)
                            row = col2.row(align=True)
                            row.operator(ButtonIKHeelLOrient.bl_idname)
                            row.operator(ButtonIKKneeTargetLOrient.bl_idname)
                        except KeyError: pass
                    if active.IKSwitchesProp.Show_All or hasRLegBones:
                        try:
                            col2 = col.column(align=True)
                            col2.prop(active.IKSwitchesProp, "IK_Ankle_Hinge_R", text = 'Hinge Right', slider=True)
                            row = col2.row(align=True)
                            row.operator(ButtonIKHeelROrient.bl_idname)
                            row.operator(ButtonIKKneeTargetROrient.bl_idname)
                        except KeyError: pass

                if active.IKSwitchesProp.Show_All or hasHindBones:
                    col = box.column(align=True)
                    col.label(text="IK Hind Ankle Rotation:")
                    if active.IKSwitchesProp.Show_All or hasLHindBones:
                        try:
                            col2 = col.column(align=True)
                            col2.prop(active.IKSwitchesProp, "IK_HindLimb3_Hinge_L", text = 'Hinge Left', slider=True)
                            row = col2.row(align=True)
                            row.operator(ButtonIKHindLimb3LOrient.bl_idname)
                            row.operator(ButtonIKHindLimb2TargetLOrient.bl_idname)
                        except KeyError: pass
                    if active.IKSwitchesProp.Show_All or hasRHindBones:
                        try:
                            col2 = col.column(align=True)
                            col2.prop(active.IKSwitchesProp, "IK_HindLimb3_Hinge_R", text = 'Hinge Right', slider=True)
                            row = col2.row(align=True)
                            row.operator(ButtonIKHindLimb3ROrient.bl_idname)
                            row.operator(ButtonIKHindLimb2TargetROrient.bl_idname)
                        except KeyError: pass


        box = layout.box()
        box.label(text="Chain Controls", icon=ICON_OUTLINER_OB_ARMATURE)

        limbBones = util.sym(['Shoulder.','Elbow.','Wrist.','Knee.','Ankle.','Foot.','Toe.', 'Head', 'Neck', 'Chest', 'Spine4', 'Spine3', 'Spine2', 'Spine1', 'Torso'])
        activebone = context.active_pose_bone
        if activebone and activebone.bone.select:
            try:
                con = activebone.constraints.get(TARGETLESS_NAME)
                if not con:
                    return

                if con.use_tail:
                    ii = con.chain_count-1
                else:
                    ii = con.chain_count-1

                chainend = rig.get_bone_recursive(activebone, ii)
                endname = chainend.name

                col = box.column(align=True)
                row = col.row(align=True)
                row.label(text=activebone.name)
                row.label(text='', icon=ICON_ARROW_LEFTRIGHT)
                row.label(text=endname)



                col = box.column(align=True)
                row = col.row(align=True)
                row2 = row.row(align=True)
                row2.operator(ButtonChainParent.bl_idname)
                if activebone.parent==chainend:
                    row2.enabled=False

                row2 = row.row(align=True)
                row2.operator(ButtonChainLimb.bl_idname)
                if activebone.name not in limbBones:
                    row2.enabled = False

                row2 = row.row(align=True)
                row2.operator(ButtonChainCOG.bl_idname)
                if chainend.name=='COG':
                    row2.enabled=False



                row = col.row(align=True)
                row2=row.row(align=True)
                row2.operator(ButtonChainLess.bl_idname)
                if activebone.parent==chainend:
                    row2.enabled=False

                row2=row.row(align=True)
                row2.operator(ButtonChainMore.bl_idname)
                if chainend.name=='COG':
                    row2.enabled=False

                col.label(text='Chain tip movement:')
                row = col.row(align=True)
                row.operator(ButtonChainClamped.bl_idname)
                row.operator(ButtonChainFree.bl_idname)

                col = box.column(align=False)
                col.prop(con,"influence")
            except (AttributeError, IndexError, KeyError):
                raise
                pass



class PanelRigUI(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "Rigging"

    bl_label ="Rig Controls"
    bl_idname = "AVASTAR_PT_rig_ui"

    @classmethod
    def poll(self, context):
        if context.mode != 'POSE':
            return False
        else:
            try:
                if "avastar" in context.active_object:
                    return True
            except TypeError:
                return None

    @staticmethod
    def add_rotation_limits_section(context, layout, armobj):
        meshProp = context.scene.MeshProp
        bones    = set([b.name for b in context.selected_pose_bones])

        box = layout.box()
        box.label(text='Rotation controls', icon=ICON_FILE_REFRESH)
        row = box.row(align=True)
        split = row.split(factor=0.55, align=True)
        split.label(text='Rotation Limits:')
        split.prop(meshProp, "allBoneConstraints", text='All bones', toggle=False)

        current_state, set_state = SLBoneLockRotationLimitStates(armobj, context)
        if current_state != '':
            row = box.row(align=True)



            if current_state == "Some limits":
                lock   = "Enable"
                unlock = "Disable"
            else:
                lock = set_state
                unlock = set_state

            if current_state != "No limits":
                row.operator(ButtonUnsetRotationLimits.bl_idname, text=unlock, icon=ICON_UNLOCKED).all=meshProp.allBoneConstraints
            if current_state != "All limits":
                row.operator(ButtonSetRotationLimits.bl_idname, text=lock, icon=ICON_LOCKED).all=meshProp.allBoneConstraints

        show_all = armobj.IKSwitchesProp.Show_All
        if show_all or not bones.isdisjoint(set(['Head', 'Neck', 'Chest', 'Torso','ShoulderLeft','ShoulderRight'])):
            col = box.column(align=True)
            col.label(text="Inherit Rotation")
            if show_all or not bones.isdisjoint(set(['Head'])):
                PanelRigUI.draw_inherit_rot(armobj, col, 'Head', 'Neck', 'Head')
            if show_all or not bones.isdisjoint(set(['Neck'])):
                PanelRigUI.draw_inherit_rot(armobj, col, 'Neck', 'Chest', 'Neck')
            if show_all or not bones.isdisjoint(set(['Chest'])):
                PanelRigUI.draw_inherit_rot(armobj, col, 'Chest', 'Torso', 'Chest')
            if show_all or not bones.isdisjoint(set(['ShoulderLeft'])):
                PanelRigUI.draw_inherit_rot(armobj, col, 'ShoulderLeft', 'Collar(L)', 'Shoulder(L)')
            if show_all or not bones.isdisjoint(set(['ShoulderRight'])):
                PanelRigUI.draw_inherit_rot(armobj, col, 'ShoulderRight', 'Collar(R)', 'Shoulder(R)')

    @staticmethod
    def draw_inherit_rot(armobj, col, child, parent, label):
        try:
            split = col.split(factor=0.5, align=True)
            split.alignment = 'RIGHT'
            split.label(text=label)
            row = split.row(align=True)
            row.prop(armobj.data.bones[child], "use_inherit_rotation", text = '', icon=ICON_LINKED, toggle=True)
            row.label(text=parent)
        except KeyError: pass

    def draw(self, context):
        layout = self.layout

        active   = context.active_object
        bones    = set([b.name for b in context.selected_pose_bones])


        PanelRigUI.add_rotation_limits_section(context, layout, active)
        
        if "Chest" in active.data.bones and "Torso" in active.data.bones:
            box = layout.box()
            box.label(text="Breathing:", icon=ICON_BOIDS)
            col = box.column(align=True)
            row = col.row(align=True)
            row.operator(ButtonBreatheIn.bl_idname)
            row.operator(ButtonBreatheOut.bl_idname)


class ButtonEnableEyeTarget(bpy.types.Operator):
    bl_idname = "avastar.eye_target_enable"
    bl_label ="Eye Targets"
    bl_description ="Enable Eye Targets"

    def execute(self, context):
        active = context.active_object
        arm = util.get_armature(active)
        rig.setEyeTargetInfluence(arm)
        return {'FINISHED'}





class ButtonIKWristLOrient(bpy.types.Operator):
    bl_idname = "avastar.ik_wrist_l_orient"
    bl_label ="Match Left"
    bl_description ="Match IK to left wrist"

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKWristOrientation(context, arm, 'Left')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKElbowTargetLOrient(bpy.types.Operator):
    bl_idname = "avastar.ik_elbowtarget_l_orient"
    bl_label ="Set Target"
    bl_description ="Reset Left ElbowTarget"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKElbowTargetOrientation(context, arm, 'Left')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}

class ButtonIKWristROrient(bpy.types.Operator):
    bl_idname = "avastar.ik_wrist_r_orient"
    bl_label ="Match Right"
    bl_description ="Match IK to right wrist"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKWristOrientation(context, arm, 'Right')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}



class ButtonIKElbowTargetROrient(bpy.types.Operator):
    bl_idname = "avastar.ik_elbowtarget_r_orient"
    bl_label ="Set Target"
    bl_description ="Reset Right ElbowTarget"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKElbowTargetOrientation(context, arm, 'Right')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKHeelLOrient(bpy.types.Operator):
    bl_idname = "avastar.ik_heel_l_orient"
    bl_label ="Match Left"
    bl_description ="Match IK to left foot"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKAnkleOrientation(context, arm, 'Left')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKKneeTargetLOrient(bpy.types.Operator):
    bl_idname = "avastar.ik_kneetarget_l_orient"
    bl_label ="Set Target"
    bl_description ="Reset Left KneeTarget"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKKneeTargetOrientation(context, arm, 'Left')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKHeelROrient(bpy.types.Operator):
    bl_idname = "avastar.ik_heel_r_orient"
    bl_label ="Match Right"
    bl_description ="Match IK to right foot"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKAnkleOrientation(context, arm, 'Right')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKKneeTargetROrient(bpy.types.Operator):
    bl_idname = "avastar.ik_kneetarget_r_orient"
    bl_label ="Set Target"
    bl_description ="Reset Right KneeTarget"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKKneeTargetOrientation(context, arm, 'Right')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKHindLimb3LOrient(bpy.types.Operator):
    bl_idname = "avastar.ik_hindlimb3_l_orient"
    bl_label ="Match Left"
    bl_description ="Match IK to left Hind foot"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKHindLimb3Orientation(context, arm, 'Left')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKHindLimb2TargetLOrient(bpy.types.Operator):
    bl_idname = "avastar.ik_hindlimb2target_l_orient"
    bl_label ="Set Target"
    bl_description ="Reset Left Hind Target"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKHindLimb2TargetOrientation(context, arm, 'Left')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonIKHindLimb3ROrient(bpy.types.Operator):
    bl_idname = "avastar.ik_hindlimb3_r_orient"
    bl_label ="Match Right"
    bl_description ="Match IK to right Hind foot"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKHindLimb3Orientation(context, arm, 'Right')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}



class ButtonIKHindLimb2TargetROrient(bpy.types.Operator):
    bl_idname = "avastar.ik_hindlimb2target_r_orient"
    bl_label ="Set Target"
    bl_description ="Reset Right Hind Target"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            obj = context.object
            arm = util.get_armature(obj)
            rig.setIKHindLimb2TargetOrientation(context, arm, 'Right')
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}



class ButtonChainMore(bpy.types.Operator):
    bl_idname = "avastar.chain_more"
    bl_label ="More"
    bl_description ="Increase the IK chain length"

    @classmethod
    def get_target_bone_and_chain_len(cls, context):
        activebone = context.active_pose_bone
        con = activebone.constraints[TARGETLESS_NAME]
        if con.use_tail:
            parents = activebone.parent_recursive[con.chain_count-1:]
        else:
            parents = activebone.parent_recursive[con.chain_count:]
        for idx, parent in enumerate(parents):
            if parent.name == 'Origin':

                break
            if parent.lock_ik_x and parent.lock_ik_y and parent.lock_ik_z:

                continue
            chain_count = con.chain_count + idx + 1
            return activebone, parent, chain_count
        return activebone, None, 0

    @classmethod
    def description(cls, context, properties):
        parent = None
        try:
            activebone, parent, chain_count =  ButtonChainMore.get_target_bone_and_chain_len(context)
        except:
            pass
        return ("Increase the IK chain length to %s" % parent.name) if parent else "not applicable"


    def execute(self, context):
        try:
            activebone, parent, chain_count =  ButtonChainMore.get_target_bone_and_chain_len(context)
            if parent:
                con = activebone.constraints[TARGETLESS_NAME]
                con.chain_count = chain_count
        except AttributeError:
            pass
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonChainLess(bpy.types.Operator):
    bl_idname = "avastar.chain_less"
    bl_label ="Less"
    bl_description ="Decrease the IK chain length"


    @classmethod
    def get_target_bone_and_chain_len(cls, context):

        activebone = context.active_pose_bone
        con = activebone.constraints[TARGETLESS_NAME]
        if con.use_tail:
            parents = activebone.parent_recursive[:con.chain_count-2]
        else:
            parents = activebone.parent_recursive[:con.chain_count-1]
        parents.reverse()
        for idx, parent in enumerate(parents):
            if parent.lock_ik_x and parent.lock_ik_y and parent.lock_ik_z:

                continue
            chain_len = con.chain_count - idx - 1
            return activebone, parent, chain_len
        return activebone, None, 0
        

    @classmethod
    def description(cls, context, properties):
        parent = None
        try:
            activebone, parent, chain_count =  ButtonChainLess.get_target_bone_and_chain_len(context)
        except:
            pass
        return ("Decrease the IK chain length to %s" % parent.name) if parent else "not applicable"

    def execute(self, context):
        try:
            activebone, parent, chain_count =  ButtonChainLess.get_target_bone_and_chain_len(context)
            if parent:
                con = activebone.constraints[TARGETLESS_NAME]
                con.chain_count = chain_count
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonChainCOG(bpy.types.Operator):
    bl_idname = "avastar.chain_cog"
    bl_label = "COG"
    bl_description = "Increase the IK chain length to COG"

    def execute(self, context):
        try:
            obj = context.active_object

            activebone = context.active_pose_bone
            try:
                for ii,bone in enumerate(activebone.parent_recursive):
                    if bone.name == 'COG':
                        break
                con = activebone.constraints[TARGETLESS_NAME]
                if con.use_tail:
                    con.chain_count = ii+2
                else:
                    con.chain_count = ii+1

            except AttributeError:
                pass

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonChainParent(bpy.types.Operator):
    bl_idname = "avastar.chain_parent"
    bl_label ="Parent"
    bl_description ="Set the IK chain length to 1 (parent of active bone)"

    @classmethod
    def description(cls, context, properties):
        return ("Set the IK chain length to %s" %  context.active_pose_bone.parent.name)

    def execute(self, context):
        try:
            obj = context.active_object

            activebone = context.active_pose_bone
            try:
                con = activebone.constraints[TARGETLESS_NAME]
                if con.use_tail:
                    con.chain_count = 2
                else:
                    con.chain_count = 1
                if activebone.parent.name in util.sym(['CollarLink.']):

                    con.chain_count += 1
                elif activebone.parent.name in util.sym(['HipLink.']):

                    con.chain_count += 2
                elif activebone.parent.name in util.sym(['Pelvis']):


                    con.chain_count += 1
            except AttributeError:
                pass

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonChainLimb(bpy.types.Operator):
    bl_idname = "avastar.chain_limb"
    bl_label ="Limb"
    bl_description ="Set the IK chain length to base of limb"

    @classmethod
    def get_target_bone_and_chain_len(cls, context):

        LArmBones = set(['CollarLeft','ShoulderLeft','ElbowLeft','WristLeft'])
        RArmBones = set(['CollarRight','ShoulderRight','ElbowRight','WristRight'])
        LLegBones = set(['HipLeft','KneeLeft','AnkleLeft','FootLeft','ToeLeft'])
        RLegBones = set(['HipRight','KneeRight','AnkleRight','FootRight','ToeRight'])

        activebone = context.active_pose_bone
        limb_root = None
        chain_count = 0

        con = activebone.constraints[TARGETLESS_NAME]

        if activebone.name in LArmBones:

            for ii,bone in enumerate(activebone.parent_recursive):
                if bone.name == 'CollarLeft':
                    limb_root = bone
                    break
            if con.use_tail:
                chain_count = ii+2
            else:
                chain_count = ii+1
        if activebone.name in RArmBones:

            for ii,bone in enumerate(activebone.parent_recursive):
                if bone.name == 'CollarRight':
                    limb_root = bone
                    break
            if con.use_tail:
                chain_count = ii+2
            else:
                chain_count = ii+1
        if activebone.name in LLegBones:

            for ii,bone in enumerate(activebone.parent_recursive):
                if bone.name == 'HipLeft':
                    limb_root = bone
                    break
            if con.use_tail:
                chain_count = ii+2
            else:
                chain_count = ii+1
        if activebone.name in RLegBones:

            for ii,bone in enumerate(activebone.parent_recursive):
                if bone.name == 'HipRight':
                    limb_root = bone
                    break
            if con.use_tail:
                chain_count = ii+2
            else:
                chain_count = ii+1

        return activebone, limb_root, chain_count


    @classmethod
    def description(cls, context, properties):
        activebone, limb_root, chain_count = ButtonChainLimb.get_target_bone_and_chain_len(context)
        return ("Set the IK chain length to %s" %  limb_root.name) if limb_root else "not applicable"


    def execute(self, context):
        try:
           activebone, limb_root, chain_count = ButtonChainLimb.get_target_bone_and_chain_len(context)
           if limb_root:
                con = activebone.constraints[TARGETLESS_NAME]
                con.chain_count = chain_count
        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}



class ButtonChainFree(bpy.types.Operator):
    bl_idname = "avastar.chain_free"
    bl_label ="Free"
    bl_description ="Configure so chain tip moves as part of chain"

    def execute(self, context):
        try:
            activebone = context.active_pose_bone
            try:
                con = activebone.constraints[TARGETLESS_NAME]
                m = activebone.matrix.copy()
                if con.use_tail == False:
                    con.chain_count = con.chain_count+1
                con.use_tail = True

                context.active_bone.use_inherit_rotation = True
                util.update_view_layer(context)
                activebone.matrix = m

            except AttributeError:
                pass

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonChainClamped(bpy.types.Operator):
    bl_idname = "avastar.chain_clamped"
    bl_label ="Clamped"
    bl_description ="Configure so chain tip moves as if clamped to current orientation"

    def execute(self, context):
        try:
            activebone = context.active_pose_bone
            try:
                con = activebone.constraints[TARGETLESS_NAME]
                m = activebone.matrix.copy()
                if con.use_tail == True:
                    con.chain_count = con.chain_count-1
                con.use_tail = False

                context.active_bone.use_inherit_rotation = False
                util.update_view_layer(context)
                activebone.matrix = m

            except AttributeError:
                pass

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


def SLBoneLockRotationLimitStates(armobj, context):
    all = context.scene.MeshProp.allBoneConstraints
    if all:
        bones = armobj.pose.bones
    else:
        bones = context.selected_pose_bones
    try:
        limit_count = 0
        free_count  = 0
        part_count  = 0

        if len(bones) == 0:
            return '',''

        for b in bones:
            for c in b.constraints:
                if c.type =='LIMIT_ROTATION':
                    if c.influence == 1:
                        limit_count += 1
                    elif c.influence == 0:
                        free_count += 1
                    else:
                        part_count +=1

        if free_count==0 and part_count == 0:
            return 'All limits', 'Disable rotation limits'
        if limit_count == 0 and part_count == 0:
            return 'No limits', 'Enable rotation limits'
        return 'Some limits', ''
    except:
        pass
    return '',''



class ButtonSetRotationLimits(bpy.types.Operator):
    bl_idname = "avastar.set_rotation_limits"
    bl_label ="Set"
    bl_description ="Set rotation limits on selected joints (if defined)"
    bl_options = {'REGISTER', 'UNDO'}

    all : BoolProperty(default=False)

    def execute(self, context):
        try:
            arm = util.get_armature(context.active_object)
            rig.set_bone_rotation_limit_state(arm, True, self.all)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonUnsetRotationLimits(bpy.types.Operator):
    bl_idname = "avastar.unset_rotation_limits"
    bl_label ="Unset"
    bl_description ="Unset rotation limits on selected joints (if defined)"
    bl_options = {'REGISTER', 'UNDO'}
    
    all : BoolProperty(default=False)

    def execute(self, context):
        try:
            arm = util.get_armature(context.active_object)
            rig.set_bone_rotation_limit_state(arm, False, self.all)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}

class ButtonBreatheIn(bpy.types.Operator):
    '''
    Move chest and torso for in breath
    (movement is subtle - hit repeatedly for stronger effect)
    '''
    bl_idname = "avastar.breathe_in"
    bl_label ="In"
    bl_description ="Move Chest and Torso for in-breath"



    def execute(self, context):
        try:
            armobj = util.get_armature(context.active_object)
            set_breath(armobj, -1.0)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonBreatheOut(bpy.types.Operator):
    '''
    Move chest and torso for out breath
    (movement is subtle - hit repeatedly for stronger effect)
    '''
    bl_idname = "avastar.breathe_out"
    bl_label ="Out"
    bl_description ="Move Chest and Torso for out-breath"



    def execute(self, context):
        try:
            armobj = util.get_armature(context.active_object)
            set_breath(armobj, 1.0)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}

def set_breath(armobj, f):
    thetac=0.010
    try:
        chest  = armobj.pose.bones.get('Chest')
        torso  = armobj.pose.bones.get('Torso')
        thetat = asin(chest.length/torso.length* sin(thetac))
        chest.rotation_quaternion = chest.rotation_quaternion @ Quaternion((1, f * (thetac+thetat),0,0))
        torso.rotation_quaternion = torso.rotation_quaternion @ Quaternion((1,-f * thetat,0,0))
    except KeyError:

        pass
    return




class PanelExpressions(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_category    = "Rigging"

    bl_label ="Expressions"
    bl_idname = "AVASTAR_PT_expressions"
    bl_context = 'object'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        try:
            return "avastar" in context.active_object
        except TypeError:
            return None

    def draw(self, context):
        layout = self.layout
        obj    = context.active_object
        arm    = util.get_armature(obj)
        meshes = util.findAvastarMeshes(obj)

        props = arm.RigProp
        layout.prop(props, "Hand_Posture", text='Hands')

        col = layout.column(align=True)
        for key,label in (("express_closed_mouth_300", "Closed Mouth"),
                            ("express_tongue_out_301", "Tongue Out"),
                            ("express_surprise_emote_302", "Surprise"),
                            ("express_wink_emote_303", "Wink"),
                            ("express_embarrassed_emote_304", "Embarrassed"),
                            ("express_shrug_emote_305", "Shrug"),
                            ("express_kiss_306", "Kiss"),
                            ("express_bored_emote_307", "Bored"),
                            ("express_repulsed_emote_308", "Repulsed"),
                            ("express_disdain_309", "Disdain"),
                            ("express_afraid_emote_310", "Afraid"),
                            ("express_worry_emote_311", "Worry"),
                            ("express_cry_emote_312", "Cry"),
                            ("express_sad_emote_313", "Sad"),
                            ("express_anger_emote_314", "Anger"),
                            ("express_frown_315", "Frown"),
                            ("express_laugh_emote_316", "Laugh"),
                            ("express_toothsmile_317", "Toothy Smile"),
                            ("express_smile_318", "Smile"),
                            ("express_open_mouth_632", "Open Mouth")):

            try:
                col.prop(meshes["headMesh"].data.shape_keys.key_blocks[key], "value", text=label)
            except (KeyError, AttributeError): pass

        col = layout.column(align=True)
        col.label(text="Non animatable in world")
        for key,label in (("furrowed_eyebrows_51", "Furrowed Eyebrows"),
                            ("surprised_eyebrows_53", "Surprised Eyebrows"),
                            ("worried_eyebrows_54", "Worried Eyebrows"),
                            ("frown_mouth_55", "Frown Mouth"),
                            ("smile_mouth_57", "Smile Mouth"),
                            ("blink_left_58", "Blink Left"),
                            ("blink_right_59", "Blink Right"),
                            ("lipsync_aah_70", "Lipsync Aah"),
                            ("lipsync_ooh_71", "Lipsync Ooh")):
            try:
                col.prop(meshes["headMesh"].data.shape_keys.key_blocks[key], "value", text=label)
            except (KeyError, AttributeError): pass



class ButtonCustomShape(bpy.types.Operator):
    bl_idname = "avastar.use_custom_shapes"
    bl_label ="Custom Shapes"
    bl_description ="Use custom shapes for controls"

    def execute(self, context):
        try:
            active = context.active_object

            active.data.show_bone_custom_shapes = True
            util.object_show_in_front(active, False)

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonStickShape(bpy.types.Operator):
    bl_idname = "avastar.use_stick_shapes"
    bl_label ="Stick Shapes"
    bl_description ="Use stick shapes for controls"

    def execute(self, context):
        try:
            active = context.active_object

            active.data.show_bone_custom_shapes = False
            util.object_show_in_front(active, True)
            armature_util.set_display_type(active, 'STICK')

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}




class PanelAnimationExport(bpy.types.Panel):
    '''
    Panel to control the animation export. SL parameters such as hand posture
    are set here.
    '''
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_category    = "Retarget"

    bl_label ="Animation Export"
    bl_idname = "AVASTAR_PT_animation_export"
    bl_context = 'render'

    @classmethod
    def poll(self, context):
        '''
        This panel will only appear if the object has a
        Custom Property called "avastar" (value doesn't matter)
        and when the active object has animation data to be exported
        '''
        try:
            arm = context.active_object
            return arm and arm.type=='ARMATURE' and "avastar" in arm
        except (TypeError, AttributeError):
            return False
    
        return False

    def draw(self, context):

        def get_fcurve(armobj, bname):
            if not armobj:
                return None
            animation_data = armobj.animation_data
            if not animation_data:
                return None
            action = animation_data.action
            if not action:
                return None
            groups = action.groups
            if not groups:
                return None
            fc = groups.get(bname)
            return fc

        ui_level = util.get_ui_level()
        layout = self.layout
        scn = context.scene

        obj   = context.active_object
        armobj= util.get_armature(obj)
        is_bulk_export = armobj.AnimProp.selected_actions

        animation_data = armobj.animation_data
        if animation_data is None or animation_data.action is None:
            active_action = None
            props = armobj.AnimProp
            startprop = scn
            endprop = scn
            fpsprop = scn.render
            is_nla_export = animation_data != None and len(animation_data.nla_tracks) >0
        else:
            is_nla_export = False
            active_action = animation_data.action
            props = active_action.AnimProp
            startprop = props
            endprop = props
            fpsprop = props    

        layout.prop(props, "Mode")
        export_type = 'NLA' if is_nla_export else 'Bulk' if is_bulk_export else 'Action'
        col = layout.column(align=True)
        col.label(text="%s Export options" % export_type)

        col.enabled = not is_bulk_export
        col.prop(fpsprop, "fps", text="fps")
        row = col.row(align=True)

        row.prop(startprop,"frame_start")
        if active_action:
            row.operator("avastar.action_trim",text='', icon=ICON_AUTO)
        row.prop(endprop,"frame_end")
        col = layout.column(align=True)
        col.prop(scn.SceneProp,"loc_timeline")
        col.enabled = active_action != None

        box = layout.box()
        if props.Mode == 'anim':
            box.label(text="Anim Export Options")
            col = box.column(align=True)
            row = col.row(align=True)
            row.prop(props,"Ease_In")
            row.prop(props,"Ease_Out")
            col.prop(props,"Priority")

            box.label(text="Loop Settings")
            col = box.column()
            col.prop(props,"Loop", text="Loop animation")
            row = col.row(align=True)
            row.prop(props,"Loop_In", text="In")
            row.prop(props,"Loop_Out", text="Out")
        if props.Mode == 'bvh':
            box.label(text='BVH settings')
            col = box.column(align=True)
            col.prop(props,"with_reference_frame")
            if props.with_reference_frame:
                col.prop(props, "with_bone_lock")

            if ui_level > 2:
                col.prop(props,"with_pelvis_offset")

        layout.prop(props,"Basename")
        layout.prop(scn.MeshProp, "apply_armature_scale", toggle=False)
        layout.prop(props,"Translations")

        ac = len(bpy.data.actions)
        exporting = 1

        if ac > 1:
            exporting = [a for a in bpy.data.actions if a.AnimProp.select]
            row=layout.row(align=True)
            row.prop(armobj.AnimProp, "selected_actions")
            if armobj.AnimProp.selected_actions:
                row.prop(armobj.AnimProp,"toggle_select")
                layout.template_list('AVASTAR_UL_ExportActionsPropVarList',
                                 'ExportActionsList',
                                 bpy.data,
                                 'actions',
                                 context.scene.ExportActionsIndex,
                                 'index',
                                 rows=5)

        row = layout.row()

        animation_data = armobj.animation_data

        origin_animated = False
        if not armobj.AnimProp.selected_actions:
            origin_fc = get_fcurve(armobj, 'Origin')
            if origin_fc:
                origin_animated = any(not c.mute for c in origin_fc.channels )

        no_keyframes = animation_data is None or (animation_data.action is None and len(animation_data.nla_tracks)==0)

        row_enabled = True
        row_alert = False
        warn=None
        if armobj.AnimProp.selected_actions:
                anim_exporter = "avastar.export_bulk_anim"
                text = "Bulk Export (%d/%d Actions)" % (len(exporting), ac)
        else:
            dirname, name = ExportAnimOperator.get_export_name(armobj)        
            anim_exporter = "avastar.export_single_anim"
            text = "Export: %s" % name
            if no_keyframes:
                warn = "No keyframes to export!"
                row_enabled = False
                row_alert = True
            elif origin_animated:
                if util.get_ui_level() < UI_ADVANCED:
                    warn = "Origin is animated!"
                    row_enabled = False
                else:
                    warn = "Note: Origin animated (bad!)"
                row_alert = True

        row.alert = row_alert
        row.enabled = row_enabled
        row.operator(anim_exporter, text=text, icon=ICON_RENDER_ANIMATION)
        if warn:
            col=layout.column(align=True)
            col.alert=True
            col.label(text=warn)
 
        if props.Mode == 'bvh':

            if props.with_reference_frame:
                start = scn.frame_start
            else:

                start = scn.frame_start + 1
            frames = scn.frame_end-start
            if frames > 0:
                percent_in = round(100*(2+props.Loop_In-start)/float(2+frames),3)
                percent_out = round(100*(2+props.Loop_Out-start)/float(2+frames),3)
            elif props.Loop_In==start:
                percent_in = 0
                percent_out = 100
            else:
                percent_in = 0
                percent_out = 0

            box = layout.box()
            box.label(text="Loop % calculator")
            col = box.column()

            row = col.row(align=True)
            row.prop(props,"Loop_In", text="In")
            row.prop(props,"Loop_Out", text="Out")

            row = col.row(align=True)
            row.label(text="%.3f%%"%percent_in)
            row.label(text="%.3f%%"%percent_out)
            col.label(text="Use the %values")
            col.label(text="as Loop In/Out setting")
            col.label(text="during BVH upload to SL")



class ExportAnimOperator(bpy.types.Operator):
    '''
    Export the animation
    '''
    bl_idname = "avastar.export_anim"
    bl_label = "Export Animation"
    bl_description = \
'''Export Animation (as .anim or .bvh)

- Need one or more Keyframes
- Origin Bone not animated or muted

Note: The .anim format is the SL internal format'''

    check_existing : BoolProperty(name="Check Existing", description="Check and warn on overwriting existing files", default=True)

    @staticmethod
    def get_export_name(armobj):
        if armobj == None:
            raise
        animation_data = armobj.animation_data
        if animation_data == None:
            return "", ""

        action = animation_data.action
        if action:
            actionname = action.name
            animProps = action.AnimProp
        else:
            if len(animation_data.nla_tracks)==0:
                return "", ""
            actionname = "%s-NLA" % armobj.name
            animProps = armobj.AnimProp

        mode = animProps.Mode
        priority = animProps.Priority if mode != 'bvh' else 3
        ease_in = animProps.Ease_In if mode != 'bvh' else 0.8
        ease_out = animProps.Ease_Out if mode != 'bvh' else 0.8
        loop_in = animProps.Loop_In if mode != 'bvh' else 0
        loop_out = animProps.Loop_Out if mode != 'bvh' else 0
        avatarname = armobj.name

        sub = {
        'action':actionname,
        'avatar':avatarname,
        'fps':bpy.context.scene.render.fps,
        'start':bpy.context.scene.frame_start,
        'end':bpy.context.scene.frame_end,
        'prio':priority,
        'easein':int(1000*ease_in),
        'easeout':int(1000*ease_out),
        'loopin':loop_in,
        'loopout':loop_out
        }

        basename = animProps.Basename

        dirname = os.path.dirname(bpy.data.filepath)

        name = string.Template(basename).safe_substitute(sub)
        name = util.clean_name(name)
        
        return dirname, name


    def invoke(self, context, event):
        log.warning("Invoke avastar.export_anim...")
        obj       = context.active_object
        armobj    = util.get_armature(obj)
        action    = armobj.animation_data.action
        animProps = armobj.animation_data.action.AnimProp if action else armobj.AnimProp
        mode      = animProps.Mode

        try:
            dirname, name = ButtonExportAnim.get_export_name(armobj)

            if armobj.AnimProp.selected_actions:
                self.directory = ''
                pass
            else:
                if mode=='bvh':
                    self.filepath = bpy.path.ensure_ext(os.path.join(dirname,name),".bvh")
                    self.filename_ext = ".bvh"
                    self.filter_glob = "*.bvh"
                else:
                    self.filepath = bpy.path.ensure_ext(os.path.join(dirname,name),".anim")
                    self.filename_ext = ".anim"
                    self.filter_glob = "*.anim"

            wm = context.window_manager

            wm.fileselect_add(self) # will run self.execute()
            return {'RUNNING_MODAL'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'RUNNING_MODAL'}

    def execute(self, context):

        def get_active_action(arm_obj):
            animation_data = arm_obj.animation_data
            if not animation_data:
                return None

            active_action = animation_data.action
            if not active_action:
                return None

            return None if animation_data.is_property_readonly('action') else active_action

        log.warning("Execute avastar.export_anim...")
        active = context.active_object
        amode = active.mode
        armobj = util.get_armature(active)

        try:
            active_action = get_active_action(armobj)
            animProps = armobj.animation_data.action.AnimProp if active_action else armobj.AnimProp
            basename = animProps.Basename
            mode = animProps.Mode
            scn = context.scene

            if armobj.AnimProp.selected_actions:
                filepath = self.directory
            else:
                filepath = self.filepath
                filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
            util.set_active_object(context, armobj)
            omode = util.ensure_mode_is("POSE")
            oscenedata = [scn.frame_start, scn.frame_end, scn.render.fps]

            if armobj.AnimProp.selected_actions:
                log.info("Bulk export %d actions" % len([a for a in bpy.data.actions if a.AnimProp.select]) )
            else:

                for action in bpy.data.actions:
                    action.AnimProp.select = (action == active_action)
                    if action.AnimProp.select:
                        log.debug("Marked single action [%s] for export" % (action.name) )

            if active_action or armobj.AnimProp.selected_actions:

                def get_frinfo(action, bulk, scn):
                    if bulk:

                        fr = action.frame_range
                        start = fr[0]
                        end = fr[1]
                    else:
                        start = action.AnimProp.frame_start
                        end = action.AnimProp.frame_end

                    fps = action.AnimProp.fps
                    

                    if fps == -2:
                        fps = scn.render.fps
                    if start == -2:
                        start = scn.frame_start
                    if end == -2:
                        end = scn.frame_end

                    return start, end, fps

                for action in [action for action in bpy.data.actions if action.AnimProp.select]:
                    armobj.animation_data.action = action
                    fr = action.frame_range
                    s, e, f = get_frinfo(action, armobj.AnimProp.selected_actions, scn)
                    scn.frame_start = s
                    scn.frame_end = e
                    scn.render.fps = f
                    action.AnimProp.Basename = basename
                    unused_dir, filename = ExportAnimOperator.get_export_name(armobj)
                    path = "%s/%s.%s" % (filepath, filename, mode) if armobj.AnimProp.selected_actions else filepath
                    animation.exportAnimation(context, action, path, mode)

            else:
                log.info("NLA Export to %s" % filepath)
                animation.exportAnimation(context, None, filepath, mode)

            scn.frame_start = oscenedata[0]
            scn.frame_end = oscenedata[1]
            scn.render.fps = oscenedata[2]

            if active_action:
                armobj.animation_data.action = active_action
            
            util.ensure_mode_is(omode)
            util.set_active_object(context, active)
            util.ensure_mode_is(amode)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e, context)
            return{'FINISHED'}

class ButtonExportAnim(ExportAnimOperator):
    '''
    Export the animation
    '''
    bl_idname = "avastar.export_single_anim"
    bl_label ="Export Animation"
    bl_description = \
'''Export Single Animation (as .anim or .bvh)

- Exports only if Keyframes found in Timeline
- Please mute Origin Bone animation when exists (see dope sheet) 

Note: The .anim format is the SL internal format'''

    filename_ext = ""
    filepath : bpy.props.StringProperty(
               description="Animation File Name",
               subtype="FILE_PATH", 
               default="*.bvh;*.anim")

    filter_glob : StringProperty(
        default="",
        options={'HIDDEN'},
    )

    use_filer = True
    use_filter_folder = True

class ButtonExportBulkAnim(ExportAnimOperator):
    '''
    Export the animation
    '''
    bl_idname = "avastar.export_bulk_anim"
    bl_label ="Export Animations"
    bl_description = \
'''Export A set of Actions (as .anim or .bvh)

Then the Origin Bone is muted to prevent unintentional export of Origin animations

Note: The .anim format is the SL internal format'''

    directory : bpy.props.StringProperty(
               description="Animation export folder name",
               subtype="DIR_PATH", 
               default="")

    filter_glob : StringProperty(
        default="",
        options={'HIDDEN'},
    )

    use_filer = False
    use_filter_folder = False





@persistent
def fix_bone_layers_on_update(scene):

    if util.handler_can_run(scene, check_ticker=True):
        log.debug("handler [%s] started" % "fix_bone_layers_on_update")
        bind.fix_bone_layers(bpy.context, scene, lazy=False)

@persistent
def fix_bone_layers_on_load(scene):
    return
    if not scene or util.handler_can_run(scene, check_ticker=False):
        bind.fix_bone_layers(bpy.context, scene, lazy=False)

@persistent
def fix_avastar_data_on_load(scene):

    props = util.getAddonPreferences()
    if props.fix_data_on_upload:
        log.debug("handler [%s] started" % "fix_avastar_data_on_load")
    else:
        log.debug("Automatic fix of Avastar data after load is disabled.")
        return

    def remove_invalid_constraints(armobj):
        pbones = armobj.pose.bones
        for pbone in pbones:
            for con in [con for con in pbone.constraints if hasattr(con,"subtarget")]:
                if con.target and con.target.type=='ARMATURE':
                    try:
                        subtarget = con.subtarget
                        if not subtarget or subtarget in con.target.pose.bones:
                            continue
                        pbone.constraints.remove(con)
                    except:
                        log.warning("Issue with bone:%s %s constraint:%s" % (pbone.name, con.type, con.name))
                        raise
        return


    def fix_armature_data(context, armobj, props):
        remove_invalid_constraints(armobj)
        copy_RigProps_to_RigProp(armobj)

        if 'RigType' in armobj.AnimProp:
                armobj.RigProp.RigType = armobj.AnimProp.RigType

        if 'skeleton_path' in armobj:
            del armobj['skeleton_path']

        if not armobj.library:
            rig.deform_display_reset(armobj)
            rig.fix_avastar_armature(context, armobj)

        if props.rig_version_check:
            avastar_version, rig_version, rig_id, rig_type = util.get_version_info(armobj)
            if avastar_version != rig_version and rig_id != AVASTAR_RIG_ID:
                ctx = None
                util.set_active_object(context, armobj)
                for window in context.window_manager.windows:
                    screen = window.screen
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            ctx = util.get_context_copy(context)
                            ctx['window']        = window
                            ctx['screen']        = screen
                            ctx['area']          = area
                            ctx['active_object'] = armobj
                            ctx['object']        = armobj
                            break
                if ctx:
                    bpy.ops.avastar.update_avastar(ctx, 'INVOKE_DEFAULT')


    def get_prop_safemode(ob, prop_name, default=None):
        prop = getattr(ob, prop_name) if hasattr(ob, prop_name) else ob.get(prop_name)
        if not prop:
            prop=default
        return prop

    def copy_RigProps_to_RigProp(armobj):
        rigProps = get_prop_safemode(armobj, 'RigProps')
        rigProp = get_prop_safemode(armobj, 'RigProp')
        if rigProps:

            rigProp.RigType = propgroups.RigTypeItems[get_prop_safemode(rigProps, 'RigType', default=1)][0]
            rigProp.JointType = rigProp.JointTypeItems[get_prop_safemode(rigProps, 'JointType', default=0)][0]
            rigProp.restpose_mode = get_prop_safemode(rigProps, 'restpose_mode', default=rigProp.restpose_mode)
            rigProp.generate_joint_ik = get_prop_safemode(rigProps, 'generate_joint_ik', default=rigProp.generate_joint_ik)
            rigProp.generate_joint_tails = get_prop_safemode(rigProps, 'generate_joint_tails', default=rigProp.generate_joint_tails)

            old_callback_mode = util.set_use_bind_pose_update_in_progress(True)
            rigProp.rig_use_bind_pose = get_prop_safemode(rigProps, 'rig_use_bind_pose', default=rigProp.rig_use_bind_pose)
            util.set_use_bind_pose_update_in_progress(old_callback_mode)

            use_male_shape = armobj.ShapeDrivers.get('male_80') if armobj.ShapeDrivers else None
            if use_male_shape != None:
                propgroups.gender_update(armobj, use_male_shape, disable_handler=True)

            rp = armobj.get('RigProps')
            if rp:
                del armobj['RigProps']

    def fix_action_data():
        for action in bpy.data.actions:
            old_props = action.get("AnimProps")
            if old_props == None:
                continue

            loop = old_props.get('Loop')
            if loop:
                setattr(action.AnimProp,'Loop',loop)

            for key in old_props:
                if key == 'Loop':
                    continue
                val = old_props.get(key)
                setattr(action.AnimProp,key,val)


    context = bpy.context
    scene   = context.scene
    props = util.getAddonPreferences()
    if not scene.MeshProp.weightSourceSelection:
        scene.MeshProp.weightSourceSelection = 'AUTOMATIC'
    if not scene.MeshProp.bindSourceSelection:
        scene.MeshProp.bindSourceSelection = 'COPY'
    scene.MeshProp.attachSliders         = props.default_attach
    scene.MeshProp.enable_unsupported    = props.enable_unsupported

    init_log_level(context)

    arms = [obj for obj in scene.objects if obj.type=="ARMATURE" and 'avastar' in obj]
    if len(arms) > 0:
        log.info("Fixing %d Avastar RigData %s after loading from .blend" % (len(arms), util.pluralize("structure", len(arms))) )

    oldstate = util.set_disable_handlers(scene, True)
    try:

        fix_action_data()

        for armobj in arms:
            fix_armature_data(context, armobj, props)

        try:
            context_ob = context.object
            hide_state = util.object_hide_get(context_ob)
            util.object_hide_set(context_ob, False)
            initial_mode = util.ensure_mode_is('OBJECT')
        except:
            context_ob = None
            initial_mode = None

        objects = [obj for obj in scene.objects if obj.type=="MESH" and 'original' in obj]
        for ob in [o for o in scene.objects if o.type=="MESH"]:
            if 'original' in ob:
                ob[REFERENCE_SHAPE] = ob['original']
                del ob['original']
            shape.reset_weight_groups(ob) #clean slider starting point

        if context_ob:
            util.set_active_object(context, context_ob)
            util.ensure_mode_is(initial_mode)


        props.update_status='UNKNOWN'

    finally:
        util.set_disable_handlers(scene, oldstate)




@persistent
def check_for_system_mesh_edit(scene):

    if util.handler_can_run(scene, check_ticker=False):
        log.debug("handler [%s] started" % "check_for_system_mesh_edit")
    else:
        return
    
    context = bpy.context
    ob = getattr(context,'object', None)
    if ob is None: return True
    if ob.type != 'MESH': return True
    if not 'mesh_id' in ob: return True

    if not util.is_in_user_mode():
        return True

    props = util.getAddonPreferences()
    if props.rig_edit_check == False:
        return True

    if ob.mode != 'EDIT':
        if 'editing' in ob:
            del ob['editing']
        return True

    if 'editing' in ob:
        log.debug("User tries to edit System mesh %s" % (ob.name))
        return True

    ob['editing'] = True

    ctx = None
    scene = context.scene
    util.set_active_object(context, ob)
    for window in context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                ctx = util.get_context_copy(context)
                ctx['window']        = window
                ctx['screen']        = screen
                ctx['area']          = area
                ctx['active_object'] = ob
                ctx['object']        = ob
                break
    if ctx:
        log.warning("Warn user about editing the System Mesh %s" % (ob.name))
        bpy.ops.avastar.generic_info_operator(
            msg=messages.msg_edit_system_mesh % ob.name, 
            type=SEVERITY_STRONG_WARNING
        )

    return False

@persistent
def check_for_armatures_on_update(scene):

    if util.handler_can_run(scene, check_ticker=False):
        log.debug("handler [%s] started" % "check_for_armatures_on_update")
    else:
        return

    context = bpy.context




    prop = bpy.context.scene.MocapProp
    object_count = len(bpy.data.objects)



    prop.sources.clear()
    prop.targets.clear()
    prop.object_count = object_count

    arms = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE' and obj.users > 0]
    for obj in arms:
        if "avastar" in obj:
            entry = prop.targets.add()
        else:
            entry = prop.sources.add()
        entry.name = obj.name

    if len(prop.sources) == 1 and (prop.source == None or prop.source == ""):
        prop.source = prop.sources[0].name
    if len(prop.targets) == 1 and (prop.target == None or prop.target == ""):
        prop.target = prop.targets[0].name

class PanelRetargetInfo(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Retarget"

    bl_label ="Retarget"
    bl_idname = "AVASTAR_PT_animation_retarget_info"

    @classmethod
    def poll(self, context):
        prop = context.scene.MocapProp
        active = prop and len(prop.sources) > 0 and len(prop.targets) > 0
        return not active

    def draw(self, context):

        layout = self.layout
        box = layout.box()
        box.label(text='This panel is inactive')
        col=box.column(align=True)
        col.label(text='Wakeup as follows:')
        col.separator()
        col.label(text='Make sure the scene has')
        col.label(text='- A motion capture (BVH)')
        col.label(text='- An Avastar Skeleton')
        col.label(text='- The Avastar is selected')
        col.separator()
        bbox=box.box()
        bbox.label(text='Info For newbies:', icon=ICON_INFO)
        col=bbox.column(align=True)
        col.label(text='* Open Avastar vertical tab')
        col.label(text='* Open Workflows panel')
        col.separator()
        col.label(text='* From Workflow Presets')
        col.label(text='* Select Motion Transfer')
        col.separator()
        col.label(text='* Read the Avastar docs')
        col.separator()
        col.operator("wm.url_open", text='Avastar Documentation').url=DOCUMENTATION+'/reference/usermanual/'

class PanelPoseTransfer(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Retarget"

    bl_label ="Pose Settings"
    bl_idname = "AVASTAR_PT_animation_pose_settings"

    @classmethod
    def poll(self, context):
        prop = context.scene.MocapProp
        return prop and len(prop.sources) > 0 and len(prop.targets) > 0

    def draw(self, context):

        layout = self.layout

        prop = context.scene.MocapProp

        mocap_sources = [obj.name for obj in bpy.data.objects if 'avastar' not in obj and obj.type == 'ARMATURE']
        mocap_targets = [obj.name for obj in bpy.data.objects if 'avastar' in obj and obj.type == 'ARMATURE']

        if prop.target in  mocap_targets and prop.source in  mocap_sources:

            target = bpy.data.objects[prop.target]
            col=layout.column()
            col.separator()
            box = layout.box()
            box.label(text="Pose")

            col = box.column(align=True)
            row = col.row(align=True)
            row.label(text = "Ref frame:")
            row.prop(prop, "referenceFrame", text="")
            row.enabled = not prop.use_restpose

            col = box.column(align=True)
            col.prop(prop, "use_restpose")
            col.prop(prop, "with_translation")

            col = box.column(align=True)
            row = col.row(align=True)
            row.operator("avastar.transfer_pose", text='Transfer Pose', icon=ICON_OUTLINER_OB_ARMATURE)
            row.operator("avastar.match_scales", text='Match scales', icon=ICON_SOLO_ON)
            
            pannels.PanelPosing.add_pose_bone_constraints_section(layout, target)


class PanelMotionTransfer(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = UI_LOCATION
    bl_category    = "Retarget"

    bl_label ="Motion Transfer"
    bl_idname = "AVASTAR_PT_animation_action_transfer"

    @classmethod
    def poll(self, context):
        prop = context.scene.MocapProp
        return prop and len(prop.sources) > 0 and len(prop.targets) > 0

    def draw(self, context):

        layout = self.layout

        prop = context.scene.MocapProp

        mocap_sources = [obj.name for obj in bpy.data.objects if 'avastar' not in obj and obj.type == 'ARMATURE']
        mocap_targets = [obj.name for obj in bpy.data.objects if 'avastar' in obj and obj.type == 'ARMATURE']

        row = layout.row(align=True)
        row.label(text = "Source:")
        row.prop_search(prop, "source", prop, "sources", text="", icon=ICON_ARMATURE_DATA)
        row = layout.row(align=True)
        row.label(text = "Target:")
        row.prop_search(prop, "target", prop, "targets", text="", icon=ICON_ARMATURE_DATA)

        if prop.target in  mocap_targets and prop.source in  mocap_sources:

            if prop.show_bone_mapping:
                icon = ICON_DISCLOSURE_TRI_DOWN
            else:
                icon = ICON_DISCLOSURE_TRI_RIGHT

            mcol = layout.column()

            counter = 0
            source = bpy.data.objects[prop.source]
            target = bpy.data.objects[prop.target]

            if prop.show_bone_mapping:
                box = layout.box()
                row = box.row()
                targetcol = row.column(align=True)
                targetcol.scale_x = 2
                sourcecol = row.column(align=True)
                sourcecol.scale_x = 2
                selectcol = row.column(align=True)
                selectcol.scale_x = 0.1

                targetcol.label(text="Target Rig")
                if prop.flavor == "":
                    src_label =  "Source Rig"
                else:
                    src_label = "%s" % prop.flavor 
                sourcecol.label(text=src_label)
                selectcol.label(text=" ")

                for bone in data.get_mtui_bones(target):
                    if bone in MTUI_SEPARATORS:
                        targetcol.separator()
                        sourcecol.separator()
                        selectcol.separator()
                    targetcol.label(text=bone+":")
                    link = prop.get(bone)
                    if link and  link != '':
                        counter +=1
                    sourcecol.prop_search(prop, bone, source.data, "bones", text='')
                    selectcol.operator(ButtonSetSourceBone.bl_idname, text='', icon=ICON_PIVOT_CURSOR).target_bone = bone

                targetcol.separator()
                sourcecol.separator()
                selectcol.separator()

                row = box.row()
                row.operator(ButtonClearBoneMap.bl_idname, icon=ICON_X)
                row.operator(ButtonCopyOtherSide.bl_idname, icon=ICON_ARROW_LEFTRIGHT)
            else:
                for bone in data.get_mtui_bones(target):
                    link = prop.get(bone)
                    if link and  link != '':
                        counter +=1


            mcol.alert = counter == 0
            mrow = mcol.row(align=True)
            mrow.operator(ButtonMappingDisplayDetails.bl_idname, text="", icon=icon)
            if counter == 0:
                mrow.operator(ButtonGuessMapping.bl_idname, icon=ICON_ERROR)
            else:
                mrow.operator(ButtonGuessMapping.bl_idname, text='', icon=ICON_MONKEY)


            last_select = bpy.types.AVASTAR_MT_retarget_presets_menu.bl_label
            mrow.menu("AVASTAR_MT_retarget_presets_menu", text=last_select )
            mrow.operator("avastar.retarget_presets_add", text="", icon=ICON_ADD)
            if last_select not in ["Retarget Presets", "Presets"]:
                mrow.operator("avastar.retarget_presets_update", text="", icon=ICON_FILE_REFRESH)
                mrow.operator("avastar.retarget_presets_remove", text="", icon=ICON_REMOVE).remove_active = True


            box = layout.box()
            box.label(text="Make Seamless:")
            row=box.row(align=True)
            row.prop(prop,"seamlessRotFrames")
            row.prop(prop,"seamlessLocFrames")

            col=box.column()
            col.label(text="Simplification:")
            col.prop(prop, "simplificationMethod", text='')
            if prop.simplificationMethod == 'loweslocal':
                col.prop(prop, "lowesLocalTol")
            elif prop.simplificationMethod == 'lowesglobal':
                col.prop(prop, "lowesGlobalTol")

            col = layout.column()
            col.alert = counter == 0 or not prop.get('COG')
            row = col.row(align=True)
            row.alert = col.alert
            row.operator("avastar.transfer_motion", text='Transfer Motion', icon=ICON_POSE_DATA)
            scn = context.scene

            row.alert = False
            row.operator("avastar.delete_motion", text='', icon=ICON_X)


class ButtonSetSourceBone(bpy.types.Operator):
    bl_idname = "avastar.set_source_bone"
    bl_label ="Set source bone"
    bl_description ="Copy active bone to source field"
    bl_options = {'REGISTER', 'UNDO'}

    target_bone : StringProperty()

    def execute(self, context):
        try:
            scn = context.scene
            prop = scn.MocapProp

            sbone = bpy.context.active_pose_bone

            source = bpy.data.objects[prop.source]

            if sbone.name in source.data.bones:
                setattr(prop, self.target_bone, sbone.name)

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonClearBoneMap(bpy.types.Operator):
    bl_idname = "avastar.clear_bone_map"
    bl_label ="Clear"
    bl_description ="Clear the bone mapping"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            data.clear_mtui_bones(context)
            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}


class ButtonMappingDisplayDetails(bpy.types.Operator):
    bl_idname = "avastar.mapping_display_details"
    bl_label = ""
    bl_description = "Hide/Unhide advanced mapping display"

    def execute(self, context):
        context.scene.MocapProp.show_bone_mapping = not context.scene.MocapProp.show_bone_mapping
        return{'FINISHED'}




class ButtonGuessMapping(bpy.types.Operator):
    bl_idname = "avastar.guess_bone_map"
    bl_label =  "Guess"
    bl_description =  "Guess the bone mapping from the source names\nIf no bones are mapped then the motion transfer is disabled!"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            scn = context.scene
            prop = scn.MocapProp
            source = bpy.data.objects[prop.source]
            target = bpy.data.objects[prop.target]
            prop.flavor, bonelist = animation.find_best_match(source, target)
            log.warning("Guessing Mapping: Found Flavor '%s' (%d bones)" % (prop.flavor, len(bonelist)))

            animation.retarget_rig(source, bonelist, data.get_mt_bones(target), prop)

        except Exception as e:
            util.ErrorDialog.exception(e)
        return{'FINISHED'}


class ButtonCopyOtherSide(bpy.types.Operator):
    bl_idname = "avastar.copy_other_side"
    bl_label ="Mirror Copy"
    bl_description ="Copy Limbs map to opposite side"
    bl_options = {'REGISTER', 'UNDO'}

    target_bone : StringProperty()

    def execute(self, context):
        try:
            scn = context.scene
            prop = scn.MocapProp
            target = bpy.data.objects[prop.target]
            for target1 in data.get_mtui_bones(target):
                source1 = getattr(prop, target1)
                if source1 == "":
                    continue
                if "Left" in target1:
                    target2 = target1.replace("Left","Right")
                    source2 = getattr(prop, target2)
                    if source2 == "":
                        setattr(prop, target2, util.flipName(source1))
                elif "Right" in target1:
                    target2 = target1.replace("Right","Left")
                    source2 = getattr(prop, target2)
                    if source2 == "":
                        setattr(prop, target2, util.flipName(source1))

            return{'FINISHED'}
        except Exception as e:
            util.ErrorDialog.exception(e)
            return{'FINISHED'}




class AddAvatar(bpy.types.Operator):
    bl_idname = "avastar.add_avatar"
    bl_label = "Avastar"
    bl_description ="Create new Avastar Character"
    bl_options = {'REGISTER', 'UNDO'}

    quads : BoolProperty(
                name="with Quads",
                description="create Avastar with Quads",
                default=False,

                )
                
    no_mesh : BoolProperty(
                name="only Armature",
                description="create only the Avastar Rig (no Avastar meshes, good for creating custom avatars)",
                default=False,

                )

    file          : StringProperty()
    rigType       : StringProperty()
    jointType     : StringProperty()

    @classmethod
    def poll(self, context):
        if context.active_object:
            return context.active_object.mode == 'OBJECT'
        return True

    def get_preset(self, context, file):

        sceneProps    = context.scene.SceneProp
        
        b_meshType      = sceneProps.avastarMeshType
        b_rigType       = sceneProps.avastarRigType
        b_jointType     = sceneProps.avastarJointType

        bpy.ops.script.python_file_run(filepath=file)

        self.quads      = sceneProps.avastarMeshType == 'QUADS'
        self.no_mesh    = sceneProps.avastarMeshType == 'NONE'
        self.rigType    = sceneProps.avastarRigType
        self.jointType  = sceneProps.avastarJointType

        sceneProps.avastarMeshType  = b_meshType
        sceneProps.avastarRigType   = b_rigType
        sceneProps.avastarJointType = b_jointType
        
    def execute(self, context):
        oselect_modes = util.set_mesh_select_mode((False,True,False))
        osuppress_handlers = util.set_disable_handlers(context.scene, True)

        try:

            if self.file:
                self.get_preset(context, self.file)

            arm_obj = create.createAvatar(
                context,
                quads                = self.quads, 
                no_mesh              = self.no_mesh, 
                rigType              = self.rigType,
                jointType            = self.jointType
            )

            if arm_obj == None:
                self.report({'ERROR'},("Could not create Armature\nOpen Blender Console for details on error"))
                util.set_mesh_select_mode(oselect_modes)
                return {'CANCELLED'}

            util.set_active_object(context, arm_obj)
            util.set_armature_layers(arm_obj, B_DEFAULT_POSE_LAYERS)
            
            preferences = util.getAddonPreferences()
            initial_mode = preferences.initial_rig_mode

            if initial_mode == 'POSE':
                bpy.ops.avastar.bone_preset_animate()
            elif initial_mode == 'EDIT':
                bpy.ops.avastar.bone_preset_edit()
                util.object_show_in_front(context.object, True)
            else:
                omode = util.ensure_mode_is("OBJECT")
                util.object_show_in_front(context.object, False)

            util.set_mesh_select_mode(oselect_modes)
        finally:
            util.set_disable_handlers(context.scene, osuppress_handlers)

        return {'FINISHED'}


class AVASTAR_MT_AddMenu(bpy.types.Menu):
    bl_idname = "AVASTAR_MT_AddMenu"
    bl_label = "Avastar..."

    def draw(self, context):
        layout = self.layout


        for file in glob.glob("%s/*.py" % RIG_PRESET_DIR):
            label      = os.path.basename(file).replace('.py','').replace('_',' ').replace('+',' ')
            props      = layout.operator("avastar.add_avatar", text=label, icon=ICON_OUTLINER_OB_ARMATURE)
            props.file = file


class AVASTAR_MT_AddMenu2(bpy.types.Menu):
    bl_idname="AVASTAR_MT_AddMenu2"
    bl_label = "Avastar..."

    def draw(self, context):
        layout = self.layout
        
        props = layout.operator("avastar.add_avatar", text="with Triangles", icon=ICON_OUTLINER_OB_ARMATURE)
        props.quads   = False
        props.no_mesh = False
        props.rigtype = util.getAddonPreferences().target_system

        props = layout.operator("avastar.add_avatar", text="Only Rig", icon=ICON_OUTLINER_OB_ARMATURE)
        props.quads   = False
        props.no_mesh = True
        props.rigtype = util.getAddonPreferences().target_system

class AVASTAR_MT_HelpMenu(bpy.types.Menu):
    bl_idname="AVASTAR_MT_HelpMenu"
    bl_label = "Avastar..."

    def draw(self, context):
        layout = self.layout

        layout.operator("wm.url_open", text="check for Update",     icon=ICON_URL).url=AVASTAR_URL   + "/update?myversion=" + util.get_addon_version() + "&myblender=" + str(get_blender_revision())
        layout.operator("wm.url_open", text="Short Overview",       icon=ICON_URL).url=DOCUMENTATION + "/videos/"
        layout.operator("wm.url_open", text="Getting Help",         icon=ICON_URL).url=DOCUMENTATION + "/avastar-2/getting-help/"
        layout.label(text="Basic tutorials:")
        layout.operator("wm.url_open", text="First Steps",          icon=ICON_URL).url=DOCUMENTATION + "/avastar-2/reference/first-steps/"
        layout.operator("wm.url_open", text="Pose a Character",     icon=ICON_URL).url=DOCUMENTATION + "/avastar-2/reference/pose-a-character/"
        layout.operator("wm.url_open", text="Create an Attachment", icon=ICON_URL).url=DOCUMENTATION + "/avastar-2/reference/attachments/"
        layout.operator("wm.url_open", text="Create an Animation",  icon=ICON_URL).url=DOCUMENTATION + "/avastar-2/reference/my-first-animation/"
        layout.operator("wm.url_open", text="Use your own Shape",   icon=ICON_URL).url=DOCUMENTATION + "/avastar-2/reference/use-sl-shapes/"
        layout.label(text="Knowledge:")
        layout.operator("wm.url_open", text="Skinning Basics",      icon=ICON_URL).url=DOCUMENTATION + "/knowledge/skinning-basics/"
        layout.operator("wm.url_open", text="Avastar Bones",        icon=ICON_URL).url=DOCUMENTATION + "/knowledge/avastar-bones/"
        layout.operator("wm.url_open", text="Fitted Mesh",          icon=ICON_URL).url=DOCUMENTATION + "/knowledge/nutsbolts-of-fitted-mesh/"

class AVASTAR_MT_DevkitMenu(bpy.types.Menu):
    bl_idname="AVASTAR_MT_DevkitMenu"
    bl_label = "Devkit..."

    def draw(self, context):
        layout = self.layout
        layout.operator("avastar.import_collada_devkit", text="Belleza",  icon=ICON_OUTLINER_OB_ARMATURE).devkit_type='BELLEZA'
        layout.operator("avastar.import_collada_devkit", text="Maitreya", icon=ICON_OUTLINER_OB_ARMATURE).devkit_type='MAITREYA'
        layout.operator("avastar.import_collada_devkit", text="TMP",      icon=ICON_OUTLINER_OB_ARMATURE).devkit_type='TMP'

class AVASTAR_MT_TemplatesMenu(bpy.types.Menu):
    bl_idname = "AVASTAR_MT_TemplatesMenu"
    bl_label = "Open Template..."

    def draw(self, context):
        blender_scripts  = bpy.utils.user_resource('SCRIPTS', "presets")
        destdir          = os.path.join(blender_scripts, __name__)
        path = os.path.join(destdir,"*.blend")
        log.warning("Path: %s" % path)
        templates = glob.glob(path)
        templates.sort(key=lambda x: os.path.getmtime(x))
        layout = self.layout
        layout.operator_context = 'EXEC_SCREEN'

        for template in templates:

            name = os.path.basename(template)
            name = name[0:name.index(".")]
            name = name.replace("_", " ")

            if BLENDER_VERSION > 26900:
                props = layout.operator("wm.read_homefile", text=name, icon=ICON_FILE)




            else:
                props = layout.operator("wm.open_mainfile", text=name, icon=ICON_FILE)
                props.load_ui=False
            props.filepath=template



def menu_import_avastar_devkits(self, context):
    self.layout.menu(AVASTAR_MT_DevkitMenu.bl_idname, text="Devkit", icon=ICON_OUTLINER_OB_ARMATURE)

def menu_help_avastar(self, context):
    self.layout.menu(AVASTAR_MT_HelpMenu.bl_idname, text="Avastar", icon=ICON_URL)

def menu_add_avastar(self, context):

    self.layout.menu(AVASTAR_MT_AddMenu.bl_idname, text="Avastar", icon=ICON_URL)

def menu_export_collada(self, context):

    self.layout.operator(mesh.ButtonExportSLCollada.bl_idname)

def menu_import_avastar_shape(self, context):

    self.layout.operator(mesh.ButtonImportAvastarShape.bl_idname)

user_templates = None
def menu_add_templates(self, context):
    global user_templates


    if user_templates == None:
        user_templates = register_templates()
        if user_templates == 'local':
            if True: #TODO: uncomment this -> get_blender_revision() < 278400:
                print("Use Avastar's native template system")

    if user_templates == 'local':
        if True: #TODO: uncomment this -> get_blender_revision() < 278400:
            self.layout.menu(AVASTAR_MT_TemplatesMenu.bl_idname, icon=ICON_OUTLINER_OB_ARMATURE)




class RetargetPropGroup(bpy.types.PropertyGroup):
    pass

class MocapPropGroup(bpy.types.PropertyGroup):
    flavor : StringProperty()
    source : StringProperty()
    target : StringProperty()
    object_count : IntProperty(default=0, min=0)
    referenceFrame : IntProperty()

    use_restpose : animation.g_use_restpose
    show_bone_mapping : BoolProperty(name="Show bone mapping", default = False)

    simplificationitems = [
        ('none', 'None', 'None'),
        ('loweslocal', 'Lowes Local', 'Lowes Local'),
        ('lowesglobal', 'Lowes Global', 'Lowes Global'),
        ]
    simplificationMethod : EnumProperty(items=simplificationitems, name='Method', default='none')
    lowesLocalTol : FloatProperty(default=0.02, name="Tol")
    lowesGlobalTol : FloatProperty(default=0.1, name="Tol")

    seamlessRotFrames : IntProperty(name="Rot frames",
        min=0, 
        default=0,
        description="Blend range to make seamles rotation")

    seamlessLocFrames : IntProperty(name="Loc frames",
        min=0,
        default=0,
        description="Blend range to make seamles translation")
        
    with_translation : BoolProperty(name="with Translation", default=False, description = "Prepare the Rig to allow translation animation")


def update_sync_influence(pbone, context):
    
    synced = pbone.sync_influence
    if synced and 'Grab' in pbone.constraints:
        print("update_sync_influence for", pbone.name)
        val = pbone.constraints['Grab'].influence
        pbones = context.object.pose.bones
        arm = util.get_armature(context.object)
        if pbone.name.endswith("SolverLeft"):
            arm.RigProp.IKHandInfluenceLeft = val
        elif pbone.name.endswith("SolverRight"):
            arm.RigProp.IKHandInfluenceRight = val

def update_pinch_influence(pbone,context):
    pinched = pbone.pinch_influence
    try:
        grab_inf = min(1,  2 * max(0.5-pinched, 0))
        pinch_inf= min(1,  2 * max(pinched-0.5, 0))

        pbone.constraints['Grab'].influence = grab_inf
        pbone.constraints['Pinch'].influence = pinch_inf

        if pbone.name.startswith("ikThumb"):
            otherbone = context.object.pose.bones["ikIndex%s" % pbone.name[7:]]
            otherbone.pinch_influence = pinched
    except:
        print("Could not balance grab/pinch constraint")
        raise

bpy.types.PoseBone.sync_influence = BoolProperty(
        default     = False,
        update      = update_sync_influence,
        name        ="IK Lock",
        description ="Modify the influence of all locked bones in sync"
        )

bpy.types.PoseBone.pinch_influence = FloatProperty(
        name="pinch",
        min=0, max=1, default=0,
        update=update_pinch_influence
        )


def BLinitialisation():
    ##


    ##

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)






    bpy.types.Scene.RetargetProp = PointerProperty(type = RetargetPropGroup)
    bpy.types.Scene.MocapProp = PointerProperty(type = MocapPropGroup)

    bpy.types.WindowManager.LoggerIndexProp = PointerProperty(type=LoggerIndexPropGroup)
    bpy.types.WindowManager.LoggerPropList = CollectionProperty(type=LoggerPropListGroup)
    weights.module_load()

    animation.initialisation()
    shape.shapeInitialisation()






    init_log_level(bpy.context)
    register_handlers()

    bpy.types.DATA_PT_shape_keys.prepend(shape.add_shapekey_updater)


def vgroup_items(self, context):
    if context.active_object and context.active_object.type == 'MESH':
        return [(vgroup.name, vgroup.name, "") for vgroup in context.active_object.vertex_groups]
    else:
        return []


def avastar_docs():
    return DOCUMENTATION+'/', URL_MANUAL_MAPPING.values()

class FactoryPresets(bpy.types.Operator):
    bl_idname = "avastar.rig_presets_reset"
    bl_label = "Reset preset category"
    bl_description = \
'''Reset all presets of this category to the addon factory values

Attention:

If you have defined your own Character definitions,
they will all get permanently deleted'''

    category : StringProperty()

    def execute(self, context):
        factory_reset(self.category)
        return {'FINISHED'}





addon_keymaps = []
SEPARATOR     = "===================================================================="

def register_templates():

    if 'toolset_pro' in dir(bpy.ops.sparkles):
        try:
            import sparkles
            path = TEMPLATE_DIR
            path = os.path.join(TEMPLATE_DIR,"*")
            sparkles.register_template_path(path, 'Avastar Templates')
            log.warning("Added Avastar Templates to Sparkles Template list.")
            return 'sparkles'
        except:
            pass
    return 'local'

def sl_skeleton_func_export(self, context):
    self.layout.operator("avastar.export_sl_avatar_skeleton")

def sl_skeleton_func_import(self, context):
    self.layout.operator("avastar.import_sl_avatar_skeleton")

def sl_animation_func_import(self, context):
    self.layout.operator("avastar.import_avatar_animation")


def register_RetargetPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        setattr(RetargetPropGroup, bone, StringProperty() )

def register_MocapPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        setattr(MocapPropGroup, bone, StringProperty() )    
    setattr(MocapPropGroup, "sources", CollectionProperty(type=StringListProp))
    setattr(MocapPropGroup, "targets", CollectionProperty(type=StringListProp))

def register_WeightsPropGroup_attributes():
    bones = data.get_base_bones()
    for bone in bones:
        setattr(WeightsPropGroup, bone, FloatProperty(default=0.0, min=0.0, max=1.0, name=bone))

def unregister_RetargetPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        delattr(RetargetPropGroup, bone)
    delattr(MocapPropGroup, "sources")
    delattr(MocapPropGroup, "targets")


def unregister_MocapPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        delattr(MocapPropGroup, bone)

def unregister_WeightsPropGroup_attributes():
    bones = data.get_base_bones()
    for bone in bones:
        delattr(WeightsPropGroup, bone)



def factory_reset(category):
    import shutil, tempfile
    avastar_init    = __file__
    avastar_home    = os.path.dirname(avastar_init)
    avastar_presets = os.path.join(avastar_home, "presets")
    srcdir          = os.path.join(avastar_presets,category)
    blender_scripts = bpy.utils.user_resource('SCRIPTS', "presets")
    destdir         = os.path.join(blender_scripts, __name__, category)

    if os.path.exists(destdir) and os.path.isdir(destdir):
        tmp = tempfile.mktemp(dir=os.path.dirname(destdir))
        shutil.move(destdir, tmp)
        shutil.rmtree(tmp)
    shutil.copytree(srcdir, destdir)


def import_submodule(module_name, package_name='avastar'):
    if not 'importlib' in locals():
        import bpy
        import importlib
        import os

    module = globals().get(module_name)
    if (module):
        importlib.reload(module)
        print("Module %s reloaded" % module_name)
    else:
        importlib.import_module('.%s'%module_name, package_name)
        print("Module %s.%s loaded" % (package_name,module_name))

classes = (
    LoggerIndexPropGroup,
    LoggerPropListGroup,
    AVASTAR_UL_LoggerPropVarList,
    WeightsPropGroup,
    StringListProp,
    Avastar,
    AvastarShowPrefs,
    DownloadReload,
    DownloadInstall,
    DownloadReset,
    DownloadUpdate,
    CreateReport,
    CheckForUpdates,
    AVASTAR_MT_rig_presets_menu,
    AvastarAddPresetRig,
    AvastarUpdatePresetRig,
    AvastarRemovePresetRig,
    ObjectSelectOperator,
    DisplayAvastarVersionOperator,
    DisplayAvastarVersionMismatchOperator,
    DisplayAvastarRigVersionOperator,
    WeightAcceptedHint,
    WeightIgnoredHint,
    ShapeTypeMorphHint,
    ShapeTypeSystemMorphHint,
    ShapeTypeBoneHint,
    ShapeTypeExtendedHint,
    ShapeTypeFittedHint,
    FittingTypeHint,
    FittingBoneDeletePgroup,
    FittingBoneSelectedHint,
    SynchronizeShapekeyData,
    ResetShapeSectionOperator,
    ResetShapeValueOperator,
    ButtonLoadShapeUI,
    ButtonPrintProps,
    ButtonSaveProps,
    ButtonLoadProps,
    ButtonResetToSLRestPose,
    ButtonResetToDefault,
    ButtonResetToBindshape,
    ButtonDeleteAllShapes,
    ButtonRefreshShape,
    ButtonIKMatchDetails,
    ButtonIKMatchAll,
    PanelIKUI,
    PanelRigUI,
    ButtonEnableEyeTarget,
    ButtonIKWristLOrient,
    ButtonIKElbowTargetLOrient,
    ButtonIKWristROrient,
    ButtonIKElbowTargetROrient,
    ButtonIKHeelLOrient,
    ButtonIKKneeTargetLOrient,
    ButtonIKHeelROrient,
    ButtonIKKneeTargetROrient,
    ButtonIKHindLimb3LOrient,
    ButtonIKHindLimb2TargetLOrient,
    ButtonIKHindLimb3ROrient,
    ButtonIKHindLimb2TargetROrient,
    ButtonChainMore,
    ButtonChainLess,
    ButtonChainCOG,
    ButtonChainParent,
    ButtonChainLimb,
    ButtonChainFree,
    ButtonChainClamped,
    ButtonSetRotationLimits,
    ButtonUnsetRotationLimits,
    ButtonBreatheIn,
    ButtonBreatheOut,
    PanelExpressions,
    ButtonCustomShape,
    ButtonStickShape,
    PanelAnimationExport,
    ExportAnimOperator,
    ButtonExportAnim,
    ButtonExportBulkAnim,
    PanelRetargetInfo,
    PanelPoseTransfer,
    PanelMotionTransfer,
    ButtonSetSourceBone,
    ButtonClearBoneMap,
    ButtonMappingDisplayDetails,
    ButtonGuessMapping,
    ButtonCopyOtherSide,
    AddAvatar,
    AVASTAR_MT_AddMenu,
    AVASTAR_MT_AddMenu2,
    AVASTAR_MT_HelpMenu,
    AVASTAR_MT_DevkitMenu,
    AVASTAR_MT_TemplatesMenu,
    RetargetPropGroup,
    MocapPropGroup,
    FactoryPresets,
    DevkitConfigurationEditor,
    PoseCopy,
    PosePaste,
    PoseMirrorPaste
)

modules =  (
    animation,
    armature_util,
    bind,
    const,
    context_util,
    copyrig,
    updaterig,
    create,
    data,
    debug,
    generate,
    mesh,
    messages,
    pannels,
    presets,
    propgroups,
    quadify,
    rig,
    shape,
    skeleton,
    util,
    weights,
    www
)


def register_RetargetPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        setattr(RetargetPropGroup, bone, StringProperty() )

def register_MocapPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        setattr(MocapPropGroup, bone, StringProperty() )    
    setattr(MocapPropGroup, "sources", CollectionProperty(type=StringListProp))
    setattr(MocapPropGroup, "targets", CollectionProperty(type=StringListProp))

def register_WeightsPropGroup_attributes():
    bones = data.get_base_bones()
    for bone in bones:
        setattr(WeightsPropGroup, bone, FloatProperty(default=0.0, min=0.0, max=1.0, name=bone))

def unregister_RetargetPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        delattr(RetargetPropGroup, bone)
    delattr(MocapPropGroup, "sources")
    delattr(MocapPropGroup, "targets")

def unregister_MocapPropGroup_attributes():
    for bone in MTUIBONES_EXTENDED:
        delattr(MocapPropGroup, bone)

def unregister_WeightsPropGroup_attributes():
    bones = data.get_base_bones()
    for bone in bones:
        delattr(WeightsPropGroup, bone)


def register():
    from bpy.utils import register_class
    const.register_icons()
    register_submodules()
    for cls in classes:
        registerlog.info("Register class %s" % cls)
        register_class(cls)

    register_WeightsPropGroup_attributes()
    register_RetargetPropGroup_attributes()
    register_MocapPropGroup_attributes()

    bpy.types.TOPBAR_MT_help.prepend(menu_help_avastar)
    bpy.types.TOPBAR_MT_file.prepend(menu_add_templates)
    bpy.types.VIEW3D_MT_add.append(menu_add_avastar)

    bpy.types.TOPBAR_MT_file_export.prepend(menu_export_collada)
    bpy.types.TOPBAR_MT_file_import.append(menu_import_avastar_shape)
    bpy.types.TOPBAR_MT_file_import.append(menu_import_avastar_devkits)

    bpy.types.TOPBAR_MT_file_export.append(sl_skeleton_func_export)
    bpy.types.TOPBAR_MT_file_import.append(sl_skeleton_func_import)
    bpy.types.TOPBAR_MT_file_import.append(sl_animation_func_import)

    bpy.types.VIEW3D_MT_editor_menus.append(copypaste_pose)

    BLinitialisation()

    has_warnings = False
    if bpy.app.version_cycle != 'release':
        log.warning(SEPARATOR)
        log.warning("Avastar:  Your Blender instance is in state '%s'" % bpy.app.version_cycle)
        log.warning("          We recommend to install this addon only on official")
        log.warning("          Blender releases from Blender.org")
        has_warnings = True

    bpy.utils.register_manual_map(avastar_docs)


    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new(ButtonRefreshShape.bl_idname, 'Q', 'PRESS', alt=True)
        addon_keymaps.append((km,kmi))

    avastar_init    = __file__
    avastar_home    = os.path.dirname(avastar_init)
    avastar_apptemplates = os.path.join(avastar_home, "apptemplates")
    blender_scripts  = bpy.utils.user_resource('SCRIPTS', "presets")

    avastar_themes = os.path.join(avastar_home, "interface_theme")
    destdir        = os.path.join(blender_scripts, "interface_theme")
    util.copydir(avastar_themes, destdir, overwrite=True)

    avastar_presets = os.path.join(avastar_home, "presets")
    destdir         = os.path.join(blender_scripts, __name__)
    util.copydir(avastar_presets, destdir, overwrite=True)

    if True: #TODO: uncomment this-> get_blender_revision() < 279000:

        util.copyblend(avastar_apptemplates, destdir, overwrite=True)
    else:

        path_app_templates = bpy.utils.user_resource(
            'SCRIPTS', os.path.join("startup", "bl_app_templates_user"),
            create=True,
        )
        util.copydir(avastar_apptemplates, path_app_templates, overwrite=True)
        
        if os.path.exists(destdir):
            os.rename(destdir, destdir+'_old')

    if has_warnings:
        log.warning(SEPARATOR)

def register_handlers():

    bpy.app.handlers.depsgraph_update_post.append(rig.sync_timeline_action)
    bpy.app.handlers.depsgraph_update_post.append(rig.check_dirty_armature_on_update)
    bpy.app.handlers.depsgraph_update_post.append(shape.check_dirty_mesh_on_update)
    bpy.app.handlers.depsgraph_update_post.append(fix_bone_layers_on_update)
    bpy.app.handlers.depsgraph_update_post.append(check_for_armatures_on_update)
    bpy.app.handlers.depsgraph_update_post.append(check_for_system_mesh_edit)
    bpy.app.handlers.depsgraph_update_post.append(weights.edit_object_change_handler)
    bpy.app.handlers.depsgraph_update_post.append(rig.fix_linebones_on_update)
    bpy.app.handlers.load_post.append(fix_bone_layers_on_load)
    bpy.app.handlers.load_post.append(fix_avastar_data_on_load)
    bpy.app.handlers.depsgraph_update_post.append(shape.check_dirty_mesh_on_load)
    bpy.app.handlers.frame_change_post.append(shape.update_on_framechange)
    print("Avastar Handlers registered")

def unregister_handlers():

    bpy.app.handlers.frame_change_post.remove(shape.update_on_framechange)
    bpy.app.handlers.depsgraph_update_post.remove(shape.check_dirty_mesh_on_load)
    bpy.app.handlers.load_post.remove(fix_avastar_data_on_load)
    bpy.app.handlers.load_post.remove(fix_bone_layers_on_load)
    bpy.app.handlers.depsgraph_update_post.remove(rig.fix_linebones_on_update)
    bpy.app.handlers.depsgraph_update_post.remove(weights.edit_object_change_handler)
    bpy.app.handlers.depsgraph_update_post.remove(check_for_system_mesh_edit)
    bpy.app.handlers.depsgraph_update_post.remove(check_for_armatures_on_update)
    bpy.app.handlers.depsgraph_update_post.remove(fix_bone_layers_on_update)
    bpy.app.handlers.depsgraph_update_post.remove(shape.check_dirty_mesh_on_update)
    bpy.app.handlers.depsgraph_update_post.remove(rig.check_dirty_armature_on_update)
    bpy.app.handlers.depsgraph_update_post.remove(rig.sync_timeline_action)
    print("Avastar Handlers unregistered")

def unregister():
    from bpy.utils import unregister_class   
    try:

        bpy.types.DATA_PT_shape_keys.remove(shape.add_shapekey_updater)
        unregister_handlers()

        bpy.types.TOPBAR_MT_file_export.remove(sl_skeleton_func_export)
        bpy.types.TOPBAR_MT_file_import.remove(sl_skeleton_func_import)
        bpy.types.TOPBAR_MT_file_import.remove(sl_animation_func_import)
        bpy.types.TOPBAR_MT_help.remove(menu_help_avastar)
        bpy.types.VIEW3D_MT_add.remove(menu_add_avastar)
        bpy.types.TOPBAR_MT_file_export.remove(menu_export_collada)
        bpy.types.TOPBAR_MT_file.remove(menu_add_templates)
        bpy.types.TOPBAR_MT_file_import.remove(menu_import_avastar_shape)
        bpy.types.TOPBAR_MT_file_import.remove(menu_import_avastar_devkits)

        bpy.types.VIEW3D_MT_editor_menus.remove(copypaste_pose)

    except:
        import traceback
        log.error(">>> Error during unregister %s <<<" % __name__)
        log.error("traceback: %s" % traceback.format_exc())

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


    shape.terminate()
    animation.terminate()

    del bpy.types.Object.IKSwitchesProp

    del bpy.types.Scene.MocapProp

    del bpy.types.WindowManager.LoggerIndexProp
    del bpy.types.WindowManager.LoggerPropList

    const.unregister_icons()
    bpy.utils.unregister_manual_map(avastar_docs)



    user_templates = None
    unregister_submodules()

    unregister_WeightsPropGroup_attributes()
    unregister_RetargetPropGroup_attributes()
    unregister_MocapPropGroup_attributes()

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)     
        registerlog.info("Unregistered init:%s" % cls)

    print("Avastar Shutdown Completed")

if __name__ == "__main__":

    register()

def unregister_submodules():
    for module in reversed(modules):
        module.unregister()

def register_submodules():
    for module in modules:
        module.register()

### Copyright     2011-2013 Magus Freston, Domino Marama, and Gaia Clary
### Modifications 2014-2015 Gaia Clary
###
### This file is part of Avastar 1.
###
### Avastar is distributed under an End User License Agreement and you
### should have received a copy of the license together with Avastar.
### The license can also be obtained from http://www.machinimatrix.org/
