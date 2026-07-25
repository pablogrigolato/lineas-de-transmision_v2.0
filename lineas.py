import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Modelos de Línea", page_icon="⚡", layout="wide")

st.title("⚡ Comparación de Modelos de Línea: Corta, Media y Larga")
st.caption(
    "Modelo de dos puertos (ABCD) para los tres niveles de aproximación: serie pura, "
    "π nominal y parámetros distribuidos (solución exacta). Incluye perfil de tensión a "
    "lo largo de la línea, regulación, eficiencia y error de cada aproximación."
)

# ==================================================================
# Sidebar — parámetros
# ==================================================================
st.sidebar.header("⚙️ Configuración")
tipo_sistema = st.sidebar.selectbox("Tipo de sistema", ["Trifásico", "Monofásico"])

st.sidebar.header("Parámetros de línea")
length_km = st.sidebar.number_input("Longitud (km)", min_value=0.1, max_value=2000.0,
                                    value=100.0, step=1.0)
R_ohm = st.sidebar.number_input("R (Ω/km)", min_value=0.0, max_value=100.0,
                                value=0.05, step=0.0001, format="%.4f")
L_mH = st.sidebar.number_input("L (mH/km)", min_value=0.0, max_value=100.0,
                               value=0.50, step=0.0001, format="%.4f")
C_nF = st.sidebar.number_input("C (nF/km)", min_value=0.0, max_value=1000.0,
                               value=10.0, step=0.0001, format="%.4f")
G_uS = st.sidebar.number_input(
    "G (µS/km)", min_value=0.0, max_value=1000.0, value=0.0, step=0.001, format="%.3f",
    help="Conductancia shunt (fugas por aisladores / efecto corona). Normalmente "
         "despreciable; se incluye por completitud del modelo distribuido.",
)

st.sidebar.header("Carga y tensión")
f_Hz = st.sidebar.number_input("Frecuencia (Hz)", min_value=1.0, max_value=200.0,
                               value=50.0, step=0.01)

if tipo_sistema == "Trifásico":
    Vll_kV = st.sidebar.number_input("V_LL en la demanda (kV)", min_value=0.001,
                                     max_value=1500.0, value=230.0, step=0.1)
else:
    Vph_kV = st.sidebar.number_input("V en la demanda (kV)", min_value=0.001,
                                     max_value=1500.0, value=230.0, step=0.1)

P_MW = st.sidebar.number_input("P total en la demanda (MW)", min_value=-10000.0,
                               max_value=10000.0, value=50.0, step=1.0)
Q_Mvar = st.sidebar.number_input("Q total en la demanda (Mvar)", min_value=-10000.0,
                                 max_value=10000.0, value=10.0, step=1.0)

st.sidebar.caption(
    "Convención: la tensión de la demanda es el dato (referencia 0°) y se calcula "
    "hacia atrás la del generador."
)

# ==================================================================
# Conversión a unidades SI — parámetros TOTALES de la línea
# ==================================================================
omega = 2 * np.pi * f_Hz

# Parámetros por unidad de longitud (por km)
z_km = R_ohm + 1j * omega * (L_mH * 1e-3)          # Ω/km
y_km = (G_uS * 1e-6) + 1j * omega * (C_nF * 1e-9)  # S/km

# Parámetros totales de la línea
Z = z_km * length_km          # Ω
Y = y_km * length_km          # S

if tipo_sistema == "Trifásico":
    V_ph = (Vll_kV * 1e3) / np.sqrt(3)
    n_fases = 3
else:
    V_ph = Vph_kV * 1e3
    n_fases = 1

S_tot = P_MW * 1e6 + 1j * Q_Mvar * 1e6
S_ph = S_tot / n_fases

if V_ph <= 0:
    st.error("La tensión de la demanda debe ser mayor que cero.")
    st.stop()

# ------------------------------------------------------------------
# Constantes de propagación (con manejo del caso Y = 0)
# ------------------------------------------------------------------
# γℓ = sqrt(Z·Y) es ADIMENSIONAL (Z e Y ya son totales). γ por km = γℓ/longitud.
# Zc = sqrt(Z/Y) es independiente de la longitud.
Y_nulo = (abs(Y) < 1e-18)

if Y_nulo:
    # Línea sin admitancia shunt: el modelo distribuido degenera al serie puro.
    # Límites: γℓ → 0, Zc → ∞, pero Zc·sinh(γℓ) → Z y sinh(γℓ)/Zc → 0.
    gamma_l = 0.0 + 0.0j
    Zc = np.inf + 0j
else:
    gamma_l = np.sqrt(Z * Y)
    Zc = np.sqrt(Z / Y)

