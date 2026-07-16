import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import fetcher  # noqa: E402


class TestIsNewsworthy(unittest.TestCase):
    def test_accepts_model_release(self):
        self.assertTrue(fetcher.is_newsworthy(
            "Anthropic introducing Claude Opus 4.8", "New flagship model now available"))

    def test_accepts_funding_news(self):
        self.assertTrue(fetcher.is_newsworthy(
            "AI startup raises $50M Series B", "Funding round led by a16z"))

    def test_rejects_non_ai(self):
        self.assertFalse(fetcher.is_newsworthy(
            "Best hiking trails in the Alps", "A guide to mountain routes"))

    def test_rejects_wildlife_noise(self):
        self.assertFalse(fetcher.is_newsworthy(
            "Giant anaconda filmed in the Amazon rainforest", "wildlife documentary"))

    def test_rejects_raw_paper(self):
        self.assertFalse(fetcher.is_newsworthy(
            "New arxiv paper on variational autoencoders", "research paper analysis"))

    def test_rejects_drama(self):
        self.assertFalse(fetcher.is_newsworthy(
            "Sam vs Elon: the AI beef continues", "lawsuit drama"))

    def test_rejects_roundup(self):
        self.assertFalse(fetcher.is_newsworthy(
            "This week in AI: weekly roundup", "your weekly digest"))
