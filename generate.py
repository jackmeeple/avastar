### Copyright 2015 Matrice Laville
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
import bpy, bgl
from bpy.props import *
from struct import pack, unpack, calcsize
from mathutils import Matrix, Vector, Euler

import re, os, logging, gettext
from math import *
from .const import *
from . import const, create, data, shape, util

LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')

import  xml.etree.ElementTree as et
import time, math
from xml.dom import minidom
from mathutils import Vector
from bpy_extras.io_utils import ExportHelper

log = logging.getLogger("avastar.generate")
registerlog = logging.getLogger("avastar.register")

def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

def get_valid_bones(arm, allbones, selection):
    result = []
    for b in selection:
        if b.name in ['Origin','COG','Tinker',
                      'HipLinkRight', 'HipLinkLeft',
                      'CollarLinkLeft', 'CollarLinkRight',
                      'EyeTarget',
                      'FaceEyeAltTarget'
                      ]:
            continue
        if b.name[0] == 'a': continue # remove attachment points
        if b.name[0] == 'i': continue # remove aik bones
        if b.name[0] == 'm':
            result.append(b)
            continue
        if "m"+b.name in allbones: continue # remove control bones
        result.append(b)
    return result

def check_data_part(part, d,  d0,   name, format, label):

    if not isclose(d[part], d0[part], abs_tol=0.0001):
        print("%s.%s[%d] is:[%f] should:[%f], diff:%d mue" %
              (name, label, part, d[part], d0[part], (d[part]-d0[part])*1000000) )


def check_data(d,  d0,   name, format, label):

    check_data_part(0, d,  d0, name, format, label)
    check_data_part(1, d,  d0, name, format, label)
    check_data_part(2, d,  d0, name, format, label)

TODEG = 180/math.pi
def radian2deg(v):
    return [TODEG*v[0], TODEG*v[1], TODEG*v[2]]

REFERENCE_NAMES = {

    "mSpine1"          : "mTorso",
    "mSpine2"          : "mTorso",
    "mSpine3"          : "mChest",
    "mSpine4"          : "mChest"
}
    
def format_as_vector(format, v):
    result = []
    for i in range(0,3):
        result.append( 0 if isclose(v[i], 0, rel_tol=1e-09, abs_tol=0.000001) else v[i] )
    return format % (result[0], result[1], result[2])
        
def get_reference_bone_for(dbone_name, definitions):
    reference_name = REFERENCE_NAMES.get(dbone_name, dbone_name)
    return definitions[reference_name] if reference_name in definitions else None

def prec(value, precision):
    pp = 10**precision
    val = value * pp
    if abs(val) < 1: val = 0
    return val/pp

def vprec(v,precision):
    result = [prec(el,precision) for el in v]
    return result
    

