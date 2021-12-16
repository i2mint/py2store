"""
testing local files functionality
"""
from py2store import FileReader
from py2store.test import minifs_dirpath, minifs_join


def test_file_reader():
    # Test it "raw"
    s = FileReader(minifs_dirpath)
    assert sorted(s) == sorted([minifs_join(f) for f in ['x.bin', 'A/', 'B/']])

    # Now, we'll use mk_relative_path_store to make the tests more "natural"
    # (and test it's interaction with mk_relative_path_store)
    from py2store import mk_relative_path_store

    s = mk_relative_path_store(FileReader(minifs_dirpath), prefix_attr='rootdir')
    assert sorted(s) == sorted(['x.bin', 'A/', 'B/'])  # that works!
    assert s['x.bin'] == b'contents of x'
    ss = s['A/']
    assert isinstance(ss, FileReader)

    # FIXME: The mk_relative_path_store wrapper doesn't play well with the recursion.
    #   Here, we're back to absolute paths. Make it work!
    list(ss) == [minifs_join('A/a')]  # we would like it to be 'A/a' simply
