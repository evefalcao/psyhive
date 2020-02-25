"""Tools for managing action work files in frasier.

These are work files with added naming conventions to accomodate
for additional data required to be stored.
"""

import operator
import os
import shutil
import time

from maya import cmds

import six

from psyhive import host, tk2, qt
from psyhive.utils import (
    File, abs_path, Dir, CacheMissing, store_result_to_file, store_result,
    apply_filter, get_time_f, get_time_t, store_result_on_obj,
    lprint, passes_filter, store_result_content_dependent)

from . import _fr_tools, _fr_vendor_ma

_DIR = abs_path(os.path.dirname(__file__))

EXPORT_FBX_ROOT = 'P:/projects/frasier_38732V/production/processed_fbx'

# Set up character assets
_CHAR_ROOT = 'P:/projects/frasier_38732V/assets/3D/character'
ASSETS = {}
for _name, _dir in [
        ('M', 'neutralMale'),
        ('F', 'neutralFemale'),
        ('Damsel', 'laCallingDamsel'),
        ('Jeremy', 'necessaryEvilJeremy'),
        ('Kara', 'necessaryEvilKara'),
        ('Victoria', 'rulingBodiesVictoria'),
]:
    try:
        ASSETS[_name] = tk2.TTRoot(_CHAR_ROOT+'/'+_dir)
    except ValueError:
        pass


def _rsplit(string, splitter):
    """Reverse split a string.

    This is the same a regular split, but it will split from the back.
    This is to solve the issue of using xxx as a splitter if one of the
    tokens in the filenames ends with x - reverse splitting works ok
    because the filename tokens should all start with captials.

    Args:
        string (str): string to split
        splitter (str): string to split by

    Returns:
        (str list): split string
    """
    _rev = ''.join(reversed(string))
    _rev_split = _rev.split(splitter)
    _rsplit = reversed(_rev_split)
    return [''.join(reversed(_word)) for _word in _rsplit]