def get_bone_data(arm, dbone, definitions, extended_def, sl_rotated):
    dpos  = dbone.head_local
    if dbone.parent:
        dpos = dpos - dbone.parent.head_local

    dbone_name     = dbone.name
    reference_bone = get_reference_bone_for(dbone_name, definitions)
    original_bone  = definitions[dbone_name] if dbone_name in definitions else None
    extras_bone    = extended_def[dbone_name] if dbone_name in definitions else None

    end0=dbone.tail_local - dbone.head_local
    if extras_bone:




        end = getattr(extras_bone, 'end0', None)

        if end:
            end0 = end # From definition file
        else:
            print("ERROR: the System Bone ", extras_bone.blname, "has no end0 defined")

    end0 = vprec(end0,3)

    if reference_bone:


        is_base = original_bone == reference_bone
        control_bone_name = dbone_name[1:]
        support = "base" if is_base else "extended"
        pos0    = getattr(reference_bone,'pos0',   [0,0,0])
        pivot0  = getattr(reference_bone,'pivot0', pos0)
        rot0    = getattr(reference_bone,'rot0',   [0,0,0])
        scale0  = getattr(reference_bone,'scale0', [1,1,1])
        aliases = const.ANIMBONE_MAP[control_bone_name] if control_bone_name in const.ANIMBONE_MAP else None

        if is_base and dbone_name[0]=='m':
            alias = "avatar_"+dbone_name
            aliases = alias if aliases == None else aliases + ' ' + alias

    else:

        aliases = None
        support = "extended"
        #


        #
        pos0   = dpos
        pivot0 = dpos
        rot0   = [0,0,0]
        scale0 = [1,1,1]

    connected = (dbone_name[0]=='m' and (dbone.use_connect or (dbone.parent and dbone.parent.tail_local == dbone.head_local)))

    if original_bone or not sl_rotated:




        pos0   = [-pos0[1],     pos0[0],   pos0[2]]
        pivot0 = [-pivot0[1], pivot0[0], pivot0[2]]
        rot0   = [-rot0[1],     rot0[0],   rot0[2]]
        scale0 = [scale0[1],  scale0[0], scale0[2]]

        if not sl_rotated:
            end0  = [-end0[1],   end0[0],  end0[2]] if end0 else None
            
        if dbone_name in ["mSpine2", "mSpine4"]:
            pos0   = [-pos0[0],   -pos0[1],   -pos0[2]]
            pivot0 = [-pivot0[0], -pivot0[1], -pivot0[2]]

    rot0   = radian2deg(rot0)
    end     = format_as_vector( "%1.3f %1.3f %1.3f", end0)

    if original_bone:
        attrib = original_bone.attrib
        rot   = original_bone.attrib['rot']
        pos   = original_bone.attrib['pos']
        pivot = original_bone.attrib.get('pivot',pos)
        scale = original_bone.attrib['scale']

    else:
        if dbone_name.startswith('mSpine') or dbone_name.startswith('mFaceEyeAlt') or dbone_name.startswith("mFaceRoot"):
            pivot   = format_as_vector( "%1.6f %1.6f %1.6f", pivot0)
            pos     = format_as_vector( "%1.3f %1.3f %1.3f", pos0)
            rot     = format_as_vector( "%1.6f %1.6f %1.6f", rot0)
        else:
            pivot   = format_as_vector( "%1.3f %1.3f %1.3f", pivot0)
            rot     = format_as_vector( "%1.3f %1.3f %1.3f", rot0)
            pos     = format_as_vector( "%1.3f %1.3f %1.3f", pos0)

        scale   = format_as_vector( "%1.2f %1.2f %1.2f", scale0)


    group   = arm.pose.bones[dbone_name].bone_group
    if group:
        group_name = group.name
        if group_name[0]=='m': group_name = group_name[1:]
    else:
        group_name = None
    
    return pos, pivot, scale, rot, end, connected, aliases, support, group_name

def mBoneNode(arm, bone, definitions, extended_def, sl_rotated):
    pos, pivot, scale, rot, end, connected, aliases, support, group_name = get_bone_data(arm, bone, definitions, extended_def, sl_rotated)
    attrib={'name':bone.name,
       'pos':str(pos),
       'rot':str(rot),
       'scale':str(scale),
       'pivot':str(pivot),
       'end':str(end),
       'support': support
       }
    if group_name:
        attrib['group'] = group_name
    attrib['connected'] = "true" if connected else "false"
    if aliases:
        attrib['aliases'] = aliases

    subnode = et.Element('bone', attrib=attrib)
    return subnode


def cBoneNode(arm, bone, definitions, extended_def, sl_rotated):
    pos, pivot, scale, rot, end, connected, aliases, support, group_name = get_bone_data(arm, bone, definitions, extended_def, sl_rotated)
    attrib={'name':bone.name,
       'pos':str(pos),
       'rot':str(rot),
       'scale':str(scale),
       'end':str(end),
       'support':support
       }

    if group_name:
        attrib['group'] = group_name

    subnode = et.Element('collision_volume',
       attrib=attrib
       )
    return subnode

