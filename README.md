# FastAPI Multi-Tenant RBAC Application

This project is a FastAPI application demonstrating a multi-tenant architecture with Role-Based Access Control (RBAC). Each organisation's data is isolated using `organisation_id` fields within a shared database, and the application features user authentication with JWT, and a flexible permission system tied to user roles within each organisation.

## Features

*   **Multi-Tenancy:** Supports multiple organisations, with users and roles scoped to their respective organisations. Data is logically separated within a single database using `organisation_id`.
*   **Role-Based Access Control (RBAC):**
    *   Define custom roles within each organisation.
    *   Assign fine-grained permissions to roles (e.g., "manage_users_in_org", "view_roles_in_org").
    *   Users inherit permissions based on their assigned roles.
    *   API endpoints are protected based on required permissions.
*   **User Management:**
    *   User registration within an organisation.
    *   Secure password hashing (bcrypt).
    *   JWT-based authentication (access tokens).
*   **Organisation Management:** Basic CRUD for organisations.
*   **Role Management:** CRUD for roles within specific organisations.
*   **Async Support:** Built with FastAPI and Motor for asynchronous database operations.
*   **Pydantic Validation:** Data validation for request and response models.
*   **Dependency Injection:** FastAPI's dependency injection system used for managing database sessions, authentication, and permissions.
*   **Testing:** Includes unit and integration tests using `pytest` and `mongomock`.

## Tech Stack

*   **FastAPI:** Modern, fast (high-performance) web framework for building APIs with Python.
*   **Pydantic:** Data validation and settings management using Python type annotations.
*   **Motor:** Asynchronous Python driver for MongoDB.
*   **MongoDB:** NoSQL document database.
*   **Passlib & Bcrypt:** For password hashing.
*   **python-jose:** For JWT creation and verification.
*   **Poetry:** For dependency management and packaging.
*   **Uvicorn:** ASGI server for running the FastAPI application.
*   **Pytest:** For running automated tests.
*   **Mongomock:** For mocking MongoDB in tests.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python:** Version 3.8 or higher.
*   **Poetry:** For dependency management. (See [Poetry Installation](https://python-poetry.org/docs/#installation))
*   **MongoDB:** A running MongoDB instance (version 4.0 or higher recommended).

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

3.  **Set up environment variables:**
    Create a new `.env` file in the project root and populate it with necessary environment variables. See the 'Environment Variables' section below for details and examples.

4.  **Ensure MongoDB is running:**
    Make sure your MongoDB instance is accessible and configured according to your `.env` settings.

## Environment Variables

Create a `.env` file in the project root and configure the following variables:

*   `MONGODB_URL`: The connection URL for your MongoDB instance (e.g., `mongodb://localhost:27017`).
*   `DATABASE_NAME`: The name of the database to be used by the application (e.g., `app_main_db`).
*   `SECRET_KEY`: A secret key for JWT token encoding/decoding. Generate a strong random key for production.
*   `ALGORITHM`: The algorithm used for JWT encoding (e.g., `HS256`).
*   `ACCESS_TOKEN_EXPIRE_MINUTES`: The expiration time for access tokens in minutes (e.g., `30`).

**Example `.env` file:**
```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=app_main_db
SECRET_KEY=your_very_secret_random_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Running the Application

Once the setup is complete and environment variables are configured, you can run the application using Uvicorn:

```bash
poetry run uvicorn app.main:app --reload
```

The application will typically be available at `http://127.0.0.1:8000`. The `--reload` flag enables auto-reloading when code changes, which is useful for development.

## API Endpoints Overview

The application provides the following main groups of endpoints:

*   **Organisations (`/organisations`):**
    *   `POST /`: Create a new organisation.
    *   `GET /`: List all organisations (requires specific permissions).
    *   `GET /{org_id}`: Get details of a specific organisation.
    *   `PUT /{org_id}`: Update an organisation.
    *   `DELETE /{org_id}`: Delete an organisation.

*   **Users (`/users`):**
    *   `POST /`: Register a new user within a specific organisation (payload must include `organisation_id`). Requires "manage_users_in_org" permission by an admin of that organisation.
    *   `POST /login`: Log in a user for a specific organisation (payload includes `username`, `password`, `org_id`). Returns a JWT access token.
    *   `GET /me/`: Get the details of the currently authenticated user.
    *   `GET /{user_id}`: Get details of a specific user within the authenticated user's organisation (requires "view_users_in_org" permission).
    *   `PUT /{user_id}`: Update a user within the authenticated user's organisation (requires "manage_users_in_org" permission).

*   **Roles (`/organisations/{org_id}/roles`):**
    *   `POST /`: Create a new role within the specified organisation (`org_id` from path must match `organisation_id` in payload). Requires "manage_roles_in_org" permission.
    *   `GET /`: List all roles within the specified organisation. Requires "view_roles_in_org" permission.
    *   `GET /{role_id}`: Get details of a specific role within the organisation. Requires "view_roles_in_org" permission.
    *   `PUT /{role_id}`: Update a role within the organisation. Requires "manage_roles_in_org" permission.
    *   `DELETE /{role_id}`: Delete a role within the organisation. Requires "manage_roles_in_org" permission.

Interactive API documentation (Swagger UI) is available at `/docs` and ReDoc at `/redoc` when the application is running.

## Running Tests

The project uses `pytest` for running tests and `mongomock` to mock MongoDB interactions, allowing tests to run without a live database instance.

To run the tests:

```bash
poetry run pytest
```

Ensure you have installed development dependencies if you haven't already (`poetry install` should cover this).
