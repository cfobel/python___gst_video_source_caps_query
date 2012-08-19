from __future__ import division
import logging
import platform

from path import path
import gst


class GstVideoSourceCapabilities(object):
    def __init__(self, video_source):
        pipeline = gst.Pipeline()
        source_pad = video_source.get_pad('src')
        video_sink = gst.element_factory_make('autovideosink', 'video_sink')
        pipeline.add(video_source)
        pipeline.add(video_sink)
        try:
            video_source.link(video_sink)
            pipeline.set_state(gst.STATE_READY)
            self.allowed_caps = [dict([(k, c[k])
                    for k in c.keys()] + [('name', c.get_name())])
                            for c in source_pad.get_allowed_caps()]
            pipeline.set_state(gst.STATE_NULL)
            self._allowed_info = self.unique_settings(self.allowed_caps)
        finally:
            del pipeline

    def extract_format(self, format_obj):
        return format_obj['format'].fourcc

    def extract_fps(self, framerate_obj):
        framerates = []
        try:
            for fps in framerate_obj['framerate']:
                framerates.append(fps.num / fps.denom)
        except TypeError:
            if isinstance(framerate_obj['framerate'], gst.FractionRange):
                for fps in (framerate_obj['framerate'].low,
                        framerate_obj['framerate'].high):
                    framerates.append(fps.num / fps.denom)
            else:
                fps = framerate_obj['framerate']
                framerates.append(fps.num / fps.denom)
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

def get_video_source():
    if platform.system() == 'Linux':
        video_source = gst.element_factory_make('v4l2src', 'video_source')
    else:
        video_source = gst.element_factory_make('dshowvideosrc', 'video_source')
    return video_source


def get_video_source_configs(video_source):
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    if platform.system() == 'Linux':
        devices = path('/dev/v4l/by-id').listdir()
        device_key = 'device'
    else:
        devices = video_source.probe_get_values_name('device-name')
        device_key = 'device-name'
    return device_key, devices


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


def main():
    args = parse_args()

    video_source = get_video_source()
    device_key, devices = get_video_source_configs(video_source)

    for video_device in devices:
        video_source.set_property(device_key, video_device)
        try:
            video_caps = GstVideoSourceCapabilities(video_source)
        except gst.LinkError:
            logging.warning('error querying device %s (skipping)' % video_device)
            continue
        kwargs = {'framerate': args.fps, 'format_': args.format_, }
        if args.width and args.height:
            kwargs['dimensions'] = (args.width, args.height)
        print '%s:' % getattr(video_device, 'name', video_device)
        for k, v in video_caps.unique_settings(video_caps.get_allowed_caps(**kwargs)).items():
            print 3 * ' ', '%s: %s' % (k, v)
        print 72 * '-'


if __name__ == '__main__':
    main()
