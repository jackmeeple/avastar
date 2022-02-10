### Copyright 2011-2012 Magus Freston, Domino Marama, and Gaia Clary
### Copyright 2013-2015 Gaia Clary
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

import bpy, os, logging
import  xml.etree.ElementTree as et
from struct import unpack
from math import radians
from mathutils import Euler, Vector
from . import util, const
from .util import V, sym, s2b, s2bo, mulmat, matrixScale, matrixLocation, float_array_from_string
from .const import *

log = logging.getLogger('avastar.data')
registerlog = logging.getLogger("avastar.register")





WEIGHTSMAP = {
    'hairMesh':[('mNeck','mHead'), ('mHead', None)],
    'headMesh':[('mNeck','mHead'), ('mHead', None)],
    'eyelashMesh':[('mHead',  None)],
    'upperBodyMesh':[('mPelvis','mTorso' ), ('mTorso', 'mChest'), ('mChest', 'mNeck'), ('mNeck', None),
                    ('mChest','mCollarLeft' ), ('mCollarLeft', 'mShoulderLeft'), ('mShoulderLeft', 'mElbowLeft'), ('mElbowLeft','mWristLeft' ), 
                    ('mWristLeft',None), ('mChest','mCollarRight' ), ('mCollarRight', 'mShoulderRight'), ('mShoulderRight', 'mElbowRight'),
                    ('mElbowRight','mWristRight' ), ('mWristRight', None)],
    'lowerBodyMesh':[('mPelvis','mHipRight'), ('mHipRight', 'mKneeRight'), ('mKneeRight', 'mAnkleRight'), ('mAnkleRight',  None),
                    ('mPelvis', 'mHipLeft'), ('mHipLeft', 'mKneeLeft'), ('mKneeLeft','mAnkleLeft'), ('mAnkleLeft', None)],
     'skirtMesh':[('mTorso', 'mPelvis'),('mPelvis',None ),('mPelvis','mHipRight' ),('mHipRight','mKneeRight' ),
                ('mKneeRight', None),('mPelvis', 'mHipLeft'),('mHipLeft','mKneeLeft' ),('mKneeLeft',None)],

     'eyeBallLeftMesh':[('mEyeLeft', None)],
     'eyeBallRightMesh':[('mEyeRight', None)],
}

def get_armature_rigtype(armobj):
    RigType = armobj.RigProp.RigType
    if not RigType:
        RigType = armobj.AnimProp.RigType
    if not RigType:
        RigType='BASIC'
    return RigType

def clear_mtui_bones(context, armobj=None):
    scn = context.scene
    prop = scn.MocapProp
    if not armobj:
        armobj = get_retarget_target(context)

    boneset = get_mtui_bones(armobj)
    for targetbone in boneset:
        setattr(prop, targetbone, "")

def get_dict_from_mtui_bones(context, armobj=None):
    scn = context.scene
    prop = scn.MocapProp
    if not armobj:
        armobj = get_retarget_target(context)

    dict = {}
    bones = armobj.data.bones
    for key, val in prop.items():
        if key in bones:
            dict[key]=val
    return dict

def fill_mtui_bones(context, dict, armobj=None):
    if not armobj:
        armobj = get_retarget_target(context)
    scn = context.scene
    prop = scn.MocapProp
    bones = armobj.data.bones

    for key, val in dict.items():
        if key in bones:
            prop[key]=val

def get_retarget_target(context):
    scn = context.scene
    prop = scn.MocapProp
    target = bpy.data.objects[prop.target]
    return target

def get_mtui_bones(armobj=None):
    RigType = 'EXTENDED' if armobj == None else get_armature_rigtype(armobj)
    return MTUIBONES_EXTENDED if RigType == 'EXTENDED' else MTUIBONES

def get_mt_bones(armobj=None):
    RigType = 'EXTENDED' if armobj == None else get_armature_rigtype(armobj)
    return MTBONES_EXTENDED if RigType == 'EXTENDED' else MTBONES

def get_mcm_bones(armobj=None):
    RigType = 'EXTENDED' if armobj == None else get_armature_rigtype(armobj)
    return MCMBONES_EXTENDED if RigType == 'EXTENDED' else MCMBONES

def get_msl_bones(armobj=None):
    RigType = 'EXTENDED' if armobj == None else get_armature_rigtype(armobj)
    return MSLBONES_EXTENDED if RigType == 'EXTENDED' else MSLBONES

def get_volume_bones(obj=None, only_deforming=False):
    armobj = util.get_armature(obj) if obj else None
    if armobj and only_deforming:
        bones = util.get_modify_bones(armobj)
        bone_set = [bone.name for bone in bones if bone.name in SLVOLBONES and bone.use_deform]
    else:
        bone_set = SLVOLBONES
    return bone_set
    
def get_base_bones(obj=None, only_deforming=False):
    armobj = util.get_armature(obj) if obj else None
    if armobj and only_deforming:
        bones = util.get_modify_bones(armobj)
        bone_set = [bone.name for bone in bones if bone.name in SLBASEBONES and bone.use_deform]
    else:
        bone_set = SLBASEBONES
    return bone_set
    
def get_extended_bones(obj, only_deforming=False):
    armobj = util.get_armature(obj)
    bones = util.get_modify_bones(armobj)    
    if only_deforming:
        bone_set = [bone.name for bone in bones if bone.name[0]=='m' and bone.name not in SLBASEBONES and bone.use_deform]
    else:
        bone_set = [bone.name for bone in bones if bone.name[0]=='m' and bone.name not in SLBASEBONES]
    return bone_set

def get_bone_sections(bone, sections):
   return [li[0] for li in enumerate(bone.layers) if li[1] and li[0] in sections]

def get_deform_bones(obj, rig_sections, excludes, visible=None, selected=None, use_x_mirror=False):
    armobj = util.get_armature(obj)
    if armobj:
        bone_set = get_deform_bones_for_sections(armobj, rig_sections, excludes, visible=visible, selected=selected)
        if use_x_mirror:
            missing_mirror_bones = util.get_missing_mirror_bone_names(bone_set)
            bone_set.extend(missing_mirror_bones)
    else:
        bone_set = []

    return bone_set

def get_deform_bones_for_sections(armobj, rig_sections, excludes, visible=None, selected=None):
    exclude_eyes = B_EXTENDED_LAYER_SL_EYES in excludes
    exclude_alt_eyes = B_EXTENDED_LAYER_ALT_EYES in excludes
    include_all_deform_bones = B_EXTENDED_LAYER_ALL in rig_sections

    if selected:
        bones = util.getVisibleSelectedBones(armobj)
    elif visible:
        bones = util.getVisibleBones(armobj)
    else:
        bones =  armobj.data.bones

    bone_set = []
    tink=0
    for bone in bones:

        if not bone.use_deform:
            continue
        if visible and bone.hide:
            continue
        if selected and not bone.select:
            continue
        if bone.name.startswith('mEyeAlt'):
           if not exclude_alt_eyes:
               bone_set.append(bone.name)
           continue
        elif bone.name.startswith('mEye'):
            if not exclude_eyes:
                bone_set.append(bone.name)
            continue

        if include_all_deform_bones:
            if not get_bone_sections(bone, excludes):
                bone_set.append(bone.name)
        else:
            bone_sections = get_bone_sections(bone, rig_sections)
            if bone_sections:
                if not get_bone_sections(bone, excludes):
                     bone_set.append(bone.name)

    return bone_set

def get_selected_bones(armobj, weightBoneSelection, rig_sections, excludes):
    if weightBoneSelection == 'SELECTED':
        bone_set = get_deform_bones_for_sections(armobj, rig_sections, excludes, selected=True)
    elif weightBoneSelection == 'VISIBLE':
        bone_set = get_deform_bones_for_sections(armobj, rig_sections, excludes, visible=True)
    else:
        bone_set = get_deform_bones_for_sections(armobj, rig_sections, excludes)
    return bone_set


def getVertexIndex(mesh, vertex):
    vmap = mesh['vertexRemap']
    vi = vmap[vertex] if vertex in vmap else vertex
    return(mesh['vertLookup'].index(vi))



def loadLLM(name, filename):
    '''
    load and parse binary mesh file (llm)
    '''

    stream = open( filename, 'rb' )
    llm = {}
    llm['header'] = stream.read(24).decode('utf-8').split( "\x00" )[0]
    hasWeights = unpack( "B", stream.read(1) )[0]
    hasDetailTexCoords = unpack( "B", stream.read(1) )[0]
    llm['position'] = unpack( "<3f", stream.read(12) )
    llm['rotationAngles'] = unpack( "<3f", stream.read(12) )
    llm['rotationOrder'] = unpack( "B", stream.read(1) )[0]
    llm['scale'] = unpack( "<3f", stream.read(12) )
    numVertices = unpack( "<H", stream.read(2) )[0]

    EYE_SCALE = 1

    scale = (1,1,1)


    if name == "eyeBallLeftMesh":
        shift = (0.0729999989271164+0.0006, 0.035999998450279236, 1.7619999647140503-0.0003)
        scale = (EYE_SCALE, EYE_SCALE, EYE_SCALE)


    elif name == "eyeBallRightMesh":
        shift = (0.0729999989271164+0.0006, -0.035999998450279236, 1.7619999647140503-0.0003)
        scale = (EYE_SCALE, EYE_SCALE, EYE_SCALE)


    else:
        shift = (0,0,0)    
    

    llm['baseCoords'] = []
    for i in range(numVertices):
        co = unpack("<3f", stream.read(12)) 
        llm['baseCoords'].append(s2b((co[0]*scale[0]+shift[0], co[1]*scale[1]+shift[1], co[2]*scale[2]+shift[2])))
        
    llm['baseNormals'] = []
    for i in range(numVertices):
        llm['baseNormals'].append( s2b(unpack( "<3f", stream.read(12) )))
        
    llm['baseBinormals'] = []
    for i in range(numVertices):
        llm['baseBinormals'].append( s2b(unpack( "<3f", stream.read(12) )))
    

    llm['texCoords'] = []
    for i in range(numVertices):
        llm['texCoords'].append( unpack( "<2f", stream.read(8) ))
    

    if hasDetailTexCoords:
        llm['detailTexCoords'] = []
        for i in range(numVertices):
            llm['detailTexCoords'].append( unpack( "<2f", stream.read(8) ))
    


    #









    #

    #
    if hasWeights:
        llm['weights'] = []
        for i in range(numVertices):
            raw = unpack( "<f", stream.read(4) )[0]
            idx = int(raw)-1
            iweight = raw-int(raw)
            llm['weights'].append( (idx, iweight) )
            
    if name == "eyeBallLeftMesh" or name == "eyeBallRightMesh":
        llm['weights'] = [(0,0.0)]*numVertices


    numFaces = unpack( "<H", stream.read(2) )[0]
    llm['faces'] = []
    for i in range(numFaces):
        llm['faces'].append( unpack( "<3H", stream.read(6) ))
    

    if hasWeights:
        numSkinJoints = unpack( "<H", stream.read(2) )[0]
        llm['skinJoints'] = []
        for i in range(numSkinJoints):
            llm['skinJoints'].append(stream.read(64).decode('utf-8').split("\x00")[0])
        
    if name == "eyeBallLeftMesh":
        llm['skinJoints'] = ['mEyeLeft']
    elif name == "eyeBallRightMesh":
        llm['skinJoints'] = ['mEyeRight']

    llm['morphsbyname'] = {}
    n = stream.read(64).decode('utf-8').split("\x00")[0]
    while n != "End Morphs":
        morph = {'name':n}
        numMorphVertices = unpack( "<L", stream.read(4) )[0]
        morph['vertices'] = []
        for i in range(numMorphVertices):
            v = {}
            v['vertexIndex'] = unpack( "<L", stream.read(4) )[0] # 0-indexed
            v['coord'] = s2b(unpack( "<3f", stream.read(12) ))
            v['normal'] = s2b(unpack( "<3f", stream.read(12) ))
            v['binormal'] = s2b(unpack( "<3f", stream.read(12) ))
            v['texCoord'] = unpack( "<2f", stream.read(8) )
            morph['vertices'].append( v )
        llm['morphsbyname'][n] = morph
        n = stream.read(64).decode('utf-8').split("\x00")[0]
        

    numRemaps = unpack( "<l", stream.read(4) )[0]
    map = {}
    llm['vertexRemap'] = map
    for i in range(numRemaps):
        remap = unpack( "<2l", stream.read(8) )
        map[ remap[0] ] = remap[1]
    stream.close()

    llm['vertLookup'] = [i for i in range(len(llm['baseCoords'])) if i  not in map]

    return llm


