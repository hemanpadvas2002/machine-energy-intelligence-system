import logging
import threading
import time
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter


logger = logging.getLogger(__name__)

try:
    import matlab.engine
    import matlab
except ImportError:  # pragma: no cover - depends on local MATLAB install
    matlab = None
    matlab_engine = None
else:  # pragma: no cover - depends on local MATLAB install
    matlab_engine = matlab.engine


ANALYTICS_CACHE_TTL_SECONDS = 3.0


@dataclass
class AnalyticsResult:
    timestamps: list[str]
    raw: list[float]
    filtered: list[float]
    smoothed: list[float]
    fft_frequency: list[float]
    fft_magnitude: list[float]
    engine: str

    def to_dict(self):
        return {
            "timestamps": self.timestamps,
            "values": self.raw,
            "filtered": self.filtered,
            "smoothed": self.smoothed,
            "fft_frequency": self.fft_frequency,
            "fft": self.fft_magnitude,
            "engine": self.engine,
        }


class MatlabAnalyticsService:
    def __init__(self):
        self._engine = None
        self._engine_lock = threading.Lock()
        self._cache = {}
        self._cache_lock = threading.Lock()

    def _get_engine(self):
        if matlab_engine is None:
            return None
        with self._engine_lock:
            if self._engine is None:
                self._engine = matlab_engine.start_matlab()
            return self._engine

    def process_series(self, timestamps, values, sample_interval=1.0, cache_key=None):
        if cache_key:
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached

        if not values:
            result = AnalyticsResult(
                timestamps=timestamps,
                raw=[],
                filtered=[],
                smoothed=[],
                fft_frequency=[],
                fft_magnitude=[],
                engine="empty",
            )
            if cache_key:
                self._write_cache(cache_key, result)
            return result

        try:
            engine = self._get_engine()
            result = self._process_with_matlab(engine, timestamps, values, sample_interval) if engine else None
        except Exception as exc:  # pragma: no cover - depends on local MATLAB install
            logger.warning("MATLAB analytics failed, using SciPy fallback: %s", exc)
            result = None

        if result is None:
            result = self._process_with_scipy(timestamps, values, sample_interval)

        if cache_key:
            self._write_cache(cache_key, result)
        return result

    def _read_cache(self, cache_key):
        with self._cache_lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
            timestamp, payload = entry
            if time.time() - timestamp <= ANALYTICS_CACHE_TTL_SECONDS:
                return payload
            self._cache.pop(cache_key, None)
            return None

    def _write_cache(self, cache_key, payload):
        with self._cache_lock:
            self._cache[cache_key] = (time.time(), payload)

    def _process_with_matlab(self, engine, timestamps, values, sample_interval):  # pragma: no cover
        matlab_values = matlab.double([float(value) for value in values])
        n = len(values)
        window = max(5, min(n if n % 2 == 1 else n - 1, 9))
        poly = 3 if window >= 5 else 2

        filtered = list(engine.sgolayfilt(matlab_values, poly, window))
        smoothed = list(engine.smoothdata(matlab_values, "gaussian", max(3, window)))
        fft_complex = np.array(engine.fft(matlab_values)).astype(complex)
        fft_magnitude = np.abs(fft_complex[: n // 2]).tolist()
        fft_frequency = np.fft.rfftfreq(n, d=sample_interval).tolist()[: len(fft_magnitude)]

        return AnalyticsResult(
            timestamps=timestamps,
            raw=[float(value) for value in values],
            filtered=[float(value) for value in filtered],
            smoothed=[float(value) for value in smoothed],
            fft_frequency=[float(value) for value in fft_frequency],
            fft_magnitude=[float(value) for value in fft_magnitude],
            engine="matlab",
        )

    def _process_with_scipy(self, timestamps, values, sample_interval):
        raw = np.array(values, dtype=float)
        n = len(raw)
        if n < 3:
            filtered = raw.copy()
            smoothed = raw.copy()
        else:
            window = min(9, n if n % 2 == 1 else n - 1)
            if window < 3:
                window = 3
            poly = 3 if window >= 5 else 2
            filtered = savgol_filter(raw, window_length=window, polyorder=poly, mode="interp")
            smoothed = gaussian_filter1d(raw, sigma=1.2)

        fft_values = np.abs(np.fft.rfft(raw))
        fft_frequency = np.fft.rfftfreq(n, d=sample_interval)

        return AnalyticsResult(
            timestamps=timestamps,
            raw=raw.astype(float).tolist(),
            filtered=np.asarray(filtered).astype(float).tolist(),
            smoothed=np.asarray(smoothed).astype(float).tolist(),
            fft_frequency=fft_frequency.astype(float).tolist(),
            fft_magnitude=fft_values.astype(float).tolist(),
            engine="scipy-fallback",
        )


@lru_cache(maxsize=1)
def get_matlab_analytics_service():
    return MatlabAnalyticsService()
