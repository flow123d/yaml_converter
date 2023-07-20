# Actions

Single modification action is an atomic change in the YAML file. Ideally it should be reversible.

## Overview of the converter features
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




## `add_key_to_map(self, paths, key, value)`
**FORWARD**

For every path P in path set 'paths' add key 'key' to the map at path P.
This path must be a map. Assign the given 'value' to the key. The key is inserted
before first key larger in alphabetical order.
The 'value' can be only scalar.

**REVERSE**
For every path P in the path set 'path' remove key 'key_name' from the map.


## `set_tag_from_key(self, paths, key, tag)`

**FORWARD**
For ever path P in 'paths' which has to be a map. Set 'tag' if the map contains 'key'.

**REVERSE**
just remove the tag. Ignore other tags.



## `manual_change(self, paths, message_forward, message_backward)`

**FORWARD**
For every path P in the path set 'path' which has to end by key. Rename the key (if invalidate='key')
or the tag (if invalidate='tag') by postfix '_NEED_EDIT'. And appended comment with the message_forward.

**REVERSE**
For every path P in the path set 'path', make the same, but use message_backward for the comment.

'''
for adr_node in PathSet(paths).iterate(self.tree):
    self.changed = True
    if reverse:
        self.__apply_manual_conv(adr_node.nodes_path, adr_node.address, message_backward)
    else:
        self.__apply_manual_conv(adr_node.nodes_path, adr_node.address, message_forward)
'''

## `remove_key(path_set, key_name, key_value)`
        
**FORWARD**
For every path P in path list 'path_set' remove key 'key_name'. This is an inverse action to add_key_to_map.

**REVERSE**
For every path P in the path set 'path' add key 'key_name' to the map and set it to the given default value
`key_value`.



## `copy_value(self, new_paths, old_paths)`
    Same as the `move_value` but without removint the original node.
    
## `move_value(self, new_paths, old_paths)`
        
        
**FORWARD**
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
    
    
## `rename_key(self, paths, old_key, new_key)`
    
**FORWARD**
For every path P in the path set 'paths', which has to be a map.
Rename its key 'old_key' to 'new_key'.

**REVERSE**
For every path P in the path set 'paths', rename vice versa.
TODO: Replace with generalized move_value action, problem where to apply reversed action.

## rename_tag(self, paths, old_tag, new_tag)
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

## `replace_value(self, paths, re_forward, re_backward)`
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


## `change_value(self, paths, old_val, new_val)`
"""
ACTION.
For every path in 'paths' change value equal to 'old_val' into 'new_val'
and vice versa for 'reversed'.
"""


## `scale_scalar(self, paths, multiplicator)`
'''
ACTION.
For every path P in the path set 'path' which has to be a scalar, multiply it by 'multiplicator'
REVERSE.
For every path P in the path set 'path' which has to be a scalar, divide it by 'multiplicator'
'''

