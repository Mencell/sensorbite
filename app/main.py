"""
Flask API dla systemu planowania tras ewakuacyjnych.
Główny punkt wejścia aplikacji.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from app.engine import RoutePlanner
from app.utils import validate_coordinates, setup_logger
from app.flood_service import FloodService 
import os
import logging

app = Flask(__name__)
CORS(app)

logger = setup_logger(__name__, level=logging.INFO)

planner = None

def initialize_app():
    """Funkcja inicjalizująca dane przy starcie serwera"""
    global planner
    
    logger.info("=" * 60)
    logger.info("Uruchamianie Evacuation API")
    logger.info("=" * 60)

    try:
        geojson_path = 'data/map_data.geojson'
        
        if not os.path.exists(geojson_path):
            logger.error(f"BŁĄD: Nie znaleziono pliku {geojson_path}")
            logger.error("Upewnij się że plik map_data.geojson znajduje się w katalogu data/")
            return

        planner = RoutePlanner(geojson_path)
        
        # 1. Wczytanie dróg
        if planner.load_road_network():
            logger.info("Sieć drogowa wczytana")
            
            bounds = planner.gdf.total_bounds
            logger.info(f"GRANICE MAPY (min_x, min_y, max_x, max_y): {bounds}")
            
            # 2. Budowa grafu
            if planner.build_graph():
                logger.info("Graf zbudowany")
                
                # 3. Pobranie danych o powodziach (Sentinel Logic)
                try:
                    logger.info("Pobieranie danych radarowych (Sentinel Hub logic)...")
                    flood_service = FloodService()
                    flood_zones = flood_service.get_flood_polygons()
                    
                    # Nakładanie stref na graf (blokowanie dróg)
                    planner.set_flood_zones(flood_zones)
                except Exception as e:
                    logger.warning(f"Ostrzeżenie: Nie udało się wygenerować stref powodziowych: {e}")
                
                logger.info("=" * 60)
                logger.info("API gotowe")
                logger.info("=" * 60)
            else:
                logger.error("Nie udało się zbudować grafu")
        else:
            logger.error("Nie udało się wczytać sieci drogowej")
            
    except Exception as e:
        logger.error(f"Krytyczny błąd podczas inicjalizacji: {e}")

# Wywołanie inicjalizacji
initialize_app()


@app.route('/')
def index():
    """Strona informacyjna"""
    return jsonify({
        'name': 'Evacuation API',
        'version': '1.0.0',
        'status': 'running' if planner and planner.graph else 'error',
        'endpoints': {
            'route': '/api/evac/route?start=lat,lon&end=lat,lon',
            'health': '/health'
        }
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint sprawdzający stan serwera"""
    is_healthy = planner is not None and planner.graph is not None
    
    return jsonify({
        'status': 'healthy' if is_healthy else 'unhealthy',
        'nodes_count': planner.graph.number_of_nodes() if is_healthy else 0,
        'flood_zones_active': len(planner.flood_zones) if is_healthy else 0
    }), 200 if is_healthy else 503


@app.route('/api/evac/route', methods=['GET'])
def get_evacuation_route():
    """
    Oblicza bezpieczną trasę ewakuacji.
    GET /api/evac/route?start=52.40,16.92&end=52.42,16.93
    """
    if planner is None or planner.graph is None:
        return jsonify({'error': 'Serwer nie jest gotowy (brak mapy)'}), 503
    
    try:
        # Pobranie parametrów
        start_param = request.args.get('start')
        end_param = request.args.get('end')
        
        if not start_param or not end_param:
            return jsonify({'error': 'Brak parametrów start/end'}), 400
        
        # Parsowanie
        start_lat, start_lon = validate_coordinates(start_param)
        end_lat, end_lon = validate_coordinates(end_param)
        
        logger.info(f"Request trasy: ({start_lat},{start_lon}) -> ({end_lat},{end_lon})")
        
        # Obliczenie trasy
        result = planner.find_route(start_lat, start_lon, end_lat, end_lon)
        
        if result is None:
            return jsonify({'error': 'Błąd obliczeń'}), 500
            
        if result.get('metadata', {}).get('status') == 'error':
            return jsonify(result), 404
            
        return jsonify(result), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Błąd API: {e}", exc_info=True)
        return jsonify({'error': 'Wewnętrzny błąd serwera'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)