# ============================================================
# 🏗️ DASHBOARD CONSTRUCCIÓN — con formularios integrados
# ============================================================
# pip install streamlit pandas plotly openpyxl
# python -m streamlit run dashboard_construccion_v2.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
import os

st.set_page_config(
    page_title="Cambria",
    page_icon="🏗️",
    layout="wide"
)

# ── Estilos ──────────────────────────────────────────────────
st.markdown("""
<style>
.alerta-roja  { background:#ffe0e0; border-left:4px solid #e53935;
                padding:10px 14px; border-radius:0 6px 6px 0; margin:4px 0; color:#b71c1c; }
.alerta-verde { background:#e0f2e9; border-left:4px solid #43a047;
                padding:10px 14px; border-radius:0 6px 6px 0; margin:4px 0; color:#1b5e20; }
.form-card    { background:#f8f9fa; border:1px solid #e0e0e0;
                border-radius:10px; padding:20px; margin-bottom:10px; }
</style>
""", unsafe_allow_html=True)

# ── Archivos ─────────────────────────────────────────────────
ARCH = {
    "proyectos":  "proyectos.xlsx",
    "materiales": "materiales.xlsx",
    "gastos":     "gastos.xlsx",
    "inventario": "inventario.xlsx",
}

# ── Funciones de guardado ────────────────────────────────────
def guardar_fila(archivo_key, nueva_fila: dict):
    """Agrega una fila al Excel y limpia el cache."""
    ruta = ARCH[archivo_key]
    df   = pd.read_excel(ruta)
    nueva = pd.DataFrame([nueva_fila])
    df_nuevo = pd.concat([df, nueva], ignore_index=True)
    df_nuevo.to_excel(ruta, index=False)
    st.cache_data.clear()

def actualizar_fila(archivo_key, col_clave, val_clave, cambios: dict):
    """Actualiza columnas de la fila que coincide con col_clave == val_clave."""
    ruta = ARCH[archivo_key]
    df   = pd.read_excel(ruta)
    mask = df[col_clave] == val_clave
    for col, val in cambios.items():
        df.loc[mask, col] = val
    df.to_excel(ruta, index=False)
    st.cache_data.clear()

# ── Carga de datos ───────────────────────────────────────────
@st.cache_data(ttl=30)
def cargar():
    proy = pd.read_excel(ARCH["proyectos"],  parse_dates=["fecha_inicio","fecha_fin"])
    mat  = pd.read_excel(ARCH["materiales"], parse_dates=["fecha"])
    gas  = pd.read_excel(ARCH["gastos"],     parse_dates=["fecha"])
    inv  = pd.read_excel(ARCH["inventario"])
    mat["costo_total"] = mat["cantidad_usada"] * mat["costo_unitario"]
    inv["alerta"]      = inv["stock_actual"] <= inv["stock_minimo"]
    gas["diferencia"]  = gas["ejecutado"] - gas["presupuestado"]
    gas["sobrecosto"]  = gas["diferencia"] > 0
    return proy, mat, gas, inv

# ── Sidebar ──────────────────────────────────────────────────
st.sidebar.title("CAMBRIA CONSTRUCTORA")
st.sidebar.markdown("---")

seccion = st.sidebar.radio(
    "Ir a:",
    ["📊 Dashboard", "➕ Registrar datos"],
    index=0
)

