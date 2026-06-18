import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from api.models import FuelStation
from api.views import haversine

class SpotterAssessmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed the test database with a couple of fake stations
        FuelStation.objects.create(
            opis_id="1", name="Cheap Stop", address="123 Main", city="A", state="TX", 
            price=2.00, lat=1.0, lng=1.0
        )
        FuelStation.objects.create(
            opis_id="2", name="Expensive Stop", address="456 High", city="B", state="TX", 
            price=4.00, lat=2.0, lng=2.0
        )

    def test_haversine_math(self):
        """Test the internal distance calculator"""
        dist = haversine(0, 0, 1, 0)
        self.assertTrue(68 < dist < 70)

    @patch('api.views.Nominatim')
    @patch('api.views.requests.get')
    def test_route_optimization(self, mock_requests, MockNominatim):
        """Test the API endpoint, mocking external calls for speed and reliability"""
        
        # 1. Mock the Geocoder so it doesn't need internet
        mock_geocoder_instance = MagicMock()
        mock_start = MagicMock()
        mock_start.latitude, mock_start.longitude = 0.0, 0.0
        mock_finish = MagicMock()
        mock_finish.latitude, mock_finish.longitude = 6.0, 6.0
        
        mock_geocoder_instance.geocode.side_effect = [mock_start, mock_finish]
        MockNominatim.return_value = mock_geocoder_instance

        # 2. Mock OSRM Routing API (Generate a 60-point route so the downsampler catches the stations)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "routes": [{
                "geometry": {
                    "coordinates": [[float(i)/10, float(i)/10] for i in range(61)]
                }
            }]
        }
        mock_requests.return_value = mock_response

        # 3. Hit our API
        response = self.client.get('/api/route/?start=CityA&finish=CityB')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        
        # 4. Verify all Spotter Requirements are returned
        self.assertIn("route_map_geojson", data)
        self.assertIn("optimal_fuel_stops", data)
        self.assertIn("total_fuel_cost", data)
        self.assertIn("total_distance_miles", data)
        
        # 5. Verify the algorithm stops at the cheap station, not the expensive one
        stops = data['optimal_fuel_stops']
        self.assertTrue(len(stops) > 0)
        self.assertEqual(stops[0]['name'], "Cheap Stop")
        self.assertEqual(stops[0]['price'], 2.00)