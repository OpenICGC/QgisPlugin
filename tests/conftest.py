
import httpx
import pytest

from geofinder import GeoFinder


@pytest.fixture
def gf():
    """Create a GeoFinder instance for testing."""
    return GeoFinder(icgc_url="https://eines.icgc.cat/geocodificador")


class MockResponseGenerator:
    """Helper to generate mock responses for PeliasClient."""

    def __init__(self):
        self.call_count = 0
        self.responses = []  # Fallback sequential responses
        self.pattern_responses = {} # Pattern-based responses
        self.urls_called = []

    def add_response(self, status_code=200, json_data=None, exception=None):
        """Add a planned response to the sequential queue."""
        self.responses.append({
            "status_code": status_code,
            "json": json_data or {"features": []},
            "exception": exception
        })
        return self

    def add_pattern_response(self, pattern, status_code=200, json_data=None, exception=None):
        """Add a response for a specific URL pattern."""
        self.pattern_responses[pattern] = {
            "status_code": status_code,
            "json": json_data or {"features": []},
            "exception": exception
        }
        return self

    async def mock_get(self, url, *args, **kwargs):
        """Async mock for httpx.AsyncClient.get."""
        self.call_count += 1
        url_str = str(url)
        params = kwargs.get("params", {})

        # 1. Check pattern matches
        for pattern, resp_config in self.pattern_responses.items():
            # Check if pattern is in URL path OR in any param value
            if pattern in url_str:
                 return self._make_response(url_str, resp_config)

            for p_val in params.values():
                if pattern in str(p_val):
                    return self._make_response(url_str, resp_config)

        # 2. Sequential fallback
        if self.responses:
            resp_idx = min(self.call_count - 1, len(self.responses) - 1)
            return self._make_response(url_str, self.responses[resp_idx])

        # 3. Default empty response
        return httpx.Response(200, json={"features": []}, request=httpx.Request("GET", url_str))

    def _make_response(self, url, resp_config):
        if resp_config.get("exception"):
            raise resp_config["exception"]
        return httpx.Response(
            resp_config["status_code"],
            json=resp_config["json"],
            request=httpx.Request("GET", url)
        )


@pytest.fixture
def pelias_mock(monkeypatch):
    """Fixture that patches PeliasClient's internal httpx client."""
    generator = MockResponseGenerator()

    from geofinder.pelias import PeliasClient

    # Patch the 'call' or internal client? Patching the internal client's get is better.
    # But we need to do it globally for all instances.

    original_init = PeliasClient.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # Force the mock on the client
        self.client.get = generator.mock_get

    monkeypatch.setattr(PeliasClient, "__init__", patched_init)
    return generator


def pytest_addoption(parser):
    """Add --integration command line option."""
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests marked with 'integration' unless --integration is provided."""
    if config.getoption("--integration"):
        # --integration given in cli: do not skip integration tests
        return
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
