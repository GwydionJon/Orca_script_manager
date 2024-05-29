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


def check_local_zip_file(file_path):

    input_valid = False

    if file_path is None:
        return input_valid, not input_valid, not input_valid

    file_path = Path(file_path)
    if file_path.is_file() and ".zip" in file_path.name:
        input_valid = True
    return input_valid, not input_valid, not input_valid


def _check_remote_dir(target_dir, remote_connection):

    result = remote_connection.run(f"test -d {target_dir}", warn=True)

    # if the directory does not exist, it can't already be used for a calculation.
    if result.exited != 0:
        return True, False, False

    check_existing_working_dir = remote_connection.run(f"ls {target_dir}", hide=True)

    check_existing_working_dir = check_existing_working_dir.stdout

    exists_already = False
    for file in check_existing_working_dir.strip().split("\n"):
        if "config__" in file:
            exists_already = True
            break
        if "finished" == file:
            exists_already = True
            break
        if "working" == file:
            exists_already = True
            break
        if "_molecules.json" in file:
            exists_already = True
            break
        if "job_backup.json" == file:
            exists_already = True
            break

    if exists_already:
        return False, True, True

    return True, False, False


def get_local_paths(n_clicks, path):

    output = Path(path).rglob("[!.]*.zip")
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


def _workspaces_paths(remote_connection, workspace_id=None):

    if workspace_id is None:
        output = remote_connection.run("ws_list", hide=True)

    else:
        output = remote_connection.run(f"ws_list {workspace_id}", hide=True)

    if output.stdout == "":
        return [], []
    output = output.stdout.split("\n")[:-1]

    ws_ids = [line.split(":")[1].strip() for line in output if "id:" in line]
    ws_paths = [
        line.split(":")[1].strip() for line in output if "workspace directory" in line
    ]

    return ws_ids, ws_paths


def _get_remote_paths(n_clicks, path, remote_connection):

    if path is None or path.strip() == "":
        path = "."
    if path.strip() == "/":
        path = "."

    if path[-1] != "/":
        path = path + "/"

    # get workspace ids and paths:

    ws_ids, ws_paths = _workspaces_paths(remote_connection)

    main_path = "cwd"

    if path == "workspaces/":
        path = " ".join(ws_paths)
        main_path = "workspaces"

    else:
        for ws_id, ws_path in zip(ws_ids, ws_paths):
            if ws_id in path:
                path = path.replace(ws_id, ws_path)

    output = remote_connection.run(
        f"find {path} -not -path " + r"'*/\.*' -type d -print",
        hide=True,
        warn=True,  # noqa
        timeout=60,
    )

    if output.exited != 0:
        return {"title": "Nothing found", "key": "Nothing", "children": []}

    output = output.stdout.split("\n")[:-1]

    if main_path == "cwd":
        main_path = remote_connection.run("pwd", hide=True).stdout.strip()

    output = convert_paths_to_dict(output, mode="remote")

    return {"title": main_path, "key": main_path, "children": output}


def _get_live_updates(n_intervals, target_dir, remote_connection):
    """This function will check the output file for the job status and update the textarea.

    Args:
        n_intervals (int): Value of the button to trigger the function.
        target_dir (str): Remote target dir for the calculation.
    """
    if n_intervals is None:
        return "No job submitted yet."

    output_tracking_file = target_dir + "/check_shell_output.out"
    result = remote_connection.run(
        f"[ -f {output_tracking_file} ] && cat {output_tracking_file} || echo 'Output file not yet created'",
        hide=True,
    )

    result_output = result.stdout

    if "Error" in result_output:
        return result_output, 0

    if "Starting the batch processing:" in result_output:
        return result_output, 0

    return result.stdout, -1


def disable_button_start_interval(n_clicks):
    return True, -1


def _prepare_submission(
    input_file, target_dir, output_tracking_file, remote_connection
):
    if input_file is None or target_dir is None:
        return "No job submitted yet."

    # use batch to check is the target dir exists, and if not recursivly create it.
    remote_connection.run(
        f"test -d {target_dir} || mkdir -p {target_dir}",
        hide=True,
    )

    # initiate the output file
    remote_connection.run(
        f"echo 'Starting the batch setup: ' > {output_tracking_file} "
    )

    result = remote_connection.put(input_file, target_dir)
    remote_connection.run(
        f"echo 'File {result.local} copied to {result.remote}'  >> {output_tracking_file} "
    )

    # check if the script manager has already been installed by the user, if not do so.
    remote_connection.run(
        r"command -v script_maker_cli >/dev/null 2>&1 && echo 'The orca script manager is installed. ' ||"
        + f" {{ echo >&2 'The Script maker package is not installed. Installing now:.'>>{output_tracking_file};"
        + "ml devel/python/3.11.4; echo 'Unsetting pip'; unset PIP_TARGET; "
        + f"pip install git+https://github.com/GwydionJon/Orca_script_manager >> {output_tracking_file}; }}",
        timeout=600,
        hide=True,
    )


def _submit_job(n_clicks, input_file, target_dir, remote_connection):
    """This function will copy the input file to the target dir and start the calculation.
    Will also start the interval for live updates.

    Args:
        n_clicks (int): Value of the button to trigger the function.
        input_file (str): Local input file to copy to the target dir.
        target_dir (str): Remote target dir for the calculation.
    """

    output_tracking_file = target_dir + "/check_shell_output.out"

    _prepare_submission(input_file, target_dir, output_tracking_file, remote_connection)

    # the pathllib library does not like creating unix paths on a windows machine
    # if this script is ever run on a windows server someone needs to find a better solution
    input_file = Path(input_file)
    file_to_extract = target_dir + "/" + input_file.name

    # create a new screen session to run the program in.

    screen_check = remote_connection.run("screen -ls", warn=True, hide=True)

    if Path(input_file).stem not in screen_check.stdout:
        remote_connection.run(f"screen -dmS {Path(input_file).stem}")

    # start the calculation using nohup

    print(f"script_maker_cli start-zip --zip {str(file_to_extract)} -e {target_dir}")
    result = remote_connection.run(
        f'screen -S {Path(input_file).stem} -X stuff "ml devel/python/3.11.4 ; '
        + f" script_maker_cli start-zip --zip {str(file_to_extract)} -e {target_dir} --hide_job_status "
        + f'>> {output_tracking_file} \n"',
        hide=False,
        warn=True,
    )
    # check if job was started correctly
    if result.exited != 0:
        raise Exception(f"Error starting job: \n {result.stderr}")

    return None
