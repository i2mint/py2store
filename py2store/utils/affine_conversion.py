class AffineConverter(object):
    """
    Getting a callable that will perform an affine conversion.
    Note, it does it as
        (val - offset) * scale
    (Note slope-intercept style (though there is the .from_slope_and_intercept constructor method for that)

    Inverse is available through the inv method, performing:
        val / scale + offset

    >>> convert = AffineConverter(scale=0.5, offset=1)
    >>> convert(0)
    -0.5
    >>> convert(10)
    4.5
    >>> convert.inv(4)
    9.0
    >>> convert.inv(4.5)
    10.0
    """

    def __init__(self, offset=0.0, scale=1.0):
        self.offset = offset
        self.scale = scale

    @classmethod
    def from_slope_and_intercept(cls, slope=1.0, intercept=0.0):
        cls(offset=-intercept / slope, scale=slope)

    def __call__(self, x):
        return (x - self.offset) * self.scale

    def inv(self, x):
        return x / self.scale + self.offset

    def map(self, seq):
        return (self(x) for x in seq)

    def invmap(self, seq):
        return (self.inv(x) for x in seq)


def get_affine_converter_and_inverse(offset=0, scale=1, source_type_cast=None, target_type_cast=None):
    """
    Getting two affine functions with given scale and offset, that are inverse of each other. Namely (for input val):
        (val - offset) * scale and val / scale + offset
    Note this is not "slope intercept" style!!

    The source_type_cast and target_type_case (optional), allow the user to specify if these transformations need to
    be further cast to a given type.
    :param scale:
    :param offset:
    :param source_type_cast: function to apply to input
    :param target_type_cast: function to apply to output
    :return: Two single val functions: affine_converter, inverse_affine_converter

    Note: Code is a lot more complex than the basic operations it performs. The reason was a worry of efficiency since
    the functions that are returned are intended to be used in long loops.

    See also: ocore.utils.conversion.AffineConverter

    >>> affine_converter, inverse_affine_converter = get_affine_converter_and_inverse(scale=0.5, offset=1)
    >>> affine_converter(0)
    -0.5
    >>> affine_converter(10)
    4.5
    >>> inverse_affine_converter(4)
    9.0
    >>> inverse_affine_converter(4.5)
    10.0
    >>> affine_converter, inverse_affine_converter = get_affine_converter_and_inverse(
    ...                                                 offset=1, scale=0.5, target_type_cast=int)
    >>> affine_converter(10)
    4
    """
    if offset != 0:
        if scale != 1:
            if target_type_cast is None:
                def affine_converter(val):
                    return (val - offset) * scale
            else:
                def affine_converter(val):
                    return target_type_cast((val - offset) * scale)
            if source_type_cast is None:
                def inverse_affine_converter(val):
                    return val / scale + offset
            else:
                def inverse_affine_converter(val):
                    return source_type_cast(val / scale + offset)
        else:  # scale 1, so can be ignored
            if target_type_cast is None:
                def affine_converter(val):
                    return val - offset
            else:
                def affine_converter(val):
                    return target_type_cast(val - offset)
            if source_type_cast is None:
                def inverse_affine_converter(val):
                    return val + offset
            else:
                def inverse_affine_converter(val):
                    return source_type_cast(val + offset)
    else:  # no offset
        if target_type_cast is None:
            def affine_converter(val):
                return scale * val
        else:
            def affine_converter(val):
                return target_type_cast(scale * val)
        if source_type_cast is None:
            def inverse_affine_converter(val):
                return val / scale
        else:
            def inverse_affine_converter(val):
                return source_type_cast(val / scale)

    return affine_converter, inverse_affine_converter