def cleanId(nid, name):

    #










    #





    unique_id = "%s_%s" % (name.lower().replace(" ","_"), nid)
    return unique_id



def loadDrivers(max_param_id=-1):
    '''
    Read in shape drivers from avatar_lad.xml
    '''

    #

    #


















    ladxml = et.parse(util.get_lad_file())

    DRIVERS = {}
    
    #

    #
    meshes = ladxml.findall('mesh')
    for mesh in meshes:
        lod = int(mesh.get('lod'))
        if lod != 0:

            continue

        mname = mesh.get('type')

        
        params = mesh.findall('param')       
        for p in params:
            pname = p.get('name')
            id  = int(p.get('id'))
            pid = cleanId(id, pname)
            



                
            paramd = {'pid': pid,
                      'name': pname,
                      'type': 'mesh',
                      'label': p.get('label', pname),
                      'label_min': p.get('label_min'),
                      'label_max': p.get('label_max'),
                      'value_default': float(p.get('value_default', "0")),
                      'value_min': float(p.get('value_min')),
                      'value_max': float(p.get('value_max')),
                      'sex': p.get('sex', None),
                      'edit_group': p.get('edit_group', None),
                      'mesh': mname,
                      } 
           
            vbones = []

            param_morphs = p.findall('param_morph')
            for param_morph in param_morphs:
                volume_morphs = param_morph.findall('volume_morph')
                for vol in volume_morphs:
                
                    scale = util.float_array_from_string(vol.get('scale'))
                    pos   = util.float_array_from_string(vol.get('pos'))
                    vname = vol.get('name')
                    
                    if all(v == 0 for v in scale):
                        log.info("Volume Morph %s has no scale" % (vname))
                    
                    vbone = {
                        'name':vname,
                        'scale':s2bo(scale),
                        'offset':s2b(pos),
                    }
                    vbones.append(vbone)
            
            paramd['bones'] = vbones
        
            if max_param_id == -1 or id < max_param_id:
                if pid in DRIVERS:
                    DRIVERS[pid].append(paramd)
                else:
                    DRIVERS[pid] = [paramd]

    #

    #
    params = ladxml.findall('skeleton')[0].findall('param')
    for p in params:

        pname = p.get('name')
        id    = int(p.get('id'))
        if max_param_id > -1 and id < max_param_id:
            continue
            
        pid = cleanId(id, pname)


        paramd = {'pid': pid,
                  'name': pname,
                  'type': 'bones',
                  'label': p.get('label', pname),
                  'label_min': p.get('label_min'),
                  'label_max': p.get('label_max'),
                  'value_default': float(p.get('value_default', 0)),
                  'value_min': float(p.get('value_min')),
                  'value_max': float(p.get('value_max')),
                  'edit_group': p.get('edit_group', None),
                  'sex': p.get('sex', None),
                  }

        try:
            bones = p.findall('param_skeleton')[0].findall('bone')
        except:
            log.warning("Issue in param [%s]" % pname)
            continue
        bs = []
        for b in bones:
            bname = b.get('name')
            scale = s2bo(util.float_array_from_string(b.get('scale')))


            raw = util.vector_from_string(b.get('offset'))
            offset = s2b(raw)


            bs.append({'name':bname, 'scale':scale, 'offset':offset})

        paramd['bones'] = bs


        if pid in DRIVERS:
            logging.error("unexpected duplicate pid: %s", pid)
        else:
            DRIVERS[pid] = [paramd]

    #


    drivers = ladxml.findall('driver_parameters')[0].findall('param')
    for p in drivers:
        id    = int(p.get('id'))
        if max_param_id > -1 and id < max_param_id:
            continue
            
        pname = p.get('name')
        pid = cleanId(id, pname)

        paramd = {'pid': pid,
                  'name': pname,
                  'label': p.get('label', pname),
                  'type': 'driven',
                  'label_min': p.get('label_min'),
                  'label_max': p.get('label_max'),
                  'value_default': float(p.get('value_default', 0)),
                  'value_min': float(p.get('value_min')),
                  'value_max': float(p.get('value_max')),
                  'edit_group': p.get('edit_group', None),
                  'sex': p.get('sex', None),
                  }

        dr = []
        driven=p.findall('param_driver')[0].findall('driven')
        for d in driven:










            ##


            nid="_"+d.get('id')

            did = None
            for driver in DRIVERS.keys():
                if driver.endswith(nid):
                    did=driver
                    break

            if did is None:

                continue

            drivend = {'pid':did,
                       'min1':float(d.get('min1', paramd['value_min'])),
                       'max1':float(d.get('max1', paramd['value_max'])),
                       'min2':float(d.get('min2', paramd['value_max'])),
                       'max2':float(d.get('max2', paramd['value_max'])),
                       }
            dr.append(drivend)


        paramd['driven']=dr

        if pid in DRIVERS:
            logging.error("unexpected duplicate pid: %s", pid)
        else:
            DRIVERS[pid] = [paramd]
                
    
    return DRIVERS

SEAM_EXCEPTIONS = {}
SEAM_EXTRA      = {}
PIN_EXTRA       = {}





SEAM_EXCEPTIONS['upperBodyMesh']  = [129, 168, 181, 200, 339, 1166, 1480, 1676, 1781, 2489,
                                     3048, 3273, 3380, 3430, 3885, 4189, 4351, 4709, 4744,
                                     5026, 5183, 5490]
SEAM_EXTRA['upperBodyMesh']       = []
PIN_EXTRA['upperBodyMesh']        = []
#







#
#



SEAM_EXCEPTIONS['lowerBodyMesh']  = [248, 803, 1114, 1258, 1389, 1614, 1670, 2122]
SEAM_EXTRA['lowerBodyMesh']       = []
PIN_EXTRA['lowerBodyMesh']        = []






#
#










SEAM_EXCEPTIONS['headMesh']      = [144, 347, 382, 532, 595, 621, 778, 784, 835, 862,
                                    1022, 1162, 1206, 1225, 1436, 1551, 1687, 1712, 1802,
                                    1829, 1852, 1872, 1885, 1902, 2097, 2152, 2203,
                                    2317, 2349, 2444, 1174, 1939, 467, 489, 526, 570,
                                    674, 699, 756, 999, 1210, 1235, 1261, 1301, 1352,
                                    1395, 1655, 1681, 1815, 1970, 2085, 2118, 2146, 2567,
                                    312, 554, 1359, 1402, 1752, 1949, 2075, 2460, 2510, 2554,
                                    467, 526, 570, 674, 699, 999, 1261, 1301, 1655, 2085, 2118, 2567
                                    ]
SEAM_EXTRA['headMesh']            = []
PIN_EXTRA['headMesh']             = []








#





#
#




#
#








SHAPEKEYS = {}
MESHES = {}

def get_avastar_shapekeys(ob):
    global SHAPEKEYS
    if len(SHAPEKEYS) == 0:
        loadMeshes()

    return SHAPEKEYS
    
def has_avastar_shapekeys(ob):
    if not (ob and ob.data.shape_keys):
        return False
    shapekeys = get_avastar_shapekeys(ob)
    for x in ob.data.shape_keys.key_blocks.keys():
        if x in shapekeys:
            return True
    return False


def loadMeshes():
    '''
    Load the mesh details from avatar_lad.xml and the .llm files
    '''
    global MESHES
    if len(MESHES) > 0:
        return MESHES

    global SHAPEKEYS
    ladxml = et.parse(util.get_lad_file())

    logging.info("Loading avatar data")

    meshes = ladxml.findall('mesh')
    for mesh in meshes:
        lod = int(mesh.get('lod'))
        if lod != 0:

            continue

        name = mesh.get('type')

        file_name = mesh.get('file_name')



        meshd = loadLLM(name, os.path.join(DATAFILESDIR,file_name))
        meshd['name'] = name
       


        meshd['morphs'] = {}

        MESHES[name] = meshd
        if name in SEAM_EXCEPTIONS:
           meshd['noseams']    = SEAM_EXCEPTIONS[name]
           meshd['extraseams'] = SEAM_EXTRA[name]
           meshd['extrapins']  = PIN_EXTRA[name]


        params = mesh.findall('param')       
        for p in params:
            pname = p.get('name')



            try:
                morph = meshd['morphsbyname'][pname]
            except KeyError as e:

                continue

            pid = cleanId(p.get('id'), pname)
            SHAPEKEYS[pid]=morph




           


            meshd['morphs'][pid]   = morph
            morph['value_min']     = float(p.get('value_min'))
            morph['value_max']     = float(p.get('value_max'))
            morph['value_default'] = float(p.get('value_default', 0))

    return MESHES










skeleton_meta = {}
def getCachedSkeletonDefinition(rigType, jointType):
    global skeleton_meta
    key = "%s_%s" % (rigType, jointType)
    
    skeleton = skeleton_meta.get(key, None)
    if skeleton:
        return skeleton

    skeleton = getSkeletonDefinitionFromFile(rigType, jointType)
    skeleton_meta[key] = skeleton

    return skeleton


def getSkeletonDefinitionFromFile(rigType, jointType):
    
    filepath = util.get_skeleton_file()
    boneset = load_skeleton_data(filepath, rigType, jointType)

    skeleton = Skeleton(rigType, jointType)
    skeleton.add_boneset(boneset)
    return skeleton

def getSkeletonDefinition(rigType, jointType):
    pref = util.getAddonPreferences()

    if pref.rig_cache_data:
        return getCachedSkeletonDefinition(rigType, jointType)
    else:
        return getSkeletonDefinitionFromFile(rigType, jointType)





UNCONNECTED='UNCONNECTED'
CONNECT_HEAD='CONNECT_HEAD'
CONNECT_TAIL='CONNECT_TAIL'

STRUCTURE_PARENT=0
STRUCTURE_CHILD=1
STRUCTURE_GROUP=2
STRUCTURE_LAYER=3
STRUCTURE_RIGTYPE=4    # BASIC_RIG, EXTENDED_RIG
STRUCTURE_PARENT_CONNECT=5 # UNCONNECTED, CONNECT_HEAD, CONNECT_TAIL
STRUCTURE_CHILD_CONNECT=6 # UNCONNECTED, CONNECT_HEAD, CONNECT_TAIL
STRUCTURE_HEAD=7       # Head 
STRUCTURE_TAIL=8       # When Vector then tail is relative to head

