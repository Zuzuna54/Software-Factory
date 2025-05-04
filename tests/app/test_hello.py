# tests/app/test_hello.py
import pytest
from fastapi.testclient import TestClient

# Import the app from the main application file
# Adjust the import path based on your project structure
from app.main import app

# Create a TestClient instance
# Note: It's often better to use fixtures (e.g., in conftest.py) for this
client = TestClient(app)


def test_say_hello():
    """Test the /api/v1/hello endpoint."""
    response = client.get("/api/v1/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from the Autonomous AI Team!"}


def test_health_check():
    """Test the /healthz endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
