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


def orig_split(f):
    ff = f
    prefix = file_base + "."
    if not f.startswith(prefix):
        return None
    f = f[len(prefix) - 1:]  # keep leading dot
    if not f.endswith(orig_sufix):
        return None
    f = f[:-len(orig_sufix)]  # remove including dot
    if len(f) == 0:
        return (0, ff)
    f = f[1:]  # remove leading dot
    try:
        return (int(f), ff)
    except:
        return None




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

        # expand dirs
        for wild_name in path_wild[:-1]:
            paths = []
            for dir in dirs:
                paths += [dir + "/" + f for f in os.listdir(dir) if fnmatch.fnmatch(f, wild_name)]
            dirs = []
            for path in paths:
                if os.path.isdir(path):
                    dirs.append(path)

        # expand files
        wild_name = path_wild[-1]
        paths = []
        for dir in dirs:
            paths += [dir + "/" + f for f in os.listdir(dir) if fnmatch.fnmatch(f, wild_name)]

        files = []
        for path in paths:
            if os.path.isfile(path):
                files.append(path)
        return files


    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    from change_rules import make_changes
    changes = make_changes()

    parser = argparse.ArgumentParser(
        prog="yaml-converter",
        description="Bidirectional conversion of YAML file(s) using given set of change rules.")
    #parser.add_argument("-f", "--from-version", default="0.0.0", help="Version of the input file. ")
    parser.add_argument("-s", "--save-orig", default="orig",
                        metavar='EXT',
                        help="Giving the non-empty value the original file is renamed to *.EXT.yaml."
                             "Proformed even for unchanged files in order to support --undo. These files are excluded from conversion. ")
    parser.add_argument("-d", "--dry-run", action='store_true',
                        help="Do not write the file after conversion.")
    parser.add_argument("-t", "--to-version", default="ZZ.ZZ.ZZ",
                        help="Version of the output.")
    parser.add_argument("-r", "--reverse", action='store_true',
                        help="Perform reversed conversion. Input file is in 'to-version'.")
    parser.add_argument("-u", "--undo",
                        dest='undo_level',
                        type=int,
                        const=-1,    # without value
                        default=0,  # without option
                        nargs='?',
                        metavar="N",
                        help="Undo N last conversions before proforming conversion. Undo conversions with same '--save-orig' value."
                             "For N=-1 or without N undo all conversions. ")
    parser.add_argument("--report-actions", action="store_true",
                        help="Report used actions and fiels they are used in.")
    parser.add_argument('in_file',
                        help="Input YAML (or CON) file(s). Wildcards accepted.")

    args = parser.parse_args()
    files = expand_wild_pattern(args.in_file)
    if not files:
        raise Exception("No file to convert for pattern: %s"%args.in_file)

    action_files={}
    for fname in files:
        base = os.path.splitext(fname)[0]
        dir, filename = os.path.split(fname)
        file_base = os.path.splitext(filename)[0]

        # skip non-yaml extensions
        if not fname.endswith(".yaml"):
            print("Warning: '{}' is not \"*.yaml\", skipping.".format(fname))
            continue
        orig_sufix = "." + args.save_orig + ".yaml"
        if orig_sufix == "..yaml":
            orig_sufix = None

        # skip saved original files
        if orig_sufix and fname.endswith(orig_sufix):
            continue



        # perform undo
        if args.undo_level != 0:
            dir, filename = os.path.split(fname)
            file_base = os.path.splitext(filename)[0]
            wild_name = file_base + "*" + orig_sufix
            parsed_files = ( orig_split(f) for f in os.listdir(dir) )
            i_saved_files = [ f for f in parsed_files if not f is None ]
            if i_saved_files:
                i_saved_files.sort(reverse=True)
                i, saved_files = zip(*i_saved_files)
                revert_file = saved_files[args.undo_level]
                for undo_file in saved_files[:args.undo_level]:
                    os.remove(os.path.join(dir, undo_file))
                os.remove(fname)
                os.rename(os.path.join(dir, revert_file), fname)

        with open(fname, "r") as f:
            logging.info("Converting file: {}".format(fname))
            tree = yml.load(f)
            try:
                actions = changes.apply_changes(tree, args.to_version, reversed=args.reverse, map_insert=Changes.BEGINNING)
                for act in actions:
                    action_files.setdefault(act, {})
                    action_files[act][fname]=True
            except:
                raise Exception("Failed conversion of file: {}". format(fname))

        if args.dry_run:
            continue

        # safe orig file to unused name
        orig_fname = base + orig_sufix
        i = 0
        while os.path.isfile(orig_fname):
            i += 1
            orig_fname = base + "." + str(i) + orig_sufix

        os.rename(fname, orig_fname)
        with open(fname, "w") as f:
            yml.dump(tree, f)

    if args.report_actions:
        action_list = [ (line, act, f_dict.keys()) for (act, line), f_dict in action_files.items()]
        for l,a,f in sorted(action_list, key=lambda x:x[0]):
            print( "Line: %4d Action: %12s Files: %s"%(l,a,f) )
