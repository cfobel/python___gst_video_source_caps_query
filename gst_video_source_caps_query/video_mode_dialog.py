from __future__ import division
from pprint import pprint, pformat
from multiprocessing import Process, Pipe
import time

try:
    import pygst
    pygst.require("0.10")
except ImportError:
    pass
import gst
import glib
from gst_video_source_caps_query import GstVideoSourceManager, FilteredInput,\
        get_available_video_modes, get_video_source_configs
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
        video_modes = get_available_video_modes(
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
    video_modes = get_available_video_modes(format_='YUY2')
    selected_mode = select_video_mode(video_modes)
    if selected_mode:
        return selected_mode['device'], GstVideoSourceManager.get_caps_string(selected_mode)
    else:
        return None


def get_video_mode_form(video_modes=None):
    if video_modes is None:
        video_modes = get_available_video_modes(
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
    device_key, devices = get_video_source_configs()
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


def get_pipeline(video_source=None):
    pipeline = gst.Pipeline()
    video_sink = gst.element_factory_make('autovideosink', 'video_sink')
    if video_source is None:
        video_source = select_video_source()
    pipeline.add(video_sink, video_source)
    video_source.link(video_sink)
    return pipeline


class _GStreamerProcess(Process):
    def __init__(self, *args, **kwargs):
        super(_GStreamerProcess, self).__init__(*args, **kwargs)
    
    def start(self, pipe_connection):
        self._pipe = pipe_connection
        return super(_GStreamerProcess, self).start()

    def run(self):
        self._pipeline = None
        self._check_count = 0
        self._main_loop = glib.MainLoop()
        glib.timeout_add(500, self._update_state)
        self._main_loop.run()

    def _finish(self):
        self._cleanup_pipeline()
        self._main_loop.quit()

    def _cleanup_pipeline(self):
        if self._pipeline:
            del self._pipeline
            self._pipeline = None

    def _process_request(self, request):
        if request['command'] == 'create':
            '''
            Create a pipeline
            '''
            if self._pipeline is None:
                device, caps_str = request['video_caps']
                video_source = create_video_source(device, caps_str)
                self._pipeline = get_pipeline(video_source)
        elif request['command'] == 'start':
            if self._pipeline:
                self._pipeline.set_state(gst.STATE_PLAYING)
        elif request['command'] == 'stop':
            if self._pipeline:
                self._pipeline.set_state(gst.STATE_NULL)
        elif request['command'] == 'reset':
            self._cleanup_pipeline()
        elif request['command'] == 'finish':
            self._finish()
            raise SystemExit
        elif request['command'] == 'select_video_caps':
            result = select_video_caps()
            return result

    def _update_state(self):
        while self._pipe.poll():
            request = self._pipe.recv()
            print '  [request] {}'.format(request)
            try:
                result = self._process_request(request)
                if request.get('ack', False):
                    self._pipe.send({'result': result})
            except SystemExit:
                return False
        return True


class GStreamerProcess(object):
    def select_video_caps(self):
        self.master_pipe.send({'command': 'select_video_caps',
                'ack': True})
        result = self.master_pipe.recv()
        return result['result']

    def start(self):
        self.master_pipe.send({'command': 'start', 'ack': True})

    def run(self):
        self.master_pipe, self.worker_pipe = Pipe()
        self._process = _GStreamerProcess(args=(self.worker_pipe, ))
        self._process.start(self.worker_pipe)
        self.master_pipe.send({'command': 'reset'})
        video_caps = self.select_video_caps()
        self.master_pipe.send({'command': 'create', 'ack': True,
                'video_caps': video_caps})
        result = self.master_pipe.recv()
        print 'sending START'
        self.master_pipe.send({'command': 'start'})
        time.sleep(1)
        print 'sending STOP'
        self.master_pipe.send({'command': 'stop'})
        for i in range(3):
            time.sleep(1)
            print 'sending START'
            self.master_pipe.send({'command': 'start'})
            time.sleep(1)
            print 'sending STOP'
            self.master_pipe.send({'command': 'stop'})
        print 'sending FINISH'
        self.master_pipe.send({'command': 'finish'})
        self._process.join()


if __name__ == '__main__':
    print 'Using GStreamerProcess'
    p = GStreamerProcess()
    p.run()
    p.run()