# Impedancia característica sin pérdidas (para SIL) y longitud de onda
Zsurge = np.sqrt((L_mH * 1e-3) / (C_nF * 1e-9)) if C_nF > 0 else np.inf
beta_km = np.imag(gamma_l) / length_km          # rad/km
lambda_km = (2 * np.pi / beta_km) if beta_km > 1e-15 else np.inf

# ==================================================================
# Matrices ABCD de los tres modelos
# ==================================================================
def abcd_modelos(Z, Y, gamma_l, Zc, Y_nulo):
    """Devuelve {nombre: (A, B, C, D)} para los tres niveles de aproximación."""
    # Corta: se desprecia por completo la admitancia shunt.
    corta = (1.0 + 0j, Z, 0.0 + 0j, 1.0 + 0j)

    # Media: π nominal — Y se concentra mitad y mitad en cada extremo.
    media = (1 + Z * Y / 2, Z, Y * (1 + Z * Y / 4), 1 + Z * Y / 2)

    # Larga: parámetros distribuidos (exacto).
    if Y_nulo:
        larga = corta          # límite analítico cuando Y → 0
    else:
        ch, sh = np.cosh(gamma_l), np.sinh(gamma_l)
        larga = (ch, Zc * sh, sh / Zc, ch)

    return {"Corta": corta, "Media (π nominal)": media, "Larga (distribuida)": larga}


MODELOS = abcd_modelos(Z, Y, gamma_l, Zc, Y_nulo)

# ==================================================================
# Resolución: dado el extremo receptor, se calcula el emisor
# ==================================================================
V_r = complex(V_ph)                 # referencia angular 0°
I_r = np.conj(S_ph / V_r)           # S = V·I*  ->  I = (S/V)*


def resolver(A, B, C, D):
    """Extremo emisor a partir del receptor, y magnitudes derivadas."""
    V_s = A * V_r + B * I_r
    I_s = C * V_r + D * I_r
    S_s_ph = V_s * np.conj(I_s)

    P_s = S_s_ph.real * n_fases
    Q_s = S_s_ph.imag * n_fases
    P_r = S_tot.real
    Q_r = S_tot.imag

    perdidas_P = P_s - P_r
    perdidas_Q = Q_s - Q_r
    rendimiento = (P_r / P_s * 100) if abs(P_s) > 1e-9 else np.nan

    # Regulación: (|Vr| en vacío − |Vr| a plena carga) / |Vr| a plena carga.
    # En vacío, I_r = 0  ->  V_r,vacío = V_s / A
    regulacion = ((abs(V_s) / abs(A) - abs(V_r)) / abs(V_r) * 100) if abs(A) > 1e-15 else np.nan

    # Verificación de reciprocidad de la red de dos puertos
    det = A * D - B * C

    return dict(V_s=V_s, I_s=I_s, P_s=P_s, Q_s=Q_s, P_r=P_r, Q_r=Q_r,
                perdidas_P=perdidas_P, perdidas_Q=perdidas_Q,
                rendimiento=rendimiento, regulacion=regulacion,
                A=A, B=B, C=C, D=D, det=det)


RES = {nombre: resolver(*abcd) for nombre, abcd in MODELOS.items()}
EXACTO = RES["Larga (distribuida)"]

# ==================================================================
# Métricas principales (modelo exacto)
# ==================================================================
k_ll = np.sqrt(3) if tipo_sistema == "Trifásico" else 1.0
etq_v = "V_LL" if tipo_sistema == "Trifásico" else "V"

st.subheader("Resultados del modelo exacto (línea larga)")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"{etq_v} generador",
          f"{abs(EXACTO['V_s']) * k_ll / 1e3:.2f} kV",
          f"{(abs(EXACTO['V_s']) / abs(V_r) - 1) * 100:+.2f} % vs demanda")
c2.metric("Regulación de tensión", f"{EXACTO['regulacion']:.2f} %",
          help="(|Vr| en vacío − |Vr| a plena carga) / |Vr| a plena carga, con |Vr,vacío| = |Vs|/|A|.")
c3.metric("Rendimiento", f"{EXACTO['rendimiento']:.2f} %")
c4.metric("Pérdidas activas", f"{EXACTO['perdidas_P'] / 1e6:.3f} MW")
c5.metric("Balance reactivo", f"{EXACTO['perdidas_Q'] / 1e6:+.3f} Mvar",
          help="Q generador − Q demanda. Negativo = la línea aporta reactivo neto "
               "(carga capacitiva dominante, típico en líneas largas poco cargadas).")

