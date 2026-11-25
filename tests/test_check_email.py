"""Offline tests for scripts/check_email.py against the .eml fixtures."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "support-email-triage-and-reply" / "scripts" / "check_email.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def check(name, via_stdin=False):
    path = FIXTURES / f"{name}.eml"
    if via_stdin:
        out = subprocess.run([sys.executable, "-I", str(SCRIPT), "-"], input=path.read_bytes(),
                             capture_output=True, check=True).stdout
    else:
        out = subprocess.run([sys.executable, "-I", str(SCRIPT), str(path)],
                             capture_output=True, check=True).stdout
    return json.loads(out)


def signals(result):
    return {s["signal"] for s in result["security"]["signals"]}


class Verdicts(unittest.TestCase):
    def test_fake_billing_is_likely_malicious(self):
        r = check("phishing")
        self.assertEqual(r["security"]["verdict"], "likely malicious")
        self.assertEqual(r["security"]["score"], 100)
        self.assertTrue({"SPF fail", "DMARC fail", "Risky attachment",
                         "Link text shows one domain but opens another",
                         "Reply-To domain differs from From domain"} <= signals(r))
        self.assertFalse(r["automated"])

    def test_character_swap_brand_is_likely_malicious(self):
        r = check("paypal-fake")
        self.assertEqual(r["security"]["verdict"], "likely malicious")
        self.assertIn("Lookalike or suspicious domain", signals(r))

    def test_hidden_ai_instructions_are_never_clean(self):
        r = check("injection")
        self.assertEqual(r["security"]["verdict"], "suspicious")
        self.assertIn("Text aimed at an AI assistant", signals(r))

    def test_real_brand_mail_is_clean(self):
        r = check("paypal-legit")
        self.assertEqual(r["security"]["score"], 0)
        self.assertEqual(r["security"]["verdict"], "clean")

    def test_hyphenated_domain_alone_is_not_flagged(self):
        r = check("hyphen-legit")
        self.assertEqual(r["security"]["score"], 0)

    def test_customer_email_is_clean_and_not_automated(self):
        r = check("customer")
        self.assertEqual(r["security"]["score"], 0)
        self.assertFalse(r["automated"])
        self.assertEqual(r["message_id"], "<a1@example.org>")


class AutomatedMail(unittest.TestCase):
    def test_out_of_office_is_automated(self):
        r = check("ooo")
        self.assertTrue(r["automated"])
        self.assertTrue(any("Auto-Submitted" in s for s in r["automated_signals"]))

    def test_newsletter_is_automated(self):
        r = check("newsletter")
        self.assertTrue(r["automated"])
        self.assertTrue(any("List-Unsubscribe" in s for s in r["automated_signals"]))


class Input(unittest.TestCase):
    def test_stdin_matches_file(self):
        self.assertEqual(check("phishing", via_stdin=True), check("phishing"))


if __name__ == "__main__":
    unittest.main()
