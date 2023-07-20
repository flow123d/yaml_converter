import os
import re
from path_set import PathSet
from yaml_parser_extra import get_yaml_serializer, load_commented_yaml

source_dir = os.path.dirname(os.path.abspath(__file__))

class tree_fixture(object):
    def __init__(self, fname):
        self.fname = fname
        self.tree = load_commented_yaml(fname)

    def __enter__(self):
        return self.tree
    def __exit__(self, type, value, traceback):
        pass
    def check(self, pattern, ref_paths):
        ps = PathSet(pattern)
        match_paths = {adr_node.address.s() for adr_node in  ps.iterate(self.tree)}
        assert set(ref_paths) == match_paths



def test_path_set():
    fname_in = os.path.join(source_dir, "files_path_set", "test_path_set.in.yaml")
    t = tree_fixture(fname_in)
    t.check("a/#", ["/a/0", "/a/1"])
    t.check("b/*", ["/b/a", "/b/b"])
    t.check("c/**", ["/c/a", "/c/a/a", "/c/b", "/c/b/0"])
    # t.check("c/**", ["/c/a", "/c/a/a", "/c/b", "/c/b/0"])
    # TODO test tag matching
    # TODO test alternatives
    # TODO test tail matching, review where it is used
    # TODO test value matching