# ------------------------------------------------------------------
# Parámetros característicos de la línea
# ------------------------------------------------------------------
with st.expander("📐 Parámetros característicos de la línea", expanded=False):
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Z total", f"{abs(Z):.2f} Ω", f"∠{np.degrees(np.angle(Z)):.1f}°")
    p2.metric("Y total", f"{abs(Y) * 1e6:.2f} µS", f"∠{np.degrees(np.angle(Y)):.1f}°")
    if not Y_nulo:
        p3.metric("Zc (impedancia característica)", f"{abs(Zc):.2f} Ω",
                  f"∠{np.degrees(np.angle(Zc)):.1f}°")
        p4.metric("|γℓ| (adimensional)", f"{abs(gamma_l):.4f}",
                  help="α ℓ = atenuación (nepers), β ℓ = desfase (rad). Regla práctica: "
                       "|γℓ| ≲ 0.05 el modelo π nominal es suficiente.")
    else:
        p3.metric("Zc", "∞ (Y = 0)")
        p4.metric("|γℓ|", "0")

    q1, q2, q3 = st.columns(3)
    if np.isfinite(Zsurge):
        SIL = (Vll_kV ** 2 / Zsurge) if tipo_sistema == "Trifásico" else (Vph_kV ** 2 / Zsurge)
        q1.metric("Z_surge = √(L/C)", f"{Zsurge:.2f} Ω")
        q2.metric("SIL (potencia natural)", f"{SIL:.2f} MW",
                  help="Carga a la que la línea consume exactamente el reactivo que genera; "
                       "el perfil de tensión queda plano.")
    if np.isfinite(lambda_km):
        q3.metric("Longitud de onda λ", f"{lambda_km:,.0f} km",
                  f"línea = {length_km / lambda_km * 100:.2f} % de λ")

st.markdown("---")

# ==================================================================
# Pestañas
# ==================================================================
tabs = st.tabs([
    "📋 Tablas", "📉 Perfil a lo largo de la línea", "🧭 Diagrama fasorial",
    "🔍 Error de los modelos", "🔌 Esquemas unifilares", "✅ Verificación",
])

# ------------------------------------------------------------------
# TAB 0 — Tablas
# ------------------------------------------------------------------
with tabs[0]:
    st.subheader("Tensiones y corrientes")

    filas_vc = []
    for nombre, r in RES.items():
        v_s, i_s = r["V_s"], r["I_s"]
        fila = {
            "Modelo": nombre,
            "Vph generador": f"{abs(v_s)/1e3:.3f} ∠ {np.degrees(np.angle(v_s)):.2f}° kV",
            "Iph generador": f"{abs(i_s):.2f} ∠ {np.degrees(np.angle(i_s)):.2f}° A",
            "Vph demanda": f"{abs(V_r)/1e3:.3f} ∠ 0.00° kV",
            "Iph demanda": f"{abs(I_r):.2f} ∠ {np.degrees(np.angle(I_r)):.2f}° A",
        }
        if tipo_sistema == "Trifásico":
            # V_LL = √3 · V_fase ∠ +30° (secuencia ABC)
            fila = {
                "Modelo": nombre,
                "Vph generador": fila["Vph generador"],
                "Vll generador": f"{abs(v_s)*np.sqrt(3)/1e3:.3f} ∠ "
                                 f"{np.degrees(np.angle(v_s))+30:.2f}° kV",
                "Iph generador": fila["Iph generador"],
                "Vph demanda": fila["Vph demanda"],
                "Vll demanda": f"{abs(V_r)*np.sqrt(3)/1e3:.3f} ∠ 30.00° kV",
                "Iph demanda": fila["Iph demanda"],
            }
        filas_vc.append(fila)

    df_vc = pd.DataFrame(filas_vc)
    st.dataframe(df_vc, use_container_width=True, hide_index=True)

    st.subheader("Potencias, pérdidas y desempeño")
    df_pq = pd.DataFrame([{
        "Modelo": nombre,
        "P gen (MW)": r["P_s"] / 1e6,
        "Q gen (Mvar)": r["Q_s"] / 1e6,
        "P dem (MW)": r["P_r"] / 1e6,
        "Q dem (Mvar)": r["Q_r"] / 1e6,
        "Pérdidas P (MW)": r["perdidas_P"] / 1e6,
        "Balance Q (Mvar)": r["perdidas_Q"] / 1e6,
        "Regulación (%)": r["regulacion"],
        "Rendimiento (%)": r["rendimiento"],
    } for nombre, r in RES.items()])
    st.dataframe(df_pq.style.format({c: "{:.3f}" for c in df_pq.columns if c != "Modelo"}),
                 use_container_width=True, hide_index=True)

    st.subheader("Constantes ABCD")
    df_abcd = pd.DataFrame([{
        "Modelo": nombre,
        "A = D": f"{abs(r['A']):.5f} ∠ {np.degrees(np.angle(r['A'])):.3f}°",
        "B (Ω)": f"{abs(r['B']):.3f} ∠ {np.degrees(np.angle(r['B'])):.3f}°",
        "C (µS)": f"{abs(r['C'])*1e6:.4f} ∠ {np.degrees(np.angle(r['C'])):.3f}°",
        "AD − BC": f"{r['det'].real:.9f} {r['det'].imag:+.2e}j",
    } for nombre, r in RES.items()])
    st.dataframe(df_abcd, use_container_width=True, hide_index=True)

    csv = df_pq.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Descargar resultados (CSV)", csv,
                       file_name="modelos_linea_resultados.csv", mime="text/csv")

