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

    def test_accepts_issues_word_not_sues(self):
        # 'sues' must not match inside 'issues'/'pursues'
        self.assertTrue(fetcher.is_newsworthy(
            "OpenAI issues new safety guidelines", "the company issues an update"))


class TestClassifyCategory(unittest.TestCase):
    def test_release(self):
        self.assertEqual(fetcher.classify_category(
            "Introducing Claude Opus 4.8", "now available in the API"), 'releases')

    def test_business(self):
        self.assertEqual(fetcher.classify_category(
            "OpenAI acquires io for $6.5B", "acquisition deal"), 'business')

    def test_research(self):
        self.assertEqual(fetcher.classify_category(
            "New study shows LLMs beat humans on benchmark", "research"), 'research')

    def test_launch_from_content_type(self):
        self.assertEqual(fetcher.classify_category(
            "CoolAI App", "a neat new app", content_type='product_launch'), 'launches')

    def test_launch_from_keywords(self):
        self.assertEqual(fetcher.classify_category(
            "We built a new app", "just launched today"), 'launches')

    def test_conversion_not_misclassified_as_release(self):
        # 'version' must not match inside 'conversion'
        self.assertEqual(fetcher.classify_category(
            "AI tool boosts conversion rates for marketers", "growth"), 'business')

    def test_defaults_to_business(self):
        self.assertEqual(fetcher.classify_category(
            "AI adoption grows across enterprises", "industry trends"), 'business')


class TestCalculateScore(unittest.TestCase):
    CONFIG = {
        'topics': ['ai', 'agents', 'model'],
        'filters': {'reputation_weight': 0.30, 'relevance_weight': 0.20,
                    'recency_weight': 0.30, 'max_age_hours': 48},
    }

    def test_significance_bonus_applied(self):
        base = fetcher.calculate_score(
            {'title': 'AI thing', 'description': 'ai model', 'reputation': 0.5},
            self.CONFIG)
        boosted = fetcher.calculate_score(
            {'title': 'Introducing new model', 'description': 'now available ai',
             'reputation': 0.5}, self.CONFIG)
        self.assertGreater(boosted, base)

    def test_reputation_contributes(self):
        low = fetcher.calculate_score(
            {'title': 'ai model', 'reputation': 0.1}, self.CONFIG)
        high = fetcher.calculate_score(
            {'title': 'ai model', 'reputation': 1.0}, self.CONFIG)
        self.assertGreater(high, low)


if __name__ == '__main__':
    unittest.main()
