import pytest
import filecmp
from shutil import copyfile
import os
from subprocess import call

source_dir = os.path.dirname(os.path.abspath(__file__))


def files_cmp(ref,out):
    with open(ref, "r") as f:
        t=yml.load(f)
    with open(ref, "w") as f:
        yml.dump(t, f)
    return filecmp.cmp(ref, out)

def remove_prefix(str, prefix):
    if str.startswith(prefix):
        return str[len(prefix):]
    return str

def make_test_file(self, ext):
    fname = os.path.join(source_dir, "test_rules", self.test_name_base + ext)
    if not os.path.isfile(fname) and hasattr(self, "in_file"):
        copyfile(self.in_file, fname)
    return fname

def perform(self, changes):
    test_name = self.test_name
    self.test_name_base = remove_prefix(test_name, "test_")
    in_file = self.in_file = self.make_test_file(".in.yaml")
    out_file = self.make_test_file(".out.yaml")
    ref_file = self.make_test_file(".ref.yaml")
    rev_file = self.make_test_file(".rev.yaml")
    rrf_file = self.make_test_file(".rrf.yaml")

    changes.new_version("2.0.0", automatic_rule=False)
    changes.new_version("ZZ.ZZ.ZZ", automatic_rule=False)
    with open(in_file, "r") as f:
        root = yml.load(f)
    changes.apply_changes(root, None, reversed=False)
    with open(out_file, "w") as f:
        yml.dump(root, f)
    assert files_cmp(ref_file, out_file)

    with open(ref_file, "r") as f:
        root = yml.load(f)
    changes.apply_changes(root, None, reversed=True)
    with open(rev_file, "w") as f:
        yml.dump(root, f)
    assert files_cmp(rrf_file, rev_file)



def test_convert_real_files():
    old_dir = os.path.join(source_dir, "integration", "yaml_old")
    new_dir = os.path.join(source_dir, "integration", "yaml_new")
    rev_dir = os.path.join(source_dir, "integration", "yaml_rev")
    main_script = os.path.join(source_dir,  "..", "yaml_converter.py")
    for old_file in os.listdir(old_dir):
        basename = os.path.basename(old_file)
        new_ref_file = os.path.join(new_dir, basename)
        rev_ref_file = os.path.join(rev_dir, basename)

        call(["python3", main_script, old_file])


class TestFiles:
    # Common methods
    def setup_method(self, method):
        self.test_name = method.__name__

