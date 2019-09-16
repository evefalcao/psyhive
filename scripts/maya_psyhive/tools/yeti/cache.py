"""Tools for managing yeti caching."""

import os

from maya import cmds

from psyhive import tk, host, qt, icons
from psyhive.utils import abs_path, get_single, PyFile

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_parent, set_namespace, restore_sel

ICON = icons.EMOJI.find('Ghost')


def _apply_cache_to_selected_asset(cache):
    """Apply a cache to the selected asset.

    The asset can be selected by selecting any node in the reference.

    If the asset doesn't have a matching yeti node, it will be created.

    Args:
        cache (str): path to cache file to apply
    """

    # Get asset
    _ref = ref.get_selected(catch=True)
    if not _ref:
        qt.notify_warning(
            "No asset selected.\n\nPlease select the asset you apply the "
            "cache to.")
        return
    print 'REF', _ref

    # Get yeti node
    _out = tk.get_output(cache)
    _cache_ns = _out.output_name
    assert _out.channel.startswith(_cache_ns+'_')
    _node_name = _out.channel[len(_cache_ns+'_'):]
    print 'NODE NAME', _node_name
    _yeti = _ref.get_node(_node_name, catch=True)
    if not _yeti:
        _top_node = _ref.find_top_node()
        set_namespace(':'+_ref.namespace)
        _yeti = hom.CMDS.createNode('pgYetiMaya', name=_node_name)
        set_namespace(':')
        cmds.parent(get_parent(_yeti), 'chickDad:cRoot')
    print 'YETI', _yeti

    _yeti.plug('cacheFileName').set_val(cache)
    _yeti.plug('fileMode').set_val(1)


@restore_sel
def _cache_yetis(yetis):
    """Cache a list of yeti nodes.

    Args:
        yetis (HFnDependencyNode list): nodes to cache
    """
    _work = tk.cur_work()
    _ns = get_single(set([_yeti.namespace for _yeti in yetis]))
    _ref = ref.find_ref(_ns)

    # Test outputs
    _kwargs = dict(format='fur', output_type='yeti',
                   extension='fur', output_name=_ref.namespace)
    for _yeti in yetis:
        _out = _work.map_to(
            tk.TTShotOutputFileSeq, channel=str(_yeti).replace(':', '_'),
            **_kwargs)
        print 'OUT', _out
        if _out.exists():
            _out.delete(wording='Replace')
        _out.test_dir()

    # Generate caches
    cmds.select(yetis)
    _out_path = _work.map_to(
        tk.TTShotOutputFileSeq, channel='<NAME>', **_kwargs).path
    print "OUT PATH", _out_path
    cmds.pgYetiCommand(
        writeCache=_out_path, range=host.t_range(), samples=3)


def _write_cache_from_selected_asset():
    """Cache selected asset.

    All yeti nodes in the asset are cached.

    The asset can be selected by selecting any node in the reference.
    """
    _ref = ref.get_selected(catch=True)
    if not _ref:
        qt.notify_warning("No asset selected.\n\nPlease select the asset "
                          "you want to cache.")
        return
    print 'REF', _ref

    # Get yeti nodes
    _yetis = _ref.find_nodes(type_='pgYetiMaya')
    if not _yetis:
        qt.notify_warning(
            "No yeti nodes in asset {}.\n\nThis asset cannot "
            "be cached.".format(_ref.namespace))
        return

    _cache_yetis(_yetis)


def _write_cache_from_selected_yeti():
    """Write a yeti cache from selected yeti nodes."""
    _yetis = hom.get_selected(type_='pgYetiMaya', multi=True)
    _cache_yetis(_yetis)


class _YetiCacheToolsUi(qt.HUiDialog):
    """Interface for managing yeti caching."""

    def __init__(self):
        """Constructor."""
        self.work = tk.cur_work()
        self.shot = self.work.shot
        self.names = []

        _ui_file = abs_path(
            '{}/yeti_cache_tools.ui'.format(os.path.dirname(__file__)))
        super(_YetiCacheToolsUi, self).__init__(ui_file=_ui_file)
        self.set_icon(ICON)

        self.ui.step.currentTextChanged.connect(self.ui.asset.redraw)
        self.ui.asset.currentTextChanged.connect(self.ui.version.redraw)
        self.ui.version.currentIndexChanged.connect(self.ui.cache_read.redraw)

    # @qt.list_redrawer
    def _redraw__step(self, widget):

        _steps = self.shot.find_step_roots()
        print 'WIDGET', widget

        # Update widget
        for _step in _steps:
            widget.add_item(_step.name, data=_step)
        if not _steps:
            widget.addItem('<None>')
        widget.setEnabled(bool(_steps))

    def _redraw__asset(self, widget):

        _step = self.ui.step.selected_data()

        self.names = []
        if not _step:
            _assets = []
        else:
            self.names = [_name for _name in _step.find_output_names()
                          if _name.output_type == 'yeti']
            _assets = sorted(set([_name.output_name for _name in self.names]))

        # Update widget
        widget.clear()
        widget.addItems(_assets)
        if not _assets:
            widget.addItem('<None>')
        widget.setEnabled(bool(_assets))

        self.ui.version.redraw()

    def _redraw__version(self, widget):

        _asset = self.ui.asset.currentText()
        print 'ASSET', _asset
        _name = get_single(
            [_name for _name in self.names if _name.output_name == _asset],
            catch=True)
        if not _name:
            _vers = []
        else:
            _vers = _name.find(depth=1, class_=tk.TTShotOutputVersion)

        # Update widget
        widget.clear()
        for _ver in _vers:
            widget.add_item(_ver.name, data=_ver)
        if _vers:
            widget.setCurrentIndex(len(_vers)-1)
        else:
            widget.addItem('<None>')
        widget.setEnabled(bool(_vers))

        self.ui.cache_read.redraw()

    def _redraw__cache_read(self, widget):
        _ver = self.ui.version.selected_data()
        widget.setEnabled(bool(_ver))

    def _callback__cache_write_asset(self):
        _write_cache_from_selected_asset()

    def _callback__cache_write_asset_help(self):
        _def = PyFile(__file__).find_def(
            _write_cache_from_selected_asset.__name__)
        qt.help_(_def.docs)

    def _callback__cache_write_node(self):
        _write_cache_from_selected_yeti()

    def _callback__cache_write_node_help(self):
        _def = PyFile(__file__).find_def(
            _write_cache_from_selected_yeti.__name__)
        qt.help_(_def.docs)

    def _callback__cache_read(self):
        _ver = self.ui.version.selected_data()
        _out = get_single(_ver.find_outputs())
        _apply_cache_to_selected_asset(cache=_out.path)

    def _callback__cache_read_help(self):
        _def = PyFile(__file__).find_def(
            _apply_cache_to_selected_asset.__name__)
        qt.help_(_def.get_docs().desc_full)


def launch_cache_tools():
    """Launch yeti cache tools interface."""

    # Make sure we are in a shot
    _work = tk.cur_work()
    if not _work:
        qt.notify_warning(
            'No current work file found.\n\nPlease save your scene.')
        return None

    # Launch interface
    from maya_psyhive.tools import yeti
    yeti.DIALOG = _YetiCacheToolsUi()
    return yeti.DIALOG