# coding=utf-8
import pandas as pd
from .config import cfg
from .parameters import ParameterSet
from .param import Parameter
from .drivers import MPAGE
#from .parameter import MPAGE


from .config import cfg



class Bundle(ParameterSet):
    light_column_names = ['hjd', 'ph', 'L1', 'L2', 'Lcombined', 'Lnorm', 'separation', 'magnorm', 'mag',
                          'timeshift']
    veloc_column_names = ['hjd', 'ph', 'relrv1', 'relrv2', 'eclipsecorr1', 'eclipsecorr2', 'rv1', 'rv2',
                          'timeshift', 'rvshift3b']

    def __init__(self, wdversion=None):
        super(Bundle, self).__init__()
        if wdversion is None:
            wdversion = cfg().get('executables', 'version')
        self.wdversion = wdversion
        self._light = None
        self._veloc = None


    @classmethod
    def default_binary(cls, default_file=None, bundleno=0):
        from .io import Reader_lcin
        if default_file is None:
            wdversion = cfg().get('executables', 'version')
            default_file = f'lcin.default.{wdversion}.active'
        b = cls.open(Reader_lcin.default_wd_file_abspath(default_file), bundleno=bundleno)
        return b

    @classmethod
    def open(cls, filepath, bundleno=0):
        from .io import Reader_lcin
        reader = Reader_lcin(filepath)
        return reader.bundles[bundleno]

    def __repr__(self):
        return '\n'.join([
            ' '.join([repr(v) for v in l.values()])
            for l in self.lines
        ])

    def __setitem__(self, k, v):
        try:
            el = self[k]
            el.val = v
        except KeyError as e:
            if isinstance(v, (Parameter, list)):
                super(Bundle, self).__setitem__(k, v)
            else:
                raise e

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def lc(self):
        """Runs WD `lc` program. No need to be called directly

        An access to `light` or `veloc` properties calculates data if needed"""
        from .runners import LcRunner
        r = LcRunner()
        r.run(self)

    def run_compute(self):
        """Alias of `lc()`"""
        self.lc()


    def reset(self):
        """Resets cashed results from lc"""
        self._light = None
        self._veloc = None

    @property
    def light(self):
        """Calculated (by LC) light curve"""
        if not self._light:
            self['MPAGE'] = MPAGE.LIGHT
            self.lc()
        return self._light

    @property
    def light_df(self):
        """Calculated (by LC) light curve, returns pandas DataFrame"""
        return pd.DataFrame(self.light, columns=self.light_column_names)

    @light.setter
    def light(self, val):
        self._light = val

    @property
    def veloc(self):
        """Calculated (by LC) RV curve"""
        if not self._veloc:
            self['MPAGE'] = MPAGE.VELOC
            self.lc()
        return self._veloc

    @property
    def veloc_df(self):
        """Calculated (by LC) radial velocity curve, returns pandas DataFrame"""
        return pd.DataFrame(self.veloc, columns=self.veloc_column_names)

    @veloc.setter
    def veloc(self, val):
        self._veloc = val