def create_bone_hierarchy(node, definitions, extended_def, arm, allbones, siblings, sl_rotated, depth=0):

    if len(siblings) == 1 and siblings[0].name == 'Origin':

        bone = siblings[0]
        create_bone_hierarchy(node, definitions, extended_def, arm, allbones, bone.children, sl_rotated, depth)
        return


    for bone in get_valid_bones(arm, allbones, siblings):
        if bone.name[0]!='m':
            subnode = cBoneNode(arm, bone, definitions, extended_def, sl_rotated)
            node.append(subnode)



    for bone in get_valid_bones(arm, allbones, siblings):
        if bone.name[0]=='m':
            subnode = mBoneNode(arm, bone, definitions, extended_def, sl_rotated)
            node.append(subnode)
            create_bone_hierarchy(subnode, definitions, extended_def, arm, allbones, bone.children, sl_rotated, depth+4)

def prettyXML(elem):
    raw = et.tostring(elem, encoding="US-ASCII")
    parsed = minidom.parseString(raw)
    return parsed.toprettyxml(indent="   ")


def is_SL_orientation(dbones):
    orientation = dbones['mHipLeft'].head_local - dbones['mHipRight'].head_local
    orientation = orientation.normalized()
    rotated = orientation.x < 0.5
    return rotated

class ExportAvatarSkeletonOp(bpy.types.Operator, ExportHelper):
    bl_idname = "avastar.export_sl_avatar_skeleton"
    bl_label  = "SL Skeleton (xml)"
    bl_description = "Create a valid avatar_skeleton.xml from existing avatar (reuse original definitions where appropriate)"


    filename_ext = ".xml"

    filter_glob : StringProperty(
            default="*.xml",
            options={'HIDDEN'},
            )

    @classmethod
    def poll(cls, context):
        return context and context.object and context.object.type=='ARMATURE'

    def execute(self, context):
        filepath = self.filepath
        jointtype = 'POS'
        arm   = context.object
        dbones = arm.data.bones
        valid_bones = get_valid_bones(arm, dbones, dbones)
        definitions = data.load_skeleton_data(data.GENERATE_SKELETON_DATA, 'BASIC', jointtype)
        extended_def= data.get_rigtype_boneset('EXTENDED', jointtype, filepath)
        
        mBones = [b for b in valid_bones if b.name[0] == 'm']
        cBones = [b for b in valid_bones if b.name[0] != 'm']



        skeleton_xml = et.Element('linden_skeleton',
                   attrib={'version':'2.0',
                           'num_bones':str(len(mBones)),
                           'num_collision_volumes':str(len(cBones))}
                   )



        roots = [b for b in dbones if b.parent == None]

        sl_rotated = is_SL_orientation(dbones)
        if (sl_rotated):
            print("Model is in SL Orientation")
        else:
            print("Model is in Avastar Orientation")

        create_bone_hierarchy(skeleton_xml, definitions, extended_def, arm, dbones, roots, sl_rotated)

        f = open(filepath, 'w')
        f.write(prettyXML(skeleton_xml))
        f.close()

        print("SL avatar skeleton exported to:", filepath)
        return {'FINISHED'}




