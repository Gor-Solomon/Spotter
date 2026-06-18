import pandas as pd
import os
from django.core.management.base import BaseCommand
from api.models import FuelStation

class Command(BaseCommand):
    help = 'Load fuel stations and geocode them using local US cities dataset'

    def handle(self, *args, **options):
        # 1. Load Local Cities Data
        self.stdout.write("Loading US Cities coordinates from local file...")
        try:
            cities_states = pd.read_csv('uscities.csv')
            self.stdout.write(self.style.SUCCESS("Successfully loaded local city coordinates!"))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("Could not find uscities.csv. Please ensure it is in the root folder."))
            return
            
        # Clean up the coordinate data for merging
        cities_states['CITY_Upper'] = cities_states['CITY'].astype(str).str.upper().str.strip()
        cities_states['STATE_CODE_Upper'] = cities_states['STATE_CODE'].astype(str).str.upper().str.strip()
        cities_states = cities_states.drop_duplicates(subset=['CITY_Upper', 'STATE_CODE_Upper'])
        
        # 2. Load Local Fuel Prices
        self.stdout.write("Loading fuel prices from fuel-prices-for-be-assessment.csv...")
        stations_df = pd.read_csv('fuel-prices-for-be-assessment.csv')
        stations_df['City_Upper'] = stations_df['City'].astype(str).str.upper().str.strip()
        stations_df['State_Upper'] = stations_df['State'].astype(str).str.upper().str.strip()
        
        # 3. Merge Datasets
        self.stdout.write("Merging data to assign Coordinates to Truckstops...")
        merged = pd.merge(stations_df, cities_states, left_on=['City_Upper', 'State_Upper'], right_on=['CITY_Upper', 'STATE_CODE_Upper'], how='left')
        
        # 4. Save to Database
        self.stdout.write("Populating database (this might take a few seconds)...")
        FuelStation.objects.all().delete()
        
        stations_to_create = []
        for index, row in merged.iterrows():
            lat = row['LATITUDE'] if not pd.isna(row['LATITUDE']) else None
            lng = row['LONGITUDE'] if not pd.isna(row['LONGITUDE']) else None
            
            stations_to_create.append(FuelStation(
                opis_id=str(row['OPIS Truckstop ID']),
                name=str(row['Truckstop Name']),
                address=str(row['Address']),
                city=str(row['City']),
                state=str(row['State']),
                price=float(row['Retail Price']),
                lat=lat,
                lng=lng
            ))
            
        FuelStation.objects.bulk_create(stations_to_create, batch_size=500)
        
        success_count = sum(1 for s in stations_to_create if s.lat is not None)
        self.stdout.write(self.style.SUCCESS(f"Successfully loaded {len(stations_to_create)} fuel stations! ({success_count} mapped to exact GPS coordinates)"))