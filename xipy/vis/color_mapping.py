"""This module contains some modifications of Matplotlib colormapping code.
see:
http://matplotlib.sourceforge.net/

MPL LICENSE:
http://matplotlib.svn.sourceforge.net/viewvc/matplotlib/trunk/matplotlib/license/LICENSE?view=markup

COLOR SCHEMES LICENSE:
http://matplotlib.svn.sourceforge.net/viewvc/matplotlib/trunk/matplotlib/license/LICENSE_COLORBREWER?view=markup

"""
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap, colorConverter
import matplotlib.cbook as cbook
from matplotlib._cm import datad
import numpy as np
import numpy.ma as ma

parts = np.__version__.split('.')
NP_MAJOR, NP_MINOR = map(int, parts[:2])
# true if clip supports the out kwarg
NP_CLIP_OUT = NP_MAJOR>=1 and NP_MINOR>=2

class MixedAlphaColormap(LinearSegmentedColormap):

    N = 256
    i_under = 256
    i_over = 257
    i_bad = 258
    
    @staticmethod
    def lut_indices(X):
        """
        Convert the normalized scalar array X to indices into this
        colormap's LUT, including indices into i_bad, i_over, i_under.
        """
        mask_bad = None
        if not cbook.iterable(X):
            vtype = 'scalar'
            xa = np.array([X])
        else:
            vtype = 'array'
            # force a copy here -- the ma.array and filled functions
            # do force a cop of the data by default - JDH
            xma = ma.array(X, copy=True)
            xa = xma.filled(0)
            mask_bad = ma.getmask(xma)
        if xa.dtype.char in np.typecodes['Float']:
            np.putmask(xa, xa==1.0, 0.9999999) #Treat 1.0 as slightly less than 1.
            # The following clip is fast, and prevents possible
            # conversion of large positive values to negative integers.

            if NP_CLIP_OUT:
                np.clip(xa * MixedAlphaColormap.N, -1,
                        MixedAlphaColormap.N, out=xa)
            else:
                xa = np.clip(xa * MixedAlphaColormap.N,
                             -1, MixedAlphaColormap.N)
                
            xa = xa.astype(int)
        # Set the over-range indices before the under-range;
        # otherwise the under-range values get converted to over-range.
        np.putmask(xa, xa>MixedAlphaColormap.N-1, MixedAlphaColormap.i_over)
        np.putmask(xa, xa<0, MixedAlphaColormap.i_under)
        if mask_bad is not None and mask_bad.shape == xa.shape:
            np.putmask(xa, mask_bad, MixedAlphaColormap.i_bad)
        return xa

    def fast_lookup(self, Xi, alpha=1.0, bytes=False):
        """
        *X* is already in the form of LUT indices, simply perform
        an indexing into the LUT and return
        """
        if not self._isinit: self._init()
        if not cbook.iterable(Xi):
            vtype = 'scalar'
            Xi = np.array([Xi])
        else:
            vtype = 'array'
        if cbook.iterable(alpha):
            if len(alpha) != self.N:
                raise ValueError('Provided alpha LUT is not the right length')
            alpha = np.clip(alpha, 0, 1)
            # repeat the last alpha value for i_under, i_over
            alpha = np.r_[alpha, alpha[-1], alpha[-1]]
        else:
            alpha = min(alpha, 1.0) # alpha must be between 0 and 1
            alpha = max(alpha, 0.0)

        self._lut[:-1,-1] = alpha  # Don't assign global alpha to i_bad;
                                   # it would defeat the purpose of the
                                   # default behavior, which is to not
                                   # show anything where data are missing.
        if bytes:
            lut = (self._lut * 255).astype(np.uint8)
        else:
            lut = self._lut
        rgba = np.empty(shape=Xi.shape+(4,), dtype=lut.dtype)
        lut.take(Xi, axis=0, mode='clip', out=rgba)
                    #  twice as fast as lut[xa];
                    #  using the clip or wrap mode and providing an
                    #  output array speeds it up a little more.
        if vtype == 'scalar':
            rgba = tuple(rgba[0,:])
        return rgba
        
    def __call__(self, X, alpha=1.0, bytes=False):
        """
        *X* is either a scalar or an array (of any dimension).
        If scalar, a tuple of rgba values is returned, otherwise
        an array with the new shape = oldshape+(4,). If the X-values
        are integers, then they are used as indices into the array.
        If they are floating point, then they must be in the
        interval (0.0, 1.0).
        Alpha must be a scalar.
        If bytes is False, the rgba values will be floats on a
        0-1 scale; if True, they will be uint8, 0-255.
        """
        if X.dtype.char not in np.typecodes['AllInteger']:
            xa = MixedAlphaColormap.lut_indices(X)
        else:
            xa = X
        rgba = self.fast_lookup(xa, alpha=alpha, bytes=bytes)
        return rgba
        
    # unfortunately need to grab this too, since it's staticmethod
    # and not classmethod
    @staticmethod
    def from_list(name, colors, N=256, gamma=1.0):
        """
        Make a linear segmented colormap with *name* from a sequence
        of *colors* which evenly transitions from colors[0] at val=0
        to colors[-1] at val=1.  *N* is the number of rgb quantization
        levels.
        Alternatively, a list of (value, color) tuples can be given
        to divide the range unevenly.
        """

        if not cbook.iterable(colors):
            raise ValueError('colors must be iterable')

        if cbook.iterable(colors[0]) and len(colors[0]) == 2 and \
                not cbook.is_string_like(colors[0]):
            # List of value, color pairs
            vals, colors = zip(*colors)
        else:
            vals = np.linspace(0., 1., len(colors))

        cdict = dict(red=[], green=[], blue=[])
        for val, color in zip(vals, colors):
            r,g,b = colorConverter.to_rgb(color)
            cdict['red'].append((val, r, r))
            cdict['green'].append((val, g, g))
            cdict['blue'].append((val, b, b))

        return MixedAlphaColormap(name, cdict, N, gamma)

