import subprocess
import sys
import time

import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def base_url():
    return "http://localhost:8001"


@pytest.fixture(scope="session", autouse=True)
def django_server(base_url):
    """Start Django dev server for E2E tests."""
    proc = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "8001", "--noreload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def test_user(django_server):
    """Create test user via manage.py shell."""
    subprocess.run(
        [
            sys.executable,
            "manage.py",
            "shell",
            "-c",
            (
                "from django.contrib.auth import get_user_model; "
                "from accounts.models import Account; "
                "from categories.models import Category; "
                "User = get_user_model(); "
                "user, created = User.objects.get_or_create(email='test@finanpy.dev'); "
                "user.set_password('TestPass123!'); "
                "user.save(); "
                "Account.objects.get_or_create(user=user, name='Conta E2E', defaults={'account_type':'checking','balance':'1000.00','currency':'BRL'}); "
                "Category.objects.get_or_create(user=user, name='Supermercado E2E', category_type='EXPENSE', defaults={'color':'#EF4444','icon':'🍔'}); "
                "Category.objects.get_or_create(user=user, name='Salário E2E', category_type='INCOME', defaults={'color':'#10B981','icon':'💰'});"
            ),
        ],
        check=True,
    )
    return {"email": "test@finanpy.dev", "password": "TestPass123!"}


@pytest.fixture()
def authenticated_page(page: Page, base_url: str, test_user: dict):
    """Page already logged in."""
    page.goto(f"{base_url}/login/")
    page.fill('input[name="username"], input[name="email"]', test_user["email"])
    page.fill('input[name="password"]', test_user["password"])
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/dashboard/")
    return page


@pytest.fixture()
def mobile_page(page: Page):
    """Page with mobile viewport."""
    page.set_viewport_size({"width": 375, "height": 812})
    return page
