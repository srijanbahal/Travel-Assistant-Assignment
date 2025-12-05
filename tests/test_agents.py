import unittest
import sys
import os

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.flights import search_flights
from tools.hotels import search_hotels
from tools.trains import search_trains

class TestTools(unittest.TestCase):
    def test_search_flights(self):
        # Test finding flights
        results = search_flights("Mumbai", "Delhi")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["origin"], "Mumbai")
        
        # Test no flights
        results = search_flights("Mars", "Venus")
        self.assertEqual(len(results), 0)

    def test_search_hotels(self):
        results = search_hotels("Guwahati")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["location"], "Guwahati")

    def test_search_trains(self):
        results = search_trains("Chennai", "Bangalore")
        self.assertTrue(len(results) > 0)

if __name__ == '__main__':
    unittest.main()
