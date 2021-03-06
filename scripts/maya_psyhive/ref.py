"""Tools for managing references in maya."""

import os

from maya import cmds

from psyhive.utils import (
    File, get_single, lprint, abs_path, get_path, passes_filter)
from maya_psyhive.utils import (
    restore_ns, get_parent, set_namespace, del_namespace)


class FileRef(object):
    """Represents a file referenced into maya."""

    def __init__(self, ref_node):
        """Constructor.

        Args:
            ref_node (str): reference node
        """
        self.ref_node = ref_node
        if not self.path:
            raise ValueError
        self.extn = File(self.path).extn

    @property
    def _file(self):
        """Get this ref's file path (with copy number)."""
        try:
            return str(cmds.referenceQuery(self.ref_node, filename=True))
        except RuntimeError:
            return None

    def find_meshes(self):
        """Find meshes in this reference.

        Returns:
            (HFnMesh list): meshes
        """
        from maya_psyhive import open_maya as hom
        _meshes = []
        for _shp in self.find_nodes(type_='mesh'):
            if _shp.plug('intermediateObject').get_val():
                continue
            _mesh = hom.HFnMesh(get_parent(_shp))
            _meshes.append(_mesh)
        return _meshes

    def find_node(self, type_=None, class_=None):
        """Find exactly one node within this reference.

        Args:
            type_ (str): match by type name
            class_ (class): cast node to given class

        Returns:
            (HFnDependencyNode): matching node
        """
        return get_single(self.find_nodes(type_=type_, class_=class_))

    def find_nodes(self, type_=None, class_=None, namespace=None):
        """Find nodes within this reference.

        Args:
            type_ (str): filter nodes by type
            class_ (class): override node class
            namespace (str): override search namespace

        Returns:
            (HFnDepenencyNode list): list of nodes
        """
        from maya_psyhive import open_maya as hom
        _namespace = namespace or self.namespace
        _class = class_ or hom.HFnDependencyNode

        _kwargs = {}
        if type_:
            _kwargs['type'] = type_

        _nodes = []
        for _node in cmds.ls(_namespace+":*", referencedNodes=True, **_kwargs):
            try:
                _node = _class(_node)
            except RuntimeError:
                continue
            _nodes.append(_node)
        return _nodes

    def find_tfms(self, type_=None):
        """Find transforms in this reference.

        Args:
            type_ (str): pass type flag to ls command

        Returns:
            (HFnTransform list): matching transforms
        """
        from maya_psyhive import open_maya as hom
        return self.find_nodes(type_=type_, class_=hom.HFnTransform)

    def find_top_node(self, class_=None, catch=False, verbose=0):
        """Find top node of this reference.

        Args:
            class_ (class): override class for top node
            catch (bool): no error if no top node found
            verbose (int): print process data

        Returns:
            (str|None): top node (if any)
        """
        _top_nodes = self.find_top_nodes(class_=class_, verbose=verbose)
        _top_node = get_single(_top_nodes, catch=catch, verbose=1)
        return _top_node

    def find_top_nodes(self, class_=None, verbose=0):
        """Find top node of this reference.

        Args:
            class_ (class): override class for top node
            verbose (int): print process data

        Returns:
            (str|None): top node (if any)
        """
        from maya_psyhive import open_maya as hom
        _nodes = cmds.ls(
            self.namespace+":*", long=True, dagObjects=True,
            type='transform')
        if not _nodes:
            return None
        _min_pipes = min([_node.count('|') for _node in _nodes])
        lprint('MIN PIPES', _min_pipes, verbose=verbose)
        _class = class_ or hom.HFnTransform
        _top_nodes = []
        for _node in _nodes:
            if _node.count('|') != _min_pipes:
                continue
            _top_node = _get_shortest_path(_node, class_=_class)
            _top_nodes.append(_top_node)
        _top_nodes = sorted(_top_nodes)
        lprint(' - TOP NODES', _top_nodes, verbose=verbose)
        return _top_nodes

    def get_attr(self, attr):
        """Get an attribute on this rig.

        Args:
            attr (str): attribute name
        """
        from maya_psyhive import open_maya as hom
        _attr = attr
        if isinstance(attr, hom.HPlug):
            _attr = str(attr)
        _attr = _attr.split(":")[-1]
        return '{}:{}'.format(self.namespace, _attr)

    def get_node(self, name, strip_ns=True, class_=None, catch=False):
        """Get node from this ref matching the given name.

        Args:
            name (str): name of node
            strip_ns (bool): strip namespace from node name
            class_ (class): override node class
            catch (bool): no error if node is missing

        Returns:
            (HFnDependencyNode): node name
        """
        from maya_psyhive import open_maya as hom
        _class = class_ or hom.HFnDependencyNode
        _name = name.split(":")[-1] if strip_ns else name
        _node = '{}:{}'.format(self.namespace, _name)
        if _class is str:
            return _node
        try:
            return _class(_node)
        except RuntimeError as _exc:
            if catch:
                return None
            raise ValueError("Missing node "+_node)

    def get_plug(self, plug):
        """Get plug within this reference.

        Args:
            plug (str|HPlug): plug name

        Returns:
            (HPlug): plug mapped to this reference's namespace
        """
        from maya_psyhive import open_maya as hom
        return hom.HPlug(self.get_attr(plug))

    def get_tfm(self, name):
        """Get transform node from this reference.

        Args:
            name (str): node name

        Returns:
            (HFnTransform): transform node
        """
        from maya_psyhive import open_maya as hom
        return self.get_node(name, class_=hom.HFnTransform)

    def import_nodes(self):
        """Import nodes from this reference."""
        cmds.file(self._file, importReference=True)

    def is_loaded(self):
        """Check if this reference is loaded.

        Returns:
            (bool): loaded state
        """
        return cmds.referenceQuery(self.ref_node, isLoaded=True)

    def load(self):
        """Load this reference."""
        cmds.file(self._file, loadReference=True)

    @property
    def namespace(self):
        """Get this ref's namespace."""
        if not self.is_loaded():
            return str(cmds.file(self._file, query=True, namespace=True))
        try:
            return cmds.referenceQuery(
                self.ref_node, namespace=True).lstrip(':')
        except RuntimeError:
            return None

    @property
    def path(self):

        """Get path to this ref's scene file (without copy number)."""
        if not self._file:
            return None
        return abs_path(self._file.split('{')[0])

    @property
    def prefix(self):
        """Get this ref's prefix."""
        if self.namespace:
            return None
        return str(cmds.file(self._file, query=True, namespace=True))

    def reference_query(self, **kwargs):
        """Wrapper for maya.cmds referenceQuery function.

        Returns:
            (any): referenceQuery result
        """
        return cmds.referenceQuery(self.ref_node, referenceNode=True, **kwargs)

    def reload_(self):
        """Reload this reference."""
        self.unload()
        self.load()

    def remove(self, force=False):
        """Remove this reference from the scene.

        Args:
            force (bool): remove without confirmation
        """
        from psyhive import qt
        if not force:
            _msg = (
                'Are you sure you want to remove the reference {}?\n\n'
                'This is not undoable.'.format(self.namespace))
            if not qt.yes_no_cancel(_msg) == 'Yes':
                return
        cmds.file(self._file, removeReference=True)

    def rename(self, namespace, update_ref_node=True):
        """Rename this reference's namespace.

        Args:
            namespace (str): namespace to update to
            update_ref_node (bool): update reference node name
        """
        if namespace != self.namespace:
            set_namespace(":")
            del_namespace(':'+namespace)
            cmds.file(self._file, edit=True, namespace=namespace)

        if update_ref_node:
            cmds.lockNode(self.ref_node, lock=False)
            _ref_node = cmds.rename(self.ref_node, namespace+"RN")
            cmds.lockNode(_ref_node, lock=True)
            self.__init__(_ref_node)

    def setup_anim_offsets(self, ctrl=None):
        """Setup anim offset controls.

        This sets up anim offset, multiply and time attributes and connects
        any anim curves in the reference to have the input and the anim
        time.

        Args:
            ctrl (HFnTransform): node to add attrs to
        """
        from maya_psyhive import open_maya as hom

        _ctrl = ctrl or self.find_top_node()
        _offs = _ctrl.create_attr('animOffset', 0.0)
        _mult = _ctrl.create_attr('animMult', 1.0)
        _t_anim = _ctrl.create_attr('animTime', 0.0)
        _t_mult = hom.HPlug('time1.outTime').multiply_node(_mult)
        _t_mult.add_node(_offs, output=_t_anim)

        # Connect anim
        for _crv in self.find_nodes(
                class_=hom.HFnAnimCurve, type_='animCurve'):
            _t_anim.connect(_crv.input)

        return _t_anim, _offs, _mult

    def swap_to(self, file_):
        """Swap this reference file path.

        Args:
            file_ (str): new file path
        """
        _file = get_path(file_)
        if not os.path.exists(_file):
            raise OSError("Missing file: {}".format(_file))
        try:
            cmds.file(
                _file, loadReference=self.ref_node, ignoreVersion=True,
                options="v=0", force=True)
        except RuntimeError as _exc:
            if _exc.message == 'Maya command error':
                raise RuntimeError('Maya errored on opening file '+_file)
            raise _exc

    def unload(self):
        """Load this reference."""
        cmds.file(self._file, unloadReference=True)

    def __cmp__(self, other):
        return cmp(self.ref_node, other.ref_node)

    def __hash__(self):
        return hash(self.ref_node)

    def __repr__(self):
        if self.namespace:
            _tag = ''
            _name = self.namespace
        else:
            _tag = '[P]'
            _name = self.prefix
        return '<{}{}:{}>'.format(
            type(self).__name__.strip('_'), _tag, _name)


