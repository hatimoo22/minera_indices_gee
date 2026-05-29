# -*- coding: utf-8 -*-
"""
Server-side (GEE) mineral index computation.
Supports: ASTER, Sentinel-2, Landsat 5, 7, 8, 9.
ASTER uses collection ASTER/AST_L1T_003 (TOA Radiance, L1T).
Band ratios are scale-invariant so work correctly on radiance data.
"""

def _ratio(img, a, b, name):
    return img.select(a).divide(img.select(b)).rename(name)

def _ndvi_style(img, nir, red, name):
    return img.normalizedDifference([nir, red]).rename(name)

def _sum_ratio(img, num_bands, den_bands, name):
    num = img.select(num_bands[0])
    for b in num_bands[1:]:
        num = num.add(img.select(b))
    den = img.select(den_bands[0])
    for b in den_bands[1:]:
        den = den.add(img.select(b))
    return num.divide(den).rename(name)

# ── ASTER L1T  (ASTER/AST_L1T_003) ──────────────────────────────────────────
# Bands: B01=Green, B02=Red, B3N=NIR, B04-B09=SWIR1-6
# Indices use band ratios -> scale-invariant, valid on TOA radiance

def aster_cloud_mask(image):
    """ASTER L1T has no QA_PIXEL. Use a simple valid-data mask."""
    return image.updateMask(image.select("B01").gt(0))

def _preprocess_aster(image):
    return image  # keep original band names

ASTER_INDICES = {
    "Iron_Oxide":              (lambda i: _ratio(i,"B02","B01","Iron_Oxide"),                    ["B01","B02"],             "Iron Oxide (B02/B01). Ferric iron, hematite, goethite."),
    "Ferrous_Minerals":        (lambda i: _ratio(i,"B05","B04","Ferrous_Minerals"),               ["B04","B05"],             "Ferrous Minerals (B05/B04). Fe2+ in chlorite, pyroxenes."),
    "Ferric_Oxide_Color":      (lambda i: _ratio(i,"B05","B3N","Ferric_Oxide_Color"),             ["B3N","B05"],             "Ferric Oxide Color (B05/B3N). Iron-bearing alteration."),
    "Gossan":                  (lambda i: _ratio(i,"B04","B02","Gossan"),                         ["B02","B04"],             "Gossan (B04/B02). Oxidised gossanous zones."),
    "Clay_Minerals":           (lambda i: _sum_ratio(i,["B05","B07"],["B06"],"Clay_Minerals"),    ["B05","B06","B07"],       "Clay Minerals (B05+B07)/B06. Phyllosilicates."),
    "Alunite_Index":           (lambda i: _ratio(i,"B07","B05","Alunite_Index"),                  ["B05","B07"],             "Alunite (B07/B05). Advanced argillic alteration."),
    "Kaolinite_Index":         (lambda i: _ratio(i,"B04","B05","Kaolinite_Index"),                ["B04","B05"],             "Kaolinite (B04/B05). Kaolinite/dickite."),
    "Muscovite_Index":         (lambda i: _ratio(i,"B07","B06","Muscovite_Index"),                ["B06","B07"],             "Muscovite/Sericite (B07/B06). Phyllic alteration."),
    "Propylitic_Alteration":   (lambda i: _ratio(i,"B05","B08","Propylitic_Alteration"),          ["B05","B08"],             "Propylitic Alteration (B05/B08). Chlorite/epidote zones."),
    "Carbonate_Index":         (lambda i: _ratio(i,"B06","B08","Carbonate_Index"),                ["B06","B08"],             "Carbonate (B06/B08). Calcite, dolomite."),
    "Dolomite_Index":          (lambda i: _sum_ratio(i,["B06","B09"],["B07","B08"],"Dolomite_Index"), ["B06","B07","B08","B09"], "Dolomite (B06+B09)/(B07+B08)."),
    "Silica_Index":            (lambda i: _ratio(i,"B04","B06","Silica_Index"),                   ["B04","B06"],             "Silica (B04/B06). Silicification zones."),
    "NDVI":                    (lambda i: _ndvi_style(i,"B3N","B02","NDVI"),                      ["B02","B3N"],             "NDVI (B3N-B02)/(B3N+B02)."),
}

