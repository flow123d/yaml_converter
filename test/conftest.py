import pytest
import os
import filecmp
import re

source_dir = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append(os.path.join(source_dir, ".."))
from ymlconv.yaml_parser_extra import get_yaml_serializer


# Create list of test files for the flow123d_input test.
# works like a parametrization of the tests with the list of the input files
def pytest_generate_tests(metafunc):
    if 'flow_yaml_files' in metafunc.fixturenames:
        old_dir = os.path.join(source_dir, "flow123d_input", "yaml_old")
        new_dir = os.path.join(source_dir, "flow123d_input", "yaml_new")
        rev_dir = os.path.join(source_dir, "flow123d_input", "yaml_rev")
        file_table = []
        for basename in os.listdir(old_dir):
            if not re.match('\d\d_[^.]*\.yaml', basename):
                continue
            #f basename != '03_flow_vtk.yaml':
            #    continue
            old_file = os.path.join(old_dir, basename)
            new_ref_file = os.path.join(new_dir, basename)
            rev_ref_file = os.path.join(rev_dir, basename)
            out_file = os.path.splitext(old_file)[0] + ".out.yaml"
            rev_file = os.path.splitext(new_ref_file)[0] + ".rev.yaml"
            assert os.path.isfile(new_ref_file)
            assert os.path.isfile(rev_ref_file)
            file_table.append( (old_file, out_file, new_ref_file, rev_file, rev_ref_file) )
        data_ids = [os.path.basename(ftuple[0]) for ftuple in file_table]
        metafunc.parametrize("flow_yaml_files", file_table, ids=data_ids)

@pytest.fixture
def yaml_serializer():
    """
    Test YAML serialization fixture.
    """
    return get_yaml_serializer()

@pytest.fixture
def yaml_files_cmp():
    return _yaml_files_cmp_with_output

def _yaml_files_cmp(ref,out):
    yml = get_yaml_serializer()

    # Perform the conversion on the reference file in order to nail out
    # minor representation changes
    with open(ref, "r") as f:
        t=yml.load(f)
    with open(ref, "w") as f:
        yml.dump(t, f)
    return filecmp.cmp(ref, out)

def _yaml_files_cmp_with_output(ref,out):
    # reading files
    f_ref = open(ref, "r")
    f_out = open(out, "r")

    f_ref_data = f_ref.readlines()
    f_out_data = f_out.readlines()

    i = 0
    is_same = True

    for ref_line, out_line in zip(f_ref_data, f_out_data):  # or izip_longest
        i += 1

        # matching lines from both files
        if ref_line != out_line:
            # print that line from both files
            print("Line ", i, ":")
            print("\tRef file:", ref_line, end='')
            print("\tOut file:", out_line, end='')
            is_same = False

    # closing files
    f_ref.close()
    f_out.close()

    return is_same
