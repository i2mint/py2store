How to run these tests:

To run all (from root project path):

    $ pytest

To run specific ones:

    $ pytest [test path]::[test class]::[test method]
    
For example:

    $ pytest tests/test_forms.py::TestMyForm::test_validate_smth

Other useful params:
 - `--capture=no`    - Always show live logs/prints, not only on errors. Use it, if you want to debug with `pdb`/`ipdb`.
 - `--fulltrace`     - Show traceback on `CTRL+C`
 
More info at http://doc.pytest.org/en/latest/getting-started.html
