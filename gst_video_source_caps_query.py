from __future__ import division

from path import path
#import gst


class GstVideoSourceCapabilities(object):
    def __init__(self, video_source):
        pipeline = gst.Pipeline()
        source_pad = video_source.get_pad('src')
        video_sink = gst.element_factory_make('autovideosink', 'video_sink')
        pipeline.add(video_source)
        pipeline.add(video_sink)
        video_source.link(video_sink)
        pipeline.set_state(gst.STATE_READY)
        self.allowed_caps = [dict([(k, c[k])
                for k in c.keys()] + [('name', c.get_name())])
                        for c in source_pad.get_allowed_caps()]
        pipeline.set_state(gst.STATE_NULL)
        self._allowed_info = self.unique_settings(self.allowed_caps)

    def extract_format(self, format_obj):
        return format_obj['format'].fourcc

    def extract_fps(self, framerate_obj):
        framerates = []
        try:
            for fps in framerate_obj['framerate']:
                framerates.append(fps.num / fps.denom)
        except TypeError:
            fps = framerate_obj['framerate']
            framerates.append(fps.num / fps.denom)
        return framerates

    @property
    def framerates(self):
        return self._allowed_info['framerates']

    @property
    def dimensions(self):
        return self._allowed_info['dimensions']

    @property
    def formats(self):
        return self._allowed_info['formats']

    @property
    def names(self):
        return self._allowed_info['names']

    def get_allowed_caps(self, dimensions=None, framerate=None, format_=None, name=None):
        allowed_caps = self.allowed_caps[:]
        if dimensions:
            allowed_caps = [c for c in allowed_caps if dimensions == (
                    c['width'], c['height'])]
        if framerate:
            allowed_caps = [c for c in allowed_caps
                    if framerate in self.extract_fps(c)]
        if format_:
            allowed_caps = [c for c in allowed_caps
                    if format_ == self.extract_format(c)]
        if name:
            allowed_caps = [c for c in allowed_caps if name == c['name']]
        return allowed_caps

    def unique_settings(self, caps):
        framerates = []
        for d in caps:
            framerates.extend(self.extract_fps(d))
        framerates = tuple(sorted(set(framerates)))
        dimensions = tuple(sorted(set([(d['width'], d['height'])
                for d in caps])))
        formats = tuple(sorted(set([self.extract_format(d)
                for d in caps])))
        names = tuple(sorted(set([d['name'] for d in caps])))
        info = {}
        for k, v in (('framerates', framerates), ('dimensions', dimensions),
                ('formats', formats), ('names', names)):
            if v:
                info[k] = v
        return info


def parse_args():
    """Parses arguments, returns ``(options, args)``."""
    from argparse import ArgumentParser

    parser = ArgumentParser(description="""\
Queries for supported video modes for GStreamer input devices.""",
                            epilog="""\
(C) 2012  Christian Fobel, licensed under the terms of GPLv2.""",
                           )
    parser.add_argument('--width',
                    action='store', dest='width', type=int,
                    help='video width (required if height is specified)')
    parser.add_argument('--height',
                    action='store', dest='height', type=int,
                    help='video height (required if width is specified)')
    parser.add_argument('--fps',
                    action='store', dest='fps', type=int,
                    help='video frames per second')
    parser.add_argument('--format',
                    action='store', dest='format_',
                    help='video format')
    parser.add_argument('--stream_name',
                    action='store', dest='stream_name',
                    help='stream name (e.g., "video/x-raw-yuv")')
    args = parser.parse_args()
    
    return args




if __name__ == '__main__':
    args = parse_args()

    # For Linux
    video_source = gst.element_factory_make('v4l2src', 'video_source')

    for video_device in path('/dev/v4l/by-id').listdir():
        video_source.set_property('device', video_device)
        video_caps = GstVideoSourceCapabilities(video_source)
        kwargs = {'framerate': args.fps, 'format_': args.format_, }
        if args.width and args.height:
            kwargs['dimensions'] = (args.width, args.height)
        print '%s:' % video_device.name
        for k, v in video_caps.unique_settings(video_caps.get_allowed_caps(**kwargs)).items():
            print 3 * ' ', '%s: %s' % (k, v)
