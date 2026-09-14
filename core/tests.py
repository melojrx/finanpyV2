import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from core.secrets import env_secret


class SecretEnvironmentTests(SimpleTestCase):
    def test_secret_file_has_priority_over_literal_value(self):
        with TemporaryDirectory() as directory:
            secret_file = Path(directory) / "secret"
            secret_file.write_text("from-file\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"SETTING": "literal", "SETTING_FILE": str(secret_file)},
                clear=True,
            ):
                self.assertEqual(env_secret("SETTING"), "from-file")

    def test_required_secret_missing_value_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                env_secret("SETTING", required=True)


class HealthEndpointTests(SimpleTestCase):
    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_liveness_does_not_require_database(self):
        response = self.client.get("/health/liveness/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"alive": True})

    @override_settings(ALLOWED_HOSTS=["testserver"])
    @patch("core.health_views.connection")
    def test_readiness_returns_200_when_database_is_available(self, connection):
        response = self.client.get("/health/readiness/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ready": True})
        connection.ensure_connection.assert_called_once_with()


class FrontendAssetTests(SimpleTestCase):
    def test_main_js_matches_classic_script_loading(self):
        base_template = (settings.BASE_DIR / "templates" / "base.html").read_text()
        main_js = (settings.BASE_DIR / "static" / "js" / "main.js").read_text()

        self.assertIn("js/main.js", base_template)
        self.assertNotIn('type="module"', base_template)
        self.assertNotIn("export {", main_js)

    def test_runtime_css_does_not_require_tailwind_build_step(self):
        generated_css = (
            settings.BASE_DIR / "theme" / "static" / "css" / "dist" / "styles.css"
        ).read_text()

        self.assertNotIn("@apply", generated_css)
