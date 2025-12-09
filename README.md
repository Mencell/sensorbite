# Sensorbite Evacuation Route Planner

Mikroserwis wyznaczający bezpieczne trasy ewakuacyjne z uwzględnieniem dynamicznych zagrożeń powodziowych. System analizuje sieć drogową oraz dane radarowe (symulacja Sentinel-1), aby wyznaczyć optymalną ścieżkę z punktu A do punktu B, omijając zagrożone obszary.

## Kluczowe Funkcjonalności

* **Algorytm A* (A-Star):** Szybkie wyznaczanie najkrótszej ścieżki w grafie drogowym.
* **Soft Avoid Logic:** System nie traktuje zalanych dróg jako całkowicie nieprzejezdnych, lecz nadaje im bardzo wysoką karę wagową (x100). Pozwala to na wyznaczenie trasy przez wodę tylko w ostateczności (gdy nie ma innej drogi), ale priorytetem zawsze jest bezpieczny objazd.
* **Symulacja Sentinel-1:** Zaimplementowana logika detekcji wody na podstawie analizy wstecznego rozproszenia (Backscatter) w paśmie VH (próg odcięcia -21 dB).
* **Architektura Mikroserwisu:** Lekkie API oparte o Flask, gotowe do konteneryzacji.
* **Obsługa Błędów:** Rozbudowany system raportowania błędów (HTTP 400/404/500) oraz walidacja danych wejściowych.

---

## Struktura Projektu

Kod został podzielony na moduły, co ułatwia jego rozwój i testowanie:

.
├── app/
│   ├── main.py          # Punkt wejścia aplikacji (Flask API)
│   ├── engine.py        # Logika biznesowa: budowa grafu i algorytm A*
│   ├── flood_service.py # Serwis analizy danych radarowych (Sentinel logic)
│   ├── models.py        # Modele danych (RoadSegment, RouteResult)
│   └── utils.py         # Narzędzia: logowanie, walidacja geo, matematyka
├── data/
│   └── map_data.geojson # Dane geograficzne sieci drogowej
├── tests/
│   └── test_engine.py   # Testy jednostkowe (pytest)
├── Dockerfile           # Konfiguracja środowiska uruchomieniowego
└── requirements.txt     # Zależności Python

---

## Jak uruchomić (Instalacja)

Projekt jest przygotowany do uruchomienia na dowolnym systemie (Windows/macOS/Linux).

### Opcja 1: Docker (Zalecane)
Gwarantuje identyczne środowisko jak na produkcji.

1. Zbuduj obraz:
   docker build -t sensorbite-evac .

2. Uruchom kontener:
   docker run -p 5000:5000 sensorbite-evac

### Opcja 2: Python (Lokalnie)
Wymaga Python 3.9+ oraz zainstalowanych bibliotek systemowych GDAL.

1. Zainstaluj zależności:
   pip install -r requirements.txt

2. Uruchom aplikację:
   # Ważne: Uruchamiaj jako moduł (-m), aby zachować poprawne ścieżki importów
   python -m app.main

---

## Instrukcja pracy z narzędziem (API)

### 1. Sprawdzenie stanu (Health Check)
Zwraca status serwera, liczbę węzłów w grafie oraz status serwisu powodziowego.

* URL: /health
* Metoda: GET

### 2. Wyznaczanie trasy (Testowe wywołanie)
Oblicza bezpieczną trasę między dwoma punktami (lat,lon).

* URL: /api/evac/route
* Metoda: GET
* Parametry:
    * start: współrzędne początkowe (np. 52.402,16.925)
    * end: współrzędne końcowe (np. 52.405,16.930)

#### Przykładowe wywołanie (cURL):
curl "http://localhost:5000/api/evac/route?start=52.402,16.925&end=52.405,16.930"

#### Przykładowa odpowiedź (JSON):
{
  "features": [
    {
      "geometry": { "coordinates": [[16.925, 52.402], ...], "type": "LineString" },
      "properties": {
        "distance_meters": 2605.09,
        "flooded_segments": 0,
        "nodes_count": 66
      },
      "type": "Feature"
    }
  ],
  "metadata": {
    "status": "success",
    "distance_meters": 2605.09
  }
}

---

## Testy Jednostkowe

Projekt posiada zestaw testów weryfikujących logikę wyznaczania tras oraz mechanizm omijania przeszkód. Testy symulują sytuację powodziową na mapie i sprawdzają, czy algorytm wybierze objazd.

Aby uruchomić testy i zobaczyć porównanie dystansów:
python -m pytest tests/test_engine.py -v -s

Oczekiwany wynik:
* test_find_route_basic: PASSED (Znajduje trasę w normalnych warunkach)
* test_avoid_flood_zone: PASSED (Wybiera dłuższą trasę, aby ominąć zalaną strefę)

---

## Szczegóły Techniczne

* Logowanie: Aplikacja używa wbudowanego modułu logging skonfigurowanego w utils.py. Logi zawierają poziomy INFO (start, sukces) oraz ERROR (brak plików, błędy obliczeń).
* Walidacja: Wszystkie współrzędne są sprawdzane pod kątem poprawności geograficznej (-90/90 lat, -180/180 lon).
* Obsługa błędów:
    * 503 Service Unavailable: Gdy mapa nie została wczytana.
    * 400 Bad Request: Błędny format danych wejściowych.
    * 404 Not Found: Gdy nie znaleziono połączenia między punktami.

---

Autor: Jakub Mencel