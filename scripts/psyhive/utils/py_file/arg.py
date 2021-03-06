"""Tools for managing arguments in a PyFile object."""

import ast

from psyhive.utils.misc import safe_zip, get_single


def _read_ast_default(default, safe=True):
    """Read default value of the given ast.Default object.

    Args:
        default (ast.Default): ast default object
        safe (bool): if safe is disabled, None will be returned
            if the default cannot be determined
    """
    if isinstance(default, ast.Num):
        _default = default.n
    elif isinstance(default, ast.Str):
        _default = default.s
    elif isinstance(default, ast.Name):
        if default.id == 'True':
            _default = True
        elif default.id == 'False':
            _default = False
        elif default.id == 'None':
            _default = None
        elif default.id == 'str':
            _default = str
        else:
            if not safe:
                _default = None
            else:
                print 'UNABLE TO DETERMINE DEFAULT', default
                raise ValueError(default.id)
    elif default is None:
        _default = None
    elif isinstance(default, ast.Tuple):
        _default = []
        for _item in default.elts:
            _default.append(_read_ast_default(_item))
        _default = tuple(_default)
    elif isinstance(default, ast.List):
        _default = []
        for _item in default.elts:
            _default.append(_read_ast_default(_item))
    elif isinstance(default, ast.Dict):
        _default = {}
        for _key, _val in safe_zip(default.keys, default.values):
            _default[_read_ast_default(_key)] = _read_ast_default(_val)
    elif isinstance(default, ast.Attribute):
        # Not implemented
        _default = None
    else:
        raise RuntimeError(default)

    return _default


class PyArg(object):
    """Represents a python argument."""

    def __init__(self, ast_, default, def_):
        """Constructor.

        Args:
            ast_ (ast.Module): ast object for this arg
            default (ast.Default): ast default for this arg
            def_ (PyDef): function this arg belongs to
        """
        self._ast = ast_
        self._ast_default = default
        self.name = self._ast.id
        self.default = _read_ast_default(self._ast_default, safe=False)
        self.type_ = None if self.default is None else type(self.default)
        self.def_ = def_

    def get_docs(self):
        """Get this arg's docstrings.

        Returns:
            (PyArgDocs): arg docs
        """
        return get_single([
            _arg for _arg in self.def_.get_docs().args
            if _arg.name == self.name], catch=True)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.name)
