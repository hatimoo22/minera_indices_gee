# -*- coding: utf-8 -*-
"""
Background thread: compute GEE indices and download as GeoTIFF.
"""

import os
import tempfile
import traceback

from qgis.PyQt.QtCore import QThread, pyqtSignal

from .gee_indices import build_composite, compute_indices, SENSORS


class ExportWorker(QThread):
    progress  = pyqtSignal(int)        # 0-100
    log       = pyqtSignal(str)
    layer_ready = pyqtSignal(str, str) # (index_name, file_path)
    finished  = pyqtSignal(bool, str)  # (success, summary)

    def __init__(self, sensor, aoi_coords, start_date, end_date,
                 selected_indices, output_folder, scale, cloud_masking,
                 project_id=None, parent=None):
        super().__init__(parent)
        self.sensor = sensor
        self.aoi_coords = aoi_coords      # list of [lon, lat] pairs
        self.start_date = start_date
        self.end_date = end_date
        self.selected_indices = selected_indices
        self.output_folder = output_folder
        self.scale = scale                # GSD in metres
        self.cloud_masking = cloud_masking
        self.project_id = project_id

    def run(self):
        try:
            self._run()
        except Exception:
            self.finished.emit(False, traceback.format_exc())

    def _run(self):
        import ee
        from .gee_auth import initialize, is_initialized

        if not is_initialized():
            ok, msg = initialize(self.project_id)
            if not ok:
                self.finished.emit(False, msg)
                return

        self.log.emit("Building AOI geometry...")
        aoi = ee.Geometry.Polygon(self.aoi_coords)

        self.log.emit(
            f"Fetching {self.sensor} composite "
            f"{self.start_date} to {self.end_date}...")
        composite = build_composite(
            self.sensor, aoi,
            self.start_date, self.end_date,
            cloud_masking=self.cloud_masking,
        )

        index_list = compute_indices(composite, self.sensor,
                                     self.selected_indices)
        n = len(index_list)
        if n == 0:
            self.finished.emit(False, "No indices to compute.")
            return

        os.makedirs(self.output_folder, exist_ok=True)
        ok_count = 0

        for i, (name, idx_img) in enumerate(index_list):
            self.log.emit(f"\n[{i+1}/{n}] Downloading {name}...")
            try:
                out_path = os.path.join(self.output_folder, f"{name}.tif")
                url = idx_img.getDownloadURL({
                    "name":   name,
                    "scale":  self.scale,
                    "region": aoi,
                    "format": "GEO_TIFF",
                    "filePerBand": False,
                })
                self._download(url, out_path)
                self.log.emit(f"  Saved: {out_path}")
                self.layer_ready.emit(name, out_path)
                ok_count += 1
            except Exception as e:
                self.log.emit(f"  ERROR: {e}")

            self.progress.emit(int((i + 1) / n * 100))

        summary = (f"Done: {ok_count}/{n} indices exported to:\n"
                   f"{self.output_folder}")
        self.finished.emit(True, summary)

    @staticmethod
    def _download(url, out_path):
        """Download GEE getDownloadURL response to file."""
        import urllib.request
        with urllib.request.urlopen(url, timeout=600) as resp, \
             open(out_path, "wb") as f:
            chunk = 1024 * 256  # 256 KB
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                f.write(data)
