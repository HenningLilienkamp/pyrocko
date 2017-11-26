from __future__ import division, print_function, absolute_import
import unittest
import os
import time
from pyrocko import util
import functools
import logging
import socket
import os.path as op
import tempfile

import numpy as num

from pyrocko import io, trace

logger = logging.getLogger('pyrocko.test.common')

benchmark_results = []

g_matplotlib_inited = False

H = 3600.
D = 3600.*24.


def matplotlib_use_agg():
    global g_matplotlib_inited
    if not g_matplotlib_inited:
        import matplotlib
        matplotlib.use('Agg')  # noqa
        g_matplotlib_inited = True


def test_data_file_no_download(fn):
    return os.path.join(os.path.split(__file__)[0], 'data', fn)


def make_dataset(dir=None, nstations=10, nchannels=3, tlen=10*D, deltat=0.01,
                 tinc=1*H):

    if dir is None:
        dir = tempfile.mkdtemp('_test_squirrel_dataset')

    tref = util.str_to_time('2015-01-01 00:00:00')

    nblocks = int(round(tlen / tinc))

    for istation in range(nstations):
        for ichannel in range(nchannels):
            for iblock in range(nblocks):
                tmin = tref + iblock*tinc
                nsamples = int(round(tinc/deltat))
                ydata = num.random.randint(-1000, 1001, nsamples).astype(
                    num.int32)

                tr = trace.Trace(
                    '', '%04i' % istation, '', '%03i' % ichannel,
                    tmin=tmin,
                    deltat=deltat,
                    ydata=ydata)

                io.save([tr], op.join(dir, '%s/%c/%b.mseed'))

    return dir


def test_data_file(fn):
    fpath = test_data_file_no_download(fn)
    if not os.path.exists(fpath):
        if not have_internet():
            raise unittest.SkipTest(
                'need internet access to download data file')

        url = 'http://data.pyrocko.org/testing/' + fn
        logger.info('downloading %s' % url)
        util.download_file(url, fpath)

    return fpath


def have_internet():
    try:
        return 0 < len([
            (s.connect(('8.8.8.8', 80)), s.close())
            for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]])

    except OSError:
        return False


require_internet = unittest.skipUnless(have_internet(), 'need internet access')


def have_gui():
    display = os.environ.get('DISPLAY', '')
    if not display:
        return False

    try:
        from pyrocko.gui.qt_compat import qc  # noqa
    except ImportError:
        return False

    return True


require_gui = unittest.skipUnless(have_gui(), 'no gui support configured')


class Benchmark(object):
    def __init__(self, prefix=None):
        self.prefix = prefix or ''
        self.show_factor = False
        self.results = []

    def __call__(self, func):
        def stopwatch(*args):
            t0 = time.time()
            name = self.prefix + func.__name__
            result = func(*args)
            elapsed = time.time() - t0
            self.results.append((name, elapsed))
            return result
        return stopwatch

    def labeled(self, label):
        def wrapper(func):
            @functools.wraps(func)
            def stopwatch(*args):
                t0 = time.time()
                result = func(*args)
                elapsed = time.time() - t0
                self.results.append((label, elapsed))
                return result
            return stopwatch
        return wrapper

    def __str__(self, header=True):
        if not self.results:
            return 'No benchmarks ran'
        tmax = max([r[1] for r in self.results])

        rstr = ['Benchmark results']
        if self.prefix != '':
            rstr[-1] += ' - %s' % self.prefix

        if self.results:
            indent = max([len(name) for name, _ in self.results])
        else:
            indent = 0
        rstr.append('=' * (indent + 17))
        rstr.insert(0, rstr[-1])

        if not header:
            rstr = []

        for res in self.results:
            rstr.append(
                '{0:<{indent}}{1:.8f} s'.format(*res, indent=indent+5))
            if self.show_factor:
                rstr[-1] += '{0:8.2f} x'.format(tmax/res[1])
        if len(self.results) == 0:
            rstr.append('None ran!')

        return '\n'.join(rstr)

    def clear(self):
        self.results = []
