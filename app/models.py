from dataclasses import dataclass
from typing import Optional, Dict, Any
from shapely.geometry import LineString, Polygon


@dataclass
class RoadSegment:
    """
    Reprezentuje pojedynczy segment drogi w sieci.
    
    Attributes:
        id (str): Unikalny identyfikator segmentu
        geometry (LineString): Geometria segmentu jako LineString
        length (float): Długość segmentu w metrach
        is_flooded (bool): Czy segment jest zalany
        properties (dict): Dodatkowe właściwości z OSM
    """
    id: str
    geometry: LineString
    length: float
    is_flooded: bool = False
    properties: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Walidacja po inicjalizacji"""
        if self.length < 0:
            raise ValueError("Długość segmentu nie może być ujemna")
        if not isinstance(self.geometry, LineString):
            raise TypeError("Geometria musi być typu LineString")


@dataclass
class FloodZone:
    """
    Reprezentuje strefę zagrożenia powodziowego.
    
    Attributes:
        id (str): Unikalny identyfikator strefy
        geometry (Polygon): Geometria strefy jako Polygon
        severity (float): Poziom zagrożenia (0.0 - 1.0)
        timestamp (str): Czas detekcji strefy (opcjonalne)
        source (str): Źródło danych (np. 'Sentinel Hub', 'Mock')
    """
    id: str
    geometry: Polygon
    severity: float = 1.0
    timestamp: Optional[str] = None
    source: str = "Unknown"
    
    def __post_init__(self):
        """Walidacja po inicjalizacji"""
        if not (0.0 <= self.severity <= 1.0):
            raise ValueError("Severity musi być w zakresie 0.0-1.0")
        if not isinstance(self.geometry, Polygon):
            raise TypeError("Geometria musi być typu Polygon")
    
    def to_geojson_feature(self):
        """
        Konwertuje strefę do formatu GeoJSON Feature.
        
        Returns:
            dict: GeoJSON Feature
        """
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [list(self.geometry.exterior.coords)]
            },
            'properties': {
                'id': self.id,
                'severity': self.severity,
                'timestamp': self.timestamp,
                'source': self.source
            }
        }


@dataclass
class RouteResult:
    """
    Reprezentuje wynik wyszukiwania trasy.
    
    Attributes:
        path (list): Lista węzłów tworzących trasę
        geometry (LineString): Geometria całej trasy
        distance_meters (float): Całkowita długość trasy w metrach
        flooded_segments (int): Liczba zalanych segmentów w trasie
        nodes_count (int): Liczba węzłów w trasie
        status (str): Status operacji ('success', 'error')
        message (str): Dodatkowa wiadomość (np. błędy)
    """
    path: list
    geometry: LineString
    distance_meters: float
    flooded_segments: int
    nodes_count: int
    status: str = "success"
    message: Optional[str] = None
    
    def to_geojson(self):
        """
        Konwertuje wynik do formatu GeoJSON.
        
        Returns:
            dict: GeoJSON FeatureCollection
        """
        return {
            'type': 'FeatureCollection',
            'features': [{
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': list(self.geometry.coords)
                },
                'properties': {
                    'distance_meters': round(self.distance_meters, 2),
                    'nodes_count': self.nodes_count,
                    'flooded_segments': self.flooded_segments
                }
            }],
            'metadata': {
                'distance_meters': round(self.distance_meters, 2),
                'status': self.status,
                'message': self.message
            }
        }