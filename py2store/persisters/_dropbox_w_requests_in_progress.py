import zipfile

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    import requests


shared_folder_url = 'https://www.dropbox.com/sh/0ru09jmk0w9tdnr/AAA-PPON2sYmwUUoGQpBQh1Ia?dl=1'
shared_file_url = 'https://www.dropbox.com/s/wx9j4zm7zv9zffd/0b98e2af76c94a0a9cc2808866dd62de?dl=0'

txt_filepath = 'test_file.txt'
zip_filepath = 'test_file.zip'


def download(url, path):
    headers = {'user-agent': 'Wget/1.16 (linux-gnu)'}
    response = requests.get(url, stream=True, headers=headers)
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    if url.endswith('dl=1'):
        unzip(path)


def unzip(path, output_path='.'):
    with zipfile.ZipFile(path, 'r') as zip_ref:
        zip_ref.extractall(output_path)
