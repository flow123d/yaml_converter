import types
import re
from typing import *
import dataclasses as dc
import ruamel.yaml as ruml

from ruamel.yaml.comments import CommentedMap, CommentedSeq, CommentedBase

"""
This module should provide a wrappers for the ruaml.yaml in order
to:
1. better document used functionalities and interfaces
2. fill gaps in providead features
3. hide changes between ruamel.yaml versions

Currently there is no full wrapping as we need to make changes to the YAML file representation
while preserving the comments and other representation details. That is exactly role of ruamel.yaml.
"""

CommentsTag = ruml.comments.Tag


class CommentedScalar(CommentedBase):
    """
    Class to store a scalar with its tag.
    ruamel.yaml seems to store only tags presented at input,
    for pattern matching we need tags for all nodes.
    """
    original_constructors = {}

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        representer = dumper.yaml_representers[type(data.value).__mro__[0]]
        node = representer(dumper, data.value)
        if data.tag.value is None:
            tag = node.tag
        elif data.tag.value.startswith(u'tag:yaml.org,2002'):
            tag = node.tag
        else:
            tag = data.tag.value
        # print("val: ", data.value, "repr: ", node.value, "tag: ", tag)
        return dumper.represent_scalar(tag, node.value)

    def __init__(self, tag, value):
        self.tag.value = tag
        self.value = value

    @property
    def tag(self):
        # type: () -> Any
        if not hasattr(self, CommentsTag.attrib):
            setattr(self, CommentsTag.attrib, CommentsTag())
        return getattr(self, CommentsTag.attrib)


def construct_any_tag(self, tag_suffix, node):
    '''
    Used for tag prefix '!'
    Seems to somehow force reintroduction of the '!' prefix to the tag value.
    Intent not clear.
    :param self:
    :param tag_suffix:
    :param node:
     :return:
    '''
    if tag_suffix is None:
        orig_tag = None
    else:
        orig_tag = tag_suffix
    if isinstance(node, ruml.ScalarNode):

        implicit_tag = self.composer.resolver.resolve(ruml.ScalarNode, node.value, (True, None))
        if implicit_tag in self.yaml_constructors:
            # constructor = CommentedScalar.original_constructors[implicit_tag]
            constructor = self.yaml_constructors[implicit_tag]
        else:
            constructor = self.construct_undefined

        data = constructor(self, node)
        if isinstance(data, types.GeneratorType):
            generator = data
            data = next(generator)  # type: ignore

        scal = CommentedScalar(orig_tag, data)
        yield scal

    elif isinstance(node, ruml.SequenceNode):
        for seq in self.construct_yaml_seq(node):
            seq.yaml_set_tag(orig_tag)
            yield seq
    elif isinstance(node, ruml.MappingNode):
        for map in self.construct_yaml_map(node):
            map.yaml_set_tag(orig_tag)
            yield map
    else:
        for dummy in self.construct_undefined(node):
            yield dummy


"""
def construct_scalar(self, node):
    gen = construct_any_tag(self, None, node)
    for item in gen:
        yield item
"""

'''
Helpers:
'''


def parse_yaml_str(yaml_string):
    '''
    Parse given string in YAML format and return the YAML tree.
    In combination with other methodsAdd key 'key_name' to the map at 'path', and assign to it the given 'key_value'.
    The 'key_value' can be scalar, dict or list.
    '''
    pass


def is_list_node(node):
    return type(node) in [list, CommentedSeq]


def is_map_node(node):
    return type(node) in [dict, CommentedMap]


def is_scalar_node(node):
    return type(node) in [CommentedScalar, ruml.scalarfloat.ScalarFloat, int, float, bool, type(None), str]


def is_map_key(key_str):
    return re.match('^[a-zA-Z][a-zA-Z_0-9]*$', key_str)





# def dump_commented_scalar(cls, data):
#    data.dump(cls)

def represent_commented_seq(cls, data):
    if data.tag.value is None:
        tag = u'tag:yaml.org,2002:seq'
    else:
        tag = data.tag.value
    return cls.represent_sequence(tag, data)


def get_yaml_serializer():
    """
    Get YAML serialization/deserialization object with proper
    configuration for conversion.
    :return: Confugured instance of ruamel.yaml.YAML.
    """
    yml = ruml.YAML(typ='rt')
    yml.indent(mapping=2, sequence=4, offset=2)
    yml.width=120
    yml.representer.add_representer(CommentedScalar, CommentedScalar.to_yaml)
    yml.representer.add_representer(CommentedSeq, represent_commented_seq)
    # Seems this has no effect, tag_prefix is possibly without leading '!'
    yml.constructor.add_multi_constructor("!", construct_any_tag)
    return yml



