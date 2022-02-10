### Copyright 2011, Magus Freston, Domino Marama, and Gaia Clary
### Modifications 2014-2015 Gaia Clary
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
import bpy
import os, logging, gettext, time
from math import pi, sin, cos, radians

from bpy.props import *
from mathutils import Vector, Matrix
from . import armature_util, const, rig, data, propgroups, mesh, shape, weights, util, bl_info
from .const  import *
from .init import *

from .data import Skeleton
 
LOCALE_DIR = os.path.join(os.path.dirname(__file__), 'locale')
translator = gettext.translation('avastar', LOCALE_DIR, fallback=True)

log = logging.getLogger("avastar.create")
registerlog = logging.getLogger("avastar.register")



def add_container(context, arm_obj, name, hide=True):
    scn=context.scene
    container = bpy.data.objects.new(name,None)    
    util.link_object(context, container)
    container.location    = arm_obj.location
    container.parent      = arm_obj
    container.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    util.object_hide_set(container, hide)
    util.object_select_set(container, False)
    container.hide_select = hide
    container.hide_render = hide
    return container

def add_eye_constraints(obj, context, bname, arm_obj):
    scene = context.scene
    bone_location = arm_obj.data.bones[bname].head_local
    active = util.get_active_object(context)
    cursor        = util.get_cursor(context)

    util.set_active_object(context, obj)
    util.set_cursor(context, bone_location)

    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    util.set_cursor(context, cursor)
    util.set_active_object(context, active)

    c = obj.constraints.new("COPY_LOCATION")
    c.name = COPY_LOCATION_NAME
    c.target       = arm_obj
    c.subtarget    = bname

    c = obj.constraints.new("COPY_ROTATION")
    c.name = COPY_ROTATION_NAME
    c.target       = arm_obj
    c.subtarget    = bname
    c.target_space = 'LOCAL'
    util.set_con_axis(c, 0, False)
    util.set_con_axis(c, 2, False)
    
    c = obj.constraints.new("COPY_SCALE")
    c.name = COPY_SCALE_NAME
    c.target       = arm_obj
    c.subtarget    = bname

def addGeneratedWeights(context, arm, obj, part, rigType=None):
    if rigType == None:
        rigType = util.get_rig_type()

    if rigType == 'EXTENDED':

        arm_original_mode = util.ensure_mode_is("POSE", object=arm)

        if part in ['upperBodyMesh', 'headMesh']:
            from . import mesh
            mesh.get_extended_weights(context, arm, obj, part, vert_mapping='TOPOLOGY')


def smart_bone_connector(armobj, rigType, jointType):
    SKELETON = data.getSkeletonDefinition(rigType, jointType)
    util.ensure_mode_is('EDIT')
    unknown_bones = []
    bone_names = Skeleton.bones_in_hierarchical_order(armobj)
    for bname in bone_names:
        DBONE = SKELETON.bones.get(bname)
        dbone = armobj.data.edit_bones.get(bname)
        parent_bone = dbone.parent
        if not DBONE:
            log.warn("Rig bone %s not recognized (ignore)")
            unknown_bones.append(dbone.name)
            continue


        if util.is_at_same_location(dbone.head, DBONE.b0head, rel_tol=1e-05):
            dbone.head = DBONE.b0head @ Rz90
        if DBONE.connected:
            parent_bone.tail = dbone.head
            dbone.use_connect = True

        tail = (DBONE.b0tail - DBONE.b0head) @ Rz90
        dbone.tail = dbone.head + tail

    util.ensure_mode_is('OBJECT')
    unknown_bone_count = len(unknown_bones)
    if unknown_bone_count > 0:
        log.warn("Ignoring %d unknown bones in imported rig", unknown_bone_count)

    return

def createAvatar(context, name="Avatar", quads=False, use_restpose=False, no_mesh=False, rigType='EXTENDED', jointType='PIVOT', max_param_id=-1, use_welding=True, mesh_ids=None):
    from . import propgroups
    with_meshes = not no_mesh
    util.progress_begin(0,10000)
    progress = 10

    if with_meshes:

        repo = util.ensure_avastar_repository_is_loaded()
    
    createCustomShapes()
    util.progress_update(progress, False)

    SKELETON = data.getSkeletonDefinition(rigType, jointType)
    DRIVERS = data.loadDrivers(max_param_id=max_param_id)
    shape.createShapeDrivers(DRIVERS)
    display_type='STICK'

    scn = context.scene
    oactive = util.get_active_object(context)
    ousermode = util.set_operate_in_user_mode(False)
    
    rigType   = util.get_rig_type(rigType)
    jointType = util.get_joint_type(jointType)

    log.info("Create Avatar Name         : %s" % name)
    log.info("Create Avatar Polygon type : %s" % ( 'without mesh' if no_mesh else 'QUADS' if quads else 'TRIS') )
    log.info("Create Avatar Pose         : %s" % ( "SL Neutral Shape" if use_restpose else "SL Default Shape") )
    log.info("Create Avatar Rig Type     : %s" % rigType)
    log.info("Create Avatar Joint Type   : %s" % jointType)

    arm_obj = create_empty_armature(context, name, display_type='STICK')
 

    arm_obj['avastar'] = AVASTAR_RIG_ID
    arm_obj['version'] = bl_info['version']
    arm_obj.RigProp.RigType   = rigType
    arm_obj.RigProp.JointType = jointType
    createArmature(context, arm_obj, SKELETON)

    arm_obj.IKSwitchesProp.Enable_Hands = 'FK'
    util.progress_update(progress, False)

    util.set_armature_layers(arm_obj, [B_LAYER_ORIGIN, B_LAYER_DEFORM])

    if with_meshes:
        parts = generate_system_meshes(context, arm_obj, name, rigType, mesh_ids, progress)
        arm_obj.data.show_bone_custom_shapes = True
    else:
        parts = {}

    arm_obj.data.show_bone_custom_shapes = with_meshes==True
    armature_util.set_display_type(arm_obj, display_type)
    util.object_show_in_front(arm_obj, True)

    rig.reset_cache(arm_obj)
    util.set_active_object(context, arm_obj)

    util.progress_update(progress, False)





    util.mode_set(mode='EDIT')
    util.mode_set(mode='OBJECT')


    shape.resetToRestpose(arm_obj, context, force_update=True)

    util.mode_set(mode='EDIT')
    rig.store_restpose_mats(arm_obj)
    arm_obj['sl_joints'] = {}

    util.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    util.object_select_set(arm_obj, True)
    util.set_active_object(context, arm_obj)

    if with_meshes:
        if quads == True:
            for obj in parts.values():
                try:
                    bpy.ops.avastar.quadify_avatar_mesh(mesh_id=obj["mesh_id"], object_name=obj.name)
                except:
                    print("Can not invoke Avastar quads conversion tool")
                    pass

        if use_welding:
            add_welding(parts, 'headMesh', 'upperBodyMesh')
            add_welding(parts, 'lowerBodyMesh', 'upperBodyMesh')
        util.set_active_object(context, arm_obj)

    if not use_restpose:
        log.debug("Set rig to Default pose")
        shape.reset_to_default(context)

    if arm_obj.RigProp.RigType != 'BASIC':
        rig.armatureSpineFold(arm_obj)
    
    arm_obj.RigProp.eye_setup='BASIC'
    util.set_operate_in_user_mode(ousermode)

    util.set_active_object(context, oactive)
    return arm_obj

