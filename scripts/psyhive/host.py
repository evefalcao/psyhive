"""Tools for managing executing host across multiple host applications."""

from psyhive import icons
from psyhive.utils import wrap_fn

NAME = None


def refresh():
    """Refresh current dcc interface."""


try:
    from maya import cmds
except ImportError:
    pass
else:
    from maya_psyhive import ref
    NAME = 'maya'
    batch_mode = wrap_fn(cmds.about, batch=True)
    _get_cur_scene = wrap_fn(cmds.file, query=True, location=True)
    _force_open_scene = lambda file_: cmds.file(file_, open=True, force=True)
    refresh = cmds.refresh
    reference_scene = ref.create_ref
    save_scene = wrap_fn(cmds.file, save=True)
    _scene_modified = wrap_fn(cmds.file, query=True, modified=True)
    t_start = wrap_fn(cmds.playbackOptions, query=True, minTime=True)
    t_end = wrap_fn(cmds.playbackOptions, query=True, maxTime=True)


def cur_scene():
    """Get the path to the current scene.

    Returns:
        (str|None): path to current scene (if any)
    """
    _cur_scene = _get_cur_scene()
    if _cur_scene == 'unknown':
        return None
    return _cur_scene


def open_scene(file_):
    """Open the given scene file.

    A warning is raised if the current scene has been modified.

    Args:
        file_ (str): file to open
    """
    from psyhive import qt

    if _scene_modified():
        _result = qt.raise_dialog(
            'Save changes to current scene?\n\n{}'.format(file_),
            title='Save changes',
            buttons=["Save", "Don't Save", "Cancel"],
            icon=icons.EMOJI.find('Octopus'))
        if _result == "Save":
            save_scene()
        elif _result == "Don't Save":
            pass
        else:
            raise ValueError(_result)

    _force_open_scene(file_)


def t_range():
    """Get timeline range.

    Returns:
        (tuple): start/end time
    """
    return t_start(), t_end()


def t_frames(inc=1):
    """Get a list of frames in the timeline.

    Args:
        inc (int): frame increment

    Returns:
        (int list): timeline frames
    """
    return range(int(t_start()), int(t_end())+1, inc)
