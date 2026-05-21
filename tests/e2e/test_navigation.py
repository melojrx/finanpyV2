import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestMobileNavigation:
    def test_bottom_nav_visible_on_mobile(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        nav = page.locator(".finanpy-bottom-nav")
        expect(nav).to_be_visible()

    def test_bottom_nav_hidden_on_desktop(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 1280, "height": 800})
        nav = page.locator(".finanpy-bottom-nav")
        expect(nav).to_be_hidden()

    def test_navigate_to_transactions(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        page.click('a[aria-label="Transações"]')
        page.wait_for_url("**/transactions/")
        expect(page).to_have_url(page.url)

    def test_navigate_to_budgets(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        page.click('a[aria-label="Orçamentos"]')
        page.wait_for_url("**/budgets/**")

    def test_drawer_opens_and_closes(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        page.click('[aria-label="Abrir menu"]')
        drawer = page.locator('#finanpy-drawer')
        expect(drawer).to_have_attribute("aria-hidden", "false")
        page.keyboard.press("Escape")
        expect(drawer).to_have_attribute("aria-hidden", "true")

    def test_fab_visible_on_mobile(self, authenticated_page: Page):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        fab = page.locator('[aria-label="Nova transação"]')
        expect(fab).to_be_visible()
