

import itertools
import re
import logging
from yaml_parser_extra import is_list_node, is_map_node





class Address(list):
    '''
    Class to represent an address in the yaml file including the tag info.
    '''

    def add(self, key, tag):
        '''
        Return new address object for given key and tag.
        :param key:
        :param tag:
        :return:
        '''
        x = Address(self)
        x.append((key, tag))
        return x

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
            p = p + '/'
            for pp in self.expand_alternatives(p):
                # '**' = any number of levels, any key or index per level
                pp = re.sub('\*\*', '[a-zA-Z0-9_]@(/[a-zA-Z0-9_]@)@', pp)
                # '*' = single level, any key or index per level
                pp = re.sub('\*', '[a-zA-Z0-9_]@', pp)
                # '#' = single level, only indices
                pp = re.sub('\#', '[0-9]@', pp)
                # '/' = allow tag info just after key names
                pp = re.sub('/', '(![a-zA-Z0-9_]@)?/', pp)
                # return back all starts
                pp = re.sub('@', '*', pp)
                pp = pp.strip('/')
                pp = "^" + pp + "$"
                self.patterns.append(pp)
        logging.debug("Patterns: " + str(self.patterns))
        # self.options=kwds
        self.matches = []

    def iterate(self, tree):
        """
        Generator that iterates over all paths valid both in path set and in the tree.
         Yields (nodes, address) pair. 'nodes' is list of all nodes from the root down to the
        leaf node of the path. 'address' is string address of the path target.
        :return: (nodes, address)
        nodes - list of nodes along the path from root down to the current node
        address - address of current node including the tag specification if the tag is set
        """
        logging.debug("Patterns: {}".format(self.patterns))

        yield from self.dfs_iterate([tree], Address())

    @staticmethod
    def get_node_tag(node):
        if hasattr(node, "tag"):
            tag = node.tag.value
            if tag and len(tag) > 1 and tag[0] == '!' and tag[1] != '!':
                return tag
        return ""

    # @staticmethod
    # def node_has_tag(node, tag):
    #    return tag is None or PathSet.get_node_tag(node) == tag

    def dfs_iterate(self, nodes, address):
        current = nodes[-1]
        logging.debug("DFS at: " + str(address))
        if self.match(nodes, str(address)):
            # terminate recursion in every node
            self.matches += [current]
            yield (nodes, address)

        if is_list_node(current):
            iterable = enumerate(current)
        elif is_map_node(current):
            iterable = current.items()
        else:
            return

        for key, child in iterable:
            tag = self.get_node_tag(child)[1:]
            yield from self.dfs_iterate(nodes + [child], address.add(key, tag))

    def match(self, data_path, path):
        path = path.strip('/')
        for pattern in self.patterns:
            if re.match(pattern, path) != None:
                logging.debug("Match path")
                # for key, param in self.options.items():
                #     logging.debug("Match path")
                #     if key == "have_tag":
                #         tag_path = list(param.split('/'))
                #         target = self.traverse_tree(data_path, tag_path[0:-1])
                #         target = target[-1]
                #         if not target or not hasattr(target, "tag"):
                #             return False
                #         if target.tag.value != "!" + tag_path[-1]:
                #             return False
                # logging.debug("Full Match")
                return True
        return False

    @staticmethod
    def traverse_node(nodes, key, create=False):
        curr = nodes[-1]
        if key == "..":
            nodes.pop()
        elif key.isdigit():
            assert (is_list_node(curr))
            idx = int(key)
            if idx >= len(curr):
                return None
            nodes.append(curr[idx])
        else:
            assert (is_map_node(curr))
            if not key in curr:
                if create:
                    curr[key] = None
                else:
                    return None
            nodes.append(curr[key])
        return nodes

    def traverse_tree(self, data_path, rel_path):
        """
        Move accross data tree starting at address given by 'data_path', according
        to rel_path.
        :param self:
        :param data_path: List of data nodes starting from root down to current node.
        :param rel_path: Relative address of the target node, e.g. "../key_name/1"
        :return: Data path of target node. None in case of incomaptible address.
        """
        target_path = data_path.copy()
        for key in rel_path:
            target_path = self.traverse_node(target_path, key)
            if target_path is None:
                return None
        return target_path