# ── Landsat 8 / 9 ────────────────────────────────────────────────────────────

def landsat89_cloud_mask(image):
    qa = image.select("QA_PIXEL")
    return image.updateMask(qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0)))

def _preprocess_l89(image):
    optical = image.select("SR_B.").multiply(0.0000275).add(-0.2)
    image = image.addBands(optical, overwrite=True)
    return image.select(["SR_B1","SR_B2","SR_B3","SR_B4","SR_B5","SR_B6","SR_B7"],
                        ["B1",   "B2",   "B3",   "B4",   "B5",   "B6",   "B7"])

LANDSAT89_INDICES = {
    "Iron_Oxide":              (lambda i: _ratio(i,"B4","B2","Iron_Oxide"),             ["B2","B4"],             "Iron Oxide (B4/B2)."),
    "Ferrous_Minerals":        (lambda i: _ratio(i,"B6","B5","Ferrous_Minerals"),        ["B5","B6"],             "Ferrous Minerals (B6/B5)."),
    "Ferric_Oxide":            (lambda i: _ratio(i,"B3","B1","Ferric_Oxide"),            ["B1","B3"],             "Ferric Oxide (B3/B1)."),
    "Gossan":                  (lambda i: _ratio(i,"B5","B6","Gossan"),                  ["B5","B6"],             "Gossan (B5/B6)."),
    "Clay_Minerals":           (lambda i: _ratio(i,"B6","B7","Clay_Minerals"),           ["B6","B7"],             "Clay Minerals (B6/B7)."),
    "Hydrothermal_Alteration": (lambda i: _ratio(i,"B5","B7","Hydrothermal_Alteration"), ["B5","B7"],             "Hydrothermal Alteration (B5/B7)."),
    "Advanced_Argillic":       (lambda i: _sum_ratio(i,["B4","B7"],["B5","B6"],"Advanced_Argillic"), ["B4","B5","B6","B7"], "Advanced Argillic (B4+B7)/(B5+B6)."),
    "Carbonate_Index":         (lambda i: _ratio(i,"B6","B7","Carbonate_Index"),         ["B6","B7"],             "Carbonate (B6/B7)."),
    "Silica_Index":            (lambda i: _sum_ratio(i,["B6","B4"],["B5","B3"],"Silica_Index"), ["B3","B4","B5","B6"], "Silica (B6+B4)/(B5+B3)."),
    "NDVI":                    (lambda i: _ndvi_style(i,"B5","B4","NDVI"),               ["B4","B5"],             "NDVI (B5-B4)/(B5+B4)."),
    "MNDWI":                   (lambda i: _ndvi_style(i,"B3","B6","MNDWI"),              ["B3","B6"],             "MNDWI water mask."),
    "BSI":                     (lambda i: i.select("B6").add(i.select("B4")).subtract(i.select("B5").add(i.select("B2"))).divide(i.select("B6").add(i.select("B4")).add(i.select("B5")).add(i.select("B2"))).rename("BSI"), ["B2","B4","B5","B6"], "Bare Soil Index."),
}

# ── Landsat 5 / 7 ────────────────────────────────────────────────────────────

def landsat57_cloud_mask(image):
    qa = image.select("QA_PIXEL")
    return image.updateMask(qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0)))

def _preprocess_l57(image):
    return image.select(["SR_B1","SR_B2","SR_B3","SR_B4","SR_B5","SR_B7"],
                        ["B1",   "B2",   "B3",   "B4",   "B5",   "B7"])

