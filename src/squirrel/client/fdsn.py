import time
import os
import copy
import hashlib
import logging
import cPickle as pickle
import os.path as op
from .base import Source, Selection
from pyrocko.client import fdsn
from pyrocko.io import stationxml

from pyrocko import config, util

fdsn.g_timeout = 60.

logger = logging.getLogger('pyrocko.squirrel.client.fdsn')

sites_not_supporting_startbefore = ['geonet']


def diff(fn_a, fn_b):
    try:
        if os.stat(fn_a)[8] != os.stat(fn_b)[8]:
            return True

    except OSError:
        return True

    with open(fn_a, 'rb') as fa:
        with open(fn_b, 'rb') as fb:
            while True:
                a = fa.read(1024)
                b = fb.read(1024)
                if a != b:
                    return True

                if len(a) == 0 or len(b) == 0:
                    return False


def ehash(s):
    return hashlib.sha1(s.encode('utf8')).hexdigest()


class FDSNSource(Source):

    def __init__(
            self, site,
            user_credentials=None, auth_token=None,
            age_max=3600.,
            cache_dir=None):

        Source.__init__(self)

        self._site = site
        self._selection = None
        self._age_max = age_max

        s = site
        if auth_token:
            s += auth_token
        if user_credentials:
            s += user_credentials[0]
            s += user_credentials[1]

        self._auth_token = auth_token
        self._user_credentials = user_credentials

        self._cache_dir = op.join(
            cache_dir or config.config().cache_dir,
            'fdsn',
            ehash(s))

        util.ensuredir(self._cache_dir)
        self.load_selection()

    def get_selection_filename(self):
        return op.join(self._cache_dir, 'selection.pickle')

    def get_channels_filename(self):
        return op.join(self._cache_dir, 'channels.stationxml')

    def load_selection(self):
        fn = self.get_selection_filename()
        if op.exists(fn):
            with open(fn, 'rb') as f:
                self._selection = pickle.load(f)
        else:
            self._selection = None

    def dump_selection(self):
        with open(self.get_selection_filename(), 'wb') as f:
            pickle.dump(self._selection, f)

    def outdated(self):
        filename = self.get_channels_filename()
        try:
            t = os.stat(filename)[8]
            return t < time.time() - self._age_max
        except OSError:
            return True

    def update_channel_inventory(self, selection=None):
        if selection is None:
            selection = Selection()

        if self._selection and self._selection.contains(selection) \
                and not self.outdated():

            if self._channel_sx is None:
                logger.info(
                    'using cached channel information for site %s'
                    % self._site)

                #channel_sx = stationxml.load_xml(
                #    filename=self.get_channels_filename())

            return

        if self._selection:
            selection = copy.deepcopy(self._selection)
            selection.add(selection)

        extra_args = {
            'iris': dict(matchtimeseries=True),
        }.get(self._site, {})

        if self._site in sites_not_supporting_startbefore:
            if selection.tmin is not None:
                extra_args['starttime'] = selection.tmin
            if selection.tmax is not None:
                extra_args['endtime'] = selection.tmax

        else:
            if selection.tmin is not None:
                extra_args['endafter'] = selection.tmin
            if selection.tmax is not None:
                extra_args['startbefore'] = selection.tmax

        extra_args.update(
            includerestricted=(
                self._user_credentials is not None
                or self._auth_token is not None))

        logger.info(
            'querrying channel information from site %s'
            % self._site)

        channel_sx = fdsn.station(
            site=self._site,
            format='text',
            level='channel',
            **extra_args)

        channel_sx.created = None  # timestamp would ruin diff

        fn = self.get_channels_filename() 
        fn_temp = fn + '.%i.temp' % os.getpid()
        channel_sx.dump_xml(filename=fn_temp)

        if diff(fn, fn_temp):
            os.rename(fn_temp, fn)
            squirrel.iload(fn)
        else:
            logger.info('no change')
            os.unlink(fn_temp)

        self._selection = selection
        self.dump_selection()

    def get_stations(self, tmin=None, tmax=None):
        selection = Selection(tmin, tmax)
        self.update_channel_inventory(selection)
