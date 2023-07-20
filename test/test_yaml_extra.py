"""
Test extension and wrapper functions to the ruaml.yaml package
provided in yaml_parse_extra.

"""
import os
from ymlconv.yaml_parser_extra import load_commented_yaml, AddressNode

source_dir = os.path.dirname(os.path.abspath(__file__))

def test_addres_node():
    fname_in = os.path.join(source_dir, "files_path_set", "test_yaml_wrap.yaml")
    an = AddressNode.root(load_commented_yaml(fname_in))
    assert str(an.address) == '/!!map'
    node_addrs = [str(n.address) for n in an.iterate_nodes()]
    assert node_addrs == [
        '/!!map',
        '/!!map/a!!seq',
        '/!!map/a!!seq/0!MyType',
        '/!!map/a!!seq/1!!int',
        '/!!map/b!!map',
        '/!!map/b!!map/a!!seq',
        '/!!map/b!!map/a!!seq/0!!str',
        '/!!map/c!MySeq',
        '/!!map/c!MySeq/0!!int',
        '/!!map/d!MyMap',
        '/!!map/d!MyMap/a!!int',
    ]