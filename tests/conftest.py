"""Root conftest — shared fixtures for unit and integration tests."""
import asyncio
import pytest
import pytest_asyncio
from decimal import Decimal
from uuid import uuid4


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_company_id():
    return uuid4()


@pytest.fixture
def sample_user_id():
    return uuid4()


@pytest.fixture
def sample_warehouse_id():
    return uuid4()


@pytest.fixture
def sample_product_id():
    return uuid4()
