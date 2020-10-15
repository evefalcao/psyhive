"""Tools for Supercel Clashmas project."""

import hou

from psyhive import icons, tk2, host, qt
from psyhive.utils import get_plural

ICON = icons.EMOJI.find("Christmas Tree")


def build_scene(shot='log0320', step='previz', submitter='/out/submitter1',
                submit=True):
    """Build scene from template.

    This will:

     - update the timeline to the shotgun range
     - updates the camera rop to the latest camcache from this shot
     - remove any abcs in /obj and replace them with the latest version
       of each abc in this shot
     - press the submit button on the given qube subitter

    Args:
        shot (str): name of shot to update to
        step (str): step to search for abcs
        submitter (str): path to submitter rop
        submit (bool): execute submission
    """
    _trg_shot = tk2.find_shot(shot)
    _step = _trg_shot.find_step_root(step)
    _src_work = tk2.cur_work()
    _root = hou.node('/obj')

    _submitter = hou.node(submitter)
    if not _submitter:
        raise RuntimeError('Missing submitter '+submitter)
    _cam = _root.node('renderCam')
    if not _submitter:
        raise RuntimeError('Missing camera /obj/renderCam')

    # Update frame range
    _rng = _trg_shot.get_frame_range()
    host.set_range(*_rng)

    # Update cam
    _cam_abc = _step.find_output_file(
        output_type='camcache', extn='abc', verbose=1,
        version='latest')
    print 'CAM ABC', _cam_abc
    _cam.parm('fileName').set(_cam_abc.path)
    _cam_pos = _cam.position()

    # Flush abcs
    for _node in _root.children():
        if _node.type().name().startswith('psyhou.general::alembic_import'):
            _node.destroy()

    # Bring in abcs
    for _idx, _abc in enumerate(_step.find_output_files(
            output_type='animcache', extn='abc', version='latest')):
        print 'ABC', _abc

        if _root.node(_abc.basename):
            _root.node(_abc.basename).destroy()

        _node = _root.createNode(
            node_type_name='psyhou.general::alembic_import::0.1.0',
            node_name=_abc.basename)
        _node.setPosition(_cam_pos + hou.Vector2(0, - 1 - 0.8*_idx))
        _node.parm('fileName').set(_abc.path)
        _node.parm('shop_materialpath').set('/shop/set')
        _node.parm('loadmode').set(1)
        _node.setColor(hou.Color([0, 0.5, 0]))
        print 'NODE', _node
        print

    _trg_work = _src_work.map_to(Shot=_trg_shot.name).find_next()
    print 'WORK', _trg_work

    _trg_work.save(comment='Generated by scene builder tool')

    if submit:
        print _submitter.parm('submit_node').pressButton()


def batch_submit_shots(step='previz', submitter='/out/submitter1'):
    """Batch submit shots selected from a list.

    Args:
        step (str): step to search for abcs
        submitter (str): path to submitter rop
    """
    _shots = [_shot.name for _shot in tk2.find_shots()]
    _shots = qt.multi_select(
        _shots, title='Select shots',
        msg='Select shots to submit')
    for _shot in qt.progress_bar(_shots, 'Submitting {:d} shot{}'):
        print 'BUILD SCENE', _shot
        build_scene(shot=_shot, step=step, submitter=submitter)

    print 'SUBMITTED {:d} SHOT{}'.format(
        len(_shots), get_plural(_shots).upper())