def generate_system_meshes(context, arm_obj, armname, rigType, mesh_ids, progress):

    MESHES = data.loadMeshes()
    shape.createMeshShapes(MESHES)
    util.progress_update(progress, False)

    arm_obj.RigProp.Hand_Posture = HAND_POSTURE_DEFAULT
    
    generated = {}
    AVASTAR_MESHES = {}
    meshes = add_container(context, arm_obj, armname+"_meshes")

    for mesh in MESHES.values():

        util.progress_update(progress, False)
        name = mesh['name']
        if mesh_ids != None and not name in mesh_ids:
            continue

        obj = createMesh(context, name, mesh)
        AVASTAR_MESHES[name]=obj

        obj["weight"]       = "locked"
        obj["avastar-mesh"] = 1
        obj["mesh_id"]      = name


        mat = propgroups.add_material_for(arm_obj.name, name, True, arm_obj.avastarMaterialProp.material_type, arm_obj.avastarMaterialProp.unique)
        if mat:
            obj.active_material = mat

        obj.parent = meshes

        if 'skinJoints' in mesh:
            createMeshGroups(obj, mesh)

        for pid, morph in mesh['morphs'].items():
            createShapekey(obj, pid, morph, mesh)

        mod = util.create_armature_modifier(obj, arm_obj, name="Armature", preserve_volume=False)

        if name in ["hairMesh", "skirtMesh"]:
            util.object_hide_set(obj, True)
            obj.hide_render = True
            util.object_select_set(obj, False)
        else:
            util.object_hide_set(obj, False)
            obj.hide_render = False

        if util.get_rig_type(rigType) == 'EXTENDED':
            if name in ['upperBodyMesh', #For the Hands
                        'headMesh'       #For the Face
                        ]:
                generated[name] = obj

    for name, obj in generated.items():
        addGeneratedWeights(context, arm_obj, obj, name, rigType)

    return AVASTAR_MESHES


def create_empty_armature(context, name, display_type='STICK'):
    arm_data = bpy.data.armatures.new(name)
    arm_obj  = bpy.data.objects.new(name, arm_data)
    armature_util.set_display_type(arm_obj, display_type)

    util.link_object(context, arm_obj)
    util.set_active_object(context, arm_obj)
    return arm_obj


def add_welding(parts, from_name, to_name):
    from_obj = parts.get(from_name)
    to_obj   = parts.get(to_name)
    if from_obj and to_obj:
        mod = from_obj.modifiers.new("weld", 'DATA_TRANSFER')
        mod.use_loop_data=True
        mod.data_types_loops = {'CUSTOM_NORMAL'}
        mod.use_max_distance=True
        mod.max_distance=0.01
        mod.object = to_obj

        from_obj.data.auto_smooth_angle = 1.570796
        from_obj.data.use_auto_smooth = True

        print("add_welding from [%s] to [%s]" % (from_obj.name, to_obj.name) )


def createMesh(context, name, llm_mesh):


    verts = [llm_mesh['baseCoords'][i] for i in llm_mesh['vertLookup']]
    faces = llm_mesh['faces'] # a list of face 3-tuples
    vt = llm_mesh['texCoords'] # vertex (x,y) coords
    normals = llm_mesh['baseNormals']
    if "noseams" in llm_mesh:
        noseams    = llm_mesh['noseams']
        extraseams = llm_mesh['extraseams']
        extrapins  = llm_mesh['extrapins']
    else:
        noseams    = []
        extraseams = []
        extrapins  = []

    meshFaces = []
    for f in faces:
        fv = [data.getVertexIndex(llm_mesh, v) for v in f]
        meshFaces.append(fv)
    

    bpy.ops.object.select_all(action="DESELECT")


    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (0,0,0)


    util.link_object(context, obj)
    util.set_active_object(context, obj)
    util.object_select_set(obj, True)



    mesh.from_pydata(verts, [], meshFaces)
    mesh.update(calc_edges=True)


    for e in mesh.edges:
        if not e.index in noseams:
            a, b = e.vertices
            if e.index in extraseams \
               or ( llm_mesh['vertLookup'][a] in llm_mesh['vertexRemap'].values() and \
                    llm_mesh['vertLookup'][b] in llm_mesh['vertexRemap'].values()) :
                e.use_seam = True

    mesh.update(calc_edges=True)
    util.update_view_layer(context)

    util.mode_set(mode='EDIT')
    oselect_modes = util.set_mesh_select_mode((True,True,False))

    try:
        bpy.ops.mesh.select_non_manifold(extend=False, use_wire=False, use_boundary=True, use_multi_face=False, use_non_contiguous=False, use_verts=False)
    except:
        bpy.ops.mesh.select_non_manifold(extend=False)

    bpy.ops.mesh.mark_seam(clear=False)
    bpy.ops.mesh.select_all(action='DESELECT')
    util.set_mesh_select_mode(oselect_modes)










    for v, normal in enumerate(normals):
        if v not in llm_mesh['vertexRemap']:
            mesh.vertices[data.getVertexIndex(llm_mesh, v)].normal = normal



    bpy.ops.mesh.select_all(action='DESELECT')
    util.ensure_mode_is("OBJECT")


    bpy.ops.object.shade_smooth()





    uv = util.add_uv_layer(mesh, name="SLMap")



    problemFaces = [
        ('upperBodyMesh',199),
        ('headMesh',1464),
        ('headMesh',1465),
        ('skirtMesh',200),
        ('skirtMesh',211),
        ('skirtMesh',217),
        ('eyeBallRightMesh',173),
        ('eyeBallLeftMesh',173),
        ('eyelashMesh',4),
        ('hairMesh',351),
        ]

    uv_layers = util.get_uv_layers(mesh)
    index    = util.get_uv_index_for_layer(mesh, uv.name)
    uvloops  = mesh.uv_layers[index].data
    loops    = mesh.loops
    polygons = mesh.polygons
    for i, face in enumerate(faces):
        for j in range(3):
            loop = polygons[i].loop_indices[j]
            uvloops[loop].uv = vt[face[j]]
                    

    obj.shape_key_add(name="Basis")
    obj.data.update()
    obj.active_shape_key_index = 0
    
    obj.use_shape_key_edit_mode = True
    util.tag_addon_revision(obj)
    return obj


def createShapekey(obj, pid, morph, mesh):
    key = obj.shape_key_add(name=pid)
    

    key.slider_min = morph['value_min']
    key.slider_max = morph['value_max']
    key.value      = morph['value_default']
    

    for v in morph['vertices']:

        if v['vertexIndex'] in mesh['vertexRemap']:
            continue
        i = data.getVertexIndex(mesh, v['vertexIndex'])
        key.data[i].co = Vector(mesh['baseCoords'][v['vertexIndex']]) + Vector(v['coord'])











