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
from new_convertor import PathSet, Changes, CommentedMap, CommentedSeq, CommentedScalar

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
        "/problem/secondary_equation/input_fields/*/bc_flux/",
        "/problem/primary_equation/input_fields/*/bc_flux/",
        "/problem/secondary_equation/input_fields/*/bc_flux/#/",
        "/problem/primary_equation/input_fields/*/bc_flux/#/",
        "/problem/secondary_equation/input_fields/*/bc_flux!FieldConstant/value/",
        "/problem/primary_equation/input_fields/*/bc_flux!FieldConstant/value/"
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
    path_set = PathSet(["/problem/secondary_equation/input_fields/*/bc_type/",
                        "/problem/primary_equation/input_fields/*/bc_type/"])

    changes.replace_value(path_set,
                          re_forward=("^(robin|neumann)$", "total_flux"),
                          re_backward=(None,
                                       "Select either 'robin' or 'neumann' according to the value of 'bc_flux', 'bc_pressure', 'bc_sigma'."))

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

    '''
         {
          "NAME" : "mesh sets setup, name",
          "action": "move-key",
          "parameters": {
            "source_path":"/problem/mesh/sets/*/name",
            "destination_path":"/problem/mesh/sets_new/$1/name",
              "create_path":true
          }
        },
        {
          "NAME" : "mesh sets setup, elementary regions setup, region_ids",
          "action": "move-key",
          "parameters": {
            "source_path":"/problem/mesh/sets/*/region_ids",
            "destination_path":"/problem/mesh/sets_new/$1/region_ids",
            "set_type_path":"/problem/mesh/sets_new/$1",
            "new_type":"Union",
            "create_path":true
          }
        },
        {
          "NAME" : "mesh sets setup, elementary regions setup, region_labels",
          "action": "move-key",
          "parameters": {
            "source_path":"/problem/mesh/sets/*/region_labels",
            "destination_path":"/problem/mesh/sets_new/$1/regions",
            "set_type_path":"/problem/mesh/sets_new/$1",
            "new_type":"Union",
            "create_path":true
          }
        },
        {
          "NAME" : "mesh sets setup, elementary regions setup, union",
          "action": "move-key",
          "parameters": {
            "source_path":"/problem/mesh/sets/*/union",
            "destination_path":"/problem/mesh/sets_new/$1/regions",
            "set_type_path":"/problem/mesh/sets_new/$1",
            "new_type":"Union",
            "create_path":true
          }
        },
        {
          "NAME" : "mesh sets setup, elementary regions setup, intersection",
          "action": "move-key",
          "parameters": {
            "source_path":"/problem/mesh/sets/*/intersection",
            "destination_path":"/problem/mesh/sets_new/$1/regions",
            "set_type_path":"/problem/mesh/sets_new/$1",
            "new_type":"Intersection",
            "create_path":true
          }
        },
        {
          "NAME" : "mesh sets setup, elementary regions setup, difference",
          "action": "move-key",
          "parameters": {
            "source_path":"/problem/mesh/sets/*/difference",
            "destination_path":"/problem/mesh/sets_new/$1/regions",
            "set_type_path":"/problem/mesh/sets_new/$1",
            "new_type":"Difference",
            "create_path":true
          }
        },
        {
          "action": "delete-key",
          "parameters": {
            "path": "/problem/mesh/sets/*",
            "deep": false
          }
        },
        {
          "action": "delete-key",
          "parameters": {
            "path": "/problem/mesh/sets",
            "deep": false
          }
        },
        {
          "action": "delete-key",
          "parameters": {
            "path": "/problem/mesh/regions/*",
            "deep": false
          }
        },
        {
          "action": "delete-key",
          "parameters": {
            "path": "/problem/mesh/regions",
            "deep": false
          }
        },
        {
          "action" : "merge-arrays",
          "parameters": {
            "source_path":"/problem/mesh/regions_elementary",
            "addition_path":"/problem/mesh/sets_new",
            "destination_path":"/problem/mesh/regions"
          }
        },
        {
          "action" : "merge-arrays",
          "parameters": {
            "source_path":"/problem/mesh/sets_new",
            "addition_path":"/problem/mesh/regions_elementary",
            "destination_path":"/problem/mesh/regions"
          }
        },
    '''

    # CMP AUX
    changes.add_key_to_map("/problem/primary_equation", key='nonlinear_solver', value=CommentedMap())

    changes.move_value("{/problem/primary_equation}/solver", "{}/nonlinear_solver/linear_solver")

    '''
        {
          "NAME": "Move linear_solver under nonlinear_solver in DarcyFlow.",
          "action": "add-key",
          "parameters": {
            "path": "/problem/primary_equation",
            "key": "nonlinear_solver"
          }
        },
        {
          "NAME": "Move linear_solver under nonlinear_solver in DarcyFlow.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/primary_equation/solver",
            "destination_path": "/problem/primary_equation/nonlinear_solver/linear_solver",
            "create_path":true
          }
        },
        {
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/primary_equation/solver",
            "destination_path": "/problem/primary_equation/nonlinear_solver/linear_solver",
            "create_path":true
          }
        },
    '''

    stor_map = CommentedMap()
    stor_map['region'] = CommentedScalar(None, 'ALL')
    stor_map['storativity'] = CommentedScalar(None, 1.0)
    changes.add_key_to_map("/problem/primary_equation!(Unsteady_LMH|Unsteady_MH)/",
                           key="aux_storativity",
                           value=stor_map)
    changes.move_value("{/problem/primary_equation!(Unsteady_LMH|Unsteady_MH)}/aux_storativity", "{}/input_fields/0")
    '''
        {
          "NAME": "Set storativity for Unsteady_LMH.",
          "action": "add-key",
          "parameters": {
            "path": "/problem/primary_equation",
            "key": "aux_region_key",
            "value": "ALL",
            "path-type-filter" : "Unsteady_LMH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
        {
          "NAME": "Set storativity for Unsteady_LMH.",
          "action": "add-key",
          "parameters": {
            "path": "/problem/primary_equation",
            "key": "aux_storativity_key",
            "value": "1.0",
            "path-type-filter" : "Unsteady_LMH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
        {
          "NAME": "Set storativity for Unsteady_LMH.",
          "action" : "move-key",
          "parameters": {
            "source_path":"/problem/primary_equation/aux_region_key",
            "destination_path":"/problem/primary_equation/_input_fields/0/region",
            "path-type-filter" : "Unsteady_LMH",
            "path-type-filter-path" : "/problem/primary_equation",
            "create_path":true
          }
        },
        {
          "NAME": "Set storativity for Unsteady_LMH.",
          "action" : "move-key",
          "parameters": {
            "source_path":"/problem/primary_equation/aux_storativity_key",
            "destination_path":"/problem/primary_equation/_input_fields/0/storativity",
            "path-type-filter" : "Unsteady_LMH",
            "path-type-filter-path" : "/problem/primary_equation",
            "create_path":true
          }
        },
        {
          "NAME": "Set storativity for Unsteady_LMH.",
          "action" : "merge-arrays",
          "parameters": {
            "source_path":"/problem/primary_equation/_input_fields",
            "addition_path":"/problem/primary_equation/input_fields",
            "destination_path":"/problem/primary_equation/input_fields",
            "path-type-filter" : "Unsteady_LMH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
        {
          "NAME": "Set storativity for Unsteady_LMH.",
          "action" : "move-key-forward",
          "parameters": {
            "path":"/problem/primary_equation/input_fields",
            "path-type-filter" : "Unsteady_LMH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
        {
          "NAME": "Set storativity for Unsteady_MH.",
          "action": "add-key",
          "parameters": {
            "path": "/problem/primary_equation",
            "key": "aux_region_key",
            "value": "ALL",
            "path-type-filter" : "Unsteady_MH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
        {
          "NAME": "Set storativity for Unsteady_MH.",
          "action": "add-key",
          "parameters": {
            "path": "/problem/primary_equation",
            "key": "aux_storativity_key",
            "value": "1.0",
            "path-type-filter" : "Unsteady_MH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
        {
          "NAME": "Set storativity for Unsteady_MH.",
          "action" : "move-key",
          "parameters": {
            "source_path":"/problem/primary_equation/aux_region_key",
            "destination_path":"/problem/primary_equation/_input_fields/0/region",
            "path-type-filter" : "Unsteady_MH",
            "path-type-filter-path" : "/problem/primary_equation",
            "create_path":true

          }
        },
        {
          "NAME": "Set storativity for Unsteady_MH.",
          "action" : "move-key",
          "parameters": {
            "source_path":"/problem/primary_equation/aux_storativity_key",
            "destination_path":"/problem/primary_equation/_input_fields/0/storativity",
            "path-type-filter" : "Unsteady_MH",
            "path-type-filter-path" : "/problem/primary_equation",
            "create_path":true

          }
        },
        {
          "NAME": "Set storativity for Unsteady_MH.",
          "action" : "merge-arrays",
          "parameters": {
            "source_path":"/problem/primary_equation/_input_fields",
            "addition_path":"/problem/primary_equation/input_fields",
            "destination_path":"/problem/primary_equation/input_fields",
            "path-type-filter" : "Unsteady_MH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
        {
          "NAME": "Set storativity for Unsteady_MH.",
          "action" : "move-key-forward",
          "parameters": {
            "path":"/problem/primary_equation/input_fields",
            "path-type-filter" : "Unsteady_MH",
            "path-type-filter-path" : "/problem/primary_equation"
          }
        },
    '''

    changes.rename_tag("/problem/primary_equation/", old_tag="Steady_MH", new_tag="Flow_Darcy_MH")
    changes.rename_tag("/problem/primary_equation/", old_tag="Unsteady_MH", new_tag="Flow_Darcy_MH")
    changes.rename_tag("/problem/primary_equation/", old_tag="Unsteady_LMH", new_tag="Flow_Richards_LMH")
    changes.rename_tag("/problem/", old_tag="SequentialCoupling", new_tag="Coupling_Sequential")

    '''
        {
          "NAME": "Use time aware Darcy_MH instead of Steady.",
          "action": "rename-type",
          "parameters": {
            "path": "/problem/primary_equation",
            "old_name": "Steady_MH",
            "new_name": "Flow_Darcy_MH"
          }
        },
            {
          "NAME": "Use time aware Darcy_MH instead of Steady.",
          "action": "rename-type",
          "parameters": {
            "path": "/problem/primary_equation",
            "old_name": "Unsteady_MH",
            "new_name": "Flow_Darcy_MH"
          }
        },
        {
          "NAME": "Use time aware Darcy_MH instead of Steady.",
          "action": "rename-type",
          "parameters": {
            "path": "/problem/primary_equation",
            "old_name": "Unsteady_LMH",
            "new_name": "Flow_Richards_LMH"
          }
        },
        {
          "NAME": "Rename sequential coupling",
          "action": "rename-type",
          "parameters": {
            "path": "/problem",
            "old_name": "SequentialCoupling",
            "new_name": "Coupling_Sequential"
          }
        },
    '''
    changes.rename_key("/problem/", "primary_equation", "flow_equation")
    changes.move_value("/problem/secondary_equation!Coupling_OperatorSplitting",
                       "/problem/solute_equation!Coupling_OperatorSplitting")
    changes.move_value("/problem/secondary_equation!Heat_AdvectionDiffusion_DG",
                       "/problem/heat_equation!Heat_AdvectionDiffusion_DG")
    '''
        {
          "NAME": "Rename sequential coupling keys",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/primary_equation",
            "destination_path": "/problem/flow_equation"
          }
        },
        {
          "NAME": "Rename sequential coupling keys",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/secondary_equation",
            "destination_path": "/problem/solute_equation",
            "type-filter": "Coupling_OperatorSplitting"
          }
        },
        {
          "NAME": "Rename sequential coupling keys",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/secondary_equation",
            "destination_path": "/problem/heat_equation",
            "type-filter": "Heat_AdvectionDiffusion_DG"
          }
        },
    '''

    changes.new_version("2.0.0_rc")

    # CMP AUX
    changes.add_key_to_map("/problem/flow_equation/", key="output_specific", value=CommentedMap())

    changes.move_value("/problem/flow_equation/output/raw_flow_output/",
                       "/problem/flow_equation/output_specific/raw_flow_output/")
    changes.move_value("/problem/flow_equation/output/compute_errors/",
                       "/problem/flow_equation/output_specific/compute_errors/")
    '''
        {
          "NAME": "Make output-specific key.",
          "action": "add-key",
          "parameters": {
            "path": "/problem/flow_equation",
            "key": "output_specific"
          }
        },
        {
          "NAME": "Move to output specific.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/flow_equation/output/raw_flow_output",
            "destination_path": "/problem/flow_equation/output_specific/raw_flow_output",
            "create_path":true
          }
        },
        {
          "NAME": "Move to output specific.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/flow_equation/output/compute_errors",
            "destination_path": "/problem/flow_equation/output_specific/compute_errors",
            "create_path":true
          }
        },
    '''

    changes.move_value("{/problem/flow_equation}/output/output_stream/", "{}/output_stream/")

    equations = "(flow_equation|" \
                "solute_equation/transport|" \
                "solute_equation/reaction_term|" \
                "solute_equation/reaction_term/reaction_mobile|" \
                "solute_equation/reaction_term/reaction_immobile|" \
                "heat_equation)"
    changes.rename_key("/problem/" + equations + "/output/", old_key="output_fields", new_key="fields")

    changes.move_value("{/problem/(flow_equation|solute_equation|heat_equation)/output_stream}/time_list/#/", "{}/times/#/")
    changes.move_value("{/problem/(flow_equation|solute_equation|heat_equation)/output_stream}/time_step/",
                       "{}/times/0/step/")

    changes.move_value("{/problem/(flow_equation|solute_equation|heat_equation)}/output_stream/add_input_times/",
                       "{}/output/add_input_times/")
    changes.copy_value("/problem/solute_equation/output/add_input_times/",
                       "/problem/(solute_equation/reaction_term|"
                       "solute_equation/reaction_term/reaction_mobile|"
                       "solute_equation/reaction_term/reaction_immobile"
                       ")/output/add_input_times/")
    '''
        {
          "NAME": "Move DarcyFlow output_stream.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/flow_equation/output/output_stream",
            "destination_path": "/problem/flow_equation/output_stream",
            "create_path":true
          }
        },
        {
          "NAME": "Rename DarcyFlow output_fields.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/flow_equation/output/output_fields",
            "destination_path": "/problem/flow_equation/output/fields"
          }
        },
        {
          "NAME": "Move time step for DarcyFlow output stream.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/flow_equation/output_stream/time_step",
            "destination_path": "/problem/flow_equation/output_stream/times/0/step",
            "create_path":true
          }
        },
        {
          "NAME": "Move time_list for Darcy.",
          "action" : "merge-arrays",
          "parameters": {
            "source_path": "/problem/flow_equation/output_stream/time_list",
            "addition_path": "/problem/flow_equation/output_stream/times",
            "destination_path": "/problem/flow_equation/output_stream/times"
          }
        },
        {
          "NAME": "Move time step for DarcyFlow output stream.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/flow_equation/output_stream/add_input_times",
            "destination_path": "/problem/flow_equation/output/add_input_times",
            "create_path":true
          }
        },




        {
          "NAME": "Make output_fields in transport.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/transport/output_fields",
            "destination_path": "/problem/solute_equation/transport/output/fields",
            "create_path":true
          }
        },
        {
          "NAME": "Make output_fields in dual porosity.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/reaction_term/output_fields",
            "destination_path": "/problem/solute_equation/reaction_term/output/fields",
            "create_path":true
          }
        },
        {
          "NAME": "Make output_fields in mobile reaction.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/reaction_term/reaction_mobile/output_fields",
            "destination_path": "/problem/solute_equation/reaction_term/reaction_mobile/output/fields",
            "create_path":true
          }
        },
        {
          "NAME": "Make output_fields in immobile reaction.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/reaction_term/reaction_immobile/output_fields",
            "destination_path": "/problem/solute_equation/reaction_term/reaction_immobile/output/fields",
            "create_path":true
          }
        },


        {
          "NAME": "Make time step for transport output stream.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/output_stream/time_step",
            "destination_path": "/problem/solute_equation/output_stream/times/0/step",
            "create_path":true
          }
        },
        {
          "NAME": "Move time_list for transport.",
          "action" : "merge-arrays",
          "parameters": {
            "source_path": "/problem/solute_equation/output_stream/time_list",
            "addition_path": "/problem/solute_equation/output_stream/times",
            "destination_path": "/problem/solute_equation/output_stream/times"
          }
        },


        {
          "NAME": "Move add_input_times for transport.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/output_stream/add_input_times",
            "destination_path": "/problem/solute_equation/output/add_input_times",
            "keep_source":true,
            "create_path":true
          }
        },
        {
          "NAME": "Move add_input_times for transport.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/output_stream/add_input_times",
            "destination_path": "/problem/solute_equation/reaction_term/output/add_input_times",
            "keep_source":true,
            "create_path":true
          }
        },
        {
          "NAME": "Move add_input_times for transport.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/output_stream/add_input_times",
            "destination_path": "/problem/solute_equation/reaction_term/reaction_mobile/output/add_input_times",
            "keep_source":true,
            "create_path":true
          }
        },
        {
          "NAME": "Move add_input_times for transport.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/solute_equation/output_stream/add_input_times",
            "destination_path": "/problem/solute_equation/reaction_term/reaction_immobile/output/add_input_times",
            "create_path":true
          }
        },





        {
          "NAME": "Rename Heat output_fields.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/heat_equation/output/output_fields",
            "destination_path": "/problem/heat_equation/output/fields",
            "create_path":true
          }
        },
        {
          "NAME": "Move time step for Heat output stream.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/heat_equation/output_stream/time_step",
            "destination_path": "/problem/heat_equation/output_stream/times/0/step",
            "create_path":true
          }
        },
        {
          "NAME": "Move time_list for Heat.",
          "action" : "merge-arrays",
          "parameters": {
            "source_path": "/problem/heat_equation/output_stream/time_list",
            "addition_path": "/problem/heat_equation/output_stream/times",
            "destination_path": "/problem/heat_equation/output_stream/times"
          }
        },
        {
          "NAME": "Move time step for Heat output stream.",
          "action": "move-key",
          "parameters": {
            "source_path": "/problem/heat_equation/output_stream/add_input_times",
            "destination_path": "/problem/heat_equation/output/add_input_times",
            "create_path":true
          }
        },
    '''

    empty_map = CommentedMap()
    changes.change_value("/problem/(flow_equation|solute_equation|heat_equation)/balance", True, empty_map)

    '''
        {
            "NAME": "Change balance:true",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/flow_equation/balance",
              "old_value" : "true",
              "new_value" : "{}"
            }
        },
        {
            "NAME": "Change balance:true",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/solute_equation/balance",
              "old_value" : "true",
              "new_value" : "{}"
            }
        },
        {
            "NAME": "Change balance:true",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/heat_equation/balance",
              "old_value" : "true",
              "new_value" : "{}"
            }
        },
    '''
    false_map = CommentedMap()
    false_map['add_output_times'] = False
    changes.change_value("/problem/(flow_equation|solute_equation|heat_equation)/balance", False, false_map)

    '''
        {
            "NAME": "Change balance:true",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/flow_equation/balance",
              "old_value" : "false",
              "new_value" : "{add_output_times: false}"
            }
        },
        {
            "NAME": "Change balance:true",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/solute_equation/balance",
              "old_value" : "false",
              "new_value" : "{add_output_times: false}"
            }
        },
        {
            "NAME": "Change balance:true",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/heat_equation/balance",
              "old_value" : "false",
              "new_value" : "{add_output_times: false}"
            }
        },
    '''
    changes.change_value("/problem/**/input_fields/#/region", "BOUNDARY", ".BOUNDARY")
    changes.change_value("/problem/**/input_fields/#/region", "IMPLICIT_BOUNDARY", ".IMPLICIT_BOUNDARY")

    '''
        {
            "NAME": "Change BOUNDARY to .BOUNDARY",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/*/input_fields/*/region",
              "old_value" : "BOUNDARY",
              "new_value" : ".BOUNDARY"
            }
        },
        {
            "NAME": "Change BOUNDARY to .BOUNDARY",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/solute_equation/*/input_fields/*/region",
              "old_value" : "BOUNDARY",
              "new_value" : ".BOUNDARY"
            }
        },
        {
            "NAME": "Change BOUNDARY to .BOUNDARY",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/solute_equation/reaction_term/*/input_fields/*/region",
              "old_value" : "BOUNDARY",
              "new_value" : ".BOUNDARY"
            }
        },
        {
            "NAME": "Change BOUNDARY to .BOUNDARY, hack to deal with substitution matching the substrings",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/*/input_fields/*/region",
              "old_value" : "IMPLICIT .BOUNDARY",
              "new_value" : ".IMPLICIT_BOUNDARY"
            }
        },
        {
            "NAME": "Change BOUNDARY to .BOUNDARY",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/solute_equation/*/input_fields/*/region",
              "old_value" : "IMPLICIT .BOUNDARY",
              "new_value" : ".IMPLICIT_BOUNDARY"
            }
        },
        {
            "NAME": "Change BOUNDARY to .BOUNDARY",
            "action": "change-value",
            "parameters":{
              "path" : "/problem/solute_equation/reaction_term/*/input_fields/*/region",
              "old_value" : "IMPLICIT .BOUNDARY",
              "new_value" : ".IMPLICIT_BOUNDARY"
            }
        }


      ]
    }

    '''
    changes.new_version("2.0.0")

    return changes