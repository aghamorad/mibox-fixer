"""Tests for MoBox 2.0 auto-discovery, firmware inspection, updater, and GUI import."""

import unittest

from fixer import __version__, catalog
from fixer.discover import DiscoveredBox, FirmwareReport
from fixer.tasks import Fixer
from fixer.updater import UpdateStatus, get_local_commit


class MoBoxTests(unittest.TestCase):
    def test_version_is_2x(self):
        self.assertTrue(__version__.startswith("2."))

    def test_simple_apps_exist_in_catalog(self):
        for key in Fixer.MOBOX_SIMPLE_APPS:
            self.assertIn(key, catalog.APPS_BY_KEY, f"missing simple app {key}")

    def test_firmware_report_health_flags(self):
        fw = FirmwareReport(
            model="MIBOX4",
            android_release="9",
            sdk="28",
            build_id="PI.3933",
            abis=["armeabi-v7a", "armeabi"],
            free_storage_mb=780,
            hdmi_cec_enabled=True,
            hdmi_auto_device_off=False,
            sleep_timeout_ms=-1,
            hid_drivers=["apple", "hid-generic"],
            matvt_active=True,
        )
        self.assertTrue(fw.tv_wake_ready)
        self.assertFalse(fw.has_magicmouse_driver)
        self.assertEqual(fw.arch_label, "32-bit (armeabi-v7a)")
        summary = fw.plain_summary()
        self.assertIn("MIBOX4", summary)
        self.assertIn("Ready", summary)
        self.assertIn("Active", summary)

    def test_firmware_report_detects_sleep_bug(self):
        fw = FirmwareReport(
            hdmi_cec_enabled=True,
            hdmi_auto_device_off=True,
            sleep_timeout_ms=10800000,
        )
        self.assertFalse(fw.tv_wake_ready)

    def test_discovered_box_serial(self):
        box = DiscoveredBox(ip="192.168.0.117", has_adb=True, has_remote_v2=True)
        self.assertEqual(box.serial, "192.168.0.117:5555")

    def test_updater_local_commit(self):
        sha = get_local_commit()
        self.assertTrue(len(sha) >= 7)
        st = UpdateStatus(
            local_commit=sha,
            remote_commit=sha,
            remote_message="test",
            update_available=False,
        )
        self.assertEqual(st.short_local, sha[:7])
        self.assertFalse(st.update_available)

    def test_gui_imports_cleanly(self):
        from fixer import gui

        self.assertTrue(hasattr(gui, "MoBoxApp"))
        self.assertIs(gui.FixerApp, gui.MoBoxApp)
        self.assertIn("MoBox", gui.APP_TITLE)

    def test_web_app_and_icon_assets_exist(self):
        from pathlib import Path
        from fixer import web

        root = Path(web.__file__).resolve().parent.parent
        self.assertTrue((root / "web" / "index.html").is_file())
        self.assertTrue((root / "docs" / "index.html").is_file())
        self.assertTrue((root / "docs" / "downloads" / "MoBox.apk").is_file())
        self.assertTrue((root / "docs" / "downloads" / "ZLT-X28.apk").is_file())
        self.assertTrue((root / "AndroidApp" / "build_apk.sh").is_file())
        self.assertTrue((root / "MoBoxApp" / "make_icon.py").is_file())
        self.assertIn("UP", web.REMOTE_KEYCODES)
        self.assertEqual(web.REMOTE_KEYCODES["OK"], 23)


if __name__ == "__main__":
    unittest.main()
