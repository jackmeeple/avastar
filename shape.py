### Copyright 2011, Magus Freston, Domino Marama, and Gaia Clary
### Modifications 2013-2015 Gaia Clary
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
from collections import OrderedDict
from operator import add

import bpy
from bpy.props import *
import  xml.etree.ElementTree as et
from mathutils import Vector, Matrix
import time, logging, traceback, os, gettext

from math import fabs, radians
from bpy.app.handlers import persistent

from . import context_util, bind, const, data, util, rig, propgroups
from .data import Skeleton
from .util import rescale, s2b, PVector, mulmat
from .const import *
from .context_util import *
import array
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')

log = logging.getLogger("avastar.shape")
timerlog = logging.getLogger("avastar.timer")
updatelog = logging.getLogger('avastar.update')
visitlog = logging.getLogger('avastar.visit')
registerlog = logging.getLogger("avastar.register")





MSG_UPDATE_SHAPE = 'Base Shape not found.|'\
                 +  'YOUR ACTION:\n'\
                 +  '- Detach the Sliders (No Sliders)\n'\
                 +  '- Adjust the Avastar Shape to your mesh (if necessary)\n'\
                 +  '  Or load your original character shape from file\n'\
                 +  '- Attach the Sliders again (Avatar Shape).\n'\
                 +  '\nEXPLAIN:\n'\
                 +  'Avastar was looking for the reference Shape of your mesh item.\n'\
                 +  'This reference shape is normally created whenever you attach\n'\
                 +  'the shape sliders to your mesh.\n'\
                 +  'However, the reference shape does not exist in your environment.\n'\
                 +  'This is probably caused by an update from an earlier Avastar version|'




HANDS = {
0:{'id':0, 'label': 'Spread', 'mesh': 'Hands_Spread'},
1:{'id':1, 'label': 'Relaxed', 'mesh': 'hands_relaxed_101'},
2:{'id':2, 'label': 'Point', 'mesh': 'hands_point_102'},
3:{'id':3, 'label': 'Fist', 'mesh': 'hands_fist_103'},
4:{'id':4, 'label': 'L Relaxed', 'mesh': 'hands_relaxed_l_666'},
5:{'id':5, 'label': 'L Point', 'mesh': 'hands_point_l_667'},
6:{'id':6, 'label': 'L Fist', 'mesh': 'hands_fist_l_668'},
7:{'id':7, 'label': 'R Relaxed', 'mesh': 'hands_relaxed_r_669'},
8:{'id':8, 'label': 'R Point', 'mesh': 'hands_point_r_670'},
9:{'id':9, 'label': 'R Fist', 'mesh': 'hands_fist_r_671'},
10:{'id':10, 'label': 'R Salute', 'mesh': 'hands_salute_r_766'},
11:{'id':11, 'label': 'Typing', 'mesh': 'hands_typing_672'},
12:{'id':12, 'label': 'R Peace', 'mesh': 'hands_peace_r_791'},
13:{'id':13, 'label': 'R Splayed', 'mesh': 'hands_spread_r_792'}, 
14:{'id':-1, 'label': 'None', 'mesh': 'Hands_Spread'}
}






































#

#







#



















DEFORMER_NORMALIZE_EXCEPTIONS = ["head_shape_193", "head_length_773", "face_shear_662",
                                 "eye_size_690", "eye_spacing_196", "eye_depth_769"]

def get_shapekeys(context, armobj, obj):
    section = armobj.ShapeDrivers.Sections
    try:
        result = SHAPEUI[section]
    except:
        if section == "Changed":
            result = []
            for section, pids in SHAPEUI.items():
                for pid in pids:
                    D = obj.ShapeDrivers.DRIVERS[pid][0]
                    s = D['sex']
                    if not is_set_to_default(obj,pid):
                        result.append(pid)
        elif section == "Deforming Active Object":
            result = []
            joints = util.get_joint_cache(obj)
            armobj = util.get_armature(obj)
            rig_sections = [B_EXTENDED_LAYER_ALL]
            excludes = []
            bone_set = set(data.get_deform_bones(armobj, rig_sections, excludes))
            mesh_bones = bind.get_binding_bones(context, obj, bone_set)

            for section, pids in SHAPEUI.items():
                for pid in pids:
                    D = obj.ShapeDrivers.DRIVERS[pid][0]
                    slider_bones, joint_count = get_driven_bones(armobj.data.bones, armobj.ShapeDrivers.DRIVERS, D, joints)
                    if mesh_bones & slider_bones.keys():
                        result.append(pid)
        else:
            result = SHAPE_FILTER[section]
    return result

def is_set_to_default(obj, pid):
    if pid == "male_80":
        v = getattr(obj.ShapeDrivers,pid)
        return not v

    ensure_drivers_initialized(obj)
    value   = getShapeValue(obj, pid)
    default = get_default_value(obj,pid)               
    result = fabs(value - default)
    return result < 0.001
    
def get_default_value(obj,pid):
    D = obj.ShapeDrivers.DRIVERS[pid][0]
    if pid == "male_80":
        return False
        
    default = rescale(D['value_default'], D['value_min'], D['value_max'], 0, 100)                        
    return default


def shapeInitialisation():
    
    ##

    ##
    bpy.types.Object.ShapeDrivers   = PointerProperty(type = ShapeDrivers)
    bpy.types.Object.ShapeValues    = PointerProperty(type = ShapeValues)




def terminate():

    del bpy.types.Object.ShapeValues
    del bpy.types.Object.ShapeDrivers
    




def pivotLeftUpdate(self, context):
    pivot_update(context, 'Left')


def pivotRightUpdate(self, context):
    pivot_update(context, 'Right')


def pivot_update(context, side):
    scene = context.scene
    obj = util.get_active_object(context)
    omode=util.set_object_mode('EDIT')
    foot_pivot_update(obj, context, side)
    util.set_object_mode(omode)


def foot_pivot_update(obj, context, side, refresh=True):

    def do_update(val, ikFootBall, ikHeel, ikFootPivot):
        if ikFootBall and ikHeel and ikFootPivot:
            ballh = ikFootBall.head
            heelh = ikHeel.head
            posh = val*(ballh-heelh)+heelh
            ikFootPivot.head = posh

            ballt = ikFootBall.tail
            heelt = ikHeel.tail
            post = val*(ballt-heelt)+heelt
            ikFootPivot.tail = post

    val = obj.IKSwitchesProp.IK_Foot_Pivot_L if side=='Left' else obj.IKSwitchesProp.IK_Foot_Pivot_R
    ikFootBall = obj.data.edit_bones.get('ikFootBall'+side)
    ikHeel = obj.data.edit_bones.get('ikHeel'+side)
    ikFootPivot = obj.data.edit_bones.get('ikFootPivot'+side)
    do_update(val, ikFootBall, ikHeel, ikFootPivot)

    val = obj.IKSwitchesProp.IK_HindLimb3_Pivot_L if side=='Left' else obj.IKSwitchesProp.IK_HindLimb3_Pivot_R
    ikFootBall = obj.data.edit_bones.get('ikHindFootBall'+side)
    ikHeel = obj.data.edit_bones.get('ikHindHeel'+side)
    ikFootPivot = obj.data.edit_bones.get('ikHindFootPivot'+side)
    do_update(val, ikFootBall, ikHeel, ikFootPivot)






def get_driven_bones(dbones, DRIVERS, D, joints, indent=""):
    driven_bones = {}
    driven = D.get('driven', None)
    bones  = D.get('bones', None)
    joint_count = 0
    if bones:
        scales = []
        offsets= []
        for b in bones:
            bname = b['name']
            o = Vector(b.get('offset', V0)).magnitude
            s = b.get('scale', None)
            if s:
                s = Vector(s).magnitude
                if s > 0 or o > 0:
                    dos = driven_bones.get(bname,[False,False])
                    driven_bones[bname] = [o>0 or dos[0], s>0 or dos[1]] 
                    if o>0:
                        offsets.append(bname)
                        dbone = dbones.get(bname,None)
                        mbone = dbones.get('m'+bname,None)
                        if joints and (util.has_head_offset(joints, dbone) or util.has_head_offset(joints, mbone)):
                            joint_count += 1

    if driven:

        for D2 in driven:
            dpid = D2['pid']
            DRIVER = DRIVERS[dpid]
            for DD in DRIVER:
                dpid = DD['pid']

                subbones, hj = get_driven_bones(dbones, DRIVERS, DD, joints, indent+"    ")
                joint_count += hj
                for key,val in subbones.items():
                    dos = driven_bones.get(key,[False,False])
                    driven_bones[key] = [val[0] or dos[0], val[1] or dos[1]] 


    return driven_bones, joint_count

def print_driven_bones(context=None):
    if not context:
        context=bpy.context
    arm = util.get_armature(context.object)
    if not arm:
        return False
    ensure_drivers_initialized(arm)
    DRIVERS= arm.ShapeDrivers.DRIVERS
    joints = util.get_joint_cache(arm)
    text = bpy.data.texts.new("slider_info")
    for key in SHAPEUI.keys():
        text.write("[Section:%s]\n" % key)
        has_entries=False
        for pid in SHAPEUI[key]:
            for D in DRIVERS[pid]:
                dpid = D['pid']
                bones, joint_count = get_driven_bones(arm.data.bones, DRIVERS, D, joints)
                if len(bones) > 0:
                    label = pid
                    if not has_entries:
                        text.write("\n+%s-+-%s-+-%s-%s +\n" % ('-'*30, '-'*25, '-'*5, '-'*5))
                        has_entries=True
                    keys = sorted(bones.keys())
                    for key in keys:
                        val = bones[key]
                        text.write("|%30s | %25s | %5s %5s |\n" % (label, key, 'trans' if val[0] else '', 'scale' if val[1] else ''))
                        label=''
                    text.write("+%s-+-%s-+-%s-%s +\n" % ('-'*30, '-'*25, '-'*5, '-'*5))
        if has_entries:
            text.write("\n")
    return True

def html_driven_bones(context, text_name, HEADER, FOOTER, SECTION, SECTIONELEMENT, br="\n"):
    arm = util.get_armature(context.object)
    if not arm:
        return False
    ensure_drivers_initialized(arm)
    DRIVERS= arm.ShapeDrivers.DRIVERS
    text = bpy.data.texts.new(text_name)
    sections=[]
    joints = util.get_joint_cache(arm)
    for key in SHAPEUI.keys():
        dict = {}
        dict['section'] = key
        sectionelements=[]
        has_influenced_bones = False
        for pid in SHAPEUI[key]:
            for D in DRIVERS[pid]:
                bones, joint_count = get_driven_bones(arm.data.bones, DRIVERS, D, joints)
                if len(bones) > 0:
                    has_influenced_bones = True
                    dict['slider'] = pid[0:pid.rfind('_')].replace('_', ' ').title()
                    bonelist  = []
                    translist = []
                    scalelist = []
                    keys = sorted(bones.keys())
                    for key in keys:
                        val = bones[key]
                        trans = 'trans' if val[0] else '-'
                        scale = 'scale' if val[1] else '-'
                        bonelist.append(key)
                        translist.append(trans)
                        scalelist.append(scale)
                    dict['bonelist']  = br.join(bonelist)
                    dict['translist'] = br.join(translist)
                    dict['scalelist'] = br.join(scalelist)
                    sectionelements.append(SECTIONELEMENT % dict)
        if has_influenced_bones:
            dict['elements'] = "\n".join(sectionelements)
            sections.append(SECTION % dict)
    dict['canvas'] = "\n".join(sections)
    canvas = HEADER % dict
    footer = FOOTER % dict
    text.write(canvas)
    text.write(footer)
    return True

def copy_to_scene(scene, armobj):
    dict = asDictionary(armobj, full=True)
    scene['shape_buffer'] = dict
    return dict


def copy_shape_to_object(obj, armobj):
    dict = asDictionary(armobj, full=True)
    obj['shape_buffer'] = dict
    return dict



def paste_from_scene(scene, armobj):
    shape_data = scene.get('shape_buffer')
    fromDictionary(armobj, shape_data)


def paste_shape_from_object(obj, armobj):
    shape_data = obj.get('shape_buffer')
    if shape_data:
        fromDictionary(armobj, shape_data)


class ShapeCopy(bpy.types.Operator):
    """Copy Current Shape from active Armature into a temporary shape Buffer"""
    bl_idname = "avastar.shape_copy"
    bl_label = "Copy Shape"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        ob = context.object
        armobj = util.get_armature(ob)
        return armobj != None

    def execute(self, context):
        ob = context.object
        arm_obj = util.get_armature(ob)
        copy_to_scene(context.scene, arm_obj)
        return {'FINISHED'}