STRUCTURE_BONES = OrderedDict ( [

    ("COG",             ["Origin",      None,             "Torso",        B_LAYER_TORSO,     BASIC_RIG,    UNCONNECTED,  UNCONNECTED,  "Torso",  Vector((0.0, 0.1,  0.0))]),
    ("Torso",           ["COG",         None,             "Torso",        B_LAYER_TORSO,     BASIC_RIG,    CONNECT_HEAD, CONNECT_HEAD,  "COG", "Chest"]),
    ("Tinker",          ["COG",         None,             "Torso",        B_LAYER_TORSO,     BASIC_RIG,    CONNECT_HEAD, CONNECT_HEAD, "Torso",  "mPelvis"]),
    ("Pelvis",          ["Tinker",      None,             "Torso",        B_LAYER_TORSO,     BASIC_RIG,    UNCONNECTED,  UNCONNECTED,  "mPelvis","Torso"]),

    ("CollarLinkLeft",  ["Chest",       "CollarLeft",     "Structure",    B_LAYER_STRUCTURE, BASIC_RIG,    CONNECT_TAIL, CONNECT_TAIL, None,           None]),
    ("CollarLinkRight", ["Chest",       "CollarRight",    "Structure",    B_LAYER_STRUCTURE, BASIC_RIG,    CONNECT_TAIL, CONNECT_TAIL, None,           None]),
    ("HipLinkLeft",     ["Pelvis",      "HipLeft",        "Structure",    B_LAYER_STRUCTURE, BASIC_RIG,    CONNECT_TAIL, CONNECT_TAIL, None,           None]),
    ("HipLinkRight",    ["Pelvis",      "HipRight",       "Structure",    B_LAYER_STRUCTURE, BASIC_RIG,    CONNECT_TAIL, CONNECT_TAIL, None,           None]),

    ("HandThumb0Left",  ["WristLeft",   "HandThumb1Left",  "Handstructure", B_LAYER_HAND,    EXTENDED_RIG, CONNECT_HEAD, CONNECT_TAIL, None, None]),
    ("HandIndex0Left",  ["WristLeft",   "HandIndex1Left",  "Handstructure", B_LAYER_HAND,    EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((0.015,-0.028,0.018)), None]),
    ("HandMiddle0Left", ["WristLeft",   "HandMiddle1Left", "Handstructure", B_LAYER_HAND,    EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((0.0175,-0.013,0.018)), None]),
    ("HandRing0Left",   ["WristLeft",   "HandRing1Left",   "Handstructure", B_LAYER_HAND,    EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((0.0175, 0.003,0.014)), None]),
    ("HandPinky0Left",  ["WristLeft",   "HandPinky1Left",  "Handstructure", B_LAYER_HAND,    EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((0.015, 0.015,0.007)), None]),

    ("HandThumb0Right",  ["WristRight", "HandThumb1Right",  "Handstructure", B_LAYER_HAND,   EXTENDED_RIG, CONNECT_HEAD, CONNECT_TAIL, None, None]),
    ("HandIndex0Right",  ["WristRight", "HandIndex1Right",  "Handstructure", B_LAYER_HAND,   EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((-0.015,-0.028,0.018)), None]),
    ("HandMiddle0Right", ["WristRight", "HandMiddle1Right", "Handstructure", B_LAYER_HAND,   EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((-0.0175,-0.013,0.018)), None]),
    ("HandRing0Right" ,  ["WristRight", "HandRing1Right",   "Handstructure", B_LAYER_HAND,   EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((-0.0175, 0.003,0.014)), None]),
    ("HandPinky0Right",  ["WristRight", "HandPinky1Right",  "Handstructure", B_LAYER_HAND,   EXTENDED_RIG, CONNECT_TAIL, CONNECT_TAIL, Vector((-0.015, 0.015,0.007)), None]),

    ("ThumbControllerRight", ["ElbowRight", "HandThumb0Right", "Handstructure", B_LAYER_HAND, EXTENDED_RIG, CONNECT_TAIL, UNCONNECTED, "WristRight", None]),
    ("ThumbControllerLeft",  ["ElbowLeft",  "HandThumb0Left",  "Handstructure", B_LAYER_HAND, EXTENDED_RIG, CONNECT_TAIL, UNCONNECTED, "WristLeft",  None]),

])

def get_special_bone_meta(bname):
    bone = STRUCTURE_BONES.get(bname)
    return bone

def fixate_special_bone_parent(child_name, parent_name):

    is_connected = None
    structure = get_special_bone_meta(child_name)
    if structure and parent_name != structure[STRUCTURE_PARENT]:
        parent_name = structure[STRUCTURE_PARENT]
        is_connected = structure[STRUCTURE_PARENT_CONNECT]==CONNECT_TAIL


    if child_name in SLVOLBONES and parent_name[0] != 'm':
        parent_name = 'm'+parent_name
    return parent_name, is_connected

ANIMATION_CONTROL_BONES = {
    "CWingLeft" :["Wing1Left",  "WingRoot", Vector((0,0,0.1)), "Wing"],
    "CWingRight":["Wing1Right", "WingRoot", Vector((0,0,0.1)), "Wing"]
    }

def get_hand_control_bones_for(boneset):
    lhcb  = {"C"+key[1:-5]+"Left":[key, "WristLeft", Vector((0,0,0.0)), "Hand", "CustomShape_Circle02"]   for key in boneset.keys() if key.startswith("mHand") and key.endswith("1Left")}
    rhcb  = {"C"+key[1:-6]+"Right":[key, "WristRight", Vector((0,0,0.0)), "Hand", "CustomShape_Circle02"] for key in boneset.keys() if key.startswith("mHand") and key.endswith("1Right")}
    return util.merge_dicts(lhcb, rhcb)
    

def load_control_bones(boneset, rigType):

    def add_bone(bone_name, bonegroup, boneset):
        bonelayers = BONEGROUP_MAP[bonegroup][BONEGROUP_MAP_LAYERS]
        log.debug("load_control_bones: add Special Bone %s (group:%s)" % (bone_name, bonegroup))
        bone = Bone(bone_name, bonegroup=bonegroup, bonelayers=bonelayers)
        boneset[bone_name] = bone
        return bone

    def add_control_bone(bone_name, boneset):

        if bone_name in boneset:
            return
        
        mBone = None
        mBoneName = "m"+bone_name
        if mBoneName in boneset:
            mBone = boneset[mBoneName]
            bonegroup = mBone.bonegroup if mBone.bonegroup[0] != 'm' else mBone.bonegroup[1:]
        else:
            log.warn("Custom bone: Set bone group for %s to %s" % (bone_name, bonegroup) )
            bonegroup = 'Custom'
        
        bone = add_bone(bone_name, bonegroup, boneset)
        
        if mBone:
            bone.copy(mBone)
            parentName = mBone.parent.blname
            if parentName[0] == 'm':
                parentName = parentName[1:]
            parent = boneset[parentName]
            bone.set(parent=parent)


    def add_structure_bone(bone_name, boneset, val):

        def get_relhead(parent, child, connect):
            if connect==CONNECT_TAIL:
                relhead = parent.reltail
            elif connect==CONNECT_HEAD:
                relhead = V0.copy()
            else:
                if child:
                    relhead = child.head()-parent.head()
                else:
                    relhead = V0.copy()
            return relhead

        def get_reltail(parent, child, connect):
            if child:
                if connect==CONNECT_TAIL:
                    reltail = child.relhead - parent.reltail 
                elif connect==CONNECT_HEAD:
                    reltail = child.head()-parent.head()
                else:
                    reltail = child.relhead.copy()
            else:
                reltail = parent.reltail.copy()
            return reltail

        def get_bone_diff(head, tail):

            if type(tail) is Vector:
                return tail
            if type(head) is Vector:
                return None

            tail = boneset.get(tail)
            head = boneset.get(head)
            if head == None:
                return None
            
            if tail == None:
                return head.tail() - head.head()

            return tail.head() - head.head()

        boneType = val[STRUCTURE_RIGTYPE]
        if rigType == BASIC_RIG and boneType == EXTENDED_RIG:
            return

        parent_name = val[STRUCTURE_PARENT]
        child_name  = val[STRUCTURE_CHILD]
        bonegroup   = val[STRUCTURE_GROUP]
        head_joint  = val[STRUCTURE_HEAD]
        tail_joint  = val[STRUCTURE_TAIL]
        parent_connect = val[STRUCTURE_PARENT_CONNECT]
        connected   = parent_connect == CONNECT_TAIL

        head        = get_bone_diff(parent_name, head_joint) if (head_joint and not type(head_joint) is Vector) else None
        tail        = get_bone_diff(head_joint, tail_joint) if (head_joint and not type(head_joint) is Vector) else None

        bone = boneset.get(bone_name)
        if not bone:
            bone = add_bone(bone_name, bonegroup, boneset)

        parent = boneset[parent_name]
        child  = boneset[child_name] if child_name else None

        relhead = head if head else get_relhead(parent, child, parent_connect)
        if type(head_joint) is Vector:
            relhead = relhead + head_joint
            connected = False
        reltail = tail if tail else get_reltail(parent, child, parent_connect)

        if type(head_joint) is Vector:
            reltail = reltail - head_joint
        bone.set(parent=parent, bonegroup=bonegroup, connected=connected, relhead=relhead, reltail=reltail)

        if child:
            child_connect = val[STRUCTURE_CHILD_CONNECT]
            child.set(parent=bone)
            if child_connect==CONNECT_TAIL:
                child.set(relhead=reltail, connected=True)
            elif child_connect==CONNECT_HEAD:
                child.set(relhead=relhead+reltail, connected=False)
            else:
                child.set(relhead=V0.copy(), connected=False)
        return bone


    def add_controller_bone(bone_name, boneset, val):

        bone = add_structure_bone(bone_name, boneset, val)
        return bone

    #

    #


    CONTROL_BONES   = [key[1:] for key in boneset.keys() if key.startswith("m") and key[1:] not in boneset]

    for bone_name in CONTROL_BONES:
        add_control_bone(bone_name, boneset)

    for bone_name in STRUCTURE_BONES:
        val = STRUCTURE_BONES[bone_name]
        add_structure_bone(bone_name, boneset, val)
 




    #




    #










    #




    preset_bone_custom_shapes(boneset)
    preset_bone_limitations(boneset)
    return


    











    #

    #


    #

    #

    #




def add_to_boneset(boneset, bonename, **args):
    bone = boneset.get(bonename, None)
    if bone:
        bone.set(**args)


def get_shape_for_bone(name):
    shape = BONESHAPE_MAP.get(name,None)
    return shape


def preset_bone_custom_shapes(boneset, rigpart=CONTROL_BONE_RIG):

    for key, shape_name in BONESHAPE_MAP.items():
        bname = key if rigpart == CONTROL_BONE_RIG else 'm'+key if rigpart == DEFORM_BONE_RIG else None
        add_to_boneset(boneset, bname, shape=shape_name )


