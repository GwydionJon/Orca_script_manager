import pytest
from script_maker2000.crest import Crest_Job


def test_crest():
    with pytest.raises(NotImplementedError):
        Crest_Job({"test": "test"})