LANDSAT57_INDICES = {
    "Iron_Oxide":              (lambda i: _ratio(i,"B3","B1","Iron_Oxide"),              ["B1","B3"],             "Iron Oxide (B3/B1)."),
    "Ferrous_Minerals":        (lambda i: _ratio(i,"B5","B4","Ferrous_Minerals"),         ["B4","B5"],             "Ferrous Minerals (B5/B4)."),
    "Clay_Minerals":           (lambda i: _ratio(i,"B5","B7","Clay_Minerals"),            ["B5","B7"],             "Clay Minerals (B5/B7)."),
    "Gossan":                  (lambda i: _ratio(i,"B4","B5","Gossan"),                   ["B4","B5"],             "Gossan (B4/B5)."),
    "Hydrothermal_Alteration": (lambda i: _ratio(i,"B4","B7","Hydrothermal_Alteration"),  ["B4","B7"],             "Hydrothermal Alteration (B4/B7)."),
    "Carbonate_Index":         (lambda i: _ratio(i,"B5","B7","Carbonate_Index"),          ["B5","B7"],             "Carbonate (B5/B7)."),
    "Silica_Index":            (lambda i: _sum_ratio(i,["B5","B3"],["B4","B2"],"Silica_Index"), ["B2","B3","B4","B5"], "Silica (B5+B3)/(B4+B2)."),
    "NDVI":                    (lambda i: _ndvi_style(i,"B4","B3","NDVI"),                ["B3","B4"],             "NDVI (B4-B3)/(B4+B3)."),
    "BSI":                     (lambda i: i.select("B5").add(i.select("B3")).subtract(i.select("B4").add(i.select("B1"))).divide(i.select("B5").add(i.select("B3")).add(i.select("B4")).add(i.select("B1"))).rename("BSI"), ["B1","B3","B4","B5"], "Bare Soil Index."),
}

# ── Sentinel-2 ────────────────────────────────────────────────────────────────

def sentinel2_cloud_mask(image):
    scl = image.select("SCL")
    return image.updateMask(scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)))

def _preprocess_s2(image):
    return image.select(["B2","B3","B4","B5","B6","B7","B8","B8A","B11","B12"]).divide(10000)

SENTINEL2_INDICES = {
    "Iron_Oxide":                (lambda i: _ratio(i,"B4","B2","Iron_Oxide"),                       ["B2","B4"],             "Iron Oxide (B4/B2)."),
    "Ferrous_Minerals":          (lambda i: _ratio(i,"B11","B8","Ferrous_Minerals"),                 ["B8","B11"],            "Ferrous Minerals (B11/B8)."),
    "Ferric_Oxide_Color":        (lambda i: _ratio(i,"B4","B3","Ferric_Oxide_Color"),                ["B3","B4"],             "Ferric Oxide Color (B4/B3)."),
    "Gossan":                    (lambda i: _ratio(i,"B8","B11","Gossan"),                           ["B8","B11"],            "Gossan (B8/B11)."),
    "Clay_Minerals":             (lambda i: _ratio(i,"B11","B12","Clay_Minerals"),                   ["B11","B12"],           "Clay Minerals (B11/B12)."),
    "Clay_Index_2":              (lambda i: _ndvi_style(i,"B8A","B12","Clay_Index_2"),               ["B8A","B12"],           "Clay Index 2 (B8A-B12)/(B8A+B12)."),
    "Hydrothermal_Alteration":   (lambda i: _ratio(i,"B8A","B12","Hydrothermal_Alteration"),         ["B8A","B12"],           "Hydrothermal Alteration (B8A/B12)."),
    "Kaolinite_Group":           (lambda i: _ratio(i,"B11","B8A","Kaolinite_Group"),                 ["B8A","B11"],           "Kaolinite Group (B11/B8A)."),
    "Sericite_Muscovite":        (lambda i: _sum_ratio(i,["B11","B8"],["B12","B8A"],"Sericite_Muscovite"), ["B8","B8A","B11","B12"], "Sericite/Muscovite (B11+B8)/(B12+B8A)."),
    "Alunite_Advanced_Argillic": (lambda i: _sum_ratio(i,["B4","B12"],["B8","B11"],"Alunite_Advanced_Argillic"), ["B4","B8","B11","B12"], "Advanced Argillic/Alunite (B4+B12)/(B8+B11)."),
    "Carbonate_Index":           (lambda i: _ndvi_style(i,"B11","B12","Carbonate_Index"),            ["B11","B12"],           "Carbonate (B11-B12)/(B11+B12)."),
    "Silica_Index":              (lambda i: _sum_ratio(i,["B11","B4"],["B8","B3"],"Silica_Index"),   ["B3","B4","B8","B11"],  "Silica (B11+B4)/(B8+B3)."),
    "NDVI":                      (lambda i: _ndvi_style(i,"B8","B4","NDVI"),                         ["B4","B8"],             "NDVI (B8-B4)/(B8+B4)."),
    "MNDWI":                     (lambda i: _ndvi_style(i,"B3","B11","MNDWI"),                       ["B3","B11"],            "MNDWI water mask."),
    "BSI":                       (lambda i: i.select("B11").add(i.select("B4")).subtract(i.select("B8").add(i.select("B2"))).divide(i.select("B11").add(i.select("B4")).add(i.select("B8")).add(i.select("B2"))).rename("BSI"), ["B2","B4","B8","B11"], "Bare Soil Index."),
    "Red_Edge_Chlorophyll":      (lambda i: _ratio(i,"B7","B5","Red_Edge_Chlorophyll"),              ["B5","B7"],             "Red-Edge Chlorophyll (B7/B5)."),
}