def _get_shortest_path(node, class_, verbose=0):
    """Get shortest path to the given long node path.

    If the node has a unique name then this should return just
    the name with all the underscores and parents removed.

    Args:
        node (str): long node name
        class_ (HFnDependencyNode): class to cast to
        verbose (int): print process data

    Returns:
        (HFnDependencyNode): node object
    """
    _tokens = node.split('|')
    for _idx in range(len(_tokens)-1):
        _path = ('|'.join(_tokens[-_idx:])).lstrip('|')
        lprint(_path, verbose=verbose)
        try:
            return class_(_path)
        except ValueError:
            pass
    return class_(node)


@restore_ns
def create_ref(file_, namespace, class_=None, force=False):
    """Create a reference.

    Args:
        file_ (str): path to reference
        namespace (str): reference namespace
        class_ (type): override FileRef class
        force (bool): force replace any existing ref

    Returns:
        (FileRef): reference
    """
    from psyhive import qt
    from psyhive import host

    _file = File(abs_path(file_))
    if not _file.exists():
        raise OSError("File does not exist: "+_file.path)
    _class = class_ or FileRef
    _rng = host.t_range()

    if _file.extn == 'abc':
        cmds.loadPlugin('AbcImport', quiet=True)
    elif _file.extn.lower() == 'fbx':
        cmds.loadPlugin('fbxmaya', quiet=True)

    # Test for existing
    cmds.namespace(set=":")
    if cmds.namespace(exists=namespace):
        _ref = find_ref(namespace, catch=True)
        if _ref:
            if not force:
                qt.ok_cancel('Replace existing {} reference?'.format(
                    namespace))
            _ref.remove(force=True)
        else:
            del_namespace(namespace, force=force)

    # Create the reference
    _cur_refs = set(cmds.ls(type='reference'))
    _kwargs = {
        'reference': True,
        'namespace': namespace,
        'options': "v=0;p=17",
        'ignoreVersion': True}
    cmds.file(_file.abs_path(), **_kwargs)

    # Find new reference node
    _ref = get_single(set(cmds.ls(type='reference')).difference(_cur_refs))

    # Fbx ref seems to update timeline (?)
    if host.t_range() != _rng:
        host.set_range(*_rng)

    return _class(_ref)


