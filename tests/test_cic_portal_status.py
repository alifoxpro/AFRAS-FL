"""Offline synthetic tests for form status: no external web access needed."""
import importlib.util
import unittest
from pathlib import Path
from urllib.error import URLError

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/data/check_cic_portals.py"
spec = importlib.util.spec_from_file_location("cic_form_checker", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CICPortalStatusTests(unittest.TestCase):
    def test_explicit_form_error_not_misrepresented_as_access(self):
        obj = mod.check("ciciot2023", fetch=lambda url: (
            "<h1>CIC DATASET DOWNLOAD FORM</h1>"
            "Server error. Please try again later. First Name Last Name"))
        self.assertEqual(obj["form_status"], "OFFICIAL_FORM_SERVER_ERROR")
        self.assertFalse(obj["data_downloaded"])
        self.assertFalse(obj["training_ready"])
        self.assertTrue(obj["manual_registration_required"])

    def test_visible_form_is_not_dataset_download(self):
        obj = mod.check("diad2024", fetch=lambda url: (
            "<form><label>First Name</label><label>Last Name</label>"
            "<label>Organization</label></form>"))
        self.assertEqual(obj["form_status"],
                         "REGISTRATION_FORM_VISIBLE_UNVERIFIED")
        self.assertFalse(obj["data_downloaded"])

    def test_unavailable_cannot_claim_verified(self):
        def broken(url):
            raise URLError("port unreachable")
        obj = mod.check("diad2024", fetch=broken)
        self.assertEqual(obj["form_status"], "FORM_CHECK_UNAVAILABLE")
        self.assertEqual(obj["error_type"], "URLError")
        self.assertFalse(obj["training_ready"])

    def test_captcha_requires_manual_work(self):
        obj = mod.check("ciciot2023", fetch=lambda url: (
            "reCAPTCHA challenge"))
        self.assertEqual(obj["form_status"],
                         "FORM_REQUIRES_USER_INTERACTION")

    def test_unrecognized_page_never_claims_success(self):
        obj = mod.check("ciciot2023", fetch=lambda url: (
            "<html>unrecognized maintenance</html>"))
        self.assertEqual(obj["form_status"], "UNRECOGNIZED_FORM_RESPONSE")
        self.assertFalse(obj["data_downloaded"])

    def test_unknown_dataset_refused(self):
        with self.assertRaises(ValueError):
            mod.check("other", fetch=lambda url: "")


if __name__ == "__main__":
    unittest.main()
