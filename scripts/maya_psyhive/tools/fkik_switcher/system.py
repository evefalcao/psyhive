"""Tools for switching between FK and IK.

The switch key option means:
    - in the case of a single frame switch: add a keyframe on the frame
      before switching
    - in the case of a range switch: add keyframes on the frames before
      and after the switch range

A range switch should key on the start and end frames, and then also any
of the frames between if they are already keyed.

If Elbow/Knee offset is applied on the IK ctrl, this is reset when
reverting to IK.
"""

from maya import cmds, mel

from psyhive.utils import get_single, store_result, lprint

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import single_undo, restore_sel


class _FkIkSystem(object):
    """Represents an FK/IK system."""

    def __init__(self, rig, side='Lf', limb='arm'):
        """Constructor.

        Args:
            rig (FileRef): rig
            side (str): which side (Lf/Rt)
            limb (str): which limb (arm/leg)
        """
        if side not in ['Lf', 'Rt']:
            raise ValueError(side)
        if limb not in ['arm', 'leg']:
            raise ValueError(side)

        self.rig = rig
        self.side = side
        self.limb = limb

        _names = {
            'side': side,
            'limb': limb,
            'gimbal': {'arm': 'wrist', 'leg': 'ankle'}[limb],
            'offset': {'arm': 'Elbow', 'leg': 'Knee'}[limb]}
        self.fk1 = rig.get_node('{side}_{limb}Fk_1_Ctrl'.format(**_names))
        self.fk2 = rig.get_node('{side}_{limb}Fk_2_Ctrl'.format(**_names))
        self.fk3 = rig.get_node('{side}_{limb}Fk_3_Ctrl'.format(**_names))

        self.ik_ = rig.get_node('{side}_{limb}Ik_Ctrl'.format(**_names))
        self.ik_pole = rig.get_node('{side}_{limb}Pole_Ctrl'.format(**_names))
        self.ik_pole_rp = self.ik_pole+'.rotatePivot'
        self.ik_offs = '{}.{offset}_Offset'.format(self.ik_, **_names)

        self.fk2_jnt = rig.get_node('{side}_{limb}Bnd_2_Jnt'.format(**_names))
        self.gimbal = rig.get_node(
            '{side}_{gimbal}Gimbal_Ctrl'.format(**_names))

    def apply_fk_to_ik(
            self, pole_vect_depth=10.0, build_tmp_geo=False, apply_=True,
            verbose=1):
        """Apply fk to ik.

        First the pole vector is calculated by extending a line from the
        elbow joint in the direction of the cross product of the limb
        vector (fk1 to fk3) and the limb bend.

        The ik joint is then moved to the position of the fk3 control.

        The arm/knee offset is reset on apply.

        Args:
            pole_vect_depth (float): distance of pole vector from fk2
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply the update to gimbal ctrl
            verbose (int): print process data
        """
        lprint('APPLYING FK -> IK', verbose=verbose)

        # Calculate pole pos
        _limb_v = hom.get_p(self.fk3) - hom.get_p(self.fk1)
        if self.limb == 'arm':
            _limb_bend = -hom.get_m(self.fk2).ly_().normalized()
        elif self.limb == 'leg':
            _limb_bend = hom.get_m(self.fk2).lx_().normalized()
        else:
            raise ValueError(self.limb)
        _pole_dir = (_limb_v ^ _limb_bend).normalized()
        _pole_p = hom.get_p(self.fk2) + _pole_dir*pole_vect_depth

        # Read fk3 mtx
        _fk3_mtx = hom.get_m(self.fk3)

        if build_tmp_geo:
            _limb_v.build_crv(hom.get_p(self.fk1), name='limb_v')
            _limb_bend.build_crv(hom.get_p(self.fk2), name='limb_bend')
            _pole_dir.build_crv(hom.get_p(self.fk2), name='pole_dir')
            _pole_p.build_loc(name='pole')
            _fk3_mtx.build_geo(name='fk3')
            hom.get_m(self.ik_).build_geo(name='ik')

        # Apply vals to ik ctrls
        _fk3_mtx.apply_to(self.ik_)
        if self.side == 'Rt':
            cmds.rotate(
                180, 0, 0, self.ik_, relative=True, objectSpace=True,
                forceOrderXYZ=True)
        _pole_p.apply_to(self.ik_pole, use_constraint=True)
        cmds.setAttr(self.ik_offs, 0)
        if apply_:
            cmds.setAttr(self.gimbal+'.FK_IK', 1)
            lprint('SET', self.ik_, 'TO IK', verbose=verbose)

    def apply_ik_to_fk(self, build_tmp_geo=False, apply_=True, verbose=1):
        """Apply ik to fk.

        Args:
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply update to gimbal ctrl
            verbose (int): print process data
        """
        lprint('APPLYING IK -> FK', verbose=verbose)

        # Position fk1
        _upper_v = hom.get_p(self.fk2_jnt) - hom.get_p(self.fk1)
        _pole_v = hom.get_p(self.ik_pole_rp) - hom.get_p(self.fk1)
        if self.limb == 'arm':
            _lx = _upper_v.normalized()
            if self.side == 'Rt':
                _lx = -_lx
            _ly = (_upper_v ^ _pole_v).normalized()
        elif self.limb == 'leg':
            _ly = -_upper_v.normalized()
            if self.side == 'Rt':
                _ly = -_ly
            _lx = -(_upper_v ^ _pole_v).normalized()
        else:
            raise ValueError(self.limb)
        _fk1_mtx = hom.axes_to_m(
            pos=hom.get_p(self.fk1), lx_=_lx, ly_=_ly)
        if build_tmp_geo:
            hom.get_m(self.fk1).build_geo(name='fk1_old')
            _fk1_mtx.build_geo(name='fk1_new')
            _pole_v.build_crv(hom.get_p(self.fk1), name='fk1_to_pole')
            hom.get_p(self.ik_pole_rp).build_loc(name='pole')
        _fk1_mtx.apply_to(self.fk1)
        del _lx, _ly, _pole_v, _upper_v

        # Position fk2
        _lower_v = hom.get_p(self.ik_) - hom.get_p(self.fk2_jnt)
        _pole_v = hom.get_p(self.ik_pole_rp) - hom.get_p(self.fk2_jnt)
        if self.limb == 'arm':
            _lx = _lower_v.normalized()
            _ly = (_lx ^ _pole_v).normalized()
            if self.side == 'Rt':
                _lx = -_lx
        elif self.limb == 'leg':
            _ly = -_lower_v.normalized()
            if self.side == 'Rt':
                _ly = -_ly
            _lx = (_ly ^ _pole_v).normalized()
            if self.side == 'Rt':
                _lx = -_lx
        else:
            raise ValueError(self.limb)
        _fk2_mtx = hom.axes_to_m(
            pos=hom.get_p(self.fk2), lx_=_lx, ly_=_ly)
        if build_tmp_geo:
            _lower_v.build_crv(hom.get_p(self.fk2), name='lower')
            _pole_v.build_crv(hom.get_p(self.fk2), name='fk2_to_pole')
            hom.get_m(self.fk2).build_geo(name='fk2_old')
            _fk2_mtx.build_geo(name='fk2_new')
        _fk2_mtx.apply_to(self.fk2)
        del _lx, _ly, _lower_v, _pole_v

        # Position fk3
        hom.get_m(self.ik_).apply_to(self.fk3)
        if self.side == 'Rt':
            cmds.rotate(
                180, 0, 0, self.fk3, relative=True, objectSpace=True,
                forceOrderXYZ=True)
        if apply_:
            cmds.setAttr(self.gimbal+'.FK_IK', 0)
            lprint('SET', self.ik_, 'TO FK', verbose=verbose)

    @single_undo
    @restore_sel
    def exec_switch_and_key(
            self, switch_mode, key_mode, build_tmp_geo=False,
            switch_key=False, verbose=1):
        """Execute fk/ik switch and key option.

        Args:
            switch_mode (str): fk/ik switch mode
            key_mode (str): key mode
            build_tmp_geo (bool): build temp geo
            switch_key (bool): add key(s) on switch
            verbose (int): print process data
        """

        # Read fn + trg ctrls
        if switch_mode == 'fk_to_ik':
            _fn = self.apply_fk_to_ik
        elif switch_mode == 'ik_to_fk':
            _fn = self.apply_ik_to_fk
        else:
            raise ValueError(switch_mode)

        # Apply pre frame option
        if key_mode in ['none']:
            pass
        elif key_mode == 'timeline':
            self._exec_switch_and_key_over_timeline(
                switch_mode=switch_mode, switch_key=switch_key)
            return
        elif key_mode == 'frame':
            if switch_key:
                _frame = cmds.currentTime(query=True)
                cmds.setKeyframe(self.get_key_attrs())
                cmds.currentTime(_frame-1)
                cmds.setKeyframe(self.get_key_attrs())
                cmds.currentTime(_frame)
        else:
            raise ValueError(key_mode)

        # Execute the switch
        _fn(build_tmp_geo=build_tmp_geo, verbose=verbose)

        # Apply post frame option
        if key_mode == 'none':
            pass
        elif key_mode == 'frame':
            cmds.setKeyframe(self.get_key_attrs())
        else:
            raise ValueError(key_mode)

    def _exec_switch_and_key_over_timeline(self, switch_mode, switch_key):
        """Exec switch and key over timeline selection.

        Args:
            switch_mode (str): fk/ik switch mode
            switch_key (bool): add keys on switch
        """

        # Read timeline range
        _timeline = mel.eval('$tmpVar=$gPlayBackSlider')
        _start, _end = [
            int(_val) for _val in cmds.timeControl(
                _timeline, query=True, rangeArray=True)]
        print 'TIMELINE RANGE', _start, _end

        # Get list of keyed frames
        _frames = {_start, _end}
        for _attr in self.get_key_attrs():
            _crv = get_single(
                cmds.listConnections(_attr, type='animCurve'), catch=True)
            if not _crv:
                continue
            _ktvs = cmds.getAttr(_crv+'.ktv[*]') or []
            _frames = _frames.union([
                _frame for _frame, _ in _ktvs
                if _frame > _start and _frame < _end])
        _frames = sorted(_frames)
        print 'FRAMES', _frames

        # Key current state
        _orig_frames = _frames
        if switch_key:
            _orig_frames = [_start-1] + _frames + [_end+1]
        print 'KEYING CURRENT STATE', _orig_frames
        for _frame in _orig_frames:
            cmds.currentTime(_frame)
            cmds.setKeyframe(self.get_key_attrs())

        # Key switch
        print 'KEYING SWITCH', _frames
        for _frame in _frames:
            cmds.currentTime(_frame)
            cmds.refresh()
            self.exec_switch_and_key(
                switch_mode=switch_mode, key_mode='frame',
                switch_key=False, verbose=0)

    def get_ctrls(self):
        """Get all ctrls in this system.

        Returns:
            (str list): controls
        """
        return self.get_fk_ctrls() + [self.ik_, self.ik_pole, self.gimbal]

    def get_fk_ctrls(self):
        """Get list of fk ctrls in this system.

        Returns:
            (str list): fk ctrls
        """
        return [self.fk1, self.fk2, self.fk3]

    @store_result
    def get_key_attrs(self):
        """Get attrs to key for this system."""
        _attrs = []
        for _fk_ctrl in self.get_fk_ctrls():
            _attrs += [_fk_ctrl+'.r'+_axis for _axis in 'xyz']
        _attrs += [self.ik_pole+'.t'+_axis for _axis in 'xyz']
        _attrs += [self.ik_+'.t'+_axis for _axis in 'xyz']
        _attrs += [self.ik_+'.r'+_axis for _axis in 'xyz']
        _attrs += [self.gimbal+'.FK_IK']
        _attrs += [self.ik_offs]

        return _attrs

    def toggle_ik_fk(self, build_tmp_geo=False, apply_=True):
        """Toggle between ik/fk.

        Args:
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply the switch
        """
        if not cmds.getAttr(self.gimbal+'.FK_IK'):
            self.apply_fk_to_ik(
                build_tmp_geo=build_tmp_geo, apply_=apply_)
        else:
            self.apply_ik_to_fk(
                build_tmp_geo=build_tmp_geo, apply_=apply_)

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return '<{}:{}{}>'.format(
            type(self).__name__.strip("_"), self.side,
            self.limb.capitalize())


def get_selected_systems():
    """Get selected FK/IK systems.

    Returns:
        (_FkIkSystem list): selected systems
    """
    _rig = ref.get_selected(catch=True)
    if not _rig:
        return []

    _systems = set()
    for _node in cmds.ls(selection=True):
        for _side in ['Lf', 'Rt']:
            for _limb in ['arm', 'leg']:
                _system = _FkIkSystem(rig=_rig, limb=_limb, side=_side)
                if _node in _system.get_ctrls():
                    _systems.add(_system)

    return sorted(_systems)


def get_selected_system(error=None):
    """Get selected fk/ik system.

    Args:
        error (Exception): override exception

    Returns:
        (_FkIkSystem): currently selected system

    Raises:
        (ValueError): if no systems selected
    """
    _systems = get_selected_systems()
    return get_single(
        _systems, name='FK/IK system', verb='selected', error=error)