class ShapeDebug(bpy.types.Operator):
    """create new object from Basis Shape"""
    bl_idname = "avastar.shape_debug"
    bl_label = "Object from Basis Shape"
    bl_options = {'REGISTER', 'UNDO'}
    
    shape : EnumProperty(
        items=(
            (REFERENCE_SHAPE, 'Original Shape', "Original Mesh"),
            (NEUTRAL_SHAPE, 'Neutral Shape', "Calculated restpose mesh"),
            (MORPH_SHAPE, 'Bone Morph Shape', "Calculated morphed mesh")),
        name = "Shape",
        description="Base Shape for Morphing",
        default=REFERENCE_SHAPE)

    @classmethod
    def poll(self, context):
        ob = context.object
        val = ob is not None and ob.type=='MESH'
        return val

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "shape")

    def invoke(self, context, event):
        self.shape=REFERENCE_SHAPE
        return self.execute(context)

    def execute(self, context):
        ob = context.object
        if self.shape in ob:
            nob_name = ob.name + "_" + self.shape

            if nob_name in bpy.data.objects:
                nob = bpy.data.objects[nob_name]
                location = nob.location
                util.remove_object(context, nob)
            else:
                location = ob.location

            nob = ob.copy()
            nob.data = ob.data.copy()
            nob.name = nob_name
            nob.location = location
            

            co = get_shape_data(nob, self.shape)
            nob.data.vertices.foreach_set('co',co)
            util.link_object(context, nob)
            util.set_active_object(context, nob)
            util.object_select_set(nob, True)
            util.update_view_layer(context)

        return {'FINISHED'}

class ShapePaste(bpy.types.Operator):
    """Paste Shape from internal shape Buffer into active Avastar Armature"""
    bl_idname = "avastar.shape_paste"
    bl_label = "Paste Shape"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        ob = context.object
        armobj = util.get_armature(ob)
        if armobj == None:
            return False
        return context.scene.get('shape_buffer') != None

    def execute(self, context):
        ob = context.object
        arm_obj = util.get_armature(ob)
        paste_from_scene(context.scene, arm_obj)
        return {'FINISHED'}
    
class PrintSliderRelationship(bpy.types.Operator):
    """Print slider relationship to console"""
    bl_idname = "avastar.print_slider_relationship"
    bl_label = "Slider Details"
    
    WP_HEADER        = "%(canvas)s"
    WP_FOOTER        = ""
    WP_BR            = "\n"
    WP_SECTION       = '[symple_toggle title="%(section)s" state="closed"] %(elements)s [/symple_toggle]'
    WP_SECTIONELEMENT='''
<div class="row-fluid">
<div class="rhcol span4">%(slider)s</div>
<div class="rhcol span4">%(bonelist)s</div>
<div style="text-align: center;" class="rhcol span2">%(translist)s</div>
<div style="text-align: center;" class="rhcol span2">%(scalelist)s</div>
</div>'''

    HTML_HEADER        = '''<html>
<head>
<style>
.page      {font-family: "Segoe UI",Arial,sans-serif;}
.section   {padding:1px;}
.slider    {padding-left: 15px; vertical-align:top; width:15em;}
.bonelist  {padding-left: 15px; vertical-align:top; width:15em;}
.translist {padding-left: 15px; padding-right:15px;text-align: center; vertical-align:top;}
.scalelist {padding-left: 15px; padding-right:15px;text-align: center; vertical-align:top;}
</style>
</head>
<body class="page">%(canvas)s'''
    HTML_FOOTER        = "</body></html>"
    HTML_BR            = "<br/>\n"
    HTML_SECTION       = '<h2>%(section)s</h2> <table border style="background-color:#dddddd;padding:10px;">%(elements)s</table>'
    HTML_SECTIONELEMENT='''
<tr class="section">
<td class="slider">%(slider)s</td>
<td class="bonelist">%(bonelist)s</td>
<td class="translist">%(translist)s</td>
<td class="scalelist">%(scalelist)s</td>
</tr>'''
    
    @classmethod
    def poll(self, context):
        ob = context.object
        return ob and ob.type=='ARMATURE'

    def execute(self, context):

        html_driven_bones(context, "slider_info_html", self.HTML_HEADER, self.HTML_FOOTER, self.HTML_SECTION, self.HTML_SECTIONELEMENT, self.HTML_BR)
        html_driven_bones(context, "slider_info_wp", self.WP_HEADER, self.WP_FOOTER, self.WP_SECTION, self.WP_SECTIONELEMENT, self.WP_BR)
        return {'FINISHED'}


def createShapeDrivers(DRIVERS):


    sectionitems = []
    for section in SHAPE_FILTER.keys():
        sectionitems.append((section, section, section))
    for section in SHAPEUI.keys():
        sectionitems.append((section, section, section))

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

                                    update=eval("lambda a,b:shape_slider_driver(a,b,'%s')"%pid),
                                    description = "Gender switch\ndisabled:Female\nenabled:Male",
                                    default = False))

            else:

                default = rescale(D['value_default'], D['value_min'], D['value_max'], 0, 100)
                description = "%s - %s"%(D['label_min'], D['label_max'])
                setattr(target, pid,  
                        IntProperty(name = D['label'], 

                                    update=eval("lambda a,b:shape_slider_driver(a,b,'%s')"%pid),
                                    description = description,
                                    min      = 0, max      = 100,
                                    soft_min = 0, soft_max = 100,
                                    default = int(round(default))))

                setattr(values, pid,  
                        FloatProperty(name = D['label'], 
                                    min      = 0, max      = 100,
                                    soft_min = 0, soft_max = 100,
                                    default = default))



def createMeshShapes(MESHES):



    MESHSHAPES = {}
    
    for mesh in MESHES.values():
        util.progress_update(10, False)
        meshname = mesh['name']
        MESH = {'name':meshname}



        WEIGHTS = {} 
        if 'skinJoints' in mesh:
            for joint in mesh['skinJoints']:
                WEIGHTS[joint] = {}
            
            for vidx, (bi, w) in enumerate(mesh['weights']):
                if vidx in mesh['vertexRemap']:
                    continue
                i = data.getVertexIndex(mesh, vidx)
                b1, b2 = data.WEIGHTSMAP[meshname][bi]
                WEIGHTS[b1][i] = 1-w
                if b2 is not None:
                    WEIGHTS[b2][i] = w
        MESH['weights'] = WEIGHTS



        SHAPE_KEYS= {}
        for pid, morph in mesh['morphs'].items():
            util.progress_update(1, False)

            DVS = {} 
            for v in morph['vertices']:
                ii = v['vertexIndex']
                if ii in mesh['vertexRemap']:
                    continue
                dv = v['coord']
                DVS[data.getVertexIndex(mesh, ii)] = dv

            BONEGROUPS={}
            dvset = set(DVS)
            for bone, weights in WEIGHTS.items():
                IWDVs = []
                for vid in dvset.intersection(weights):
                    IWDVs.append( (vid, WEIGHTS[bone][vid], DVS[vid]) )
                BONEGROUPS[bone] = IWDVs

            SHAPE_KEYS[pid] = BONEGROUPS
        MESH['shapekeys'] = SHAPE_KEYS



        verts = [mesh['baseCoords'][i] for i in mesh['vertLookup']]
        co = [item for sublist in verts for item in sublist]
        MESH['co'] = co

        MESHSHAPES[meshname]=MESH
    
    ShapeDrivers.MESHSHAPES = MESHSHAPES

def initialize(rigType):
    log.debug("Loading Avastar Shape Interface for rigType %s" % (rigType))
    progress=100
    util.progress_begin()
    log.debug("Loading Avastar DRIVER data rigType %s" % (rigType))
    DRIVERS = data.loadDrivers()
    util.progress_update(progress, False)
    log.debug("Create Avastar DRIVERS for rigType %s" % (rigType))
    createShapeDrivers(DRIVERS)
    util.progress_update(progress, False)
    log.debug("Loading Avastar MESH data rigType %s" % (rigType))
    MESHES = data.loadMeshes()
    util.progress_update(progress, False)
    log.debug("Loading Avastar MESHES for rigType %s" % (rigType))
    createMeshShapes(MESHES)
    util.progress_end()

def ensure_drivers_initialized(obj):
    if not hasattr(obj.ShapeDrivers, 'DRIVERS'):
        log.debug("%s %s has no Shape Drivers" % (obj.type, obj.name) )
        arm = util.get_armature(obj)
        if arm:
            log.info("Initialise Shape Drivers...")
            rigType = arm.RigProp.RigType
            omode = util.ensure_mode_is("OBJECT")
            initialize(rigType)
            util.ensure_mode_is(omode)

def getShapeValue(obj, pid, normalize=False):



    if pid=="male_80":
        value = getattr(obj.ShapeDrivers,pid)
    else:
        if normalize and pid in SHAPE_FILTER["Skeleton"] and not pid in DEFORMER_NORMALIZE_EXCEPTIONS:
            value = get_default_value(obj,pid)
        else:
            value   = obj.ShapeValues.get(pid)
            if value is None:
                value = getattr(obj.ShapeDrivers,pid)
    return value

def setShapeValue(obj, pid, default, min, max, prec=False):
    if pid=="male_80":

        obj.ShapeDrivers[pid] = default
    else:
        v = rescale(default, min, max, 0, 100)

        obj.ShapeValues[pid]  = v
        obj.ShapeDrivers[pid] = v if prec else int(round(v))



def printProperties(obj):
    male = obj.ShapeDrivers.male_80
    blockname = "Shape for: '%s'"%obj.name 
    textblock = bpy.data.texts.new(blockname)
   
    textblock.write("Shape sliders for '%s' (%s)\n"%(obj.name, time.ctime()))
    textblock.write("Custom values marked with 'M' at begin of line.\n")
    
    ensure_drivers_initialized(obj)
    for section, pids in SHAPEUI.items():
        textblock.write("\n=== %s ===\n\n"%section)
        for pid in pids:
            D = obj.ShapeDrivers.DRIVERS[pid][0]
            s = D['sex']
            modified = "M"
            if is_set_to_default(obj,pid):
                modified = " "
                
            if s is None or (s=='male' and male==True) or (s=='female' and male==False):
                textblock.write("%c  %s: %d\n"%(modified, D["label"], round(getShapeValue(obj, pid))))                

    logging.info("Wrote shape data to textblock '%s'",blockname)

    return blockname


def fromDictionary(obj, dict, update=True, init=False):
    armobj = util.get_armature(obj)
    log.info("|- Paste shape from dictionary to [%s]" % (armobj.name) )

    armobj.ShapeDrivers.Freeze = 1
    pidcount = 0
    for pid, v in dict.items():
        if pid=="male_80":
            v = v > 0
            armobj.ShapeDrivers[pid] = v
        elif pid=='section':
            armobj.ShapeDrivers.Sections=v
        else:
            armobj.ShapeValues[pid]  = v
            armobj.ShapeDrivers[pid] = int(round(v))
        pidcount += 1


    armobj.ShapeDrivers.Freeze = 0
    scene = bpy.context.scene

    if update:
        context = bpy.context


        refreshAvastarShape(context, refresh=True, init=init)


        log.info("|- Updated shape of [%s]" % (armobj.name) )

    log.info("|- Updated %d pids for in [%s]" % (pidcount, armobj.name) )


def asDictionary(obj, full=False):
    armobj = util.get_armature(obj)
    ensure_drivers_initialized(armobj)

    log.info("|- Copy shape from [%s] to dictionary" % (armobj.name) )

    dict = {}
    male = armobj.ShapeDrivers.male_80
    section = armobj.ShapeDrivers.Sections
    if section:
        dict['section']=section
    

    pidcount = 0
    for section, pids in SHAPEUI.items():
        modified = [pid for pid in pids if (pid != 'male_80' and (full or not is_set_to_default(armobj,pid)))]
        for pid in modified:
            D     = armobj.ShapeDrivers.DRIVERS[pid][0]
            sex   = D['sex']
            if True: #sex is None or (sex=='male' and male==True) or (sex=='female' and male==False):
                dict[pid]  = getattr(armobj.ShapeValues,pid)
                pidcount += 1

    log.info("|- Added %d pids to dictionary of [%s]" % (pidcount, armobj.name) )
    return dict

