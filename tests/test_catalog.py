"""Tests that do not need a device or the network."""

import unittest

from fixer import catalog
from fixer.downloader import pick_asset, resolve_url, human_size


class CatalogIntegrity(unittest.TestCase):
    def test_no_duplicate_packages(self):
        pkgs = [b.package for b in catalog.BLOAT]
        self.assertEqual(len(pkgs), len(set(pkgs)), "duplicate package in BLOAT")

    def test_no_duplicate_app_keys(self):
        keys = [a.key for a in catalog.APPS]
        self.assertEqual(len(keys), len(set(keys)), "duplicate app key")

    def test_every_category_is_declared(self):
        for item in catalog.BLOAT:
            self.assertIn(item.category, catalog.CATEGORY_ORDER)

    def test_every_category_has_items(self):
        used = {b.category for b in catalog.BLOAT}
        self.assertEqual(used, set(catalog.CATEGORY_ORDER))

    def test_lookup_tables_agree(self):
        self.assertEqual(len(catalog.BLOAT_BY_PACKAGE), len(catalog.BLOAT))
        self.assertEqual(len(catalog.APPS_BY_KEY), len(catalog.APPS))

    def test_risky_items_are_not_default(self):
        """Anything flagged dangerous must be opt-in only."""
        for item in catalog.BLOAT:
            if item.danger:
                self.assertFalse(
                    item.default, f"{item.package} is risky but enabled by default"
                )

    def test_apps_have_a_download_source(self):
        for app in catalog.APPS:
            with self.subTest(app=app.key):
                self.assertTrue(
                    app.asset or app.arch_assets or app.url,
                    f"{app.key} has nothing to download",
                )

    def test_apps_have_a_package_and_component(self):
        for app in catalog.APPS:
            with self.subTest(app=app.key):
                self.assertTrue(app.package.count(".") >= 1)
                if app.component:
                    # component must reference its own package
                    self.assertTrue(app.component.startswith(app.package + "/"))

    def test_playlists_are_https(self):
        for name, url in catalog.IPTV_PLAYLISTS.items():
            with self.subTest(playlist=name):
                self.assertTrue(url.startswith("https://"))


class AssetSelection(unittest.TestCase):
    def test_32bit_device_gets_armv7(self):
        app = catalog.APPS_BY_KEY["smarttube"]
        self.assertIn("armeabi-v7a", pick_asset(app, ["armeabi-v7a", "armeabi"]))

    def test_64bit_device_gets_arm64(self):
        app = catalog.APPS_BY_KEY["smarttube"]
        self.assertIn("arm64", pick_asset(app, ["arm64-v8a", "armeabi-v7a"]))

    def test_single_asset_apps_always_resolve(self):
        for key in ("beam", "airplay", "fossify", "materialfiles"):
            app = catalog.APPS_BY_KEY[key]
            self.assertIsNotNone(pick_asset(app, ["armeabi-v7a"]))

    def test_lantern_armv7_is_not_the_arm64_build(self):
        app = catalog.APPS_BY_KEY["lantern"]
        chosen = pick_asset(app, ["armeabi-v7a", "armeabi"])
        self.assertIn("armv7", chosen)

    def test_url_uses_the_release_tag(self):
        app = catalog.APPS_BY_KEY["beam"]
        url, name = resolve_url(app, ["armeabi-v7a"])
        self.assertIn(app.version, url)
        self.assertTrue(url.startswith("https://github.com/"))

    def test_human_size(self):
        self.assertEqual(human_size(512), "512 B")
        self.assertEqual(human_size(2048), "2.0 KB")
        self.assertEqual(human_size(25 * 1024 * 1024), "25.0 MB")


if __name__ == "__main__":
    unittest.main()
