"""
Funkcje pomocnicze używane w całej aplikacji.
Zawiera: walidację, obliczanie odległości, konfigurację logowania.
"""

import logging
import math
import os


def setup_logger(name, level=logging.INFO):
    """
    Konfiguruje logger z handlerami dla konsoli i pliku.
    
    Args:
        name (str): Nazwa loggera (zwykle __name__)
        level: Poziom logowania (default: INFO)
        
    Returns:
        logging.Logger: Skonfigurowany logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Unikaj duplikacji handlerów
    if logger.handlers:
        return logger
    
    # Format logów
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    log_dir = 'logs'
    # Zabezpieczenie przed błędem tworzenia katalogu
    try:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(f'{log_dir}/app.log')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:  
        pass  # Jeśli nie można utworzyć katalogu/pliku, po prostu loguj tylko na konsolę
    
    return logger


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Oblicza odległość między dwoma punktami geograficznymi używając wzoru haversine.
    
    Args:
        lat1 (float): Szerokość geograficzna punktu 1 (stopnie)
        lon1 (float): Długość geograficzna punktu 1 (stopnie)
        lat2 (float): Szerokość geograficzna punktu 2 (stopnie)
        lon2 (float): Długość geograficzna punktu 2 (stopnie)
        
    Returns:
        float: Odległość w metrach
    """
    R = 6371000  # Promień Ziemi w metrach
    
    # Konwersja na radiany
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2) ** 2 + 
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def validate_coordinates(coord_string):
    """
    Waliduje i parsuje współrzędne z formatu 'lat,lon'
    
    Args:
        coord_string (str): String w formacie 'lat,lon'
        
    Returns:
        tuple: (lat, lon) jako float
        
    Raises:
        ValueError: Jeśli format jest nieprawidłowy lub współrzędne poza zakresem
    """
    try:
        parts = coord_string.strip().split(',')
        
        if len(parts) != 2:
            raise ValueError("Współrzędne muszą być w formacie 'lat,lon'")
        
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        
        # Walidacja zakresów
        if not (-90 <= lat <= 90):
            raise ValueError(f"Szerokość geograficzna poza zakresem: {lat}")
        
        if not (-180 <= lon <= 180):
            raise ValueError(f"Długość geograficzna poza zakresem: {lon}")
        
        return (lat, lon)
        
    except ValueError as e:
        raise ValueError(f"Nieprawidłowy format współrzędnych '{coord_string}': {e}")
    except Exception as e:
        raise ValueError(f"Błąd parsowania współrzędnych '{coord_string}': {e}")


def calculate_bbox(gdf):
    """
    Oblicza bounding box z GeoDataFrame.
    """
    bounds = gdf.total_bounds
    return (bounds[0], bounds[1], bounds[2], bounds[3])


def format_distance(meters):
    """
    Formatuje odległość do czytelnej formy.
    """
    if meters >= 1000:
        return f"{meters/1000:.2f} km"
    else:
        return f"{int(meters)} m"