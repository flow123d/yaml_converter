import pytest
import os
import YAMLConverter
import filecmp

source_dir = os.path.dirname(os.path.abspath(__file__))

# Create list of test files for the flow123d_input test.
def pytest_generate_tests(metafunc):
    if 'yaml_old_file' in metafunc.fixturenames:
        old_dir = os.path.join(source_dir, "flow123d_input", "yaml_old")
        new_dir = os.path.join(source_dir, "flow123d_input", "yaml_new")
        rev_dir = os.path.join(source_dir, "flow123d_input", "yaml_rev")
        file_table = []
        for old_file in os.listdir(old_dir):
            basename = os.path.basename(old_file)
            new_ref_file = os.path.join(new_dir, basename)
            rev_ref_file = os.path.join(rev_dir, basename)
            assert os.path.isfile(new_ref_file)
            assert os.path.isfile(rev_ref_file)
            file_table.append( (old_file, new_ref_file, rev_ref_file) )
        metafunc.parametrize("yaml_old_file, yaml_new_file, yaml_rev_file", file_table)


