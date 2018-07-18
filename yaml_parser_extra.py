import types
import re

import ruamel.yaml as ruml
from ruamel.yaml.comments import CommentedMap, CommentedSeq

CommentsTag = ruml.comments.Tag


class CommentedScalar:
    """
    Class to store all scalars with their tags
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
    if tag_suffix is None:
        orig_tag = None
    else:
        orig_tag = "!" + tag_suffix
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
    yml.constructor.add_multi_constructor("!", construct_any_tag)
    return yml

