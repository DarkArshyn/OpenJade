"""Bounded reconstruction of observed camera operations, not active-menu state."""
import math
import numpy as np


def converted_basis(source_basis):
    """Axis changes in 00438790 before its matrix flag/normalization helper."""
    basis=np.asarray(source_basis,dtype=float)
    if basis.shape!=(3,3) or not np.isfinite(basis).all():raise ValueError('Invalid basis')
    return -basis[[0,2,1]]


def view_matrix(basis,position):
    """00437F70: row-vector rigid inverse; caller supplies camera-block basis."""
    basis=np.asarray(basis,dtype=float);position=np.asarray(position,dtype=float)
    if basis.shape!=(3,3) or position.shape!=(3,) or not np.isfinite(basis).all() or not np.isfinite(position).all():raise ValueError('Invalid camera transform')
    if not np.allclose(basis@basis.T,np.eye(3),atol=1e-5):raise ValueError('Rigid basis required')
    result=np.eye(4);result[:3,:3]=basis.T;result[3,:3]=-position@basis.T
    return result


def projection_matrix(angle_radians,ratio,depth_a,depth_b,axis_flag=False):
    """00660690 coefficients; runtime aspect and depth fields remain caller inputs."""
    values=(angle_radians,ratio,depth_a,depth_b)
    if not all(math.isfinite(v) for v in values) or not 0<angle_radians<math.pi or ratio<=0 or depth_b==depth_a:raise ValueError('Invalid projection inputs')
    cotangent=1/math.tan(angle_radians/2)
    result=np.zeros((4,4))
    result[0,0]=cotangent*ratio if axis_flag else cotangent
    result[1,1]=-cotangent if axis_flag else -cotangent/ratio
    result[2,2]=(depth_a+depth_b)/(depth_b-depth_a)
    result[2,3]=1
    result[3,2]=float(np.float32(-.05))
    return result


def projection_angles(angle_radians, width, height, context_flags=0, ratio_mode=2, custom_ratio=1.0):
    """Expose 00660690 axis angles for explicit context inputs, not live state."""
    if not all(math.isfinite(v) and v > 0 for v in (width,height)):
        raise ValueError('Invalid viewport dimensions')
    ratio=height/width if 1 <= ratio_mode <= 6 else custom_ratio
    matrix=projection_matrix(angle_radians,ratio,1,1000,bool(context_flags & 4))
    return dict(horizontal_degrees=math.degrees(2*math.atan(1/abs(matrix[0,0]))),
                vertical_degrees=math.degrees(2*math.atan(1/abs(matrix[1,1]))),
                ratio=ratio,axis='vertical' if context_flags & 4 else 'horizontal')
