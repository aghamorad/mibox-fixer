"""The failure messages a user actually sees when an install is refused."""

import unittest
from pathlib import Path

from fixer import catalog
from fixer.adb import PLAY_PROTECT_HINT, Adb, explain_install_failure


class FakeAdb(Adb):
    """An Adb that records the shell commands instead of running them."""

    def __init__(self, verifier_before: str, install_result=(True, "Success")):
        self.binary = "adb"
        self.serial = "test:5555"
        self.commands: list[str] = []
        self._verifier_before = verifier_before
        self._install_result = install_result

    def shell(self, command: str, *, timeout: int = 60, check: bool = False) -> str:
        self.commands.append(command)
        if command.startswith("settings get global"):
            return self._verifier_before
        return ""

    def install(self, apk, *, reinstall=True, downgrade=True):
        self.commands.append(f"install {apk}")
        return self._install_result


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


class VerifierWorkaround(unittest.TestCase):
    APK = Path("/tmp/tvbro.apk")

    def test_verifier_is_turned_off_for_the_install_and_back_on_after(self):
        adb = FakeAdb(verifier_before="1")
        ok, _ = adb.install_past_play_protect(self.APK)
        self.assertTrue(ok)
        self.assertEqual(
            adb.commands,
            [
                "settings get global package_verifier_enable",
                "settings put global package_verifier_enable 0",
                f"install {self.APK}",
                "settings put global package_verifier_enable 1",
            ],
        )

    def test_a_failed_install_still_restores_the_verifier(self):
        adb = FakeAdb(verifier_before="1", install_result=(False, "blocked"))
        ok, message = adb.install_past_play_protect(self.APK)
        self.assertFalse(ok)
        self.assertEqual(message, "blocked")
        self.assertEqual(adb.commands[-1], "settings put global package_verifier_enable 1")

    def test_an_unset_verifier_defaults_back_to_enabled(self):
        adb = FakeAdb(verifier_before="null")
        adb.install_past_play_protect(self.APK)
        self.assertEqual(adb.commands[-1], "settings put global package_verifier_enable 1")

    def test_a_verifier_that_was_already_off_stays_off(self):
        adb = FakeAdb(verifier_before="0")
        adb.install_past_play_protect(self.APK)
        self.assertEqual(adb.commands[-1], "settings put global package_verifier_enable 0")


if __name__ == "__main__":
    unittest.main()
