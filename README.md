YAML Converter
==============

[![Build Status](https://travis-ci.org/flow123d/yaml_converter.svg?branch=master)](https://travis-ci.org/flow123d/yaml_converter)
[![Code Health](https://landscape.io/github/flow123d/yaml_converter/master/landscape.svg?style=flat)](https://landscape.io/github/flow123d/yaml_converter/master)
[![Code Climate](https://codeclimate.com/github/flow123d/yaml_converter/badges/gpa.svg)](https://codeclimate.com/github/flow123d/yaml_converter)
[![Test Coverage](https://codeclimate.com/github/flow123d/yaml_converter/badges/coverage.svg)](https://codeclimate.com/github/flow123d/yaml_converter/coverage)


Bidirectional converter for specific YAML files.

Primary motivation is to have a bidirectional converter for Flow123d input files. 
However, long term plan is to make it an independent tool for bidirectional 
conversion of custom YAML file formats.

Requirements
------------
ruamel.yaml


# Documentation

## PathSet syntax
Modification rules (described further on) are applied to the addresses in the given YAML file
that match given PathSet pattern. PathSet pattern is an address like:

  /key_a/1/key_b

Following constructs can be used:

'\*'  character  - match any key

'#'  character   - match any index

'\*\*'           - match any sub path (can contain both keys and indices)

'KEY!TAG'        - match the KEY only if it have tag TAG. Usefull for custom tags or in combination with '*'.

'(A|B|C)'        - match A or B or C. Can be used for both keys and tags.

## Change rules

add_key_to_map(paths, key, value)

set_tag_from_key(paths, key, tag)

manual_change(paths, message_forward, message_backward)

copy_value(new_paths, old_paths)

move_value(new_paths, old_paths)

rename_key(paths, old_key, new_key)

rename_tag(paths, old_tag, new_tag):

replace_value(paths, re_forward, re_backward)

change_value(paths, old_val, new_val)

scale_scalar(paths, multiplicator)