class FrasierWork(tk2.TTWork):
    """Represents a work file on frasier.

    Each work file represents a recorded mocap action, and has been copied
    from a correctly named vendor in file.
    """

    disp = None
    label = None

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to work file
        """
        super(FrasierWork, self).__init__(path)

        self.cache_fmt = '{}/cache/{}_{{}}.cache'.format(
            self.dir, self.basename)
        self.blast = self.map_to(
            tk2.TTOutputFileSeq, output_type='blast', output_name='blast_cam',
            extension='jpg', format='jpg')
        self.face_blast = self.map_to(
            tk2.TTOutputFileSeq, output_type='faceBlast',
            output_name='blast_cam', extension='jpg', format='jpg')
        self.blast_comp = self.map_to(
            tk2.TTOutputFile, extension='mov', output_type='blastComp',
            output_name='blast_cam', format='mov')

        self.type_ = {
            'd': 'Disposition',
            'v': 'Vignette',
        }.get(self.task[0])
        if not self.type_:
            raise ValueError('Unhandled type')

        _tokens = _rsplit(self.task[1:], 'xxx')
        if self.type_ == 'Disposition':
            self.disp, self.label, _iter = _tokens
            assert self.label[0].isupper()
            self.name = self.disp
            self.desc = self.label
        elif self.type_ == 'Vignette':
            self.vignette, self.desc, _iter = _tokens
            self.name = self.vignette
        else:
            raise ValueError(self.type_)

        assert len(_iter) == 3
        assert _iter[0] == 'I'
        assert _iter[1:].isdigit()

        self.iter = int(_iter[1:])

    @property
    def processed_mov(self):
        """Get path to processed mov file."""
        _dir = 'P:/projects/frasier_38732V/production/processed_mov'
        _fbx = self.get_export_fbx()
        _mov = '{}/{}/{}.mov'.format(
            _dir, Dir(EXPORT_FBX_ROOT).rel_path(_fbx), _fbx.basename)
        return _mov

    def delete_all_data(self, force=False):
        """Delete all generated data from this action file.

        This includes all blasts and exports and the work file itself.

        Args:
            force (bool): delete data without confirmation
        """
        if not force:
            qt.ok_cancel(
                'Delete all data?\n\nWork:\n{}\n\nVendor file:\n{}'.format(
                    self.path, self.get_vendor_file()))

        for _seq in [self.blast, self.face_blast, self.blast_comp]:
            _seq.delete(force=True)

        for _file in [
                self.get_export_fbx(),
                self.get_export_fbx(dated=True),
                File(self.processed_mov),
                self]:
            _file.delete(force=True)

    def get_char_name(self):
        """Get character name for this work file.

        This matches the char tag in the vendor in files.

        Returns:
            (str): character name
        """
        _root = self.get_root()
        for _a_name, _a_root in ASSETS.items():
            if _a_root == _root:
                return _a_name
        raise ValueError(self)

    def get_age(self):
        """Get age of this work file (from vendor in folder date).

        Returns:
            (float): age in seconds
        """
        return time.time() - self.get_mtime()

    def get_mtime(self):
        """Get mtime of this work file (from vendor in folder date).

        Returns:
            (float): mtime in seconds
        """
        try:
            _vendor_file = self.get_vendor_file()
        except CacheMissing:
            return None
        _dir = Dir(_fr_vendor_ma.MOBURN_ROOT).rel_path(
            _vendor_file).split('/')[0]
        _date_str = _dir.split('_')[-1]
        return get_time_f(time.strptime(_date_str, '%Y-%m-%d'))

    def get_mtime_fmt(self, fmt):
        """Get formatted modified time.

        Args:
            fmt (str): time format

        Returns:
            (str): formatted time string
        """
        return time.strftime(fmt, get_time_t(self.get_mtime()))

    def get_ref_data(self):
        """Get reference mov data.

        Some files have reference footage associated with them. This is
        defined in the refs_movs.data spreadsheet. If there is ref
        footage associated with this file, a mov path and start seconds
        tuple is returned. Otherwise None is returned.

        Returns:
            (tuple): mov path, start seconds
        """
        _vendor_file = self.get_vendor_file()
        _ref_movs_data = _get_ref_movs_data()
        if _vendor_file not in _ref_movs_data:
            return None
        _mov, _start = _ref_movs_data[_vendor_file]
        return _mov, _start

    def get_ref_mov(self):
        """Get reference mob path for this wor file.

        Returns:
            (str|None): path to ref mov (if any)
        """
        _data = self.get_ref_data()
        if not _data:
            return None
        _mov, _ = _data
        return _mov

    @store_result_on_obj
    def get_work_area(self):
        """Get work area for this work file (to facilitate caching).

        Returns:
            (CTTWorkArea): cacheable work area
        """
        _work_area = self.map_to(tk2.TTWorkArea)
        return tk2.obtain_cacheable(_work_area)

    @store_result_to_file
    def get_vendor_file(self, file_=None, force=False):
        """Get vendor file associated with this work file.

        Args:
            file_ (str): apply vendor file data
            force (bool): force rewrite cache data (requires file_)

        Returns:
            (str): path to vendor file
        """
        if not file_:
            raise CacheMissing
        assert isinstance(file_, six.string_types)
        return file_

    def set_vendor_file(self, file_):
        """Set vendor file for this work.

        Args:
            file_ (str): work file
        """
        self.get_vendor_file(force=True, file_=file_)

    def get_range(self):
        """Get frame range of this work.

        Returns:
            (float tuple): start/end frames
        """
        return _fr_vendor_ma.FrasierVendorMa(
            self.get_vendor_file()).get_range()

    def get_export_fbx(self, dated=False):
        """Get path to export fbx for this work file.

        Args:
            dated (bool): get path to dated fbx (in date folder)

        Returns:
            (str): path to export fbx
        """
        _char_name = self.get_char_name()
        _char = {'M': 'Male', 'F': 'Female'}.get(_char_name, _char_name)

        if self.type_ == 'Disposition':
            _fmt = (
                '{root}/Dispositions/{char}/{work.disp}/'
                '{char}_{work.disp}_{work.label}_{work.iter:02d}.fbx')
        elif self.type_ == 'Vignette':
            _fmt = (
                '{root}/{char}/{work.vignette}/'
                '{char}_{work.vignette}_{work.desc}_{work.iter:02d}.fbx')
        else:
            raise ValueError(self)

        _fbx_path = _fmt.format(root=EXPORT_FBX_ROOT, work=self, char=_char)

        if dated:
            _fbx_root = Dir(EXPORT_FBX_ROOT)
            _vendor_root = Dir(_fr_vendor_ma.MOBURN_ROOT)
            # print self.get_vendor_file()
            # print _fbx_path

            _vendor_file = self.get_vendor_file()
            _delivery_dir = _vendor_root.rel_path(_vendor_file).split('/')[0]
            assert self.get_mtime_fmt('%Y-%m-%d') in _delivery_dir
            _date_fbx = File('{}/{}/{}'.format(
                _fbx_root.path, _delivery_dir,
                _fbx_root.rel_path(_fbx_path)))
            # print _date_fbx.path
            return _date_fbx

        return File(_fbx_path)

    @store_result_content_dependent
    def has_ik_legs(self, force=False, verbose=0):
        """Test if this work file ik legs.

        Args:
            force (bool): force reread data
            verbose (int): print process data

        Returns:
            (bool): whether legs have been update to ik
        """
        if not host.cur_scene() == self.path:
            raise CacheMissing
        for _ctrl in ['SK_Tier1_Male:FKIKLeg_R', 'SK_Tier1_Male:FKIKLeg_L']:
            _attr = _ctrl+'.FKIKBlend'
            lprint("CHECKING", _attr, cmds.getAttr(_attr), verbose=verbose)
            if not cmds.getAttr(_attr) == 10:
                return False
        return True

    def export_fbx(self):
        """Export fbx from this work file."""
        _fbx = self.get_export_fbx()
        print 'EXPORT FBX', _fbx.path
        _dated_fbx = self.get_export_fbx(dated=True)
        print 'DATED FBX', _dated_fbx.path
        _fr_tools.export_hsl_fbx_from_cur_scene(_fbx.path)
        _dated_fbx.test_dir()
        shutil.copy(_fbx.path, _dated_fbx.path)


def find_action_works(
        type_=None, task_filter=None, day_filter=None, max_age=None,
        after=None, task=None, root=None, filter_=None, version=None,
        fbx_filter=None, ma_filter=None, force=False):
    """Find action work files in frasier project.

    Args:
        type_ (str): filter by type (eg. Vignette, Disposition)
        task_filter (str): apply filter to work task attribute
        day_filter (str): filter by day (in %y%m%d format)
        max_age (float): reject any work files older than is many secs
        after (str): return works on or after this day (in %y%m%d format)
        task (str): filter by exact task name
        root (TTRoot): filter by root
        filter_ (str): apply filter to work file path
        version (int): filter by version (v001 are always ingested files)
        fbx_filter (str): apply filter export fbx path
        ma_filter (str): filter by vendor ma path
        force (bool): force reread actions from disk

    Returns:
        (FrasierWork list): list of work files
    """
    _works = _read_action_works(force=force)

    # Filter by task
    if task_filter:
        _works = apply_filter(
            _works, task_filter, key=operator.attrgetter('task'))
    if task:
        _works = [_work for _work in _works if _work.task == task]

    if type_:
        _works = [_work for _work in _works if _work.type_ == type_]

    if filter_:
        _works = apply_filter(
            _works, filter_, key=operator.attrgetter('path'))

    if root:
        _works = [_work for _work in _works if _work.get_root() == root]

    if max_age is not None:
        _works = [_work for _work in _works if _work.get_age() < max_age]

    if day_filter:
        _works = [_work for _work in _works
                  if _work.get_mtime() and
                  _work.get_mtime_fmt('%y%m%d') == day_filter]

    if after:
        _cutoff = get_time_f(time.strptime(after, '%y%m%d'))
        _works = [_work for _work in _works
                  if _work.get_mtime() and
                  _work.get_mtime() >= _cutoff]

    if fbx_filter:
        _works = [_work for _work in _works
                  if passes_filter(_work.get_export_fbx().path, fbx_filter)]

    if ma_filter:
        _works = [_work for _work in _works
                  if _work.get_mtime() and
                  passes_filter(_work.get_vendor_file(), ma_filter)]

    if version:
        _works = [_work for _work in _works if _work.version == version]

    return _works


@store_result
def _read_action_works(force=False):
    """Read action work files from disk.

    Args:
        force (bool): force reread from disk

    Returns:
        (FrasierWork list): list of all frasier work files
    """
    _works = []
    for _asset in ASSETS.values():
        _anim = _asset.find_step_root('animation')
        for _work in _anim.find_work(class_=FrasierWork, dcc='maya'):
            _works.append(_work)
    return _works


@store_result
def _get_ref_movs_data(force=False):
    """Read reference movs spreadsheet data.

    Args:
        force (bool): force reread from disk

    Returns:
        (dict): vendor in mov, reference mov and start frame data
    """
    _data = {}
    _data_file = _DIR+'/_fr_ref_movs.data'

    for _line in File(_data_file).read_lines()[1:]:
        _line = _line.strip()
        if not _line.strip():
            continue

        # Extract ma
        _ma = _line.split('.ma')[0]+'.ma'
        assert _ma in _line
        _line = _line.replace(_ma, '').strip()
        _ma = abs_path(_ma)

        # Extract mov
        _mov = _line.split('.mov')[0]+'.mov'
        assert _mov in _line
        _line = _line.replace(_mov, '').strip()
        _mov = abs_path(_mov)

        # Extract start
        _tokens = _line.split()
        _start, _ = _tokens
        _start = float(_start)

        _data[_ma] = _mov, _start

    return _data


def cur_work():
    """Get current workfile.

    Returns:
        (FrasierWork): current work
    """
    return FrasierWork(host.cur_scene())
