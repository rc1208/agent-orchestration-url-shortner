from pathlib import Path

import pytest

from agentic_url_shortener.codebase_analysis import PythonCodebaseAnalyzer


pytestmark = pytest.mark.unit


def test_analyzer_discovers_modules_symbols_routes_and_tests() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "brownfield_url_service"
    result = PythonCodebaseAnalyzer().analyze(fixture, "Add expiration and analytics")

    assert "app/service.py" in result.modules
    assert any("UrlService" in symbol for symbol in result.symbols)
    assert "POST /urls -> create_url" in result.routes
    assert "tests/test_service.py" in result.tests
    assert result.impacted_files
    assert all(reference.path in result.modules for reference in result.evidence)
