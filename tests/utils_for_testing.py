dflt_test_data = {
    "a01.csv": b"1,2,3\n4,5,6\n",
    "a02.txt": b"Something interesting",
    "Sub/aru": b"outback",
    "Sub/way.bin": b"menu",
    "Sub/standard/housing": b"conditions",
    "Sub/standard/work/performance": b"write-up",
    "Sub/standard/work/quality": b"stats",
}


def write_test_data(test_store, test_data=dflt_test_data):
    """Write the `test_data` into the `test_store`
    test_store needs to be a store that accepts binary values and string keys where forward-slash is permitted"""
    n = len(test_store)
    if n > 0:
        user_wants_it = check_if_the_user_wants_to_delete_all_the_elements(n)
        if user_wants_it:
            for k in test_store:
                print(f"Deleting {k}")
                del test_store[k]
        else:
            print("\nOkay, I won't delete anything")
    for i, (k, v) in enumerate(test_data.items(), 1):
        test_store[k] = v


def check_if_the_user_wants_to_delete_all_the_elements(n):
    confirmation = (
        "I really want to delete these {n} elements forever, so help me god."
    )
    conf_msg = confirmation.format(n="XX")
    msg = (
            f"Your store wasn't empty. In fact it has {n} elements."
            + "I can delete them for you, \n"
            + "but you'll have to be explicit about this wish for.\n"
            + f"If you really want to delete all {n} elements in your store, type\n--> {conf_msg}\n"
            + " without the --> and where XX is replaced by that number of elements I mentioned twice "
            + "(if you're not paying attention, you shouldn't be allowed to do it).\n"
            + "If not, just type anything (or nothing) and hit enter.\n"
            + "So go on, what do you want to do?\n--> ".format(conf_msg=conf_msg)
    )
    feedback = input(msg)
    return feedback == confirmation.format(n=n)
