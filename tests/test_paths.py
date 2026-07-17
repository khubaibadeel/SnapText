import pytest
from snaptext_app.core.paths import get_app_data_dir, get_screenshots_dir

def test_app_data_dir_creation():
    path = get_app_data_dir()
    assert path.exists()
    assert path.is_dir()
    assert "SnapText" in str(path)

def test_screenshots_dir_creation():
    path = get_screenshots_dir()
    assert path.exists()
    assert path.is_dir()