def find_ref(namespace=None, filter_=None, catch=False, class_=None,
             prefix=None, extn=None, verbose=0):
    """Find reference with given namespace.

    Args:
        namespace (str): namespace to match
        filter_ (str): apply filter to names list
        catch (bool): no error on fail to find matching ref
        class_ (FileRef): override FileRef class
        prefix (str): match reference by prefix (prefix references don't
            use namespaces)
        extn (str): filter by extension
        verbose (int): print process data

    Returns:
        (FileRef): matching ref
    """
    _refs = find_refs(namespace=namespace, filter_=filter_, class_=class_,
                      prefix=prefix, extn=extn)
    lprint('Found {:d} refs'.format(len(_refs)), _refs, verbose=verbose)
    return get_single(_refs, catch=catch, name='ref')


def find_refs(namespace=None, filter_=None, class_=None, prefix=None,
              unloaded=True, nested=False, extn=None):
    """Find reference with given namespace.

    Args:
        namespace (str): namespace to match
        filter_ (str): namespace filter
        class_ (FileRef): override FileRef class
        prefix (str): filter by reference prefix (prefix references don't
            use namespaces)
        unloaded (bool): return unloaded refs (default is True)
        nested (bool): include nested references in results
        extn (str): filter by extension

    Returns:
        (FileRef list): scene refs
    """
    _refs = _read_refs(class_=class_)

    if namespace:
        _refs = [_ref for _ref in _refs if _ref.namespace == namespace]
    if extn:
        _refs = [_ref for _ref in _refs if _ref.extn == extn]
    if prefix:
        _refs = [_ref for _ref in _refs if _ref.prefix == prefix]
    if filter_:
        _refs = [_ref for _ref in _refs
                 if _ref.namespace and passes_filter(_ref.namespace, filter_)]
    if not unloaded:
        _refs = [_ref for _ref in _refs if _ref.is_loaded()]
    if not nested:
        _refs = [_ref for _ref in _refs
                 if not _ref.reference_query(parent=True)]
    return _refs


