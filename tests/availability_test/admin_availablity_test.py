import pytest

def admin_page_availablity_test(authenticated_client):
    responce = authenticated_client.get('/admin')
    assert 200 <= responce.status_code < 300