# ------------------------------------------------------------------
# TAB 1 — Perfil de tensión y corriente a lo largo de la línea
# ------------------------------------------------------------------
with tabs[1]:
    st.subheader("Perfil de tensión y corriente")
    st.caption(
        "Solución exacta de la línea distribuida evaluada en cada punto: "
        "V(x) = cosh(γx)·Vr + Zc·sinh(γx)·Ir, con x medido desde la demanda. "
        "Sólo el modelo largo describe el interior de la línea; los otros dos "
        "aparecen como puntos en el extremo generador."
    )

    n_pts = 400
    x_desde_dem = np.linspace(0.0, length_km, n_pts)   # km desde la demanda
    x_desde_gen = length_km - x_desde_dem              # km desde el generador

    if Y_nulo:
        V_x = V_r + (z_km * x_desde_dem) * I_r
        I_x = np.full_like(x_desde_dem, I_r, dtype=complex)
    else:
        gamma_km = gamma_l / length_km
        gx = gamma_km * x_desde_dem
        V_x = np.cosh(gx) * V_r + Zc * np.sinh(gx) * I_r
        I_x = (np.sinh(gx) / Zc) * V_r + np.cosh(gx) * I_r

    Vmag_kV = np.abs(V_x) * k_ll / 1e3
    Imag_A = np.abs(I_x)

    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(
        x=x_desde_gen, y=Vmag_kV, mode="lines", name=f"|{etq_v}| (kV)",
        line=dict(color="#22a884", width=3),
        hovertemplate="x = %{x:.1f} km<br>|V| = %{y:.2f} kV<extra></extra>",
    ))
    fig_perf.add_trace(go.Scatter(
        x=x_desde_gen, y=Imag_A, mode="lines", name="|I| (A)", yaxis="y2",
        line=dict(color="#e69f00", width=2, dash="dot"),
        hovertemplate="x = %{x:.1f} km<br>|I| = %{y:.1f} A<extra></extra>",
    ))

    # Puntos del extremo emisor según cada modelo aproximado
    marcadores = {"Corta": "#d62728", "Media (π nominal)": "#9467bd"}
    for nombre, color in marcadores.items():
        fig_perf.add_trace(go.Scatter(
            x=[0.0], y=[abs(RES[nombre]["V_s"]) * k_ll / 1e3],
            mode="markers", name=f"{nombre} — emisor",
            marker=dict(size=11, color=color, symbol="diamond",
                        line=dict(color="#fff", width=1)),
            hovertemplate=f"{nombre}<br>|V| = %{{y:.2f}} kV<extra></extra>",
        ))

    fig_perf.add_hline(y=abs(V_r) * k_ll / 1e3, line=dict(color="#888", dash="dash", width=1),
                       annotation_text="tensión de la demanda", annotation_position="bottom right")

    fig_perf.update_layout(
        xaxis=dict(title="Distancia desde el generador (km)"),
        yaxis=dict(title=f"|{etq_v}| (kV)", color="#22a884"),
        yaxis2=dict(title="|I| (A)", overlaying="y", side="right", color="#e69f00",
                    showgrid=False),
        height=460, hovermode="x unified",
        legend=dict(orientation="h", y=1.12, font=dict(size=11)),
        margin=dict(l=20, r=20, t=40, b=40),
    )
    st.plotly_chart(fig_perf, use_container_width=True, config={"displaylogo": False})

    if np.isfinite(Zsurge):
        P_dem = abs(S_tot.real) / 1e6
        SIL_v = (Vll_kV ** 2 / Zsurge) if tipo_sistema == "Trifásico" else (Vph_kV ** 2 / Zsurge)
        if SIL_v > 0:
            if P_dem < 0.9 * SIL_v:
                st.info(f"Carga ({P_dem:.1f} MW) por debajo del SIL ({SIL_v:.1f} MW): "
                        "la línea genera más reactivo del que consume y la tensión tiende "
                        "a subir hacia la demanda (efecto Ferranti).")
            elif P_dem > 1.1 * SIL_v:
                st.info(f"Carga ({P_dem:.1f} MW) por encima del SIL ({SIL_v:.1f} MW): "
                        "consumo reactivo dominante, la tensión cae a lo largo de la línea.")
            else:
                st.success(f"Carga ({P_dem:.1f} MW) próxima al SIL ({SIL_v:.1f} MW): "
                           "perfil de tensión prácticamente plano.")

    df_perfil = pd.DataFrame({
        "x_desde_generador_km": x_desde_gen,
        "V_magnitud_kV": Vmag_kV,
        "V_angulo_deg": np.degrees(np.angle(V_x)),
        "I_magnitud_A": Imag_A,
        "I_angulo_deg": np.degrees(np.angle(I_x)),
    })
    st.download_button("⬇ Descargar perfil (CSV)",
                       df_perfil.to_csv(index=False).encode("utf-8"),
                       file_name="perfil_linea.csv", mime="text/csv")

