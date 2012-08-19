from __future__ import division

from path import path
import gst


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
                for k in c.keys()]) for c in source_pad.get_allowed_caps()]
        pipeline.set_state(gst.STATE_NULL)
        _framerates = []
        for d in self.allowed_caps:
            try:
                for fps in d['framerate']:
                    _framerates.append(fps.num / fps.denom)
            except TypeError:
                fps = d['framerate']
                _framerates.append(fps.num / fps.denom)
        self._framerates = tuple(sorted(set(_framerates)))
        self._dimensions = tuple(sorted(set([(d['width'], d['height'])
                for d in self.allowed_caps])))
        self._formats = tuple(sorted(set([d['format'].fourcc
                for d in self.allowed_caps])))

    @property
    def framerates(self):
        return self._framerates

    @property
    def dimensions(self):
        return self._dimensions

    @property
    def formats(self):
        return self._formats


if __name__ == '__main__':
    # For Linux
    video_source = gst.element_factory_make('v4l2src', 'video_source')

    for video_device in path('/dev/v4l/by-id').listdir():
        video_source.set_property('device', video_device)
        video_caps = GstVideoSourceCapabilities(video_source)
        print '%s:' % video_device.name
        print 3 * ' ', video_caps.framerates
        print 3 * ' ', video_caps.dimensions
        print 3 * ' ', video_caps.formats
        print 72 * '-'