def saveProperties(obj, filepath, normalize=False, pack=False):

        

   
    comment = et.Comment("Generated with Avastar on %s"%time.ctime())
    comment.tail = os.linesep
    pool = et.Element('linden_genepool', attrib={'version':'1.0'})  
    pool.tail = os.linesep
    xml = et.ElementTree(pool) 
    archetype = et.Element('archetype', attrib={'name': obj.name})   
    archetype.tail = os.linesep
    pool.append(comment)
    pool.append(archetype)

    ensure_drivers_initialized(obj) 
    male = getShapeValue(obj,'male_80')
    for section, pids in SHAPEUI.items():
        for pid in pids:
            D = obj.ShapeDrivers.DRIVERS[pid][0]
            s = D['sex']
            if s is None or (s=='male' and male==True) or (s=='female' and male==False):

                np   = pid.split("_")
                id   = np[-1]
                name = np[:-1]
            
                if id == "80":
                    v = 0.0
                    if male: v += 1.0
                else:
                    value100 = getShapeValue(obj, pid, normalize)
                    v    = rescale(value100, 0, 100, D['value_min'], D['value_max']) 
                
                data = {
                'id':id,
                'name':'_'.join(name),
                'value':"%.3f"%v,
                }
                
                item = et.Element('param', attrib=data)
                item.tail = os.linesep
                archetype.append(item)
                
    if pack:
        blockname = filepath
        if blockname in bpy.data.texts:
            textblock = bpy.data.texts[blockname]
            textblock.clear()
        else:
            textblock = bpy.data.texts.new(blockname)
        root = root=xml.getroot()
        textblock.write(et.tostring(root).decode())
    else:
        xml.write(filepath, xml_declaration=True)
    return filepath


RESTPOSE_FEMALE={
    'hip_length_842' : 50.000000,
    'forehead_angle_629' : 50.000000,

    'lip_width_155' : 40.909091,
    'height_33' : 53.488372,
    'eyelid_inner_corner_up_880' : 52.000000,
    'shoe_heels_197' : 0.000000,
    'thickness_34' : 31.818182,
    'lip_cleft_deep_764' : 45.454545,
    'wide_nose_bridge_27' : 52.000000,
    'big_brow_1' : 13.043478,
    'hip_width_37' : 53.333333,
    'shift_mouth_663' : 50.000000,
    'head_shape_193' : 50.000000,
    'jaw_angle_760' : 37.500000,
    'eye_size_690' : 50.000000,
    'deep_chin_185' : 50.000000,
    'tall_lips_653' : 33.333333,
    'male_package_879' : 20.000000,
    'torso_length_38' : 50.000000,
    'platform_height_503' : 0.000000,
    'weak_chin_7' : 50.000000,
    'bulbous_nose_tip_6' : 40.000000,
    'shoulders_36' : 56.250000,
    'eyebrow_size_119' : 0.000000,
    'broad_nostrils_4' : 33.333333,
    'eye_depth_769' : 50.000000,
    'square_jaw_17' : 33.333333,
    'jaw_jut_665' : 50.000000,
    'squash_stretch_head_647' : 33.333333,
    'double_chin_8' : 25.000000,
    'baggy_eyes_23' : 25.000000,
    'wide_nose_517' : 33.333333,
    'leg_length_692' : 50.000000,

    'eyelid_corner_up_650' : 52.000000,
    'noble_nose_bridge_11' : 25.000000,
    'hand_size_675' : 50.000000,
    'nose_big_out_2' : 24.242424,
    'wide_lip_cleft_25' : 34.782609,
    'lower_bridge_nose_758' : 50.000000,
    'arm_length_693' : 50.000000,
    'pointy_eyebrows_16' : 14.285714,
    'low_septum_nose_759' : 40.000000,
    'wide_eyes_24' : 42.857143,
    'head_size_682' : 71.428571,
    'ears_out_15' : 25.000000,
    'neck_thickness_683' : 66.666667,
    'puffy_upper_cheeks_18' : 37.500000,
    'high_cheek_bones_14' : 33.333333,
    'big_ears_35' : 33.333333,
    'mouth_height_506' : 50.000000,
    'crooked_nose_656' : 50.000000,
    'arced_eyebrows_31' : 0.000000,
    'egg_head_646' : 100-56.521739,
    'bulbous_nose_20' : 25.000000,
    'eyebone_head_shear_661' : 50.000000,
    'pointy_ears_796' : 11.764706,
    'puffy_lower_lids_765' : 10.714286,
    'sunken_cheeks_10' : 33.333333,
    'eyebone_head_elongate_772' : 50.000000,

    'lower_eyebrows_757' : 66.666667,
    'upturned_nose_tip_19' : 60.000000,
    'upper_eyelid_fold_21' : 13.333333,
    'eyebone_big_eyes_689' : 50.000000,
    'eye_spacing_196' : 50.000000,
    'neck_length_756' : 50.000000,
    "butt_size_795":30,
}

def get_restpose_values(armobj, generate=False):
    
    if not generate:
        return RESTPOSE_FEMALE

    RESTPOSE = {}
    ensure_drivers_initialized(armobj)
    for D in armobj.ShapeDrivers.DRIVERS.values():
        for P in D:
            if P['type'] == 'bones':
                pid = P.get('pid')
                min = P.get('value_min')
                max = P.get('value_max')
                val = P.get('value_default', 0)
                fv = 100 * (val - min) / (max - min)
                RESTPOSE[pid] = fv
    return RESTPOSE


def reset_to_shape(arm_obj, posedata=None, preserveGender=True):
    arm_obj['is_in_restpose'] = False
    for pids in SHAPEUI.values():
        for pid in pids:
            if pid == "male_80" and preserveGender:

                continue

            P = arm_obj.ShapeDrivers.DRIVERS.get(pid,None)
            if not P:
                continue
            D = P[0]

            if posedata and pid in posedata:
                v = posedata[pid]
                arm_obj.ShapeValues[pid]  = v
                arm_obj.ShapeDrivers[pid] = int(round(v))

            else:
                setShapeValue(arm_obj,pid,D['value_default'], D['value_min'], D['value_max'])

def reset_to_restpose(context, arm_obj):
    omode = util.ensure_mode_is("OBJECT")
    ensure_drivers_initialized(arm_obj)
    arm_obj.RigProp.Hand_Posture = HAND_POSTURE_DEFAULT
    resetToRestpose(arm_obj, context)
    util.ensure_mode_is(omode)

def resetToRestpose(arm_obj, context=None, preserveGender=True, init=False, force_update=False):
    if not context: context = bpy.context
    scene=context.scene

    arm_obj.ShapeDrivers.Freeze = 1
    RESTPOSE = get_restpose_values(arm_obj, generate=False)
    resetToPose(arm_obj, RESTPOSE, context, preserveGender, init, force_update)
    arm_obj['is_in_restpose'] = True
    rig.set_appearance_editable(context, False, armobj=arm_obj)

def resetToBindpose(arm_obj, context=None, preserveGender=True, init=False, force_update=False):
    if not context: context = bpy.context

    arm_obj.ShapeDrivers.Freeze = 1
    binding = arm_obj.get(SHAPE_BINDING)
    bindpose = None
    if binding:
        bindpose =  binding.get('values')

    if not bindpose:
        bindpose = get_restpose_values(arm_obj)

    resetToPose(arm_obj, bindpose, context, preserveGender, init, force_update)

def resetToPose(arm_obj, posedata, context, preserveGender, init, force_update):
    scene=context.scene


    arm_obj.ShapeDrivers.Freeze = 1
    reset_to_shape(arm_obj, posedata, preserveGender)
    arm_obj.ShapeDrivers.Freeze = 0

    refreshAvastarShape(context)
    util.enforce_armature_update(context, arm_obj)
    arm_obj.RigProp.restpose_mode = True
    arm_obj['is_in_restpose'] = False



def resetToDefault(arm, context=None):
    if not context:
        context = bpy.context

    active = context.active_object
    util.set_active_object(context, arm)
    reset_to_default(context)
    util.set_active_object(context, active)

def reset_to_default(context):
    scene=context.scene
    armobj = context.active_object


    armobj.ShapeDrivers.Freeze = 1
    reset_armature_weight_groups(context, armobj)
    reset_to_shape(armobj, posedata=None, preserveGender=True)
    resetEyes(armobj)
    armobj.ShapeDrivers.Freeze = 0

    refreshAvastarShape(context)
    update_tail_info(context, armobj)
    util.enforce_armature_update(context, armobj)
    armobj.RigProp.restpose_mode = False


def resetEyes(armobj):
    factor = 20
    util.adjust_eye_target_distance(armobj, factor, 'Eye')
    util.adjust_eye_target_distance(armobj, factor, 'FaceEyeAlt')


def update_tail_info(context, armobj, remove=False):
    if context == None:
        context = bpy.context

    active = context.object
    active_mode = active.mode
    arm_mode = armobj.mode

    if active != armobj:
        util.set_active_object(context, armobj)

    util.ensure_mode_is("EDIT")
    joints = util.get_joint_cache(armobj)

    for bone in armobj.data.edit_bones:
        key, joint = rig.get_joint_for_bone(joints, bone)
        util.remove_head_offset(bone)
        util.remove_tail_offset(bone)
        if remove or joint == None:
            if 'bhead' in bone: del bone['bhead']
            if 'btail' in bone: del bone['btail']
            if 'joint' in bone: del bone['joint']

    util.ensure_mode_is(arm_mode)
    if active != armobj:
        util.set_active_object(context, active)
        util.ensure_mode_is(active_mode)


def manage_avastar_shapes(context, armobj, ids):
    shapes = util.getChildren(armobj, type="MESH")
    meshes = {c.get('mesh_id'):c for c in shapes if 'mesh_id' in c and util.is_avastar_mesh(c)}

    for child in meshes.values():
        key = child.get('mesh_id')
        if key not in ids:
            util.remove_object(context, child)

    for key in ids:
        if key not in meshes.keys():
            log.warning("TODO: Need to add missing %s" % key)
    


@persistent
def update_on_framechange(scene):

    if util.handler_can_run(scene, check_ticker=False):
        log.debug("handler [%s] started" % "update_on_framechange")
    else:
        return

    context=bpy.context
    view_layer = context.view_layer

    active = None
    omode  = None

    try:
        for armobj in [obj for obj in view_layer.objects if obj.type=="ARMATURE" and "avastar" in obj]:
            if armobj.animation_data and armobj.animation_data.action:
                if not (hasattr(armobj, 'ShapeDrivers') and hasattr(armobj.ShapeDrivers, 'DRIVERS')):
                    ensure_drivers_initialized(armobj)

                update = False

                try:
                    recurse_call = True
                    armobj.ShapeDrivers.Freeze = 1


                    animated_pids = [fcurve.data_path.split(".")[1] for fcurve in armobj.animation_data.action.fcurves if fcurve.data_path.split(".")[0]=='ShapeDrivers']
                    
                    for pids in SHAPEUI.values():
                        for pid in pids:
                            if pid in animated_pids:
                                D = armobj.ShapeDrivers.DRIVERS[pid][0]
                                if pid != 'male_80':
                                    v100 = getattr(armobj.ShapeDrivers, pid)
                                    vorg = getattr(armobj.ShapeValues, pid)
                                    if vorg != v100:

                                        armobj.ShapeValues[pid] = float(v100)
                                        update=True
                                        active = util.get_active_object(context)
                                        omode  = active.mode if active else None
                                        break
                    if update:

                        util.set_active_object(bpy.context, armobj)
                        armobj.ShapeDrivers.Freeze = 0
                        refreshAvastarShape(context)
                except:



                    logging.warn("Could not initialise Armature %s (Maybe not an Avastar ?)", armobj.name)
                    print(traceback.format_exc())
                    raise
                finally:
                    armobj.ShapeDrivers.Freeze = 0
                    recurse_call = False
                if update:

                    foot_pivot_update(armobj, context, 'Left', False)
                    foot_pivot_update(armobj, context, 'Right', True)

    except:
        print("Stepped out of update shape due to exception.")
        print(traceback.format_exc())
        pass #raise
    finally:
        if active and omode:
            util.set_active_object(context, active)
            util.ensure_mode_is(omode)


def loadProps(context, obj, filepath, pack=False):
    
    ensure_drivers_initialized(obj)

    obj.ShapeDrivers.Freeze = 1

    if pack:
        blockname = filepath
        if blockname in bpy.data.texts:
            textblock = bpy.data.texts[blockname]
            txt=textblock.as_string()
            xml=et.XML(txt)
        else:
            return
    else:
        xml=et.parse(filepath)



    for item in xml.getiterator('param'):
        nid = "%s"%item.get('id')
        pname = item.get('name') # this tends to be lowercase
        value = float(item.get('value'))

        pid = None
        for driver in obj.ShapeDrivers.DRIVERS.keys():
            if driver.endswith("_"+nid):
                pid = driver
                break

        if pid is None:
            logging.debug("ignoring shape key: %s (%s)",pname, nid)
            continue

        if pid=="male_80":
            value = value > 0


        D = obj.ShapeDrivers.DRIVERS[pid][0]
        setShapeValue(obj,pid,value, D['value_min'], D['value_max'])

    obj.ShapeDrivers.Freeze = 0
    refreshAvastarShape(context, refresh=True)


