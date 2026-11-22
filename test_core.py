import unittest
import pandas as pd
from kavach.core import haversine_km, geofence_status, cluster_fire_hotspots, estimate_population, score_threat

class TestKavachCore(unittest.TestCase):
    def test_same_point_distance_zero(self):
        self.assertAlmostEqual(haversine_km(23.2,77.4,23.2,77.4),0,places=5)

    def test_geofence_classes(self):
        self.assertEqual(geofence_status(23.2599,77.4126,23.2599,77.4126,5,10)[0],"DANGER")
        self.assertEqual(geofence_status(23.30,77.45,23.2599,77.4126,1,20)[0],"WARNING")
        self.assertEqual(geofence_status(24.0,78.0,23.2599,77.4126,1,2)[0],"SAFE")

    def test_cluster_hotspots(self):
        df=pd.DataFrame([
            {"latitude":23.25,"longitude":77.41,"frp":10,"confidence":"h","observed":"now"},
            {"latitude":23.251,"longitude":77.411,"frp":20,"confidence":"h","observed":"now"},
            {"latitude":24.0,"longitude":78.0,"frp":5,"confidence":"n","observed":"now"}
        ])
        clusters=cluster_fire_hotspots(df,8)
        self.assertEqual(len(clusters),2)
        self.assertEqual(int(clusters.hotspot_count.sum()),3)

    def test_population_estimate(self):
        self.assertGreater(estimate_population(5,1000),0)

    def test_score_bounds(self):
        self.assertGreaterEqual(score_threat("Fire","Critical",500,100000),0)
        self.assertLessEqual(score_threat("Fire","Critical",500,100000),100)

if __name__=="__main__":
    unittest.main()
