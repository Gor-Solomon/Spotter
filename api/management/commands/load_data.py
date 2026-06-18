import pandas as pd
from django.core.management.base import BaseCommand
from api.models import FuelStation

class Command(BaseCommand):
    help = 'Load fuel stations and geocode them using an open source US cities dataset'

    def handle(self, *args, **options):
        self.stdout.write("Downloading US Cities & States coordinates mapping...")
        cities_df = pd.read_csv('https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv')
        states_df = pd.read_csv('https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_states.csv')
        
        # Merge to map STATE_CODE to LAT/LNG
        cities_states = pd.merge(cities_df, states_df, left_on='ID_STATE', right_on='ID')
        cities_states['CITY_Upper'] = cities_states['CITY'].str.upper().str.strip()
        cities_states['STATE_CODE_Upper'] = cities_states['STATE_CODE'].str.upper().str.strip()
        cities_states = cities_states.drop_duplicates(subset=['CITY_Upper', 'STATE_CODE_Upper'])
        
        self.stdout.write("Loading fuel prices from fuel-prices-for-be-assessment.csv...")
        stations_df = pd.read_csv('fuel-prices-for-be-assessment.csv')
        stations_df['City_Upper'] = stations_df['City'].str.upper().str.strip()
        stations_df['State_Upper'] = stations_df['State'].str.upper().str.strip()
        
        self.stdout.write("Merging data to assign Coordinates to Truckstops...")
        merged = pd.merge(stations_df, cities_states, left_on=['City_Upper', 'State_Upper'], right_on=['CITY_Upper', 'STATE_CODE_Upper'], how='left')
        
        self.stdout.write("Populating database...")
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
        self.stdout.write(self.style.SUCCESS(f"Successfully loaded {len(stations_to_create)} fuel stations!"))