def createMeshGroups(obj, mesh):



    for joint in mesh['skinJoints']:
        group = obj.vertex_groups.new(name=joint)





    name = mesh['name']
    for ii in range(len( mesh['weights'] )):
        if ii in mesh['vertexRemap']:
            continue
        i = data.getVertexIndex(mesh, ii)
        b,w = mesh['weights'][ii]
        b1, b2 = data.WEIGHTSMAP[name][b]
        obj.vertex_groups[b1].add([i], 1.0-w, 'REPLACE')
        if b2 is not None and w!=0:
            obj.vertex_groups[b2].add([i], w, 'REPLACE')


def add_initial_rotation(pbone, delta):
    original_mode = pbone.rotation_mode
    pbone.rotation_mode = "QUATERNION"
    pbone.rotation_quaternion.z += delta
    pbone.rotation_mode = original_mode
    
def add_bone_group(arm, name, color_set):
    bpy.ops.pose.group_add()
    bg = arm.pose.bone_groups.active 
    bg.name = name
    bg.color_set = color_set

def add_bone_groups(arm):
    for group, val in BONEGROUP_MAP.items():
        colorset   = val[0]       
        add_bone_group(arm, group, colorset)



def createArmature(context, arm_obj, SKELETON):
    IR = 0.001
    scn = context.scene    
    rigType = arm_obj.RigProp.RigType

    util.set_active_object(context, arm_obj)
    util.object_select_set(arm_obj, True)

    util.set_object_mode('EDIT')



    createBoneRecursive(SKELETON["Origin"], None, arm_obj)

    util.set_object_mode('POSE')
    add_bone_groups(arm_obj)


    util.set_object_mode('EDIT')

    util.set_armature_layers(arm_obj, B_REFERENCE_POSE_LAYERS if rigType == 'REFERENCE' else B_DEFAULT_POSE_LAYERS)

    rig.adjustBoneRoll(arm_obj)
    rig.adjustSLToRig(arm_obj) # Forces SL bones into exact Rest pose (adjust bone roll ?)


    util.set_object_mode('POSE')
    setCustomShapesRecursive(SKELETON["Origin"], arm_obj)

    if rigType!= 'REFERENCE':

        createConstraints(context, arm_obj, SKELETON)


    util.mode_set(mode='OBJECT')
    Skeleton.get_toe_hover_z(arm_obj, reset=True)
    



    for pbone in arm_obj.pose.bones:


        pbone.lock_scale = [True, True, True] 

        BONE = SKELETON[pbone.name]
        if BONE == None:
            continue



        pbone.ik_stiffness_x = BONE.stiffness[0]
        pbone.ik_stiffness_y = BONE.stiffness[1]
        pbone.ik_stiffness_z = BONE.stiffness[2]

        if BONE.limit_rx is not None \
           or BONE.limit_ry is not None \
           or BONE.limit_rz is not None: 


            con = pbone.constraints.new("LIMIT_ROTATION")
            con.name = LIMIT_ROTATION_NAME
            con.owner_space = 'LOCAL' 


            if BONE.limit_rx is not None:
                pbone.use_ik_limit_x = True
                pbone.ik_min_x = radians(BONE.limit_rx[0])
                pbone.ik_max_x = radians(BONE.limit_rx[1])
                con.min_x = radians(BONE.limit_rx[0])
                con.max_x = radians(BONE.limit_rx[1])
                con.use_limit_x = True
            if BONE.limit_ry is not None:
                pbone.use_ik_limit_y = True
                pbone.ik_min_y = radians(BONE.limit_ry[0])
                pbone.ik_max_y = radians(BONE.limit_ry[1])
                con.min_y = radians(BONE.limit_ry[0])
                con.max_y = radians(BONE.limit_ry[1])
                con.use_limit_y = True
            if BONE.limit_rz is not None:
                pbone.use_ik_limit_z = True
                pbone.ik_min_z = radians(BONE.limit_rz[0])
                pbone.ik_max_z = radians(BONE.limit_rz[1])
                con.min_z = radians(BONE.limit_rz[0])
                con.max_z = radians(BONE.limit_rz[1])
                con.use_limit_z = True





        if pbone.name in ["Tinker", "Pelvis", "PelvisInv"]:
            pbone.lock_location = [True, True, True]



        if "Link" in pbone.name or pbone.name == "Pelvis" or "Line" in pbone.name:
            pbone.lock_rotation = [True, True, True] 
            pbone.lock_rotation_w = True
            pbone.lock_location = [True, True, True]
            pbone.lock_ik_x = True
            pbone.lock_ik_y = True
            pbone.lock_ik_z = True

        B = SKELETON[pbone.name]
        if B.bonegroup in arm_obj.pose.bone_groups:
            pbone.bone_group = arm_obj.pose.bone_groups[B.bonegroup]
        else:            
            print("Bone group [%s : %s] does not exist" % (pbone.name, B.bonegroup) )

        if pbone.name == "ElbowRight":
            add_initial_rotation(pbone,IR)
        elif pbone.name == "ElbowLeft":
            add_initial_rotation(pbone,-IR)


    defaultLayers = getDefaultLayers(rigType)
    for layer in defaultLayers:
        arm_obj.data.layers[layer] = True

    for pbone in arm_obj.pose.bones:

        if pbone.name[0] == "m" or "m"+pbone.name in arm_obj.pose.bones or pbone.name in ['Tinker','PelvisInv']:
            pbone['priority'] = NULL_BONE_PRIORITY



    for bname in sym_expand(arm_obj.data.bones.keys(), ['*Link.','*Line', 'Pelvis']):
        if bname in arm_obj.data.bones:
            arm_obj.data.bones[bname].hide_select = True

    for bname in data.get_volume_bones(only_deforming=False):
        if bname in arm_obj.pose.bones:
            arm_obj.pose.bones[bname].lock_rotation[0]=True
            arm_obj.pose.bones[bname].lock_rotation[1]=True
            arm_obj.pose.bones[bname].lock_rotation[2]=True
            arm_obj.pose.bones[bname].lock_location[0]=True
            arm_obj.pose.bones[bname].lock_location[1]=True
            arm_obj.pose.bones[bname].lock_location[2]=True

    for bone in arm_obj.data.bones:
        bone.layers[B_LAYER_DEFORM] = bone.use_deform
        B = SKELETON[bone.name]
        if B:
            bone['b0head'] = B.b0head
            bone['b0tail'] = B.b0tail - B.b0head
        else:
            log.warning("Create Armature: Skeleton Bone %s not in Definition" % bone.name)

def init_meta_data(blbone, BONE):

    is_structure = BONE.is_structure
    if is_structure == None:
        is_structure = False

    blbone['is_structure'] = is_structure
    if BONE.slname is not None or BONE.blname:
        blbone['scale']   = tuple(BONE.scale)
        blbone['offset']  = tuple(BONE.offset)
        blbone[JOINT_BASE_HEAD_ID] = tuple(BONE.relhead)
        blbone[JOINT_BASE_TAIL_ID] = tuple(BONE.reltail) if BONE.reltail is not None else tuple(Vector(blbone[JOINT_BASE_HEAD_ID]) + Vector((0,0.1,0)))
        blbone['scale0']  = tuple(BONE.scale0)
        blbone['rot0']    = tuple(BONE.rot0)
        blbone['pivot0']  = tuple(BONE.pivot0)
        blbone['pos0']    = tuple(BONE.pos0)

        if BONE.slname is not None:
            blbone['slname'] = BONE.slname
        if BONE.bvhname is not None:
            blbone['bvhname'] = BONE.bvhname


