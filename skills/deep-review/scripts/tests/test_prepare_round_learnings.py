import unittest

from prepare_round import evaluate_learning


class PrepareRoundLearningsTest(unittest.TestCase):
    def test_evaluate_learning_staleness(self):
        fields = {"scope": ["app/timecards/**/*.py"], "_staleness_count": 2}
        live_on_master = evaluate_learning(fields, ["app/other.py"], ["app/timecards/x.py"], ["app/timecards/x.py"])
        self.assertEqual((live_on_master.staleness, live_on_master.expire, live_on_master.matched), (0, False, True))
        gone = evaluate_learning({"scope": ["app/gone/**"], "_staleness_count": 1}, ["a.py"], ["b.py"], [])
        self.assertEqual((gone.staleness, gone.expire), (2, False))
        expired = evaluate_learning({"scope": ["app/gone/**"], "_staleness_count": 2}, ["a.py"], ["b.py"], ["app/gone/x.py"])
        self.assertEqual((expired.staleness, expired.expire, expired.matched), (3, True, False))


if __name__ == "__main__":
    unittest.main()