# ------------------------------------------------------------------
# TAB 2 — Diagrama fasorial
# ------------------------------------------------------------------
with tabs[2]:
    st.subheader("Diagrama fasorial")
    st.caption(
        "Tensiones de fase en kV y corrientes escaladas para que sean comparables "
        "en el mismo plano. La demanda está tomada como referencia (0°)."
    )

    v_kv = [abs(V_r) / 1e3] + [abs(r["V_s"]) / 1e3 for r in RES.values()]
    i_a = [abs(I_r)] + [abs(r["I_s"]) for r in RES.values()]
    escala_i = (max(v_kv) / max(i_a) * 0.55) if max(i_a) > 1e-9 else 1.0

    fig_fas = go.Figure()

    def add_fasor(z, nombre, color, escala=1.0, dash="solid"):
        x, y = z.real * escala, z.imag * escala
        fig_fas.add_trace(go.Scatter(
            x=[0, x], y=[0, y], mode="lines+markers", name=nombre,
            line=dict(color=color, width=2.5, dash=dash),
            marker=dict(size=[0, 9], color=color, symbol="arrow-bar-up",
                        angleref="previous"),
            hovertemplate=f"{nombre}<br>%{{customdata[0]:.3f}} ∠ %{{customdata[1]:.2f}}°<extra></extra>",
            customdata=[[abs(z), np.degrees(np.angle(z))]] * 2,
        ))

    add_fasor(V_r / 1e3, "Vr (demanda)", "#ffffff")
    colores_mod = {"Corta": "#d62728", "Media (π nominal)": "#9467bd",
                   "Larga (distribuida)": "#22a884"}
    for nombre, r in RES.items():
        add_fasor(r["V_s"] / 1e3, f"Vs — {nombre}", colores_mod[nombre])

    add_fasor(I_r, "Ir (demanda)", "#e69f00", escala_i, "dot")
    add_fasor(RES["Larga (distribuida)"]["I_s"], "Is — Larga", "#7ad151", escala_i, "dot")

    lim = max(max(v_kv), max(i_a) * escala_i) * 1.2
    fig_fas.update_layout(
        xaxis=dict(title="Real", range=[-lim * 0.35, lim], zeroline=True,
                   zerolinecolor="rgba(128,128,128,0.5)"),
        yaxis=dict(title="Imaginario", range=[-lim * 0.6, lim * 0.6],
                   scaleanchor="x", scaleratio=1, zeroline=True,
                   zerolinecolor="rgba(128,128,128,0.5)"),
        height=520, legend=dict(font=dict(size=10)),
        margin=dict(l=20, r=20, t=30, b=40),
    )
    st.plotly_chart(fig_fas, use_container_width=True, config={"displaylogo": False})

    delta = np.degrees(np.angle(EXACTO["V_s"])) - 0.0
    st.caption(
        f"Ángulo de carga δ (entre Vs y Vr, modelo exacto): **{delta:.2f}°**. "
        f"Corrientes dibujadas con factor de escala {escala_i:.4f} kV/A."
    )