def preset_bone_constants(boneset, rigType):
    from .util import V
    #

    #







    

    pelvishead = boneset['mPelvis'].relhead
    pelvistail = boneset['mPelvis'].reltail
    coghead    = pelvishead+pelvistail # COG is relative to Origin like mPelvis!

    add_to_boneset(boneset, "Torso",     shape="CustomShape_Torso", relhead=(0,0,0), connected=False)
    add_to_boneset(boneset, "COG",       shape="CustomShape_COG",    relhead=coghead, reltail=(0,0.1,0) , connected=False)
    add_to_boneset(boneset, "Tinker",    shape="CustomShape_Pelvis", relhead=(0,0,0), reltail=-pelvistail, connected=False, bonegroup='IK Legs', bonelayers=[B_LAYER_IK_LEGS])
    add_to_boneset(boneset, "Pelvis",    shape="CustomShape_Target", relhead=-pelvistail, reltail=pelvistail, connected=False)



    collarLeft  = boneset["mCollarLeft"]
    collarRight = boneset["mCollarRight"]
    hipLeft     = boneset["mHipLeft"]
    hipRight    = boneset["mHipRight"]
    chest       = boneset["mChest"]
    pelvis      = boneset["mPelvis"]

    add_to_boneset(boneset, "CollarLeft",      relhead=collarLeft.relhead,  reltail=collarLeft.reltail,  shape="CustomShape_Collar")
    add_to_boneset(boneset, "CollarRight",     relhead=collarRight.relhead, reltail=collarRight.reltail, shape="CustomShape_Collar")
    add_to_boneset(boneset, "HipLeft",         relhead=hipLeft.relhead,     reltail=hipLeft.reltail,     shape="CustomShape_Circle03")
    add_to_boneset(boneset, "HipRight",        relhead=hipRight.relhead,    reltail=hipRight.reltail,    shape="CustomShape_Circle03")

    add_to_boneset(boneset, "CollarLinkLeft",  relhead=chest.reltail,  reltail=collarLeft.relhead-chest.reltail, is_structure=True)
    add_to_boneset(boneset, "CollarLinkRight", relhead=chest.reltail,  reltail=collarRight.relhead-chest.reltail, is_structure=True)
    add_to_boneset(boneset, "HipLinkLeft",     relhead=pelvis.reltail, reltail=hipLeft.relhead-pelvis.reltail, is_structure=True, connected=False)
    add_to_boneset(boneset, "HipLinkRight",    relhead=pelvis.reltail, reltail=hipRight.relhead-pelvis.reltail, is_structure=True, connected=False)


    add_to_boneset(boneset, "Chest",         shape="CustomShape_Circle10")
    add_to_boneset(boneset, "Neck",          shape="CustomShape_Neck")
    add_to_boneset(boneset, "Head",          shape="CustomShape_Head")
    add_to_boneset(boneset, "ShoulderLeft",  shape="CustomShape_Circle03")
    add_to_boneset(boneset, "ShoulderRight", shape="CustomShape_Circle03")
    add_to_boneset(boneset, "ElbowLeft",     shape="CustomShape_Circle03")
    add_to_boneset(boneset, "ElbowRight",    shape="CustomShape_Circle03")
    add_to_boneset(boneset, "WristLeft",     shape="CustomShape_Circle05")
    add_to_boneset(boneset, "WristRight",    shape="CustomShape_Circle05")
    add_to_boneset(boneset, "KneeLeft",      shape="CustomShape_Circle03")
    add_to_boneset(boneset, "KneeRight",     shape="CustomShape_Circle03")
    add_to_boneset(boneset, "AnkleLeft",     shape="CustomShape_Circle05")
    add_to_boneset(boneset, "AnkleRight",    shape="CustomShape_Circle05")

    if rigType == BASIC_RIG:
        return

    elbowLeft = boneset["mElbowLeft"]
    wristLeft = boneset["mWristLeft"]
    
    handThumb0Left  = boneset["HandThumb0Left"]
    handIndex0Left  = boneset["HandIndex0Left"]
    handMiddle0Left = boneset["HandMiddle0Left"]
    handRing0Left   = boneset["HandRing0Left"]
    handPinky0Left  = boneset["HandPinky0Left"]

    handThumb1Left  = boneset["HandThumb1Left"]
    handIndex1Left  = boneset["HandIndex1Left"]
    handMiddle1Left = boneset["HandMiddle1Left"]
    handRing1Left   = boneset["HandRing1Left"]
    handPinky1Left  = boneset["HandPinky1Left"]


    thumb_tail = wristLeft.reltail + handThumb1Left.relhead
    add_to_boneset(boneset, "HandThumb0Left",  relhead = elbowLeft.reltail, reltail = handThumb1Left.relhead-elbowLeft.reltail, connected=False, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandIndex0Left",  relhead = wristLeft.reltail, reltail = handIndex1Left.relhead-wristLeft.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandMiddle0Left", relhead = wristLeft.reltail, reltail = handMiddle1Left.relhead-wristLeft.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandRing0Left",   relhead = wristLeft.reltail, reltail = handRing1Left.relhead-wristLeft.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandPinky0Left",  relhead = wristLeft.reltail, reltail = handPinky1Left.relhead-wristLeft.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")

    add_to_boneset(boneset, "HandThumb1Left",  relhead = handThumb0Left.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandIndex1Left",  relhead = handIndex0Left.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandMiddle1Left", relhead = handMiddle0Left.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandRing1Left",   relhead = handRing0Left.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandPinky1Left",  relhead = handPinky0Left.reltail, connected=True, is_structure=False)
 
    elbowRight = boneset["mElbowRight"]
    wristRight = boneset["mWristRight"]
    handThumb0Right  = boneset["HandThumb0Right"]
    handIndex0Right  = boneset["HandIndex0Right"]
    handMiddle0Right = boneset["HandMiddle0Right"]
    handRing0Right   = boneset["HandRing0Right"]
    handPinky0Right  = boneset["HandPinky0Right"]

    handThumb1Right  = boneset["HandThumb1Right"]
    handIndex1Right  = boneset["HandIndex1Right"]
    handMiddle1Right = boneset["HandMiddle1Right"]
    handRing1Right   = boneset["HandRing1Right"]
    handPinky1Right  = boneset["HandPinky1Right"]

    thumb_tail = wristRight.reltail + handThumb1Right.relhead
    add_to_boneset(boneset, "HandThumb0Right",  relhead = elbowRight.reltail, reltail = handThumb1Right.relhead-elbowRight.reltail, connected=False, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandIndex0Right",  relhead = wristRight.reltail, reltail = handIndex1Right.relhead-wristRight.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandMiddle0Right", relhead = wristRight.reltail, reltail = handMiddle1Right.relhead-wristRight.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandRing0Right",   relhead = wristRight.reltail, reltail = handRing1Right.relhead-wristRight.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")
    add_to_boneset(boneset, "HandPinky0Right",  relhead = wristRight.reltail, reltail = handPinky1Right.relhead-wristRight.reltail, connected=True, is_structure=True, deform=False, group="Handstructure")

    add_to_boneset(boneset, "HandThumb1Right",  relhead = handThumb0Right.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandIndex1Right",  relhead = handIndex0Right.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandMiddle1Right", relhead = handMiddle0Right.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandRing1Right",   relhead = handRing0Right.reltail, connected=True, is_structure=False)
    add_to_boneset(boneset, "HandPinky1Right",  relhead = handPinky0Right.reltail, connected=True, is_structure=False)

    add_to_boneset(boneset, "ThumbControllerRight",
        relhead = elbowRight.reltail,
        reltail = wristRight.reltail,
        connected=True,
        is_structure=True,
        deform=False,
        group="Handstructure",
        shape="CustomShape_Circle02")

    add_to_boneset(boneset, "ThumbControllerLeft",
        relhead = elbowLeft.reltail,
        reltail = wristLeft.reltail,
        connected=True,
        is_structure=True,
        deform=False,
        group="Handstructure",
        shape="CustomShape_Circle02")
 



class Bone:

    bonegroups = []

    def __init__(self, blname, bvhname=None, slname=None, relhead=V0.copy(), reltail=Vector((0,0,-0.1)), parent=None, 
                 bonelayers=[B_LAYER_TORSO], shape=None, shape_scale=None, roll = 0, connected=False, group="Rig", 
                 stiffness=[0.0,0.0,0.0], limit_rx=None, limit_ry=None, limit_rz=None, deform=False,
                 scale0=V1.copy(), rot0=V0.copy(), skeleton='basic', bonegroup='Custom', 
                 mandatory='false', leaf=None, wire=True, pos0=V0.copy(), pivot0=V0.copy(), attrib= None,
                 end0=V0.copy(), is_structure=False):

        self.blname       = blname # Blender name
        self.children     = []
        self.parent       = None
        self.scale        = V0.copy()
        self.offset       = V0.copy()
        self.is_ik_root   = False
        self.ik_end       = None
        self.ik_root      = None
        self.wire         = True
        self.attrib       = None
        self.is_structure = False
        self.b0head       = V0.copy()
        self.b0tail       = V0.copy()
               
        self.set(all=True,
            bvhname    = bvhname,
            slname     = slname,
            relhead    = relhead,
            reltail    = reltail,
            parent     = parent, 
            bonelayers = bonelayers,
            shape      = shape,
            shape_scale= shape_scale,
            roll       = roll,
            connected  = connected,
            group      = group, 
            stiffness  = stiffness,
            limit_rx   = limit_rx,
            limit_ry   = limit_ry,
            limit_rz   = limit_rz,
            deform     = deform,
            scale0     = scale0,
            rot0       = rot0,
            pos0       = pos0,
            pivot0     = pivot0,
            skeleton   = skeleton,
            bonegroup  = bonegroup,
            mandatory  = mandatory,
            leaf       = leaf,
            wire       = wire,
            attrib     = attrib,
            end0       = end0,
            is_structure = is_structure
            )

    def copy(self, other_bone):
        EXCLUDED_ATTRIBUTES = ['blname', 'children', 'parent', 'bvhname', 'slname', 'bonelayers', 'shape', 'shape_scale', 'group', 'deform', 'bonegroup', 'attrib']
        for key, val in other_bone.__dict__.items():
            if key not in EXCLUDED_ATTRIBUTES:
                setattr(self, key, val)


    def set(self,all=False, bvhname=None, slname=None, 
            relhead=None, reltail=None, parent=None, 
            bonelayers=None, shape=None, shape_scale= None, 
            roll = None, connected=None, group=None, 
            stiffness=None, limit_rx=None, limit_ry=None, limit_rz=None, deform=None,
            scale0=None, rot0=None, pos0=None, pivot0=None, 
            skeleton=None, bonegroup=None, 
            mandatory=None, leaf=None, wire=None,
            attrib=None, end0=None, is_structure=None):

        if not shape:
            shape = get_shape_for_bone(self.blname)

        if all or bvhname   != None: self.bvhname   = bvhname   # BVH name or None
        if all or slname    != None: self.slname    = slname    # SL name or None
        if all or relhead   != None: self.relhead   = relhead   # Default bone head relative to parent head, SL frame
        if all or reltail   != None: self.reltail   = reltail   # Default bone tail relative to own head, SL frame

        if parent != None:
            old_parent = self.parent
            if old_parent and self in old_parent.children:
                old_parent.children.remove(self)

            self.parent = parent
            if not self in parent.children:
                parent.children.append(self) # set up the children bones
            
        if all or bonelayers != None: self.bonelayers = bonelayers    # layers bone will be visible on 
        if all or shape      != None: self.shape      = shape     # name of custom shape if used
        if all or shape_scale!= None: self.shape_scale= shape_scale# custom shape scale
        if all or roll       != None: self.roll       = roll      # bone roll angle in radians
        if all or connected  != None: self.connected  = connected # wether bone is connected to parent
        if all or group      != None: self.group      = group
        if all or scale0     != None: self.scale0     = scale0
        if all or rot0       != None: self.rot0       = rot0
        if all or pos0       != None: self.pos0       = pos0
        if all or pivot0     != None: self.pivot0     = pivot0
        if all or stiffness  != None: self.stiffness  = stiffness
        if all or limit_rx   != None: self.limit_rx   = limit_rx
        if all or limit_ry   != None: self.limit_ry   = limit_ry
        if all or limit_rz   != None: self.limit_rz   = limit_rz
        if all or deform     != None: self.deform     = deform
        if all or skeleton   != None: self.skeleton   = skeleton
        
        if all or bonegroup   != None:
            if not bonegroup in Bone.bonegroups:
                Bone.bonegroups.append(bonegroup)
            self.bonegroup     = bonegroup
            
        if all or mandatory  != None: self.mandatory = mandatory
        if all or leaf       != None: self.leaf      = leaf
        if all or wire       != None: self.wire      = wire
        if all or attrib     != None: self.attrib    = attrib
        if all or end0       != None: self.end0      = end0
        if all or is_structure != None: self.is_structure = is_structure

        
    def get_scale(self):
        if self.is_structure and self.parent:
            return self.parent.get_scale()
        dps = Vector(self.scale)
        ps0 = Vector(self.scale0)
        return ps0, dps
    
    def get_headMatrix(self):
        if self.is_structure and self.parent:
            return self.parent.get_headMatrix()
        M = self.headMatrix()
        return M
    
    def headMatrix(self):
    
        o = Vector(self.offset)
        h = Vector(self.relhead)
        
        if hasattr(self, 'parent') and self.parent:
            M  = self.parent.get_headMatrix()
            ps0, dps = self.parent.get_scale()
            matrixScale(ps0+dps, M, replace=True)
            matrixLocation(h+o,M)
            
        else:

            M = Matrix()
        
        return M

    def get_parent(self):
        if self.parent:
            if self.parent.is_structure:
                return self.parent.get_parent()
            else:
                return self.parent
        else:
            return None
        
    def head(self, bind=True):
        '''
        Return the location of the bone head relative to Origin head
        '''
        



        
        o = Vector(self.offset)
        h = Vector(self.relhead)
        oh = o+h
        parent = self.get_parent()
        if parent:
            ph = parent.head(bind)
            if bind:
                ps0, dps = parent.get_scale()
                ps = ps0+dps
            else:
                ps = V(1,1,1)

            psoh = Vector([ps[i]*oh[i] for i in range(3)])
            ah = ph + psoh
            
        else:

            ah = V0.copy()
        
        return ah

    def tail(self):
        '''
        Return the location of the bone tail relative to topmost bone head
        '''

        ah = self.head()
        t = self.reltail if self.reltail is not None else V(0.0,0.1,0.0)        
        s = Vector([1 + self.scale[i] / self.scale0[i] for i in range(3)])
        
        at = ah+Vector([s[i]*t[i] for i in range(3)])
        return at
    
    def pprint(self):
        print("bone       ", self.blname)
        print("bone bvh   ", self.bvhname)
        print("children   ", self.children)
        print("parent     ", self.parent.blname if self.parent else None)
        print("scale      ", self.scale)
        print("offset     ", self.offset)
        print("slname     ", self.slname)
        print("relhead    ", self.relhead)
        print("reltail    ", self.reltail)
        print("bonelayers ", self.bonelayers)
        print("shape      ", self.shape)
        print("shape_scale", self.shape_scale)
        print("roll       ", self.roll)
        print("connected  ", self.connected)
        print("group      ", self.group)
        print("scale0     ", self.scale0)
        print("rot0       ", self.rot0)
        print("stiffness  ", self.stiffness)
        print("limit_rx   ", self.limit_rx)
        print("limit_ry   ", self.limit_ry)
        print("limit_rz   ", self.limit_rz)
        print("deform     ", self.deform)
        print("skeleton   ", self.skeleton)
        print("bonegroup  ", self.bonegroup)
        print("mandatory  ", self.mandatory)
        print("leaf       ", self.leaf)
        print("end0       ", self.end0)

    def diff(self, obone):
        if obone.blname     != self.blname     : print("%15s.blname: %s    | %s" % (self.blname, self.blname, obone.blname))
        if obone.bvhname    != self.bvhname    : print("%15s.bvhname:%s    | %s" % (self.blname, self.bvhname, obone.bvhname))
        if obone.scale      != self.scale      : print("%15s.scale:%s      | %s" % (self.blname, self.scale, obone.scale))
        if obone.offset     != self.offset     : print("%15s.offset:%s     | %s" % (self.blname, self.offset, obone.offset))
        if obone.slname     != self.slname     : print("%15s.slname:%s     | %s" % (self.blname, self.slname, obone.slname))
        if obone.relhead    != self.relhead    : print("%15s.relhead:%s    | %s" % (self.blname, self.relhead, obone.relhead))
        if obone.reltail    != self.reltail    : print("%15s.reltail:%s    | %s" % (self.blname, self.reltail, obone.reltail))
        if obone.bonelayers != self.bonelayers : print("%15s.layers:%s     | %s" % (self.blname, self.bonelayers, obone.bonelayers))
        if obone.shape      != self.shape      : print("%15s.shape:%s      | %s" % (self.blname, self.shape, obone.shape))
        if obone.shape_scale!= self.shape_scale: print("%15s.shape_scale:%s| %s" % (self.blname, self.shape_scale, obone.shape_scale))
        if obone.roll       != self.roll       : print("%15s.roll:%s       | %s" % (self.blname, self.roll, obone.roll))
        if obone.connected  != self.connected  : print("%15s.connected:%s  | %s" % (self.blname, self.connected, obone.connected))
        if obone.group      != self.group      : print("%15s.group:%s      | %s" % (self.blname, self.group, obone.group))
        if obone.scale0     != self.scale0     : print("%15s.scale0:%s     | %s" % (self.blname, self.scale0, obone.scale0))
        if obone.rot0       != self.rot0       : print("%15s.rot0:%s       | %s" % (self.blname, self.rot0, obone.rot0))
        if obone.stiffness  != self.stiffness  : print("%15s.stiffness:%s  | %s" % (self.blname, self.stiffness, obone.stiffness))
        if obone.limit_rx   != self.limit_rx   : print("%15s.limit_rx:%s   | %s" % (self.blname, self.limit_rx, obone.limit_rx))
        if obone.limit_ry   != self.limit_ry   : print("%15s.limit_ry:%s   | %s" % (self.blname, self.limit_ry, obone.limit_ry))
        if obone.limit_rz   != self.limit_rz   : print("%15s.limit_rz:%s   | %s" % (self.blname, self.limit_rz, obone.limit_rz))
        if obone.deform     != self.deform     : print("%15s.deform:%s     | %s" % (self.blname, self.deform, obone.deform))
        if obone.skeleton   != self.skeleton   : print("%15s.skeleton:%s   | %s" % (self.blname, self.skeleton, obone.skeleton))
        if obone.bonegroup  != self.bonegroup  : print("%15s.bonegroup:%s  | %s" % (self.blname, self.bonegroup, obone.bonegroup))
        if obone.mandatory  != self.mandatory  : print("%15s.mandatory:%s  | %s" % (self.blname, self.mandatory, obone.mandatory))
        if obone.leaf       != self.leaf       : print("%15s.leaf     :%s  | %s" % (self.blname, self.leaf     , obone.leaf     ))
        if obone.end0       != self.end0       : print("%15s.end0     :%s  | %s" % (self.blname, self.end0     , obone.end0     ))


        op = obone.parent.blname if obone.parent else None
        sp = self.parent.blname  if self.parent else None
        parent_mismatch = op != sp and ( op == None or sp == None)
        if parent_mismatch : print("%15s.parent:%s    | %s" % (self.blname, op, sp))


        selfnames  = [child.blname for child in self.children]
        othernames = [child.blname for child in obone.children]
        for selfname in [ name for name in selfnames if name not in othernames]:
            print("%15s.child:%s missing in obone" % (self.blname, selfname))
        for oname in [ name for name in othernames if name not in selfnames]:
            print("%15s.child:%s missing in self" % (self.blname, oname))


class Skeleton:

    def __init__(self, rig_type, joint_type):

        self.rig_type = rig_type
        self.joint_type = joint_type

        self.bones = {}
        self.slbones = {}
        self.bvhbones = {}

    def __getitem__(self, key):
        return self.bones[key] if key in self.bones else None

    def __setitem__(self, key, value):
        self.bones[key] = value

    def __iter__(self):
        return self.bones.__iter__()

    def add_bone(self, B):
        self.bones[B.blname] = B
        if B.slname is not None:
            self.slbones[B.slname] = B
        if B.bvhname is not None:
            self.bvhbones[B.bvhname] = B
    
    def add_boneset(self, boneset):
        for bone in boneset.values():
            self.add_bone(bone)

    def add(self, blname,  *args,  **nargs):
        '''
        Convenience method to add a Bone() and link them together
        '''

        B = Bone(blname,  *args,  **nargs)
        self.add_bone(B)
        return B

    def addv(self, blname, relhead, reltail, parent, rot0=V0.copy(), scale0=V1.copy()):
        '''
        Convenience method to add a volume Bone() and link them together
        '''

        rot0 = [radians(r) for r in s2b(rot0)]
        scale0 = s2bo(scale0)

        reltail = Vector(( reltail[0]/scale0[0], reltail[1]/scale0[1], reltail[2]/scale0[2] ))


        B = Bone(blname,  slname=blname, relhead=relhead, reltail=reltail, parent=parent,
                 layers=[B_LAYER_VOLUME], group='Collision', rot0=rot0, scale0=scale0, shape="CustomShape_Volume",
                 skeleton='basic', bonegroup='Volume', mandatory='false')
        self.add_bone(B)
        return B

    @staticmethod
    def get_toe_hover_z(armobj, reset=False, bind=True):
        hover = Skeleton.get_toe_hover(armobj, reset, bind)
        hover[0]=hover[1]=0
        return hover

    @staticmethod
    def get_toe_hover(armobj, reset=False, bind=True):
        if reset or not 'toe_hover' in armobj:
            bones    = util.get_modify_bones(armobj)
            b_toe    = bones.get('mToeRight',  None)
            l_toe    = Skeleton.head(context=None, dbone=b_toe,    bones=bones, bind=bind) if b_toe else V0
            b_origin = bones.get('Origin',  None)
            l_origin = Skeleton.head(context=None, dbone=b_origin,    bones=bones, bind=bind) if b_origin else V0
            hover    = Vector(l_toe-l_origin)
            armobj['toe_hover'] = hover
        else:
            hover = armobj['toe_hover']


        return hover

    @staticmethod
    def get_parent(bone):
        if bone.parent:
            parent = bone.parent
            if parent.get('is_structure', False):# or parent.name in ['Tinker', 'COG']:
                return Skeleton.get_parent(parent)
            else:
                return parent
        else:
            return None
 
    @staticmethod
    def get_bone_info(context, dbone, bones):
        if dbone == None or bones == None:
            if context == None:
                context=bpy.context
            if dbone == None:
                dbone = context.active_bone
            if bones == None:
                armobj = context.object
                bones   = util.get_modify_bones(armobj)
        return dbone, bones

    @staticmethod
    #

    #
    def has_connected_children(dbone):
        for child in dbone.children:
           if child.use_connect:
               return True
        return False
        
    @staticmethod
    def get_restposition(context, dbone, bind=True, with_joint=True, use_bind_pose=False):
        M = Matrix(([1,0,0],[0,1,0],[0,0,1]))
        j = V0

        if dbone == None:
            return V0.copy()

        parent  = Skeleton.get_parent(dbone)
        if not parent:
            pos = Vector(dbone.head) # This is the location of the root bone (Origin)
        else:

            pos = Skeleton.get_restposition(context, parent, bind, with_joint, use_bind_pose)

            d = V0.copy() if dbone.get('is_structure',False) else Vector(dbone.get(JOINT_BASE_HEAD_ID,(0,0,0)))

            if with_joint:
                from . import rig
                if not context:
                    context = bpy.context
                armobj = util.get_armature(context.object)
                joints = util.get_joint_cache(armobj)

                if joints:
                    jh,jt = util.get_joint_position(joints, dbone)
                    has_offset = jh.magnitude
                else:
                    has_offset = False

                if has_offset:
                    if use_bind_pose:
                        try:
                            bindHead, bindTail = rig.get_sl_bindposition(armobj, dbone, use_cache=True)
                            restHead, restTail = rig.get_custom_restposition(armobj, dbone, use_cache=True, with_joint_offset=True)
                            if bindTail and restTail:

                                M = bindTail.rotation_difference(restTail).to_matrix()
                        except:
                            log.warning("Could not calculate rotation difference from bone %s:%s" % (armobj.name, dbone.name) )
                    d += jh
                else:
                    if bind:
                        d += Vector(dbone.get('offset', (0,0,0)))
            else:
                if bind:
                    d += Vector(dbone.get('offset', (0,0,0)))
            if bind:
                s = util.get_bone_scale(parent) if parent else V1.copy()
                dd = mulmat(d, M)
                dd = Vector([s[i]*d[i] for i in range(3)])
                d = mulmat(M, dd)

            pos += d

        return pos

    @staticmethod


    def headMatrix(context=None, dbone=None, bones=None, bind=True, with_joints=True, use_bind_pose=False):
        dbone, bones = Skeleton.get_bone_info(context, dbone, bones)
        bonename = dbone.name
        M = Matrix()
        parent = Skeleton.get_parent(dbone)
        oh = Skeleton.get_restposition(context, dbone, bind, with_joints, use_bind_pose)
        if parent:

            if bind:
                ps = util.get_bone_scale(dbone)
                matrixScale(ps, M) #We do not care about the scaling of the parent matrix here
            ps0 = Vector(dbone.get('scale0',(1,1,1)))
            matrixScale(ps0,M) # only needed for collision volumes ?
        M = matrixLocation(oh,M)
        return M

    @staticmethod
    def tailMatrix(context=None, dbone=None, bones=None, Mh=None, bind=True, with_joints=True, use_bind_pose=False):
        '''
        Return the location of the bone tail relative to topmost bone head
        with default=True it ignores scaling and offsets
        if bones is set then prefer SL bones (mBones) as reference
        Hint: the control skeleton can have a different hierarchy 
              so the control skeleton can potentially scale different 
              then the SL Skeleton. Caveat: this effectively synchronises
              the control bones to the mBones when the shape sliders are updated!
        '''

        location = None
        dbone, bones = Skeleton.get_bone_info(context, dbone, bones)
        if not Mh:
            Mh = Skeleton.headMatrix(context, dbone, bones, bind, with_joints)
        



        name = dbone.name
        reference_name = name if name[0] in ['m','a'] or name in SLVOLBONES or name in ['Tinker', 'EyeTarget'] or "Link" in name else 'm' + name
        reference_bone = bones.get(reference_name, None)
        if reference_bone:
            for child in reference_bone.children:
                if child.name[0] != 'm':
                    c = bones.get('m'+child.name, None)
                    if c:
                        child = c
                if child.use_connect:
                    location = Skeleton.headMatrix(context, child, bones, bind, with_joints, use_bind_pose).translation.copy()
                    break

        Mt = Mh.copy()
        sp = util.get_bone_scale(dbone)
        if bind and dbone.parent:
            if dbone.name in SLVOLBONES:
                Mt = matrixScale(sp, Mt, replace=True)
                sp = util.get_bone_scale(dbone.parent)
                Mt = matrixScale(sp,Mt)
            else:
                Mt = matrixScale(sp, Mt, replace=True)

        if location == None:
            if with_joints:
                h     = Vector(dbone.get('btail', dbone.get(JOINT_BASE_TAIL_ID,(0,0,0))))
            else:
                h     = Vector(dbone.get(JOINT_BASE_TAIL_ID,(0,0,0)))
            oh = h
            location  = Vector([oh[i]*sp[i] for i in range(3)]) + Mh.translation

        Mt = matrixLocation(location, Mt, replace=True)
        return Mt

    @staticmethod
    def head(context=None, dbone=None, bones=None, bind=True, with_joints=True, use_bind_pose=False):
        '''
        Return the location of the bone head relative to Origin head
        with scale=False it ignores scaling and offsets  
        if bones is set then prefer SL bones (mBones) as reference
        Hint: the control skeleton can have a different hierarchy 
              so the control skeleton can potentially sclae different 
              then the SL Skeleton. Caveat: this effectively synchronises
              the control bones to the mBones when the shape sliders are updated!
        '''
        M = Skeleton.headMatrix(context, dbone, bones, bind, with_joints, use_bind_pose)
        loc = M.translation
        return loc

    @staticmethod
    def bones_in_hierarchical_order(arm, roots=None, bone_names=None, order='TOPDOWN'):
        if not bone_names:
            bone_names = []

        if not roots:
            roots = [b for b in arm.data.bones if b.parent == None]

        for root in roots:
            bone_names.append(root.name)
            if root.children:
                Skeleton.bones_in_hierarchical_order(arm, root.children, bone_names)

        if order == 'BOTTOMUP':
            bone_names.reverse()
        return bone_names
    
    @staticmethod
    def get_bone_end(dbone, scale=True):
        be  = Vector(dbone.get(JOINT_BASE_TAIL_ID, (0,0.1,0)))
        
        if scaled:
            s  = Vector(dbone.get('scale0', (1,1,1)))
            s += Vector(dbone.get('scale',  (0,0,0)))
            be = Vector([s[0]*be[0], s[1]*be[1], s[2]*be[2]])
        return be

    @staticmethod
    def tail(context=None, dbone=None, bones=None, bind=True, with_joints=True, use_bind_pose=False):
        '''
        Return the location of the bone tail relative to topmost bone head
        with scale=False it ignores scaling and offsets  
        if bones is set then prefer SL bones (mBones) as reference
        Hint: the control skeleton can have a different hierarchy 
              so the control skeleton can potentially sclae different 
              then the SL Skeleton. Caveat: this effectively synchronises
              the control bones to the mBones when the shape sliders are updated!
        '''

        Mh = Skeleton.headMatrix(context, dbone, bones, bind, with_joints, use_bind_pose)
        Mt = Skeleton.tailMatrix(context, dbone, bones, Mh, bind, with_joints, use_bind_pose)

        loc = Mt.translation
        return loc



def preset_bone_limitations(boneset):
    #

    #



    
    for bone, val in DEFAULT_BONE_LIMITS.items():
        if bone in boneset:
            stiffness, limit_rx, limit_ry, limit_rz, roll = val
            if roll:
                roll = radians(roll)
            boneset[bone].set( stiffness = stiffness, limit_rx = limit_rx, limit_ry = limit_ry, limit_rz = limit_rz, roll = roll)




def set_bone_layer(boneset, category, bcategory=None):
    if bcategory==None: bcategory = category
    layers = LAYER_MAP[category]
    for key in util.bone_category_keys(boneset, bcategory):
        boneset[key].layers = [layers[0]]


    if len(layers) == 2:
        for key in util.bone_category_keys(boneset, "m"+bcategory):
            boneset[key].layers = [layers[1]]


def get_leaf_bones(boneset):
    return [boneset[b.blname[1:]] for b in boneset.values() if b.blname[0]=='m' and b.leaf]

def get_ik_roots(boneset, rigType):

    return [b for b in boneset.values() if b.is_ik_root and (rigType=='EXTENDED' or b.skeleton=='basic')]

def connect_bone_chains(boneset):
    for cb in get_leaf_bones(boneset):
        entry     = cb
        chain_len = 1
        if not entry.blname.startswith('Wing4Fan'):
            while entry.parent and entry.parent.reltail == entry.relhead:
                entry.connected = entry.blname not in ['Skull', 'FaceEar1Right', 'FaceEar1Left', 'Torso', 'Pelvis']

                entry = entry.parent
                chain_len +=1

        if chain_len > 0:

            entry.is_ik_root = True
            entry.ik_len     = chain_len
            entry.ik_end     = cb
            cb.ik_root       = entry

def set_bento_bone_layers(boneset):
    for n in sym(['Eye.',
                  'FaceEyeAlt.'
                 ]):
        if n in boneset:

            boneset[n].layers=[B_LAYER_EXTRA]

    for n in sym(['FaceEyeAltTarget']):
        if n in boneset: boneset[n].layers=[B_LAYER_EYE_ALT_TARGET]
    try:
        for n in sym(["ikFaceLipCorner.","ikFaceEyebrowCenter.", "ikFaceLipShape", "ikFaceLipShapeMaster"]):
            boneset[n].layers=[B_LAYER_IK_FACE]
    except:
        pass

def set_bone_layers(boneset):
    boneset['COG'].layers=[B_LAYER_TORSO]


    for n in sym(['Ankle.', 'Knee.', 'Hip.']):
        boneset[n].layers=[B_LAYER_LEGS]
        

    for n in sym(['Collar.', 'Shoulder.', 'Elbow.', 'Wrist.']):
        boneset[n].layers=[B_LAYER_ARMS]
        

    for n in ['Tinker', 'Torso', 'Chest']:
        boneset[n].layers=[B_LAYER_TORSO]


    for n in ['Neck', 'Head']:
        boneset[n].layers=[B_LAYER_TORSO]


    for n in sym_expand(boneset.keys(), ['*Link.', 'Pelvis']):
        boneset[n].layers=[B_LAYER_STRUCTURE]
    

    for n in sym(['Toe.', 'Foot.', 'Skull','Eye.',
                 ]):
        if n in boneset: boneset[n].layers=[B_LAYER_EXTRA]
        
    for n in sym(['EyeTarget']):
        if n in boneset: boneset[n].layers=[B_LAYER_EYE_TARGET]

    for n in sym(['CollarLink.', 'Pelvis']):
        boneset[n].layers=[B_LAYER_STRUCTURE]



def create_face_rig(boneset):

    from .util import V
    for symmetry in ["Left", "Right"]:
        for handle in ["FaceLipCorner","FaceEyebrowCenter"]:
            try:
                parentBoneName = "%s%s" % (handle,symmetry)
                parentBone = boneset.get(parentBoneName)
                headBone   = boneset.get('Head')
                if parentBone and headBone:
                    relhead    = parentBone.tail() - headBone.head()
                    reltail    = parentBone.reltail
                    ikHandleName = "ik%s" % parentBoneName
                    shape_scale = 2 if handle == "FaceEyebrowCenter" in handle else 1

                    ikHandle = Bone(ikHandleName,
                           parent     = headBone,
                           relhead    = relhead ,
                           reltail    = 0.25*reltail,
                           connected  = False,
                           bonelayers = [B_LAYER_IK_FACE],
                           bonegroup  = 'IK Face',
                           shape      = 'CustomShape_Pinch',
                           shape_scale= shape_scale,
                           wire       = False
                         )
                    boneset[ikHandleName] = ikHandle
            except Exception as e:
                util.ErrorDialog.exception(e)
                continue
    try:
        faceRoot     = boneset.get('FaceLowerRoot', boneset.get('FaceRoot', boneset.get('Head')))

        lipLeft      = boneset['FaceLipCornerLeft']
        lipRight     = boneset['FaceLipCornerRight']
        upperCenter  = boneset.get('FaceLipUpperCenter', None)
        lowerCenter  = boneset.get('FaceLipLowerCenter', None)
        teethUpper   = boneset.get('FaceTeethUpper', None)

        if lowerCenter and upperCenter and teethUpper:
            relhead = (0, (lowerCenter.relhead[1] + upperCenter.relhead[1]), -0.015)
            parent  = teethUpper
        else:
            parent = faceRoot
            relhead = lowerCenter.relhead + lipLeft.reltail
            relhead = (0, relhead[1] - 0.01, -0.015)
            reltail = lipLeft.reltail

        reltail = (0, -0.02, 0)



        lipShapeBone = Bone('ikFaceLipShape',
                            parent      = parent,
                            relhead     = relhead,
                            reltail     = reltail,
                            shape       = 'CustomShape_Lip',
                            shape_scale = 0.8,
                            connected   = False,
                            bonegroup   = 'IK Face',
                            bonelayers  = [B_LAYER_IK_FACE]
                            )
        boneset['ikFaceLipShape'] = lipShapeBone


        lipShapeMaster = Bone('ikFaceLipShapeMaster',
                            parent     = parent,
                            relhead    = relhead,
                            reltail    = (0.02,0,0),
                            shape      = 'CustomShape_Cube',
                            connected  = False,
                            shape_scale = 1.5,
                            bonegroup  = 'IK Face',
                            bonelayers = [B_LAYER_IK_FACE]
                            )
        boneset['ikFaceLipShapeMaster'] = lipShapeMaster


    except:
        pass


def create_hand_rig(boneset):
    from .util import V
    for symmetry in ["Left", "Right"]:
        for finger in ["Thumb","Index","Middle","Ring","Pinky"]:
            try:
                wrist        = boneset["Wrist%s" % symmetry]
                fingerEnd    = boneset["Hand%s3%s" % (finger, symmetry)]
                ikSolverName = "ik%sSolver%s" % (finger, symmetry)
                ikTargetName = "ik%sTarget%s" % (finger, symmetry)
            except:
                continue
            ikSolver = Bone(ikSolverName,
                       parent     = fingerEnd,
                       reltail    = fingerEnd.reltail + Vector((0,0,0.01)),
                       connected  = True,
                       bonelayers = [B_LAYER_IK_HIDDEN],
                       group      = 'IK'
                     )

            ikTarget = Bone(ikTargetName,
                       parent     = wrist,
                       relhead    = fingerEnd.tail() - wrist.head(),# + V(0,-.01,0),
                       reltail    = fingerEnd.reltail,
                       bonelayers = [B_LAYER_IK_HAND],
                       shape      = "CustomShape_Pinch",
                       group      = 'IK'
                     )

            if finger == 'Index':
                ikPinchName = "ik%sPinch%s" % (finger, symmetry)
                fingerMiddle  = boneset["Hand%s2%s" % (finger, symmetry)]
                thumbMiddle   = boneset["HandThumb2%s" % (symmetry)]
                ikPinch = Bone(ikPinchName,
                           parent     = wrist,
                           relhead    = 0.5*(thumbMiddle.head() + fingerMiddle.head()) - wrist.head() + Vector((0,0,-0.05)),
                           reltail    = fingerMiddle.reltail,
                           bonelayers = [B_LAYER_IK_HAND],
                           shape      = "CustomShape_Pinch",
                           group      = 'IK'
                         )
                boneset[ikPinchName] = ikPinch

            boneset[ikSolverName] = ikSolver
            boneset[ikTargetName] = ikTarget


def create_ik_bones(boneset):

    LH = Vector((0.08279900252819061, -0.005131999962031841, -0.005483999848365784))
    RH = Vector((-0.08279900252819061, -0.005131999962031841, -0.005483999848365784))

    LB = Vector((0.08279900252819061, 0.1735360026359558, -0.0031580000650137663))
    RB = Vector((-0.08279900252819061, 0.1735360026359558, -0.0031580000650137663))

    create_ik_arm_bones(boneset)
    create_ik_leg_bones(boneset, 'Left', LH, LB)
    create_ik_leg_bones(boneset, 'Right', RH, RB)

    mHindLimb3Left = boneset.get("mHindLimb3Left")
    if mHindLimb3Left:

        mHindLimb3Left = Vector(boneset["mHindLimb3Left"].head())
        mHindLimb3Left[2]=LH[2]
        mHindLimb3Right = mHindLimb3Left.copy()

        LH = LB.copy()
        RH = RB.copy()
        mHindLimb3Right[0] *= -1
        LH[1] = mHindLimb3Left[1] - LB[1]
        RH[1] = mHindLimb3Left[1] - RB[1]

        create_ik_limb_bones(boneset, 'Left', mHindLimb3Left, LH)
        create_ik_limb_bones(boneset, 'Right', mHindLimb3Right, RH)


def create_ik_arm_bones(boneset):

    Origin = boneset['Origin']
    bonegroup  = "IK Arms"
    bonelayers = BONEGROUP_MAP[bonegroup][1]
    ikLine = Vector((0,0.5,0))

    def create_side(boneset, side):
        mElbow  = boneset["mElbow%s"%side]
        mWrist  = boneset["mWrist%s"%side]

        ikWrist = Bone("ikWrist%s"%side, relhead=mWrist.head(), reltail=mWrist.reltail, parent=Origin, bonelayers=bonelayers, group="IK", shape="CustomShape_Hand", bonegroup=bonegroup)

        line_location = mElbow.head() - ikWrist.head()
        target_location = line_location + ikLine

        ikElbowTarget = Bone("ikElbowTarget%s"%side, 
                            relhead=target_location,
                            reltail=s2b(V((0, 0, 0.1))),
                            parent=ikWrist,
                            bonelayers=bonelayers,
                            group="IK",
                            shape="CustomShape_Target",
                            bonegroup=bonegroup)

        ikElbowLine = Bone("ikElbowLine%s"%side,
                            relhead=line_location,
                            reltail=ikLine,
                            parent=ikWrist,
                            bonelayers=bonelayers,
                            group="IK",
                            shape="CustomShape_Line",
                            bonegroup=bonegroup)

        return [ikWrist, ikElbowTarget, ikElbowLine]

    LBS = create_side(boneset, 'Left')
    RBS = create_side(boneset, 'Right')

    for bone in LBS + RBS:
        boneset[bone.blname]=bone

def create_ik_leg_bones(boneset, side, Heel, Ball):

    Origin = boneset['Origin']
    bonegroup  = "IK Legs"
    bonelayers = BONEGROUP_MAP[bonegroup][1]
    ikLine = Vector((0,-0.25,0))

    ankle  = boneset.get('mAnkle%s'%side)
    toe    = boneset.get('mToe%s'%side)
    if ankle and toe:
        ankle_loc  = ankle.head()
        toe_loc    = toe.head()
        heel_relhead   = ankle_loc
        heel_relhead.z = 0
        ball_relhead   = toe_loc - heel_relhead
    else:
        ball_relhead = Heel-Ball
        heel_relhead = Heel

    
    ikHeel     = Bone("ikHeel"+side,      relhead=heel_relhead, reltail=s2b(V((0, 0, -0.1))),  parent=Origin,      group="IK", bonelayers=bonelayers, shape="CustomShape_Foot",      bonegroup=bonegroup)
    ikFootPivot= Bone("ikFootPivot"+side, relhead=V0,           reltail=ikHeel.reltail,  parent=ikHeel,  group="IK", bonelayers=bonelayers, shape="CustomShape_FootPivot", bonegroup=bonegroup)
    ikFootBall = Bone("ikFootBall"+side, relhead=ball_relhead,  reltail=s2b(V((0, 0, -0.02))), parent=ikHeel, bonelayers=bonelayers, group="IK", shape='CustomShape_Target', bonegroup=bonegroup)

    bonelayers = BONEGROUP_MAP[bonegroup][1]

    line_location = boneset["mKnee"+side].head() - ikHeel.head()
    target_location = line_location + ikLine
    ikKneeTarget = Bone("ikKneeTarget"+side, relhead=target_location, reltail=s2b(V((0, 0, 0.1))),parent=ikHeel, bonelayers=bonelayers, group="IK", shape="CustomShape_Target", bonegroup=bonegroup)
    ikKneeLine = Bone("ikKneeLine"+side, relhead=line_location, reltail=ikLine, parent=ikHeel, bonelayers=bonelayers, group="IK", shape="CustomShape_Line", bonegroup=bonegroup)


    bonegroup  = "Structure"
    bonelayers = BONEGROUP_MAP[bonegroup][1]

    mAnkle = boneset["mAnkle"+side]
    ankle_location = mAnkle.head() - ikFootPivot.head()
    
    bonegroup  = "IK Legs"
    bonelayers = BONEGROUP_MAP[bonegroup][1]
    
    ikAnkle = Bone("ikAnkle"+side, relhead=ankle_location, reltail=mAnkle.reltail, parent=ikFootPivot, bonelayers=bonelayers, group="IK", bonegroup=bonegroup)

    IK_BONES = [ikHeel, ikFootPivot,
                ikFootBall, ikKneeTarget,
                ikKneeLine, ikAnkle]

    for bone in IK_BONES:
        boneset[bone.blname]=bone

def create_ik_limb_bones(boneset, side, Heel, Ball):

    Origin = boneset['Origin']
    bonegroup  = "IK Limbs"
    bonelayers = BONEGROUP_MAP[bonegroup][1]
    ikLine = Vector((0,-0.25,0))

    ankle  = boneset.get('mHindLimb3%s'%side)
    toe    = boneset.get('mHindLimb4%s'%side)
    if ankle and toe:
        ankle_loc  = ankle.head()
        toe_loc    = toe.tail()
        heel_relhead   = ankle_loc
        heel_relhead.z = 0
        ball_relhead   = toe_loc#heel_relhead - toe_loc
    else:
        ball_relhead = Heel-Ball
        heel_relhead = Heel
    
    ikLimbHeel     = Bone("ikHindHeel"+side,      relhead=heel_relhead, reltail=s2b(V((0, 0, -0.1))),  parent=Origin,      group="IK", bonelayers=bonelayers, shape="CustomShape_Foot",      bonegroup=bonegroup)
    ikLimbFootPivot= Bone("ikHindFootPivot"+side, relhead=V0,           reltail=ikLimbHeel.reltail,  parent=ikLimbHeel,  group="IK", bonelayers=bonelayers, shape="CustomShape_FootPivot", bonegroup=bonegroup)
    ikLimbFootBall = Bone("ikHindFootBall"+side,  relhead=ball_relhead, reltail=s2b(V((0, 0, -0.02))), parent=ikLimbHeel, bonelayers=bonelayers, group="IK", shape="CustomShape_Target", bonegroup=bonegroup)


    line_location = boneset["mHindLimb2"+side].head() - ikLimbHeel.head()
    target_location = line_location + ikLine
    ikLimbKneeTarget = Bone("ikHindLimb2Target"+side, relhead=target_location, reltail=s2b(V((0, 0, 0.1))),parent=ikLimbHeel, bonelayers=bonelayers, group="IK", shape="CustomShape_Target", bonegroup=bonegroup)
    ikLimbKneeLine = Bone("ikHindLimb2Line"+side, relhead=line_location, reltail=ikLine, parent=ikLimbHeel, bonelayers=bonelayers, group="IK", shape="CustomShape_Line", bonegroup=bonegroup)


    mHindLimb3 = boneset["mHindLimb3"+side]
    loc = mHindLimb3.head() - ikLimbFootPivot.head()
    ikLimbAnkle = Bone("ikHindLimb3"+side, relhead=loc, reltail=mHindLimb3.reltail, parent=ikLimbFootPivot, bonelayers=bonelayers, group="IK", bonegroup=bonegroup)

    IK_BONES = [ikLimbHeel, ikLimbFootPivot,
                ikLimbFootBall, ikLimbKneeTarget,
                ikLimbKneeLine, ikLimbAnkle]

    for bone in IK_BONES:
        boneset[bone.blname]=bone


def load_attachment_points(boneset, rigtype):
    from .util import V
    '''
    Load attachment points from avatar_lad.xml
    '''



    ATTACH = {}
    ladfile = util.get_lad_file()
    ladxml = et.parse(ladfile)

    skel = ladxml.find('skeleton')
    attachments = skel.findall('attachment_point')

    up = Vector((0,0,0.03))
    reltail=s2b(up)
    bonegroup="Attachment"
    bonelayers=BONEGROUP_MAP[bonegroup][1]
    shape="CustomShape_Target"
    deform=False
    

    for attach in attachments:

        joint = attach.get('joint')
        if joint in boneset or joint=="mRoot":
            name = attach.get('name')

            pos = util.vector_from_string(attach.get('position'))
            rot = util.vector_from_string(attach.get('rotation'))
            for ii in range(len(rot)):
                rot[ii] = radians(float(rot[ii]))

            if joint=="mRoot":
                mPelvis = boneset["mPelvis"]
                root = mPelvis.head()
                relhead=s2b(pos+root)
                parent=boneset["Origin"]
                rot0=V0.copy()

            else:
                relhead=s2b(V(pos))
                parent=boneset[joint]
                rot0=s2bo(V(rot))            

            abone_name = "a"+name

            bone = Bone(abone_name,
                         relhead=relhead,
                         reltail=reltail,
                         parent=parent, 
                         group=bonegroup,
                         bonelayers=bonelayers,
                         shape=shape, 
                         deform=deform,
                         rot0=rot0,
                         pos0=V(pos),
                         pivot0=relhead,
                         skeleton='basic', 
                         bonegroup=bonegroup, 
                         mandatory='false')
            boneset[abone_name] = bone


def get_bone_attributes(bone_xml):
    type   = bone_xml.tag
    attrib = bone_xml.attrib

    if type=='bone':
        blname = attrib['name']
        if blname in sym(['mAnkle.', 'mKnee.', 'mHip.']):
            attrib['skeleton']  = 'basic'
            attrib['bonegroup']  = 'mLegs'
            attrib['mandatory'] = 'true'
        elif blname in sym(['mCollar.', 'mShoulder.', 'mElbow.', 'mWrist.']):
            attrib['skeleton']  = 'basic'
            attrib['bonegroup']  = 'mArms'
            attrib['mandatory'] = 'true'
        elif blname in ['mPelvis', 'mTorso', 'mChest', 'mNeck', 'mHead']:
            attrib['skeleton']  = 'basic'
            attrib['bonegroup']  = 'mTorso'
            attrib['mandatory'] = 'true'
        elif blname in sym(['mToe.', 'mFoot.', 'mSkull', 'mEye.']):
            attrib['skeleton']  = 'basic'
            attrib['bonegroup'] = 'mExtra'
            attrib['mandatory'] = 'false'
        else:
            attrib['skeleton']  = 'extended'
            attrib['mandatory'] = 'false'
            
            if blname.startswith('mSpine'):
                attrib['bonegroup'] = 'Spine'
            else:        
                attrib['bonegroup'] = attrib.get('group', 'Custom')

    else:
        attrib['skeleton']  = 'basic'
        attrib['bonegroup']  = 'Collision'
        attrib['mandatory'] = 'false'

    return attrib

def has_connected_child(parent_xml):
    sibblings = parent_xml.findall('bone')
    for bone_xml in sibblings:
        attrib = get_bone_attributes(bone_xml)
        blname     = attrib['name']
        if 'connected' in attrib:
            connected = attrib['connected']
            if  connected =='true':
                return True



    attrib     = get_bone_attributes(parent_xml)
    blname     = attrib['name']

    return False

def load_bone_hierarchy(parent_xml, parent_bone, boneset, rigType, jointtype):
    from .util import V

    if boneset == None:
        boneset = {}

    sibblings = parent_xml.findall('*')

    for bone_xml in sibblings:
        bone_type  = bone_xml.tag    # can be 'bone' or 'collision_volume'
        attrib     = get_bone_attributes(bone_xml)
        blname     = attrib['name']

        can_add = True
        if bone_type == 'bone' and 'support' in attrib and attrib['support'] == "extended":
            if rigType == 'BASIC':
                log.info("Ignore extended bone %s" % blname)
                can_add = False

        ctrl_name  = blname[1:] if blname.startswith("m") else None

        pos0 = s2b(Vector(float_array_from_string(attrib['pos'])))   if 'pos'   in attrib else None

        scale0  = s2bo(Vector(float_array_from_string(attrib['scale']))) if 'scale' in attrib else None
        pivot0  = s2b(Vector(float_array_from_string(attrib['pivot']))) if 'pivot' in attrib else pos0

        connected = attrib['connected']=='true' if 'connected' in attrib else False


        relhead  = pos0 if blname.startswith('mToe') or jointtype=='POS' else pivot0



        if blname=='mNeck' or (can_add and connected and bone_type=='bone' and parent_bone): #and (parent_bone.reltail == None or blname=='mNeck'):
            parent_bone.reltail = relhead
            parent_bone.end0    = relhead
            parent_bone.leaf    = False

        end0    = s2b(Vector(float_array_from_string(attrib['end'])))  if 'end' in attrib else None #and has_connected_child(bone_xml)==False else None
        reltail = end0






        
        if reltail == None and blname in BONE_TAIL_LOCATIONS:
            print("load_bone_hierarchy: enforce predefined bone tail for ", blname)
            reltail = s2b(Vector((BONE_TAIL_LOCATIONS[blname])))
        
        leaf       = True
        bonegroup  = attrib['bonegroup']
        if 'm' + bonegroup in BONEGROUP_MAP:
            bonegroup  = 'm' + bonegroup
        bonelayers = BONEGROUP_MAP[bonegroup][1]
        
        if bone_type == 'bone':

            if 'support' in attrib and attrib['support'] == "extended":
                group      = 'SL Extended'
            else:
                group      = 'SL Base'

            deform  = True
            bvhname = ANIMBONE_MAP[ctrl_name] if ctrl_name in ANIMBONE_MAP else None
            shape   = get_shape_for_bone(blname)
            rot0    = s2bo(Vector(float_array_from_string(attrib['rot'])))  if 'rot' in attrib else None
        else:
            bonelayers  = [B_LAYER_VOLUME]
            deform      = True
            group       = "Collision"
            bvhname     = None
            shape       = "CustomShape_Volume"
            raw_rot     = s2b(Vector(float_array_from_string(attrib['rot']))) if 'rot' in attrib else V0.copy()
            rot0        = [radians(r) for r in raw_rot]
            
            if reltail:
                eul  = Euler( rot0, 'XYZ')
                reltail = Vector(reltail)
                reltail.rotate(eul)
            else:
                print("load bone hierarchy: found bone %s without defined reltail" % (blname) )

        if can_add:
            log.debug("load_bone_hierarchy add bone %s", blname)
            childbone = Bone(blname, 
                        bvhname    = bvhname, 
                        slname     = blname, 
                        relhead    = relhead,
                        reltail    = reltail,
                        end0       = end0,                        
                        parent     = parent_bone,
                        bonelayers = bonelayers, 
                        shape      = shape, 
                        roll       = 0, 
                        connected  = connected, 
                        group      = group, 
                        stiffness  = [0.0,0.0,0.0], 
                        limit_rx   = None, 
                        limit_ry   = None, 
                        limit_rz   = None, 
                        deform     = deform, 
                        scale0     = scale0, 
                        rot0       = rot0,
                        pos0       = pos0,
                        pivot0     = pivot0,
                        skeleton   = attrib['skeleton'],
                        bonegroup  = bonegroup,
                        mandatory  = attrib['mandatory'],
                        leaf       = leaf,
                        attrib     = attrib
                        )

            refbone = childbone
            boneset[blname] = refbone
        else:
            refbone = parent_bone

        load_bone_hierarchy(bone_xml, refbone, boneset, rigType, jointtype)

    return boneset

bonesets = {}

def get_reference_boneset(arm, rigtype=None, jointtype=None):
    effectiveRigType   = arm.RigProp.RigType if rigtype == None else rigtype
    effectiveJointType = arm.RigProp.JointType if jointtype == None else jointtype
    filepath = util.get_skeleton_file()

    boneset = load_skeleton_data(filepath, effectiveRigType, effectiveJointType, use_cache=True)
    return boneset

def get_rigtype_boneset(rigType, jointtype, filepath):
    boneset = load_skeleton_data(filepath, rigType, jointtype)
    return boneset

def get_boneset(rigType, jointtype):
    global bonesets
    key = "%s_%s" % (rigType,jointtype)
    boneset = bonesets.get(key)
    return boneset
    
def add_boneset(rigType, jointtype, boneset):
    global bonesets
    key = "%s_%s" % (rigType,jointtype)
    bonesets[key] = boneset


def load_skeleton_data(filepath, rigType, jointtype, use_cache=None):

    if use_cache==None:
        pref = util.getAddonPreferences()
        use_cache = pref.rig_cache_data

    if use_cache:
        boneset = load_cached_skeleton_data(filepath, rigType, jointtype)
    else:
        boneset = load_skeleton_data_from_file(filepath, rigType, jointtype)
    return boneset


def load_cached_skeleton_data(filepath, rigType, jointtype):
    from .util import V
    global bonesets
    boneset = get_boneset(rigType, jointtype)
    if not boneset:
        boneset = load_skeleton_data_from_file(filepath, rigType, jointtype)
        add_boneset(rigType, jointtype, boneset)
    return boneset


def load_skeleton_data_from_file(filepath, rigType, jointtype):
    skeletontree = et.parse(filepath)
    root = skeletontree.getroot()

    blname = "Origin"
    origin = Bone(blname,
                    bvhname     = None,
                    slname      = blname,
                    reltail     = s2b(V(BONE_TAIL_LOCATIONS[blname])),
                    bonelayers  = [B_LAYER_ORIGIN],
                    shape="CustomShape_Origin",
                    skeleton='basic', bonegroup='Origin', mandatory='false')

    boneset = {"Origin": origin}
    load_bone_hierarchy(root, origin, boneset, rigType, jointtype)
    

    boneset["mHipRight"].roll     = radians(-7.5)
    boneset["mHipLeft"].roll      = radians( 7.5)

    
    if rigType != 'REFERENCE':
        create_ik_bones(boneset)
        load_control_bones(boneset, rigType)
        create_hand_rig(boneset)
        create_face_rig(boneset)
        add_eye_targets(boneset, rigType)
        
    load_attachment_points(boneset, rigType)
    








    print("Loaded %s.%s Skeleton" % (rigType,jointtype))


    for bone in boneset.values():
        bone.b0head = bone.head(bind=True)
        bone.b0tail = bone.tail()

    add_boneset(rigType, jointtype, boneset)

    return boneset

def add_eye_targets(boneset, rigType):
    mEyeRight = boneset["mEyeRight"]
    mEyeLeft  = boneset["mEyeLeft"]
    
    loc = 0.5*(mEyeRight.relhead+mEyeLeft.relhead)
    EyeTarget = Bone("EyeTarget", relhead=V((loc.x, loc.y-2.0, loc.z)), reltail=V((0,0,0.1)), 
                        bonelayers=[B_LAYER_EYE_TARGET], parent=boneset["Head"], shape="CustomShape_EyeTarget",
                        skeleton='basic', bonegroup='Eye Target', mandatory='false')
    boneset["EyeTarget"] = EyeTarget

    if util.get_rig_type(rigType) == 'EXTENDED':
        FaceEyeTarget = Bone("FaceEyeAltTarget", relhead=V((loc.x, loc.y-2.0, loc.z)), reltail=V((0,0,0.1)), 
                            bonelayers=[B_LAYER_EYE_ALT_TARGET], parent=boneset["Head"], shape="CustomShape_EyeTarget",
                            skeleton='basic', bonegroup='Eye Alt Target', mandatory='false')
        boneset["FaceEyeAltTarget"] = FaceEyeTarget


class LoadSkeleton(bpy.types.Operator):
    bl_idname = "avastar.load_skeleton"
    bl_label  = "Load Skeleton"
    bl_description = "Load the Avastar Skeleton from file"

    def execute(self, context):
        omode = util.ensure_mode_is("OBJECT", context=context)
        
        filepath = util.get_skeleton_file()
        effectiveRigType   = arm.RigProp.RigType if rigtype == None else rigtype
        effectiveJointType = arm.RigProp.JointType if jointtype == None else jointtype

        boneset   = get_rigtype_boneset(effectiveRigType, effectiveJointType, filepath)
        util.ensure_mode_is(omode, context=context)
        return {'FINISHED'}
        

if __name__ == '__main__':



    pass






    





    
### Copyright 2011-2012 Magus Freston, Domino Marama, and Gaia Clary
### Copyright 2013-2015 Gaia Clary
###
### This file is part of Avastar 1.
### 
### Avastar is distributed under an End User License Agreement and you
### should have received a copy of the license together with Avastar.
### The license can also be obtained from http://www.machinimatrix.org/

classes = (
    LoadSkeleton,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered data:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered data:%s" % cls)
