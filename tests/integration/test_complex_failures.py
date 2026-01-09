import httpx
import pytest

from geofinder.exceptions import ServiceError, ServiceTimeoutError
from geofinder.pelias import PeliasClient


@pytest.mark.asyncio
async def test_intermittent_timeout():
    """Test scenario where the service times out twice and then succeeds."""
    client = PeliasClient(
        url="https://test.example.com",
        max_retries=3,
        retry_base_delay=0.01
    )

    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise httpx.TimeoutException("Simulated timeout")
        return httpx.Response(200, json={"features": [{"properties": {"name": "Barcelona"}}]}, request=httpx.Request("GET", args[0]))

    client.client.get = mock_get

    result = await client.geocode("Barcelona")
    assert call_count == 3
    assert result["features"][0]["properties"]["name"] == "Barcelona"
    await client.close()

@pytest.mark.asyncio
async def test_malformed_json_response():
    """Test scenario where the service returns HTTP 200 but malformed/unexpected JSON."""
    client = PeliasClient(url="https://test.example.com")

    async def mock_get(*args, **kwargs):
        # Missing 'features' key which is expected by PeliasClient
        return httpx.Response(200, json={"unexpected": "data"}, request=httpx.Request("GET", args[0]))

    client.client.get = mock_get

    # Depending on implementation, it might raise KeyError or handle it.
    # We want to ensure it doesn't crash the whole app but handles the error gracefully.
    with pytest.raises(ServiceError):
        await client.geocode("Barcelona")
    await client.close()

@pytest.mark.asyncio
async def test_latency_spike_causing_timeout():
    """Test scenario with a simulated delay that triggers the client's timeout."""
    # We set a very low timeout on the client to trigger it quickly
    client = PeliasClient(url="https://test.example.com", timeout=0.05)

    async def mock_get(*args, **kwargs):
        # Explicitly raise ReadTimeout to simulate the behavior of a real client
        # when the timeout is reached during a read operation.
        request = httpx.Request("GET", args[0])
        raise httpx.ReadTimeout("Simulated read timeout", request=request)

    client.client.get = mock_get

    with pytest.raises(ServiceTimeoutError):
        await client.geocode("Barcelona")
    await client.close()

@pytest.mark.asyncio
async def test_503_service_unavailable_retries():
    """Verify that 503 errors are retried and eventually fail if persistent."""
    client = PeliasClient(
        url="https://test.example.com",
        max_retries=2,
        retry_base_delay=0.01,
        retry_on_5xx=True
    )

    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        request = httpx.Request("GET", args[0])
        return httpx.Response(503, text="Service Unavailable", request=request)

    client.client.get = mock_get

    with pytest.raises(ServiceError) as exc_info:
        await client.geocode("Barcelona")

    assert call_count == 3 # 1 original + 2 retries
    assert "Service Unavailable" in str(exc_info.value) or "503" in str(exc_info.value)
    await client.close()
