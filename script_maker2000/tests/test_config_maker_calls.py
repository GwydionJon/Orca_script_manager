from script_maker2000.dash_ui.config_maker_calls import (
    create_config_file,
    check_layer_config,
    create_layer_cyto_graph,
    add_additional_settings_block,
    displayTapNodeData,
    _ordered_dict_recursive,
    check_input_path,
)
import copy
from collections import defaultdict, OrderedDict
from pathlib import Path

possible_layer_types = ["type1", "type2", "type3"]
possible_resource_settings = ["setting1", "setting2", "setting3"]
loop_config_keys = ["type", "step_id", "max_n_jobs", "options"]
options_keys = [
    "ram_per_core",
    "n_cores_per_calculation",
    "n_calculation_at_once",
    "disk_storage",
    "args",
    "automatic_ressource_allocation",
]


def test_create_config_file():
    main_config_inputs = {
        "parallel_layer_run": None,
        # "common_input_files": "file1,file2",
        # "xyz_path": "/path/to/xyz",
        "input_file_path": "/path/to/input",
        "max_n_jobs": "4",
        "max_ram_per_core": "8",
        "max_nodes": "2",
        "wait_for_results_time": "10",
    }

    structure_check_config_inputs = {
        "structure_check_1": "value1",
        "structure_check_2": "value2",
    }

    analysis_config_inputs = {
        "analysis_check_1": "value1",
        "analysis_check_2": "value2",
    }

    layer_config_inputs = {
        "layer_name": ["layer1", "layer2"],
        "type": ["type1", "type2"],
        "step_id": ["0", "1"],
        "additional_input_files": [None, "file3"],
        "additional_settings_block": {
            "block": [None, None],
            "value": [None, None],
        },
        "ram_per_core": ["8", "16"],
        "n_cores_per_calculation": ["4", "8"],
        "n_calculation_at_once": ["2", "4"],
        "disk_storage": ["100", "200"],
    }

    result = create_config_file(
        1,
        main_config_inputs,
        structure_check_config_inputs,
        analysis_config_inputs,
        layer_config_inputs,
    )

    assert isinstance(result, tuple)
    assert len(result) == 4
    assert isinstance(result[0], list)
    assert isinstance(result[1], defaultdict)
    assert isinstance(result[2], str)
    assert isinstance(result[3], bool)

    main_config_inputs_json = copy.deepcopy(main_config_inputs)
    main_config_inputs_json["input_file_path"] = (
        Path(__file__).parent
        / "test_data"
        / "input_files"
        / "example_xyz"
        / "example_molecules.json"
    )
    result = create_config_file(
        1,
        main_config_inputs_json,
        structure_check_config_inputs,
        analysis_config_inputs,
        layer_config_inputs,
    )

    config = result[1]
    assert (
        Path(config["main_config"]["input_file_path"]).name
        == main_config_inputs_json["input_file_path"].name
    )

    main_config_inputs_dir = copy.deepcopy(main_config_inputs)
    main_config_inputs_dir["input_file_path"] = (
        Path(__file__).parent / "test_data" / "input_files" / "example_xyz"
    )
    result = create_config_file(
        1,
        main_config_inputs_dir,
        structure_check_config_inputs,
        analysis_config_inputs,
        layer_config_inputs,
    )

    config = result[1]
    assert (
        Path(config["main_config"]["input_file_path"]).name
        == main_config_inputs_dir["input_file_path"].name
    )

    main_config_inputs_xyz = copy.deepcopy(main_config_inputs)
    main_config_inputs_xyz["input_file_path"] = (
        Path(__file__).parent
        / "test_data"
        / "input_files"
        / "example_xyz"
        / "START_a004_b007__c0m1.xyz"
    )
    result = create_config_file(
        1,
        main_config_inputs_xyz,
        structure_check_config_inputs,
        analysis_config_inputs,
        layer_config_inputs,
    )

    config = result[1]
    assert (
        Path(config["main_config"]["input_file_path"]).name
        == main_config_inputs_xyz["input_file_path"].name
    )


def test_check_layer_config():
    layer_config_inputs = {
        "layer_name": ["layer1", "layer2"],
        "type": ["type1", "type2"],
        "step_id": ["0", "1"],
        "additional_input_files": [None, "file3"],
        "additional_settings_block": {
            "block": [None, "block2"],
            "value": [None, "value2"],
        },
        "ram_per_core": ["8", "16"],
        "n_cores_per_calculation": ["4", "8"],
        "n_calculation_at_once": ["2", "4"],
        "disk_storage": ["100", "200"],
    }
    settings_dict = defaultdict(OrderedDict)

    check_layer_config(layer_config_inputs, settings_dict, 0, "layer1")

    assert "layer1" in settings_dict["loop_config"]
    assert settings_dict["loop_config"]["layer1"]["type"] == "type1"
    assert settings_dict["loop_config"]["layer1"]["step_id"] == "0"
    assert settings_dict["loop_config"]["layer1"]["options"]["ram_per_core"] == 8
    assert (
        settings_dict["loop_config"]["layer1"]["options"]["n_cores_per_calculation"]
        == 4
    )
    assert (
        settings_dict["loop_config"]["layer1"]["options"]["n_calculation_at_once"] == 2
    )
    assert settings_dict["loop_config"]["layer1"]["options"]["disk_storage"] == 100
    assert settings_dict["loop_config"]["layer1"]["options"]["args"] == {}


def test_create_layer_cyto_graph():
    settings_dict = defaultdict(
        OrderedDict,
        {
            "loop_config": {
                "layer1": {
                    "type": "type1",
                    "step_id": "0",
                    "additional_input_files": "file1",
                    "options": {},
                },
                "layer2": {
                    "type": "type2",
                    "step_id": "1",
                    "additional_input_files": "file2",
                    "options": {},
                },
            }
        },
    )

    graph = create_layer_cyto_graph(settings_dict)

    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["data"]["source"] == "layer1"
    assert graph["edges"][0]["data"]["target"] == "layer2"


def test_check_input_path(tmpdir):
    file = tmpdir.join("test.xyz")
    file.write("content")

    valid, invalid = check_input_path(file.strpath)
    assert valid
    assert not invalid

    valid, invalid = check_input_path(tmpdir.strpath)
    assert valid
    assert not invalid

    valid, invalid = check_input_path("/invalid/path")
    assert not valid
    assert invalid


def test_add_additional_settings_block():
    n_clicks = 1
    additional_settings_value_col_children = []
    additional_settings_block_col_children = []
    button_id = {"type": "add_settings_block", "index": 0}

    result = add_additional_settings_block(
        n_clicks,
        additional_settings_value_col_children,
        additional_settings_block_col_children,
        button_id,
    )

    assert len(result[0]) == 1
    assert len(result[1]) == 1


def test_displayTapNodeData():
    data = {"key": "value"}
    result = displayTapNodeData(data)
    assert isinstance(result, str)
    assert "key" in result
    assert "value" in result


def test_ordered_dict_recursive():
    d = {"b": 2, "a": {"d": 4, "c": 3}}
    result = _ordered_dict_recursive(d)
    assert isinstance(result, OrderedDict)
    assert list(result.keys()) == ["b", "a"]
    assert list(result["a"].keys()) == ["d", "c"]
