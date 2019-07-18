"""Tools for managing the base transform node class."""

from maya import cmds

from psyhive.utils import get_single
from maya_psyhive.utils import add_to_grp, set_col

from maya_psyhive.open_maya.base_node import BaseNode
from maya_psyhive.open_maya.plug import HPlug
from maya_psyhive.open_maya.point import ORIGIN


class BaseTransform(BaseNode):
    """Base class for any transform object."""

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): tranform node name
        """
        from maya_psyhive import open_maya as hom
        super(BaseTransform, self).__init__(node)

        # Get shape (if any)
        _shps = cmds.listRelatives(self.node, shapes=True) or []
        _shp = get_single([str(_shp) for _shp in _shps], catch=True)
        self.shp = hom.HFnDependencyNode(_shp) if _shp else None

        # Create plugs
        for _param in 'trs':
            for _axis in 'xyz':
                _attr = _param+_axis
                _plug = HPlug(self.node+'.'+_attr)
                setattr(self, _attr, _plug)
        self.translate = HPlug(self.node+'.translate')
        self.rotate = HPlug(self.node+'.rotate')
        self.scale = HPlug(self.node+'.scale')
        self.visibility = HPlug(self.node+'.visibility')

    def add_u_scale(self):
        """Add uniform scale attribute to control scale xyz atts.

        Returns:
            (HPlug): uniform scale
        """
        _u_scale = self.create_attr('uScale', 1.0)
        _u_scale.connect(self.scale, axes='XYZ')
        return _u_scale

    def add_to_grp(self, grp):
        """Add this node to a group, creating it if required.

        Args:
            grp (str): group to add to
        """
        add_to_grp(self, grp)

    def aim_constraint(self, *args, **kwargs):
        """Aim constrain a node to this node.

        Returns:
            (HFnTransform): aim constraint
        """
        from maya_psyhive import open_maya as hom
        _constr = cmds.aimConstraint(self, *args, **kwargs)[0]
        return hom.HFnTransform(_constr)

    def bbox(self):
        """Get this node's bounding box.

        Returns:
            (HBoundingBox): bounding box
        """
        from maya_psyhive import open_maya as hom
        return hom.get_bbox(str(self))

    def delete_history(self):
        """Delete this node's history."""
        cmds.delete(self, constructionHistory=1)

    def flush(self):
        """Flush this object's transformations.

        This means resetting the pivot, freezing transform and
        deleting history.
        """
        self.set_pivot()
        self.freeze_transforms()
        self.delete_history()

    def freeze_transforms(self, translate=True, rotate=True, scale=True):
        """Freeze transforms on this node.

        Args:
            translate (bool): freeze translation
            rotate (bool): freeze rotation
            scale (bool): freeze scale
        """
        _kwargs = dict(
            apply=True, translate=translate, rotate=rotate, scale=scale,
            normal=False, preserveNormals=True)
        cmds.makeIdentity(self, **_kwargs)

    def hide(self):
        """Hide this node."""
        self.visibility.set_val(False)

    def get_p(self):
        """Get position of this transform.

        Returns:
            (HPoint): position
        """
        from maya_psyhive import open_maya as hom
        return hom.get_p(self)

    def get_m(self):
        """Get matrix of this object's transform.

        Returns:
            (HMatrix): matrix
        """
        from maya_psyhive import open_maya as hom
        return hom.get_m(self)

    def parent(self, *args, **kwargs):
        """Wrapper for cmds.parent command."""
        cmds.parent(self, *args, **kwargs)

    def parent_constraint(self, *args, **kwargs):
        """Parent constrain a node to this node.

        Returns:
            (HFnTransform): parent constraint
        """
        from maya_psyhive import open_maya as hom
        _constr = cmds.parentConstraint(self, *args, **kwargs)[0]
        return hom.HFnTransform(_constr)

    def point_constraint(self, *args, **kwargs):
        """Point constrain a node to this node.

        Returns:
            (HFnTransform): point constraint
        """
        from maya_psyhive import open_maya as hom
        _constr = cmds.pointConstraint(self, *args, **kwargs)[0]
        return hom.HFnTransform(_constr)

    def set_col(self, col):
        """Set colour of this node in maya viewport.

        Args:
            col (str): colour to apply
        """
        set_col(str(self), col)

    def set_pivot(self, pos=None, scale=True, rotate=True):
        """Set this node's scale/rotate pivot.

        Args:
            pos (HPoint): position (if not origin)
            scale (bool): apply to scale pivot
            rotate (bool): apply to rotate pivot
        """
        _pos = pos or ORIGIN
        for _tgl, _plug in [
                (scale, self.plug('scalePivot')),
                (rotate, self.plug('rotatePivot'))]:
            if _tgl:
                cmds.move(_pos[0], _pos[1], _pos[2], _plug)

    def u_scale(self, scale):
        """Apply a uniform scale to this node.

        Args:
            scale (float): scale value
        """
        self.scale.set_val([scale, scale, scale])