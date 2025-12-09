"""
Główny silnik planowania tras ewakuacyjnych.
"""

import networkx as nx
import geopandas as gpd
from shapely.geometry import LineString
import logging
from app.utils import haversine_distance

logger = logging.getLogger(__name__)


class RoutePlanner:
    """Planner tras ewakuacyjnych z omijaniem stref zagrożenia"""
    
    def __init__(self, geojson_path):
        """
        Args:
            geojson_path (str): Ścieżka do pliku GeoJSON z siecią drogową
        """
        self.geojson_path = geojson_path
        self.graph = None
        self.gdf = None
        self.flood_zones = []
        logger.info(f"Inicjalizacja RoutePlanner: {geojson_path}")
        
    def load_road_network(self):
        """Wczytuje sieć drogową z pliku GeoJSON"""
        try:
            logger.info("Wczytywanie sieci drogowej...")
            self.gdf = gpd.read_file(self.geojson_path)
            logger.info(f"Wczytano {len(self.gdf)} elementów")
            return True
        except FileNotFoundError:
            logger.error(f"Nie znaleziono pliku: {self.geojson_path}")
            return False
        except Exception as e:
            logger.error(f"Błąd wczytywania: {e}")
            return False
    
    def build_graph(self):
        """Buduje graf sieciowy z danych drogowych"""
        if self.gdf is None:
            logger.error("Najpierw wywołaj load_road_network()")
            return False
        
        logger.info("Budowanie grafu...")
        self.graph = nx.Graph()
        edge_count = 0
        
        for idx, row in self.gdf.iterrows():
            geom = row.geometry
            
            if geom.geom_type == 'LineString':
                edge_count += self._add_linestring_to_graph(geom, idx)
            elif geom.geom_type == 'MultiLineString':
                for line in geom.geoms:
                    edge_count += self._add_linestring_to_graph(line, idx)
        
        logger.info(f"✓ Graf: {self.graph.number_of_nodes()} węzłów, {edge_count} krawędzi")
        return True
    
    def _add_linestring_to_graph(self, linestring, feature_id):
        """Dodaje LineString do grafu jako serię krawędzi"""
        coords = list(linestring.coords)
        added = 0
        
        for i in range(len(coords) - 1):
            start = coords[i]
            end = coords[i + 1]
            
            distance = haversine_distance(start[1], start[0], end[1], end[0])
            
            self.graph.add_edge(
                start, end,
                weight=distance,
                geometry=LineString([start, end]),
                segment_id=f"{feature_id}_{i}",
                is_flooded=False
            )
            added += 1
        
        return added
    
    def set_flood_zones(self, flood_zones):
        """
        Ustawia strefy zagrożenia i oznacza zalane krawędzie grafu.
        
        Args:
            flood_zones (list): Lista Polygon reprezentujących strefy zagrożenia
        """
        self.flood_zones = flood_zones
        logger.info(f"Ustawiono {len(flood_zones)} stref zagrożenia")
        self._mark_flooded_edges()
    
    def _mark_flooded_edges(self):
        """Oznacza krawędzie przecinające strefy zagrożenia wysoką wagą"""
        if not self.flood_zones:
            logger.warning("Brak stref zagrożenia")
            return
        
        logger.info("Oznaczanie zalanych segmentów...")
        flooded_count = 0
        
        for u, v, data in self.graph.edges(data=True):
            edge_geom = data.get('geometry')
            
            if edge_geom:
                for flood_zone in self.flood_zones:
                    if edge_geom.intersects(flood_zone):
                        data['is_flooded'] = True
                        
                        data['weight'] = data['weight'] * 100
                        flooded_count += 1
                        break
        
        logger.info(f"Oznaczono {flooded_count} zalanych segmentów")
    
    def find_route(self, start_lat, start_lon, end_lat, end_lon):
        """
        Znajduje optymalną trasę między punktami.
        
        Args:
            start_lat, start_lon: Współrzędne startu
            end_lat, end_lon: Współrzędne celu
            
        Returns:
            dict: GeoJSON z trasą i metadanymi lub None
        """
        if self.graph is None:
            logger.error("Graf nie został zbudowany")
            return None
        
        try:
            logger.info(f"Szukanie trasy: ({start_lat},{start_lon}) -> ({end_lat},{end_lon})")
            
            start_node = self._find_nearest_node(start_lat, start_lon)
            end_node = self._find_nearest_node(end_lat, end_lon)
            
            if start_node is None or end_node is None:
                logger.error("Nie znaleziono węzłów w grafie")
                return None
            
            path = nx.astar_path(
                self.graph,
                start_node,
                end_node,
                heuristic=self._heuristic,
                weight='weight'
            )
            
            route_coords = [(lon, lat) for lon, lat in path]
            total_distance = self._calculate_path_length(path)
            flooded_segments = self._count_flooded_segments(path)
            
            result = {
                'type': 'FeatureCollection',
                'features': [{
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': route_coords
                    },
                    'properties': {
                        'distance_meters': round(total_distance, 2),
                        'nodes_count': len(path),
                        'flooded_segments': flooded_segments
                    }
                }],
                'metadata': {
                    'start': {'lat': start_lat, 'lon': start_lon},
                    'end': {'lat': end_lat, 'lon': end_lon},
                    'distance_meters': round(total_distance, 2),
                    'status': 'success'
                }
            }
            
            logger.info(f"✓ Trasa: {len(path)} węzłów, {total_distance:.0f}m, {flooded_segments} zalanych segmentów")
            return result
            
        except nx.NetworkXNoPath:
            logger.error("Brak dostępnej trasy")
            return {
                'metadata': {
                    'status': 'error',
                    'message': 'Nie znaleziono trasy między punktami'
                }
            }
        except Exception as e:
            logger.error(f"Błąd podczas szukania trasy: {e}")
            return None
    
    def _find_nearest_node(self, lat, lon):
        """Znajduje najbliższy węzeł grafu do podanych współrzędnych"""
        min_distance = float('inf')
        nearest_node = None
        
        for node in self.graph.nodes():
            node_lon, node_lat = node
            distance = haversine_distance(lat, lon, node_lat, node_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
        
        return nearest_node
    
    def _heuristic(self, node1, node2):
        """A* - odległość haversine"""
        lon1, lat1 = node1
        lon2, lat2 = node2
        return haversine_distance(lat1, lon1, lat2, lon2)
    
    def _calculate_path_length(self, path):
        """Oblicza rzeczywistą długość trasy (bez kar za zalanie)"""
        total = 0
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i + 1])
            if edge_data:
                weight = edge_data.get('weight', 0)
                # Jeśli zalane, przywróć oryginalną wagę
                if edge_data.get('is_flooded', False):
                    weight = weight / 100
                total += weight
        return total
    
    def _count_flooded_segments(self, path):
        """Liczy ile segmentów w trasie jest zalanych"""
        count = 0
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i + 1])
            if edge_data and edge_data.get('is_flooded', False):
                count += 1
        return count