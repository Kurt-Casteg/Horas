"""Asegura que el directorio raíz del proyecto esté en sys.path para los tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