# ── Sensor registry ───────────────────────────────────────────────────────────

SENSORS = {
    "ASTER":      {"collection":"ASTER/AST_L1T_003",               "indices":ASTER_INDICES,     "cloud_mask":aster_cloud_mask,     "preprocess":_preprocess_aster},
    "Sentinel-2": {"collection":"COPERNICUS/S2_SR_HARMONIZED",     "indices":SENTINEL2_INDICES, "cloud_mask":sentinel2_cloud_mask, "preprocess":_preprocess_s2},
    "Landsat 8":  {"collection":"LANDSAT/LC08/C02/T1_L2",          "indices":LANDSAT89_INDICES, "cloud_mask":landsat89_cloud_mask, "preprocess":_preprocess_l89},
    "Landsat 9":  {"collection":"LANDSAT/LC09/C02/T1_L2",          "indices":LANDSAT89_INDICES, "cloud_mask":landsat89_cloud_mask, "preprocess":_preprocess_l89},
    "Landsat 7":  {"collection":"LANDSAT/LE07/C02/T1_L2",          "indices":LANDSAT57_INDICES, "cloud_mask":landsat57_cloud_mask, "preprocess":_preprocess_l57},
    "Landsat 5":  {"collection":"LANDSAT/LT05/C02/T1_L2",          "indices":LANDSAT57_INDICES, "cloud_mask":landsat57_cloud_mask, "preprocess":_preprocess_l57},
}

# ── Compute ───────────────────────────────────────────────────────────────────

def build_composite(sensor_name, aoi, start_date, end_date, cloud_masking=True):
    import ee
    cfg = SENSORS[sensor_name]
    col = ee.ImageCollection(cfg["collection"]).filterBounds(aoi).filterDate(start_date, end_date)
    def process(img):
        if cloud_masking:
            img = cfg["cloud_mask"](img)
        return cfg["preprocess"](img)
    return col.map(process).median().clip(aoi)

def compute_indices(composite, sensor_name, selected_index_names):
    cfg = SENSORS[sensor_name]
    results = []
    for name in selected_index_names:
        if name not in cfg["indices"]:
            continue
        func, _, _ = cfg["indices"][name]
        results.append((name, func(composite)))
    return results