def get_binding_data(armobj, dbone, use_cache, normalize=True):
    BoneLoc0, t = rig.get_custom_restposition(armobj, dbone, use_cache)
    MScale, sb  = util.getBoneScaleMatrix(armobj, dbone, normalize=normalize)
    BoneLoc,  t = rig.get_custom_bindposition(armobj, dbone, use_cache)
    return BoneLoc0, BoneLoc, MScale




def update_system_shapekeys(context, armobj, meshobjs, hover, changed_bones, force_all_meshes):
    bone_scales = {}
    bones = util.get_modify_bones(armobj)
    ensure_drivers_initialized(armobj)

    for mname,  meshobj in meshobjs.items():

        if not util.object_visible_get(meshobj, context=context):

            continue

        MESH = get_reference_for_mesh(mname, meshobj)

        if not MESH:
            log.error("Shape Drivers for %s no longer exists (can not apply sliders)" % mname)
            continue

        mesh_weights = MESH['weights'].items()
        if is_shape_unchanged(changed_bones, mesh_weights, force_all_meshes):

            continue

        update_system_shapekey(armobj, bones, meshobj, MESH, hover, mesh_weights, bone_scales)

    return

def update_system_shapekey(armobj, bones, meshobj, MESH, hover, mesh_weights, bone_scales):


    co = list(MESH['co'])


    shapekey_items = MESH['shapekeys'].items()

    dco = create_reference_shape(co, armobj, bones, meshobj, mesh_weights)
    dco = [f - hover.z if (i+1)%3==0 else f for i,f in enumerate(dco)]

    keyblocks = meshobj.data.shape_keys.key_blocks
    keyblocks[0].data.foreach_set('co',dco)
    
    for pid, SK in shapekey_items:
        sk_items = SK if type(SK) == list else SK.items() 
        if len(sk_items) == 0:
            continue

        co2 = dco.copy()
        if type(sk_items) is list:
            for vi, val in enumerate(sk_items):
                co2[vi]   += sk_items[vi]
        else:
            for bname, IWDVs in sk_items:

                if len(IWDVs) == 0:
                    continue

                scale = get_bone_scale_from_cache(bone_scales, bones, bname)
                for vi,w,dv in IWDVs:

                    x=3*vi
                    y=x+1
                    z=x+2

                    co2[x] += w*dv[0]*scale[0]
                    co2[y] += w*dv[1]*scale[1]
                    co2[z] += w*dv[2]*scale[2]

        try:
            keyblocks[pid].data.foreach_set('co',co2)
        except:
            logging.debug("Morph shape_key not found: pid %s" % pid)

    meshobj.update_tag()
    return


def get_bone_scale_from_cache(bone_scales, bones, bname):
    scale = bone_scales.get(bname)
    if not scale:
        scale = util.get_bone_scale(bones[bname])
        bone_scales[bname] = scale
    return scale


def create_reference_shape(co, armobj, bones, meshobj, mesh_weights):



    dco = co.copy()
    if mesh_weights:
        mask = [0]*int(len(co)/3)
        for bname, weights in mesh_weights:
            dbone = bones[bname]
            if dbone.use_deform:
                BoneLoc0, BoneLoc, MScale = get_shape_transform(armobj, dbone, use_cache=True)
                if BoneLoc0==None:
                    continue

                for vi,w in weights.items():
                    if abs(w) > 0:
                        offset = 3*vi
                        vertLocation   = Vector(co[offset:offset+3])
                        targetLocation = mulmat(MScale, (vertLocation - BoneLoc0)) + BoneLoc
                        L              = w * targetLocation

                        if mask[vi]:
                            dco[offset  ] += L[0]
                            dco[offset+1] += L[1]
                            dco[offset+2] += L[2]
                        else:
                            mask[vi] = 1
                            dco[offset  ] = L[0]
                            dco[offset+1] = L[1]
                            dco[offset+2] = L[2]
    return dco


def get_reference_for_mesh(name, meshobj):
    reference_name = meshobj.get('mesh_id')
    if not reference_name:
        reference_name = name
    return meshobj.ShapeDrivers.MESHSHAPES.get(reference_name)
    

def is_shape_unchanged(changed_bones, mesh_weights, force_all_meshes):
    if force_all_meshes:
        return False
    for bname, weights in mesh_weights:
        if bname in changed_bones:
            return False
    return True





@persistent
def check_dirty_mesh_on_load(scene):
    check_dirty_mesh(scene)

@persistent
def check_dirty_mesh_on_update(scene):

    if util.handler_can_run(scene, check_ticker=False):
        log.debug("handler [%s] started" % "check_dirty_mesh_on_update")
        check_dirty_mesh(scene)


def check_dirty_mesh(scene):
    context = bpy.context
    active = util.get_active_object(context)
    if not active or active.type !='MESH' or (DIRTY_SHAPE in active and active.mode=='EDIT') or not util.is_in_user_mode():
        return

    armobj = util.get_armature(active)
    if not armobj:
        return

    if active.mode == 'EDIT' and not active.get(CHECKSUM):

        active[CHECKSUM] = util.calc_object_checksum(active)
        return

    if active.mode == 'EDIT':
        if armobj and armobj.get('avastar') and scene.SceneProp.panel_appearance_enabled and not 'avastar-mesh' in active:
            active[DIRTY_MESH] = True

            shape_keys = active.data.shape_keys
            if  shape_keys:
                active[DIRTY_SHAPE] = True
    else:
        if DIRTY_MESH in active:

            if not rig.need_rebinding(armobj, [active]):
                del active[DIRTY_MESH]
                return

            mode = active.mode
            if util.getAddonPreferences().enable_auto_mesh_update or scene.MeshProp.auto_rebind_mesh:
                from . import mesh

                if mode == 'WEIGHT_PAINT':
                    util.mode_set('OBJECT')
                del active[DIRTY_MESH]
                mesh.ButtonRebindArmature.execute_rebind(context, scene.SceneProp.apply_as_bindshape)
                generateMeshShapeData(active)

                if mode == 'WEIGHT_PAINT':
                    util.mode_set(mode)


def add_shapekey_updater(self, context):
    ui_level = util.get_ui_level()
    if ui_level < UI_ADVANCED:
        return

    obj = context.object
    if not (obj.type=='MESH' and obj.data.shape_keys and obj.data.shape_keys.key_blocks):
        return

    armobj = util.get_armature(obj)
    if not armobj:
        return

    if 'avastar' in armobj and not 'avastar-mesh' in obj:
        animation_data = obj.data.shape_keys.animation_data
        if animation_data:
            drivers = animation_data.drivers
            if drivers and len(drivers) > 0:
                preferences = util.getPreferences()
                col = self.layout.column()
                col.prop(preferences.system,"use_scripts_auto_execute", icon=ICON_SCRIPT, text='')

def shapes_from_object(meshobj, armobj, mesh_weights):
    log.warning("bind shape keys for Mesh [%s] in Armature [%s]" % (meshobj.name, armobj.name) )
    shape_data = {}

    shape_keys = meshobj.data.shape_keys
    if not shape_keys:
        return shape_data

    key_blocks = shape_keys.key_blocks
    if not key_blocks:
        return shape_data

    for index, block in enumerate(key_blocks):
        if index == 0:
            log.warning("Get reference shape from block [%s]" % (block.name) )
            base_mesh = util.fast_get_verts(meshobj.data.vertices).copy()
            continue
        else:
            co = util.fast_get_verts(block.data).copy()

        count = min(len(co), len(base_mesh)) # to not fall into the edit mesh trap
        co = co.copy()
        for i in range(0,count):
            co[i] = co[i] - base_mesh[i]
        shape_data[block.name] = co.copy() # Here the keys are strings and the values are distances to the reference mesh

    return shape_data

def create_meshshape(mname, meshobj, armobj):
    MESH = {}
    MESH['name'] = mname
    MESH['co'] = util.fast_get_verts(meshobj.data.vertices)
    MESH['weights'] = weights_from_groups(meshobj, deforming=True)
    MESH['shapekeys'] = shapes_from_object(meshobj, armobj, MESH['weights'])
    MESH['hover'] = get_custom_hover(meshobj)
    return MESH


def add_meshshape_to_cache(mname, meshobj, armobj, MESHSHAPES_CACHE):
    MESH = create_meshshape(mname, meshobj, armobj)
    MESHSHAPES_CACHE[mname] = MESH
    return MESH


def getMESH(mname, meshobj, armobj, use_cache=True):
    if use_cache:
        MESH = None
        if hasattr(meshobj, 'ShapeDrivers'):
            DRIVERS = meshobj.ShapeDrivers
            if hasattr(DRIVERS, 'MESHSHAPES'):
                MESHSHAPES = DRIVERS.MESHSHAPES
                MESH = MESHSHAPES.get(mname)
                if not MESH:
                    log.warning("Apply sliders to morphs (getMesh): Adding MESH info for name %s - object %s" % (mname, meshobj.name) )
                    MESH = add_meshshape_to_cache(mname, meshobj, armobj, MESHSHAPES)
    else:
        MESH = create_meshshape(mname, meshobj, armobj)
    return MESH
    
def removeMESH(mname, meshobj):
    MESH = None
    if hasattr(meshobj, 'ShapeDrivers'):
        DRIVERS = meshobj.ShapeDrivers
        if hasattr(DRIVERS, 'MESHSHAPES'):
            MESHSHAPES = DRIVERS.MESHSHAPES
            MESH = MESHSHAPES.get(mname)
            if MESH:
                log.warning("Apply sliders to morphs (removeMesh): Removing MESH info for name %s - object %s" % (mname, meshobj.name) )
                del MESHSHAPES[mname]
    return MESH

def generateMeshShapeData(meshobj):
    if not meshobj:
        return

    armobj = util.get_armature(meshobj)
    if not armobj:
        return

    if not hasattr(armobj.ShapeDrivers, 'DRIVERS'):
        return

    mname = meshobj.name
    MESHSHAPES = meshobj.ShapeDrivers.MESHSHAPES
    add_meshshape_to_cache(mname, meshobj, armobj, MESHSHAPES)
    if DIRTY_SHAPE in meshobj:
        del meshobj[DIRTY_SHAPE]

def bindBoneScales(co, armobj, child, mesh_weights, inverse=False):
    dco = [0.0]*len(co)
    mask = [0]*int(len(co)/3)
    hobj = get_custom_hover(child)
    harm = get_floor_hover(armobj)
    
    for bname, weights in mesh_weights.items():
        dbone = armobj.data.bones.get(bname)
        if not dbone:
            log.debug("bind Bone Scales: Vertex group %s has no bone in armature %s" % (bname, armobj.name) )
            continue

        BoneLoc0, BoneLoc, MScaleLocal = calculate_shape_transform(armobj, child, bname, init=inverse, use_binding=True, use_cache=True)
        if not BoneLoc0:
            continue

        for index, weight in weights.items():

            offset = 3 * index
            vertLocation   = Vector(co[offset:offset+3])
            targetLocation = mulmat(MScaleLocal, (vertLocation - BoneLoc0+hobj)) + BoneLoc-hobj
            L              = weight * targetLocation

            dco[offset]   += L[0]
            dco[offset+1] += L[1]
            dco[offset+2] += L[2]

            mask[index] = 1

    hover = hobj-harm
    for index in range(len(mask)):
        if mask[index]:
            ii = 3*index
            co[ii]   = dco[ii  ] + hover[0]
            co[ii+1] = dco[ii+1] + hover[1]
            co[ii+2] = dco[ii+2] + hover[2]

