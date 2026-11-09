"""Generate docs/images/architecture.excalidraw (editable source of the README diagram).

Run: python scripts/build_architecture_diagram.py
Tool logos are embedded from docs/images/icons/. Open the output at
https://excalidraw.com (File > Open) to edit, then re-export docs/images/architecture.png.
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
from pathlib import Path

IMAGES = Path(__file__).resolve().parents[1] / "docs" / "images"
ICONS = IMAGES / "icons"
OUT = IMAGES / "architecture.excalidraw"
MIME = {".svg": "image/svg+xml", ".png": "image/png"}
ICON = 34  # icon edge length in px
TEXT_PAD = 8

random.seed(42)
elements: list[dict] = []
files: dict[str, dict] = {}
_ids = iter(range(1, 10_000))


def _base(kind: str, x: float, y: float, w: float, h: float, **kw) -> dict:
    el = {
        "id": f"{kind}-{next(_ids)}",
        "type": kind,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": kw.get("stroke", "#1e1e1e"),
        "backgroundColor": kw.get("bg", "transparent"),
        "fillStyle": "solid",
        "strokeWidth": kw.get("sw", 2),
        "strokeStyle": kw.get("style", "solid"),
        "roughness": 1,
        "opacity": kw.get("opacity", 100),
        "groupIds": kw.get("groups", []),
        "frameId": None,
        "roundness": kw.get("roundness", {"type": 3}),
        "seed": random.randint(1, 2**31),
        "version": 1,
        "versionNonce": random.randint(1, 2**31),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }
    elements.append(el)
    return el


def image(name: str, x: float, y: float, size: float = ICON, groups=None) -> dict:
    path = next(ICONS.glob(f"{name}.*"))
    data = path.read_bytes()
    file_id = hashlib.sha1(data).hexdigest()
    files[file_id] = {
        "mimeType": MIME[path.suffix],
        "id": file_id,
        "dataURL": f"data:{MIME[path.suffix]};base64,"
        + base64.b64encode(data).decode(),
        "created": 1,
    }
    el = _base("image", x, y, size, size, roundness=None, groups=groups or [], sw=1)
    el.update(fileId=file_id, status="saved", scale=[1, 1], crop=None)
    return el


def text(
    x, y, s, size=16, color="#1e1e1e", align="left", container=None, valign="middle"
):
    lines = s.split("\n")
    width = max(len(line) for line in lines) * size * 0.55
    height = len(lines) * size * 1.25
    el = _base("text", x, y, width, height, stroke=color, roundness=None)
    el.update(
        text=s,
        originalText=s,
        fontSize=size,
        fontFamily=5,  # Excalifont
        textAlign=align,
        verticalAlign=valign if container else "top",
        containerId=container["id"] if container else None,
        autoResize=True,
        lineHeight=1.25,
    )
    if container:
        container["boundElements"].append({"type": "text", "id": el["id"]})
        el["x"] = container["x"] + 5
        el["width"] = container["width"] - 10
        if valign == "bottom":
            el["y"] = container["y"] + container["height"] - height - TEXT_PAD
        else:
            el["y"] = container["y"] + (container["height"] - height) / 2
    return el


def box(x, y, w, h, label, bg, icons=(), size=16):
    """Rounded box; tool logos sit centred on top, the label below them."""
    group = [f"group-{next(_ids)}"] if icons else []
    r = _base("rectangle", x, y, w, h, bg=bg, groups=group)
    text(
        0,
        0,
        label,
        size=size,
        align="center",
        container=r,
        valign="bottom" if icons else "middle",
    )
    gap = 10
    total = len(icons) * ICON + (len(icons) - 1) * gap
    for i, name in enumerate(icons):
        image(name, x + (w - total) / 2 + i * (ICON + gap), y + 10, groups=group)
    return r


def zone(x, y, w, h, title, color, icons=()):
    _base(
        "rectangle",
        x,
        y,
        w,
        h,
        bg=color,
        stroke="#868e96",
        style="dashed",
        sw=1,
        opacity=60,
    )
    offset = 0
    for name in icons:
        image(name, x + 10 + offset, y + 6, size=24)
        offset += 30
    text(x + 12 + offset, y + 8, title, size=18, color="#495057")


def _anchor(el, side):
    x, y, w, h = el["x"], el["y"], el["width"], el["height"]
    return {
        "right": (x + w, y + h / 2),
        "left": (x, y + h / 2),
        "top": (x + w / 2, y),
        "bottom": (x + w / 2, y + h),
    }[side]


def arrow(
    src, dst, s_side="right", d_side="left", label=None, dashed=False, color="#1e1e1e"
):
    sx, sy = _anchor(src, s_side)
    ex, ey = _anchor(dst, d_side)
    a = _base(
        "arrow",
        sx,
        sy,
        abs(ex - sx),
        abs(ey - sy),
        stroke=color,
        style="dashed" if dashed else "solid",
        roundness={"type": 2},
    )
    a.update(
        points=[[0, 0], [ex - sx, ey - sy]],
        lastCommittedPoint=None,
        startBinding={"elementId": src["id"], "focus": 0, "gap": 4},
        endBinding={"elementId": dst["id"], "focus": 0, "gap": 4},
        startArrowhead=None,
        endArrowhead="arrow",
        elbowed=False,
    )
    src["boundElements"].append({"type": "arrow", "id": a["id"]})
    dst["boundElements"].append({"type": "arrow", "id": a["id"]})
    if label:
        # Excalidraw always renders arrow-bound labels at the arrow midpoint.
        t = text(0, 0, label, size=14, align="center", container=a)
        t["width"] = len(label) * 14 * 0.55
        t["x"] = sx + (ex - sx) / 2 - t["width"] / 2
        t["y"] = sy + (ey - sy) / 2 - 9
    return a


# --- Title -------------------------------------------------------------------
text(20, -40, "Web Analytics Engineering — Xóm Ecom Tracker", size=28)

# --- Zones -------------------------------------------------------------------
zone(270, 20, 1180, 160, "Orchestration", "#f8f0fc")
zone(20, 200, 220, 230, "Source", "#f1f3f5")
zone(270, 200, 230, 450, "Ingestion (Python)", "#e7f5ff")
zone(
    530,
    200,
    920,
    370,
    "Supabase PostgreSQL · dbt medallion",
    "#ebfbee",
    icons=("supabase", "postgresql", "dbt"),
)
zone(1480, 200, 200, 230, "Serving", "#fff4e6")
zone(20, 680, 970, 180, "CI/CD & Metadata", "#f3f0ff")
zone(1010, 600, 670, 260, "Observability", "#fff9db")

# --- Orchestration -----------------------------------------------------------
airflow = box(
    690,
    50,
    360,
    110,
    "Airflow + Astronomer Cosmos\nDAG web_analytics_medallion · daily",
    "#eebefa",
    icons=("airflow", "cosmos"),
)

# --- Source & ingestion ------------------------------------------------------
LAYER_H = 140
mssql = box(
    40,
    255,
    180,
    LAYER_H,
    "SQL Server\nxomdata_dataset\n.web_analytics",
    "#dee2e6",
    icons=("sqlserver",),
)
extract = box(
    290,
    255,
    190,
    LAYER_H,
    "Full extraction\nread-only, keyset\nbatches ≤ 10k rows",
    "#a5d8ff",
    icons=("python",),
)
raw = box(
    290,
    480,
    170,
    LAYER_H,
    "Supabase Storage\nS3 · gzip JSONL\n+ complete marker",
    "#a5d8ff",
    icons=("supabase",),
)

# --- Warehouse ---------------------------------------------------------------
landing = box(
    550,
    255,
    150,
    LAYER_H,
    "Landing\n6 tables\natomic publish",
    "#ffffff",
    icons=("postgresql",),
)
bronze = box(
    730,
    255,
    150,
    LAYER_H,
    "Bronze\n6 brz_* views\nJSON envelopes",
    "#ffd8a8",
    icons=("dbt",),
)
silver = box(
    910,
    255,
    150,
    LAYER_H,
    "Silver\n6 slv_* tables\ntyped entities",
    "#e9ecef",
    icons=("dbt",),
)
gold = box(
    1090,
    255,
    150,
    LAYER_H,
    "Gold\n12 domain\nfacts & dims",
    "#ffec99",
    icons=("dbt",),
)
platinum = box(
    1270,
    255,
    160,
    LAYER_H,
    "Platinum\n6 business\ndata marts",
    "#d0bfff",
    icons=("dbt",),
)
snapshot = box(1030, 440, 150, 100, "Product SCD2\nsnapshot", "#c3fae8", icons=("dbt",))

# --- Serving -----------------------------------------------------------------
grafana = box(
    1500,
    255,
    160,
    LAYER_H,
    "Grafana\nbusiness + ops\ndashboards",
    "#ffc078",
    icons=("grafana",),
)

# --- CI/CD -------------------------------------------------------------------
CI_Y, CI_H = 725, 110
ci = box(
    40,
    CI_Y,
    200,
    CI_H,
    "CI\nlint · tests · dbt build",
    "#e5dbff",
    icons=("githubactions",),
)
cd = box(
    300,
    CI_Y,
    200,
    CI_H,
    "CD (slim)\nstate:modified+ --defer",
    "#e5dbff",
    icons=("githubactions",),
)
artifacts = box(
    540,
    CI_Y,
    200,
    CI_H,
    "S3: versioned\ndbt artifacts",
    "#e5dbff",
    icons=("supabase",),
)
omd = box(
    780,
    CI_Y,
    190,
    CI_H,
    "OpenMetadata\ncatalog & lineage",
    "#e5dbff",
    icons=("openmetadata",),
)

# --- Observability -----------------------------------------------------------
OBS_H = 95
statsd = box(
    1030, 645, 180, OBS_H, "Airflow StatsD\nmetrics", "#fff3bf", icons=("airflow",)
)
prom = box(1260, 645, 180, OBS_H, "Prometheus", "#fff3bf", icons=("prometheus",))
logs = box(1030, 755, 180, OBS_H, "Airflow log files", "#fff3bf", icons=("airflow",))
alloy = box(1260, 755, 180, OBS_H, "Grafana Alloy", "#fff3bf", icons=("alloy",))
loki = box(1480, 755, 180, OBS_H, "Loki", "#fff3bf", icons=("loki",))

# --- Data flow ---------------------------------------------------------------
arrow(mssql, extract)
arrow(extract, raw, "bottom", "top", label="archive")
arrow(extract, landing)
text(493, 298, "publish", size=14)
arrow(landing, bronze)
arrow(bronze, silver)
arrow(silver, gold)
arrow(gold, platinum)
arrow(silver, snapshot, "bottom", "left")
arrow(snapshot, gold, "right", "bottom")
arrow(platinum, grafana)

# --- Control flow ------------------------------------------------------------
purple = "#9c36b5"
arrow(airflow, extract, "left", "top", label="ingest", dashed=True, color=purple)
arrow(airflow, gold, "bottom", "top", label="dbt run/test", dashed=True, color=purple)

arrow(ci, cd)
arrow(cd, artifacts)
arrow(artifacts, omd)
arrow(cd, landing, "top", "bottom", label="deploy", dashed=True, color=purple)

arrow(statsd, prom)
arrow(prom, grafana, "right", "bottom")
arrow(logs, alloy)
arrow(alloy, loki)
arrow(loki, grafana, "top", "bottom")

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"gridSize": 20, "viewBackgroundColor": "#ffffff"},
    "files": files,
}
OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {OUT}")