# ------------------------------------------------------------------
# TAB 3 — Error de los modelos aproximados
# ------------------------------------------------------------------
with tabs[3]:
    st.subheader("Error de las aproximaciones respecto del modelo exacto")

    ref = EXACTO
    filas_err = []
    for nombre, r in RES.items():
        if nombre == "Larga (distribuida)":
            continue
        filas_err.append({
            "Modelo": nombre,
            "Error |Vs| (%)": (abs(r["V_s"]) - abs(ref["V_s"])) / abs(ref["V_s"]) * 100,
            "Error ∠Vs (°)": np.degrees(np.angle(r["V_s"]) - np.angle(ref["V_s"])),
            "Error |Is| (%)": (abs(r["I_s"]) - abs(ref["I_s"])) / abs(ref["I_s"]) * 100
                              if abs(ref["I_s"]) > 1e-9 else np.nan,
            "Error pérdidas P (%)": (r["perdidas_P"] - ref["perdidas_P"]) / ref["perdidas_P"] * 100
                                    if abs(ref["perdidas_P"]) > 1e-6 else np.nan,
            "Error regulación (p.p.)": r["regulacion"] - ref["regulacion"],
        })
    df_err = pd.DataFrame(filas_err)
    st.dataframe(df_err.style.format({c: "{:+.4f}" for c in df_err.columns if c != "Modelo"}),
                 use_container_width=True, hide_index=True)

    st.markdown("**Cómo crece el error con la longitud** (mismos parámetros por km y misma carga):")

    longitudes = np.linspace(5, max(600.0, length_km * 1.5), 80)
    err_corta, err_media = [], []
    for Lk in longitudes:
        Z_l = z_km * Lk
        Y_l = y_km * Lk
        if abs(Y_l) < 1e-18:
            err_corta.append(0.0)
            err_media.append(0.0)
            continue
        g_l = np.sqrt(Z_l * Y_l)
        Zc_l = np.sqrt(Z_l / Y_l)
        vs_c = 1 * V_r + Z_l * I_r
        vs_m = (1 + Z_l * Y_l / 2) * V_r + Z_l * I_r
        vs_e = np.cosh(g_l) * V_r + Zc_l * np.sinh(g_l) * I_r
        err_corta.append((abs(vs_c) - abs(vs_e)) / abs(vs_e) * 100)
        err_media.append((abs(vs_m) - abs(vs_e)) / abs(vs_e) * 100)

    fig_err = go.Figure()
    fig_err.add_trace(go.Scatter(x=longitudes, y=err_corta, mode="lines", name="Corta",
                                 line=dict(color="#d62728", width=2.5)))
    fig_err.add_trace(go.Scatter(x=longitudes, y=err_media, mode="lines", name="Media (π nominal)",
                                 line=dict(color="#9467bd", width=2.5)))
    fig_err.add_hline(y=0, line=dict(color="#888", width=1))
    for lim_err, txt in [(1.0, "1 %"), (-1.0, None)]:
        fig_err.add_hline(y=lim_err, line=dict(color="#666", dash="dot", width=1),
                          annotation_text=txt, annotation_position="top left")
    fig_err.add_vline(x=length_km, line=dict(color="#22a884", dash="dash", width=2),
                      annotation_text=f"longitud actual ({length_km:.0f} km)",
                      annotation_position="top right")
    fig_err.update_layout(
        xaxis_title="Longitud de línea (km)",
        yaxis_title="Error en |Vs| respecto del modelo exacto (%)",
        height=420, hovermode="x unified",
        margin=dict(l=20, r=20, t=30, b=40),
    )
    st.plotly_chart(fig_err, use_container_width=True, config={"displaylogo": False})

    st.caption(
        "Criterio habitual: por debajo de ~80 km el modelo corto alcanza; entre ~80 y "
        "~250 km se usa el π nominal; por encima conviene el modelo distribuido. "
        "El indicador independiente de la longitud es |γℓ|: mientras se mantenga "
        "por debajo de ~0.05 el π nominal es adecuado."
    )

