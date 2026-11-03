import pytest

def test_available_moder_page(authenticated_client):
    responce = authenticated_client.get('/moderation')
    assert 200 <= responce.status_code < 300
    