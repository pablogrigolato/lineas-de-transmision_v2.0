import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

st.title("Comparación de Modelos de Línea: Corta, Media y Larga")

# Sidebar: tipo de sistema y parámetros
st.sidebar.header("Configuración")
tipo_sistema = st.sidebar.selectbox("Tipo de sistema", ["Trifásico", "Monofásico"])

st.sidebar.header("Parámetros de Línea")
length_km = st.sidebar.number_input("Longitud (km)", min_value=0.1, max_value=1000.0, value=100.0, step=0.01)
R_ohm = st.sidebar.number_input("R (Ω/km)", min_value=0.0, max_value=100.0, value=0.05, step=0.0001, format="%.4f")
L_mH = st.sidebar.number_input("L (mH/km)", min_value=0.0, max_value=100.0, value=0.50, step=0.0001, format="%.4f")
C_nF = st.sidebar.number_input("C (nF/km)", min_value=0.0, max_value=100.0, value=10.0, step=0.0001, format="%.4f")

st.sidebar.header("Carga")
f_Hz = st.sidebar.number_input("Frecuencia (Hz)", min_value=1.0, max_value=200.0, value=50.0, step=0.0001)

if tipo_sistema == "Trifásico":
    Vll_kV = st.sidebar.number_input("V_LL (kV)", min_value=0.0, max_value=500.0, value=230.0, step=0.0001)
else:
    Vph_kV = st.sidebar.number_input("V (kV)", min_value=0.0, max_value=500.0, value=230.0, step=0.0001)

P_MW = st.sidebar.number_input("P total (MW)", min_value=-10000.0, max_value=10000.0, value=50.0, step=0.01)
Q_Mvar = st.sidebar.number_input("Q total (Mvar)", min_value=-10000.0, max_value=10000.0, value=10.0, step=0.01)

# Conversión a unidades
ω = 2 * np.pi * f_Hz
ℓ = length_km * 1e3
R = R_ohm * length_km
L = L_mH * 1e-3 * length_km
C = C_nF * 1e-9 * length_km

if tipo_sistema == "Trifásico":
    V_ll = Vll_kV * 1e3
    V_ph = V_ll / np.sqrt(3)
    S_tot = P_MW * 1e6 + 1j * Q_Mvar * 1e6
    S_ph = S_tot / 3
else:
    V_ph = Vph_kV * 1e3
    V_ll = None
    S_tot = P_MW * 1e6 + 1j * Q_Mvar * 1e6
    S_ph = S_tot    # en monofásico la potencia total se usa tal cual

# Parámetros por fase (misma fórmula para mono/trifásico sobre la fase considerada)
Z = R + 1j * ω * L
Y = 1j * ω * C
γ = np.sqrt(Z * Y)
Zc = np.sqrt(Z / Y)

A1, B1, C1, D1 = 1, Z, 0, 1
A2, B2, C2, D2 = 1 + Z * Y / 2, Z, Y * (1 + Z * Y / 4), 1 + Z * Y / 2
A3, B3, C3, D3 = np.cosh(γ), Zc * np.sinh(γ), (1 / Zc) * np.sinh(γ), np.cosh(γ)

def enviar(A, B, C, D, S_phase, V_phase):
    I_ph = np.conj(S_phase / V_phase)
    V_s = A * V_phase + B * I_ph
    I_s = C * V_phase + D * I_ph
    S_s = V_s * np.conj(I_s)
    factor = 3 if tipo_sistema == "Trifásico" else 1
    return V_s, I_s, S_s.real * factor, S_s.imag * factor

V1, I1, P1, Q1 = enviar(A1, B1, C1, D1, S_ph, V_ph)
V2, I2, P2, Q2 = enviar(A2, B2, C2, D2, S_ph, V_ph)
V3, I3, P3, Q3 = enviar(A3, B3, C3, D3, S_ph, V_ph)

def mag_ang(z):
    return abs(z), np.degrees(np.angle(z))

# Magnitudes y ángulos en kV / A
Vs1_ph, a1_vs = mag_ang(V1 / 1e3)
Is1_ph, a1_is = mag_ang(I1)
Vs2_ph, a2_vs = mag_ang(V2 / 1e3)
Is2_ph, a2_is = mag_ang(I2)
Vs3_ph, a3_vs = mag_ang(V3 / 1e3)
Is3_ph, a3_is = mag_ang(I3)

Vr_ph, a_vr = mag_ang(V_ph / 1e3)
Ir_ph, a_ir = mag_ang(np.conj(S_ph / V_ph))

