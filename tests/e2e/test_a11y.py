import pytest
from playwright.sync_api import Page
from axe_playwright_python.sync_playwright import Axe


@pytest.mark.a11y
class TestAccessibility:
    """Run axe-core on key pages. Target: 0 critical/serious violations."""

    PAGES = [
        "/dashboard/",
        "/transactions/",
        "/transactions/create/",
        "/budgets/plano/",
        "/accounts/",
        "/goals/",
    ]

    @pytest.mark.parametrize("path", PAGES)
    def test_page_accessibility(self, authenticated_page: Page, path: str, base_url: str):
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(f"{base_url}{path}")
        page.wait_for_load_state("load")

        axe = Axe()
        results = axe.run(page)

        violations = [
            v
            for v in results.response.get("violations", [])
            if v["impact"] in ("critical", "serious")
        ]

        if violations:
            messages = []
            for v in violations:
                nodes = ", ".join(n["target"][0] for n in v["nodes"][:3])
                messages.append(f"[{v['impact']}] {v['id']}: {v['description']} ({nodes})")
            pytest.fail(
                f"{len(violations)} critical/serious a11y violations on {path}:\n"
                + "\n".join(messages)
            )

    def test_dashboard_no_violations_desktop(self, authenticated_page: Page, base_url: str):
        page = authenticated_page
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(f"{base_url}/dashboard/")
        page.wait_for_load_state("load")

        axe = Axe()
        results = axe.run(page)

        critical = [
            v for v in results.response.get("violations", []) if v["impact"] == "critical"
        ]
        assert len(critical) == 0, f"Critical violations: {critical}"
