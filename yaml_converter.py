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
from YAMLConverter import *
import os
import sys
import argparse
import fnmatch
import logging




if __name__ == "__main__":

    def expand_wild_pattern(pattern):
        '''
        :param pattern: Path pattern, see fnmatch module.
        :return: List of files matching the pattern.
        '''
        path_wild = pattern.split('/')
        if path_wild[0]:
            # relative path
            dirs = ["."]
        else:
            # absloute
            dirs = ["/"]

        files = []
        for wild_name in path_wild:
            # separate dirs and files
            paths = []
            for dir in dirs:
                paths += [dir + "/" + f for f in os.listdir(dir) if fnmatch.fnmatch(f, wild_name)]
            dirs = []
            for path in paths:
                if os.path.isdir(path):
                    print("dir append: %s"%path)
                    dirs.append(path)
                elif os.path.isfile(path):
                    print("file append: %s"%path)
                    if not path.endswith(".new.yaml"):
                        files.append(path)
                else:
                    assert False, "Path neither dir nor file."
        return files


    logging.basicConfig(stream=sys.stdout, level=logging.WARNING)
    from change_rules import make_changes
    changes = make_changes()

    parser = argparse.ArgumentParser()
    #parser.add_argument("-f", "--from-version", default="0.0.0", help="Version of the input file. ")
    parser.add_argument("-t", "--to-version", default="ZZ.ZZ.ZZ", help="Version of the output.")
    parser.add_argument("-r", "--reverse", action='store_true', help="Perform reversed conversion. Input file is in 'to-version'.")
    parser.add_argument('in_file', help="Input YAML (or CON) file(s). Wildcards accepted.")

    args = parser.parse_args()
    files = expand_wild_pattern(args.in_file)
    if not files:
        raise Exception("No file to convert for pattern: %s"%args.in_file)

    action_files={}
    for fname in files:
        base = os.path.splitext(fname)[0]
        if not fname.endwith(".yaml"):
            print("Warning: '{}' is not \"*.yaml\", skipping.".format(fname))
        with open(fname, "r") as f:
            tree = yml.load(f)
            actions = changes.apply_changes(tree, args.to_version, reversed=args.reverse, map_insert=Changes.BEGINNING)
            for act in actions:
                action_files.setdefault(act, {})
                action_files[act][fname]=True

        out_fname = base + ".new.yaml"
        with open(out_fname, "w") as f:
            yml.dump(tree, f)

    action_list = [ (line, act, f_dict.keys()) for (act, line), f_dict in action_files.items()]
    for l,a,f in sorted(action_list, key=lambda x:x[0]):
        print( "Line: %4d Action: %12s Files: %s"%(l,a,f) )
