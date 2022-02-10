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

import bpy
import logging, importlib
from math import pi, sin, cos, radians
from mathutils import Euler

from .const import *
from . import util

log = logging.getLogger('avastar.init')


def circle(r=0.5, h=0.5, axis=True, steps=30):
    '''
    Generate the vertices and edges for a circle
    '''

    v = []
    for q in range(0, steps):
        v.append((r*cos(q*2*pi/float(steps)), h, r*sin(q*2*pi/float(steps))))
    e = []
    for i in range(len(v)-1):
        e.append((i, i+1))
    e.append((i+1, 0))

    if axis:
        v.append((0, 0, 0))
        v.append((0, 1, 0))
        e.append((i+2, i+3))

    return v, e


def createCustomShapes():
    #

    #









    custom_shape_collection = get_custom_shape_collection()

    name = "CustomShape_Line"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        edges = [(0, 1)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Origin"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(-0.435, 0.435, 0.0), (-0.512, 0.342, 0.0),
                 (-0.569, 0.235, 0.0), (-0.604, 0.120, 0.0),
                 (-0.120, 0.604, 0.0), (-0.235, 0.569, 0.0),
                 (-0.342, 0.512, 0.0), (-0.120, 0.788, 0.0),
                 (-0.788, 0.120, 0.0), (-0.243, 0.788, 0.0),
                 (-0.788, 0.243, 0.0), (0.000, 0.973, 0.0),
                 (-0.973, 0.000, 0.0)]
        verts = [(3*v[0], 3*v[1], 3*v[2]) for v in verts]
        edges = [(0, 1), (1, 2), (2, 3), (4, 5), (5, 6),
                 (0, 6), (4, 7), (3, 8), (7, 9), (8, 10),
                 (9, 11), (10, 12)]

        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("Mirror", "MIRROR")
        util.set_mod_axis(mod, 0, True)
        util.set_mod_axis(mod, 1, True)

    name = "CustomShape_Head"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(-1.89, 1.1, -0.09), (-1.9, 0.8, -0.09),
                 (-1.1, 0.8, -1.8), (0.92, 0.8, -1.8),
                 (1.7, 0.8, -0.09), (1.71, 1.1, -0.09),
                 (1.7, 1.41, -0.09), (0.92, 1.41, -1.8),
                 (-1.1, 1.41, -1.8), (-1.89, 1.41, -0.09)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                 (6, 7), (7, 8), (8, 9), (0, 9)]

        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 2

    name = "CustomShape_Collar"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(1.52, 1.1, 0.0), (1.52, 0.92, 0.0), (0.85, 0.92, 1.44),
                 (-0.85, 0.92, 1.44), (-1.52, 0.92, 0.0), (-1.53, 1.1, 0.0),
                 (-1.52, 1.29, 0.0), (-0.85, 1.29, 1.44), (0.85, 1.29, 1.44),
                 (1.52, 1.29, 0.0)] 
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                 (6, 7), (7, 8), (8, 9), (0, 9)]

        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 2

    name = "CustomShape_COG"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(0.3, 1.54, 0.0), (0.29, 1.66, 0.06), (0.27, 1.54, 0.12), (0.24, 1.66, 0.18), 
        (0.2, 1.54, 0.22), (0.15, 1.66, 0.26), (0.09, 1.54, 0.29), (0.03, 1.66, 0.3), 
        (-0.03, 1.54, 0.3), (-0.09, 1.66, 0.29), (-0.15, 1.54, 0.26), (-0.2, 1.66, 0.22), 
        (-0.24, 1.54, 0.18), (-0.27, 1.66, 0.12), (-0.29, 1.54, 0.06), (-0.3, 1.66, 0.0), 
        (-0.29, 1.54, -0.06), (-0.27, 1.66, -0.12), (-0.24, 1.54, -0.18), (-0.2, 1.66, -0.22), 
        (-0.15, 1.54, -0.26), (-0.09, 1.66, -0.29), (-0.03, 1.54, -0.3), (0.03, 1.66, -0.3), 
        (0.09, 1.54, -0.29), (0.15, 1.66, -0.26), (0.2, 1.54, -0.22), (0.24, 1.66, -0.18), 
        (0.27, 1.54, -0.12), (0.29, 1.66, -0.06), (0.0, 0.0, 0.0), (0.0, 1.62, 0.0), 
        (0.29, 1.58, -0.06), (0.27, 1.7, -0.12), (0.24, 1.58, -0.18), (0.2, 1.7, -0.22), 
        (0.15, 1.58, -0.26), (0.09, 1.7, -0.29), (0.03, 1.58, -0.3), (-0.03, 1.7, -0.3), 
        (-0.09, 1.58, -0.29), (-0.15, 1.7, -0.26), (-0.2, 1.58, -0.22), (-0.24, 1.7, -0.18), 
        (-0.27, 1.58, -0.12), (-0.29, 1.7, -0.06), (-0.3, 1.58, 0.0), (-0.29, 1.7, 0.06), 
        (-0.27, 1.58, 0.12), (-0.24, 1.7, 0.18), (-0.2, 1.58, 0.22), (-0.15, 1.7, 0.26), 
        (-0.09, 1.58, 0.29), (-0.03, 1.7, 0.3), (0.03, 1.58, 0.3), (0.09, 1.7, 0.29), 
        (0.15, 1.58, 0.26), (0.2, 1.7, 0.22), (0.24, 1.58, 0.18), (0.27, 1.7, 0.12), 
        (0.29, 1.58, 0.06), (0.3, 1.7, 0.0), (0.0, 0.69, 0.0), (0.0, 1.53, 0.0)] 
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), 
        (10, 11), (11, 12), (12, 13), (13, 14), (14, 15), (15, 16), (16, 17), (17, 18), (18, 19), 
        (19, 20), (20, 21), (21, 22), (22, 23), (23, 24), (24, 25), (25, 26), (26, 27), (27, 28), 
        (28, 29), (0, 29), (32, 61), (32, 33), (33, 34), (34, 35), (35, 36), (36, 37), (37, 38), 
        (38, 39), (39, 40), (40, 41), (41, 42), (42, 43), (43, 44), (44, 45), (45, 46), (46, 47), 
        (47, 48), (48, 49), (49, 50), (50, 51), (51, 52), (52, 53), (53, 54), (54, 55), (55, 56), 
        (56, 57), (57, 58), (58, 59), (59, 60), (60, 61), (30, 62), (31, 63), (62, 63)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 2

    name = "CustomShape_Circle01"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts, edges = circle(r=0.1)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Circle02"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        obj.rotation_euler=(1.5708, 0, 0)
        verts, edges = circle(r=0.2)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Circle03"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts, edges = circle(r=0.3)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Circle05"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts, edges = circle(r=0.5)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Circle10"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts, edges = circle(r=1.0)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Torso"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts, edges = circle(r=1.2)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Neck"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts, edges = circle(r=1.3)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Pelvis"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts, edges = circle(r=3.2)
        mesh.from_pydata(verts, edges, [])
        mesh.update()

    name = "CustomShape_Target"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(0.2, 0.0, 0.0), (0.0, -0.2, 0.0), (0.0, 0.0, 0.2)]
        edges = [(0,1), (1,2), (2,0)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("Mirror", "MIRROR")
        util.set_mod_axis(mod, 0, True)
        util.set_mod_axis(mod, 1, True)
        util.set_mod_axis(mod, 2, True)
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 3

    name = "CustomShape_Tinker"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(0.6, 0.0, 0.0), (0.0, -0.6, 0.0), (0.0, 0.0, 0.6)]
        edges = [(0,1), (1,2), (2,0)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("Mirror", "MIRROR")
        util.set_mod_axis(mod, 0, True)
        util.set_mod_axis(mod, 1, True)
        util.set_mod_axis(mod, 2, True)
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 3

    name = "CustomShape_Face"
    if name not in bpy.data.objects:    
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(0.0, 1.0149999856948853, 0.0), (0.07199999690055847, 0.9850000143051147, 0.0), 
                 (0.0, 1.0010000467300415, 0.04399999976158142), (0.0, 0.9850000143051147, 0.07199999690055847), 
                 (0.0430000014603138, 0.9850000143051147, 0.04540000110864639), (0.03319999948143959, 1.0049999952316284, 0.0),
                 (0.02199999988079071, 1.0010000467300415, 0.020600000396370888)]
        edges = [(3, 2), (5, 1), (4, 3), (1, 4), (4, 6), (2, 0), (0, 5), (5, 6), (2, 6)]

        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("Mirror", "MIRROR")
        mod.use_axis[0] = True
        mod.use_axis[1] = False
        mod.use_axis[2] = True
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 3

    name = "CustomShape_Volume"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(0.2, 0.0, 0.0), (0.0, -0.5, 0.0), (0.0, 0.0, 0.2)]
        edges = [(0,1), (1,2), (2,0)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("Mirror", "MIRROR")
        util.set_mod_axis(mod, 0, True)
        util.set_mod_axis(mod, 1, True)
        util.set_mod_axis(mod, 2, True)



    name = "CustomShape_Pinch"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [
                 (0.0, 0.0883883461356163, 0.0883883461356163),    (-0.08838833123445511, 0.0, 0.0883883461356163), 
                 (-0.04783540591597557, 0.0, 0.11548495292663574), (0.0, -0.0883883461356163, 0.0883883461356163), 
                 (0.0, 0.0, 0.125),                                (-0.047835420817136765, 0.11548493802547455, 0.0), 
                 (-0.08838833123445511, 0.0883883610367775, 0.0),  (-0.11548492312431335, 0.04783545061945915, 0.0), 
                 (0.0, 0.125, 0.0),                                (-0.047835420817136765, -0.11548493802547455, 0.0), 
                 (-0.08838833123445511, -0.0883883610367775, 0.0), (-0.11548492312431335, -0.04783545061945915, 0.0), 
                 (-0.125, 0.0, 0.0),                               (0.0, -0.125, 0.0)
                ]
        edges = [(4, 0), (2, 1), (5, 8), (6, 5), (7, 6), (12, 7),
                 (2, 4), (1, 6), (0, 6), (0, 1), (3, 13), (4, 3),
                 (10, 9), (11, 10), (12, 11), (13, 9), (1, 10),
                 (3, 10), (3, 1), (0, 8), (1, 12)]
        faces = []#[(1, 0, 6), (0, 1, 2, 4), (9, 13, 3, 10), (1, 10, 3), (3, 4, 2, 1), (5, 6, 0, 8), (7, 12, 1, 6), (11, 10, 1, 12)]
        mesh.from_pydata(verts, edges, faces)
        mesh.update()
        obj.show_wire = True
        mod = obj.modifiers.new("Mirror", "MIRROR")
        util.set_mod_axis(mod, 0, True)
        util.set_mod_axis(mod, 1, True)
        util.set_mod_axis(mod, 2, True)
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 1
    
    name = "CustomShape_Cube"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [( 0.1,  0.1, -0.1),
                 ( 0.1, -0.1, -0.1),
                 (-0.1, -0.1, -0.1),
                 (-0.1,  0.1, -0.1),
                 ( 0.1,  0.1,  0.1),
                 ( 0.1, -0.1,  0.1),
                 (-0.1, -0.1,  0.1),
                 (-0.1, 00.1,  0.1)
                ]
        edges = [(0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7)]
        faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)]
        mesh.from_pydata(verts, edges, faces)
        mesh.update()
        obj.show_wire = False

    name = "CustomShape_Lip"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(-1.2, -0.4, 0.0), (0.0, 0.12, -1.2), (-0.72, -0.08, -0.8), (-0.4, 0.04, -1.04), (-1.08, -0.24, -0.48)]
        edges = [(4, 0), (3, 2), (1, 3), (2, 4)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        obj.show_wire = True
        mod = obj.modifiers.new("Mirror", "MIRROR")
        util.set_mod_axis(mod, 0, True)
        util.set_mod_axis(mod, 2, True)
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 1

    name = "CustomShape_Hand"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(-0.52, 0.01, -0.23), (0.52, 0.01, -0.23), (-0.69, 1.0, -0.23), (0.71, 1.0, -0.23), 
                (-0.69, 2.12, -0.23), (-0.69, 0.32, 0.39), (0.71, 0.32, 0.39), (0.71, 2.12, -0.23), 
                (0.62, 2.03, -0.21), (0.62, 0.38, 0.33), (-0.6, 0.38, 0.33), (-0.6, 2.03, -0.21), 
                (0.62, 0.97, -0.21), (-0.6, 0.97, -0.21), (0.46, 0.1, -0.21), (-0.46, 0.1, -0.21)] 
        edges = [(0, 5), (0, 2), (1, 6), (1, 3), (2, 4), (3, 7), (4, 7), (5, 6), (9, 10), (8, 11), 
                (8, 12), (11, 13), (12, 14), (9, 14), (13, 15), (10, 15)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 3

    name = "CustomShape_Foot"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(0.8, 0.0, -2.58), (0.8, 0.0, 1.0), (-0.78, 0.0, 1.0), (-0.78, 0.0, -2.58), (0.8, 0.0, -1.46), 
                 (-0.78, 0.0, -1.46), (0.8, 0.0, 0.2), (-0.78, 0.0, 0.2), (-0.7, 0.0, 0.09), (0.72, 0.0, 0.09), 
                 (-0.7, 0.0, -1.39), (0.72, 0.0, -1.39), (-0.7, 0.0, -2.48), (-0.7, 0.0, 0.89), 
                 (0.72, 0.0, 0.89), (0.72, 0.0, -2.48)] 
        edges = [(1, 2), (0, 3), (0, 4), (3, 5), (4, 6), (1, 6), (5, 7), (2, 7), (8, 13), (8, 10), (9, 14), 
                 (9, 11), (10, 12), (11, 15), (12, 15), (13, 14)]    
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 3

    name = "CustomShape_FootPivot"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(-0.63, 0.0, -0.02), (-0.62, 0.0, -0.16), (0.62, 0.0, -0.16), (0.63, 0.0, -0.02), 
                (-0.71, -0.25, -0.09), (0.71, -0.25, -0.09), (-0.71, 0.0, -0.16), (0.71, 0.0, -0.16), 
                (0.71, 0.0, -0.02), (-0.71, 0.0, -0.02), (-0.0, 0.0, -0.02), (-0.0, 0.0, -0.16), (0.07, 0.0, -0.09), (-0.07, 0.0, -0.09)] 
        edges = [(1, 2), (0, 3), (1, 6), (4, 6), (2, 7), (5, 7), (3, 8), (5, 8), (0, 9), (4, 9), 
                (10, 12), (10, 13), (11, 12), (11, 13)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 2

    name = "CustomShape_EyeTarget"
    if name not in custom_shape_collection.objects:
        obj, mesh = add_custom_shape(name, custom_shape_collection)
        verts = [(1.0, 0.0, 0.0), (0.55, 0.44, -0.0), (0.12, 0.09, -0.0), (0.12, -0.09, 0.0), (0.55, -0.44, 0.0), 
                (0.55, -0.31, 0.0), (0.25, 0.0, 0.0), (0.55, 0.31, -0.0), (0.86, 0.0, 0.0), (0.0, 0.09, -0.0), 
                (0.0, -0.09, 0.0), (-0.86, 0.0, -0.0), (-0.55, 0.31, -0.0), (-0.25, 0.0, -0.0), (-0.55, -0.31, -0.0), 
                (-0.55, -0.44, -0.0), (-0.12, -0.09, -0.0), (-0.12, 0.09, -0.0), (-0.55, 0.44, -0.0), (-0.99, 0.0, -0.0)] 
        edges = [(2, 9), (3, 10), (5, 8), (5, 6), (6, 7), (7, 8), (1, 2), (0, 1), (0, 4), (3, 4), (15, 16), 
                (15, 19), (18, 19), (17, 18), (11, 12), (12, 13), (13, 14), (11, 14), (10, 16), (9, 17)]
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        mod = obj.modifiers.new("subsurf", 'SUBSURF')
        mod.levels = 2

def add_custom_shape(name, collection):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.use_fake_user=True
    log.debug("Added custom shape [%s]" % name)
    return obj, mesh

def get_custom_shape_collection():
    collection = bpy.data.collections.get(AVASTAR_CUSTOM_SHAPES)
    if not collection:
        collection = bpy.data.collections.new(AVASTAR_CUSTOM_SHAPES)
        collection.hide_render=True
        collection.hide_select=True
        collection.hide_viewport=True
        collection.use_fake_user=True
    return collection
