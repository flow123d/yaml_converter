import types
import re
from typing import *
import dataclasses as dc
import ruamel.yaml as ruml
from ruamel.yaml.comments import CommentedMap, CommentedSeq, CommentedBase, TaggedScalar


"""
This module should provide a wrappers for the ruaml.yaml in order
to:
1. better document used functionalities and interfaces
2. fill gaps in providead features
3. hide changes between ruamel.yaml versions

Currently there is no full wrapping as we need to make changes to the YAML file representation
while preserving the comments and other representation details. That is exactly role of ruamel.yaml.

Provided functionalities (updated 23/07/19):
loading:
  - load_commented_yaml, get_yaml_serializer, construct_any_tag
    - construct any custom tag using its default type constructor and then setting the custom tag
    - keep custom tags with the '!' prefix
  - unify_node_tree:
    - scalar nodes are wrapped into a common CommentedScalar class
      in order to provide sort of uniformity
    - introduce node._path_set_tag attribute to store the tag used for the path matching
      via. the get_node_tag function
  - get_node_tag:
    - return the tag representation used for the matching, without '!' prefix
      None -> implicit tag in default short representation, e.g. !str, !int, etc.
      default_tag -> short representation
      custom_tag (beginning with '!') -> just the suffix without leading '!'
representation:
  - CommentedScalar: provides a uniform representation of the scalar nodes      
"""

CommentsTag = ruml.comments.Tag

def load_commented_yaml(fname: str, loader=None):
    """
    Load a YAML to the nodes with tags and comments.
    Introduce path_set_tags.
    """
    if loader is None:
        loader = get_yaml_serializer()
    with open(fname, "r") as f:
        root_node = unify_tree_dfs(loader.load(f))
    return root_node

def get_yaml_serializer():
    """
    Get YAML serialization/deserialization object with proper
    configuration for conversion.
    :return: Confugured instance of ruamel.yaml.YAML.
    """
    yml = ruml.YAML(typ='rt')
    yml.indent(mapping=2, sequence=4, offset=2)
    yml.width=120
    # loader
    yml.constructor.add_multi_constructor("!", construct_any_tag)
    # dumper
    yml.representer.add_representer(CommentedScalar, CommentedScalar.to_yaml)
    #yml.representer.add_representer(CommentedSeq, represent_commented_seq)
    return yml



def construct_any_tag(self, tag_suffix, node):
    '''
    A YAML construction of the custom tag nodes.
    Should not be called for the default tag nodes.
    :param self: a yaml constructor
    :param tag_suffix: the custom tag without leading '!'
    :param node: current parsed node
     :return: new node
    '''
    assert tag_suffix
    #if tag_suffix is None:
    #    orig_tag = None
    #else:
    orig_tag = '!' + tag_suffix
    if isinstance(node, ruml.ScalarNode):
        # Construct
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
        for seq in self.construct_yaml_seq(node): # yields a single CommentedSeq just before it is filled with the data
             seq.yaml_set_tag(orig_tag)
             yield seq
    elif isinstance(node, ruml.MappingNode):
        for map in self.construct_yaml_map(node): # yields a single CommentedMap just before it is filled with the data
            map.yaml_set_tag(orig_tag)
            yield map
    else:
        for dummy in self.construct_undefined(node):
            yield dummy


class CommentedScalar(CommentedBase):
    """
    Class to store a scalar with its tag.
    ruamel.yaml otherwise produce instances of individual Python scalar types which
    complicates later generic pattern matching.
    We seems to store only tags presented at input,
    for pattern matching we need tags for all nodes.
    """
    original_constructors = {}

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)

    @classmethod
    def to_yaml(cls, dumper, data:'CommentedScalar'):
        representer = dumper.yaml_representers[type(data.value).__mro__[0]]
        node : ruml.ScalarNode = representer(dumper, data.value)
        if data.tag.value is None:
            # not clear how this could happen and what case should be resolved here
            tag = node.tag
        elif data.tag.value.startswith(u'tag:yaml.org,2002'):
            # try to simplify representation of the default tags
            tag = node.tag
        else:
            # Whe the value is used only in this case
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





