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
from yaml_parser_extra import get_yaml_serializer
from YAMLConverter import Changes
#from YAMLConverter import

import regex as re
import os
import sys
import argparse
import fnmatch
import logging
import glob
from shutil import copyfile


class ExcFailedConversion(Exception):
    pass


def get_parsed_args(args):
    parser = argparse.ArgumentParser(
        prog="yaml-converter",
        description="Bidirectional conversion of YAML file(s) using given set of change rules.\n"
                    "Original file is stored as FILE.origNN.yaml. Undo option '-u' can be used to\n"
                    "restore the original file before new conversion takes the place.")
    parser.add_argument("-o", "--output", help="Filename to use for the converted file.")
    parser.add_argument("-d", "--dry-run", action='store_true',
                        help="Do not write the file after conversion.")
    parser.add_argument("-t", "--to-version", default="ZZ.ZZ.ZZ",
                       help="Version of the output. Defult is the newest version. Version '0' can be used to revert to the very first version.")
    # parser.add_argument("-r", "--reverse", action='store_true',
    #                     help="Perform reversed conversion. Input file is in 'to-version'.")
    parser.add_argument("-u", "--undo",
                        dest='undo_level',
                        type=int,
                        const=-1,    # without value
                        default=0,  # without option
                        nargs='?',
                        metavar="N",
                        help="Undo N last conversions before proforming conversion."
                             "Without N specified undo all conversions. ")
    parser.add_argument("--report-actions", action="store_true",
                        help="Report used actions and files they are used in.")
    parser.add_argument('in_files', nargs='*',
                        help="Input YAML (or CON) file(s). Wildcards accepted.")

    return parser.parse_args(args)

# TODO:
# - finish flow123d_input test
# - add option to match also value in PathSet, e.g. to identify just some values of an array
#   Syntax /a/#/key:(value1| value2| ..)
def save_and_undo(fname, undo_level):

    # skip non-yaml extensions
    if not fname.endswith(".yaml") or fnmatch.fnmatch(fname, "*.orig??.yaml"):
        return None

    base = os.path.splitext(fname)[0]
    dir, filename = os.path.split(fname)
    file_base = os.path.splitext(filename)[0]

    # safe orig file to unused name
    for i in range(100):
        orig_fname = "{}.orig{:02d}.yaml".format(base, i)
        if not os.path.isfile(orig_fname):
            break
    else:
        raise Exception("Too many saved files.")
    copyfile(fname, orig_fname)

    # perform undo
    if undo_level != 0:

        parsed_files = []
        for forig in os.listdir(dir):
            orig_fname = os.path.basename(forig)
            m = re.match('.*orig(\d\d).yaml', orig_fname)
            if m:
               #undo_idx = int(m.group(1))
               fname = m.group(0)
               parsed_files.append( fname )

        if parsed_files:
            parsed_files.sort(reverse=True)
            revert_file = parsed_files[undo_level]
            for undo_file in parsed_files[:undo_level]:
                os.remove(os.path.join(dir, undo_file))
            os.remove(fname)
            os.rename(os.path.join(dir, revert_file), fname)

    return fname

def convert(changes, to_version, fname_in, fname_out):

    yml = get_yaml_serializer()
    with open(fname_in, "r") as f:
        logging.info("Converting file: {}".format(fname_in))
        tree = yml.load(f)

    try:
        actions = changes.apply_changes(tree, to_version, map_insert=Changes.BEGINNING)
    except:
        raise ExcFailedConversion("Failed conversion of file: {}".format(fname_in))

    if fname_out is not None:
        with open(fname_out, "w") as f:
            yml.dump(tree, f)

    return actions


def main(cmd_args):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    log = logging.getLogger('Converter')

    from change_rules import make_changes
    changes = make_changes()

    args = get_parsed_args(cmd_args)


    files = [ f for in_file in args.in_files for f in glob.glob(in_file) ]
    if not files:
        raise Exception("No file to convert for pattern: %s"%args.in_file)

    action_files={}
    for fname in files:
        #print("File: ", fname)
        if args.dry_run:
            fname_in = fname
            fname_out = None
        else:
            fname_out = fname_in = save_and_undo(fname, args.undo_level)
            if args.output is not None:
                fname_out = args.output

        if fname_in is None:
            logging.info("Skipping backup file: {}".format(fname))
            continue

        #print("Convert: ", fname)
        try:
            actions = convert(changes, args.to_version, fname_in, fname_out)
        except ExcFailedConversion:
            log.exception("Failed conversion.")
            actions = []

        for act in actions:
            action_files.setdefault(act, set())
            action_files[act].add(fname)



    if args.report_actions:
        action_list = [ (line, act, f_dict) for (act, line), f_dict in action_files.items()]
        for l,a,f in sorted(action_list, key=lambda x:x[0]):
            print( "Line: %4d Action: %12s Files: %s"%(l,a,f) )


if __name__ == "__main__":
    main(sys.argv[1:])