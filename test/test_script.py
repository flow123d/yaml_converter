"""
Test the command line interface.
"""
import yaml_converter
import os
import glob
from shutil import copyfile
import YAMLConverter
import filecmp

source_dir = os.path.dirname(os.path.abspath(__file__))




def test_script_undo(yaml_files_cmp):
    fname = os.path.join(source_dir, "test_script_data", "add_key.in.yaml")

    # save orginal file for refenece
    ref_file_1 = fname + ".ref1"
    copyfile(fname, ref_file_1)

    # partial convert
    yaml_converter.main(['-t', '2.0.0_rc', fname])
    assert os.path.isfile(os.path.join(source_dir, "test_script_data", "add_key.in.orig00.yaml"))
    # intermediate reference file
    ref_file_2 = fname + ".ref2"
    copyfile(fname, ref_file_2)

    # same convert, do nothing, but we save anyway
    yaml_converter.main(['-t', '2.0.0_rc', fname])
    assert os.path.isfile(os.path.join(source_dir, "test_script_data", "add_key.in.orig01.yaml"))

    # final conversion
    yaml_converter.main([fname])
    assert os.path.isfile(os.path.join(source_dir, "test_script_data", "add_key.in.orig02.yaml"))

    # undo just two runs, no conversion
    yaml_converter.main(['-u', '2', '-d', fname])
    yaml_files_cmp(ref_file_1, fname)

    yaml_converter.main(['-u', '-d', fname])
    yaml_files_cmp(ref_file_2, fname)

    for f in glob.glob(os.path.join(source_dir, "test_script_data", "add_key.in.orig*")):
        os.remove(f)
    os.remove(os.path.join(source_dir, "test_script_data", "add_key.in.yaml.ref1"))
    os.remove(os.path.join(source_dir, "test_script_data", "add_key.in.yaml.ref2"))

