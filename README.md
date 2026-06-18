# Spotter Backend Assessment: Fuel Routing API

An optimized routing API built in Django that calculates the most cost-effective fuel stops for a trip within the USA. It assumes a vehicle with a 500-mile maximum range and an efficiency of 10 miles per gallon.

---

## 🎥 Demonstration Video
**Please view the `demo_video.mp4` file included in this repository** for a full walkthrough of the API functionality, the interactive map UI, and the backend architecture. 

---

## 🚀 Tech Stack
* **Framework:** Django (Python 3.11)
* **Database:** SQLite (for portability and speed)
* **Containerization:** Docker & Docker Compose
* **Data Processing:** Pandas
* **Routing Engine:** Open Source Routing Machine (OSRM) API

---

## 🧠 System Architecture & Logic

### 1. Data Ingestion & Geocoding (`load_data.py`)
To prevent the API from making thousands of slow geocoding requests on the fly, I built a custom Django Management Command. 
* It ingests the provided `fuel-prices-for-be-assessment.csv`.
* It merges the OPIS data with an open-source US Cities database using Pandas to assign exact latitude and longitude coordinates to every truck stop.
* It populates the local SQLite database in seconds.

### 2. Routing Engine
To minimize external API calls (fulfilling the assessment requirements), the app makes **one single call** to the free OSRM driving API. This returns the complete route polyline and total distance.

### 3. Greedy Optimization Algorithm
To calculate the optimal fuel stops, the algorithm performs the following steps:
1. **Spatial Filtering:** Filters the database to only consider fuel stations near the bounding box of the calculated route.
2. **Downsampling & Snapping:** Projects those stations onto the route polyline to determine their exact distance from the starting location.
3. **Cost Optimization:** Starting at mile 0, the algorithm looks ahead up to the 500-mile maximum range limit. It finds the absolute cheapest fuel station in that reachable radius.
4. **Virtual Refueling:** The vehicle "stops" at the cheapest station, calculates the gallons needed (at 10 MPG) since the last stop, and adds it to the total cost. This repeats until the destination is reached.

---

## 🛠️ How to Run Locally

Because this application is containerized with Docker, you do not need to install Python or Django locally. 

**1. Start the Docker containers:**
```bash
docker-compose up -d