'''
Helpers:
'''


def is_list_node(node):
    return type(node) in [list, CommentedSeq]


def is_map_node(node):
    return type(node) in [dict, CommentedMap]


def is_scalar_node(node):
    return type(node) in [CommentedScalar, TaggedScalar, ruml.scalarfloat.ScalarFloat, int, float, bool, type(None), str]


def is_map_key(key_str):
    return re.match('^[a-zA-Z][a-zA-Z_0-9]*$', key_str)





# def dump_commented_scalar(cls, data):
#    data.dump(cls)

# def represent_commented_seq(cls, data):
#     if data.tag.value is None:
#         tag = u'tag:yaml.org,2002:seq'
#     else:
#         tag = '!' + data.tag.value
#     return cls.represent_sequence(tag, data)


# def represent_commented_map(cls, data):
#     if data.tag.value is None:
#         tag = u'tag:yaml.org,2002:map'
#     else:
#         tag = '!' + data.tag.value
#     return cls.represent_mapping(tag, data)






def unify_tree_dfs(node):
    """
    Convert tree to unified form, where all nodes are CommentedMap, CommentedSeq or CommentedScalar,
    default tags are presented explicitely as '!<full_default tag>
    and custom tags are in form '!<tag>'
    :param node:
    :return:
    """
    if is_list_node(node):
        for idx in range(len(node)):
            node[idx] = unify_tree_dfs(node[idx])
        if type(node) != CommentedSeq:
            node =  CommentedSeq(node)
        set_path_tag(node, '!seq')
        #if node.tag.value is None:
        #    node.yaml_set_tag(u'tag:yaml.org,2002:seq')
    elif is_map_node(node):
        for key, child in node.items():
            node[key] = unify_tree_dfs(child)
        if type(node) != CommentedMap:
            node = CommentedMap(node)
        set_path_tag(node, '!map')
        #if node.tag.value is None:
        #    node.yaml_set_tag(u'tag:yaml.org,2002:map')
    elif is_scalar_node(node):
        if type(node) != CommentedScalar:
            node = CommentedScalar(None, node)
        set_path_tag(node, implicit_path_set_tag(node.value))

    else:
        assert False, "Unsupported node type: {}".format(type(node))
    return node



__tags_for_types = {
    float: '!float', #u'tag:yaml.org,2002:float',
    int: '!int', #u'tag:yaml.org,2002:int',
    bool: '!bool', #u'tag:yaml.org,2002:bool',
    str: '!str', #u'tag:yaml.org,2002:str',
    type(None): 'null', #u'tag:yaml.org,2002:null'}
    ruml.scalarfloat.ScalarFloat: '!float', #u'tag:yaml.org,2002:float',
}

def implicit_path_set_tag(node_value):
    """
    Return implicit tag for the scalar node values.
    :param node:
    :return:
    """
    try:
        return __tags_for_types[type(node_value)]
    except:
        assert False, "Unsupported node value type: {}".format(type(node_value))

def set_path_tag(node, implicit_tag):
    if node.tag is None or not node.tag.value:
        node._path_set_tag = implicit_tag
    else:
        node_tag = node.tag.value
        assert node_tag.startswith('!')
        node._path_set_tag = node_tag[1:]


def get_node_tag(node):
    try:
        return node._path_set_tag
    except:
        assert False, "Node {} has no _path_set_tag".format(node)



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
        return  "/".join([str(key) for key, tag in self])


@dc.dataclass
class AddressNode:
    _address: List[Tuple[str, str]] = dc.field()
    _nodes_path: List[CommentedBase] = dc.field()
    # TODO: introduce own wrapper object CommentedNode providing at least
    # some guaranteed uniformity

    @classmethod
    def root(cls, node: CommentedBase):
        root_address = [('', get_node_tag(node))]
        root_node_path = [node]
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

