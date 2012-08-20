#!/usr/bin/env python

import distutils.core

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

# Setup script for path

kw = {
    'name': "gst_video_source_caps_query",
    'version': "{{ ___VERSION___ }}",
    'description': "Query video sources for supported modes",
    'author': "Christian Fobel",
    'author_email': "christian@fobel.net",
    'url': "http://github.com/cfobel/python___gst_video_source_caps_query",
    'license': "GPLv2 License",
    'packages': ['gst_video_source_caps_query'],
    'cmdclass': dict(build_py=build_py),
}


# If we're running Python 2.3, add extra information
if hasattr(distutils.core, 'setup_keywords'):
    if 'classifiers' in distutils.core.setup_keywords:
        kw['classifiers'] = [
            'Development Status :: 5 - Production/Stable',
            'License :: OSI Approved :: MIT License',
            'Intended Audience :: Developers',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules'
          ]
    if 'download_url' in distutils.core.setup_keywords:
        urlfmt = "http://github.com/cfobel/python___gst_video_source_caps_query/tarball/%s"
        kw['download_url'] = urlfmt % kw['version']


distutils.core.setup(**kw)
