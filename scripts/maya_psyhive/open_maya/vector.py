"""Tools for managing 3d vectors."""

from maya import cmds
from maya.api import OpenMaya as om

from maya_psyhive.open_maya.utils import cast_result
from maya_psyhive.open_maya.base_array3 import BaseArray3
from maya_psyhive.utils import set_col, get_unique


class HVector(BaseArray3, om.MVector):
    """Represents a 3d vector."""

    __mul__ = cast_result(om.MVector.__mul__)
    __neg__ = cast_result(om.MVector.__neg__)
    __xor__ = cast_result(om.MVector.__xor__)

    def as_mtx(self):
        """Get this vector as a transformation matrix.

        Returns:
            (HMatrix): matrix
        """
        from maya_psyhive import open_maya as hom
        _vals = list(hom.HMatrix().to_tuple())
        for _idx in range(3):
            _vals[12+_idx] = self[_idx]
        return hom.HMatrix(_vals)

    def build_crv(self, pos=None, col=None, name='HVector'):
        """Build a curve to display this vector.

        Args:
            pos (HPoint): start point of vector
            col (str): vector colour
            name (str): name for vector geo
        """
        from maya_psyhive import open_maya as hom
        _pos = pos or HVector()
        _end = _pos+self
        _crv = cmds.curve(
            point=[_pos.to_tuple(), _end.to_tuple()],
            degree=1, name=get_unique(name))
        if col:
            set_col(_crv, col)
        return hom.HFnNurbsCurve(_crv)

    def normalized(self):
        """Get the normalized version of this vector."""
        _dup = HVector(self)
        _dup.normalize()
        return _dup


X_AXIS = HVector(1, 0, 0)
Y_AXIS = HVector(0, 1, 0)
Z_AXIS = HVector(0, 0, 1)
