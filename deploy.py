import subprocess

# # TODO: Both of these are python. Change to use python objects directly.
print('--------------------------- setup_output ---------------------------')
setup_output = subprocess.run('python setup.py sdist bdist_wheel'.split(' '))
# print(f"{setup_output}\n")

print('--------------------------- upload_output ---------------------------')
upload_output = subprocess.run('python -m twine upload dist/*'.split(' '))
# print(f"{upload_output.decode()}\n")

# import twine