# Conversiones y representación para trifásico (si aplica)
def compute_vll_info(v_ph_kv, ang_ph_deg):
    """Devuelve (vll_float, ang_ll_float) o (None, None) si no aplica."""
    if v_ph_kv is None:
        return None, None
    vll = float(v_ph_kv) * np.sqrt(3)
    ang_ll = float(ang_ph_deg) + 30.0
    return vll, ang_ll

if tipo_sistema == "Trifásico":
    Vs1_ll_val, a1_vll = compute_vll_info(Vs1_ph, a1_vs)
    Vs2_ll_val, a2_vll = compute_vll_info(Vs2_ph, a2_vs)
    Vs3_ll_val, a3_vll = compute_vll_info(Vs3_ph, a3_vs)
    Vr_ll_val, a_vll = compute_vll_info(Vr_ph, a_vr)
else:
    Vs1_ll_val = Vs2_ll_val = Vs3_ll_val = Vr_ll_val = None
    a1_vll = a2_vll = a3_vll = a_vll = None

# Tablas de resultados (strings preparados según sistema)
def fmt_v(v_ph, ang_ph, vll_val, ang_ll, is_ph, ang_i):
    vph_text = f"{v_ph:.2f}∠{ang_ph:.1f} kV"
    if vll_val is None:
        vll_text = "-"
    else:
        vll_text = f"{vll_val:.2f}∠{ang_ll:.1f} kV"
    iph_text = f"{is_ph:.1f}∠{ang_i:.1f} A"
    return vph_text, vll_text, iph_text

r1 = ["Corta", *fmt_v(Vs1_ph, a1_vs, Vs1_ll_val, a1_vll, Is1_ph, a1_is),
      f"{Vr_ph:.2f}∠{a_vr:.1f} kV", (f"{Vr_ll_val:.2f}∠{a_vll:.1f} kV" if Vr_ll_val is not None else "-"),
      f"{Ir_ph:.1f}∠{a_ir:.1f} A"]
r2 = ["Media", *fmt_v(Vs2_ph, a2_vs, Vs2_ll_val, a2_vll, Is2_ph, a2_is),
      f"{Vr_ph:.2f}∠{a_vr:.1f} kV", (f"{Vr_ll_val:.2f}∠{a_vll:.1f} kV" if Vr_ll_val is not None else "-"),
      f"{Ir_ph:.1f}∠{a_ir:.1f} A"]
r3 = ["Larga", *fmt_v(Vs3_ph, a3_vs, Vs3_ll_val, a3_vll, Is3_ph, a3_is),
      f"{Vr_ph:.2f}∠{a_vr:.1f} kV", (f"{Vr_ll_val:.2f}∠{a_vll:.1f} kV" if Vr_ll_val is not None else "-"),
      f"{Ir_ph:.1f}∠{a_ir:.1f} A"]

df_vc = pd.DataFrame([r1, r2, r3], columns=[
    "Modelo", "Vph Generador", "Vll Generador", "Iph Generador",
    "Vph Demanda", "Vll Demanda", "Iph Demanda"
])

df_pq = pd.DataFrame([
    ["Corta", f"{P1/1e6:.2f}", f"{Q1/1e6:.2f}", f"{P_MW:.2f}", f"{Q_Mvar:.2f}"],
    ["Media", f"{P2/1e6:.2f}", f"{Q2/1e6:.2f}", f"{P_MW:.2f}", f"{Q_Mvar:.2f}"],
    ["Larga", f"{P3/1e6:.2f}", f"{Q3/1e6:.2f}", f"{P_MW:.2f}", f"{Q_Mvar:.2f}"],
], columns=["Modelo", "P Generador (MW)", "Q Generador (Mvar)", "P Demanda (MW)", "Q Demanda (Mvar)"])

# Figura: adaptada para mostrar/ocultar Vll según tipo y con formateo seguro
def _fmt_vll_text(vll_val, ang_ll):
    if vll_val is None:
        return ""
    return f"Vll={vll_val:.1f}∠{ang_ll:.1f}° kV"

