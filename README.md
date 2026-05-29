# Minera Indices GEE - QGIS Plugin

Compute mineral spectral indices **directly from Google Earth Engine** — no local downloads of raw imagery needed. Supports ASTER, Landsat 5/7/8/9, and Sentinel-2 with automatic cloud masking.

## Features

- Connect to GEE from within QGIS
- Draw AOI rectangle interactively on the QGIS canvas
- Pick sensor, date range, and spatial resolution
- Auto cloud masking (QA band / SCL)
- Server-side median composite
- Download each index as a GeoTIFF, auto-loaded into QGIS

## Supported Sensors & Indices

| Sensor | GEE Collection | Indices |
|---|---|---|
| Sentinel-2 | COPERNICUS/S2_SR_HARMONIZED | 16 |
| Landsat 8 | LANDSAT/LC08/C02/T1_L2 | 13 |
| Landsat 9 | LANDSAT/LC09/C02/T1_L2 | 13 |
| Landsat 7 | LANDSAT/LE07/C02/T1_L2 | 9 |
| Landsat 5 | LANDSAT/LT05/C02/T1_L2 | 9 |
| ASTER | ASTER/AST_09T_003 | 13 |

Indices include: Iron Oxide, Ferrous Minerals, Ferric Oxide, Gossan, Clay Minerals, Alunite, Kaolinite, Sericite/Muscovite, Propylitic Alteration, Carbonate, Dolomite, Silica, NDVI, MNDWI, BSI, and more.

## Requirements

- QGIS 3.0+
- A Google Earth Engine account (free at [earthengine.google.com](https://earthengine.google.com))
- `earthengine-api` Python package

### Installing earthengine-api on Windows (OSGeo4W)

Open the **OSGeo4W Shell** as Administrator and run:

```
pip install earthengine-api
```

Then restart QGIS.

## Usage

1. Open **Raster > Minera Indices GEE**
2. Enter your GEE Cloud Project ID (or leave blank for legacy accounts)
3. Click **Authenticate** (opens browser on first use)
4. Click **Connect / Test** to verify the connection
5. Select sensor and date range
6. Click **Draw Rectangle on Map** and drag your AOI
7. Choose an output folder
8. Select indices and click **Run**

Results are saved as GeoTIFF files and automatically added to the QGIS project.

## License

GNU General Public License v2 or later

## Author

Hatim - hatimoo22@live.com

## Issues

https://github.com/hatimoo22/minera_indices/issues
