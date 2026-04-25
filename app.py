import geopandas as gpd
import pandas as pd
import streamlit as st
from pathlib import Path
import folium
from streamlit_folium import st_folium

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Emergency Access in Peru",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Emergency Healthcare Access in Peru")
st.markdown("District-level geospatial analysis of emergency service accessibility across Peru.")

# ── data loading (cached so it only runs once) ────────────────────────────────
@st.cache_data
def load_metrics():
    return pd.read_csv("output/tables/district_metrics.csv", dtype={"ubigeo": str})

@st.cache_resource
def load_geo_metrics():
    metrics   = load_metrics()
    distritos = gpd.read_file("data/raw/DISTRITOS.shp")
    distritos.columns = [c.lower() for c in distritos.columns]
    distritos["ubigeo"] = distritos["iddist"].astype(str).str.zfill(6)
    return distritos.merge(metrics, on="ubigeo", how="left")

@st.cache_data
def load_ipress_points():
    df = pd.read_csv("data/processed/ipress_clean.csv", dtype={"ubigeo": str})
    return df.dropna(subset=["lat", "lon"])

# ── tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Data & Methodology",
    "📊 Static Analysis",
    "🗺️ GeoSpatial Results",
    "🔍 Interactive Exploration",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DATA & METHODOLOGY
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("Problem Statement")
    st.markdown("""
    Emergency healthcare access is unequally distributed across Peru's 1,873 districts.
    Rural and remote districts often have few or no IPRESS (health facilities) nearby,
    forcing populations to travel long distances during medical emergencies.

    This project quantifies that inequality using four public datasets and two complementary
    access metrics — a **baseline supply score** and a **distance-penalized alternative score** —
    to identify the most underserved districts and understand where distance makes access worse.
    """)

    st.header("Data Sources")
    sources = pd.DataFrame({
        "Dataset": [
            "IPRESS Health Facilities",
            "District Boundaries (DISTRITOS)",
            "Populated Centers (CCPP)",
            "Emergency Production by IPRESS (ConsultaC1)",
        ],
        "Source": ["MINSA / datosabiertos.gob.pe", "d2cml-ai GitHub", "IGN / datosabiertos.gob.pe", "SUSALUD"],
        "Records": ["20,805 active facilities", "1,873 districts", "136,587 populated centers", "2,096,321 rows (2015–2026)"],
        "Key fields": ["UBIGEO, lat/lon, category, beds", "Polygon geometry, UBIGEO", "Point geometry, district codes", "UBIGEO, year, attendances"],
    })
    st.dataframe(sources, use_container_width=True, hide_index=True)

    st.header("Cleaning Decisions")
    st.markdown("""
    | Issue | Decision |
    |---|---|
    | IPRESS coordinates were **swapped** (NORTE held longitude, ESTE held latitude) | Corrected column assignment before building GeoDataFrame |
    | Newer ConsultaC1 files (2018+) stored totals in `nu_total_atendidos` instead of `nro_total_atenciones` | Merged both columns, filling NaN from the alternative |
    | 963 rows with `atenciones = 0` but `atendidos > 0` | Kept as-is — data entry issue in source, documented as limitation |
    | CCPP UBIGEO could not be reliably derived from text columns | Used **spatial join** (point-in-polygon) to assign districts instead |
    | Several districts report very low annual attendances (< 10) | Retained — reflects genuine underreporting, not a processing error |
    """)

    st.header("Methodology")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Baseline Score")
        st.markdown("""
        Measures **pure supply**: how many facilities and beds exist
        relative to the number of populated centers in each district.

        ```
        score = 0.6 × norm(facilities / communities)
              + 0.4 × norm(beds / communities)
        ```
        Scaled to 0–100. Higher = better supply.
        """)
    with col2:
        st.subheader("Alternative Score (Distance-Penalized)")
        st.markdown("""
        Same supply indicators but **penalized by the average distance**
        from populated centers to the nearest IPRESS.

        ```
        score = 0.6 × norm(facilities / (communities × (1 + avg_km)))
              + 0.4 × norm(beds / (communities × (1 + avg_km)))
        ```
        A district with facilities 30 km away scores much lower than
        one with the same number of facilities 2 km away.
        """)

    st.header("Limitations")
    st.markdown("""
    - **Underreporting**: SUSALUD only captures facilities that actively submit data. Districts may have facilities that are not counted.
    - **No population data**: we use number of populated centers as a proxy for population pressure, which may not reflect actual headcount.
    - **Static snapshot**: IPRESS data reflects current facility status; historical openings/closures are not accounted for in the supply score.
    - **Distance is straight-line**: actual travel time along roads is not modelled.
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — STATIC ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    metrics = load_metrics()

    st.header("Static Analysis")
    st.markdown("""
    The three chart pairs below were selected to answer the four analytical questions progressively:
    first by identifying who is underserved, then by isolating the role of distance,
    and finally by comparing demand against physical access constraints.
    Bar charts were chosen for ranking comparisons (easy to read top/bottom lists),
    a scatter plot for showing the relationship between two continuous scores across all districts,
    and histograms for understanding distributional shape rather than just averages.
    """)

    # --- row 1: underserved / served
    st.subheader("Which districts are most and least served?")
    c1, c2 = st.columns(2)
    with c1:
        st.image("output/figures/chart_top_underserved.png", use_container_width=True)
        st.caption(
            "Districts with zero supply score, ranked by distance to the nearest IPRESS. "
            "Red bars indicate no facilities registered within the district."
        )
    with c2:
        st.image("output/figures/chart_top_served.png", use_container_width=True)
        st.caption(
            "Districts with the highest baseline score are concentrated in Lima and other large urban centres, "
            "reflecting the strong urban concentration of health infrastructure."
        )

    st.markdown("""
    **Why these charts:** Bar charts make it immediately clear which districts sit at the extremes.
    Showing both ends (most and least served) in one view allows direct comparison of the urban-rural gap.
    """)
    st.divider()

    # --- row 2: baseline vs alternative + score diff
    st.subheader("How does distance change the picture?")
    c1, c2 = st.columns(2)
    with c1:
        st.image("output/figures/chart_baseline_vs_alternative.png", use_container_width=True)
        st.caption(
            "Each dot is one district. Points **below** the dashed line score worse once distance is factored in — "
            "their facilities exist but are far from communities. Colour shows average distance to nearest IPRESS."
        )
    with c2:
        st.image("output/figures/chart_score_diff_dist.png", use_container_width=True)
        st.caption(
            "Most districts see little change between scores (difference near zero), "
            "but a tail of districts lose significant score once distance is penalised."
        )

    st.markdown("""
    **Why these charts:** A scatter plot reveals whether the two scores agree or diverge across all 1,873 districts at once.
    The score-difference histogram then shows how large that divergence is and how common it is —
    something a table alone could not convey.
    """)
    st.divider()

    # --- row 3: attendances + distance histogram
    st.subheader("Emergency demand and spatial access")
    c1, c2 = st.columns(2)
    with c1:
        st.image("output/figures/chart_atenciones_by_dept.png", use_container_width=True)
        st.caption(
            "Lima accounts for the vast majority of recorded emergency attendances, "
            "partly due to population size and partly due to higher reporting rates."
        )
    with c2:
        st.image("output/figures/chart_distance_distribution.png", use_container_width=True)
        st.caption(
            "Most populated centers are within 5 km of an IPRESS, but the distribution has a long right tail — "
            "some communities are over 70 km from the nearest facility."
        )

    st.markdown("""
    **Why these charts:** A bar chart by department contextualizes where emergency demand is actually recorded,
    highlighting reporting gaps in rural areas. The distance histogram justifies the distance-penalty approach:
    the long tail confirms that for a significant minority of communities, proximity to care is a real barrier.
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GEOSPATIAL RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("GeoSpatial Results")

    # --- maps: baseline and alternative side by side
    st.subheader("District-level maps")
    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown("**Baseline Access Score**")
        st.image("output/figures/map_baseline_score.png", use_container_width=True)
    with mc2:
        st.markdown("**Alternative Score (distance-penalized)**")
        st.image("output/figures/map_alternative_score.png", use_container_width=True)

    st.divider()

    mc3, mc4 = st.columns(2)
    with mc3:
        st.markdown("**Number of IPRESS Facilities**")
        st.image("output/figures/map_n_ipress.png", use_container_width=True)
    with mc4:
        st.markdown("**Avg Distance to Nearest IPRESS (km)**")
        st.image("output/figures/map_avg_dist.png", use_container_width=True)

    st.divider()

    st.markdown("**Score Difference (Baseline − Alternative)**")
    st.image("output/figures/map_score_diff.png", use_container_width=True)

    st.divider()

    # --- district comparison table
    st.subheader("District-level metrics table")
    metrics = load_metrics()

    dept_options = ["All"] + sorted(metrics["departamento"].dropna().unique().tolist())
    selected_dept = st.selectbox("Filter by department", dept_options, key="dept_selector")

    display = metrics.copy()
    if selected_dept != "All":
        display = display[display["departamento"] == selected_dept]

    display = display[[
        "distrito", "departamento", "provincia",
        "n_ipress", "n_camas", "n_ccpp",
        "avg_dist_km", "total_atenciones",
        "baseline_score", "alternative_score", "score_diff",
    ]].sort_values("baseline_score", ascending=False)

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # --- summary tables side by side
    st.subheader("Summary tables")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Most underserved districts** (farthest from any IPRESS)")
        under = pd.read_csv("output/tables/top_underserved.csv", dtype={"ubigeo": str})
        st.dataframe(
            under[["distrito", "departamento", "n_ipress", "avg_dist_km", "baseline_score"]],
            use_container_width=True, hide_index=True,
        )
    with c2:
        st.markdown("**Best-served districts** (highest baseline score)")
        best = pd.read_csv("output/tables/top_served.csv", dtype={"ubigeo": str})
        st.dataframe(
            best[["distrito", "departamento", "n_ipress", "avg_dist_km", "baseline_score"]],
            use_container_width=True, hide_index=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — INTERACTIVE EXPLORATION
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("Interactive Exploration")

    geo_metrics = load_geo_metrics()
    ipress_df   = load_ipress_points()

    # --- variable selector
    var_options = {
        "baseline_score":    "Baseline Access Score",
        "alternative_score": "Alternative Score (distance-penalized)",
        "score_diff":        "Score Difference (Baseline − Alternative)",
        "n_ipress":          "Number of IPRESS Facilities",
        "avg_dist_km":       "Avg Distance to Nearest IPRESS (km)",
    }
    selected_var = st.selectbox(
        "Variable to display on map",
        options=list(var_options.keys()),
        format_func=lambda k: var_options[k],
        key="var_selector",
    )
    show_ipress = st.checkbox("Show IPRESS facility locations", value=False, key="show_ipress")

    # --- build folium map
    geo_json = geo_metrics[["ubigeo", "distrito_x", "departamen", selected_var, "geometry"]].copy()
    geo_json = geo_json.rename(columns={"distrito_x": "distrito"})
    geo_json["distrito"]    = geo_json["distrito"].fillna("Unknown")
    geo_json["departamen"]  = geo_json["departamen"].fillna("Unknown")
    geo_json[selected_var]  = geo_json[selected_var].fillna(0)
    geo_json["geometry"]    = geo_json["geometry"].simplify(0.01, preserve_topology=True)

    m = folium.Map(location=[-9.19, -75.0], zoom_start=5, tiles="CartoDB positron")

    choropleth = folium.Choropleth(
        geo_data=geo_json.__geo_interface__,
        data=geo_json[["ubigeo", selected_var]],
        columns=["ubigeo", selected_var],
        key_on="feature.properties.ubigeo",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.2,
        legend_name=var_options[selected_var],
        name=var_options[selected_var],
    ).add_to(m)

    # Tooltip on hover
    folium.GeoJson(
        geo_json.__geo_interface__,
        style_function=lambda f: {"fillOpacity": 0, "weight": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=["distrito", "departamen", selected_var],
            aliases=["District", "Department", var_options[selected_var]],
            localize=True,
        ),
    ).add_to(m)

    # IPRESS points (optional)
    if show_ipress:
        sample = ipress_df.sample(min(2000, len(ipress_df)), random_state=42)
        for _, row in sample.iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=2,
                color="#1f78b4",
                fill=True,
                fill_opacity=0.6,
                tooltip=f"{row.get('nombre_del_establecimiento','IPRESS')} ({row.get('categoria','')})",
            ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=550, returned_objects=[])

    st.divider()

    # --- baseline vs alternative comparison
    st.subheader("Baseline vs Alternative: where does distance hurt most?")
    st.markdown("""
    The table below shows districts where the **score drops the most** when distance is taken into account.
    A large drop means the district has facilities on paper, but they are far from the communities that need them.
    """)

    metrics = load_metrics()
    comparison = (
        metrics[metrics["score_diff"].notna()]
        .nlargest(20, "score_diff")[[
            "distrito", "departamento", "n_ipress",
            "avg_dist_km", "baseline_score", "alternative_score", "score_diff"
        ]]
        .rename(columns={
            "distrito": "District",
            "departamento": "Department",
            "n_ipress": "Facilities",
            "avg_dist_km": "Avg Dist (km)",
            "baseline_score": "Baseline Score",
            "alternative_score": "Alt. Score",
            "score_diff": "Score Drop",
        })
    )
    st.dataframe(comparison, use_container_width=True, hide_index=True)
