"""Package entry point for the GUI: ``python -m datacard_gen.gui``."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is visible when running from the src layout.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datacard_gen_gui import main  # noqa: E402

if __name__ == "__main__":
    main()
