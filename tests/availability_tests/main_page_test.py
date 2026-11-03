import pytest

def test_is_available_main_page(client):
    responce = client.get('/')
    assert 200 <= responce.status_code < 300