"""General utilities for py_gui interfaces."""

from psyhive import icons, tools, qt
from psyhive.tools import catch_error
from psyhive.utils import PyFile, str_to_seed, to_nice

NICE_COLS = [
    'salmon', 'tomato', 'darksalmon', 'coral', 'orangered', 'lightsalmon',
    'sandybrown', 'darkorange', 'orange', 'goldenrod', 'gold', 'yellow',
    'olivedrab', 'yellowgreen', 'darkolivegreen', 'greenyellow', 'chartreuse',
    'lawngreen', 'darkgreen', 'forestgreen', 'green', 'lightgreen', 'lime',
    'limegreen', 'palegreen', 'mediumseagreen', 'seagreen', 'springgreen',
    'mediumspringgreen', 'aquamarine', 'mediumaquamarine', 'turquoise',
    'lightseagreen', 'mediumturquoise', 'cyan', 'darkcyan', 'darkslategrey',
    'darkturquoise', 'teal', 'cadetblue', 'powderblue', 'lightblue',
    'deepskyblue', 'lightskyblue', 'steelblue', 'dodgerblue',
    'lightslategrey', 'slategray', 'slategrey', 'lightsteelblue',
    'cornflowerblue', 'royalblue', 'blue', 'darkblue', 'mediumblue',
    'midnightblue', 'navy', 'darkslateblue', 'mediumslateblue', 'slateblue',
    'mediumpurple', 'blueviolet', 'indigo', 'darkorchid', 'darkviolet',
    'mediumorchid', 'darkmagenta', 'magenta', 'plum', 'purple', 'thistle',
    'violet', 'orchid', 'mediumvioletred', 'deeppink', 'hotpink',
    'palevioletred', 'crimson', 'pink', 'lightpink']


def get_def_icon(name, set_):
    """Pick random icon for the given def name.

    Args:
        name (str): def name to use as seed
        set_ (Collection): icon set to use
    """
    _rand = str_to_seed(name)
    return _rand.choice(set_.get_paths())


def get_exec_fn(def_, read_arg_fns, catch_error=True):
    """Get execute command for the given def and read arg functions.

    Args:
        def_ (PyDef): def being executed
        read_arg_fns (dict): name/fn dict of functions to read def args
        catch_error (bool): apply catch_error decorator
    """
    _mod = def_.py_file.get_module()

    def _exec_fn(*xargs):
        print '############ Start {} ##############'.format(def_.name)
        del xargs
        reload(_mod)
        _kwargs = {}
        for _arg_name, _arg_fn in read_arg_fns.items():
            _kwargs[_arg_name] = _arg_fn()
        _fn = getattr(_mod, def_.name)
        if catch_error:
            _fn = tools.catch_error(_fn)
        _fn(**_kwargs)
        print '############ Complete {} ############'.format(def_.name)

    return _exec_fn


def get_code_fn(def_):
    """Get function to open def code.

    Args:
        def_ (PyDef): def to open code for
    """

    @catch_error
    def _code_fn(*args):
        del args
        print 'SEARCHING FOR', def_.name, 'IN', def_.py_file
        _py_file = PyFile(def_.py_file.path)
        _py_file.find_def(def_.name).edit()
    return _code_fn


def get_help_fn(def_):
    """Get help function for the given def.

    Args:
        def_ (PyDef): def to get help function for
    """
    def _help_fn(*args):
        del args
        qt.notify(
            def_.get_docs().text,
            title='Help - '+to_nice(def_.name),
            icon=icons.EMOJI.find('Info'))
    return _help_fn