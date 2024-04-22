from script_maker2000.dash_ui.dash_main_gui import create_main_app


def test_ui(clean_tmp_dir):

    config = clean_tmp_dir / "example_config.json"
    create_main_app(str(config), None)