def createBoneRecursive(BONE, parent, arm_obj, rigType=None):
    if not rigType:
        rigType = arm_obj.RigProp.RigType

    if rigType == 'BASIC' and BONE.skeleton=='extended':
        blbone = None
    else:
        blbone = add_bone_to_armature(BONE, arm_obj, parent)

    if len(BONE.children) > 0:
        keys = [child.blname for child in BONE.children] 

        for CHILD in BONE.children:
            if blbone:
                blchild = createBoneRecursive(CHILD, blbone, arm_obj, rigType)
                blchild.parent = blbone
            else:
                blbone = createBoneRecursive(CHILD, parent, arm_obj, rigType)
    return blbone


def add_bone_to_armature(BONE, arm_obj, parent):
    name = BONE.blname
    blbone = arm_obj.data.edit_bones.new(name)
    h = Vector(BONE.head())
    t = Vector(BONE.tail())
    size = (t-h).magnitude



    blbone.parent = parent
    blbone.head   = h
    blbone.tail   = t
    blbone.layers = [ii in BONE.bonelayers for ii in range(32)]
    blbone.roll   = BONE.roll
    blbone.use_inherit_scale = False
    blbone.use_inherit_rotation = True
    blbone.use_local_location = True
    rig.set_connect(blbone, BONE.connected, "create_Bone_Recursive")
    if hasattr(BONE,'deform'):
        blbone.use_deform = BONE.deform
    else:
        blbone.use_deform = False

    init_meta_data(blbone, BONE)
    return blbone



def setCustomShapesRecursive(bone, arm_ob):
    if bone.shape is not None:
        pbone = arm_ob.pose.bones.get(bone.blname)
        dbone = arm_ob.data.bones.get(bone.blname)
        if pbone and dbone:
            pbone.custom_shape = bpy.data.objects[bone.shape]
            dbone.show_wire = bone.wire
            try:
                if bone.shape_scale is not None:
                    arm_ob.pose.bones[bone.blname].custom_shape_scale = bone.shape_scale
            except:
                print("WARN: This version of Blender does not support scaling of Custom shapes")
                print("      Ignoring Custom Shape Scale for bone [%s]" % (bone.blname))

    for child in bone.children: 
        setCustomShapesRecursive(child, arm_ob)

def add_bone_constraint(type, pbone, name=None, space='LOCAL', influence=1.0, target=None, subtarget=None, mute=False):
    con = pbone.constraints.new(type)
    
    if target:
        con.target=target
    if subtarget:
        con.subtarget=subtarget

    try:
        con.owner_space  = space
        con.target_space = space
    except:
        pass
    
    con.influence = influence
    con.show_expanded = False
    con.mute = mute

    if name:
        con.name=name
    return con

def set_constraint_limit(con, states, values):
    if con.type=='LIMIT_ROTATION':
        con.use_limit_x = states[0]
        con.min_x       = values[0][0]
        con.max_x       = values[0][1]
        
        con.use_limit_y = states[1]
        con.min_y       = values[1][0]
        con.max_y       = values[1][1]
        
        con.use_limit_z = states[2]
        con.min_z       = values[2][0]
        con.max_z       = values[2][1]

    elif con.type=='LIMIT_LOCATION':
        con.use_min_x = states[0]
        con.use_max_x = states[0]
        con.min_x       = values[0][0]
        con.max_x       = values[0][1]
        
        con.use_min_y = states[0]
        con.use_max_y = states[0]
        con.min_y       = values[1][0]
        con.max_y       = values[1][1]
        
        con.use_min_z = states[0]
        con.use_max_z = states[0]
        con.min_z       = values[2][0]
        con.max_z       = values[2][1]

def set_source_range(con, source, values):
    con.map_from = source
    if source == 'LOCATION':
        con.from_min_x = values[0][0]
        con.from_max_x = values[0][1]
        con.from_min_y = values[1][0]
        con.from_max_y = values[1][1]
        con.from_min_z = values[2][0]
        con.from_max_z = values[2][1]
    elif source == 'ROTATION':
        con.from_min_x_rot = values[0][0]*DEGREES_TO_RADIANS
        con.from_max_x_rot = values[0][1]*DEGREES_TO_RADIANS
        con.from_min_y_rot = values[1][0]*DEGREES_TO_RADIANS
        con.from_max_y_rot = values[1][1]*DEGREES_TO_RADIANS
        con.from_min_z_rot = values[2][0]*DEGREES_TO_RADIANS
        con.from_max_z_rot = values[2][1]*DEGREES_TO_RADIANS
    elif source == 'SCALE':
        con.from_min_x_scale = values[0][0]
        con.from_max_x_scale = values[0][1]
        con.from_min_y_scale = values[1][0]
        con.from_max_y_scale = values[1][1]
        con.from_min_z_scale = values[2][0]
        con.from_max_z_scale = values[2][1]
    
def set_destination (con, dest,   values):
    con.map_to = dest
    
    if dest == 'LOCATION':
        con.to_min_x = values[0][0]
        con.to_max_x = values[0][1]
        con.to_min_y = values[1][0]
        con.to_max_y = values[1][1]
        con.to_min_z = values[2][0]
        con.to_max_z = values[2][1]
    elif dest == 'ROTATION':
        con.to_min_x_rot = values[0][0]*DEGREES_TO_RADIANS
        con.to_max_x_rot = values[0][1]*DEGREES_TO_RADIANS
        con.to_min_y_rot = values[1][0]*DEGREES_TO_RADIANS
        con.to_max_y_rot = values[1][1]*DEGREES_TO_RADIANS
        con.to_min_z_rot = values[2][0]*DEGREES_TO_RADIANS
        con.to_max_z_rot = values[2][1]*DEGREES_TO_RADIANS
    elif dest == 'SCALE':
        con.to_min_x_scale = values[0][0]
        con.to_max_x_scale = values[0][1]
        con.to_min_y_scale = values[1][0]
        con.to_max_y_scale = values[1][1]
        con.to_min_z_scale = values[2][0]
        con.to_max_z_scale = values[2][1]
    
def set_mapping(con, x, y, z):
    con.map_to_x_from=x
    con.map_to_y_from=y
    con.map_to_z_from=z
    

class FaceController:

    ID = 'face_controller'

    def __init__(self, stored_influences=None):
        if stored_influences == None:
            stored_influences = {}
        self.face_influences = stored_influences


    def get_face_influences(self):
        return self.face_influences


    def get_bone_influences(self, bone_name):
        bone_influences = self.face_influences.get(bone_name)
        if bone_influences == None:
            bone_influences = {}
            self.face_influences[bone_name] = bone_influences
        return bone_influences


    def add_influence(self, bone, constraint):
        self.add_influence_by_name(bone.name, constraint.name, constraint.influence)


    def add_influence_by_name(self, bone_name, constraint_name, influence):
        bone_influences = self.get_bone_influences(bone_name)
        bone_influences[constraint_name] = influence


    def get_influence(self, bone_name, constraint_name, val):
        bone_influences = self.get_bone_influences(bone_name)
        influence = bone_influences.get(constraint_name, val)
        return influence


    def adjust_influences(self, arm, factor):
        pbones = arm.pose.bones
        for bone_name, bone_influences in self.face_influences.items():
            pbone = pbones.get(bone_name)
            if pbone:
                for item in bone_influences.items():
                    constraint_name = item[0]
                    influence = item[1] 
                    con = pbone.constraints.get(constraint_name)
                    if con:
                        con.influence = influence*factor
        return


