import unittest
import filecmp
from shutil import copyfile
from yaml_converter import *
import sys

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


class TestActions(unittest.TestCase):
    '''
    def test_add_key(self):
        changes=Changes()
        changes.new_version("0.0.0")
        changes.add_key_to_map("/", key="flow123d_version", value="2.0.0")
        self.perform(changes)


    def test_manual_change(self):
        changes=Changes()
        changes.new_version("0.0.0")
        # Change sign of oter fields manually
        path_set = PathSet(
            ["/problem/secondary_equation/input_fields/#/bc_flux!(FieldElementwise|FieldInterpolatedP0|FieldPython)/",
             "/problem/primary_equation/input_fields/#/bc_flux!(FieldElementwise|FieldInterpolatedP0|FieldPython)/"])
        changes.manual_change(path_set,
                              message_forward="Change sign of this field manually.",
                              message_backward="Change sign of this field manually.")
        self.perform(changes)


    def test_rename_key(self):
        changes=Changes()
        changes.new_version("0.0.0")
        # Change degree keys in PadeApproximant
        path_set = "/problem/secondary_equation/**/ode_solver!PadeApproximant/"
        changes.rename_key(path_set, old_key="denominator_degree", new_key="pade_denominator_degree")
        changes.rename_key(path_set, old_key="nominator_degree", new_key="pade_nominator_degree")

        equations = "(primary_equation|" \
                    "secondary_equation|" \
                    "secondary_equation/reaction_term)"
        changes.rename_key("/problem/" + equations + "/output/", old_key="output_fields", new_key="fields")

        self.perform(changes)


    def test_set_tag_from_key(self):
        changes=Changes()
        changes.new_version("0.0.0")

        # Set  to DG transport
        changes.set_tag_from_key("/problem/*/", key='dg_penalty',  tag='TransportDG')
        self.perform(changes)


    def test_rename_tag(self):
        changes=Changes()
        changes.new_version("0.0.0")

        # Rename equations and couplings
        path = "/problem/secondary_equation/"
        changes.rename_tag(path, old_tag="TransportOperatorSplitting", new_tag="Coupling_OperatorSplitting")
        self.perform(changes)


    def test_replace_value(self):
        changes=Changes()
        changes.new_version("0.0.0")


        # Change sign of boundary fluxes
        path_set = PathSet(["/problem/(primary_equation|secondary_equation)/input_fields/*/bc_flux!FieldFormula/value/"])

        changes.replace_value(path_set,
            re_forward=('^(.*)$', '-(\\1)'),
            re_backward=('^(.*)$', '-(\\1)'))

        # Test manual conversion, alternative paths
        path_set = PathSet(["/problem/(secondary_equation|primary_equation)/input_fields/*/bc_type/"])

        changes.replace_value(path_set,
            re_forward=("^(robin|neumann)$", "total_flux"),
            re_backward=(None, "Select either 'robin' or 'neumann' according to the value of 'bc_flux', 'bc_pressure', 'bc_sigma'."))
        self.perform(changes)

    def test_change_value(self):
        changes=Changes()
        changes.new_version("0.0.0")

        # Rename equations and couplings
        changes.change_value("/(problem|sec)/a", old_val=1, new_val="one")
        changes.change_value("/(problem|sec)/b", old_val=True, new_val=CommentedMap())
        self.perform(changes)

    def test_scale_scalar(self):
        changes=Changes()
        changes.new_version("0.0.0")

        # Change sign of boundary fluxes
        path_set = [
            "/problem/(primary|secondary)_equation/input_fields/*/bc_flux/",
            "/problem/(primary|secondary)_equation/input_fields/*/bc_flux/#/",
            "/problem/(primary|secondary)_equation/input_fields/*/bc_flux!FieldConstant/value/",
        ]
        changes.scale_scalar(path_set, multiplicator=-1)
        self.perform(changes)
    '''

    def test_move_value(self):
        changes=Changes()
        changes.new_version("0.0.0")

        # Move FV transport
        path_in = "/problem/secondary_equation_1!TransportOperatorSplitting/{(output_fields|input_fields)}/"
        path_out = "/problem/secondary_equation_1!Coupling_OperatorSplitting/transport!Solute_Advection_FV/{}/"
        changes.move_value(path_in, path_out)

        # Move DG transport
        path_in = "/problem/secondary_equation_2!SoluteTransport_DG/{(input_fields|output_fields|solver|dg_order|dg_variant|solvent_density)}/"
        path_out = "/problem/secondary_equation_2!Coupling_OperatorSplitting/transport!SoluteTransport_DG/{}/"
        changes.move_value(path_in, path_out)

        changes.move_value("/problem/secondary_equation_3!HeatTransfer_DG/",
                            "/problem/secondary_equation_3!Heat_AdvectionDiffusion_DG/")

        # Changes in mesh record
        changes.set_tag_from_key("/problem/mesh/regions/#/", key='id', tag='From_ID')
        changes.set_tag_from_key("/problem/mesh/regions/#/", key='element_list', tag='From_Elements')

        changes.set_tag_from_key("/problem/mesh/sets/#/", key='region_ids', tag='Union')
        changes.set_tag_from_key("/problem/mesh/sets/#/", key='region_labels', tag='Union')
        changes.set_tag_from_key("/problem/mesh/sets/#/", key='union', tag='Union')
        changes.rename_key("/problem/mesh/sets/#!Union/", old_key='region_labels', new_key='regions')
        changes.rename_key("/problem/mesh/sets/#!Union/", old_key='union', new_key='regions')
        changes.set_tag_from_key("/problem/mesh/sets/#/", key='intersection', tag='Intersection')
        changes.set_tag_from_key("/problem/mesh/sets/#/", key='difference', tag='Difference')
        changes.move_value("{/problem/mesh}/sets/#{!(Union|Intersection|Difference)}/", "{}/regions/#{}/")

        # copy values
        changes.copy_value("{/problem}/secondary_equation_2/substances", "{}/secondary_equation_3/substances")
        self.perform(changes)


####################################

    def  make_test_file(self, ext):
        fname = "tests/" + self.test_name_base + ext
        if not os.path.isfile(fname) and hasattr(self, "in_file"):
            copyfile(self.in_file, fname)
        return fname


    def perform(self, changes):
        test_name = self.id().split('.')[-1]
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
        changes.apply_changes( root, None , reversed=False)
        with open(out_file, "w") as f:
            yml.dump(root, f)
        self.assertTrue(files_cmp(ref_file, out_file))

        with open(ref_file, "r") as f:
            root = yml.load(f)
        changes.apply_changes(root, None, reversed=True)
        with open(rev_file, "w") as f:
            yml.dump(root, f)
        self.assertTrue(files_cmp(rrf_file, rev_file))


class TestAllRules(unittest.TestCase):
    '''
    Integration test to test correct conversion of all yaml files
    from dir: 'yaml_old' to dir 'yaml_new' and back to 'yaml_rev'
    '''


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.WARNING)
    logging.debug("First debug message.")

    unittest.main()