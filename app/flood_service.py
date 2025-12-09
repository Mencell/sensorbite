"""
Ta implementacja używa symulowanych danych radarowych do demonstracji działania systemu.
Logika detekcji (próg -21dB dla bandy VH) odpowiada oryginalnemu skryptowi Sentinel Hub:
https://github.com/makingsensingbeneficial/EO-bite/blob/main/tools/scrips/flood.js
"""

import numpy as np
import rasterio
from rasterio import features
from shapely.geometry import shape, Polygon
import logging

logger = logging.getLogger(__name__)


class FloodService:
    """
    Serwis wykrywania stref powodziowych z danych radarowych Sentinel-1.

    """
    def get_flood_polygons(self) -> list[Polygon]:
        logger.info("Uruchamianie analizy danych radarowych...")
        

        width, height = 100, 100
        
        vh_input = np.random.uniform(0.05, 0.2, (height, width))
        
        water_pixels = np.random.uniform(0.001, 0.005, (height, width))
        
        vh_input[40:60, :] = water_pixels[40:60, :] 

        with np.errstate(divide='ignore'):
            vh_db = 10 * np.log10(vh_input)

        flood_threshold = -21.0

        flood_mask = (vh_db < flood_threshold).astype(np.uint8)

        min_lon, min_lat = 16.92, 52.40
        max_lon, max_lat = 16.96, 52.42
        
        transform = rasterio.transform.from_bounds(
            min_lon, min_lat, 
            max_lon, max_lat, 
            width, height
        )

        found_polygons = []
        for geom, value in features.shapes(flood_mask, transform=transform):
            if value == 1:

                poly = shape(geom)
                found_polygons.append(poly)

        logger.info(f"FloodService: Wykryto {len(found_polygons)} stref zalania (threshold: {flood_threshold}dB)")
        return found_polygons