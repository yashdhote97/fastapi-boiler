import pytest
from fastapi.testclient import TestClient
from app.models.role import RoleCreate # For payload
from app.security import get_password_hash # For user setup

# test_app_client and mock_db fixtures are provided by conftest.py

@pytest.fixture(scope="function")
def org_and_users_for_role_tests_single_db(mock_db): # Renamed fixture, depends on mock_db
    org_id_val = "role_test_org_single_db"

    # 1. Setup Organisation directly in the 'organisations' collection
    mock_db.organisations.insert_one(
        {"_id": org_id_val, "name": "Role Test Organisation SD", "settings": {}}
    )

    # 2. Setup Roles directly in the 'roles' collection (shared, but with organisation_id)
    manager_role_id_val = "role_manager_sdb_id"
    viewer_role_id_val = "role_viewer_sdb_id"
    mock_db.roles.insert_many([
        {
            "_id": manager_role_id_val, "name": "Role Manager SD",
            "permissions": ["manage_roles_in_org"], "organisation_id": org_id_val # Explicit org_id
        },
        {
            "_id": viewer_role_id_val, "name": "Role Viewer SD",
            "permissions": ["view_roles_in_org"], "organisation_id": org_id_val # Explicit org_id
        }
    ])

    # 3. Setup Users directly in the 'users' collection
    manager_user_email_val = "rolemanager_sdb@example.com"
    viewer_user_email_val = "roleviewer_sdb@example.com"
    admin_user_id_val = "manager_user_for_roles_sdb_id"
    viewer_user_id_val = "viewer_user_for_roles_sdb_id"

    mock_db.users.insert_many([
        {
            "_id": admin_user_id_val, "email": manager_user_email_val,
            "hashed_password": get_password_hash("password"),
            "organisation_id": org_id_val, "role_ids": [manager_role_id_val], "is_active": True
        },
        {
            "_id": viewer_user_id_val, "email": viewer_user_email_val,
            "hashed_password": get_password_hash("password"),
            "organisation_id": org_id_val, "role_ids": [viewer_role_id_val], "is_active": True
        }
    ])

    # Yield data needed for tests
    fixture_data = {
        "org_id": org_id_val,
        "manager_email": manager_user_email_val,
        "viewer_email": viewer_user_email_val,
    }
    yield fixture_data
    # No explicit cleanup needed thanks to function-scoped mock_db


def get_auth_token(client: TestClient, email: str, password: str, org_id: str) -> str:
    response = client.post("/users/login", json={"username": email, "password": password, "org_id": org_id})
    assert response.status_code == 200, f"Login failed for {email}: {response.text}"
    return response.json()["access_token"]


def test_role_creation_with_permission(test_app_client: TestClient, org_and_users_for_role_tests_single_db):
    setup_data = org_and_users_for_role_tests_single_db
    org_id = setup_data["org_id"]
    manager_email = setup_data["manager_email"]

    manager_token = get_auth_token(test_app_client, manager_email, "password", org_id)

    new_role_payload = {
        "name": "Developer Role SD",
        "permissions": ["write_code", "debug_code"],
        "organisation_id": org_id # Crucial: payload must specify the org_id
    }
    response = test_app_client.post(
        f"/organisations/{org_id}/roles/", # Path also has org_id
        json=new_role_payload,
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 201, response.text
    created_role = response.json()
    assert created_role["name"] == "Developer Role SD"
    assert "write_code" in created_role["permissions"]
    assert created_role["organisation_id"] == org_id


def test_role_creation_without_permission(test_app_client: TestClient, org_and_users_for_role_tests_single_db):
    setup_data = org_and_users_for_role_tests_single_db
    org_id = setup_data["org_id"]
    viewer_email = setup_data["viewer_email"]

    viewer_token = get_auth_token(test_app_client, viewer_email, "password", org_id)

    new_role_payload = {
        "name": "Forbidden Role SD",
        "permissions": ["special_ops"],
        "organisation_id": org_id
    }
    response = test_app_client.post(
        f"/organisations/{org_id}/roles/",
        json=new_role_payload,
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert response.status_code == 403, response.text
    assert "User does not have the required permission: manage_roles_in_org" in response.json()["detail"]


def test_role_creation_mismatch_org_id_path_body(test_app_client: TestClient, org_and_users_for_role_tests_single_db):
    setup_data = org_and_users_for_role_tests_single_db
    path_org_id = setup_data["org_id"] # e.g., "role_test_org_single_db"
    manager_email = setup_data["manager_email"]

    manager_token = get_auth_token(test_app_client, manager_email, "password", path_org_id)

    mismatched_org_id_in_body = "some_other_org_id"
    new_role_payload = {
        "name": "Mismatch Org Role",
        "permissions": ["test_perm"],
        "organisation_id": mismatched_org_id_in_body # Different from path_org_id
    }
    response = test_app_client.post(
        f"/organisations/{path_org_id}/roles/", # Path uses path_org_id
        json=new_role_payload,
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 400, response.text # Due to mismatch check in router
    assert "Role's organisation_id in body must match organisation_id in path" in response.json()["detail"]


def test_role_creation_in_different_org_forbidden(test_app_client: TestClient, org_and_users_for_role_tests_single_db, mock_db):
    # User from org_and_users_for_role_tests_single_db["org_id"]
    user_org_id = org_and_users_for_role_tests_single_db["org_id"]
    manager_email = org_and_users_for_role_tests_single_db["manager_email"]

    # Create a second organisation directly for this test
    other_org_id_val = "other_org_for_role_test_sdb"
    mock_db.organisations.insert_one(
        {"_id": other_org_id_val, "name": "Other Org SD", "settings": {}}
    )

    manager_token = get_auth_token(test_app_client, manager_email, "password", user_org_id)

    # Attempt to create a role, targeting other_org_id in path,
    # with role.organisation_id also being other_org_id
    new_role_payload = {
        "name": "Cross Org Role SD",
        "permissions": ["cross_permissions"],
        "organisation_id": other_org_id_val
    }
    response = test_app_client.post(
        f"/organisations/{other_org_id_val}/roles/", # Targeting other_org_id in path
        json=new_role_payload,
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    # This is caught by verify_user_org_access because current_user.organisation_id (user_org_id)
    # does not match the path parameter other_org_id_val.
    assert response.status_code == 403, response.text
    assert "You do not have access to this organisation." in response.json()["detail"]
    # No explicit cleanup for other_org_id_val needed due to function-scoped mock_db
