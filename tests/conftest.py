import pytest
from fastapi.testclient import TestClient
from mongomock import MongoClient as MongoMockClient # Synchronous client for basic mocking
from mongomock.patches import AIOAsyncMotorClientMock # For async motor
from app.main import app # Your FastAPI app
from app.config import settings # To get DATABASE_NAME

# It's important that these patches apply before the app.db.database module is fully imported
# by other modules, especially the 'client' and 'database' global variables.
# Pytest fixtures and autouse=True can help manage this.

@pytest.fixture(scope="function") # Changed to function scope for better test isolation
def mock_db(monkeypatch):
    """
    Fixture to mock the MongoDB client and database object for a single test function.
    Uses AIOAsyncMotorClientMock from mongomock for the client
    and a specific database from that client.
    Clears the database after each test.
    """
    try:
        from mongomock.patches import AIOAsyncMotorClientMock
    except ImportError:
        pytest.fail("mongomock is not installed. Please install with `pip install mongomock`.")

    # Create a new mock client for each test function
    mock_client_instance = AIOAsyncMotorClientMock()

    # Get the database name from settings
    db_name = settings.DATABASE_NAME
    mock_database_instance = mock_client_instance[db_name]

    # Monkeypatch the client and database objects in app.db.database
    # This assumes app.db.database defines global 'client' and 'database' variables.
    monkeypatch.setattr("app.db.database.client", mock_client_instance)
    monkeypatch.setattr("app.db.database.database", mock_database_instance)

    # print(f"MongoDB client and database '{db_name}' mocked for test function.") # For debugging

    yield mock_database_instance # Provide the mock database object to the test

    # Teardown: Drop the database to ensure clean state for the next test
    # AIOAsyncMotorClientMock doesn't have drop_database on the client itself for a specific DB directly
    # We need to clear collections or use a new client instance.
    # Since we create a new AIOAsyncMotorClientMock instance per function,
    # the "dropping" is implicit in that the next test gets a fresh mock client.
    # If we want to be explicit or if the client was session-scoped, we'd do:
    # for collection_name in await mock_database_instance.list_collection_names():
    #    await mock_database_instance[collection_name].delete_many({})
    # print(f"Mock database '{db_name}' implicitly cleared after test function.") # For debugging


@pytest.fixture(scope="function")
def test_app_client(mock_db): # Depends on mock_db to ensure patching is done
    """
    Provides a TestClient instance for making requests to the FastAPI app.
    This client uses the mocked MongoDB setup by the mock_db fixture.
    Scope is function to align with mock_db's function scope for isolation.
    """
    client = TestClient(app)
    return client
