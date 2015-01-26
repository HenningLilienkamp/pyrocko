
import os
import time
import unittest
import tempfile
import shutil

import common
from pyrocko import squirrel, util, pile, io


class SquirrelTestCase(unittest.TestCase):

    test_files = [
        ('test1.mseed', 'mseed'),
        ('test2.mseed', 'mseed'),
        ('test1.sac', 'sac'),
        ('test1.stationxml', 'stationxml'),
        ('test2.stationxml', 'stationxml'),
        ('test1.stations', 'pyrocko_stations'),
        ('test1.cube', 'datacube')]

    def test_detect(self):
        for (fn, format) in SquirrelTestCase.test_files:
            fpath = common.test_data_file(fn)
            self.assertEqual(format, squirrel.detect_format(fpath))

    def test_load(self):
        ii = 0
        for (fn, format) in SquirrelTestCase.test_files:
            fpath = common.test_data_file(fn)
            for nut in squirrel.iload(fpath, content=[]):
                ii += 1

        assert ii == 396

        ii = 0
        sq = squirrel.Squirrel()
        for (fn, _) in SquirrelTestCase.test_files:
            fpath = common.test_data_file(fn)
            for nut in squirrel.iload(fpath, content=[], squirrel=sq):
                ii += 1

        assert ii == 396

        ii = 0
        for (fn, _) in SquirrelTestCase.test_files:
            fpath = common.test_data_file(fn)
            for nut in squirrel.iload(fpath, content=[], squirrel=sq):
                ii += 1

        ii = 0
        for (fn, _) in SquirrelTestCase.test_files:
            fpath = common.test_data_file(fn)
            for nut in squirrel.iload(fpath, squirrel=sq):
                ii += 1

        assert ii == 396

    def test_query_mtimes(self):
        fpaths = [
            common.test_data_file(fn)
            for (fn, _) in SquirrelTestCase.test_files]

        sq = squirrel.Squirrel()
        for nut in squirrel.iload(fpaths, squirrel=sq, content=[]):
            pass

        mtimes_ref = dict(
            (fpath, os.stat(fpath)[8]) for fpath in fpaths)

        def check(fpaths, mtimes):
            for fpath, mtime in zip(fpaths, mtimes):
                self.assertEqual(mtimes_ref.get(fpath, None), mtime)

        fpaths1 = fpaths + ['nonexistent']
        mtimes = sq.get_mtimes(fpaths)
        check(fpaths, mtimes)

        fpaths2 = fpaths1[::-2]
        mtimes2 = sq.get_mtimes(fpaths2)
        check(fpaths2, mtimes2)

        mtimes3 = [sq.get_mtime(fpath) for fpath in fpaths1]
        check(fpaths1, mtimes3)

    def test_dig_undig(self):
        nuts = []
        for file_name in 'abcde':
            for file_element in xrange(2):
                nuts.append(squirrel.Nut(
                    file_name=file_name,
                    file_format='test',
                    file_mtime=0.0,
                    file_segment=0,
                    file_element=file_element,
                    kind='test'))

        sq = squirrel.Squirrel()
        sq.dig(nuts)

        data = []
        for file_name in 'abcde':
            nuts2 = sq.undig(file_name)
            for nut in nuts2:
                data.append((nut.file_name, nut.file_element))
        self.assertEqual(
            [(file_name, i) for file_name in 'abcde' for i in xrange(2)],
            data)

        data = []
        for fn, nuts2 in sq.undig_many(filenames=['a', 'c']):
            for nut in nuts2:
                data.append((nut.file_name, nut.file_element))

        self.assertEqual(
            [(file_name, i) for file_name in 'ac' for i in xrange(2)],
            data)

    def benchmark_load(self):
        dir = '/tmp/testdataset_d'
        if not os.path.exists(dir):
            common.make_dataset(dir, tinc=36., tlen=1*common.D)

        fns = sorted(util.select_files([dir]))

        ts = []

        if True:
            cachedirname = tempfile.mkdtemp('testcache')

            ts.append(time.time())
            pile.make_pile(
                fns, fileformat='detect', cachedirname=cachedirname)

            ts.append(time.time())
            print 'pile, initial scan: %g' % (ts[-1] - ts[-2])

            pile.make_pile(
                fns, fileformat='detect', cachedirname=cachedirname)

            ts.append(time.time())
            print 'pile, rescan: %g' % (ts[-1] - ts[-2])

            shutil.rmtree(cachedirname)

        else:
            ts.append(time.time())
            ii = 0
            for fn in fns:
                for tr in io.load(fn, getdata=True):
                    ii += 1

            ts.append(time.time())
            print 'plain load baseline: %g' % (ts[-1] - ts[-2])

        ts.append(time.time())

        ii = 0
        for nut in squirrel.iload(fns, content=[]):
            ii += 1

        ts.append(time.time())
        print 'squirrel, no db: %g' % (ts[-1] - ts[-2])

        ii = 0
        dbfilename = '/tmp/squirrel.db'
        if os.path.exists(dbfilename):
            os.unlink(dbfilename)
        sq = squirrel.Squirrel(dbfilename)

        print len(fns)

        for nut in squirrel.iload(fns, content=[], squirrel=sq):
            ii += 1

        print ii

        ts.append(time.time())
        print 'squirrel, initial scan: %g' % (ts[-1] - ts[-2])

        ii = 0
        for nut in squirrel.iload(fns, content=[], squirrel=sq):
            ii += 1

        ts.append(time.time())
        print 'squirrel, rescan: %g' % (ts[-1] - ts[-2])

        ii = 0
        for nut in squirrel.iload(fns, content=[], squirrel=sq,
                                  check_mtime=False):
            ii += 1

        ts.append(time.time())
        print 'squirrel, rescan, no mtime check: %g' % (ts[-1] - ts[-2])

        for fn, nuts in sq.undig_many(fns):
            ii += 1

        ts.append(time.time())
        print 'squirrel, pure undig: %g' % (ts[-1] - ts[-2])

        sq.choose(fns)

        ts.append(time.time())
        print 'squirrel, select workload: %g' % (ts[-1] - ts[-2])


if __name__ == "__main__":
    util.setup_logging('test_catalog', 'debug')
    def dostuff():
        unittest.main()

    import cProfile
    cProfile.run('dostuff()')
