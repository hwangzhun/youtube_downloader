from src.config.get_software_version import get_software_version

def test_get_version():
    assert get_software_version() == "1.1.0"
