"""The failure messages a user actually sees when an install is refused."""

import unittest

from fixer import catalog
from fixer.adb import PLAY_PROTECT_HINT, explain_install_failure


class InstallFailureMessages(unittest.TestCase):
    def test_play_protect_failure_gets_a_way_forward(self):
        raw = (
            "Performing Streamed Install\n"
            "adb: failed to install tvbro-3.0.5.apk: Failure "
            "[INSTALL_FAILED_VERIFICATION_FAILURE]"
        )
        message = explain_install_failure(raw)
        self.assertEqual(message, PLAY_PROTECT_HINT)
        # The hint has to name the cause and at least one way past it.
        self.assertIn("Play Protect", message)
        self.assertIn("package_verifier_enable", message)

    def test_signing_mismatch_is_explained(self):
        message = explain_install_failure("Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]")
        self.assertIn("signing key", message)

    def test_downgrade_is_explained(self):
        message = explain_install_failure("Failure [INSTALL_FAILED_VERSION_DOWNGRADE]")
        self.assertIn("newer version", message)

    def test_storage_is_explained(self):
        message = explain_install_failure(
            "Failure [INSTALL_FAILED_INSUFFICIENT_STORAGE]"
        )
        self.assertIn("free space", message)

    def test_unknown_failures_are_passed_through_untouched(self):
        raw = "Failure [INSTALL_FAILED_SOMETHING_NEW]"
        self.assertEqual(explain_install_failure(raw), raw)


class SelfUpdatingApps(unittest.TestCase):
    def test_only_apps_that_ship_an_updater_are_flagged(self):
        flagged = {a.key for a in catalog.APPS if a.self_updates}
        self.assertEqual(flagged, {"beam"})

    def test_flagged_apps_have_a_package_to_grant(self):
        for app in catalog.APPS:
            if app.self_updates:
                with self.subTest(app=app.key):
                    self.assertTrue(app.package)


if __name__ == "__main__":
    unittest.main()
