# Emergency Healthcare Access in Peru

## What does the project do?

This project builds a complete geospatial analytics pipeline in Python to measure and visualize **emergency healthcare access inequality across Peru's 1,873 districts**. It combines four public datasets — health facilities, emergency care activity, populated centers, and district boundaries — to produce district-level access scores, static charts, choropleth maps, and an interactive Streamlit web application.

---

## What is the main analytical goal?

The goal is to identify which Peruvian districts are most underserved in terms of emergency healthcare access, and to understand **where distance makes access worse than it appears on paper**. To do this, two complementary metrics are constructed and compared:

- **Baseline score**: measures pure supply — how many facilities and beds exist relative to the number of populated centers in each district.
- **Alternative score**: same supply indicators but penalized by the average distance from populated centers to the nearest health facility.

The difference between both scores reveals districts where facilities technically exist but remain physically far from the communities that need them.

---

## What datasets were used?

| Dataset | Source | Records | Key fields |
|---|---|---|---|
| IPRESS Health Facilities | MINSA / datosabiertos.gob.pe | 20,805 active facilities | UBIGEO, coordinates, category, beds |
| District Boundaries | d2cml-ai GitHub (IGN) | 1,873 districts | Polygon geometry, UBIGEO |
| Populated Centers (CCPP) | IGN / datosabiertos.gob.pe | 136,587 centers | Point geometry, district codes |
| Emergency Production by IPRESS (ConsultaC1) | SUSALUD | 2,096,321 rows (2015–2026) | UBIGEO, year, attendances |

---

## How were the data cleaned?

The cleaning pipeline (`src/cleaning.py`) addresses the following issues:

- **Column normalization**: all column names were lowercased, stripped of accents, and standardized with underscores.
- **Swapped coordinates in IPRESS**: the `NORTE` column contained longitude values and `ESTE` contained latitude values — these were corrected before building the GeoDataFrame.
- **Split attendance columns in ConsultaC1**: files from 2018 onward stored totals in a different column (`nu_total_atendidos`) instead of `nro_total_atenciones`. Both columns were merged using the alternative as a fallback when the primary was missing.
- **UBIGEO zero-padding**: district codes were standardized to a 6-digit zero-padded string (e.g. `"150"` → `"000150"`) for consistent joins across all datasets.
- **CCPP spatial join**: populated center district codes were unreliable as text fields, so district assignment was done via point-in-polygon spatial join instead of UBIGEO matching.
- **Active facilities only**: IPRESS records with status other than `"ACTIVADO"` were excluded.

---

## How were the district-level metrics constructed?

The metrics pipeline (`src/metrics.py`) follows four steps:

**1. Aggregation**
- IPRESS facilities and beds are counted per district using a spatial join.
- Populated centers are counted per district and their average/maximum distance to the nearest IPRESS is computed using `sjoin_nearest` in UTM projection (EPSG:32718).
- Emergency attendances are summed per district across all available years.

**2. Baseline score**
Measures supply relative to demand (number of populated centers):

```
baseline = 0.6 × normalize(facilities / communities)
         + 0.4 × normalize(beds / communities)
```

Scaled to 0–100. Higher = better supply.

**3. Alternative score**
Same as baseline but penalized by average travel distance:

```
alternative = 0.6 × normalize(facilities / (communities × (1 + avg_km)))
            + 0.4 × normalize(beds / (communities × (1 + avg_km)))
```

A district with facilities 30 km away scores much lower than one with the same number of facilities 2 km away.

**4. Score difference**
```
score_diff = baseline_score − alternative_score
```
A high positive value means the district appears well-served by facility count alone, but distance significantly reduces real access.

All scores use min-max normalization applied across all 1,873 districts.

---

## How to install the dependencies?

Make sure you have Python 3.9 or higher installed. Then run:

```bash
pip install -r requirements.txt
```

The main libraries used are: `geopandas`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `folium`, `streamlit`, `streamlit-folium`, and `mapclassify`.

