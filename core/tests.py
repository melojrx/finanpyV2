from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class FrontendAssetTests(SimpleTestCase):
    def test_main_js_matches_classic_script_loading(self):
        base_template = (settings.BASE_DIR / "templates" / "base.html").read_text()
        main_js = (settings.BASE_DIR / "static" / "js" / "main.js").read_text()

        self.assertIn("js/main.js", base_template)
        self.assertNotIn('type="module"', base_template)
        self.assertNotIn("export {", main_js)

    def test_runtime_css_does_not_require_tailwind_build_step(self):
        custom_css = (settings.BASE_DIR / "static" / "css" / "custom.css").read_text()

        self.assertNotIn("@apply", custom_css)
