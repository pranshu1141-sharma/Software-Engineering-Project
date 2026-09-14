from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import pytest
from healthcare_ml import patient_api as service


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(service, 'DB_PATH', tmp_path / 'demo.sqlite3')
    service.init_db()
    return TestClient(service.app)


def auth(client):
    return {'Authorization': 'Bearer ' + client.post('/api/session').json()['token']}


def booking(client, headers, request_id='request-001'):
    slot = client.get('/api/providers/d1/slots').json()['slots'][0]['value']
    payload = {'provider_id': 'd1', 'slot': slot, 'request_id': request_id}
    response = client.post('/api/appointments', json=payload, headers=headers)
    return response, payload


def test_booking_idempotency_and_owner_isolation(client):
    owner, stranger = auth(client), auth(client)
    response, payload = booking(client, owner)
    assert response.status_code == 201
    uid = response.json()['id']
    assert client.post('/api/appointments', json=payload, headers=owner).json()['id'] == uid
    assert len(client.get('/api/appointments', headers=owner).json()['appointments']) == 1
    assert client.get('/api/appointments', headers=stranger).json()['appointments'] == []
    assert client.post(f'/api/appointments/{uid}/cancel', headers=stranger).status_code == 404
    assert client.get('/api/appointments').status_code == 401


def test_slot_race_and_cancellation_release(client):
    first, second = auth(client), auth(client)
    slot = client.get('/api/providers/d1/slots').json()['slots'][0]['value']
    def attempt(headers):
        return client.post('/api/appointments', headers=headers, json={'provider_id': 'd1', 'slot': slot, 'request_id': 'race-booking'})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(attempt, [first, second]))
    assert sorted(r.status_code for r in responses) == [201, 409]
    winner = 0 if responses[0].status_code == 201 else 1
    headers = [first, second][winner]
    uid = responses[winner].json()['id']
    assert client.post(f'/api/appointments/{uid}/cancel', headers=headers).status_code == 200
    assert client.post('/api/appointments', headers=headers, json={'provider_id': 'd1', 'slot': slot, 'request_id': 'new-request'}).status_code == 201


def test_complete_queue_journey(client):
    owner = auth(client)
    response, _ = booking(client, owner)
    uid = response.json()['id']
    assert client.get(f'/api/appointments/{uid}/queue', headers=owner).status_code == 409
    assert client.post(f'/api/appointments/{uid}/check-in', headers=owner).status_code == 200
    assert client.post(f'/api/appointments/{uid}/cancel', headers=owner).status_code == 409
    for expected in [2, 1, 0]:
        result = client.post(f'/api/appointments/{uid}/demo-advance', headers=owner)
        assert result.status_code == 200
        assert result.json()['ahead'] == expected
    result = client.post(f'/api/appointments/{uid}/demo-advance', headers=owner).json()
    assert result['appointment']['status'] == 'completed'
    assert result['estimated_minutes'] == 0


def test_real_model_guidance_and_invalid_input(client):
    owner = auth(client)
    result = client.post('/api/guidance', headers=owner, json={'text': 'My skin has itchy flaky patches and a rash.'})
    assert result.status_code == 200
    assert 'Dermatology' in result.json()['specialties']
    assert result.json()['review_required']
    assert client.post('/api/guidance', headers=owner, json={'text': '          '}).status_code == 422
    assert client.get('/api/providers/missing/slots').status_code == 404
