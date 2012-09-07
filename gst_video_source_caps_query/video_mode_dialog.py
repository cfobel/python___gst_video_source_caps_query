from __future__ import division
from pprint import pprint, pformat
from multiprocessing import Process

try:
    import pygst
    pygst.require("0.10")
except ImportError:
    pass
import gst
import glib
from gst_video_source_caps_query import GstVideoSourceManager, FilteredInput
from pygtkhelpers.ui.extra_widgets import Enum, Form
from pygtkhelpers.ui.form_view_dialog import FormViewDialog, create_form_view
from pygtkhelpers.ui.extra_dialogs import field_entry_dialog


def get_video_mode_map(video_modes):
    format_cap = lambda c: '[%s] ' % getattr(c['device'], 'name',
            c['device'])[:20] + '{width:4d}x{height:d} {fps:2.0f}fps '\
                    '({fourcc:s})'.format(
                            fps=c['framerate'].num / c['framerate'].denom, **c)
    video_mode_map = dict([(format_cap(c), c) for c in video_modes]) 
    return video_mode_map


def get_video_mode_enum(video_modes=None):
    if video_modes is None:
        video_modes = GstVideoSourceManager.get_available_video_modes(
                format_='YUY2')
    video_mode_map = get_video_mode_map(video_modes)
    video_keys = sorted(video_mode_map.keys())
    return Enum.named('video_mode').valued(*video_keys)


def select_video_mode(video_modes):
    video_mode_map = get_video_mode_map(video_modes)
    video_keys = sorted(video_mode_map.keys())
    enum = get_video_mode_enum(video_modes)
    valid, response = field_entry_dialog(enum.using(default=video_keys[0]))
    try:
        if valid:
            return video_mode_map[response]
    except:
        raise ValueError, 'No video mode matching: %s' % response


def select_video_caps():
    video_modes = GstVideoSourceManager.get_available_video_modes(format_='YUY2')
    selected_mode = select_video_mode(video_modes)
    if selected_mode:
        return selected_mode['device'], GstVideoSourceManager.get_caps_string(selected_mode)
    else:
        return None


def get_video_mode_form(video_modes=None):
    if video_modes is None:
        video_modes = GstVideoSourceManager.get_available_video_modes(
                format_='YUY2')
    video_mode_map = get_video_mode_map(video_modes)
    video_keys = sorted(video_mode_map.keys())
    form = Form.of(Enum.named('video_mode').valued(
            *video_keys).using(default=video_keys[0]))
    return form


def get_video_mode_form_view(video_modes=None, values=None, use_markup=True):
    form_view = create_form_view(get_video_mode_form(), values=values,
            use_markup=use_markup)
    return form_view


def select_video_source():
    result = select_video_caps()    
    if result is None:
        return None
    device, caps_str = result
    return create_video_source(device, caps_str)


def create_video_source(device, caps_str):
    video_source = GstVideoSourceManager.get_video_source()
    device_key, devices = GstVideoSourceManager.get_video_source_configs()
    video_source.set_property(device_key, device)
    filtered_input = FilteredInput('filtered_input', caps_str, video_source)
    return filtered_input


def test_pipeline():
    pipeline = gst.Pipeline()
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    video_source = select_video_source()
    pipeline.add(video_sink, video_source)
    video_source.link(video_sink)
    pipeline.set_state(gst.STATE_PLAYING)
    glib.MainLoop().run()


if __name__ == '__main__':
    p = Process(target=test_pipeline)
    p.start()
    p.join()
