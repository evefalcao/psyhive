"""Tools for managing the fk/ik interface."""

import os

from maya import cmds

from psyhive import qt, icons
from psyhive.tools import HandledError, get_usage_tracker
from psyhive.utils import abs_path, wrap_fn

from maya_psyhive.tools.fkik_switcher import system

_DIALOG = None
UI_FILE = abs_path('fkik_switcher.ui', root=os.path.dirname(__file__))
ICON = icons.EMOJI.find('Left-Right Arrow', catch=True)


class _NoSystemSelected(HandledError):
    """Raised when no FK/IK system is selected."""

    def __init__(self, msg):
        """Constructor.

        Args:
            msg (str): error message
        """
        super(_NoSystemSelected, self).__init__(msg=msg)


class _FkIkSwitcherUi(qt.HUiDialog3):
    """Interface for FK/IK switcher."""

    def __init__(self, system_=None):
        """Constructor.

        Args:
            system_ (class): override FkIkSystem type
        """
        self.system = system_
        super(_FkIkSwitcherUi, self).__init__(ui_file=UI_FILE)
        if ICON:
            self.set_icon(ICON)

    def _callback__FkToIk(self):
        print 'FK -> IK'
        self._execute_switch(mode='fk_to_ik')

    def _callback__IkToFk(self):
        print 'IK -> FK'
        self._execute_switch(mode='ik_to_fk')

    def _callback__Keyframe(self):
        _system = system.get_selected_system(
            class_=self.system, error=HandledError)
        cmds.setKeyframe(_system.get_key_attrs())

    def _context__Keyframe(self, menu):
        menu.setStyleSheet('background-color:DimGrey; color:white')
        try:
            _system = system.get_selected_system(class_=self.system)
        except ValueError as _exc:
            menu.add_label(_exc.message)
        else:
            _nodes = _system.get_ctrls()
            menu.add_action('Select nodes', wrap_fn(cmds.select, _nodes))

    def _execute_switch(self, mode):
        """Execute switch ik/fk mode.

        Args:
            mode (str): transition to make
        """
        _system = system.get_selected_system(
            class_=self.system, error=HandledError)
        _system.exec_switch_and_key(
            switch_mode=mode,
            switch_key=self.ui.SwitchKey.isChecked(),
            key_mode=self._read_key_mode())

    def _read_key_mode(self):
        """Read current key mode from radio buttons."""
        for _name in ['None', 'Frame', 'Timeline']:
            _elem = getattr(self.ui, 'Key'+_name)
            if _elem.isChecked():
                return _name
        raise ValueError("Failed to read key mode")


@get_usage_tracker(name='launch_fkik_switcher')
def launch_interface(system_=None):
    """Launch FK/IK switcher interface.

    Args:
        system_ (class): override FkIkSystem type

    Returns:
        (FkIkSwitcherUi): dialog instance
    """
    global _DIALOG
    _DIALOG = _FkIkSwitcherUi(system_=system_)
    return _DIALOG