---

## How to run the processing pipeline?

Download the four datasets and place them in `data/raw/` following the structure below:

```
data/raw/
├── IPRESS.csv
├── DISTRITOS.shp  (+ .dbf, .prj, .shx, .cpg)
├── CCPP/
│   └── CCPP_IGN100K.shp  (+ companion files)
└── ConsultaC1_*.csv  (one file per year, 2015–2026)
```

Then run the full pipeline from the project root:

```python
from src.data_loader import load_ipress, load_distritos, load_ccpp, load_emergencias
from src.cleaning import clean_ipress, clean_distritos, clean_ccpp, clean_emergencias, save_processed
from src.geospatial import (build_ipress_gdf, sjoin_to_distritos,
    compute_nearest_ipress_distance, aggregate_ipress_by_district,
    aggregate_ccpp_by_district, aggregate_emergencias_by_district)
from src.metrics import compute_metrics
from src.visualization import generate_all

ipress    = clean_ipress(load_ipress())
distritos = clean_distritos(load_distritos())
ccpp      = clean_ccpp(load_ccpp())
emerg     = clean_emergencias(load_emergencias())

save_processed(ipress, distritos, ccpp, emerg)

ipress_gdf = build_ipress_gdf(ipress)
ipress_gdf = sjoin_to_distritos(ipress_gdf, distritos)
ccpp_gdf   = sjoin_to_distritos(ccpp, distritos)
ccpp_dist  = compute_nearest_ipress_distance(ccpp_gdf, ipress_gdf)

agg_ipress = aggregate_ipress_by_district(ipress_gdf)
agg_ccpp   = aggregate_ccpp_by_district(ccpp_dist)
agg_emerg  = aggregate_emergencias_by_district(emerg)

metrics = compute_metrics(agg_ipress, agg_ccpp, agg_emerg, distritos)
generate_all(metrics, distritos)
```

Outputs are saved to `data/processed/`, `output/figures/`, and `output/tables/`.

---

## How to run the Streamlit app?

```bash
streamlit run app.py
```

Then open your browser at **http://localhost:8501**.

The app has four tabs:
1. **Data & Methodology** — problem statement, data sources, cleaning decisions, limitations
2. **Static Analysis** — charts with written interpretations
3. **GeoSpatial Results** — choropleth maps and filterable district table
4. **Interactive Exploration** — Folium map with hover tooltips and baseline vs alternative comparison

---

## What are the main findings?

- **Access is highly concentrated in urban areas**: Lima and other large cities account for the vast majority of both facility supply and recorded emergency attendances. Lima's baseline score (100) is roughly 160 times the national median (0.08).
- **Many rural districts have zero registered facilities**: districts in Huancavelica, Cajamarca, Arequipa, and Puno score zero on the baseline and have average distances to the nearest IPRESS exceeding 20–33 km.
- **Distance substantially worsens access in some districts**: the score difference map reveals districts — particularly in Puno and Madre de Dios — where facilities technically exist but communities must travel long distances to reach them, making the real access situation much worse than supply numbers suggest.
- **Underreporting is geographically uneven**: only 946 of 1,873 districts appear in the SUSALUD emergency production data for 2023, meaning large parts of rural Peru are invisible in administrative records — itself a signal of weak institutional reach.

---

## What are the main limitations?

- **Underreporting**: SUSALUD only captures facilities that actively submit data. Districts may have facilities that are not counted in the emergency production dataset.
- **No population data**: the number of populated centers is used as a proxy for population pressure, which does not reflect actual headcount or population density.
- **Straight-line distances**: distances between populated centers and facilities are computed as the crow flies, not along actual roads. Real travel times in mountainous or jungle areas may be far longer.
- **Static facility snapshot**: the IPRESS dataset reflects current registration status. Historical openings, closures, or changes in service level are not accounted for.
- **Score sensitivity**: both metrics use min-max normalization, which means the scores are relative to the current set of districts. Adding or removing districts would change all scores.