st.sidebar.markdown("---")
todos = "Todos los proyectos"
proy_raw, _, _, _ = cargar()
lista_proy = [todos] + sorted(proy_raw["proyecto"].tolist())
sel_proy = st.sidebar.selectbox("Filtrar proyecto:", lista_proy)
st.sidebar.caption(f"Última carga: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ============================================================
# SECCIÓN A — DASHBOARD
# ============================================================
if seccion == "📊 Dashboard":

    proyectos, materiales, gastos, inventario = cargar()

    # Aplicar filtro
    pf = proyectos if sel_proy == todos else proyectos[proyectos["proyecto"] == sel_proy]
    proy_lista = pf["proyecto"].tolist()
    mf = materiales[materiales["proyecto"].isin(proy_lista)]
    gf = gastos[gastos["proyecto"].isin(proy_lista)]

    # ── Título ───────────────────────────────────────────────
    st.title("📊 Dashboard de Cambria")
    st.caption("Los datos se actualizan automáticamente al registrar información nueva.")
    st.divider()

    # ── KPIs ─────────────────────────────────────────────────
    st.subheader("Resumen general")
    c1, c2, c3, c4, c5 = st.columns(5)
    avance_prom   = pf["avance_real"].mean() if len(pf) else 0
    total_contrat = pf["valor_contrato"].sum()
    total_ejec    = gf["ejecutado"].sum()
    total_presupu = gf["presupuestado"].sum()
    alertas_inv   = inventario["alerta"].sum()

    with c1: st.metric("🏠 Proyectos", len(pf))
    with c2:
        st.metric("📈 Avance promedio", f"{avance_prom:.0f}%",
                  delta=f"{avance_prom - pf['avance_meta'].mean():.0f}% vs meta" if len(pf) else None)
    with c3: st.metric("💰 Contratos", f"${total_contrat/1_000_000:.0f}M")
    with c4:
        delta_g = total_ejec - total_presupu
        st.metric("💸 Gasto ejecutado", f"${total_ejec/1_000_000:.0f}M",
                  delta=f"${delta_g/1_000_000:.1f}M vs presupuesto", delta_color="inverse")
    with c5:
        st.metric("⚠️ Alertas inventario", int(alertas_inv),
                  delta_color="inverse" if alertas_inv else "normal")
    st.divider()

    # ── Ejecución de obras ───────────────────────────────────
    st.subheader("🏗️ Ejecución de obras")
    if pf.empty:
        st.info("Sin proyectos con los filtros actuales.")
    else:
        for _, row in pf.iterrows():
            real  = row["avance_real"]
            meta  = row["avance_meta"]
            diff  = real - meta
            color = "#43a047" if diff >= 0 else ("#fb8c00" if diff >= -10 else "#e53935")
            dias_rest = max((row["fecha_fin"] - pd.Timestamp(date.today())).days, 0)

            col_i, col_b = st.columns([1, 2])
            with col_i:
                st.markdown(f"**{row['proyecto']}**")
                st.caption(f"👤 {row['responsable']}  |  🔧 {row['etapa']}  |  ⏳ {dias_rest} días")
                st.caption(f"🗓️ Fin: {row['fecha_fin'].strftime('%d/%m/%Y')}  |  💰 ${row['valor_contrato']/1_000_000:.0f}M")
            with col_b:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=[real], y=["Avance real"], orientation="h",
                                     marker_color=color, text=f"{real}%", textposition="inside"))
                fig.add_trace(go.Bar(x=[meta], y=["Meta"], orientation="h",
                                     marker_color="#90a4ae", text=f"{meta}%", textposition="inside"))
                fig.update_layout(height=100, margin=dict(l=0,r=20,t=0,b=0),
                                  xaxis=dict(range=[0,100], showticklabels=False),
                                  barmode="overlay", showlegend=False,
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                estado = "✅ A tiempo" if diff >= 0 else (f"⚠️ Atrasado {abs(diff):.0f}%" if diff >= -10 else f"🔴 Crítico: {abs(diff):.0f}% de atraso")
                st.caption(estado)
            st.markdown("---")
    st.divider()

    # ── Materiales ───────────────────────────────────────────
    st.subheader("🧱 Materiales utilizados")
    if mf.empty:
        st.info("Sin datos de materiales.")
    else:
        cm1, cm2 = st.columns(2)
        with cm1:
            rm = mf.groupby("material")["costo_total"].sum().reset_index().sort_values("costo_total")
            fig = px.bar(rm, x="costo_total", y="material", orientation="h",
                         title="Gasto por material", color="costo_total",
                         color_continuous_scale="Blues")
            fig.update_layout(coloraxis_showscale=False, height=340,
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with cm2:
            if sel_proy == todos:
                rp = mf.groupby("proyecto")["costo_total"].sum().reset_index()
                fig2 = px.pie(rp, names="proyecto", values="costo_total",
                              title="Por proyecto", hole=0.35,
                              color_discrete_sequence=px.colors.qualitative.Set2)
                fig2.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                ev = mf.groupby("fecha")["costo_total"].sum().reset_index()
                fig2 = px.line(ev, x="fecha", y="costo_total", markers=True,
                               title=f"Evolución — {sel_proy}")
                fig2.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
    st.divider()

    # ── Gastos ───────────────────────────────────────────────
    st.subheader("💰 Gastos vs presupuesto")
    if not gf.empty:
        for _, row in gf[gf["sobrecosto"]].iterrows():
            st.markdown(f'<div class="alerta-roja">🔴 <b>{row["proyecto"]}</b> — {row["concepto"]}: '
                        f'sobrecosto de <b>${row["diferencia"]/1_000_000:.1f}M</b></div>',
                        unsafe_allow_html=True)
        cg1, cg2 = st.columns(2)
        with cg1:
            rc = gf.groupby("categoria")[["presupuestado","ejecutado"]].sum().reset_index()
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(name="Presupuestado", x=rc["categoria"],
                                  y=rc["presupuestado"], marker_color="#90caf9"))
            fig3.add_trace(go.Bar(name="Ejecutado", x=rc["categoria"],
                                  y=rc["ejecutado"], marker_color="#1565c0"))
            fig3.update_layout(title="Por categoría", barmode="group", height=340,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)
        with cg2:
            rg = gf.groupby("proyecto")[["presupuestado","ejecutado"]].sum().reset_index()
            rg["pct"] = (rg["ejecutado"] / rg["presupuestado"] * 100).round(1)
            rg["color"] = rg["pct"].apply(lambda x: "#43a047" if x<=100 else ("#fb8c00" if x<=110 else "#e53935"))
            fig4 = go.Figure(go.Bar(x=rg["pct"], y=rg["proyecto"], orientation="h",
                                    marker_color=rg["color"],
                                    text=rg["pct"].apply(lambda x: f"{x}%"),
                                    textposition="outside"))
            fig4.add_vline(x=100, line_dash="dash", line_color="gray")
            fig4.update_layout(title="% presupuesto consumido", height=340,
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig4, use_container_width=True)
    st.divider()

    # ── Inventario ───────────────────────────────────────────
    st.subheader("📦 Inventario de insumos")
    ci1, ci2 = st.columns([2, 1])
    with ci1:
        ip = inventario.sort_values("stock_actual").copy()
        ip["color"] = ip["alerta"].map({True: "#e53935", False: "#43a047"})
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(y=ip["material"], x=ip["stock_actual"], orientation="h",
                              marker_color=ip["color"],
                              text=ip["stock_actual"].astype(str)+" "+ip["unidad"],
                              textposition="outside", name="Stock actual"))
        fig5.add_trace(go.Scatter(y=ip["material"], x=ip["stock_minimo"],
                                  mode="markers", name="Mínimo",
                                  marker=dict(color="orange", size=10, symbol="line-ns-open", line_width=2)))
        fig5.update_layout(title="Stock actual vs mínimo", height=380,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig5, use_container_width=True)
    with ci2:
        st.markdown("**Estado**")
        for _, row in inventario.iterrows():
            pct  = min(int(row["stock_actual"]/row["stock_minimo"]*100), 100)
            icon = "🔴" if row["alerta"] else "🟢"
            st.markdown(f"{icon} **{row['material']}**")
            st.progress(pct)
            st.caption(f"{row['stock_actual']} {row['unidad']} | mín: {row['stock_minimo']}")
        alertas_mat = inventario[inventario["alerta"]]
        if not alertas_mat.empty:
            st.markdown("---")
            for _, row in alertas_mat.iterrows():
                faltante = row["stock_minimo"] - row["stock_actual"]
                st.markdown(
                    f'<div class="alerta-roja">🔴 <b>{row["material"]}</b><br>'
                    f'Pedir: {faltante} {row["unidad"]}<br>📞 {row["proveedor"]}</div>',
                    unsafe_allow_html=True)
    st.divider()

    # Descarga
    st.subheader("⬇️ Exportar")
    cd1, cd2, cd3, cd4 = st.columns(4)
    with cd1: st.download_button("📊 Proyectos",  pf.to_csv(index=False).encode(),  "proyectos.csv",  "text/csv")
    with cd2: st.download_button("🧱 Materiales", mf.to_csv(index=False).encode(),  "materiales.csv", "text/csv")
    with cd3: st.download_button("💰 Gastos",     gf.to_csv(index=False).encode(),  "gastos.csv",     "text/csv")
    with cd4: st.download_button("📦 Inventario", inventario.to_csv(index=False).encode(), "inventario.csv", "text/csv")