def create_face_controllers(arm, group):
    face_controller = FaceController()
    pbones = arm.pose.bones

    try:
        lipmaster = pbones['ikFaceLipShapeMaster']
        lipshape  = pbones['ikFaceLipShape']
    except:
        print("No face controllers defined for this Skeleton")
        return

    for symmetry in ["Left", "Right"]:

        xmirror = 1 if symmetry=='Left' else -1

        subtarget = 'ikFaceEyebrowCenter%s' % symmetry
        if subtarget in pbones:
            for handle in(["FaceEyebrowInner","FaceEyebrowCenter", "FaceEyebrowOuter"]):
                pbone = pbones["%s%s" % (handle,symmetry)]
                influence = 1 if "Center" in handle else 0.25
                con   = add_bone_constraint('COPY_TRANSFORMS', pbone, name="AVA Transform", target=arm, subtarget = subtarget, influence=influence)
                face_controller.add_influence(pbone, con)

        for part in ['Upper', 'Lower', 'Corner']:
            pbone = pbones.get ('FaceLip%s%s' % (part, symmetry))
            if not pbone:
                continue

            if part == 'Upper':
                ymirror = 1
                scale = 1
            else:
                ymirror = -1
                scale = 2

            subtarget = 'ikFaceLipCorner%s' % symmetry
            if subtarget in pbones:
                con = add_bone_constraint('COPY_TRANSFORMS', pbone, name="AVA Transform", target=arm, subtarget = subtarget, influence = 0.15)
                face_controller.add_influence(pbone, con)

            subtarget = lipshape.name
            if subtarget in pbones:

                if part == 'Corner':
                    influence = 0.75
                    xd = [-0.01*xmirror, 0.01*xmirror]
                    yd = [-0.015, 0.015]
                    zd = [0.02, -0.02]
                else:
                    influence = 0.5
                    xd = [-0.005*xmirror, 0.005*xmirror]
                    yd = [-scale*0.001, scale*0.001]
                    zd = [-0.01*ymirror, 0.01*ymirror]

                con = add_bone_constraint('TRANSFORM', pbone, name="AVA Location", space='POSE', target=arm, subtarget = lipshape.name, influence=influence)
                face_controller.add_influence(pbone, con)
                set_source_range(con, 'SCALE',    [[0.5,1.5],    [0.5,1.5],      [0.5,1.50]] )
                set_mapping(con, 'X', 'X', 'Z')
                set_destination (con, 'LOCATION', [xd, yd, zd] )

            subtarget = lipmaster.name
            if subtarget in pbones:
                con = add_bone_constraint('TRANSFORM', pbone, name="AVA Rotation",       target=arm, subtarget = lipmaster.name, influence=1.0)
                face_controller.add_influence(pbone, con)
                set_source_range(con, 'ROTATION',    [[-15, 10],    [-15, 10],      [-15, 10]] )
                set_mapping(con, 'X', 'Y', 'X')
                xd = [-0.0015*xmirror*ymirror, 0.001*xmirror*ymirror] if part == 'Upper' else [0.00, 0.00]
                yd = [0.00,-0.00]
                zd = [-0.0075,0.005]
                set_destination (con, 'LOCATION', [xd, yd, zd] )


        pbone = pbones['FaceCheekLower%s' % symmetry]
        subtarget = lipshape.name
        if subtarget in pbones:
            con = add_bone_constraint('TRANSFORM', pbone, name="AVA Rotation",       target=arm, subtarget = lipshape.name)
            face_controller.add_influence(pbone, con)
            set_source_range(con, 'SCALE',    [[0.5,1.5],    [0.5,1.5],      [0.5,1.50]] )
            set_mapping(con, 'X', 'X', 'Z')
            set_destination (con, 'LOCATION', [[0.015*xmirror,-0.015*xmirror],    [0.005,-0.005], [-0.01,0.01]] )


        pbone = pbones['FaceNose%s' % symmetry]
        subtarget = lipshape.name
        if subtarget in pbones:
            con = add_bone_constraint('TRANSFORM', pbone, name="AVA Location",       target=arm, subtarget = lipshape.name)
            face_controller.add_influence(pbone, con)
            set_source_range(con, 'SCALE',    [[0.5,1.5], [0.5,1.5], [0.5,1.50]] )
            set_mapping(con, 'X', 'X', 'Z')
            set_destination (con, 'LOCATION', [[0,0],     [0,0],     [-0.002,0.002]] )

    con = add_bone_constraint('LIMIT_ROTATION', lipmaster)
    face_controller.add_influence(pbone, con)
    con.name = LIMIT_ROTATION_NAME

    set_constraint_limit(con, [False, True, True], [[ 0.000, 0.000], [ 0.000,0.000], [ 0.000, 0.000]])
    con = add_bone_constraint('LIMIT_LOCATION', lipmaster)
    face_controller.add_influence(pbone, con)
    set_constraint_limit(con, [True, True, True],  [[-0.02, 0.02], [-0.02, 0.02], [0, 0.1]])
    
    con = add_bone_constraint('TRANSFORM', lipshape, name="AVA Scale",    target=arm, subtarget = lipmaster.name)
    face_controller.add_influence(pbone, con)
    set_source_range(con, 'LOCATION', [[-0.02, 0.02],[-0.02, 0.02],[ 0, 0.1]])
    set_destination (con, 'SCALE',    [[0.5,1.5],    [0.5,1.5],    [1.0,1.5]]    )
    set_mapping(con, 'Y', 'Y', 'Z')
    




    
    try:
        pbone = pbones['FaceLipUpperCenter']
        con = add_bone_constraint('TRANSFORM', pbone, name="AVA Location", space='POSE', target=arm, subtarget = lipshape.name, influence=0.75)
        face_controller.add_influence(pbone, con)
        set_source_range(con, 'SCALE',    [[0.5,1.5],    [0.5,1.5],      [0.5,1.50]] )
        set_destination (con, 'LOCATION', [[0.0,0.0],    [0.002,-0.002], [-0.01,0.01]] )

        pbone = pbones['FaceLipLowerCenter']
        con = add_bone_constraint('TRANSFORM', pbone, name="AVA Location", space='POSE', target=arm, subtarget = lipshape.name)
        face_controller.add_influence(pbone, con)
        set_source_range(con, 'SCALE',    [[0.5,1.5],    [0.5,1.5],      [0.5,1.50]] )
        set_destination (con, 'LOCATION', [[0.0,0.0],    [0.002,-0.002], [0.02,-0.02]] )

        con = add_bone_constraint('TRANSFORM', pbone, name = "AVA Tranform", target=arm, subtarget = lipmaster.name)
        face_controller.add_influence(pbone, con)
        set_source_range(con, 'ROTATION',    [[-15, 10],    [-15, 10],      [-15, 10]] )
        set_mapping(con, 'X', 'Y', 'X')
        xd = [0.00,-0.00]
        yd = [0.00,-0.00]
        zd = [-0.00075,0.0005]
        set_destination (con, 'LOCATION', [xd, yd, zd] )

    except:
        pass

    pbone = pbones['FaceNoseCenter']
    con = add_bone_constraint('TRANSFORM', pbone, name="AVA Location",    target=arm, subtarget = lipshape.name)
    face_controller.add_influence(pbone, con)
    set_source_range(con, 'SCALE',    [[0.5,1.5],    [0.5,1.5],    [0.5,1.50]]  )
    set_destination (con, 'LOCATION', [[0.0,0.0],    [0.00,-0.0],  [-0.004,0.004]] )

    pbone = pbones['FaceJaw']
    con = add_bone_constraint('TRANSFORM', pbone, name="AVA Location",    target=arm, subtarget = lipshape.name)
    face_controller.add_influence(pbone, con)
    set_source_range(con, 'SCALE',    [[0.5,1.5],    [0.5,1.5],  [0.5,1.50]]  )
    set_destination (con, 'ROTATION', [[-10.0,10.0], [0.0,0.0],  [0.0,0.0]] )
    set_mapping(con, 'Z', 'Y', 'X')

    pbone = pbones['FaceTeethLower']
    con = add_bone_constraint('TRANSFORM', pbone, name="AVA Location",    target=arm, subtarget = lipshape.name)
    face_controller.add_influence(pbone, con)
    set_source_range(con, 'SCALE',    [[0.5,1.5],  [0.5,1.5],  [0.5,1.50]]  )
    set_destination (con, 'LOCATION', [[0.0,0.0],  [0.0,0.0],  [0.0,0.0]] )
    set_mapping(con, 'X', 'Y', 'Z')

    arm[FaceController.ID] = face_controller.get_face_influences()
    return


