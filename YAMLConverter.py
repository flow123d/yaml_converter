'''
New convertor of input YAML files.
Features:
- conversion rules implemented directly in Python using predefined set of actions in form of methods
- conversion rules operates on YAML tree using natural dict and list composed types
- use ruamel.yaml lib to preserve comments, order of keys etc.
- each set of rules will be in separate method, registered into main list of rules,
  every such change set will have an unique number (increasing), some change sets may be noted by flow123d release
  Both the release and input change set number will be part of the YAML file in order to apply changes only once.
- Try to make actions reversible, so we can make also (some) back conversion.
- can run in quiet mode or in debug mode, individual change sets may be noted as stable to do not report warnings as default
- can be applied to the input format specification and check that it produce target format specification

Compatible with ruamel.yaml 0.15.31

'''
import ruamel.yaml as ruml
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from yaml_parser_extra import is_map_node, is_list_node, is_scalar_node, is_map_key, CommentedScalar
import re
import os
import sys
import argparse
import fnmatch
import logging
import copy
import inspect
from path_set import PathSet



def enlist(s):
    if type(s) != list:
        return [s]
    else:
        return s


class Changes:
    ALPHABETIC = 0
    BEGINNING = 1

    # Possible values of self.map_insert. Determine insertion of new keys into a commented, ordered map.
    # SORTED - before first item that has key greater then inserted item
    # BEGINNING - at beginning of the map

    def __init__(self):
        self.current_version = None
        self._version_changes = None
        self._changes = []

    def new_version(self, version, automatic_rule=True):
        """
        1. Add chenge rule for the flow123d_version key, set its value to 'version'.
        2. Close list of changes form previous version.
        3. Open new change list.
        :param version: Version tag, e.g. "major.minor.patch"
        :return: None
        """

        if self.current_version is not None:
            # not the first call, so we have both initial and final version of current changes frame
            assert version is not None
            if automatic_rule and version is not None:
                assert re.match('[^.]*\.[^.]*\.[^.]*', version)
                assert re.match('[^.]*\.[^.]*\.[^.]*', self.current_version)
                minor = self.current_version.split('.')[0:2]
                if minor < ['2', '0']:
                    self.add_key_to_map("/", key="flow123d_version", value=version)
                else:
                    self.change_value("/flow123d_version", old_val=self.current_version, new_val=version)

            self._changes.append((self.current_version, version, self._version_changes))
        self.current_version = version
        self._version_changes = []

    def unify_tree_dfs(self, node):
        if is_list_node(node):
            for idx in range(len(node)):
                node[idx] = self.unify_tree_dfs(node[idx])
            if type(node) != CommentedSeq:
                return CommentedSeq(node)
        elif is_map_node(node):
            for key, child in node.items():
                node[key] = self.unify_tree_dfs(child)
            if type(node) != CommentedMap:
                return CommentedMap(node)
        elif is_scalar_node(node):
            if type(node) != CommentedScalar:

                tags_for_types = { \
                    float: u'tag:yaml.org,2002:float', \
                    int: u'tag:yaml.org,2002:int', \
                    bool: u'tag:yaml.org,2002:bool', \
                    str: u'tag:yaml.org,2002:str', \
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

    def close_changes(self):
        if hasattr(self, '_reversed'):
            return
        # close last list version
        assert len(self._version_changes) == 0, "Missing final version of changes (call new_version after all changes)."
        # self.new_version(None)

        self._reversed = copy.deepcopy(self._changes)
        self._reversed.reverse()
        self._reversed = [(v1, v0, list(reversed(changes))) for v0, v1, changes in self._reversed]

    @property
    def versions(self):
        versions = [ self._changes[0][0] ]
        versions += [ v1 for v0, v1, _ in self._changes ]
        return versions

    def intersecting_intervals(self, a, b):
        '''
        Returns true if interval a intersect interval b.
        :param a: Tuple, a= (a0, a1), limits of the interval.
        :param b: Tuple, limits of the interval b.
        :return: bool
        '''
        a0, a1 = a
        b0, b1 = b
        return not (b1 < a0 or a1 < b0)

    def apply_changes(self, tree, out_version, in_version=None, warn=True, map_insert=None):
        """
        Apply initailized list of actions to the data tree 'root'.
        :param tree: Input data tree.
        :param out_version: Target version tag, we apply all changes for versions less then this one.
        and greater or equal to the version of the file. If this is smaller then actual version of the file
        the reversed conversion is performed.
        :param warn: Produce warnings for nondeterministic conversions.
        :param map_insert: Method where to insert new values into maps. ALPHABETIC or BEGINNING.
        :return: List of used actions
        """
        self.close_changes()

        if map_insert is not None:
            self.map_insert = map_insert
        else:
            self.map_insert = self.ALPHABETIC
        tree = self.unify_tree_dfs(tree)

        assert is_map_node(tree)

        if in_version is None:
            in_version = tree.get('flow123d_version', None)
            if in_version is not None:
                in_version = in_version.value

        #if reversed:
        #    in_version, out_version = out_version, in_version
        # in_version is always the smaller one
        if out_version == '0':
            out_version = self._changes[0][0]

        if in_version is None:
            in_version = self._changes[0][0]
        if out_version is None:
            out_version = self._changes[-1][0]

        if in_version > out_version:
            reversed=True
            changes = self._reversed
        else:
            reversed = False
            changes = self._changes


        active = 0
        actions = []
        self.tree = tree
        for v0, v1, change_list in changes:
            if in_version == v0:
                active += 1
            if out_version == v0:
                active += 2
            if active == 1:
                for forward, backward, ac_name, line_num in change_list:
                    if reversed:
                        action = backward
                    else:
                        action = forward
                    self.changed = False
                    action()
                    if self.changed:
                        actions.append((ac_name, line_num))
                    self.tree = self.unify_tree_dfs(self.tree)
        if active in [0, 1]:
            logging.warning("End version %s is not in the change list." % out_version)
        if active in [0, 2]:
            logging.warning("Start version %s is not in the change list." % in_version)

        return actions

    def __getattribute__(self, item):
        """
        For every action method (with underscore) is defined a proxy method to add the action into
        change list. Both forward and backward actions are generated.
        :param item:
        :return:
        """
        func_name = "_" + item
        try:
            func = object.__getattribute__(self, func_name)
        except AttributeError:
            func = None
        if func:
            line_number = inspect.getouterframes(inspect.currentframe())[1][2]

            def wrap(*args, **kargs):
                def forward():
                    func(*args, reversed=False, **kargs)

                def backward():
                    func(*args, reversed=True, **kargs)

                self._version_changes.append((forward, backward, func.__name__, line_number))

            return wrap
        else:
            return object.__getattribute__(self, item)

    def __idx_for_key(self, map, key, equal=False):
        '''
        Returns index of a key equal or larger then given 'key'.
        :param map: CommentedSeq
        :param key: String key.
        :return: index
        '''
        index = len(map.keys())
        for idx, dict_key in enumerate(map.keys()):
            if (equal and str(dict_key) == str(key)) \
                    or (not equal and str(dict_key) >= str(key)):
                index = idx
                break
        return index

    def __set_map(self, map, key, value, hint_idx=None):
        '''
        Unified method how to insert new keys into maps. Particular method may be
        determined by parameter 'map_insert' of apply_changes.
        :param map: CommentedMap
        :param key:
        :param value:
        :return:
        '''
        assert is_map_node(map)
        assert is_map_key(key)
        if key in map:
            map[key] = value

        # insert new key
        if hint_idx is not None:
            assert type(hint_idx) == int, "hint: %s" % str(hint_idx)
            index = hint_idx
        else:
            if self.map_insert == self.ALPHABETIC:
                index = self.__idx_for_key(map, key)
            elif self.map_insert == self.BEGINNING:
                index = 0
            else:
                assert False
        map.insert(index, key, value)


    def __brace_substitution(self, old, new):
        """
        Subsititute {} in new by corresponding {...} in 'old'.
        :param old:
        :param new:
        :return: old, new ... changed
        """
        old_braces = re.findall('{[^}]*}', old)

        while True:
            # need to get just first match each time, since 'new' is changed
            new_brace = next(re.finditer('{[^}]*}', new), None)
            if new_brace is None:
                break
            if not old_braces:
                raise Exception("Missing brace(s) in {}.".format(old))
            old_brace = old_braces.pop(0)[1:-1]  # strip braces
            new = new[:new_brace.start()] + old_brace + new[new_brace.end():]

        if old_braces:
            raise Exception("Too many braces in {}.".format(old))
        # remove all braces from old
        old = re.sub("[{}]", "", old)
        assert not re.findall("[{}]", new)
        return old, new

    def __idx_addr(self, addr):
        '''
        Return list [ (key, idx), ..]
        :param addr: Address
        :return:
        '''
        iaddr = []
        node = self.tree
        for key, tag in addr:
            if is_map_node(node):
                idx = self.__idx_for_key(node, key, equal=True)
            else:
                idx = key
            iaddr.append((key, idx))
            node = node[key]
        return iaddr

    def __remove_value(self, nodes, addr_list):
        '''
        Remove last of the 'nodes' list and possibly all empty parent nodes.
        Preserve comments.
        :param nodes: List of nodes from root down to the value to remove.
        :param addr_list: Address of the value.
        :return: REturn removed value
        '''
        # remove value
        if len(nodes) <= 1:
            return None

        key = addr_list[-1][0]

        if is_map_node(nodes[-2]):
            assert is_map_key(key)
            value = nodes[-2].pop(key)
        elif is_list_node(nodes[-2]):
            assert type(key) == int
            value = nodes[-2].pop(key)
        else:
            assert False
        try:
            comment = nodes[-2].ca.items.pop(key)
        except KeyError:
            comment = None

        # remove empty maps and seqs
        if len(nodes[-2]) == 0:
            self.__remove_value(nodes[:-1], addr_list[:-1])
        return (value, comment)

    def __set_tag(self, node, tag):
        '''
        Set tag of given node.
        :param node: must be Commented* node
        :param tag: tag without '!', "" means set to None, None value is ignored
        :return: None
        '''
        if tag is not None:
            # have tag spec in 'new', set the tag
            if tag == "":
                node.tag.value = None
            else:
                node.tag.value = "!" + tag

    def __move_value(self, value, nodes, path_list, orig_addr, comment):
        """
        Add moved value to the tree.

        :param n_nodes:
        :param path: list of tuples (key, tag, value_type)
        :return: Updated subtree.
        """
        if not path_list:
            return value

        if len(path_list) != 1:
            comm = None
        else:
            comm = comment

        key, tag = path_list.pop(0)
        if orig_addr:
            orig_key, orig_idx = orig_addr.pop(0)
            if orig_key != key:
                orig_addr = []
        else:
            orig_idx = None

        if key in ['#', '0']:
            if nodes is None:
                nodes = [CommentedSeq()]
            assert is_list_node(nodes[-1])
            if key == '0':
                i = 0
            if key == '#':
                i = len(nodes[-1])
            new_value = self.__move_value(value, None, path_list, orig_addr, comment)
            self.__set_tag(new_value, tag)
            nodes[-1].insert(i, new_value)

        elif is_map_key(key):
            if nodes is None:
                nodes = [CommentedMap()]

            assert is_map_node(nodes[-1])
            if key in nodes[-1]:
                nodes_plus = nodes + [nodes[-1][key]]
            else:
                nodes_plus = None
            new_value = self.__move_value(value, nodes_plus, path_list, orig_addr, comment)
            self.__set_tag(new_value, tag)

            # CMP AUX
            # nodes[-1][key] = new_value

            self.__set_map(nodes[-1], key, new_value, hint_idx=orig_idx)
        else:
            raise Exception("Wrong key: {}".format(key))

        if comm is not None:  # just when setting final value
            #print("Dict:", nodes[-1])
            #print("Key:", key)
            nodes[-1].ca.items[key] = comm

        return nodes[-1]


    def __apply_manual_conv(self, nodes, address, message):
        if len(nodes) < 2 or not is_map_node(nodes[-2]):
            return

        key = address[-1][0]
        map_of_key = nodes[-2]
        assert is_map_node(map_of_key)

        curr = nodes[-1]

        if is_scalar_node(curr):
            comment = "# :{}  # {}".format(curr.value, message)
            map_of_key.yaml_add_eol_comment(comment, key)
            curr.value = None
            self.changed = True
        else:
            # nodes[-1].yaml_set_start_comment(message)
            ckey = 'COMMENTED_' + key

            map_of_key[ckey] = nodes[-1]
            map_of_key.yaml_set_comment_before_after_key(ckey, before=message, indent=len(nodes))
            del map_of_key[key]


    def __commented_value(self, x):
        if is_map_node(x):
            return dict(x)
        elif is_list_node(x):
            return list(x)
        elif type(x) == CommentedScalar:
            return x.value
        else:
            return x

    def __commented_cmp(self, a, b):
        return self.__commented_value(a) == self.__commented_value(b)


    '''
    ACTIONS, __get_attr__ provides related method without underscore to add the action into changes.
    In general actions do not raise erros but report warnings and just skip the conversion for actual path.
    '''

    def _add_key_to_map(self, paths, key, value, reversed):
        '''
        ACTION.
        For every path P in path set 'paths' add key 'key' to the map at path P.
        This path must be a map. Assign the given 'value' to the key. The key is inserted
        before first key larger in alphabetical order.
        The 'value' can be only scalar.
        REVERSE.
        For every path P in the path set 'path' remove key 'key_name' from the map.
        '''
        for nodes, address in PathSet(paths).iterate(self.tree):
            curr = nodes[-1]
            if not is_map_node(curr):
                logging.warning("Expecting map at path: {}".format(address.s()))
                continue
            if reversed:
                if key in curr:
                    del curr[key]
                    self.changed = True
            else:
                if key in curr:
                    logging.warning("Overwriting key: %s == %s" % (address.s() + '/' + key, curr[key]))
                # Must make deep copy otherwise we share value accross all changed trees
                # which may cause spurious values in empy maps going form other files.
                new_val = copy.deepcopy(value)
                self.__set_map(curr, key, new_val)
                self.changed = True

    def _set_tag_from_key(self, paths, key, tag, reversed):
        '''
        ACTION.
        For ever path P in 'paths' which has to be a map. Set 'tag' if the map contains 'key'.
        Reversed: just remove the tag. Ignore other tags.
        :param paths:
        :param key:
        :param tag:
        :param reversed:
        :return:
        '''

        for nodes, address in PathSet(paths).iterate(self.tree):

            assert is_map_node(nodes[-1]), "Node: {}".format(nodes[-1])
            if not key in nodes[-1]:
                continue

            self.changed = True
            if reversed:
                curr_tag = nodes[-1].tag.value
                if curr_tag and curr_tag != '!' + tag:
                    raise Exception("Deleting wrong tag: {}, expected: {}".format(curr_tag, tag))
                self.__set_tag(nodes[-1], "")  # remove tag
            else:
                self.__set_tag(nodes[-1], tag)

    def _manual_change(self, paths, message_forward, message_backward, reversed):
        '''
        ACTION.
        For every path P in the path set 'path' which has to end by key. Rename the key (if invalidate='key')
        or the tag (if invalidate='tag') by postfix '_NEED_EDIT'. And appended comment with the message_forward.
        REVERSE.
        For every path P in the path set 'path', make the same, but use message_backward for the comment.
        '''
        for nodes, address in PathSet(paths).iterate(self.tree):
            self.changed = True
            if reversed:
                self.__apply_manual_conv(nodes, address, message_backward)
            else:
                self.__apply_manual_conv(nodes, address, message_forward)

    """
    def remove_key(path_set, key_name, key_value):
        '''
        ACTION.
        For every path P in path list 'path_set' remove key 'key_name'. This is an inverse action to add_key_to_map.
        REVERSE.
        For every path P in the path set 'path' add key 'key_name' to the map and set it to the given default value
        `key_value`.
        '''
    """


    def _copy_value(self, new_paths, old_paths, reversed):
        self._move_value(new_paths, old_paths, reversed, copy_val=True)

    def _move_value(self, new_paths, old_paths, reversed, copy_val=False):
        """
        ACTION.
        Move a values from 'new_paths' to 'old_paths'.
        We can not use standard patterns as this makes move a non-invertible action.
        We first expand both lists into list of pairs of simple paths with tag specifications and
        than apply move for each pair of these paths.


        Path_in must be pattern for absolute path, '*' and '**' are not allowed.

        1. In path_out, substitute every {} with corresponding {*} in path_in.
        2. Expand both old_paths and new_paths for alternatives
           resulting lists should be of the same size. Otherwise we report error since this is indpendent of the data.
        3. For every corresponding pair of 'old' and 'new' paths:
           - tag spec must be in both paths for corresponding keys
           - find 'old' in the tree (no tag spec '/x/' means any tag, empty tag /x!/, means no tag)
            # - is allowed, means any item of a list
           - create path in the tree according to 'new',
           - set tags if specified, check tag spec in 'old'
           - # means append to the list
           - move value from old path to new path
           - remove any empty map or list in 'old' path
        """
        new_paths = enlist(new_paths)
        old_paths = enlist(old_paths)
        rev = reversed
        del reversed
        cases = []
        assert len(new_paths) == len(old_paths)
        for old, new in zip(new_paths, old_paths):
            old, new = self.__brace_substitution(old, new)
            old_alts = PathSet.expand_alternatives(old)
            new_alts = PathSet.expand_alternatives(new)
            if copy_val:
                assert len(old_alts) == 1
                old_alts = old_alts * len(new_alts)
            else:
                assert len(old_alts) == len(new_alts), "old: {} new: {}".format(old_alts, new_alts)
            for o_alt, n_alt in zip(old_alts, new_alts):
                # TODO: check tag specifications

                if rev:
                    o_alt, n_alt = n_alt, o_alt

                path_match = [match for match in PathSet(o_alt).iterate(self.tree)]
                # if path_match:
                #    if len(path_match) > 1:
                #        raise Exception("More then single match for the move path: {}".format(old))

                # Reverse list matches to move list elemenets from end.

                for match in path_match[::-1]:
                    nodes, addr = match
                    if copy_val:
                        if rev:
                            self.__remove_value(nodes, addr)
                        else:
                            value = copy.deepcopy(nodes[-1])
                            cases.append((value, n_alt, nodes, [], None))
                    else:
                        orig_idx_addr = self.__idx_addr(addr)
                        value, comment = self.__remove_value(nodes, addr)
                        cases.append((value, n_alt, nodes, orig_idx_addr, comment))

        for case in cases:
            self.changed = True
            value_to_move, new, nodes, addr, comment = case
            # create list of (key, tag); tag=None if no tag is specified
            new_split = new.strip('/').split('/')
            path_list = [(item.split('!') + [None])[:2] for item in new_split]
            self.tree = self.__move_value(value_to_move, [self.tree], path_list, addr, comment)


    def _rename_key(self, paths, old_key, new_key, reversed):
        '''
        ACTION.
        For every path P in the path set 'paths', which has to be a map.
        Rename its key 'old_key' to 'new_key'.
        REVERSE.
        For every path P in the path set 'paths', rename vice versa.
        TODO: Replace with generalized move_value action, problem where to apply reversed action.
        '''
        if reversed:
            old_key, new_key = new_key, old_key

        for nodes, address in PathSet(paths).iterate(self.tree):
            curr = nodes[-1]
            if not is_map_node(curr):
                logging.info("Expecting map at path: {}".format(address))
                continue

            if not old_key in curr:
                logging.info("No key {} to rename at {}.".format(old_key, address))
                continue

            self.changed = True

            orig_idx = self.__idx_for_key(curr, old_key, equal=True)
            value = curr.pop(old_key)
            try:
                comment = curr.ca.items.pop(old_key)
            except KeyError:
                comment = None
            # value = self.__remove_value(nodes + [curr[old_key]], address.add(old_key, None))
            self.__set_map(curr, new_key, value, hint_idx=orig_idx)
            if comment:
                curr.ca.items[new_key] = comment

    def _rename_tag(self, paths, old_tag, new_tag, reversed):
        '''
        ACTION.
        For every path P in the path set 'paths':
        Rename the path tag  'old_key' to 'new_key'. Other tags are ignored, producing warning.
        REVERSE.
        For every path P in the path set 'paths', rename vice versa.

        Can be used also to set or delete a tag:
        rename_tag(old_tag=None, new_tag="XYZ")
        rename_tag(old_tag="XYZ", new_tag=None)
        TODO: Replace with generalized move_value action, problem where to apply reversed action.
        '''
        if old_tag[0] == '!':
            old_tag = old_tag[1:]
        if new_tag[0] == '!':
            new_tag = new_tag[1:]
        if reversed:
            old_tag, new_tag = new_tag, old_tag
        for nodes, address in PathSet(paths).iterate(self.tree):
            curr = nodes[-1]
            assert hasattr(curr, 'tag'), "All nodes should be CommentedXYZ."

            self.changed = True
            if curr.tag.value == "!" + old_tag:
                curr.tag.value = "!" + new_tag
            else:
                logging.warning(
                    "Current tag: '{}', expected: '{}' at path: {}".format(curr.tag.value[1:], old_tag, address))

    def _replace_value(self, paths, re_forward, re_backward, reversed):
        """
        ACTION.
        For every P in 'paths', apply regexp substitution 're_forward'
        REVERSED:
        For the same path set apply 're_backward'

        :param re_forward:  (regexp, substitute)
        :param re_backward: (regexp, substitute)
            ... used as re.sub(regexp, substitute, value)
        If regexp is None, then substitute is tuple for the manual conversion.
        :return: None
        """
        if reversed:
            regexp = re_backward
        else:
            regexp = re_forward
        for nodes, address in PathSet(paths).iterate(self.tree):
            curr = nodes[-1]
            if not is_scalar_node(curr):
                # print("Node: ", curr)
                logging.warning("Expecting scalar at path: {} get: {}".format(address, type(curr)))
                continue
            assert type(curr) == CommentedScalar, "Wrong type: {} {}".format(type(curr))
            if not type(curr.value) == str:
                # print("Node: ", curr)
                logging.warning("Expecting string at path: {} get: {}".format(address, type(curr)))
                continue

            self.changed = True
            if regexp[0] is None:
                self.__apply_manual_conv(nodes, address, regexp[1])  # manual
            else:
                curr.value = re.sub(regexp[0], regexp[1], curr.value)


    def _change_value(self, paths, old_val, new_val, reversed):
        """
        ACTION.
        For every path in 'paths' change value equal to 'old_val' into 'new_val'
        and vice versa for 'reversed'.
        """
        if reversed:
            old_val, new_val = new_val, old_val

        for nodes, address in PathSet(paths).iterate(self.tree):
            if self.__commented_cmp(nodes[-1], old_val):
                key = address[-1][0]
                nodes[-2][key] = copy.deepcopy(new_val)

    def _scale_scalar(self, paths, multiplicator, reversed):
        '''
        ACTION.
        For every path P in the path set 'path' which has to be a scalar, multiply it by 'multiplicator'
        REVERSE.
        For every path P in the path set 'path' which has to be a scalar, divide it by 'multiplicator'
        '''
        for nodes, address in PathSet(paths).iterate(self.tree):
            curr = nodes[-1]
            if not is_scalar_node(curr):
                # print("Node: ", curr)
                logging.warning("Expecting scalar at path: {} get: {}".format(address, type(curr)))
                continue
            assert type(curr) == CommentedScalar, "Wrong type: {} {}".format(type(curr))
            if not isinstance(curr.value, (int, float)):
                continue

            self.changed = True
            is_int = curr.value is int
            # x_value = curr.value
            if reversed:
                curr.value /= multiplicator
            else:
                curr.value *= multiplicator

            # Workaround for BUG in library, do not keep attributes (_prec) during inplace ops.
            if type(curr.value) == ruml.scalarfloat.ScalarFloat:
                curr.value = float(curr.value)

            if is_int and float(curr.value).is_integer():
                curr.value = int(curr.value)



