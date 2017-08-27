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

'''
from yaml_converter import PathSet, Changes, CommentedMap, CommentedSeq, CommentedScalar

def make_changes():
    changes = Changes()

    # Add header key 'flow123d_version'
    changes.new_version("1.8.2")

    # Change degree keys in PadeApproximant
    path_set = PathSet(["/problem/secondary_equation/**/ode_solver!PadeApproximant/"])

    changes.rename_key(path_set, old_key="denominator_degree", new_key="pade_denominator_degree")
    changes.rename_key(path_set, old_key="nominator_degree", new_key="pade_nominator_degree")

    # Change sign of boundary fluxes
    path_set = PathSet([
        "/problem/secondary_equation/input_fields/#/bc_flux/",
        "/problem/primary_equation/input_fields/#/bc_flux/",
        "/problem/secondary_equation/input_fields/#/bc_flux/#/",
        "/problem/primary_equation/input_fields/#/bc_flux/#/",
        "/problem/secondary_equation/input_fields/#/bc_flux!FieldConstant/value/",
        "/problem/primary_equation/input_fields/#/bc_flux!FieldConstant/value/"
    ])
    changes.scale_scalar(path_set, multiplicator=-1)

    # Change sign of boundary fluxes formulas
    path_set = PathSet(["/problem/secondary_equation/input_fields/*/bc_flux!FieldFormula/value/",
                        "/problem/primary_equation/input_fields/*/bc_flux!FieldFormula/value/"])

    changes.replace_value(path_set,
                          re_forward=('^(.*)$', '-(\\1)'),
                          re_backward=('^(.*)$', '-(\\1)'))

    # Change sign of oter fields manually
    path_set = PathSet(
        ["/problem/secondary_equation/input_fields/*/bc_flux!(FieldElementwise|FieldInterpolatedP0|FieldPython)",
         "/problem/primary_equation/input_fields/*/bc_flux!(FieldElementwise|FieldInterpolatedP0|FieldPython)"])

    changes.manual_change(path_set,
                          message_forward="Change sign of this field manually.",
                          message_backward="Change sign of this field manually.")

    # Merge robin and neumann BC types into total_flux

    changes.replace_value("/problem/primary_equation/input_fields/*/bc_type/",
                          re_forward=("^(robin|neumann)$", "total_flux"),
                          re_backward=(None,
                                       "Select either 'robin' or 'neumann' according to the value of 'bc_flux', 'bc_pressure', 'bc_sigma'."))


    changes.replace_value("/problem/secondary_equation/input_fields/*/bc_type/",
                          re_forward=("^(robin|neumann)$", "diffusive_flux"),
                          re_backward=(None,
                                       "Select either 'robin' or 'neumann' according to the value of 'bc_flux', 'bc_pressure', 'bc_sigma'."))

    # Move FV transport
    path_in = "/problem/secondary_equation!TransportOperatorSplitting/{(output_fields|input_fields)}/"
    path_out = "/problem/secondary_equation!Coupling_OperatorSplitting/transport!Solute_Advection_FV/{}/"
    changes.move_value(path_in, path_out)

    # Move DG transport
    path_in = "/problem/secondary_equation!SoluteTransport_DG/{(input_fields|output_fields|solver|dg_order|dg_variant|solvent_density)}/"
    path_out = "/problem/secondary_equation!Coupling_OperatorSplitting/transport!Solute_AdvectionDiffusion_DG/{}/"
    changes.move_value(path_in, path_out)

    changes.move_value("/problem/secondary_equation!HeatTransfer_DG/",
                       "/problem/secondary_equation!Heat_AdvectionDiffusion_DG/")

    # Remove r_set, use region instead
    # Reversed change is not unique
    changes.rename_key("/**/input_fields/*/", old_key="r_set", new_key="region")

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


    # CMP AUX
    changes.add_key_to_map("/problem/primary_equation", key='nonlinear_solver', value=CommentedMap())

    changes.move_value("{/problem/primary_equation}/solver", "{}/nonlinear_solver/linear_solver")


    stor_map = CommentedMap()
    stor_map['region'] = CommentedScalar(None, 'ALL')
    stor_map['storativity'] = CommentedScalar(None, 1.0)
    changes.add_key_to_map("/problem/primary_equation!(Unsteady_LMH|Unsteady_MH)/",
                           key="aux_storativity",
                           value=stor_map)
    changes.move_value("{/problem/primary_equation!(Unsteady_LMH|Unsteady_MH)}/aux_storativity", "{}/input_fields/0")

    changes.rename_tag("/problem/primary_equation/", old_tag="Steady_MH", new_tag="Flow_Darcy_MH")
    changes.rename_tag("/problem/primary_equation/", old_tag="Unsteady_MH", new_tag="Flow_Darcy_MH")
    changes.rename_tag("/problem/primary_equation/", old_tag="Unsteady_LMH", new_tag="Flow_Richards_LMH")
    changes.rename_tag("/problem/", old_tag="SequentialCoupling", new_tag="Coupling_Sequential")


    changes.rename_key("/problem/", "primary_equation", "flow_equation")
    changes.move_value("/problem/secondary_equation!Coupling_OperatorSplitting",
                       "/problem/solute_equation!Coupling_OperatorSplitting")
    changes.move_value("/problem/secondary_equation!Heat_AdvectionDiffusion_DG",
                       "/problem/heat_equation!Heat_AdvectionDiffusion_DG")

    changes.new_version("2.0.0_rc")

    # CMP AUX
    #changes.add_key_to_map("/problem/flow_equation/", key="output_specific", value=CommentedMap())

    changes.move_value("/problem/flow_equation/output/raw_flow_output/",
                       "/problem/flow_equation/output_specific/raw_flow_output/")
    changes.move_value("/problem/flow_equation/output/compute_errors/",
                       "/problem/flow_equation/output_specific/compute_errors/")

    changes.move_value("{/problem/flow_equation}/output/output_stream/", "{}/output_stream/")

    equations = "(solute_equation/transport|" \
                "solute_equation/reaction_term|" \
                "solute_equation/reaction_term/reaction_mobile|" \
                "solute_equation/reaction_term/reaction_immobile|" \
                "heat_equation)"
    changes.rename_key("/problem/flow_equation/output/", old_key="output_fields", new_key="fields")
    changes.move_value("{/problem/" + equations + "}/output_fields/", "{}/output/fields")

    changes.move_value("{/problem/(flow_equation|solute_equation|heat_equation)/output_stream}/time_list/", "{}/times/")
    changes.move_value("{/problem/(flow_equation|solute_equation|heat_equation)/output_stream}/time_step/",
                       "{}/times/0/step/")

    changes.move_value("{/problem/(flow_equation|solute_equation|heat_equation)}/output_stream/add_input_times/",
                       "{}/output/add_input_times/")
    changes.copy_value("/problem/solute_equation/output/add_input_times/",
                       "/problem/(solute_equation/reaction_term|"
                       "solute_equation/reaction_term/reaction_mobile|"
                       "solute_equation/reaction_term/reaction_immobile"
                       ")/output/add_input_times/")

    empty_map = CommentedMap()
    changes.change_value("/problem/(flow_equation|solute_equation|heat_equation)/balance", True, empty_map)

    false_map = CommentedMap()
    false_map['add_output_times'] = False
    changes.change_value("/problem/(flow_equation|solute_equation|heat_equation)/balance", False, false_map)

    changes.change_value("/problem/**/input_fields/#/region/", "BOUNDARY", ".BOUNDARY")
    changes.change_value("/problem/**/input_fields/#/region/", "IMPLICIT BOUNDARY", ".IMPLICIT_BOUNDARY")

    changes.new_version("2.0.0")

    return changes