# ============================================================
# SECCIÓN B — FORMULARIOS DE REGISTRO
# ============================================================
else:
    proyectos, materiales, gastos, inventario = cargar()

    st.title("➕ Registrar datos")
    st.caption("Completa el formulario y presiona Guardar. El dashboard se actualizará automáticamente.")
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏗️ Avance de obra",
        "🧱 Uso de material",
        "💰 Gasto",
        "📦 Inventario"
    ])

    # ── TAB 1: Avance de obra ─────────────────────────────────
    with tab1:
        st.subheader("Actualizar avance de obra")
        st.caption("Usa este formulario cada vez que quieras reportar el progreso de un proyecto.")

        col_f, col_p = st.columns([1, 1])

        with col_f:
            with st.form("form_avance", clear_on_submit=True):
                st.markdown("**¿Qué proyecto vas a actualizar?**")
                proy_sel = st.selectbox(
                    "Proyecto",
                    proyectos["proyecto"].tolist(),
                    key="av_proy"
                )

                # Mostrar valores actuales
                datos_actual = proyectos[proyectos["proyecto"] == proy_sel].iloc[0]
                st.info(f"📌 Avance actual: **{datos_actual['avance_real']}%** | Etapa: **{datos_actual['etapa']}**")

                nuevo_avance = st.number_input(
                    "Nuevo avance real (%)",
                    min_value=0, max_value=100,
                    value=int(datos_actual["avance_real"]),
                    step=1
                )
                nueva_etapa = st.selectbox(
                    "Etapa actual",
                    ["Preliminares", "Cimentación", "Estructura",
                     "Mampostería", "Cubierta", "Instalaciones",
                     "Acabados", "Acabados finales", "Entregado"],
                    index=["Preliminares","Cimentación","Estructura",
                           "Mampostería","Cubierta","Instalaciones",
                           "Acabados","Acabados finales","Entregado"].index(datos_actual["etapa"])
                    if datos_actual["etapa"] in ["Preliminares","Cimentación","Estructura",
                                                  "Mampostería","Cubierta","Instalaciones",
                                                  "Acabados","Acabados finales","Entregado"] else 0
                )
                observacion = st.text_area("Observación (opcional)", height=80)
                submitted = st.form_submit_button("💾 Guardar avance", use_container_width=True, type="primary")

            if submitted:
                actualizar_fila("proyectos", "proyecto", proy_sel, {
                    "avance_real": nuevo_avance,
                    "etapa": nueva_etapa
                })
                st.success(f"✅ Avance de **{proy_sel}** actualizado a **{nuevo_avance}%** — etapa: {nueva_etapa}")
                st.balloons()

        with col_p:
            st.markdown("**Vista previa — avance actual de todos los proyectos**")
            fig_prev = px.bar(
                proyectos.sort_values("avance_real"),
                x="avance_real", y="proyecto", orientation="h",
                color="avance_real", color_continuous_scale="RdYlGn",
                range_color=[0, 100],
                labels={"avance_real": "% avance", "proyecto": ""},
                text="avance_real"
            )
            fig_prev.update_traces(texttemplate="%{text}%", textposition="outside")
            fig_prev.update_layout(height=340, coloraxis_showscale=False,
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_prev, use_container_width=True)

        st.divider()
        st.markdown("**¿Quieres agregar un proyecto nuevo?**")
        with st.expander("➕ Registrar proyecto nuevo"):
            with st.form("form_nuevo_proy", clear_on_submit=True):
                c1n, c2n = st.columns(2)
                with c1n:
                    n_nombre     = st.text_input("Nombre del proyecto")
                    n_cliente    = st.text_input("Cliente")
                    n_responsable= st.text_input("Responsable")
                    n_contrato   = st.number_input("Valor contrato ($)", min_value=0, step=1_000_000)
                with c2n:
                    n_inicio = st.date_input("Fecha inicio", value=date.today())
                    n_fin    = st.date_input("Fecha fin estimada")
                    n_etapa  = st.selectbox("Etapa inicial",
                                            ["Preliminares","Cimentación","Estructura"])
                    n_meta   = st.number_input("Meta de avance inicial (%)", 0, 100, 5)
                sub_nuevo = st.form_submit_button("🏠 Crear proyecto", use_container_width=True, type="primary")

            if sub_nuevo:
                if not n_nombre:
                    st.error("El nombre del proyecto es obligatorio.")
                else:
                    guardar_fila("proyectos", {
                        "proyecto": n_nombre, "fecha_inicio": str(n_inicio),
                        "fecha_fin": str(n_fin), "avance_real": 0,
                        "avance_meta": n_meta, "etapa": n_etapa,
                        "responsable": n_responsable, "cliente": n_cliente,
                        "valor_contrato": n_contrato
                    })
                    st.success(f"✅ Proyecto **{n_nombre}** creado correctamente.")

    # ── TAB 2: Uso de material ────────────────────────────────
    with tab2:
        st.subheader("Registrar uso de material")
        st.caption("Registra cada vez que se consuma un material en obra.")

        col_fm, col_pm = st.columns([1, 1])

        MATERIALES_LISTA = sorted(inventario["material"].tolist())
        UNIDADES         = ["bultos","m³","varillas","tablas","und","galones","metros","kg","litros"]

        with col_fm:
            with st.form("form_material", clear_on_submit=True):
                m_proy     = st.selectbox("Proyecto", proyectos["proyecto"].tolist())
                m_material = st.selectbox("Material", MATERIALES_LISTA)

                # Mostrar stock disponible
                stock_disp = inventario[inventario["material"] == m_material]["stock_actual"].values
                if len(stock_disp):
                    unidad_mat = inventario[inventario["material"] == m_material]["unidad"].values[0]
                    st.info(f"📦 Stock disponible: **{stock_disp[0]} {unidad_mat}**")

                m_cantidad   = st.number_input("Cantidad usada", min_value=0.1, step=1.0)
                m_unidad     = st.selectbox("Unidad", UNIDADES,
                                            index=UNIDADES.index(unidad_mat) if unidad_mat in UNIDADES else 0)
                m_costo_unit = st.number_input("Costo unitario ($)", min_value=0, step=1000,
                                               value=int(inventario[inventario["material"]==m_material]["costo_unitario"].values[0])
                                               if len(stock_disp) else 0)
                m_fecha      = st.date_input("Fecha de uso", value=date.today())
                sub_mat      = st.form_submit_button("💾 Guardar consumo", use_container_width=True, type="primary")

            if sub_mat:
                guardar_fila("materiales", {
                    "proyecto": m_proy, "material": m_material,
                    "cantidad_usada": m_cantidad, "unidad": m_unidad,
                    "fecha": str(m_fecha), "costo_unitario": m_costo_unit
                })
                # Descontar del inventario
                stock_nuevo = float(stock_disp[0]) - m_cantidad if len(stock_disp) else 0
                actualizar_fila("inventario", "material", m_material, {"stock_actual": max(stock_nuevo, 0)})
                nuevo_stock = max(stock_nuevo, 0)
                st.success(f"✅ Registrado: {m_cantidad} {m_unidad} de **{m_material}** en {m_proy}.")
                if nuevo_stock <= inventario[inventario["material"]==m_material]["stock_minimo"].values[0]:
                    st.warning(f"⚠️ Stock de **{m_material}** por debajo del mínimo ({nuevo_stock:.0f} {m_unidad}). ¡Considera reponer!")

        with col_pm:
            st.markdown("**Consumo acumulado por material**")
            resumen_cons = materiales.groupby("material")["cantidad_usada"].sum().reset_index()
            resumen_cons = resumen_cons.sort_values("cantidad_usada", ascending=True)
            fig_cons = px.bar(resumen_cons, x="cantidad_usada", y="material", orientation="h",
                              color="cantidad_usada", color_continuous_scale="Oranges",
                              labels={"cantidad_usada": "Cantidad total", "material": ""})
            fig_cons.update_layout(height=380, coloraxis_showscale=False,
                                   paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_cons, use_container_width=True)

    # ── TAB 3: Gasto ─────────────────────────────────────────
    with tab3:
        st.subheader("Registrar gasto")
        st.caption("Registra cada egreso: mano de obra, materiales, maquinaria, etc.")

        col_fg, col_pg = st.columns([1, 1])

        CATEGORIAS = ["Mano de obra","Materiales","Maquinaria","Diseño","Legal","Otros"]
        MESES      = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                      "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

        with col_fg:
            with st.form("form_gasto", clear_on_submit=True):
                g_proy      = st.selectbox("Proyecto", proyectos["proyecto"].tolist())
                g_concepto  = st.text_input("Concepto (ej: Pago cuadrilla semana 3)")
                g_categoria = st.selectbox("Categoría", CATEGORIAS)
                g_c1, g_c2  = st.columns(2)
                with g_c1:
                    g_presup = st.number_input("Presupuestado ($)", min_value=0, step=100_000)
                with g_c2:
                    g_ejec   = st.number_input("Ejecutado ($)", min_value=0, step=100_000)
                g_mes   = st.selectbox("Mes", MESES,
                                       index=date.today().month - 1)
                g_fecha = st.date_input("Fecha", value=date.today())

                dif = g_ejec - g_presup
                if dif > 0:
                    st.warning(f"⚠️ Este gasto supera el presupuesto en ${dif:,.0f}")
                elif g_presup > 0 and g_ejec <= g_presup:
                    st.success(f"✅ Dentro del presupuesto (ahorro: ${abs(dif):,.0f})")

                sub_gas = st.form_submit_button("💾 Guardar gasto", use_container_width=True, type="primary")

            if sub_gas:
                if not g_concepto:
                    st.error("El concepto es obligatorio.")
                else:
                    guardar_fila("gastos", {
                        "proyecto": g_proy, "concepto": g_concepto,
                        "categoria": g_categoria, "presupuestado": g_presup,
                        "ejecutado": g_ejec, "mes": g_mes, "fecha": str(g_fecha)
                    })
                    st.success(f"✅ Gasto **{g_concepto}** registrado en {g_proy}.")

        with col_pg:
            st.markdown("**Resumen de gastos — todos los proyectos**")
            res_gas = gastos.groupby("proyecto")[["presupuestado","ejecutado"]].sum().reset_index()
            res_gas["pct"] = (res_gas["ejecutado"] / res_gas["presupuestado"].replace(0,1) * 100).round(1)
            res_gas["color"] = res_gas["pct"].apply(
                lambda x: "#43a047" if x <= 100 else ("#fb8c00" if x <= 110 else "#e53935"))
            fig_gas = go.Figure(go.Bar(
                x=res_gas["pct"], y=res_gas["proyecto"], orientation="h",
                marker_color=res_gas["color"],
                text=res_gas["pct"].apply(lambda x: f"{x:.0f}%"), textposition="outside"
            ))
            fig_gas.add_vline(x=100, line_dash="dash", line_color="gray", annotation_text="100%")
            fig_gas.update_layout(title="% presupuesto ejecutado", height=340,
                                  xaxis_title="% ejecutado",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_gas, use_container_width=True)

    # ── TAB 4: Inventario ─────────────────────────────────────
    with tab4:
        st.subheader("Actualizar inventario")
        st.caption("Registra compras de materiales o ajusta el stock manualmente.")

        col_fi, col_pi = st.columns([1, 1])

        with col_fi:
            st.markdown("**Registrar compra (reponer material)**")
            with st.form("form_compra", clear_on_submit=True):
                i_material = st.selectbox("Material", inventario["material"].tolist())
                datos_inv  = inventario[inventario["material"] == i_material].iloc[0]
                st.info(f"📦 Stock actual: **{datos_inv['stock_actual']} {datos_inv['unidad']}** | "
                        f"Mínimo: {datos_inv['stock_minimo']} {datos_inv['unidad']}")
                i_cantidad    = st.number_input(f"Cantidad comprada ({datos_inv['unidad']})",
                                                min_value=0.1, step=1.0)
                i_costo_unit  = st.number_input("Costo unitario ($)", min_value=0, step=1000,
                                                value=int(datos_inv["costo_unitario"]))
                i_proveedor   = st.text_input("Proveedor", value=datos_inv["proveedor"])
                sub_compra    = st.form_submit_button("📥 Registrar compra", use_container_width=True, type="primary")

            if sub_compra:
                nuevo_stock = float(datos_inv["stock_actual"]) + i_cantidad
                actualizar_fila("inventario", "material", i_material, {
                    "stock_actual": nuevo_stock,
                    "costo_unitario": i_costo_unit,
                    "proveedor": i_proveedor
                })
                st.success(f"✅ Stock de **{i_material}** actualizado: "
                           f"{datos_inv['stock_actual']} → **{nuevo_stock:.0f} {datos_inv['unidad']}**")

            st.markdown("---")
            st.markdown("**Ajuste manual de stock**")
            with st.form("form_ajuste", clear_on_submit=True):
                aj_material = st.selectbox("Material a ajustar",
                                           inventario["material"].tolist(), key="aj_mat")
                aj_datos    = inventario[inventario["material"] == aj_material].iloc[0]
                aj_nuevo    = st.number_input(
                    f"Nuevo stock ({aj_datos['unidad']})",
                    min_value=0.0, step=1.0,
                    value=float(aj_datos["stock_actual"])
                )
                aj_min = st.number_input(
                    "Nuevo stock mínimo", min_value=0.0, step=1.0,
                    value=float(aj_datos["stock_minimo"])
                )
                sub_ajuste = st.form_submit_button("🔧 Aplicar ajuste", use_container_width=True)

            if sub_ajuste:
                actualizar_fila("inventario", "material", aj_material,
                                {"stock_actual": aj_nuevo, "stock_minimo": aj_min})
                st.success(f"✅ Inventario de **{aj_material}** ajustado a {aj_nuevo:.0f} {aj_datos['unidad']}.")

        with col_pi:
            st.markdown("**Estado actual del inventario**")
            inv_plot = inventario.sort_values("stock_actual").copy()
            inv_plot["color"]  = inv_plot["alerta"].map({True:"#e53935", False:"#43a047"})
            inv_plot["estado"] = inv_plot["alerta"].map({True:"⚠️ Bajo", False:"✅ OK"})

            fig_inv = go.Figure()
            fig_inv.add_trace(go.Bar(
                y=inv_plot["material"], x=inv_plot["stock_actual"],
                orientation="h", marker_color=inv_plot["color"],
                text=inv_plot["stock_actual"].astype(str)+" "+inv_plot["unidad"],
                textposition="outside", name="Stock actual"
            ))
            fig_inv.add_trace(go.Scatter(
                y=inv_plot["material"], x=inv_plot["stock_minimo"],
                mode="markers", name="Mínimo requerido",
                marker=dict(color="orange", size=10, symbol="line-ns-open", line_width=2)
            ))
            fig_inv.update_layout(
                title="Stock actual vs mínimo",
                height=420,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_inv, use_container_width=True)

            st.markdown("**Valor total del inventario**")
            inventario["valor_total"] = inventario["stock_actual"] * inventario["costo_unitario"]
            valor_total = inventario["valor_total"].sum()
            st.metric("💵 Valor en bodega", f"${valor_total:,.0f}")
