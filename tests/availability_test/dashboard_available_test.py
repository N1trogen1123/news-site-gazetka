import pytest

def test_dashboard_accessible_for_user(authenticated_client):
    response = authenticated_client.get('/dashboard')
    assert 200 <= response.status_code < 300