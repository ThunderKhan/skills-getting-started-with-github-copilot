from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture
def activity_data(monkeypatch):
    isolated_activities = deepcopy(app_module.activities)
    monkeypatch.setattr(app_module, "activities", isolated_activities)
    return isolated_activities


@pytest.fixture
def client(activity_data):
    with TestClient(app_module.app) as test_client:
        yield test_client


def test_get_activities_returns_activity_data(client, activity_data):
    # Arrange
    expected_activity_names = set(activity_data)

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert set(response.json()) == expected_activity_names
    assert response.json() == activity_data
    for activity in response.json().values():
        assert isinstance(activity["description"], str)
        assert isinstance(activity["schedule"], str)
        assert isinstance(activity["max_participants"], int)
        assert isinstance(activity["participants"], list)


def test_signup_registers_student_and_updates_participant_count(client, activity_data):
    # Arrange
    activity_name = "Chess Club"
    email = "new.student@mergington.edu"
    original_count = len(activity_data[activity_name]["participants"])

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    updated_activity = client.get("/activities").json()[activity_name]
    assert email in updated_activity["participants"]
    assert len(updated_activity["participants"]) == original_count + 1


def test_signup_rejects_duplicate_registration(client, activity_data):
    # Arrange
    activity_name = "Chess Club"
    email = activity_data[activity_name]["participants"][0]
    original_count = len(activity_data[activity_name]["participants"])

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }
    assert len(client.get("/activities").json()[activity_name]["participants"]) == original_count


def test_signup_for_unknown_activity_returns_not_found(client):
    # Arrange
    activity_name = "Unknown Activity"

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_removes_student_and_updates_participant_count(client, activity_data):
    # Arrange
    activity_name = "Chess Club"
    email = activity_data[activity_name]["participants"][0]
    original_count = len(activity_data[activity_name]["participants"])

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity_name}"}
    updated_activity = client.get("/activities").json()[activity_name]
    assert email not in updated_activity["participants"]
    assert len(updated_activity["participants"]) == original_count - 1


def test_unregistering_absent_participant_returns_not_found(client, activity_data):
    # Arrange
    activity_name = "Chess Club"
    email = "absent.student@mergington.edu"
    original_participants = activity_data[activity_name]["participants"].copy()

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }
    assert client.get("/activities").json()[activity_name]["participants"] == original_participants


def test_unregistering_from_unknown_activity_returns_not_found(client):
    # Arrange
    activity_name = "Unknown Activity"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
