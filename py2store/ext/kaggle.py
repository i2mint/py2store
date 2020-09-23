"""
Moved to otosense/haggle
Made pip installable.
"""

import warnings

warnings.warn(
    "Moved to otosense/haggle and has it's own pip installable package. Change code to reflect",
    DeprecationWarning)

from haggle.dacc import *