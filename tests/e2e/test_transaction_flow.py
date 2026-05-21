import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestTransactionFlow:
    def test_create_expense_via_form(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})

        page.goto(page.url.replace("/dashboard/", "/transactions/create/"))
        page.wait_for_load_state("load")

        page.fill('input[name="description"]', "Teste E2E - Supermercado")
        page.fill('input[name="amount"]', "150,00")

        type_select = page.locator('select[name="transaction_type"]')
        if type_select.is_visible():
            type_select.select_option("EXPENSE")

        account_select = page.locator('select[name="account"]')
        if account_select.is_visible():
            account_select.select_option(index=1)

        page.click('#category-trigger')
        page.locator('.category-item').first.click()

        page.locator('#transaction-form button[type="submit"]').click()
        page.wait_for_url("**/transactions/**")

    def test_fab_opens_transaction_form(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})

        fab = page.locator('[aria-label="Nova transação"]')
        fab.click()

        page.wait_for_url("**/transactions/create/")
        expect(page.locator('#transaction-form')).to_be_visible()