def apply_shapekeys_to_custom_meshes(context, armobj, mname, meshobj):
        




    start = time.time()
    bones = util.get_modify_bones(armobj)    


    if util.object_visible_get(meshobj, context=context):
        log.debug("Apply sliders to custom mesh: Propagate morph sliders for Custom Mesh %s" % meshobj.name)
    else:

        log.debug("Apply sliders to morphs: Custom Mesh %s is not visible (skip)" % meshobj.name)
        return

    shape_keys = meshobj.data.shape_keys
    if not shape_keys:
        log.debug("Apply sliders to custom mesh: Custom Mesh %s has no Shape Keys (skip)" % (meshobj.name) )

        return

    key_blocks = shape_keys.key_blocks
    if not key_blocks or len(key_blocks) == 0:
        log.debug("Apply sliders to custom mesh: Custom Mesh %s has no Shape Key Blocks (skip)" % (meshobj.name) )

        return # no key blocks

    log.debug("Apply sliders to custom mesh: getMesh from %s" % (meshobj.name) )
    MESH = getMESH(mname, meshobj, armobj, use_cache=True)
    mesh_weights = MESH['weights']

    if not mesh_weights:
        log.warning("Apply sliders to custom mesh: Custom Mesh %s has no deforming weights defined (skip)" % (meshobj.name) )

        return









    shapekey_diffs = MESH['shapekeys'] # Use cache
    log.debug("Apply sliders to custom mesh: update Custom Mesh %s" % (meshobj.name))

    for index, block in enumerate(key_blocks):
        if index == 0:
            co_ref = util.fast_get_verts(meshobj.data.vertices)
            block.data.foreach_set('co',co_ref)
            co_ref = MESH['co']
        else:

            co = shapekey_diffs.get(block.name)
            if co:
                try:
                    co = list(map(add, co, co_ref))
                    bindBoneScales(co, armobj, meshobj, mesh_weights)
                    block.data.foreach_set('co',co)
                except:
                    log.warning("Apply sliders to custom mesh: kaput!")







#

#

#


#



def weights_from_groups(meshobj, deforming=True):
    if deforming:
        armobj = util.get_armature(meshobj)
        if armobj == None:
            return None
    else:
        armobj = None

    groups = meshobj.vertex_groups
    if not groups or len(groups) == 0:
        return None

    mesh_weights = {}
    verts = meshobj.data.vertices
    unweighted = 0
    for vert in verts:

        weights={}
        weightsum = 0

        for group in vert.groups:
            vgroup = meshobj.vertex_groups[group.group]
            gname = vgroup.name
            if deforming:
                if gname not in armobj.data.bones:
                    continue # is not a bone weight group
                if not armobj.data.bones[gname].use_deform:
                    continue # bone is not deforming
            weights[gname] = group.weight
            weightsum += group.weight

        if weightsum == 0:
            unweighted += 1
            continue

        for gname, gweight in weights.items():
            gweights = mesh_weights.get(gname)
            if not gweights:
                gweights = {}
                mesh_weights[gname] = gweights
            gweights[vert.index] = gweight/weightsum

    if unweighted > 0:
        log.warning("Ignored %d unweighted vertices in Mesh %s" % (unweighted, meshobj.name) )

    return mesh_weights




def has_slider_meta(obj):
    return REFERENCE_SHAPE in obj and NEUTRAL_SHAPE in obj and MORPH_SHAPE in obj


def createSliderShapeKeys(obj):
    co = util.fast_get_verts(obj.data.vertices)
    store_shape_data(obj, REFERENCE_SHAPE, co)
    store_shape_data(obj, NEUTRAL_SHAPE, co)
    store_shape_data(obj, MORPH_SHAPE, co)

def destroy_shape_info(context, armobj):
    with util.slider_context() as is_locked:
        objs = util.get_animated_meshes(context, armobj, with_avastar=False, only_selected=False)
        for ob in objs:
            detachShapeSlider(ob, reset=False)
            ob.ObjectProp.slider_selector = 'NONE'
        armobj.ObjectProp.slider_selector = 'NONE'

def detachShapeSlider(obj, reset=True):
    props = [DIRTY_MESH, CHECKSUM, MORPH_SHAPE, NEUTRAL_SHAPE, MESH_STATS, 'original']
    for prop in props:
        if prop in obj:
            del obj[prop]

    try:
        if REFERENCE_SHAPE in obj:
            if reset:
                if not apply_shape_data(obj, REFERENCE_SHAPE):
                    log.warning("Could not load original shape into Mesh")
                    log.warning("probable cause: The Mesh was edited while sliders where enabled.")
                    log.warning("Keep Shape as it is and discard stored original")
            del obj[REFERENCE_SHAPE]
    except:
        log.warning("Error while trying to apply shape to %s" % obj.name)

    return

def old_detachShapeSlider(obj, reset=True):

    detachShapeSlider(obj, reset=reset)

    if obj.data.shape_keys is not None:
        try:
            active = util.get_active_object(bpy.context)
            util.set_active_object(bpy.context, obj)
            original_mode = util.ensure_mode_is("OBJECT")

            if MORPH_SHAPE in obj.data.shape_keys.key_blocks:
                obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(MORPH_SHAPE)
                bpy.ops.object.shape_key_remove()

            if NEUTRAL_SHAPE in obj.data.shape_keys.key_blocks:
                obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(NEUTRAL_SHAPE)
                bpy.ops.object.shape_key_remove()

            if len(obj.data.shape_keys.key_blocks) == 1:
                util.ensure_mode_is("EDIT")
                util.ensure_mode_is("OBJECT")
                bpy.ops.object.shape_key_remove(all=True)

            util.ensure_mode_is(original_mode)
            util.set_active_object(bpy.context, active)
        except:
            log.warning("Error while trying to remove shape keys from %s" % obj.name)

class ShapeSliderDetach(bpy.types.Operator):
    """Detach Avatar shape from the context object"""
    bl_idname = "avastar.shape_slider_detach"
    bl_label = "Detach shape Slider of active Object"
    bl_options = {'REGISTER', 'UNDO'}

    reset : BoolProperty(name="Reset Shape", default=True, description = "Reset Object to shape when Sliders had been attached" )

    @classmethod
    def poll(self, context):
        ob = context.object
        return ob != None

    def execute(self, context):
        if context.object and context.object.type == 'MESH':
            log.warning("Calling detachShapeSlider for %s" % (context.object))
            detachShapeSlider(context.object, reset=True)
        return {'FINISHED'}
        
def attachShapeSlider(context, arm, obj):

    visitlog.debug("shape.attachShapeSlider arm:%s obj:%s" % (arm.name, obj.name) )
    active = util.get_active_object(context)
    prop   = context.scene.MeshProp
    
    util.tag_addon_revision(obj)

    createSliderShapeKeys(obj)
    ensure_drivers_initialized(arm)

    arm_select = util.object_select_get(arm)
    util.object_select_set(arm, True)




    util.set_active_object(context, active)
    util.object_select_set(arm, arm_select)

def initShapeSlider(context, arm, attached_objects):
    custom_object_map = animated_custom_objects(context, arm, attached_objects)
    log.warning("| Init %d Slider References for %s" % (len(custom_object_map), list(custom_object_map.keys())) )
    apply_rig_config_to_meshes(context, arm, custom_object_map, False, V0)


def refresh_shape(context, arm, obj, graceful=False, only_weights=False):
    original_mode = obj.mode
    active_group_index = obj.vertex_groups.active_index
    shape_filename = arm.name

    if True:#shape_filename in bpy.data.texts:
    
        temp_filename  = "current_shape"
   
        original_mode  = util.ensure_mode_is("OBJECT")
        
        #
        #
        update_custom_bones(obj, arm)
        refreshAvastarShape(context, only_weights=only_weights)
        #
        #
        #
        #

        util.ensure_mode_is(original_mode)
        obj.vertex_groups.active_index = active_group_index
        return shape_filename
    elif graceful:
        return None
    else:
        raise util.Warning(MSG_UPDATE_SHAPE)

def get_joint_copy(joint):
    head = Vector(joint['head'])
    tail = Vector(joint['tail'])
    roll = joint['roll']
    copy = {'head':head, 'tail':tail, 'roll':roll}
    return copy

def get_floor_hover(armobj, use_cache=False):
    pos, tail, dh, dt = rig.get_floor_compensation(armobj, use_cache=use_cache)
    return dh

def adjust_edit_bone(dbone, head_local, tail_local, roll):
    rig.reset_item_cache(dbone, full=True)
    dbone.head = head_local
    dbone.tail = tail_local
    dbone.roll = roll

def refresh_spine_joint_positions(armobj):
    ebones = armobj.data.edit_bones
    mTorso  = ebones.get('mTorso')
    mChest  = ebones.get('mChest')
    mPelvis = ebones.get('mPelvis')
    if not (mTorso and mChest and mPelvis):
        return

    mChestHead = mChest.head.copy()
    mChestTail = mChest.tail.copy()
    mTorsoHead = mTorso.head.copy()
    mTorsoTail = mTorso.tail.copy()
    mPelvisHead = mPelvis.head.copy()
    mPelvisTail = mPelvis.tail.copy()

    length = (mTorsoHead-mChestHead).magnitude
    if length < MIN_JOINT_OFFSET_STRICT:
        log.warning("Can not adjust spine bones. Reason: mChest and mTorso are located too close to each other")
        return

    if not armobj.RigProp.spine_unfold_upper:

        mSpine3 = ebones.get('mSpine3')
        mSpine4 = ebones.get('mSpine4')
        Spine3  = ebones.get('Spine3')
        Spine4  = ebones.get('Spine4')

        if mSpine3:
            mSpine3.head = mTorsoTail.copy()
            mSpine3.tail = mTorsoHead.copy()
            mSpine3.roll = util.sanitize_f(mSpine3.roll)
        if Spine3:
            Spine3.head  = mTorsoTail.copy()
            Spine3.tail  = mTorsoHead.copy()
            Spine3.roll = util.sanitize_f(Spine3.roll)
        if mSpine4:
            mSpine4.head = mTorsoHead.copy()
            mSpine4.tail = mTorsoTail.copy()
            mSpine4.roll = util.sanitize_f(mSpine4.roll)
        if Spine4:
            Spine4.head = mTorsoHead.copy()
            Spine4.tail = mTorsoTail.copy()
            Spine4.roll = util.sanitize_f(Spine4.roll)

    if not armobj.RigProp.spine_unfold_lower:

        mSpine1 = ebones.get('mSpine1')
        mSpine2 = ebones.get('mSpine2')
        Spine1  = ebones.get('Spine1')
        Spine2  = ebones.get('Spine2')

        if mSpine1:
            mSpine1.head = mPelvisTail.copy()
            mSpine1.tail = mPelvisHead.copy()
            mSpine1.roll = util.sanitize_f(mSpine1.roll)
        if Spine1:
            Spine1.head  = mPelvisTail.copy()
            Spine1.tail  = mPelvisHead.copy()
            Spine1.roll = util.sanitize_f(Spine1.roll)
        if mSpine2:
            mSpine2.head = mPelvisHead.copy()
            mSpine2.tail = mPelvisTail.copy()
            mSpine2.roll = util.sanitize_f(mSpine2.roll)
        if Spine2:    
            Spine2.head = mPelvisHead.copy()
            Spine2.tail = mPelvisTail.copy()
            Spine2.roll = util.sanitize_f(Spine2.roll)


def refresh_joint_positions(armobj, dbone):

    def can_be_adjusted(armobj, bone_name):
        if bone_name=='COG':
            return False
        if not bone_name.startswith('mSpine'):
            can_adjust = True
        else:
            can_adjust = (armobj.RigProp.spine_unfold_upper and bone_name in ('mSpine3', 'mSpine4')) \
                     or (armobj.RigProp.spine_unfold_lower and bone_name in ('mSpine1', 'mSpine2'))
        return can_adjust

    if not dbone:
        return

    bone_name = dbone.name
    if not can_be_adjusted(armobj, bone_name):
        return

    head_local, tail_local, roll = get_edit_bone_location(armobj, dbone)
    adjust_edit_bone(dbone, head_local, tail_local, roll)

    if not dbone.use_connect:
        return

    parent = dbone.parent
    if not parent:
        return


    dvec = head_local - parent.head
    if dvec.magnitude > MIN_BONE_LENGTH:
        rig.reset_item_cache(parent, full=True)
        parent.tail = head_local.copy()


def get_edit_bone_location(armobj, dbone):
    head_local, tail_local = rig.get_custom_bindposition(armobj, dbone, use_cache=True)
    roll = util.sanitize_f(dbone.roll)


    if tail_local.magnitude < MIN_BONE_LENGTH:
        tail_local = util.sanitize_v(head_local + Vector((0,0.02,0))) # Should never happen
    else:
        tail_local = util.sanitize_v(head_local + tail_local)
    return head_local, tail_local, roll


def add_offset_to_hierarchy(ebones, dbone, parent_bone, hover):
    if dbone == None or hover.magnitude==0:
        return
    
    if dbone.name != 'Origin':
        dbone.head = parent_bone.tail.copy() if (parent_bone and dbone.use_connect) else (dbone.head-hover)
        dbone.tail -= hover

    for child in dbone.children:
        add_offset_to_hierarchy(ebones, child, dbone, hover)
    

