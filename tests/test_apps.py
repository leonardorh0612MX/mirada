"""APPS page launching: pure resolution, OS only in open_app."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.apps import resolve_launch


class TestResolveLaunch(unittest.TestCase):
    def test_url_passthrough(self):
        self.assertEqual(resolve_launch("https://www.youtube.com"),
                         ("url", "https://www.youtube.com"))

    def test_discord_native_when_installed(self):
        kind, payload = resolve_launch(
            "discord", exists=lambda p: True, local_app_data="C:\\LAD")
        self.assertEqual(kind, "exe")
        self.assertIn("Update.exe", payload[0])
        self.assertEqual(payload[1:], ["--processStart", "Discord.exe"])

    def test_discord_web_fallback(self):
        self.assertEqual(
            resolve_launch("discord", exists=lambda p: False,
                           local_app_data="C:\\LAD"),
            ("url", "https://discord.com/app"))

    def test_path_goes_to_shell(self):
        self.assertEqual(resolve_launch("C:\\Apps\\tool.exe"),
                         ("shell", "C:\\Apps\\tool.exe"))

    def test_blank_is_shell_noop(self):
        self.assertEqual(resolve_launch(""), ("shell", ""))


if __name__ == "__main__":
    unittest.main()
