import os

def get_root_path():
    _full_path = os.path.realpath(__file__)
    path, __file = os.path.split(_full_path)

    return path + "/"
