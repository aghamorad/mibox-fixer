import unittest

from build_world_playlist import CURATED, FAVORITES, build
from setup_mibox import PLAYLIST, configure_source


class WorldSetupTests(unittest.TestCase):
    def test_world_playlist_keeps_all_upstream_entries(self):
        source = "#EXTM3U x-tvg-url=\"example\"\n" + "#EXTINF:-1,Channel\nhttps://example.org/live\n" * 1000
        result = build(source)
        self.assertEqual(result.count("#EXTINF"), 1000 + len(CURATED))
        self.assertIn('group-title="Top Picks"', result)
        self.assertIn('group-title="World News"', result)
        self.assertIn("CNN International", result)
        self.assertLess(result.index("Dry Bar Comedy"), result.index(",Channel"))

    def test_rejects_incomplete_upstream(self):
        with self.assertRaises(ValueError):
            build("#EXTM3U\n")

    def test_preserves_existing_sources_and_is_idempotent(self):
        config = {"iptvSourceList": {"value": [{"name": "Existing", "url": "https://example.org"}]}}
        self.assertEqual(configure_source(config), 1)
        self.assertEqual(configure_source(config), 1)
        self.assertEqual(len(config["iptvSourceList"]["value"]), 2)
        self.assertEqual(config["iptvSourceList"]["value"][1]["url"], PLAYLIST)


if __name__ == "__main__":
    unittest.main()
