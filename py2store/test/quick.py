import pytest
from py2store import QuickStore

store = QuickStore()  # will print what (tmp) rootdir it is choosing

# Write something and then read it out again
store['foo'] = 'baz'
assert store['foo'] == 'baz'
# Go see that there is now a file in the rootdir, named 'foo'!

# Write something more complicated
store['hello/world'] = [1, 'flew', {'over': 'a', "cuckoo's": map}]
assert store['hello/world'] == [1, 'flew', {'over': 'a', "cuckoo's": map}]

# do you have the key 'foo' in your store?
assert ('foo' in store) == True

# how many items do you have now?
assert len(store) >= 2  # can't be sure there were no elements before, so can't assert == 2

# delete the stuff you've written
del store['foo']
del store['hello/world']

if __name__ == '__main__':
    pytest.main()
