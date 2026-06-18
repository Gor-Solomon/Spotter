import math
import requests
from django.http import JsonResponse
from django.views import View
from geopy.geocoders import Nominatim
from .models import FuelStation

def haversine(lon1, lat1, lon2, lat2):
    """Calculates distance between two coordinate pairs in miles"""
    R = 3958.8 
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

class RouteView(View):
    def get(self, request):
        start_loc = request.GET.get('start', 'New York, NY')
        finish_loc = request.GET.get('finish', 'Los Angeles, CA')
        
        # 1. Geocode Start and Finish
        geolocator = Nominatim(user_agent="fuel_routing_api")
        start_geo = geolocator.geocode(start_loc)
        finish_geo = geolocator.geocode(finish_loc)
        
        if not start_geo or not finish_geo:
            return JsonResponse({'error': 'Could not accurately geocode locations.'}, status=400)
            
        # 2. Get Route from Free OSRM API
        url = f"http://router.project-osrm.org/route/v1/driving/{start_geo.longitude},{start_geo.latitude};{finish_geo.longitude},{finish_geo.latitude}?overview=full&geometries=geojson"
        resp = requests.get(url).json()
        
        if 'routes' not in resp or not resp['routes']:
            return JsonResponse({'error': 'No route found.'}, status=400)
            
        route = resp['routes'][0]
        coords = route['geometry']['coordinates'] # Route polyline
        
        # Map out cumulative distances to route points
        cum_dist = [0.0]
        for i in range(1, len(coords)):
            d = haversine(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1])
            cum_dist.append(cum_dist[-1] + d)
            
        total_distance = cum_dist[-1]
        
        # 3. Filter stations within bounds of the route
        stations = list(FuelStation.objects.exclude(lat__isnull=True).values())
        min_lon, max_lon = min(c[0] for c in coords) - 1, max(c[0] for c in coords) + 1
        min_lat, max_lat = min(c[1] for c in coords) - 1, max(c[1] for c in coords) + 1
        filtered_stations = [s for s in stations if min_lon <= s['lng'] <= max_lon and min_lat <= s['lat'] <= max_lat]
        
        # Project candidates dynamically to closest points on the route (downsampled for speed)
        candidates = []
        for s in filtered_stations:
            min_d, best_idx = float('inf'), 0
            for i in range(0, len(coords), 10): 
                d = haversine(s['lng'], s['lat'], coords[i][0], coords[i][1])
                if d < min_d:
                    min_d, best_idx = d, i
                    
            if min_d < 30: # Only look at stations reasonably close to the path
                candidates.append({'station': s, 'dist_from_start': cum_dist[best_idx]})
                
        candidates.sort(key=lambda x: x['dist_from_start'])
        
        # 4. Greedy optimization approach for minimal cost (500-mile max range)
        current_pos, max_range, mpg, total_cost = 0.0, 500.0, 10.0, 0.0
        stops = []
        
        while current_pos + max_range < total_distance:
            reachable = [c for c in candidates if current_pos < c['dist_from_start'] <= current_pos + max_range]
            if not reachable:
                return JsonResponse({'error': 'Not enough fuel stations on route to complete the trip.'}, status=400)
                
            best_stop = min(reachable, key=lambda x: x['station']['price'])
            dist_driven = best_stop['dist_from_start'] - current_pos
            gallons_needed = dist_driven / mpg
            
            # Use price from previously visited stop to refuel, default to initial if it's the first leg
            price_to_use = stops[-1]['price'] if stops else best_stop['station']['price']
            total_cost += gallons_needed * price_to_use
            
            stops.append({
                'name': best_stop['station']['name'],
                'city': best_stop['station']['city'],
                'state': best_stop['station']['state'],
                'price': best_stop['station']['price'],
                'lat': best_stop['station']['lat'],
                'lng': best_stop['station']['lng'],
            })
            
            current_pos = best_stop['dist_from_start']
            
        # Add the cost to reach the destination from the last stop
        dist_remaining = total_distance - current_pos
        if dist_remaining > 0:
            gallons_needed = dist_remaining / mpg
            price_to_use = stops[-1]['price'] if stops else 3.50
            total_cost += gallons_needed * price_to_use
            
        return JsonResponse({
            'route_map_geojson': route['geometry'],
            'total_distance_miles': round(total_distance, 2),
            'optimal_fuel_stops': stops,
            'total_fuel_cost': round(total_cost, 2)
        })