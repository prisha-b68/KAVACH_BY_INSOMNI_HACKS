from __future__ import annotations

from io import BytesIO
import pandas as pd


def read_csv_upload(uploaded_file) -> pd.DataFrame:
    """Read a user CSV safely, trying common Indian/Excel encodings."""
    raw = uploaded_file.getvalue()
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(BytesIO(raw), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return pd.read_csv(BytesIO(raw))


def find_column(columns, candidates):
    lookup = {str(c).strip().lower().replace(" ", "_"): c for c in columns}
    for candidate in candidates:
        key = candidate.strip().lower().replace(" ", "_")
        if key in lookup:
            return lookup[key]
    return None


def valid_coordinate_frame(df: pd.DataFrame, lat_col: str, lon_col: str) -> pd.DataFrame:
    out = df.copy()
    out["_latitude"] = pd.to_numeric(out[lat_col], errors="coerce")
    out["_longitude"] = pd.to_numeric(out[lon_col], errors="coerce")
    out = out.dropna(subset=["_latitude", "_longitude"])
    return out[out["_latitude"].between(-90, 90) & out["_longitude"].between(-180, 180)]
