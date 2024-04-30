import logging
from script_maker2000.batch_manager import BatchManager  # noqa
import script_maker2000.cpu_benchmark_analysis  # noqa


script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


script_maker_log.setLevel("DEBUG")
script_maker_error.setLevel("DEBUG")