def create_hand_chain_controllers(arm):
    group = "Hand"
    pbones = arm.pose.bones
    for pbone in [b for b in pbones if b.name.startswith(group) and (b.name.endswith("Left") or b.name.endswith("Right"))]:
        name = pbone.name
        symmetry = "Left" if name.endswith("Left") else "Right"
        part     = name[len(group):-len(symmetry)-1]
        sindex   = name[-len(symmetry)-1]

        if sindex == None: continue # Should never happen
        index = int(sindex)
        if not name.endswith("0"+symmetry):
            con = pbone.constraints.new("LIMIT_ROTATION")
            con.name = LIMIT_ROTATION_NAME
            con.use_limit_x = True
            con.min_x = -90 * DEGREES_TO_RADIANS
            con.max_x =  15 * DEGREES_TO_RADIANS

            min = -30 if name.startswith("HandThumb1") else -10
            max =  30 if name.startswith("HandThumb1") else  10
            con.use_limit_y = True
            con.min_y = min * DEGREES_TO_RADIANS
            con.max_y = max * DEGREES_TO_RADIANS

            if index == 1:
                min = -30
                max = 50 if name.startswith("HandPinky") else 40 if name.startswith("HandThumb1") else 20
                if symmetry == "Left":
                    min, max = -max, -min
            else:
                min = max = 0

            con.use_limit_z = True
            con.min_z = min * DEGREES_TO_RADIANS
            con.max_z = max * DEGREES_TO_RADIANS
            con.owner_space = 'LOCAL'
            con.influence = 1

        if index == 1:
            pbone.lock_rotation[1]=False if name.startswith("HandThumb1") else  True
            pbone.lock_rotation_w=True
            pbone.lock_rotations_4d=True
            continue

        if index == 3: #disable IK constraints for now (set back to index == 3 top reactivate)
            try:
                solver          = pbones["ik%sSolver%s" % (part,symmetry)]
                target          = pbones["ik%sTarget%s" % (part,symmetry)]
                con             = solver.constraints.new("IK")
                con.target      = arm
                con.subtarget   = target.name
                con.chain_count = 3
                con.use_tail    = False
                con.mute        = True
                con.name        = 'Grab'
                con.influence   = 0

                if part in ['Thumb','Index']:
                    target          = pbones["ikIndexPinch%s" % (symmetry)]
                    con             = solver.constraints.new("IK")
                    con.target      = arm
                    con.subtarget   = target.name
                    con.chain_count = 3
                    con.use_tail    = False
                    con.mute        = False
                    con.name        = 'Pinch'
                    con.influence   = 0

            except:

                pass

        if not name.endswith("0"+symmetry):
            con = pbone.constraints.new("COPY_ROTATION")
            con.name = COPY_ROTATION_NAME
            con.target = arm
            con.subtarget = pbone.parent.name
            con.use_offset = True
            con.target_space = 'LOCAL'
            con.owner_space = 'LOCAL'
            con.influence = 0.5 if index==3 else 1 # make finger tips curl less

            util.set_con_axis(con, 1, False)
            util.set_con_axis(con, 2, False)

        pbone.use_ik_limit_x = True
        pbone.ik_min_x = -90 * DEGREES_TO_RADIANS
        pbone.ik_max_x = 0
        pbone.lock_ik_y = True
        pbone.lock_ik_z = True



def getDefaultLayers(rigType):
    defaultLayers = B_VISIBLE_LAYERS_SL
    defaultLayers.append(B_LAYER_EYE_TARGET if rigType == 'BASIC' else B_LAYER_EYE_ALT_TARGET)
    return defaultLayers


def getRotLocBoneSet(pbones, rigType):

    LArm  = ['mCollarLeft', 'mShoulderLeft','mElbowLeft','mWristLeft']
    RArm  = ['mCollarRight', 'mShoulderRight','mElbowRight','mWristRight']
    LLeg  = ['mHipLeft','mKneeLeft','mAnkleLeft', 'mFootLeft', 'mToeLeft']
    RLeg  = ['mHipRight','mKneeRight','mAnkleRight', 'mFootRight', 'mToeRight']
    LLimb = ['mHindLimb1Left','mHindLimb2Left','mHindLimb3Left', 'mHindLimb4Left']
    RLimb = ['mHindLimb1Right','mHindLimb2Right','mHindLimb3Right', 'mHindLimb4Right']
    Torso = ['mPelvis', 'mTorso', 'mChest', 'mNeck', 'mHead', 'mSkull', 'mEyeLeft', 'mEyeRight']
    Face  = ['mFaceEyeAltLeft', 'mFaceEyeAltRight']

    RotLocBones = LArm+RArm+LLeg+RLeg+Torso
    Custom = []
    if rigType != 'BASIC':
        Custom += util.bone_category_keys(pbones, "mWing")
        Custom += util.bone_category_keys(pbones, "mTail")
        Custom += util.bone_category_keys(pbones, "mFace")
        Custom += util.bone_category_keys(pbones, "mHand")
        Custom += util.bone_category_keys(pbones, "mGroin")
        Custom += util.bone_category_keys(pbones, "mHind")
        Custom += util.bone_category_keys(pbones, "mSpine")

        RotLocBones.extend(LLimb+RLimb+Custom+Face)
    return RotLocBones