cmap_d = dict()

# reverse all the colormaps.
# reversed colormaps have '_r' appended to the name.

def _reverser(f):
    def freversed(x):
        return f(1-x)
    return freversed

def revcmap(data):
    data_r = {}
    for key, val in data.iteritems():
        if callable(val):
            valnew = _reverser(val)
                # This doesn't work: lambda x: val(1-x)
                # The same "val" (the first one) is used
                # each time, so the colors are identical
                # and the result is shades of gray.
        else:
            valnew = [(1.0 - a, b, c) for a, b, c in reversed(val)]
        data_r[key] = valnew
    return data_r

LUTSIZE = mpl.rcParams['image.lut']

_cmapnames = datad.keys()  # need this list because datad is changed in loop

for cmapname in _cmapnames:
    cmapname_r = cmapname+'_r'
    cmapspec = datad[cmapname]
    if 'red' in cmapspec:
        datad[cmapname_r] = revcmap(cmapspec)
        cmap_d[cmapname] = MixedAlphaColormap(
                                cmapname, cmapspec, LUTSIZE)
        cmap_d[cmapname_r] = MixedAlphaColormap(
                                cmapname_r, datad[cmapname_r], LUTSIZE)
    else:
        revspec = list(reversed(cmapspec))
        if len(revspec[0]) == 2:    # e.g., (1, (1.0, 0.0, 1.0))
            revspec = [(1.0 - a, b) for a, b in revspec]
        datad[cmapname_r] = revspec

        cmap_d[cmapname] = MixedAlphaColormap.from_list(
                                cmapname, cmapspec, LUTSIZE)
        cmap_d[cmapname_r] = MixedAlphaColormap.from_list(
                                cmapname_r, revspec, LUTSIZE)

locals().update(cmap_d)
