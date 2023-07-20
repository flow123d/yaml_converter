

import itertools
import re
import logging
from .yaml_parser_extra import AddressNode, is_scalar_node



def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]



class PathSet(object):
    @staticmethod
    def expand_alternatives(pattern):
        """
        For given pattern with alternatives return list of patters for all valid alternative combinations.
        :param pattern:
        :return:
        """
        # pass through all combinations of alternatives (X|Y|Z)
        list_of_alts = []
        for alt_group in re.finditer('\([^|]*(\|[^|]*)*\)', pattern):
            before_group = pattern[0:alt_group.start()]
            list_of_alts.append([before_group])

            # swallow parenthesis
            alts = alt_group.group(0)[1:-1]
            alts = alts.split('|')
            list_of_alts.append(alts)
            pattern = pattern[alt_group.end():]
        list_of_alts.append([pattern])

        return [''.join(pp_list) for pp_list in itertools.product(*list_of_alts)]

    """
    Set of places in YAML file to which apply a given rule
    """

    def __init__(self, path_patterns):
        """
        Construct a path search object. This can be combined with a YAML tree to
        iterate through al matching paths using the 'iterate' generator.
        :param path_patterns: Pattern format:
            ** - match any sub path
            * - match any map key
            # - match any array item
            key!tag - match a key only with given tag
            (x|y) - match either x or y, any number of alternatives, can be used for both keys and tags.
        """
        if type(path_patterns) == PathSet:
            self.path_patterns = path_patterns.path_patterns
        elif type(path_patterns) == str:
            self.path_patterns = [path_patterns]
        else:
            assert type(path_patterns) == list
            assert len(path_patterns) > 0
            assert type(path_patterns[0]) == str
            self.path_patterns = path_patterns

        self.patterns = []

        for p in self.path_patterns:
            p = p.strip('/')
            for pp in self.expand_alternatives(p):
                # split to path_pattern, tail_pattern and value_pattern
                pp = pp + ":::"
                l = pp.split(':', maxsplit=3)
                if len(l) != 4:
                    assert True
                base_p, tail_p, value_p, _ = l
                if tail_p:
                    tail_p = self.make_path_re(base_p + "/" + tail_p)
                base_p = self.make_path_re(base_p)


                if value_p:
                    value_p = re.compile(value_p)
                else:
                    value_p = None
                self.patterns.append( (base_p, tail_p, value_p) )
        logging.debug("Patterns: " + str(self.patterns))

    def make_path_re(self, path_pattern):
        pp = path_pattern + '/'
        # we process all '*' to '@' to avoid double porcessing,
        # we then replace '@' back to '*' at the end

        # '**' = any number of levels, any key or index per level
        pp = re.sub('\*\*', '[a-zA-Z0-9_]@(/[a-zA-Z0-9_]@)@', pp)
        # '*' = single level, any key or index per level
        pp = re.sub('\*', '[a-zA-Z0-9_]@', pp)
        # '#' = single level, only indices
        pp = re.sub('\#', '[0-9]@', pp)
        # merge multiple '/'
        pp = re.sub('/+', '/', pp)
        # '/' = allow tag info just after key names
        pp = re.sub('/', '(!!?[a-zA-Z0-9_]@)?/', pp)
        # return back all starts
        pp = re.sub('@', '*', pp)
        pp = pp.strip('/')
        pp = "^" + pp + "$"
        return re.compile(pp)

    def iterate(self, root_node):
        """
        Generator that iterates over all paths valid both in path set and in the tree.
         Yields (nodes, address) pair. 'nodes' is list of all nodes from the root down to the
        leaf node of the path. 'address' is string address of the path target.
        :return: (nodes, address)
        nodes - list of nodes along the path from root down to the current node
        address - address of current node including the tag specification if the tag is set
        """
        logging.debug("Patterns: {}".format(self.patterns))
        root_an = AddressNode.root(root_node)
        for adr_node in root_an.iterate_nodes():
            if self.match(adr_node):
                logging.debug("Match path")
                yield (adr_node)


    # @staticmethod
    # def node_has_tag(node, tag):
    #    return tag is None or PathSet.get_node_tag(node) == tag


    def match(self, adr_node:AddressNode):
        path = str(adr_node.address)
        path = remove_prefix(path, '/!!map')
        path = path.lstrip('/')
        for pattern, tail_pattern, value_pattern in self.patterns:
            # Check match in base path.
            if pattern.match(path) is None:
                continue

            # check existence of tail_path
            if tail_pattern:
                for an in adr_node.iterate_nodes():
                    if tail_pattern.match(an.address):
                        break
                else:
                    # No match of tail
                    continue

            # check match of value
            if value_pattern is not None:
                if not self.match_value(value_pattern, adr_node.yaml_node):
                    continue

            return True
        return False


    def match_value(self,  value_pattern, node):
        if not is_scalar_node(node):
            return False
        if type(node.value) != str:
            return False
        if value_pattern.match(node.value):
            return True
        else:
            return False

    ###################
    # Helper methods to traverse the YAML tree using a relative path.

    # @staticmethod
    # def traverse_node(nodes, key, create=False):
    #     curr = nodes[-1]
    #     if key == "..":
    #         nodes.pop()
    #     elif key.isdigit():
    #         assert (is_list_node(curr))
    #         idx = int(key)
    #         if idx >= len(curr):
    #             return None
    #         nodes.append(curr[idx])
    #     else:
    #         assert (is_map_node(curr))
    #         if not key in curr:
    #             if create:
    #                 curr[key] = None
    #             else:
    #                 return None
    #         nodes.append(curr[key])
    #     return nodes
    #
    # def traverse_tree(self, data_path, rel_path):
    #     """
    #     Move accross data tree starting at address given by 'data_path', according
    #     to rel_path.
    #     :param self:
    #     :param data_path: List of data nodes starting from root down to current node.
    #     :param rel_path: Relative address of the target node, e.g. "../key_name/1"
    #     :return: Data path of target node. None in case of incomaptible address.
    #     """
    #     target_path = data_path.copy()
    #     for key in rel_path:
    #         target_path = self.traverse_node(target_path, key)
    #         if target_path is None:
    #             return None
    #     return target_path