def getRotLocIKSet(rigType):
    RotLocIK = [
        ("WristLeft","ikWristLeft"),
        ("WristRight","ikWristRight"),
        ("AnkleLeft","ikAnkleLeft"),
        ("AnkleRight","ikAnkleRight")
    ]
    if rigType != 'BASIC':
        RotLocIK.extend(
            [
                ("HindLimb3Left","ikHindLimb3Left"),
                ("HindLimb3Right","ikHindLimb3Right")
            ]
        )
    return RotLocIK


def getChainSet(rigType):



    if  get_blender_revision() < 284300:
        return getLimitedChainSet(rigType)

    chains =  {'CollarLeft':[4,1], 'ShoulderLeft':[2,1],'ElbowLeft':[3,1],'WristLeft':[4,1],
               'CollarRight':[4,1], 'ShoulderRight':[2,1],'ElbowRight':[3,1],'WristRight':[4,1],
               'HipLeft':[4,1],'KneeLeft':[2,1],'AnkleLeft':[3,1], 'FootLeft':[4,1], 'ToeLeft':[5,1],
               'HipRight':[4,1],'KneeRight':[2,1],'AnkleRight':[3,1], 'FootRight':[4,1], 'ToeRight':[5,1],
               'Tinker':[2,1], 'Torso':[2,1], 'Chest':[2,1], 'Neck':[3,1], 'Head':[4,1], 'Skull':[5,1],
               'EyeLeft':[1,1], 'EyeRight':[1,1]
              }

    if rigType != 'BASIC':
        chains.update({'HindLimb1Left':[4,1],'HindLimb2Left':[2,1],'HindLimb3Left':[3,1], 'HindLimb4Left':[4,1]})
        chains.update({'HindLimb1Right':[4,1],'HindLimb2Right':[2,1],'HindLimb3Right':[3,1], 'HindLimb4Right':[4,1]})
        chains.update({'FaceEyeAltLeft':[1,1], 'FaceEyeAltRight':[1,1]})
        chains.update({'Wing1Left':[1,1], 'Wing2Left':[2,1], 'Wing3Left':[3,1], 'Wing4Left':[4,1]})
        chains.update({'Wing1Right':[1,1], 'Wing2Right':[2,1], 'Wing3Right':[3,1], 'Wing4Right':[4,1]})
        chains.update({'Tail1':[1,1], 'Tail2':[2,1], 'Tail3':[3,1], 'Tail4':[4,1], 'Tail5':[5,1], 'Tail6':[6,1]})

    return chains


def getLimitedChainSet(rigType):




    chains =  {'WristLeft'     :[4,1],
               'WristRight'    :[4,1],
               'AnkleLeft'     :[3,1],
               'AnkleRight'    :[3,1],
               'Neck'          :[3,1]
              }
    if rigType != 'BASIC':
        chains['HindLimb3Left']  = [3,1]
        chains['HindLimb3Right'] = [3,1]
    return chains