def adjust_joint_positions(context, armobj, fix_hover, use_cache=False):

    bone_hierarchy = rig.bones_in_hierarchical_order(armobj)
    skeleton_bone_names = util.getSkeletonBoneNames(bone_hierarchy)
    control_bone_names = util.getControlledBoneNames(bone_hierarchy)
    eye_states = util.disable_eye_targets(armobj)

    for name in skeleton_bone_names:
        dbone = armobj.data.edit_bones.get(name)
        refresh_joint_positions(armobj, dbone)


    refresh_spine_joint_positions(armobj)



    if fix_hover:
        hover = get_floor_hover(armobj, use_cache=use_cache)
        origin = armobj.data.edit_bones.get('Origin')
        add_offset_to_hierarchy(armobj.data.edit_bones, origin, None, hover)
    else:
        hover = V0

    for name in control_bone_names:
        mbone = armobj.data.edit_bones.get(name)
        cbone = armobj.data.edit_bones.get(name[1:])
        if mbone and cbone:
            adjust_edit_bone(cbone, mbone.head.copy(), mbone.tail.copy(), mbone.roll)

    util.enable_eye_targets(armobj, eye_states)
    return hover

#

#
def animated_custom_objects(context, armobj, attached_objects=None):
    selection = attached_objects if attached_objects else context.visible_objects
    custom_objects = [ \
            ob for ob in selection \
            if ob.type=='MESH' and \
            not 'avastar-mesh' in ob and \
            any([mod for mod in ob.modifiers if mod.type=='ARMATURE' and mod.object==armobj])]

    custom_object_map = {o.name:o for o in custom_objects}
    return custom_object_map

all_driven_bones = None
all_bone_drivers = None

def get_bone_drivers(arm_obj, dbone):

    def get_driven_bones_map(arm_obj):
        global all_driven_bones
        if all_driven_bones != None:
            return all_driven_bones

        all_bone_drivers = get_bone_driver_map(arm_obj)
        all_driven_bones = {}
        for key,D in all_bone_drivers.items():
            bones=D[0].get('bones')
            for bname in [b['name'] for b in bones]:
                driver_set = all_driven_bones.get(bname)
                if not driver_set:
                    driver_set = []
                    all_driven_bones[bname] = driver_set
                driver_set.append(D)
        return all_driven_bones

    def get_bone_driver_map(arm_obj):
        global all_bone_drivers
        if all_bone_drivers != None:
            return all_bone_drivers

        ensure_drivers_initialized(arm_obj)
        DRIVERS = arm_obj.ShapeDrivers.DRIVERS
        all_bone_drivers = {key:D for key,D in DRIVERS.items() if D[0].get('bones')}
        return all_bone_drivers

    drivers_for_bones = get_driven_bones_map(arm_obj)

    bone_drivers = drivers_for_bones.get(dbone.name)
    if bone_drivers:
        bone_drivers = [D[0] for D in bone_drivers]
    else:
        bone_drivers = []
    if dbone.parent:
        parent_drivers = get_bone_drivers(arm_obj, dbone.parent)
        bone_drivers.extend(parent_drivers)
    return bone_drivers

def driven_meshes(context, arm_obj):
    animated_meshes = util.get_animated_meshes(context, arm_obj, only_visible=False)
    system_meshes = {}
    custom_meshes = {}
    for obj in animated_meshes:
        target = system_meshes if 'avastar-mesh' in obj else custom_meshes
        target[obj.name] = obj

    return system_meshes, custom_meshes

def get_bone_dict(bones, bonechanges):
    result = set()
    bone_lists = [ [l['name'] for l in D[0]['bones']] for D in bonechanges]
    for bone_list in bone_lists:
        for bname in bone_list:
            bone = bones.get(bname)
            if bone:
                if bone.name not in result:
                    util.add_bone_and_children(bone, result)
    return result

def slider_driver(self, context, target):
    


    start = time.time()
    scene = context.scene
    active = util.get_active_object(context)
    arm_obj = util.get_armature(active)
    if arm_obj is None:
        return

    system_obj_map, custom_obj_map = driven_meshes(context, arm_obj)
    
    log.warning("driver: slider:%s arm:%s %d system meshes %d custom meshes" % (target, arm_obj.name, len(system_obj_map), len(custom_obj_map)))
    ensure_drivers_initialized(arm_obj)
    visibility = ensure_armature_visible(context, arm_obj)



    propagate_driver_values(arm_obj, target)
    mesh_changes, bone_changes = expandDrivers(arm_obj, [target])
    log.warning("driver: found %d mesh changes, %d bone changes" % (len(mesh_changes), len(bone_changes) ))
        

    restore_visibility(context, arm_obj, visibility)
    tic = util.logtime(start, "slider_driver total runtime", 4, 67)
    return

def propagate_driver_values(arm_obj, target):
    Ds = arm_obj.ShapeDrivers.DRIVERS[target]
    for D in Ds:
        pid = D['pid']
        if pid != 'male_80':
            v100 = getattr(arm_obj.ShapeDrivers, pid)
            arm_obj.ShapeValues[pid] = float(v100)

def restore_visibility(context, arm_obj, visibility):
    arm_is_visible = visibility['visible']
    if not arm_is_visible:
        arm_layer_is_hidden = visibility['hidden']
        arm_layers = visibility['layers'] 
        if arm_layer_is_hidden:
            util.object_hide_set(armobj, arm_layer_is_hidden)




def ensure_armature_visible(context, arm_obj):
    arm_is_visible = util.object_visible_get(arm_obj, context=context)
    arm_layers = None
    arm_layer_is_hidden = None
    
    if not arm_is_visible:
        arm_layer_is_hidden = util.object_hide_get(arm_obj)
        util.object_hide_set(arm_obj, False)




    visibility = {
        "visible" : arm_is_visible,
        "hidden" : arm_layer_is_hidden,
        "layers": arm_layers
    }
    return visibility


class times:

    timings = None
    tic = None
    toc = None
    begin = None


    def __init__(self):
        self.timings = []
        self.tic = time.time()
        self.begin = self.tic


    def add(self, comment):
        self.toc = time.time()
        total = int(1000*(self.toc - self.begin))
        delta = int(1000*(self.toc - self.tic))
        self.timings.append([delta, total, "%d:%s" % (len(self.timings), comment)])
        self.tic = self.toc


    def get_timings(self):
        return self.timings


def shape_slider_driver(self, context, slider_pid):



    if self.Freeze:
        return

    osuppress_handlers = util.set_disable_handlers(context.scene, True)
    try:
        armobj = util.get_armature_from_context(context)
        omode = util.ensure_mode_is('OBJECT')
        refreshAvastarShape(context, refresh=False, target=slider_pid)
        util.ensure_mode_is(omode)
    finally:
        util.set_disable_handlers(context.scene, osuppress_handlers)
    return


def refreshAvastarShape(context, refresh=True, init=False, target="", only_weights=False):
    
    active_obj_mode = None
    arm_obj_mode = None


    def backup_object_modes(context, active_obj, arm_obj):
        if active_obj == arm_obj:
            active_obj_mode = arm_obj_mode = active_obj.mode
        else:
            active_obj_mode = active_obj.mode
            util.set_active_object(context, arm_obj)
            arm_obj_mode = arm_obj.mode
        return active_obj_mode, arm_obj_mode


    def restore_object_modes(context, active_obj, arm_obj):
        if arm_obj_mode:
            util.ensure_mode_is(arm_obj_mode)
            util.set_active_object(context, active_obj)
            util.ensure_mode_is(active_obj_mode)


    scene = context.scene
    if scene.SceneProp.panel_appearance_enabled == False:
        return

    active_obj = util.get_active_object(context)
    arm_obj = util.get_armature(active_obj)
    if arm_obj is None:
        return

    active_obj_mode, arm_obj_mode = backup_object_modes(context, active_obj, arm_obj)
    custom_object_map = animated_custom_objects(context, arm_obj, None)
    with_bone_check=True

    if custom_object_map:
        prepare_reference_meshes(custom_object_map.values(), arm_obj)

    inner_updateShape(context, target, scene, refresh, init, custom_object_map, with_bone_check, only_weights=only_weights)

    restore_object_modes(context, active_obj, arm_obj)


def oldUpdateShape(self, context, target="", scene=None, refresh=False, init=False, object=None, msg="Slider", with_bone_check=True, force_update=False):
    if scene is None:
        scene = context.scene

    if not (scene.SceneProp.panel_appearance_enabled or force_update):
        return

    active = util.get_active_object(context)
    armobj = util.get_armature(active)
    if armobj is None:
        return
 
    omode = amode = None
    if active != armobj:
        amode = active.mode
        util.set_active_object(context, armobj)
        omode = armobj.mode

    oldstate = util.set_disable_update_slider_selector(True)
    attached_objects = [object] if object else None
    custom_object_map = animated_custom_objects(context, armobj, attached_objects)
    inner_updateShape(context, target, scene, refresh, init, custom_object_map, with_bone_check)
    if omode:
        util.ensure_mode_is(omode)
        util.set_active_object(context, active)
        util.ensure_mode_is(amode)

    util.set_disable_update_slider_selector(oldstate)
    return


all_change_sliders= ["leg_length_692","heel_height_198", "platform_height_503"]
recurse_call = False
def inner_updateShape(context, target, scene, refresh, init, custom_object_map, with_bone_check, only_weights=False):
    '''
    Update avatar shape based on driver values.
    Important:

    This function relies on correct bone data info to calculate the correct
    bone locations. When used during a rig update, we first have to preset
    correct joint location information.

    '''

    active = util.get_active_object(context)
    amode = active.mode
    armobj = util.get_armature(active)
    armobj['is_in_restpose'] = False

    global recurse_call
    ensure_drivers_initialized(armobj)
    log.debug("Check dirty for active:%s armature:%s" % (active.name, armobj.name))
    if DIRTY_RIG in armobj:
        log.warning("Calling Jointpos Store from Update Shape for %s" % (armobj.name) )
        bpy.ops.avastar.armature_jointpos_store(sync=False)

    if armobj.ShapeDrivers.Freeze:


        return

    arm_is_visible, arm_layer_is_hidden = ensure_armature_is_visible(armobj, context)

    try:
        hover = None
        if not target:
            adjust_slider_cache(reset=True)

        util.set_active_object(context, armobj)

        oumode = util.set_operate_in_user_mode(False)


        if not only_weights:
            targets = []
            if refresh:

                for section, pids in SHAPEUI.items():
                    targets.extend(pids)
            elif target != "" and not recurse_call:
                targets = [target]
                armobj.RigProp.restpose_mode = False

                try:

                    Ds = armobj.ShapeDrivers.DRIVERS[target]
                    recurse_call=True 
                    for D in Ds:
                        pid = D['pid']
                        if pid != 'male_80':
                            v100 = getattr(armobj.ShapeDrivers, pid)
                            armobj.ShapeValues[pid] = float(v100)
                except:
                    pass
                finally:
                    recurse_call = False





            meshchanges, bonechanges = expandDrivers(armobj, targets)
            changed_bones = get_bone_dict(armobj.data.bones, bonechanges)

            if not refresh and len(bonechanges)>0:


                targets = []
                for section, pids in SHAPEUI.items():
                    targets.extend(pids)
                meshchanges, bonechanges = expandDrivers(armobj, targets)

            ava_objects = util.getAvastarChildSet(armobj, type='MESH', visible=True)
            log.debug("Updating %d Avastar meshes and %d custom meshes" % (len(ava_objects),len(custom_object_map)) )


            if ava_objects or custom_object_map:
                for D,v,p in meshchanges:
                    if ava_objects:
                        updateSystemMeshKey(armobj, D, v, p, ava_objects)
                    if custom_object_map:
                        updateCustomMeshKey(armobj, D, v, p, custom_object_map)

            if with_bone_check and len(bonechanges)>0:


                rig.reset_scales(armobj)
                calculate_offsets(armobj, bonechanges)
                fix_hover = True


                cactive, cmode = util.change_active_object(context, armobj, new_mode="EDIT", msg="inner_updateShape 1:")
                hover = adjust_joint_positions(context, armobj, fix_hover, use_cache=True)
                adjustSupportRig(context, armobj)
                armobj.update_from_editmode()







                force_all_meshes=(target and target in all_change_sliders)

                if ava_objects:
                    update_system_shapekeys(context, armobj, ava_objects, hover, changed_bones, force_all_meshes)

                util.transform_origin_to_rootbone(context, armobj)
                bone_hierarchy = rig.bones_in_hierarchical_order(armobj)

                for name in bone_hierarchy:
                    dbone = armobj.data.bones.get(name,None)
                    if not dbone:
                        log.warning("Bone %s is not in Rig %s" % (name, armobj.name) )
                        continue

                    if dbone and 'p_offset' in dbone:
                        del dbone['p_offset']

                util.change_active_object(context, cactive, new_mode=cmode, msg="inner_updateShape 2:")







        apply_rig_config_to_meshes(context, armobj, custom_object_map, init, hover)

        setHands(armobj, scene=scene)
        util.set_operate_in_user_mode(oumode)

    finally:
        util.set_active_object(context, active)

    if not arm_is_visible:
        if arm_layer_is_hidden:
            util.object_hide_set(armobj, arm_layer_is_hidden)

    return