class ImportAvatarSkeletonOp(bpy.types.Operator, ExportHelper):
    bl_idname = "avastar.import_sl_avatar_skeleton"
    bl_label = "SL Skeleton (xml)"
    bl_description ="Create new Avastar Character using custom avatar_skeleton"
    bl_options = {'REGISTER', 'UNDO'}


    filename_ext = ".xml"

    filter_glob : StringProperty(
            default="*.xml",
            options={'HIDDEN'},
            )

    quads : BoolProperty(
                name="with Quads",
                description="create Avastar with Quads",
                default=False,
                options={'HIDDEN'},
                )

    no_mesh : BoolProperty(
                name="only Armature",
                description="create only the Avastar Rig (no Avastar meshes, good for creating custom avatars)",
                default=False,
                options={'HIDDEN'},
                )
                
    with_extended_drivers : BoolProperty(
                name="With All Drivers",
                description="Create all drivers when importing the skeleton.\nNote: When you want to edit the imported avatar-skeleton.xml\nand later export the skeleton file,\n then you must disable this option!",
                default = False)

    @classmethod
    def poll(self, context):
        if context.active_object:
            return context.active_object.mode == 'OBJECT'
        return True
        
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self,'with_extended_drivers')

    def execute(self, context):

        max_param_id = -1 if self.with_extended_drivers else 29999
        oselect_modes = util.set_mesh_select_mode((False,True,False))

        arm_obj = create.createAvatar(context, quads=self.quads, no_mesh = self.no_mesh, rigType='EXTENDED', max_param_id=max_param_id)
        util.set_active_object(context, arm_obj)
        shape.resetToRestpose(arm_obj, context)
        arm_obj.RigProp.Hand_Posture = HAND_POSTURE_DEFAULT
        util.set_mesh_select_mode(oselect_modes)
        return {'FINISHED'}




#




def compare(active=None, selected=None):  
    if not active:
        active=bpy.context.object
    if not selected:
        selected = bpy.context.selected_objects

    type = active.type
    print("%s type %s" % (active, type))
    of_different_type = [o for o in selected if o!=active and o.type != type]
    of_same_type = [o for o in selected if o != active and o.type == type]

    for o in of_different_type:
        print("%s has type %s - can not compare" % (o.name, o.type) )
    for o in of_same_type:
        print("%s added to comparison" % (o.name) )
    if type == 'ARMATURE':
        armature_compare(active, of_same_type)
        
def armature_compare(active, selected):
        dbones = active.data.bones
        print("%s has %d bones" % (active.name, len(dbones)))
        for other in selected:
            odbones = other.data.bones
            print("%s bonecount %s" % (other.name, "matches" if len(dbones) == len(odbones) else len(odbones)))
            bone_compare(active, other)
            
def bone_compare(this_armature, other_armature):
    adbones = this_armature.data.bones
    odbones = other_armature.data.bones
    for adbone in adbones:
        bname = adbone.name
        if bname in odbones:
            bone_data_compare(bname, this_armature, other_armature)
        else:
            print("Bone %s does not exist in armature %s" % (dname, other_armature.name) )

MAXVAL=0.001
            
def bone_data_compare(bname, this_armature, other_armature):
    adbone = this_armature.data.bones[bname]
    odbone = other_armature.data.bones[bname]
    tell_diff(adbone.head, odbone.head, vectorcomp, "bone %s: head active: %s" % (bname, "%s other:%s"))
    tell_diff(adbone.tail, odbone.tail, vectorcomp, "bone %s: tail active: %s" % (bname, "%s other:%s"))

    tell_diff(tovec(adbone.get('bind_mat')),
              tovec(odbone.get('bind_mat')),
              vectorcomp,
              "bone %s bind_mat%s" % (bname, "\n%s\n%s"))

def tovec(v):
    return Vector(v) if v else None

def  tell_diff(item1, item2, comp, template):
    if not comp(item1, item2):
        print(template % (item1, item2))

def vectorcomp(vec1,vec2):
    if not (vec1 or vec2):
        return True
    if not (vec1 and vec2):
        return False
    return all([abs(a-b)<MAXVAL for a,b in zip(vec1, vec2)])

def matrixcomp(mat1, mat2):
    for i in range(len(mat1)):
        for j in range(len(mat1)):
            if abs(mat1[i][j]- mat2[i][j]) > MAXVAL:
                return False
    return True

classes = (
    ExportAvatarSkeletonOp,
    ImportAvatarSkeletonOp,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered generate:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered generate:%s" % cls)
