import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
@pytest.mark.parametrize('origin', [
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
    'http://localhost:5173',
    'http://localhost:5174',
])
async def test_local_frontend_origins_can_preflight_login(origin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.options(
            '/api/v1/auth/login',
            headers={
                'Origin': origin,
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type',
            },
        )
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == origin