def ensure_armature_is_visible(armobj, context):
    arm_is_visible = util.object_visible_get(armobj,context=context)
    if not arm_is_visible:
        arm_layer_is_hidden = util.object_hide_get(armobj)
        util.object_hide_set(armobj, False)





    else:
        arm_layer_is_hidden = None
    return arm_is_visible, arm_layer_is_hidden

def apply_rig_config_to_meshes(context, armobj, custom_object_map, init, hover):
    if hover == None:
        rig.reset_cache(armobj, full=True)
        hover = get_floor_hover(armobj)

    for child in custom_object_map.values():
        if not has_shape_data(child):
            log.info("%s has no slider data, ignore" % (child.name) )
            continue

        arm = util.getArmature(child)
        if arm is None:
            log.warning("%s has no associated Armature, ignore" % (child.name) )
            continue

        log.debug("%s custom bones for %s" % ("Init" if init else "Update", child.name))
        if init:
            init_custom_bones(child, arm, hover=hover)
        else:
            update_custom_bones(child, arm, hover=hover)

        apply_shapekeys_to_custom_meshes(context, arm, child.name, child)
        child.update_tag(refresh={'DATA'})

    return

def get_bones_from_groups(bones, vertex_groups):
    active_bones = []
    for group in vertex_groups:
        if group.name in bones and bones[group.name].use_deform:
            active_bones.append(bones[group.name])
    return active_bones

def sort_bones_by_hierarhy(bones, active_bones):
    processed   = []
    unprocessed = []
    for i, bone in enumerate(active_bones):
        if bone in bones:
            processed.append(bone)
        else:
            unprocessed.append(bone)

    if len(unprocessed) > 0:
        for bone in bones:
            children = bone.children
            if len(children) > 0:
                r = sort_bones_by_hierarhy(bone.children, unprocessed)
                if len(r) > 0:
                    processed.append(r)
    return processed

def prepare_reference_meshes(custom_objects, arm_obj):
    for child in custom_objects:
        if not has_shape_data(child):
            log.info("create slider data for Mesh Object '%s'" % (child.name) )
            init_custom_bones(child, arm_obj)

def has_shape_data(meshobj):
    return meshobj.get(NEUTRAL_SHAPE, None) != None and meshobj.get(MORPH_SHAPE, None) != None

    
def get_shape_data(child, key):
    visitlog.debug("get shape data: child:%s key:%s" % (child.name, key) )
    skey = str(key)
    dta = child.get(skey,None)

    if not dta:

        if REFERENCE_SHAPE in child:
            dta = child[REFERENCE_SHAPE].to_list()

            source = REFERENCE_SHAPE
        else:
            dta = util.fast_get_verts(child.data.vertices)

            source = 'mesh'
            
        visitlog.debug("get shape data: copied %d values child:%s from: %s to: %s" % (len(dta), source, child.name, key))
        child[skey] = dta
        return dta
    else:
        visitlog.debug("get shape data: reading %d values child:%s from key :%s" % (len(dta), child.name, key))

    lvert = 3*len(child.data.vertices)
    ldta  = len(dta)
    dta = dta.to_list() # convert from idproperty to array

    if lvert != ldta:
        if  lvert > ldta:
            lvert = int(lvert/3)
            ldta  = int(ldta/3)
            updatelog.warning("get shape data: %s:%s Adding Shape data on the fly for %d missing verts" % (child.name, skey, (lvert-ldta)) )

            verts = child.data.vertices
            for i in range(ldta, lvert):
                co = verts[i].co.copy()
                dta.extend([co[0], co[1], co[2]])
            child[skey] = dta

        else:
            updatelog.warning("get shape data: %s:%s shape has %d verts, mesh has %d verts (please reset shape)" % (child.name, skey, ldta, lvert) )
    visitlog.debug("get shape data: loaded shape %s:%s with %d verts %d dta" % (child.name, skey, lvert, len(dta)) )
    return dta

def store_shape_data(child, key, co):
    if co:

        child[key] = co.copy()
        return True
    else:

        return False

def apply_shape_data(child, key):
    co = child.get(key)
    try:
        util.fast_set_verts(child.data, co)
        return True
    except:
        log.warning("Could not Set Shape Data for Obj:%s - key %s. (suppose to reset Shape Info" % (child.name, key) )
        return False

def update_shape_from_weightmaps(weightmaps, weighted_verts, armobj, child, init, hover):


    height = armobj.matrix_local.to_scale().z * (hover.z - child.RigProp.bind_hover)
    height = Vector((0,0,height))#@child.matrix_local.inverted()
    hobj = get_custom_hover(child)
    hover = hobj[2]

    co = get_shape_data(child, REFERENCE_SHAPE)
    for i in range(2,len(co),3):
        co[i] += hover

    fco = co.copy()
    precos = get_precos(child, co, use_cache=False) 





    




    for bname, weights in weightmaps.values():
        if weights:
            calculate_shape_delta(armobj, child, bname, weights, co, fco, init, precos, use_cache=True)

    hover = hobj[2] + height[2]
    for i in range(2,len(fco),3):
        fco[i] -= hover

    return fco

def init_shape_transform(armobj, child, hover):
    transforms = get_shape_bindings(armobj, use_cache=True)
    sliders, values = get_slider_bindings(armobj)

    child[SHAPE_BINDING] = { SHAPE_TRANSFORMS:transforms,
                        SHAPE_SLIDERS:sliders,
                        SHAPE_VALUES:values,
                        SHAPE_HOVER:hover
                       }

def get_slider_bindings(armobj):
    if not hasattr(armobj.ShapeDrivers, 'DRIVERS'):
        rigType = armobj.RigProp.RigType
        DRIVERS = data.loadDrivers()
        ensure_drivers_initialized(armobj)
        createShapeDrivers(DRIVERS)

    sliders = armobj.ShapeDrivers.get_attributes(),
    values = armobj.ShapeValues.get_attributes()

    return sliders, values

def get_shape_bindings(armobj, use_cache=True):
    transforms = {}

    for dbone in armobj.data.bones:
        BoneLoc0, BoneLoc, MScaleLocal = get_shape_transform(armobj, dbone, use_cache=use_cache, normalize=True)
        transforms[dbone.name] = [BoneLoc0.copy(), BoneLoc.copy(), MScaleLocal.copy()]

    return transforms

def get_shape_binding(child, bname):
    binding = child.get(SHAPE_BINDING)
    if not binding:
        return None, None, None

    BoneLoc0, BoneLoc, MScaleLocal = binding[SHAPE_TRANSFORMS][bname]
    return Vector(BoneLoc0), Vector(BoneLoc), Matrix(MScaleLocal)

def calculate_shape_transform(armobj, child, bname, init, use_binding=True, use_cache=True):
    bones = util.get_modify_bones(armobj)
    dbone = bones.get(bname, None)
    if not dbone:
        return None, None, None

    BoneLoc0, BoneLoc, MScaleLocal = get_shape_transform(armobj, dbone, use_cache=use_cache)

    if use_binding and not init:
        RestBoneLoc0, RestBoneLoc, RestMScaleLocal = get_shape_binding(child, bname)
        if RestBoneLoc:
            BoneLoc0 = RestBoneLoc
            MScaleFinal = mulmat(RestMScaleLocal.inverted(), MScaleLocal)
        else:
            MScaleFinal = MScaleLocal
    else:
        MScaleFinal = MScaleLocal

    if init:
        BoneLoc, BoneLoc0 = BoneLoc0, BoneLoc
        MScaleFinal= MScaleFinal.inverted()

    return BoneLoc0, BoneLoc, MScaleFinal

def get_shape_transform(armobj, dbone, use_cache=True, normalize=True):
    BoneLoc0, BoneLoc, MScale = get_binding_data(armobj, dbone, use_cache=use_cache, normalize=normalize)








    if armobj.RigProp.rig_use_bind_pose:
        M = rig.bind_rotation_matrix(armobj, dbone).to_4x4()
        MScaleLocal = mulmat(M, MScale, M.inverted())
    else:
        MScaleLocal = MScale.copy()

    return BoneLoc0, BoneLoc, MScaleLocal

shape_store = {}
last_call_target = None
last_call_time = 0

def shape_store_used(target):
    global last_call_target
    global last_call_time
    global shape_store
    return shape_store and last_call_target==target

def check_slider_cache_consistency(target, timeout=5):
    global last_call_target
    global last_call_time
    now = time.time()
    target_changed = target != last_call_target
    timed_out = now - last_call_time > timeout 
    return target_changed or timed_out


def adjust_slider_cache(target=None, reset=False):
    global last_call_target
    global last_call_time
    global shape_store

    last_call_time = 0 if reset else time.time()
    last_call_target = target

    if reset:
        shape_store = {}


def get_global_store(store_name):
    global shape_store
    store = shape_store.get(store_name)
    if store == None:
        store = {}
        shape_store[store_name] = store
    return store


def get_precos(child, co, use_cache=True):
    if use_cache:
        precos_store = get_global_store('precos_store')
        precos = precos_store.get(child.name)

    if use_cache==False or precos==None:
        precos = precalc_vertex_data(child, co)

    if use_cache:
        precos_store[child.name] = precos

    return precos


def reset_armature_weight_groups(context, armobj):
    custom_object_map = animated_custom_objects(context, armobj)
    for obj in custom_object_map.values():
        reset_weight_groups(obj)


def reset_weight_groups(child):
    weightgroups_store = get_global_store('weightgroups_store')
    weight_groups = weightgroups_store.get(child.name)

    if weight_groups:
        del weightgroups_store[child.name]


def get_weight_groups(bones, child):
    weightgroups_store = get_global_store('weightgroups_store')
    weights_and_verts = weightgroups_store.get(child.name)

    if weights_and_verts:
        weightmaps     = weights_and_verts[0]
        weighted_verts = weights_and_verts[1]
    else:
        weightmaps, weighted_verts = collect_weight_groups(bones, child, all_verts=True)
        weightgroups_store[child.name] = [weightmaps, weighted_verts]

    return weightmaps, weighted_verts

def precalc_vertex_data(child, co):
    coflen = len(co)
    MChild  = child.matrix_local
    MChildI = MChild.inverted()
    precos = []

    offset = 0
    for index in range(int(coflen/3)):
        vert_local_co = Vector(co[offset:offset+3])  # in local space
        vert_world_co = MChild @ vert_local_co       # in object space
        precos.append([vert_local_co,vert_world_co])
        offset += 3

    return precos









#



#



#















#


#







def calculate_shape_delta(armobj, child, bname, weights, co, dco, init, precos, use_cache=True):
    





    BoneLoc0, BoneLoc, MScaleLocal = calculate_shape_transform(armobj, child, bname, init=init, use_binding=True, use_cache=use_cache)
    if not BoneLoc0:
        return
    
    bones = util.get_modify_bones(armobj)
    dbone = bones.get(bname, None)

    coflen = len(co)
    MChild  = child.matrix_local
    MChildI = MChild.inverted()
    has_bone_rotation = util.is_rotation_matrix(MScaleLocal)
    has_bone_scale = not util.is_unity_matrix(MScaleLocal, has_bone_rotation)
    has_object_rotation = util.is_rotation_matrix(MChild)
    has_object_scale = not util.is_unity_matrix(MChild, has_object_rotation)

    for index, weight in weights:

        dco_index = get_dco_index(index, coflen, child)
        if dco_index == None:
            continue

        vert_local_co, vert_world_co = get_preco_verts(precos, index)
        if vert_local_co == None or vert_world_co == None:
            continue

        delta_world = vert_world_co - BoneLoc0
        if has_bone_scale:
            delta_world = MScaleLocal @ delta_world

        shape_local_co = delta_world + BoneLoc
        if has_object_scale:
            shape_local_co = MChildI @ shape_local_co

        DL = weight * (shape_local_co - vert_local_co)
        update_shape_delta(dco_index, dco, DL)

    return


