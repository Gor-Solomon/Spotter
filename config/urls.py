from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

HTML_UI = """
<!DOCTYPE html>
<html>
<head>
    <title>Spotter Fuel Optimizer</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background: #f4f7f6; color: #333; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h2 { margin-top: 0; color: #2c3e50; }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 16px; }
        button { padding: 12px 25px; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 6px; font-size: 16px; font-weight: bold; transition: 0.3s;}
        button:hover { background: #218838; }
        #map { height: 500px; width: 100%; border-radius: 12px; margin-top: 20px; border: 2px solid #eee;}
        .stats { display: flex; gap: 15px; margin-top: 20px; }
        .stat-box { background: #e9ecef; padding: 20px; border-radius: 10px; flex: 1; text-align: center; }
        .stat-box h3 { margin: 0 0 10px 0; font-size: 14px; color: #6c757d; text-transform: uppercase; }
        .stat-box p { margin: 0; font-size: 24px; font-weight: bold; color: #212529; }
        #loading { text-align: center; font-size: 18px; font-weight: bold; color: #007bff; display: none; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Spotter Fuel Route Optimizer</h2>
        <div class="input-group">
            <input type="text" id="start" placeholder="Start (e.g. New York, NY)" value="New York, NY">
            <input type="text" id="finish" placeholder="Finish (e.g. Miami, FL)" value="Miami, FL">
            <button onclick="calcRoute()">Calculate Route</button>
        </div>
        
        <div id="loading">Calculating optimal route and fuel stops...</div>
        
        <div class="stats" id="stats" style="display:none;">
            <div class="stat-box"><h3>Total Distance</h3><p id="dist">0 miles</p></div>
            <div class="stat-box"><h3>Total Fuel Cost</h3><p id="cost">$0.00</p></div>
            <div class="stat-box"><h3>Fuel Stops</h3><p id="stops-count">0</p></div>
        </div>

        <div id="map"></div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map').setView([39.8283, -98.5795], 4);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map);
        let layerGroup = L.layerGroup().addTo(map);

        async function calcRoute() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('stats').style.display = 'none';
            layerGroup.clearLayers();

            const start = document.getElementById('start').value;
            const finish = document.getElementById('finish').value;

            try {
                const res = await fetch(`/api/route/?start=${encodeURIComponent(start)}&finish=${encodeURIComponent(finish)}`);
                const data = await res.json();
                
                if (data.error) {
                    alert(data.error);
                    document.getElementById('loading').style.display = 'none';
                    return;
                }

                document.getElementById('dist').innerText = data.total_distance_miles + " mi";
                document.getElementById('cost').innerText = "$" + data.total_fuel_cost;
                document.getElementById('stops-count').innerText = data.optimal_fuel_stops.length;
                document.getElementById('stats').style.display = 'flex';

                // Draw the blue route line
                const routeLine = L.geoJSON(data.route_map_geojson, { style: { color: '#007bff', weight: 5 } }).addTo(layerGroup);
                map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });

                // Add markers for fuel stops
                data.optimal_fuel_stops.forEach((stop, index) => {
                    let marker = L.marker([stop.lat, stop.lng]).addTo(layerGroup);
                    marker.bindPopup(`<b>Stop ${index + 1}: ${stop.name}</b><br>Price: $${stop.price} / gallon<br>${stop.city}, ${stop.state}`);
                });
            } catch(e) {
                alert("Error calculating route. Check terminal for details.");
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

def frontend_view(request):
    return HttpResponse(HTML_UI)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', frontend_view),  # This serves the UI on the base URL
]