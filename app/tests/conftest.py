import sys
from unittest.mock import MagicMock

_mock_connection = MagicMock()
_mock_connection.engine = MagicMock()

sys.modules["database.connection"] = _mock_connection