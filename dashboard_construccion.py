# ============================================================
# 🏗️ DASHBOARD - EMPRESA DE CONSTRUCCIÓN CASAS CAMPESTRES
# ============================================================
# pip install streamlit pandas plotly openpyxl
# python -m streamlit run dashboard_construccion.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

st.set_page_config(
    page_title="Construcciones Dashboard",
    page_icon="🏗️",
    layout="wide"
)

# ── Estilos ──────────────────────────────────────────────────
st.markdown("""
<style>
    .alerta-roja  { background:#ffe0e0; border-left:4px solid #e53935;
                    padding:10px 14px; border-radius:6px; margin:4px 0; color:#b71c1c; }
    .alerta-verde { background:#e0f2e9; border-left:4px solid #43a047;
                    padding:10px 14px; border-radius:6px; margin:4px 0; color:#1b5e20; }
    .kpi-label    { font-size:13px; color:#888; margin-bottom:2px; }
    .kpi-valor    { font-size:26px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Carga de datos ───────────────────────────────────────────
@st.cache_data(ttl=60)
def cargar():
    proyectos  = pd.read_excel("proyectos.xlsx",  parse_dates=["fecha_inicio","fecha_fin"])
    materiales = pd.read_excel("materiales.xlsx", parse_dates=["fecha"])
    gastos     = pd.read_excel("gastos.xlsx",     parse_dates=["fecha"])
    inventario = pd.read_excel("inventario.xlsx")
    materiales["costo_total"] = materiales["cantidad_usada"] * materiales["costo_unitario"]
    inventario["alerta"]      = inventario["stock_actual"] <= inventario["stock_minimo"]
    gastos["diferencia"]      = gastos["ejecutado"] - gastos["presupuestado"]
    gastos["sobrecosto"]      = gastos["diferencia"] > 0
    return proyectos, materiales, gastos, inventario

proyectos, materiales, gastos, inventario = cargar()

# ── Sidebar ──────────────────────────────────────────────────
st.sidebar.image("https://via.placeholder.com/240x60/1a3a5c/ffffff?text=Mi+Constructora", width=240)
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Filtros")

todos = "Todos los proyectos"
lista = [todos] + sorted(proyectos["proyecto"].tolist())
sel   = st.sidebar.selectbox("Proyecto:", lista)

responsables = ["Todos"] + sorted(proyectos["responsable"].unique().tolist())
resp_sel = st.sidebar.selectbox("Responsable:", responsables)

st.sidebar.markdown("---")
st.sidebar.markdown("🔄 *Los datos se actualizan automáticamente al guardar los archivos Excel.*")
st.sidebar.caption(f"Última carga: {date.today().strftime('%d/%m/%Y')}")

# Filtrar proyectos
pf = proyectos.copy()
if sel != todos:
    pf = pf[pf["proyecto"] == sel]
if resp_sel != "Todos":
    pf = pf[pf["responsable"] == resp_sel]

proy_lista = pf["proyecto"].tolist()
mf = materiales[materiales["proyecto"].isin(proy_lista)]
gf = gastos[gastos["proyecto"].isin(proy_lista)]

# ── Título ───────────────────────────────────────────────────
st.title("Dashboard de Cambria Constructora")
st.caption("Seguimiento en tiempo real de proyectos, materiales, gastos e inventario")
st.divider()

# ============================================================
# MÓDULO 1 — KPIs GLOBALES
# ============================================================
st.subheader("📊 Resumen General")
c1, c2, c3, c4, c5 = st.columns(5)

avance_prom   = pf["avance_real"].mean() if len(pf) else 0
total_contrat = pf["valor_contrato"].sum()
total_ejec    = gf["ejecutado"].sum()
total_presupu = gf["presupuestado"].sum()
alertas_inv   = inventario["alerta"].sum()

with c1:
    st.metric("🏠 Proyectos activos", len(pf))
with c2:
    st.metric("📈 Avance promedio", f"{avance_prom:.0f}%",
              delta=f"{avance_prom - pf['avance_meta'].mean():.0f}% vs meta" if len(pf) else None)
with c3:
    st.metric("💰 Contratos totales", f"${total_contrat/1_000_000:.0f}M")
with c4:
    delta_gasto = total_ejec - total_presupu
    st.metric("💸 Gasto ejecutado", f"${total_ejec/1_000_000:.0f}M",
              delta=f"${delta_gasto/1_000_000:.1f}M vs presupuesto",
              delta_color="inverse")
with c5:
    st.metric("⚠️ Alertas inventario", int(alertas_inv),
              delta="materiales por debajo del mínimo" if alertas_inv else "Inventario OK",
              delta_color="inverse" if alertas_inv else "normal")

st.divider()

# ============================================================
# MÓDULO 2 — EJECUCIÓN DE OBRAS
# ============================================================
st.subheader("🏗️ Ejecución y Avance de Obras")

if pf.empty:
    st.info("No hay proyectos con los filtros seleccionados.")
else:
    for _, row in pf.iterrows():
        real = row["avance_real"]
        meta = row["avance_meta"]
        diff = real - meta
        color = "#43a047" if diff >= 0 else ("#fb8c00" if diff >= -10 else "#e53935")

        dias_totales   = (row["fecha_fin"] - row["fecha_inicio"]).days
        dias_transcurr = (pd.Timestamp(date.today()) - row["fecha_inicio"]).days
        dias_restantes = max((row["fecha_fin"] - pd.Timestamp(date.today())).days, 0)

        with st.container():
            col_info, col_barra = st.columns([1, 2])
            with col_info:
                st.markdown(f"**{row['proyecto']}**")
                st.caption(f"👤 {row['responsable']}  |  🗓️ Termina: {row['fecha_fin'].strftime('%d/%m/%Y')}  |  ⏳ {dias_restantes} días restantes")
                st.caption(f"🔧 Etapa: {row['etapa']}  |  💰 Contrato: ${row['valor_contrato']/1_000_000:.0f}M")
            with col_barra:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[real], y=["Avance real"], orientation="h",
                    marker_color=color, name="Real",
                    text=f"{real}%", textposition="inside",
                    hovertemplate=f"Real: {real}%<extra></extra>"
                ))
                fig.add_trace(go.Bar(
                    x=[meta], y=["Meta"], orientation="h",
                    marker_color="#90a4ae", name="Meta",
                    text=f"{meta}%", textposition="inside",
                    hovertemplate=f"Meta: {meta}%<extra></extra>"
                ))
                fig.update_layout(
                    height=110, margin=dict(l=0,r=20,t=0,b=0),
                    xaxis=dict(range=[0,100], showticklabels=False),
                    barmode="overlay", showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig, use_container_width=True)

                estado = "✅ A tiempo" if diff >= 0 else (f"⚠️ Atrasado {abs(diff):.0f}%" if diff >= -10 else f"🔴 Crítico: {abs(diff):.0f}% de atraso")
                st.caption(estado)
        st.markdown("---")

st.divider()

# ============================================================
# MÓDULO 3 — MATERIALES USADOS
# ============================================================
st.subheader("🧱 Materiales Utilizados")

if mf.empty:
    st.info("Sin datos de materiales para los proyectos seleccionados.")
else:
    col_m1, col_m2 = st.columns(2)

    with col_m1:
        resumen_mat = mf.groupby("material")["costo_total"].sum().reset_index()
        resumen_mat = resumen_mat.sort_values("costo_total", ascending=True)
        fig_mat = px.bar(
            resumen_mat, x="costo_total", y="material", orientation="h",
            title="Gasto total por tipo de material",
            color="costo_total", color_continuous_scale="Blues",
            labels={"costo_total": "Costo total ($)", "material": ""}
        )
        fig_mat.update_layout(coloraxis_showscale=False, height=360,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig_mat.update_traces(hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>")
        st.plotly_chart(fig_mat, use_container_width=True)

    with col_m2:
        if sel == todos:
            resumen_proy = mf.groupby("proyecto")["costo_total"].sum().reset_index()
            fig_proy = px.pie(
                resumen_proy, names="proyecto", values="costo_total",
                title="Distribución de materiales por proyecto",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.35
            )
            fig_proy.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_proy, use_container_width=True)
        else:
            evol = mf.groupby("fecha")["costo_total"].sum().reset_index()
            fig_evol = px.line(
                evol, x="fecha", y="costo_total",
                title=f"Evolución de consumo — {sel}",
                markers=True,
                labels={"costo_total": "Costo ($)", "fecha": "Fecha"}
            )
            fig_evol.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_evol, use_container_width=True)

    with st.expander("📋 Ver tabla detallada de materiales"):
        tabla_m = mf.copy()
        tabla_m["costo_total"] = tabla_m["costo_total"].apply(lambda x: f"${x:,.0f}")
        tabla_m["costo_unitario"] = tabla_m["costo_unitario"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(tabla_m, use_container_width=True)

st.divider()

# ============================================================
# MÓDULO 4 — GASTOS Y PRESUPUESTO
# ============================================================
st.subheader("💰 Gastos vs Presupuesto")

if gf.empty:
    st.info("Sin datos de gastos para los proyectos seleccionados.")
else:
    # Alertas de sobrecosto
    sobrecostos = gf[gf["sobrecosto"]]
    if not sobrecostos.empty:
        for _, row in sobrecostos.iterrows():
            exceso = row["diferencia"] / 1_000_000
            st.markdown(
                f'<div class="alerta-roja">🔴 <b>{row["proyecto"]}</b> — {row["concepto"]}: '
                f'sobrecosto de <b>${exceso:.1f}M</b> '
                f'(presupuesto ${row["presupuestado"]/1_000_000:.1f}M → ejecutado ${row["ejecutado"]/1_000_000:.1f}M)</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown('<div class="alerta-verde">✅ Todos los rubros dentro del presupuesto</div>', unsafe_allow_html=True)

    st.markdown("")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        resumen_cat = gf.groupby("categoria")[["presupuestado","ejecutado"]].sum().reset_index()
        fig_cat = go.Figure()
        fig_cat.add_trace(go.Bar(name="Presupuestado", x=resumen_cat["categoria"],
                                 y=resumen_cat["presupuestado"], marker_color="#90caf9"))
        fig_cat.add_trace(go.Bar(name="Ejecutado",     x=resumen_cat["categoria"],
                                 y=resumen_cat["ejecutado"],     marker_color="#1565c0"))
        fig_cat.update_layout(
            title="Presupuestado vs ejecutado por categoría",
            barmode="group", height=360,
            yaxis_title="Pesos ($)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_g2:
        resumen_proy_g = gf.groupby("proyecto")[["presupuestado","ejecutado"]].sum().reset_index()
        resumen_proy_g["pct"] = (resumen_proy_g["ejecutado"] / resumen_proy_g["presupuestado"] * 100).round(1)
        resumen_proy_g["color"] = resumen_proy_g["pct"].apply(
            lambda x: "#43a047" if x <= 100 else ("#fb8c00" if x <= 110 else "#e53935")
        )
        fig_pct = go.Figure(go.Bar(
            x=resumen_proy_g["pct"], y=resumen_proy_g["proyecto"],
            orientation="h",
            marker_color=resumen_proy_g["color"],
            text=resumen_proy_g["pct"].apply(lambda x: f"{x}%"),
            textposition="outside"
        ))
        fig_pct.add_vline(x=100, line_dash="dash", line_color="gray", annotation_text="100%")
        fig_pct.update_layout(
            title="% del presupuesto consumido",
            height=360, xaxis_title="% ejecutado",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_pct, use_container_width=True)

    with st.expander("📋 Ver tabla de gastos"):
        tabla_g = gf[["proyecto","concepto","categoria","presupuestado","ejecutado","diferencia","mes"]].copy()
        def color_dif(val):
            color = "color: #e53935" if val > 0 else "color: #43a047"
            return color
        tabla_g["presupuestado"] = tabla_g["presupuestado"].apply(lambda x: f"${x:,.0f}")
        tabla_g["ejecutado"]     = tabla_g["ejecutado"].apply(lambda x: f"${x:,.0f}")
        tabla_g["diferencia"]    = tabla_g["diferencia"].apply(lambda x: f"+${x:,.0f}" if x > 0 else f"${x:,.0f}")
        st.dataframe(tabla_g, use_container_width=True)

st.divider()

# ============================================================
# MÓDULO 5 — INVENTARIO DE INSUMOS
# ============================================================
st.subheader("📦 Inventario de Insumos")

col_i1, col_i2 = st.columns([2, 1])

with col_i1:
    inv_plot = inventario.sort_values("stock_actual", ascending=True).copy()
    inv_plot["color"] = inv_plot["alerta"].map({True: "#e53935", False: "#43a047"})
    inv_plot["estado"] = inv_plot["alerta"].map({True: "⚠️ Stock bajo", False: "✅ OK"})

    fig_inv = go.Figure()
    fig_inv.add_trace(go.Bar(
        y=inv_plot["material"], x=inv_plot["stock_actual"],
        orientation="h", name="Stock actual",
        marker_color=inv_plot["color"],
        text=inv_plot["stock_actual"].astype(str) + " " + inv_plot["unidad"],
        textposition="outside"
    ))
    fig_inv.add_trace(go.Scatter(
        y=inv_plot["material"], x=inv_plot["stock_minimo"],
        mode="markers", name="Mínimo requerido",
        marker=dict(color="orange", size=10, symbol="line-ns-open", line_width=2)
    ))
    fig_inv.update_layout(
        title="Stock actual vs mínimo requerido",
        height=400, xaxis_title="Cantidad",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_inv, use_container_width=True)

with col_i2:
    st.markdown("**Estado del inventario**")
    st.markdown("")
    for _, row in inventario.iterrows():
        pct  = min(row["stock_actual"] / row["stock_minimo"] * 100, 150)
        icon = "🔴" if row["alerta"] else "🟢"
        st.markdown(f"{icon} **{row['material']}**")
        st.progress(min(int(pct), 100))
        st.caption(f"{row['stock_actual']} {row['unidad']} | mín: {row['stock_minimo']}")

    alertas_lista = inventario[inventario["alerta"]]
    if not alertas_lista.empty:
        st.markdown("---")
        st.markdown("**⚠️ Materiales que necesitan reposición:**")
        for _, row in alertas_lista.iterrows():
            faltante = row["stock_minimo"] - row["stock_actual"]
            st.markdown(
                f'<div class="alerta-roja">🔴 <b>{row["material"]}</b><br>'
                f'Stock: {row["stock_actual"]} | Mínimo: {row["stock_minimo"]}<br>'
                f'Pedir al menos {faltante} {row["unidad"]}<br>'
                f'📞 {row["proveedor"]}</div>',
                unsafe_allow_html=True
            )

with st.expander("📋 Ver tabla completa de inventario"):
    tabla_i = inventario.copy()
    tabla_i["costo_unitario"] = tabla_i["costo_unitario"].apply(lambda x: f"${x:,.0f}")
    tabla_i["valor_total"]    = (inventario["stock_actual"] * inventario["costo_unitario"]).apply(lambda x: f"${x:,.0f}")
    st.dataframe(tabla_i, use_container_width=True)

st.divider()

# ── Descarga ─────────────────────────────────────────────────
st.subheader("⬇️ Exportar datos")
col_d1, col_d2, col_d3, col_d4 = st.columns(4)
with col_d1:
    st.download_button("📊 Proyectos",    pf.to_csv(index=False).encode(),    "proyectos_filtrado.csv",    "text/csv")
with col_d2:
    st.download_button("🧱 Materiales",   mf.to_csv(index=False).encode(),    "materiales_filtrado.csv",   "text/csv")
with col_d3:
    st.download_button("💰 Gastos",       gf.to_csv(index=False).encode(),    "gastos_filtrado.csv",       "text/csv")
with col_d4:
    st.download_button("📦 Inventario",   inventario.to_csv(index=False).encode(), "inventario.csv",       "text/csv")

st.divider()
st.caption("🏗️ Dashboard de Construcción | Desarrollado con Streamlit")