def createConstraints(context, armobj, SKELETON):
    rigType = SKELETON.rig_type
    pbones = armobj.pose.bones
    #

    #
    pbone = pbones['ElbowLeft'] 
    pbone.lock_ik_y = True
    pbone.lock_ik_x = True
    con = pbone.constraints.new("IK")
    con.name = IKNAME
    con.use_tail = True
    con.use_stretch = False
    con.target = armobj
    con.subtarget = "ikWristLeft"
    con.pole_target = armobj
    con.pole_subtarget = "ikElbowTargetLeft"   
    con.chain_count = 2
    con.pole_angle = pi # different from right, go figure.
    con.influence = 0

    pbone = pbones['ElbowRight'] 
    pbone.lock_ik_y = True
    pbone.lock_ik_x = True
    con = pbone.constraints.new("IK")
    con.name = IKNAME
    con.use_tail = True
    con.use_stretch = False
    con.target = armobj
    con.subtarget = "ikWristRight"
    con.pole_target = armobj
    con.pole_subtarget = "ikElbowTargetRight"   
    con.chain_count = 2
    con.pole_angle = 0
    con.influence = 0

    pbone = pbones['KneeLeft'] 

    pbone.lock_ik_z = True
    con = pbone.constraints.new("IK")
    con.name = IKNAME
    con.use_tail = True
    con.use_stretch = False
    con.target = armobj
    con.subtarget = "ikAnkleLeft"
    con.pole_target = armobj
    con.pole_subtarget = "ikKneeTargetLeft"   
    con.chain_count = 2
    con.pole_angle = radians(-90)
    con.influence = 0

    pbone = pbones['KneeRight'] 

    pbone.lock_ik_z = True
    con = pbone.constraints.new("IK")
    con.name = IKNAME
    con.use_tail = True
    con.use_stretch = False
    con.target = armobj
    con.subtarget = "ikAnkleRight"
    con.pole_target = armobj
    con.pole_subtarget = "ikKneeTargetRight"   
    con.chain_count = 2
    con.pole_angle = radians(-90)
    con.influence = 0

    pbone = pbones.get('HindLimb2Right')
    if pbone:

        pbone.lock_ik_z = True
        con = pbone.constraints.new("IK")
        con.name = IKNAME
        con.use_tail = True
        con.use_stretch = False
        con.target = armobj
        con.subtarget = "ikHindLimb3Right"
        con.pole_target = armobj
        con.pole_subtarget = "ikHindLimb2TargetRight"   
        con.chain_count = 2
        con.pole_angle = radians(-90)
        con.influence = 0

    pbone = pbones.get('HindLimb2Left')
    if pbone:

        pbone.lock_ik_z = True
        con = pbone.constraints.new("IK")
        con.name = IKNAME
        con.use_tail = True
        con.use_stretch = False
        con.target = armobj
        con.subtarget = "ikHindLimb3Left"
        con.pole_target = armobj
        con.pole_subtarget = "ikHindLimb2TargetLeft"   
        con.chain_count = 2
        con.pole_angle = radians(-90)
        con.influence = 0














    #

    #
    create_ik_linebone_cons(armobj, 'Elbow', 'Left')
    create_ik_linebone_cons(armobj, 'Elbow', 'Right')
    create_ik_linebone_cons(armobj, 'Knee', 'Left')
    create_ik_linebone_cons(armobj, 'Knee', 'Right')
    create_ik_linebone_cons(armobj, 'HindLimb2', 'Left')
    create_ik_linebone_cons(armobj, 'HindLimb2', 'Right')


    con = pbones["mPelvis"].constraints.new("COPY_LOCATION")
    con.name = COPY_LOCATION_NAME
    con.target = context.active_object
    con.subtarget = "Pelvis"
    con.influence = 1

    RotLocBones = getRotLocBoneSet(pbones, rigType)
    for b in [b for b in RotLocBones if b in pbones]:
        con = pbones[b].constraints.new("COPY_ROTATION")
        con.name = COPY_ROTATION_NAME
        con.target = context.active_object
        con.target_space = 'WORLD'
        con.owner_space = 'WORLD'
        con.subtarget = b[1:]
        con.influence = 1

        con = pbones[b].constraints.new("COPY_LOCATION")
        con.name = COPY_LOCATION_NAME
        con.target = context.active_object
        con.subtarget = b[1:]
        con.target_space = 'WORLD'
        con.owner_space = 'WORLD'
        con.influence = 1

    RotLocIK = getRotLocIKSet(rigType)
    for b1,b2 in RotLocIK:
        pbone = pbones.get(b1)
        if pbone:

            def data_path_to_IK(bone_name):
                bone = pbones[bone_name]
                con = rig.get_IK_constraint(bone)
                con_name = con.name if con else 'IK'
                return 'pose.bones["%s"].constraints["%s"].influence' % (bone_name, con_name)

            con = pbone.constraints.new("COPY_ROTATION")
            con.name = COPY_ROTATION_NAME
            con.target = context.active_object
            con.subtarget = b2
            con.target_space = 'WORLD'
            con.owner_space = 'WORLD'
            con.influence = 1

            fcurve = con.driver_add('influence')
            driver = fcurve.driver
            driver.type = 'MIN'

            v1 = driver.variables.new()
            v1.type = 'SINGLE_PROP'
            v1.name = 'hinge'

            t1 = v1.targets[0]
            t1.id = armobj

            v2 = driver.variables.new()
            v2.type = 'SINGLE_PROP'
            v2.name = 'ik'

            t2 = v2.targets[0]
            t2.id = armobj

            if b1 == "WristLeft":
                t1.data_path = 'IKSwitchesProp.IK_Wrist_Hinge_L'
                t2.data_path = data_path_to_IK("ElbowLeft")
            elif b1 == "WristRight":
                t1.data_path = 'IKSwitchesProp.IK_Wrist_Hinge_R'
                t2.data_path = data_path_to_IK("ElbowRight")
            elif b1 == "AnkleLeft":
                t1.data_path = 'IKSwitchesProp.IK_Ankle_Hinge_L'
                t2.data_path = data_path_to_IK("KneeLeft")
            elif b1 == "AnkleRight":
                t1.data_path = 'IKSwitchesProp.IK_Ankle_Hinge_R'
                t2.data_path = data_path_to_IK("KneeRight")
            elif b1 == "HindLimb3Left":
                t1.data_path = 'IKSwitchesProp.IK_HindLimb3_Hinge_L'
                t2.data_path = data_path_to_IK("HindLimb2Left")
            elif b1 == "HindLimb3Right":
                t1.data_path = 'IKSwitchesProp.IK_HindLimb3_Hinge_R'
                t2.data_path = data_path_to_IK("HindLimb2Right")

    create_targetless_ik(armobj, SKELETON)

    basic_eyes = ["Eye"]
    extended_eyes = ["Eye", "FaceEyeAlt"]
    eye_chains = basic_eyes if rigType=='BASIC' else extended_eyes
    for b in eye_chains:
        for symmetry in ["Left", "Right"]:
            name = "%s%s" % (b,symmetry)
            bone = pbones[name] if name in pbones else None
            if bone:
                con = bone.constraints.new("DAMPED_TRACK")
                con.target     = context.active_object
                con.subtarget  = "%sTarget" % b
                con.track_axis = "TRACK_Y"
                con.head_tail  = 0.0
            else:
                log.info("EyeBone %s is not in pbones of armature %s" % (name,armobj.name))
    armobj.IKSwitchesProp.Enable_Eyes=True
    if rigType == 'EXTENDED':
        create_hand_chain_controllers(armobj)
        create_face_controllers(armobj, "Face")
        armobj.IKSwitchesProp.Enable_AltEyes=True
        for bside in ['Left','Right']:
            Wrist = pbones.get("Wrist%s" % bside)
            if Wrist:
                HandThumb0 = pbones.get("%s%s" % ('HandThumb0',bside))
                ThumbController = pbones.get("%s%s" % ('ThumbController',bside))

                if ThumbController:
                    if HandThumb0:














                        for i in range(0,3):
                            HandThumb0.lock_location[i]=True
                            HandThumb0.lock_rotation[i]=True
                            HandThumb0.lock_scale[i]=True
                        HandThumb0.lock_rotation[2]=False

                    ThumbController.lock_rotation[0]=True
                    ThumbController.lock_rotation[2]=True
                    con = ThumbController.constraints.new("COPY_ROTATION")
                    con.name = COPY_ROTATION_NAME

                    util.set_con_axis(con, 0, True)
                    util.set_con_axis(con, 1, True)
                    util.set_con_axis(con, 2, True)

                    con.use_offset=True
                    con.target_space = 'LOCAL'
                    con.owner_space = 'LOCAL'
                    con.target = armobj
                    con.subtarget = Wrist.name
                    con.influence = 1


def create_targetless_ik(armobj, SKELETON):
    pbones = armobj.pose.bones
    rigType = SKELETON.rig_type
    boneset = SKELETON.bones











    chains =  getChainSet(rigType)















    for bone, vals in chains.items():
        bone = pbones.get(bone, None)
        if bone:
            if  bone.name.startswith("Hand"):
                continue # discard targetless IK for fingers
            bone['ik_count']     = vals[0]
            bone['ik_influence'] = vals[1]
            create_ik_targetless_cons(bone)
        else:
            log.info("Bone %s is not in pbones of armature %s" % (bone, armobj.name))


def create_ik_targetless_cons(bone):

    count = bone.get('ik_count')
    if count is None:
        count = 0

    influence = bone.get('ik_influence')
    if influence is None:
        influence = 0

    con = bone.constraints.new("IK")
    con.name = TARGETLESS_NAME
    con.use_tail = True
    con.use_stretch = False
    con.chain_count = count
    con.influence = influence
    return con

def remove_ik_targetless_cons(bone):
    con =  bone.constraints.get(TARGETLESS_NAME)
    if con:
         bone.constraints.remove(con)


def create_ik_linebone_cons(armobj, bname, side):
    pbones = armobj.pose.bones
    linebone = pbones.get('ik%sLine%s'%(bname,side))
    if linebone:
        target    = armobj
        subtarget = "m%s%s" % (bname, side)

        con = linebone.constraints.new("COPY_LOCATION")
        con.name = COPY_LOCATION_NAME
        con.target = target
        con.subtarget = subtarget
        con.influence = 1.0

        subtarget = "ik%sTarget%s" % (bname, side)
        targetbone = pbones[subtarget]
        rest_length=(targetbone.head - linebone.head).magnitude

        con = linebone.constraints.new("STRETCH_TO")
        con.name = STRETCHTO_NAME
        con.target = target
        con.subtarget = subtarget
        con.influence = 1.0
        con.rest_length = rest_length


def reset_rig(armobj):
    rigType = bpy.context.object.RigProp.RigType
    jointType = bpy.context.object.RigProp.JointType
    SKELETON = data.getSkeletonDefinition(rigType,jointType)
    BONES = SKELETON.bones
    omode = util.ensure_mode_is('EDIT')
    for b in armobj.data.edit_bones:
        for key in b.keys():
            del b[key]
        BONE = BONES.get(b.name)
        if BONE:
            init_meta_data(b, BONE)
        else:
            log.warning("No Metadata for bone %s" % b.name)        
    

if __name__ == '__main__':

    pass


classes = (

)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered create:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered create:%s" % cls)
