from pathlib import Path
from collections import defaultdict


default_style = {"margin": "10px", "width": "100%"}


def convert_paths_to_dict(path_list, mode="remote"):

    def tree():
        return defaultdict(tree)

    def add_path(root, parts, full_path):
        for part in parts:
            found = False
            for child in root:
                if child["title"] == part:
                    root = child["children"]
                    found = True
                    break
            if not found:
                new_child = {"title": part, "key": full_path, "children": []}
                root.append(new_child)
                root = new_child["children"]
        return root

    root = []
    for path in path_list:

        path = Path(path)
        parts = path.parts

        if mode == "local":
            add_path(root, parts, str(path.resolve()))
        else:
            add_path(root, parts, str(path))

    def default_to_regular(d):
        if isinstance(d, defaultdict):
            d = {k: default_to_regular(v) for k, v in d.items()}
        return d

    return default_to_regular(root)


def check_local_tar_file(file_path):

    input_valid = False

    if file_path is None:
        return input_valid, not input_valid, not input_valid

    file_path = Path(file_path)
    if file_path.is_file() and ".tar" in file_path.name:
        input_valid = True
    return input_valid, not input_valid, not input_valid


def get_local_paths(n_clicks, path):

    output = Path(path).rglob("[!.]*")
    output = [str(p) for p in output]
    output = convert_paths_to_dict(output, mode="local")

    output = {"title": str(Path.cwd()), "key": str(Path.cwd()), "children": output}

    return output


def return_selected_path(selected_path):
    if selected_path is None or len(selected_path) == 0:
        return None
    return str(Path(selected_path[0]).as_posix())


def print_selected_path(selected_path):
    if selected_path is None or len(selected_path) == 0:
        return "No path selected yet."
    return f"You selected: {str(Path(selected_path[0]).as_posix())}"