def create_figure(title, Vs_ph, Vs_ang, Vs_ll, Vs_ll_ang, Is_ph, Is_ang, Vr_ph, Vr_ang, Vr_ll, Vr_ll_ang, Ir_ph, Ir_ang, P_s, Q_s, gamma_l=None, shunt=False):
    fig = go.Figure()
    fig.add_shape(type="line", x0=0.1, x1=0.9, y0=0.5, y1=0.5, line=dict(color="white", width=4))
    fig.add_shape(type="circle", x0=0.08, x1=0.12, y0=0.45, y1=0.55, line=dict(color="white", width=2))
    fig.add_shape(type="circle", x0=0.88, x1=0.92, y0=0.45, y1=0.55, line=dict(color="white", width=2))
    for x in (0.2, 0.8):
        fig.add_shape(
            type="line",
            x0=x, x1=x, y0=0.4, y1=0.6,
            line=dict(color="white", width=3)
        )
    #    fig.add_annotation(x=x, y=0.35, text="Y/2", showarrow=False)

    vll_gen_text = _fmt_vll_text(Vs_ll, Vs_ll_ang)
    vll_dem_text = _fmt_vll_text(Vr_ll, Vr_ll_ang)

    gen_text = f"Generador\nVph={Vs_ph:.1f}∠{Vs_ang:.1f}° kV"
    if vll_gen_text:
        gen_text += f"\n{vll_gen_text}"

    dem_text = f"Demanda\nVph={Vr_ph:.1f}∠{Vr_ang:.1f}° kV"
    if vll_dem_text:
        dem_text += f"\n{vll_dem_text}"

    fig.add_annotation(x=0.3, y=0.6, ax=0.1, ay=0.6, arrowhead=3, arrowcolor="green", arrowwidth=2, text=gen_text)
    fig.add_annotation(x=0.7, y=0.6, ax=0.9, ay=0.6, arrowhead=3, arrowcolor="green", arrowwidth=2, text=dem_text)

    fig.add_annotation(x=0.3, y=0.4, ax=0.1, ay=0.4, arrowhead=3, arrowcolor="red", arrowwidth=2, text=f"Iph={Is_ph:.0f}∠{Is_ang:.1f}° A")
    fig.add_annotation(x=0.7, y=0.4, ax=0.9, ay=0.4, arrowhead=3, arrowcolor="red", arrowwidth=2, text=f"Iph={Ir_ph:.0f}∠{Ir_ang:.1f}° A")

    fig.add_annotation(x=0.5, y=0.3, showarrow=False, text=f"Generador: P={P_s:.2f} MW  Q={Q_s:.2f} Mvar\nDemanda: P={P_MW:.2f} MW  Q={Q_Mvar:.2f} Mvar", bgcolor="black", opacity=0.7)

    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1])
    fig.update_layout(title_text=title, title_x=0.5, height=300, margin=dict(l=5, r=5, t=30, b=5))
    return fig

# Pestañas y salida (pasamos None para Vll cuando no aplica)
tabs = st.tabs(["Tablas", "Línea Corta", "Línea Media", "Línea Larga"])

with tabs[0]:
    st.subheader("Tensiones y Corrientes")
    st.table(df_vc)
    st.subheader("Potencias")
    st.table(df_pq)

with tabs[1]:
    fig_corta = create_figure(
        "Línea Corta",
        Vs1_ph, a1_vs,
        (Vs1_ll_val if Vs1_ll_val is not None else None), a1_vll,
        Is1_ph, a1_is,
        Vr_ph, a_vr,
        (Vr_ll_val if Vr_ll_val is not None else None), a_vll,
        Ir_ph, a_ir,
        P1/1e6, Q1/1e6
    )
    st.plotly_chart(fig_corta, use_container_width=True)

with tabs[2]:
    fig_pi = create_figure(
        "Línea Media",
        Vs2_ph, a2_vs,
        (Vs2_ll_val if Vs2_ll_val is not None else None), a2_vll,
        Is2_ph, a2_is,
        Vr_ph, a_vr,
        (Vr_ll_val if Vr_ll_val is not None else None), a_vll,
        Ir_ph, a_ir,
        P2/1e6, Q2/1e6,
        shunt=True
    )
    st.plotly_chart(fig_pi, use_container_width=True)

with tabs[3]:
    fig_larga = create_figure(
        "Línea Larga",
        Vs3_ph, a3_vs,
        (Vs3_ll_val if Vs3_ll_val is not None else None), a3_vll,
        Is3_ph, a3_is,
        Vr_ph, a_vr,
        (Vr_ll_val if Vr_ll_val is not None else None), a_vll,
        Ir_ph, a_ir,
        P3/1e6, Q3/1e6,
        gamma_l=abs(γ * ℓ)
    )
    st.plotly_chart(fig_larga, use_container_width=True)
