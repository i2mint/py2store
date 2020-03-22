"""Tools to cache time-series data.
"""

from collections import deque
from py2store.utils.affine_conversion import get_affine_converter_and_inverse


class RegularTimeseriesCache:
    """
    A type that pretends to be a (possibly very large) list, but where contents of the list are populated as they are
    needed. Further, the indexing of the list can be overwritten for the convenience of the user.

    The canonical application is where we have segments of continuous waveform indexed by utc microseconds timestamps.

    It is convenient to be able to read segments of this waveform as if it was one big waveform (handling the
    discontinuities gracefully), and have the choice of using (relative or absolute) integer indices or utc indices.
    """

    def __init__(self, data_rate=1, time_rate=1, maxlen=None):
        self.buffer = deque(iterable=(), maxlen=maxlen)
        self.data_rate = data_rate
        self.time_rate = time_rate
        self.time_per_data = self.time_rate / self.data_rate
        self.data_per_time = self.data_rate / self.time_rate
        self.bt = None
        self.tt = None

    def time_to_idx(self, t):
        return (t - self.bt) * self.data_per_time

    def idx_to_time(self, idx):
        return idx * self.time_per_data + self.bt

    def update(self, bt):
        pass

    def __getitem__(self, item):
        if isinstance(item, slice):
            start = item.start
