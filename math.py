### Copyright     2020 The Machinimatrix Team
###
### This file is part of Avastar
###
### The module has been created based on this document:
### A Beginners Guide to Dual-Quaternions:
### http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.407.9047
###
### BEGIN GPL LICENSE BLOCK #####
#




#




#



#
#
from mathutils import Vector, Matrix, Euler, Quaternion

class DualQuaternion():
    quat_real : Quaternion
    quat_dual : Quaternion
    def __init__(self, *args):

        if len(args) == 0: #DualQuaternion()
            self.quat_real = Quaternion((1, 0,0,0))
            self.quat_dual = Quaternion((0, 0,0,0))
        elif len(args) == 1:
            if isinstance(args[0], Quaternion): #DualQuaternion(Quaternion)
                self.quat_real = args[0].copy()
                self.quat_dual = Quaternion((0, 0,0,0))
            else: #DualQuaternion(Vector)
                self.quat_real = Quaternion((1, 0,0,0))
                self.quat_dual = Quaternion((0, *args[0] * 0.5))
        else:
            if isinstance(args[0], Quaternion):
                if isinstance(args[1], Quaternion): #DualQuaternion(Quaternion, Quaternion)
                    self.quat_real = args[0].copy()
                    self.quat_dual = args[1].copy()
                    self.quat_real.normalize()
                else: #DualQuaternion(Quaternion, Vector)
                    self.quat_real = args[0].copy()
                    self.quat_real.normalize()
                    self.quat_dual = (Quaternion((0, *args[1])) @ self.quat_real) * 0.5
            else:
                raise #Illegal combination of constructor parameters


    def __str__(self):
        return "real: %s\ndual:%s" % (self.quat_real, self.quat_dual)

    def __repr__(self):
        return "DualQuaternion( %s, %s )" % (Quaternion.__repr__(self.quat_real), Quaternion.__repr__(self.quat_dual))

    @staticmethod
    def dot(dqa, dqb):
        return Quaternion.dot( dqa.quat_real, dqb.quat_real )


    def scaled(self, factor):
        dqa = DualQuaternion(self.quat_real, self.quat_dual)
        dqa.scale(factor)
        return dqa


    def scale(self, factor):
        self.quat_real *= factor
        self.quat_dual *= factor


    def normalized(self):
        dqa = DualQuaternion(self.quat_real, self.quat_dual)
        dqa.normalize()
        return dqa


    def normalize(self):
        mag = Quaternion.dot( self.quat_real, self.quat_real )
        if mag > 0.000001:
            self.quat_real *= 1.0 / mag
            self.quat_dual *= 1.0 / mag
        else:
            raise


    def conjugated(self):
        dqa = DualQuaternion(self.quat_real, self.quat_dual)
        dqa.conjugate()
        return dqa


    def conjugate(self):
        Quaternion.conjugate( self.quat_real )
        Quaternion.conjugate( self.quat_dual )


    def __matmul__(self, rhs):
        quatr = rhs.quat_real @ self.quat_real
        quatd = rhs.quat_dual @ self.quat_real + rhs.quat_real @ self.quat_dual
        return DualQuaternion(quatr, quatd)


    @staticmethod
    def __add__(self, rhs):
        quatr = self.quat_real + rhs.quat_real
        quatd = self.quat_dual + rhs.quat_dual
        return DualQuaternion(quatr, quatd)


    def to_rotation(self):
        return self.quat_real


    def to_translation(self):
        t = (self.quat_dual * 2) @ Quaternion.conjugated(self.quat_real)
        return Vector((t.x, t.y, t.z))


    def to_matrix(self):
        q = DualQuaternion.normalized( self )
        M = Matrix()
        w = q.quat_real.w
        x = q.quat_real.x
        y = q.quat_real.y
        z = q.quat_real.z

        M[0][0] = w*w + x*x - y*y - z*z
        M[1][0] = 2*x*y + 2*w*z
        M[2][0] = 2*x*z - 2*w*y
        M[0][1] = 2*x*y - 2*w*z
        M[1][1] = w*w + y*y - x*x - z*z
        M[2][1] = 2*y*z + 2*w*x
        M[0][2] = 2*x*z + 2*w*y
        M[1][2] = 2*y*z - 2*w*x
        M[2][2] = w*w + z*z - x*x - y*y

        t = (q.quat_dual * 2) @ Quaternion.conjugated( q.quat_real)
        M[0][3] = t.x
        M[1][3] = t.y
        M[2][3] = t.z
        return M
