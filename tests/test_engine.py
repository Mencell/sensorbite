import os
import json
import shutil
from shapely.geometry import Polygon
from app.engine import RoutePlanner
from app.utils import validate_coordinates, haversine_distance

class TestUtils:
    def test_validate_coordinates_valid(self):
        assert validate_coordinates("52.40,16.92") == (52.40, 16.92)

    def test_haversine_distance(self):
        # Dystans ok. 111km
        dist = haversine_distance(52.0, 16.0, 53.0, 16.0)
        assert 110000 < dist < 112000

class TestRoutePlanner:
    def setup_method(self):
        # Tworzy tymczasowy katalog na testowe dane
        self.test_dir = "tests/temp_data"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
        
        # Tworzy prosty plik GeoJSON z dwiema drogami:
        # 1. Droga PROSTA (krótka) - zostanie zalana
        # A (16.90, 52.40) -> B (16.92, 52.40)
        # 2. Droga OBJAZD (długa) - będzie bezpieczna
        # A (16.90, 52.40) -> C (16.91, 52.41) -> B (16.92, 52.40)
        self.geojson_path = os.path.join(self.test_dir, "test_map.geojson")
        
        data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[16.90, 52.40], [16.92, 52.40]]
                    },
                    "properties": {"id": "direct"}
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[16.90, 52.40], [16.91, 52.41]]
                    },
                    "properties": {"id": "detour1"}
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[16.91, 52.41], [16.92, 52.40]]
                    },
                    "properties": {"id": "detour2"}
                }
            ]
        }
        
        with open(self.geojson_path, 'w') as f:
            json.dump(data, f)

        self.planner = RoutePlanner(self.geojson_path)
        self.planner.load_road_network()
        self.planner.build_graph()

    def teardown_method(self):
        # Sprzątanie po testach
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_find_route_basic(self):
        """Sprawdza czy znajduje najkrótszą trasę (prostą) bez powodzi"""
        result = self.planner.find_route(52.40, 16.90, 52.40, 16.92)
        assert result is not None
        coords = result['features'][0]['geometry']['coordinates']
        assert len(coords) == 2 
        assert result['metadata']['status'] == 'success'

    def test_avoid_flood_zone(self):
        """Sprawdza czy omija zalaną strefę i porównuje dystanse"""
        
        # KROK 1: Oblicz trasę BEZ powodzi (bazową)
        print("\n--- ROZPOCZĘCIE TESTU OBJAZDU ---")
        base_result = self.planner.find_route(52.40, 16.90, 52.40, 16.92)
        base_dist = base_result['metadata']['distance_meters']
        print(f"1. Długość trasy bezpośredniej: {base_dist:.2f} m")

        # KROK 2: Zdefiniuj strefę zalania (barierę)
        # Blokujemy tylko linię Y=52.40
        flood_poly = Polygon([
            (16.905, 52.399),
            (16.915, 52.399),
            (16.915, 52.401),
            (16.905, 52.401)
        ])
        
        # Nakładamy strefy
        self.planner.set_flood_zones([flood_poly])
        
        # KROK 3: Szukamy trasy ponownie
        detour_result = self.planner.find_route(52.40, 16.90, 52.40, 16.92)
        detour_dist = detour_result['metadata']['distance_meters']
        print(f"2. Długość trasy z objazdem:    {detour_dist:.2f} m")
        
        # KROK 4: Asercje
        coords = detour_result['features'][0]['geometry']['coordinates']
        
        # Sprawdzamy czy objazd jest faktycznie dłuższy
        assert detour_dist > base_dist, "Objazd powinien być dłuższy niż trasa prosta"
        
        # Sprawdzamy czy ma 3 punkty (czyli czy poszedł przez punkt C)
        assert len(coords) == 3