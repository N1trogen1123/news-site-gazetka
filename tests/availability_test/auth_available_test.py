import pytest

def test_available_auth_page(client):
    responce_1 = client.get('/auth/login')
    responce_2 = client.get('/auth/register')
    assert (200 <= responce_1.status_code < 300) and (200 <= responce_2.status_code < 300)
