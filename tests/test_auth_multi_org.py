import pytest
from fastapi.testclient import TestClient
from jose import jwt # For decoding tokens
from app.config import settings # For token decoding algorithm/key
# Models are not directly used for client.post json payloads but good for reference
# from app.models.organisation import OrganisationCreate
# from app.models.user import UserCreate
# from app.models.role import RoleCreate

# test_app_client and mock_db fixtures are provided by conftest.py

def test_user_login_and_me_endpoint(test_app_client: TestClient, mock_db):
    # Direct DB setup using the mock_db fixture (which is function-scoped)
    org_id_val = "testorg1"
    user_email = "user1@testorg1.com"
    user_password = "testpassword"

    # Create organisation directly in the 'organisations' collection of the mocked DB
    mock_db.organisations.insert_one(
        {"_id": org_id_val, "name": "Test Org 1", "description": "Org for login test", "settings": {}}
    )

    from app.security import get_password_hash # For hashing password
    hashed_password = get_password_hash(user_password)

    # Create user directly in the 'users' collection of the mocked DB
    user_id_val = "user1_in_org1"
    mock_db.users.insert_one({
        "_id": user_id_val,
        "email": user_email,
        "hashed_password": hashed_password,
        "full_name": "Test User One",
        "organisation_id": org_id_val, # Explicitly set organisation_id
        "role_ids": [],
        "is_active": True
    })

    # Test Login
    login_data = {
        "username": user_email,
        "password": user_password,
        "org_id": org_id_val
    }
    response = test_app_client.post("/users/login", json=login_data)
    assert response.status_code == 200, response.text
    token_info = response.json()
    assert "access_token" in token_info
    access_token = token_info["access_token"]

    # Decode token and verify
    decoded_token = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded_token["sub"] == user_email
    assert decoded_token["org_id"] == org_id_val

    # Test login with incorrect org_id
    login_data_wrong_org = {**login_data, "org_id": "wrongorg"}
    # First, ensure "wrongorg" does not exist or login will fail differently.
    # If it did exist, it would be a valid login for that user if they were in "wrongorg".
    # Here, crud_organisation.get_organisation_by_id will return None for "wrongorg".
    response_wrong_org = test_app_client.post("/users/login", json=login_data_wrong_org)
    assert response_wrong_org.status_code == 401, response_wrong_org.text # From router if org not found

    # Test login with incorrect password
    login_data_wrong_pass = {**login_data, "password": "wrongpassword"}
    response_wrong_pass = test_app_client.post("/users/login", json=login_data_wrong_pass)
    assert response_wrong_pass.status_code == 401, response_wrong_pass.text

    # Test /users/me access
    me_response = test_app_client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_response.status_code == 200, me_response.text
    user_me_data = me_response.json()
    assert user_me_data["email"] == user_email
    assert user_me_data["organisation_id"] == org_id_val
    assert user_me_data["id"] == user_id_val
    # No explicit cleanup needed due to function-scoped mock_db

def test_user_registration_requires_permission(test_app_client: TestClient, mock_db):
    admin_org_id = "admin_org_for_reg"
    admin_email = "admin@org_reg.com"
    admin_password = "password"

    viewer_email = "viewer@org_reg.com" # User without manage_users_in_org permission
    viewer_password = "password"

    # 1. Setup Organisation directly
    mock_db.organisations.insert_one(
        {"_id": admin_org_id, "name": "Org For Registration Test", "settings": {}}
    )

    # 2. Setup Roles directly in the 'roles' collection (shared, but with organisation_id)
    manager_role_id_val = "manager_role_for_reg"
    viewer_role_id_val = "viewer_role_for_reg"
    mock_db.roles.insert_many([
        {
            "_id": manager_role_id_val, "name": "User Manager",
            "permissions": ["manage_users_in_org"], "organisation_id": admin_org_id
        },
        {
            "_id": viewer_role_id_val, "name": "User Viewer",
            "permissions": ["view_users_in_org"], "organisation_id": admin_org_id
        }
    ])

    # 3. Setup Users directly in the 'users' collection
    from app.security import get_password_hash
    admin_user_id_val = "admin_user_for_reg_id"
    viewer_user_id_val = "viewer_user_for_reg_id"
    mock_db.users.insert_many([
        {
            "_id": admin_user_id_val, "email": admin_email,
            "hashed_password": get_password_hash(admin_password),
            "organisation_id": admin_org_id, "role_ids": [manager_role_id_val], "is_active": True
        },
        {
            "_id": viewer_user_id_val, "email": viewer_email,
            "hashed_password": get_password_hash(viewer_password),
            "organisation_id": admin_org_id, "role_ids": [viewer_role_id_val], "is_active": True
        }
    ])

    # 4. Login admin user to get token
    admin_login_resp = test_app_client.post("/users/login", json={"username": admin_email, "password": admin_password, "org_id": admin_org_id})
    assert admin_login_resp.status_code == 200, admin_login_resp.text
    admin_token = admin_login_resp.json()["access_token"]

    # 5. Admin attempts to create a new user in their own organisation (should succeed)
    new_user_payload = {
        "email": "newly_created@org_reg.com", "password": "new_password",
        "organisation_id": admin_org_id, # Must match admin's org
        "full_name": "Newby User", "role_ids": []
    }
    create_resp_admin = test_app_client.post("/users/", json=new_user_payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert create_resp_admin.status_code == 201, create_resp_admin.text
    created_user_data = create_resp_admin.json()
    assert created_user_data["email"] == "newly_created@org_reg.com"
    assert created_user_data["organisation_id"] == admin_org_id

    # 6. Login viewer user to get token
    viewer_login_resp = test_app_client.post("/users/login", json={"username": viewer_email, "password": viewer_password, "org_id": admin_org_id})
    assert viewer_login_resp.status_code == 200, viewer_login_resp.text
    viewer_token = viewer_login_resp.json()["access_token"]

    # 7. Viewer attempts to create a new user (should fail with 403)
    another_user_payload = {
        "email": "another_new@org_reg.com", "password": "new_password2",
        "organisation_id": admin_org_id, # Targetting same org
        "full_name": "Another Newby"
    }
    create_resp_viewer = test_app_client.post("/users/", json=another_user_payload, headers={"Authorization": f"Bearer {viewer_token}"})
    assert create_resp_viewer.status_code == 403, create_resp_viewer.text
    assert "User does not have the required permission: manage_users_in_org" in create_resp_viewer.json()["detail"]
    # No explicit cleanup needed due to function-scoped mock_db