def get_selected(catch=False, multi=False, class_=None, verbose=0):
    """Get selected ref.

    Args:
        catch (bool): no error on None
        multi (bool): allow multiple selections
        class_ (class): override ref class
        verbose (int): print process data

    Returns:
        (FileRef): selected file ref
        (None): if no ref is selected and catch used

    Raises:
        (ValueError): if no ref is selected
    """
    _sel_ref_nodes = cmds.ls(selection=True, type='reference')
    lprint('SEL REF NODES', _sel_ref_nodes, verbose=verbose)

    _ref_nodes = set(_sel_ref_nodes)
    for _node in cmds.ls(selection=True):
        try:
            _ref_node = cmds.referenceQuery(_node, referenceNode=True)
        except RuntimeError:
            continue
        _ref_nodes.add(_ref_node)
    _ref_nodes = sorted(_ref_nodes)
    lprint('REF NODES', _ref_nodes, verbose=verbose)

    _class = class_ or FileRef
    _refs = [_class(_ref_node) for _ref_node in _ref_nodes]
    lprint('REFS', _refs, verbose=verbose)
    if multi:
        return _refs
    _ref = get_single(
        _refs, fail_message='No reference selected', catch=catch)
    if not _ref:
        return None
    return _ref


def obtain_ref(file_, namespace, class_=None):
    """Search for a reference and create it if it doesn't exist.

    Args:
        file_ (str): file to reference
        namespace (str): reference namespace
        class_ (FileRef): override FileRef class
    """
    _ref = find_ref(namespace, catch=True, class_=class_)
    if _ref:
        if abs_path(_ref.path) != abs_path(file_):
            print 'A', abs_path(_ref.path)
            print 'B', abs_path(file_)
            raise ValueError('Path mismatch')
        return _ref

    return create_ref(file_=file_, namespace=namespace, class_=class_)


def _read_refs(class_=None):
    """Read references in the scene.

    Args:
        class_ (FileRef): override FileRef class - any refs which raise
            a ValueError on init are excluded from the list

    Returns:
        (FileRef list): list of refs
    """
    _class = class_ or FileRef
    _refs = []
    for _ref_node in cmds.ls(type='reference'):
        try:
            _ref = _class(_ref_node)
        except ValueError:
            continue
        _refs.append(_ref)
    return _refs