# ------------------------------------------------------------------
# TAB 4 — Esquemas unifilares
# ------------------------------------------------------------------
with tabs[4]:
    st.subheader("Esquemas unifilares")

    COL_LINEA = "#9aa0a6"
    COL_TXT = "#c9d1d9"

    def _cap(fig, x, y_top, y_bot):
        """Símbolo de capacitor + tierra en una rama shunt vertical."""
        y_mid = (y_top + y_bot) / 2
        fig.add_shape(type="line", x0=x, x1=x, y0=y_top, y1=y_mid + 0.035,
                      line=dict(color=COL_LINEA, width=2))
        for dy in (0.035, 0.0):
            fig.add_shape(type="line", x0=x - 0.035, x1=x + 0.035,
                          y0=y_mid + dy, y1=y_mid + dy,
                          line=dict(color=COL_LINEA, width=3))
        fig.add_shape(type="line", x0=x, x1=x, y0=y_mid, y1=y_bot + 0.05,
                      line=dict(color=COL_LINEA, width=2))
        for i, w in enumerate([0.045, 0.030, 0.015]):
            fig.add_shape(type="line", x0=x - w, x1=x + w,
                          y0=y_bot + 0.05 - i * 0.022, y1=y_bot + 0.05 - i * 0.022,
                          line=dict(color=COL_LINEA, width=2))

    def esquema(nombre, r):
        fig = go.Figure()
        Y_L = 0.68           # altura del conductor
        Y_G = 0.18           # nivel de tierra

        # Conductor
        fig.add_shape(type="line", x0=0.10, x1=0.90, y0=Y_L, y1=Y_L,
                      line=dict(color=COL_LINEA, width=3))
        # Barras de los extremos
        for x in (0.10, 0.90):
            fig.add_shape(type="line", x0=x, x1=x, y0=Y_L - 0.13, y1=Y_L + 0.13,
                          line=dict(color=COL_LINEA, width=5))

        # Impedancia serie (rectángulo)
        fig.add_shape(type="rect", x0=0.44, x1=0.56, y0=Y_L - 0.05, y1=Y_L + 0.05,
                      line=dict(color=COL_LINEA, width=2), fillcolor="rgba(34,168,132,0.25)")

        if nombre == "Corta":
            z_txt = f"Z = {abs(Z):.2f} ∠{np.degrees(np.angle(Z)):.1f}° Ω"
            sub = "Sin rama shunt: se desprecia Y por completo."
        elif nombre.startswith("Media"):
            z_txt = f"Z = {abs(Z):.2f} ∠{np.degrees(np.angle(Z)):.1f}° Ω"
            sub = "π nominal: Y se reparte en dos mitades iguales."
            if not Y_nulo:
                for x in (0.26, 0.74):
                    _cap(fig, x, Y_L, Y_G)
                fig.add_annotation(x=0.26, y=Y_L - 0.10, showarrow=False,
                                   text=f"Y/2 = {abs(Y)/2*1e6:.2f} µS", font=dict(size=11, color=COL_TXT))
                fig.add_annotation(x=0.74, y=Y_L - 0.10, showarrow=False,
                                   text=f"Y/2 = {abs(Y)/2*1e6:.2f} µS", font=dict(size=11, color=COL_TXT))
        else:
            # π equivalente EXACTO: Z' = Zc·sinh(γℓ), Y'/2 = tanh(γℓ/2)/Zc
            if Y_nulo:
                Zp, Yp2 = Z, 0.0 + 0j
            else:
                Zp = Zc * np.sinh(gamma_l)
                Yp2 = np.tanh(gamma_l / 2) / Zc
            z_txt = f"Z' = {abs(Zp):.2f} ∠{np.degrees(np.angle(Zp)):.1f}° Ω"
            sub = ("π equivalente exacto: Z' = Zc·senh(γℓ), Y'/2 = tgh(γℓ/2)/Zc. "
                   "Reproduce la línea distribuida sin error.")
            if not Y_nulo:
                for x in (0.26, 0.74):
                    _cap(fig, x, Y_L, Y_G)
                for x in (0.26, 0.74):
                    fig.add_annotation(x=x, y=Y_L - 0.10, showarrow=False,
                                       text=f"Y'/2 = {abs(Yp2)*1e6:.2f} µS",
                                       font=dict(size=11, color=COL_TXT))

        fig.add_annotation(x=0.50, y=Y_L + 0.11, showarrow=False, text=z_txt,
                           font=dict(size=12, color=COL_TXT))

        # Flechas de corriente (axref/ayref en coordenadas de datos)
        fig.add_annotation(x=0.30, y=Y_L + 0.05, ax=0.16, ay=Y_L + 0.05,
                           axref="x", ayref="y", xref="x", yref="y",
                           arrowhead=3, arrowcolor="#e15759", arrowwidth=2,
                           text=f"Is = {abs(r['I_s']):.1f} ∠{np.degrees(np.angle(r['I_s'])):.1f}° A",
                           font=dict(size=11, color="#e15759"), yshift=16)
        fig.add_annotation(x=0.84, y=Y_L + 0.05, ax=0.70, ay=Y_L + 0.05,
                           axref="x", ayref="y", xref="x", yref="y",
                           arrowhead=3, arrowcolor="#e15759", arrowwidth=2,
                           text=f"Ir = {abs(I_r):.1f} ∠{np.degrees(np.angle(I_r)):.1f}° A",
                           font=dict(size=11, color="#e15759"), yshift=16)

        # Rótulos de extremos (Plotly requiere <br>, no \n)
        v_s = r["V_s"]
        gen = (f"<b>Generador</b><br>Vph = {abs(v_s)/1e3:.2f} ∠{np.degrees(np.angle(v_s)):.1f}° kV")
        dem = (f"<b>Demanda</b><br>Vph = {abs(V_r)/1e3:.2f} ∠0.0° kV")
        if tipo_sistema == "Trifásico":
            gen += f"<br>Vll = {abs(v_s)*np.sqrt(3)/1e3:.2f} ∠{np.degrees(np.angle(v_s))+30:.1f}° kV"
            dem += f"<br>Vll = {abs(V_r)*np.sqrt(3)/1e3:.2f} ∠30.0° kV"
        fig.add_annotation(x=0.10, y=Y_L + 0.20, showarrow=False, text=gen,
                           font=dict(size=11, color=COL_TXT), align="center")
        fig.add_annotation(x=0.90, y=Y_L + 0.20, showarrow=False, text=dem,
                           font=dict(size=11, color=COL_TXT), align="center")

        fig.add_annotation(
            x=0.5, y=0.06, showarrow=False, align="center",
            text=(f"Generador: P = {r['P_s']/1e6:.2f} MW   Q = {r['Q_s']/1e6:.2f} Mvar<br>"
                  f"Demanda: P = {P_MW:.2f} MW   Q = {Q_Mvar:.2f} Mvar<br>"
                  f"Pérdidas: {r['perdidas_P']/1e6:.3f} MW   |   η = {r['rendimiento']:.2f} %"),
            bgcolor="rgba(0,0,0,0.55)", bordercolor=COL_LINEA, borderwidth=1,
            borderpad=6, font=dict(size=11, color=COL_TXT),
        )

        fig.update_xaxes(visible=False, range=[0, 1])
        fig.update_yaxes(visible=False, range=[0, 1])
        fig.update_layout(title_text=nombre, title_x=0.5, height=430,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=5, r=5, t=40, b=5))
        return fig, sub

    sub_tabs = st.tabs(list(RES.keys()))
    for st_tab, (nombre, r) in zip(sub_tabs, RES.items()):
        with st_tab:
            fig, sub = esquema(nombre, r)
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
            st.caption(sub)