def get_custom_hover(child):
    binding = child.get(SHAPE_BINDING)
    if binding == None:
        return V0
    
    hover = binding.get('hover')
    if hover == None:
        return V0

    return Vector(hover)


def get_dco_index(index, coflen, child):
    dco_index = 3*index
    if dco_index+3 > coflen:
        updatelog.error("Update custom bones: reference data too small: %s has %d entries, but needs %d to solve vector index %d" 
                        % (child.name, coflen, dco_index+3, index) )
        return None
    return dco_index


def get_preco_verts(precos, index):
    maxi = len(precos)
    if index >= maxi:
        return None,None
    if index < 0:
        return None, None

    return precos[index]


def get_world_delta(vert_world_co, BoneLoc0, MScaleLocal, has_bone_scale):
    d = vert_world_co-BoneLoc0
    if has_bone_scale:
        d = MScaleLocal @ d
    return d

def get_shape_local(d, BoneLoc, MChildI, has_object_scale):
    shape_local = d + BoneLoc
    if has_object_scale:
        shape_local = MChildI @ shape_local
    return shape_local


def update_shape_delta(offset, dco, DL):
    dco[offset]    += DL[0]
    dco[offset+1]  += DL[1]
    dco[offset+2]  += DL[2]


def get_weighted_co(weight, shape_local_co, vert_local_co):
    return weight * (shape_local_co - vert_local_co)


def create_morph_shape(child, armobj, to_shape, all_verts=True, hover=None):

    init = to_shape==NEUTRAL_SHAPE
    bones = util.get_modify_bones(armobj)








    weightmaps, weighted_verts = get_weight_groups(bones, child)
    if weightmaps:
        if hover == None:
            hover = get_floor_hover(armobj)
        fco = update_shape_from_weightmaps(weightmaps, weighted_verts, armobj, child, init, hover)


    else:
        fco = None

    return fco


def get_weightmaps(bones, child):
    weightmaps = {}

    for group in child.vertex_groups:
        bone = bones.get(group.name)
        if bone and bone.use_deform:
            weightmaps[group.index] = (group.name, [])

    return weightmaps


def remove_unused_weightmaps(weightmaps):
    for key, values in weightmaps.items():
        if len(values) == 0:
            del weightmaps[key]


def add_weighted_vert(weighted_verts, v, g, nw):
    weightmap = weighted_verts.get(v)
    if weightmap == None:
        weightmap = {}
        weighted_verts[v]=weightmap
    weightmap[g]=nw



def collect_weight_groups(bones, child, all_verts): 
    weightmaps = get_weightmaps(bones, child)
    weighted_verts = {}
    unweightedvertices = False


    for v in child.data.vertices:
        if all_verts or v.select:
            totw = 0
            vgroups = [] # will contain only valid deforming bone groups 
            for g in v.groups:
                if g.group in weightmaps:
                    vgroups.append((g.group,g.weight))
                    totw += g.weight



            if totw == 0:

                unweightedvertices = True
                continue


            for g,w in vgroups:
                nw = w/totw


                weightmaps[g][1].append((v.index, nw))
                add_weighted_vert(weighted_verts, v, g, nw)

    remove_unused_weightmaps(weightmaps)

    if unweightedvertices:
        updatelog.warning("Bind Resolver: Found unweighted vertices in %s" % child.name)
            
    return weightmaps, weighted_verts


def update_custom_bones(child, armobj, all_verts=True, hover=None):

    to_shape   = MORPH_SHAPE
    co = create_morph_shape(child, armobj, to_shape, all_verts, hover)
    if co:
        store_shape_data(child, to_shape, co)
        apply_shape_data(child, to_shape)


    return

def init_custom_bones(child, armobj, all_verts=True, hover=None):

    if hover == None:
        hover = get_floor_hover(armobj, use_cache=False)

    createSliderShapeKeys(child)
    init_shape_transform(armobj, child, hover)
    child.RigProp.bind_hover=hover.z

    to_shape   = NEUTRAL_SHAPE
    co = create_morph_shape(child, armobj, to_shape, all_verts, hover)
    if co:
        store_shape_data(child, to_shape, co)
    else:
        updatelog.warning("Init custom bones: Mesh object %s has no mesh shape data (ignore)" % (child.name) )
        return


def expandDrivers(armobj, targets):
    
    meshchanges = []
    bonechanges = []
    

    try:
        use_male_shape = armobj.ShapeDrivers.male_80
    except:
        use_male_shape = False

    ensure_drivers_initialized(armobj)
    for target in targets: 


        try:
            Ds = armobj.ShapeDrivers.DRIVERS[target]
        except:
            Ds = []

        for D in Ds:
        
            pid = D['pid']
            
            
            v100 = getShapeValue(armobj,pid)
            if pid == 'male_80':
                v = v100
            else:
                v = rescale(v100, 0, 100, D['value_min'], D['value_max'])
            
            
            for_gender = D['sex']
            if (for_gender == 'male' and not use_male_shape) or (for_gender == 'female' and use_male_shape):
                v = 0


            
            if D['type'] == 'mesh':

                meshchanges.append((D, v, v100/100))
                if len(D['bones'])>0:

                    bonechanges.append((D, v, v100/100))
            elif D['type'] == 'bones':

                bonechanges.append((D, v, v100/100))
            elif D['type'] == 'driven':

                expandDrivenKeys(armobj, D, v, meshchanges, bonechanges)
            else:
                logging.error(D)
                raise Exception("Unknown shape driver %s"%pid)

    return meshchanges, bonechanges



def restore_spine_fold_state(armobj):
    foldstate = armobj.get('spine_unfold', 'none')
    if foldstate == 'none':
        bpy.ops.avastar.armature_spine_fold()
    if foldstate == 'all':
        bpy.ops.avastar.armature_spine_unfold()
    if foldstate == 'upper':
        bpy.ops.avastar.armature_spine_unfold_upper()
    if foldstate == 'lower':
        bpy.ops.avastar.armature_spine_unfold_lower()
        

def adjustSupportRig(context, armobj=None):
    if not armobj:
        armobj = context.active_object




    rig.adjustAvatarCenter(armobj)

    rig.adjustHipLink(armobj, 'Left')
    rig.adjustHipLink(armobj, 'Right')

    rig.adjustCollarLink(armobj, 'Left')
    rig.adjustCollarLink(armobj, 'Right')

    rig.adjustThumbController(armobj, 'Left')
    rig.adjustThumbController(armobj, 'Right')
    rig.adjustFingerLink(armobj, 'Left')
    rig.adjustFingerLink(armobj, 'Right')

    rig.adjustIKToRig(armobj)

    resetEyes(armobj)


    foot_pivot_update(armobj, context, 'Left', refresh=False)
    foot_pivot_update(armobj, context, 'Right', refresh=False)


def updateCustomMeshKey(arm, D, v, p, meshobjs):
    '''
    Update from driver that controls a mesh morph
    '''
    if not meshobjs:
        return
    pid = D.get('pid')
    if not pid:
        return
    try:
        for key, meshobj in meshobjs.items():
            skeys = meshobj.data.shape_keys
            if skeys and pid in skeys.key_blocks:
                sk = skeys.key_blocks[pid]
                if abs(v-sk.value) > 0.000001:
                    log.debug("Update pid %s:%s" % (key,pid) )
                    sk.value = sk.slider_max*p + sk.slider_min*(1-p)
    except KeyError as e:
        log.error("KeyError: %s" % e)
        pass

def updateSystemMeshKey(obj, D, v, p, meshobjs):
    '''
    Update from driver that controls a mesh morph
    '''
   
    try: 
        key = D.get('mesh')
        pid = D.get('pid')
        if not key or not pid:
            return
        meshobj = meshobjs.get(key)
        if not meshobj:
            return
        shape_keys = meshobj.data.shape_keys
        if not shape_keys:
            return
        key_block = shape_keys.key_blocks.get(pid)
        if not key_block:
            return
        old = key_block.value
        if abs(v-old) > 0.000001:
            key_block.value = v
    except KeyError as e:            
        pass

def get_shapekey_blocks(obj):
    shape_keys = obj.data.shape_keys
    if not shape_keys:
        return None
    return shape_keys.key_blocks

def calculate_offsets(arm_obj, bonechanges):
    if bonechanges:
        from . import shape
        bones = util.get_modify_bones(arm_obj)
        for D,v,p in bonechanges:
            if abs(v) > VERY_CLOSE and len(D['bones']) > 0:

                adjust_slider_meta_data(arm_obj, bones, D, v)




def adjust_slider_meta_data(armobj, bones, D, v):
    '''
    Update from driver that controls bone scale and offset
    '''

    for B in D['bones']:
        bname = B['name']
        bone = bones.get(bname, None)


        if not bone:
            continue

        if util.bone_can_scale(armobj, bone):
            scale  = Vector(bone['scale'])  + Vector(B['scale'])*v
        else:
            scale = Vector((0,0,0))

        offset = Vector(bone['offset']) + Vector(B['offset'])*v

        bone['scale']  = scale
        bone['offset'] = offset


        if bone.name[0] == 'm':
            bone = bones.get(bname[1:])
            if bone:
                bone['scale']  = scale
                bone['offset'] = offset


def expandDrivenKeys(armobj, D, v, meshchanges, bonechanges):
    '''
    Expand from driver that controls other drivers
    '''










    #

    use_male_shape = armobj.ShapeDrivers.male_80
    pid = D['pid']

    for DR in D['driven']:
        drpid = DR['pid'] 

        if drpid in [
                    'eyeball_size_679',
                    'eyeball_size_680',
                    'eyeball_size_681',
                    'eyeball_size_687',
                    'eyeball_size_688',
                    'eyeball_size_691',
                    'eyeball_size_694',
                    'eyeball_size_695',
                    ]:

            continue

        if drpid == 'muscular_torso_106' and \
            ((use_male_shape and pid == 'torso_muscles_649') or \
             (not use_male_shape and pid == 'torso_muscles_678')):



            continue




        if v < DR['min1'] or v > DR['min2']:
            vg = 0.0
            
        elif v >= DR['max1'] and v <= DR['max2']:
            vg = 1.0

        elif v < DR['max1']:

            try:
                vg = (v - DR['min1'])/(DR['max1']-DR['min1'])
            except ZeroDivisionError:
                vg = 1.0

        else:

            try:
                vg = 1.0 - (v - DR['max2'])/(DR['min2']-DR['max2'])
            except ZeroDivisionError:
                vg = 1.0

        try:
            D2s = armobj.ShapeDrivers.DRIVERS[drpid]
        except KeyError:
            if drpid not in ["pants_length_shadow_915","pants_length_cloth_615","pants_length_cloth_1018","pants_length_cloth_1036","lower_clothes_shading_913","upper_clothes_shading_899"]:

                logging.warn("Missing driver: %s", drpid)
            continue

        counter=0
        for D2 in D2s:
            counter +=1

            


            v2 = rescale(vg, 0.0, 1.0, D2['value_min'], D2['value_max'] )

            is_for_gender = D2['sex']
            
            if (is_for_gender == 'male' and not use_male_shape) or (is_for_gender == 'female' and use_male_shape):
                v2 = 0
                

                    
            if D2['type'] == 'mesh':
                meshchanges.append((D2, v2, vg))
                if len(D2['bones'])>0:
                    bonechanges.append((D2, v2, vg))
            elif D2['type'] == 'bones':
                bonechanges.append((D2, v2, vg))
            else:
                logging.error(D2)
                raise Exception("Unknown shape driver %s"%D2['pid'])


def setHands(obj, scene):
    arm = util.get_armature(obj)
    props = arm.RigProp

    if "avastar" in obj:

        meshes = util.findAvastarMeshes(obj)
        if 'upperBodyMesh' in meshes:
            upperbodyMesh = meshes['upperBodyMesh']
            if upperbodyMesh.data.shape_keys:


                for ii in range(1,14):
                    mesh = HANDS[ii]['mesh']

                    if ii == int(props.Hand_Posture):
                        value = 1
                    else:
                        value = 0

                    shape_key = upperbodyMesh.data.shape_keys.key_blocks.get(mesh, None)
                    if shape_key:
                        shape_key.value = value

classes = (
    ShapeCopy,
    ShapeDebug,
    ShapePaste,
    PrintSliderRelationship,
    ShapeSliderDetach,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered shape:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered shape:%s" % cls)
