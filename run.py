from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Always load this checkout first. This avoids accidentally importing an older
# SnapText package from another folder or from Python's site-packages.
root_text = str(PROJECT_ROOT)
if root_text in sys.path:
    sys.path.remove(root_text)
sys.path.insert(0, root_text)
os.chdir(PROJECT_ROOT)

from snaptext_app.main import run
from snaptext_app.version import __version__


if __name__ == "__main__":
    print(f"SnapText {__version__}")
    print(f"Application folder: {PROJECT_ROOT}")
    run()