# ------------------------------------------------------------------
# TAB 5 — Verificación
# ------------------------------------------------------------------
with tabs[5]:
    st.subheader("Verificación del modelo")

    st.markdown("**1. Reciprocidad de la red de dos puertos: AD − BC = 1**")
    ok_todos = True
    for nombre, r in RES.items():
        err = abs(r["det"] - 1)
        ok = err < 1e-9
        ok_todos &= ok
        st.write(f"{'✅' if ok else '❌'} {nombre}: AD − BC = "
                 f"{r['det'].real:.12f} {r['det'].imag:+.2e}j  (error {err:.2e})")
    if ok_todos:
        st.success("Las tres matrices ABCD son recíprocas, como corresponde a una red pasiva "
                   "y bilateral. Además A = D en las tres, por simetría de la línea.")

    st.markdown("**2. Balance de potencia**")
    st.write(f"P generador − P demanda = {EXACTO['perdidas_P']/1e6:.4f} MW "
             f"({'consumo' if EXACTO['perdidas_P'] > 0 else 'aporte'} neto de la línea)")
    st.write(f"Q generador − Q demanda = {EXACTO['perdidas_Q']/1e6:+.4f} Mvar")

    st.markdown("**3. Coherencia entre modelos**")
    st.write(f"|γℓ| = {abs(gamma_l):.5f} → "
             + ("el π nominal es adecuado (|γℓ| < 0.05)." if abs(gamma_l) < 0.05
                else "conviene el modelo distribuido (|γℓ| ≥ 0.05)."))

    with st.expander("📖 Formulación empleada"):
        st.latex(r"\begin{bmatrix} V_s \\ I_s \end{bmatrix} = "
                 r"\begin{bmatrix} A & B \\ C & D \end{bmatrix}"
                 r"\begin{bmatrix} V_r \\ I_r \end{bmatrix}")
        st.markdown("**Línea corta** — se desprecia la admitancia shunt:")
        st.latex(r"A = D = 1, \quad B = Z, \quad C = 0")
        st.markdown("**Línea media (π nominal)** — la admitancia se concentra en los extremos:")
        st.latex(r"A = D = 1 + \frac{ZY}{2}, \quad B = Z, \quad C = Y\left(1 + \frac{ZY}{4}\right)")
        st.markdown("**Línea larga (parámetros distribuidos)** — solución exacta:")
        st.latex(r"A = D = \cosh(\gamma \ell), \quad B = Z_c \sinh(\gamma \ell), "
                 r"\quad C = \frac{\sinh(\gamma \ell)}{Z_c}")
        st.latex(r"\gamma = \sqrt{zy}, \quad Z_c = \sqrt{\frac{z}{y}}, \quad "
                 r"z = R + j\omega L, \quad y = G + j\omega C")
        st.markdown("**Regulación de tensión** y **rendimiento**:")
        st.latex(r"RV\% = \frac{|V_s|/|A| - |V_r|}{|V_r|} \times 100, \qquad "
                 r"\eta\% = \frac{P_r}{P_s} \times 100")
        st.markdown(
            "Los parámetros $z$ e $y$ son por unidad de longitud; $Z = z\\ell$ e $Y = y\\ell$ "
            "son los totales. Nótese que $\\gamma\\ell = \\sqrt{ZY}$ es adimensional y que "
            "$Z_c = \\sqrt{Z/Y} = \\sqrt{z/y}$ no depende de la longitud."
        )
