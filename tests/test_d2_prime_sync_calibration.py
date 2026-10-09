"""Independent constants for the calibration decisions; no training."""
import unittest
from scripts.run_d2_prime_sync_calibration import metrics, norm_quantile, attack_decision, evaluation_indices


class CalibrationRules(unittest.TestCase):
    def test_fixed_last_five_macro(self):
        c = {"round": [250,260,270,280,290,300], "class_total": [100]*10,
             "class_correct": [[99]*10,[40]*10,[41]*10,[42]*10,[43]*10,[44]*10]}
        m = metrics(c)
        self.assertAlmostEqual(m["M"], .42)
        self.assertAlmostEqual(m["M_endpoint"], .44)
        self.assertAlmostEqual(m["tail8_last5"], .42)

    def test_quantile_is_raw_linear_95(self):
        q = norm_quantile([1.,2.,3.,4.])
        self.assertAlmostEqual(q["B_M"], 3.85)
        self.assertEqual(q["fraction_above_B_M"], .25)

    def test_floor_and_damage_rules(self):
        clean = {"M": .50, "M_endpoint": .51}
        self.assertEqual(attack_decision(clean, {"M": .43,"M_endpoint":.44}, {"M":.32}, True), "PASS")
        self.assertEqual(attack_decision(clean, {"M": .12,"M_endpoint":.10}, {"M":.15}, True), "NEEDS_10_PERCENT")
        self.assertEqual(attack_decision(clean, {"M": .43,"M_endpoint":.44}, {"M":.15}, True), "FAIL_RFA_FLOOR")
        self.assertEqual(attack_decision(clean, {"M": .48,"M_endpoint":.48}, {"M":.32}, True), "FAIL_INSUFFICIENT_AVG_DAMAGE")
        self.assertEqual(attack_decision(clean, {"M": .43,"M_endpoint":.44}, {"M":.32}, False), "FAIL_INACTIVE_ATTACK")

    def test_disjoint_predeclared_indices(self):
        dev, final = evaluation_indices([0,1,2,0,1,2,0,1,2,0,1,2], 3)
        self.assertEqual(dev, [0,1,2,3,4,5])
        self.assertEqual(final, [6,7,8,9,10,11])


if __name__ == "__main__":
    unittest.main()