def get_node_tag(node):
    try:
        tag = node.tag.value
        tag = tag.replace('tag:yaml.org,2002:', '!') # represent default tags as !<defult_name_suffix>
        return tag
    except:
        return ""





def unify_tree_dfs(node):
    """
    Convert tree to unified form, where all nodes are CommentedMap, CommentedSeq or CommentedScalar.
    :param node:
    :return:
    """
    if is_list_node(node):
        for idx in range(len(node)):
            node[idx] = unify_tree_dfs(node[idx])
        if type(node) != CommentedSeq:
            return CommentedSeq(node)
        node.yaml_set_tag(u'tag:yaml.org,2002:seq')
    elif is_map_node(node):
        for key, child in node.items():
            node[key] = unify_tree_dfs(child)
        if type(node) != CommentedMap:
            return CommentedMap(node)
        node.yaml_set_tag(u'tag:yaml.org,2002:map')
    elif is_scalar_node(node):
        if type(node) != CommentedScalar:
            tags_for_types = {
                float: u'tag:yaml.org,2002:float',
                int: u'tag:yaml.org,2002:int',
                bool: u'tag:yaml.org,2002:bool',
                str: u'tag:yaml.org,2002:str',
                type(None): u'tag:yaml.org,2002:null'}
            tag = None
            for x_type, x_tag in tags_for_types.items():
                if isinstance(node, x_type):
                    tag = x_tag
            # assert type(node) in tags_for_types
            # tag = tags_for_types[type(node)]
            return CommentedScalar(tag, node)
    else:
        assert False, "Unsupported node type: {}".format(type(node))
    return node



class Address(list):
    '''
    Class to represent an address in the yaml file including the tag info.
    '''
    def __str__(self):
        '''
        Full string representation.
        :return:
        '''
        return "/" + "/".join([str(key) + "!" + str(tag) for key, tag in self])

    def s(self):
        '''
        Representation without tag info.
        :return:
        '''
        return "/" + "/".join([str(key) for key, tag in self])


@dc.dataclass
class AddressNode:
    _address: List[Tuple[str, str]] = dc.field()
    _nodes_path: List[CommentedBase] = dc.field()
    # TODO: introduce own wrapper object CommentedNode providing at least
    # some guaranteed uniformity

    @classmethod
    def file_root(cls, fname: str, loader=None):
        if loader is None:
            loader = get_yaml_serializer()
        with open(fname, "r") as f:
            root_node = unify_tree_dfs(loader.load(f))
        root_address = [('', get_node_tag(root_node))]
        root_node_path = [root_node]
        return cls(root_address, root_node_path)

    def _child(self, key, child):
        new_addr = self._address + [(key, get_node_tag(child))]
        return AddressNode(new_addr, self._nodes_path + [child])

    def childs(self):
        """
        Iterator that yields AddressNode childs if the
        self.yaml_node is a map or sequence.
        The address attributes are produced in particular.

        :return:
        """
        yaml_node = self.yaml_node
        if is_list_node(yaml_node):
            key_node_iter = enumerate(yaml_node)
        elif is_map_node(yaml_node):
            key_node_iter = yaml_node.items()
        else:
            return None

        yield from (self._child(key, node) for key, node in key_node_iter)

    def iterate_nodes(self):
        yield self
        for ch in self.childs():
            yield from ch.iterate_nodes()

    @property
    def address(self):
        return Address(self._address)

    @property
    def yaml_node(self):
        return self._nodes_path[-1]

    @property
    def nodes_path(self):
        return self._nodes_path

#
# def iterate_nodes(an: AddressNode):
#     """
#     Iterate over subtree using DFS
#     :param nodes: list of nodes from root of the whole tree to root of the iterated subtree.
#     :param address: Address instance (address of the node) of the root of subtree
#
#     :yield: (nodelist, address) ... for all nodes of the subtree
#     """
#     yield an
#     current = an.yaml_node
#     childs_iter = an.childs()
#     if childs_iter is None:
#         return
#
#     for key, child in childs_iter:
#         #tag = get_node_tag(child)[1:]  # remove leading '!'
#         tag = get_node_tag(child)   # tag without '!' alrady
#     yield from an.childs()(nodes + [child], address.add(key, tag))
#
