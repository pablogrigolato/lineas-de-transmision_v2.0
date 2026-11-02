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
# Sidebar — configuración general
# ==================================================================
st.sidebar.header("⚙️ Configuración")
tipo_sistema = st.sidebar.selectbox("Tipo de sistema", ["Trifásico", "Monofásico"])

SENTIDO_DEM = "Dato en la demanda → calcular generador"
SENTIDO_GEN = "Dato en el generador → calcular demanda"
sentido = st.sidebar.radio(
    "Sentido del cálculo", [SENTIDO_DEM, SENTIDO_GEN],
    help="El primer sentido es directo (una sola evaluación de ABCD). El segundo es un "
         "flujo de carga de dos barras: la tensión de la demanda es incógnita y depende "
         "de la carga, por lo que se resuelve iterativamente.",
)
invertido = (sentido == SENTIDO_GEN)

# ------------------------------------------------------------------
# Parámetros de línea — tres formas de ingreso
# ------------------------------------------------------------------
st.sidebar.header("Parámetros de línea")

MODO_RLC = "R, L, C por km"
MODO_RXB = "R, X, B por km"
MODO_TOT = "R, X, B totales"
modo_entrada = st.sidebar.radio(
    "Forma de ingreso", [MODO_RLC, MODO_RXB, MODO_TOT],
    help="Las tablas de conductores suelen dar reactancia (Ω/km) y susceptancia (µS/km) "
         "directamente; los estudios de red a veces dan los valores totales del tramo.",
)

length_km = st.sidebar.number_input("Longitud (km)", min_value=0.1, max_value=2000.0,
                                    value=100.0, step=1.0)

if modo_entrada == MODO_RLC:
    f_Hz = st.sidebar.number_input("Frecuencia (Hz)", min_value=1.0, max_value=200.0,
                                   value=50.0, step=0.01)
    R_in = st.sidebar.number_input("R (Ω/km)", min_value=0.0, max_value=100.0,
                                   value=0.05, step=0.0001, format="%.4f")
    L_mH = st.sidebar.number_input("L (mH/km)", min_value=0.0, max_value=100.0,
                                   value=0.50, step=0.0001, format="%.4f")
    C_nF = st.sidebar.number_input("C (nF/km)", min_value=0.0, max_value=1000.0,
                                   value=10.0, step=0.0001, format="%.4f")
    G_in = st.sidebar.number_input("G (µS/km)", min_value=0.0, max_value=1000.0,
                                   value=0.0, step=0.001, format="%.3f",
                                   help="Conductancia shunt (fugas por aisladores / corona). "
                                        "Normalmente despreciable.")
    omega = 2 * np.pi * f_Hz
    z_km = R_in + 1j * omega * (L_mH * 1e-3)
    y_km = (G_in * 1e-6) + 1j * omega * (C_nF * 1e-9)

elif modo_entrada == MODO_RXB:
    R_in = st.sidebar.number_input("R (Ω/km)", min_value=0.0, max_value=100.0,
                                   value=0.05, step=0.0001, format="%.4f")
    X_in = st.sidebar.number_input("X (Ω/km)", min_value=0.0, max_value=100.0,
                                   value=0.1571, step=0.0001, format="%.4f")
    B_in = st.sidebar.number_input("B (µS/km)", min_value=0.0, max_value=10000.0,
                                   value=3.1416, step=0.0001, format="%.4f")
    G_in = st.sidebar.number_input("G (µS/km)", min_value=0.0, max_value=1000.0,
                                   value=0.0, step=0.001, format="%.3f")
    z_km = R_in + 1j * X_in
    y_km = (G_in * 1e-6) + 1j * (B_in * 1e-6)
    st.sidebar.caption("X y B se toman ya referidas a la frecuencia de operación, "
                       "por lo que la frecuencia no interviene en el cálculo.")

else:  # MODO_TOT
    R_tot = st.sidebar.number_input("R total (Ω)", min_value=0.0, max_value=10000.0,
                                    value=5.0, step=0.01, format="%.4f")
    X_tot = st.sidebar.number_input("X total (Ω)", min_value=0.0, max_value=10000.0,
                                    value=15.708, step=0.01, format="%.4f")
    B_tot = st.sidebar.number_input("B total (µS)", min_value=0.0, max_value=100000.0,
                                    value=314.159, step=0.01, format="%.4f")
    G_tot = st.sidebar.number_input("G total (µS)", min_value=0.0, max_value=10000.0,
                                    value=0.0, step=0.01, format="%.4f")
    z_km = (R_tot + 1j * X_tot) / length_km
    y_km = ((G_tot * 1e-6) + 1j * (B_tot * 1e-6)) / length_km
    st.sidebar.caption("La longitud sólo se usa para el eje del perfil y para expresar "
                       "los parámetros por km.")

# ------------------------------------------------------------------
# Carga y tensión
# ------------------------------------------------------------------
st.sidebar.header("Carga y tensión")

etq_extremo = "el generador" if invertido else "la demanda"
if tipo_sistema == "Trifásico":
    V_dato_kV = st.sidebar.number_input(f"V_LL en {etq_extremo} (kV)", min_value=0.001,
                                        max_value=1500.0, value=230.0, step=0.1)
else:
    V_dato_kV = st.sidebar.number_input(f"V en {etq_extremo} (kV)", min_value=0.001,
                                        max_value=1500.0, value=230.0, step=0.1)

P_MW = st.sidebar.number_input("P total en la demanda (MW)", min_value=-10000.0,
                               max_value=10000.0, value=50.0, step=1.0)
Q_Mvar = st.sidebar.number_input("Q total en la demanda (Mvar)", min_value=-10000.0,
                                 max_value=10000.0, value=10.0, step=1.0)

st.sidebar.caption(
    "La carga siempre se especifica en la demanda. Lo que cambia con el sentido es "
    "cuál de las dos tensiones es dato y cuál se calcula."
)

# ==================================================================
# Magnitudes base
# ==================================================================
if tipo_sistema == "Trifásico":
    V_dato = (V_dato_kV * 1e3) / np.sqrt(3)   # por fase
    n_fases = 3
    k_ll = np.sqrt(3)
    etq_v = "V_LL"
else:
    V_dato = V_dato_kV * 1e3
    n_fases = 1
    k_ll = 1.0
    etq_v = "V"

S_tot = P_MW * 1e6 + 1j * Q_Mvar * 1e6
S_ph = S_tot / n_fases

if V_dato <= 0:
    st.error("La tensión debe ser mayor que cero.")
    st.stop()

Z = z_km * length_km
Y = y_km * length_km


# ==================================================================
# Constantes de propagación y matrices ABCD
# ==================================================================
def constantes_linea(z_km, y_km, Lk):
    """(Z, Y, γℓ, Zc, Y_nulo, Z_nulo) para un tramo de longitud Lk."""
    Z = z_km * Lk
    Y = y_km * Lk
    Y_nulo = abs(Y) < 1e-18
    Z_nulo = abs(Z) < 1e-18
    if Y_nulo:
        # Sin admitancia shunt: γℓ → 0, Zc → ∞, pero Zc·senh(γℓ) → Z.
        g, Zc = 0.0 + 0j, np.inf + 0j
    elif Z_nulo:
        # Sin impedancia serie: γℓ → 0, Zc → 0, pero senh(γℓ)/Zc → Y.
        g, Zc = 0.0 + 0j, 0.0 + 0j
    else:
        g = np.sqrt(Z * Y)
        Zc = np.sqrt(Z / Y)
    return Z, Y, g, Zc, Y_nulo, Z_nulo


def abcd_modelos(Z, Y, g, Zc, Y_nulo, Z_nulo):
    """{nombre: (A, B, C, D)} para los tres niveles de aproximación."""
    corta = (1.0 + 0j, Z, 0.0 + 0j, 1.0 + 0j)
    media = (1 + Z * Y / 2, Z, Y * (1 + Z * Y / 4), 1 + Z * Y / 2)
    if Y_nulo:
        larga = corta
    elif Z_nulo:
        larga = (1.0 + 0j, 0.0 + 0j, Y, 1.0 + 0j)
    else:
        ch, sh = np.cosh(g), np.sinh(g)
        larga = (ch, Zc * sh, sh / Zc, ch)
    return {"Corta": corta, "Media (π nominal)": media, "Larga (distribuida)": larga}


Z, Y, gamma_l, Zc, Y_nulo, Z_nulo = constantes_linea(z_km, y_km, length_km)
MODELOS = abcd_modelos(Z, Y, gamma_l, Zc, Y_nulo, Z_nulo)

# Impedancia de onda y longitud de onda (independientes del modo de entrada)
x_km, b_km = np.imag(z_km), np.imag(y_km)
Zsurge = np.sqrt(x_km / b_km) if b_km > 1e-18 else np.inf
beta_km = np.imag(gamma_l) / length_km
lambda_km = (2 * np.pi / beta_km) if beta_km > 1e-15 else np.inf


# ==================================================================
# Resolución del sentido inverso (flujo de carga de dos barras)
# ==================================================================
# Con la tensión del generador como dato, Vr es incógnita y el problema deja de
# ser lineal:   A·Vr + B·conj(S/Vr) = Vs.  Se resuelve por Newton sobre las
# partes real e imaginaria de Vr, con continuación en la carga (se rampea de 0
# al 100 %) para no perder la solución cerca del límite de transmisión.
def _newton_vr(A, B, V_s, S_ph, V0, tol=1e-11, itmax=40):
    Vr = V0
    Sc = np.conj(S_ph)
    for _ in range(itmax):
        cv = np.conj(Vr)
        if abs(cv) < 1e-12:
            return Vr, False
        f = A * Vr + Sc * B / cv - V_s
        if abs(f) < tol * abs(V_s):
            return Vr, True
        dfu = A - Sc * B / cv ** 2          # ∂f/∂(Re Vr)
        dfv = 1j * A + 1j * Sc * B / cv ** 2  # ∂f/∂(Im Vr)
        J = np.array([[dfu.real, dfv.real], [dfu.imag, dfv.imag]])
        if abs(np.linalg.det(J)) < 1e-30:
            return Vr, False
        du, dv = np.linalg.solve(J, [-f.real, -f.imag])
        Vr = Vr + (du + 1j * dv)
    return Vr, False


def resolver_vr(A, B, V_s, S_ph, paso0=0.25, paso_min=1e-5):
    """Devuelve (Vr, convergio, lambda_max). lambda_max < 1 indica que la carga
    supera el máximo transmisible con esa tensión de generador."""
    V0 = V_s / A if abs(A) > 1e-9 else V_s
    if abs(S_ph) < 1e-9:
        return V0, True, 1.0
    Vr, lam, paso = V0, 0.0, paso0
    while lam < 1.0 - 1e-9 and paso > paso_min:
        lam_try = min(1.0, lam + paso)
        Vn, ok = _newton_vr(A, B, V_s, S_ph * lam_try, Vr)
        if ok:
            Vr, lam = Vn, lam_try
            paso = min(paso * 1.6, paso0)
        else:
            paso *= 0.5
    return Vr, lam >= 1.0 - 1e-9, lam


def resolver(A, B, C, D, V_dato, S_ph, invertido):
    """Resuelve la línea completa y devuelve todas las magnitudes derivadas."""
    convergio, lam = True, 1.0
    if invertido:
        V_s = complex(V_dato)              # referencia angular 0° en el generador
        V_r, convergio, lam = resolver_vr(A, B, V_s, S_ph)
        I_r = np.conj(S_ph / V_r) if abs(V_r) > 1e-9 else 0j
        I_s = C * V_r + D * I_r
    else:
        V_r = complex(V_dato)              # referencia angular 0° en la demanda
        I_r = np.conj(S_ph / V_r)
        V_s = A * V_r + B * I_r
        I_s = C * V_r + D * I_r

    S_s_ph = V_s * np.conj(I_s)
    P_s, Q_s = S_s_ph.real * n_fases, S_s_ph.imag * n_fases
    P_r, Q_r = S_tot.real, S_tot.imag

    perdidas_P = P_s - P_r
    perdidas_Q = Q_s - Q_r
    rendimiento = (P_r / P_s * 100) if abs(P_s) > 1e-9 else np.nan
    regulacion = ((abs(V_s) / abs(A) - abs(V_r)) / abs(V_r) * 100) \
        if (abs(A) > 1e-15 and abs(V_r) > 1e-9) else np.nan

    return dict(V_s=V_s, I_s=I_s, V_r=V_r, I_r=I_r,
                P_s=P_s, Q_s=Q_s, P_r=P_r, Q_r=Q_r,
                perdidas_P=perdidas_P, perdidas_Q=perdidas_Q,
                rendimiento=rendimiento, regulacion=regulacion,
                A=A, B=B, C=C, D=D, det=A * D - B * C,
                convergio=convergio, lam=lam)


RES = {nom: resolver(*abcd, V_dato, S_ph, invertido) for nom, abcd in MODELOS.items()}
EXACTO = RES["Larga (distribuida)"]

# ------------------------------------------------------------------
# Manejo de la no convergencia (carga por encima del máximo transmisible)
# ------------------------------------------------------------------
# Sólo el modelo exacto decide si el caso tiene solución física. Un modelo
# aproximado puede predecir colapso antes que el exacto — eso es un resultado
# informativo (muestra hasta dónde miente la aproximación), no un error.
if not EXACTO["convergio"]:
    lam = EXACTO["lam"]
    st.error(
        f"**Sin solución para la carga pedida.** Con {V_dato_kV:.1f} kV en el generador, "
        f"la máxima potencia transmisible es del orden de **{lam * P_MW:.1f} MW + "
        f"j{lam * Q_Mvar:.1f} Mvar** ({lam * 100:.1f} % de lo solicitado). Más allá de ese "
        "punto el flujo de carga no tiene solución operativa: es la nariz de la curva P-V "
        "(colapso de tensión). Bajá la carga, subí la tensión del generador o compensá "
        "reactivo."
    )
    st.stop()

no_conv = [n for n, r in RES.items() if not r["convergio"]]
if no_conv:
    detalle = ", ".join(f"{n} (≈{RES[n]['lam'] * P_MW:.0f} MW)" for n in no_conv)
    st.warning(
        f"El modelo exacto sí tiene solución, pero estos modelos aproximados predicen "
        f"colapso antes de alcanzar la carga pedida: {detalle}. Se los excluye de la "
        "comparación. Es una señal fuerte de que la aproximación ya no es válida para "
        "esta longitud."
    )
    RES = {n: r for n, r in RES.items() if r["convergio"]}

# ==================================================================
# Métricas principales (modelo exacto)
# ==================================================================
if invertido:
    titulo_res = "Resultados del modelo exacto — tensión calculada en la demanda"
    V_calc, V_ref = EXACTO["V_r"], EXACTO["V_s"]
    etq_calc, etq_otro = "demanda", "generador"
else:
    titulo_res = "Resultados del modelo exacto — tensión calculada en el generador"
    V_calc, V_ref = EXACTO["V_s"], EXACTO["V_r"]
    etq_calc, etq_otro = "generador", "demanda"

st.subheader(titulo_res)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(f"{etq_v} {etq_calc}", f"{abs(V_calc) * k_ll / 1e3:.2f} kV",
          f"{(abs(V_calc) / abs(V_ref) - 1) * 100:+.2f} % vs {etq_otro}")
c2.metric("Regulación de tensión", f"{EXACTO['regulacion']:.2f} %",
          help="(|Vr| en vacío − |Vr| a plena carga) / |Vr| a plena carga, con |Vr,vacío| = |Vs|/|A|.")
c3.metric("Rendimiento", f"{EXACTO['rendimiento']:.2f} %")
c4.metric("Pérdidas activas", f"{EXACTO['perdidas_P'] / 1e6:.3f} MW")
c5.metric("Balance reactivo", f"{EXACTO['perdidas_Q'] / 1e6:+.3f} Mvar",
          help="Q generador − Q demanda. Negativo = la línea aporta reactivo neto.")

with st.expander("📐 Parámetros característicos de la línea", expanded=False):
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Z total", f"{abs(Z):.2f} Ω", f"∠{np.degrees(np.angle(Z)):.1f}°")
    p2.metric("Y total", f"{abs(Y) * 1e6:.2f} µS", f"∠{np.degrees(np.angle(Y)):.1f}°")
    if not (Y_nulo or Z_nulo):
        p3.metric("Zc (impedancia característica)", f"{abs(Zc):.2f} Ω",
                  f"∠{np.degrees(np.angle(Zc)):.1f}°")
        p4.metric("|γℓ| (adimensional)", f"{abs(gamma_l):.4f}",
                  help="Regla práctica: con |γℓ| ≲ 0.05 el π nominal es suficiente.")
    else:
        p3.metric("Zc", "∞ (Y = 0)" if Y_nulo else "0 (Z = 0)")
        p4.metric("|γℓ|", "0")

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("z por km", f"{abs(z_km):.4f} Ω/km", f"∠{np.degrees(np.angle(z_km)):.1f}°")
    q2.metric("y por km", f"{abs(y_km) * 1e6:.4f} µS/km", f"∠{np.degrees(np.angle(y_km)):.1f}°")
    if np.isfinite(Zsurge) and Zsurge > 0:
        SIL = (V_dato_kV ** 2 / Zsurge) if not invertido else \
              ((abs(EXACTO["V_r"]) * k_ll / 1e3) ** 2 / Zsurge)
        q3.metric("Z_surge = √(X/B)", f"{Zsurge:.2f} Ω")
        q4.metric("SIL (potencia natural)", f"{SIL:.2f} MW",
                  help="Carga a la que la línea consume exactamente el reactivo que genera.")
    if np.isfinite(lambda_km):
        st.caption(f"Longitud de onda λ = {lambda_km:,.0f} km — la línea abarca el "
                   f"{length_km / lambda_km * 100:.2f} % de λ.")

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
    filas = []
    for nombre, r in RES.items():
        vs, is_, vr, ir = r["V_s"], r["I_s"], r["V_r"], r["I_r"]
        fila = {"Modelo": nombre,
                "Vph generador": f"{abs(vs)/1e3:.3f} ∠ {np.degrees(np.angle(vs)):.2f}° kV"}
        if tipo_sistema == "Trifásico":
            fila["Vll generador"] = (f"{abs(vs)*np.sqrt(3)/1e3:.3f} ∠ "
                                     f"{np.degrees(np.angle(vs))+30:.2f}° kV")
        fila["Iph generador"] = f"{abs(is_):.2f} ∠ {np.degrees(np.angle(is_)):.2f}° A"
        fila["Vph demanda"] = f"{abs(vr)/1e3:.3f} ∠ {np.degrees(np.angle(vr)):.2f}° kV"
        if tipo_sistema == "Trifásico":
            fila["Vll demanda"] = (f"{abs(vr)*np.sqrt(3)/1e3:.3f} ∠ "
                                   f"{np.degrees(np.angle(vr))+30:.2f}° kV")
        fila["Iph demanda"] = f"{abs(ir):.2f} ∠ {np.degrees(np.angle(ir)):.2f}° A"
        filas.append(fila)
    st.dataframe(pd.DataFrame(filas), width='stretch', hide_index=True)

    st.subheader("Potencias, pérdidas y desempeño")
    df_pq = pd.DataFrame([{
        "Modelo": n,
        "P gen (MW)": r["P_s"] / 1e6, "Q gen (Mvar)": r["Q_s"] / 1e6,
        "P dem (MW)": r["P_r"] / 1e6, "Q dem (Mvar)": r["Q_r"] / 1e6,
        "Pérdidas P (MW)": r["perdidas_P"] / 1e6,
        "Balance Q (Mvar)": r["perdidas_Q"] / 1e6,
        "Regulación (%)": r["regulacion"], "Rendimiento (%)": r["rendimiento"],
    } for n, r in RES.items()])
    fmt_pq = {
        "P gen (MW)": "{:.2f}", "Q gen (Mvar)": "{:.2f}",
        "P dem (MW)": "{:.2f}", "Q dem (Mvar)": "{:.2f}",
        "Pérdidas P (MW)": "{:.3f}", "Balance Q (Mvar)": "{:+.3f}",
        "Regulación (%)": "{:.2f}", "Rendimiento (%)": "{:.2f}",
    }
    st.dataframe(df_pq.style.format(fmt_pq), width='stretch', hide_index=True)

    st.subheader("Constantes ABCD")
    st.dataframe(pd.DataFrame([{
        "Modelo": n,
        "A = D": f"{abs(r['A']):.5f} ∠ {np.degrees(np.angle(r['A'])):.3f}°",
        "B (Ω)": f"{abs(r['B']):.3f} ∠ {np.degrees(np.angle(r['B'])):.3f}°",
        "C (µS)": f"{abs(r['C'])*1e6:.4f} ∠ {np.degrees(np.angle(r['C'])):.3f}°",
        "AD − BC": f"{r['det'].real:.9f} {r['det'].imag:+.2e}j",
    } for n, r in RES.items()]), width='stretch', hide_index=True)

    st.download_button("⬇ Descargar resultados (CSV)",
                       df_pq.round(3).to_csv(index=False).encode("utf-8"),
                       file_name="modelos_linea_resultados.csv", mime="text/csv")

# ------------------------------------------------------------------
# TAB 1 — Perfil a lo largo de la línea
# ------------------------------------------------------------------
with tabs[1]:
    st.subheader("Perfil de tensión y corriente")
    st.caption(
        "Solución exacta evaluada punto a punto: V(x) = cosh(γx)·Vr + Zc·senh(γx)·Ir, "
        "con x medido desde la demanda. Sólo el modelo largo describe el interior de la "
        "línea; los otros dos aparecen como puntos en el extremo calculado."
    )

    V_r_e, I_r_e = EXACTO["V_r"], EXACTO["I_r"]
    x_dem = np.linspace(0.0, length_km, 400)
    x_gen = length_km - x_dem

    if Y_nulo:
        V_x = V_r_e + (z_km * x_dem) * I_r_e
        I_x = np.full_like(x_dem, I_r_e, dtype=complex)
    elif Z_nulo:
        V_x = np.full_like(x_dem, V_r_e, dtype=complex)
        I_x = I_r_e + (y_km * x_dem) * V_r_e
    else:
        gx = (gamma_l / length_km) * x_dem
        V_x = np.cosh(gx) * V_r_e + Zc * np.sinh(gx) * I_r_e
        I_x = (np.sinh(gx) / Zc) * V_r_e + np.cosh(gx) * I_r_e

    Vmag = np.abs(V_x) * k_ll / 1e3
    Imag = np.abs(I_x)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_gen, y=Vmag, mode="lines", name=f"|{etq_v}| (kV)",
                             line=dict(color="#22a884", width=3),
                             hovertemplate="x = %{x:.1f} km<br>|V| = %{y:.2f} kV<extra></extra>"))
    fig.add_trace(go.Scatter(x=x_gen, y=Imag, mode="lines", name="|I| (A)", yaxis="y2",
                             line=dict(color="#e69f00", width=2, dash="dot"),
                             hovertemplate="x = %{x:.1f} km<br>|I| = %{y:.1f} A<extra></extra>"))

    # Extremo calculado según cada modelo aproximado
    x_marca = 0.0 if not invertido else length_km
    clave = "V_s" if not invertido else "V_r"
    for nombre, color in [("Corta", "#d62728"), ("Media (π nominal)", "#9467bd")]:
        if nombre not in RES:
            continue
        fig.add_trace(go.Scatter(
            x=[x_marca], y=[abs(RES[nombre][clave]) * k_ll / 1e3],
            mode="markers", name=f"{nombre} — {etq_calc}",
            marker=dict(size=11, color=color, symbol="diamond",
                        line=dict(color="#fff", width=1)),
            hovertemplate=f"{nombre}<br>|V| = %{{y:.2f}} kV<extra></extra>"))

    fig.add_hline(y=abs(V_dato) * k_ll / 1e3, line=dict(color="#888", dash="dash", width=1),
                  annotation_text=f"tensión dato ({etq_otro})", annotation_position="bottom right")
    fig.update_layout(
        xaxis=dict(title="Distancia desde el generador (km)"),
        yaxis=dict(title=f"|{etq_v}| (kV)", color="#22a884"),
        yaxis2=dict(title="|I| (A)", overlaying="y", side="right", color="#e69f00",
                    showgrid=False),
        height=460, hovermode="x unified",
        legend=dict(orientation="h", y=1.12, font=dict(size=11)),
        margin=dict(l=20, r=20, t=40, b=40))
    st.plotly_chart(fig, width='stretch', config={"displaylogo": False})

    if np.isfinite(Zsurge) and Zsurge > 0:
        V_ref_kv = abs(V_r_e) * k_ll / 1e3
        SIL_v = V_ref_kv ** 2 / Zsurge
        P_dem = abs(S_tot.real) / 1e6
        if SIL_v > 0:
            if P_dem < 0.9 * SIL_v:
                st.info(f"Carga ({P_dem:.1f} MW) por debajo del SIL ({SIL_v:.1f} MW): la "
                        "línea genera más reactivo del que consume y la tensión tiende a "
                        "subir hacia la demanda (efecto Ferranti).")
            elif P_dem > 1.1 * SIL_v:
                st.info(f"Carga ({P_dem:.1f} MW) por encima del SIL ({SIL_v:.1f} MW): "
                        "consumo reactivo dominante, la tensión cae a lo largo de la línea.")
            else:
                st.success(f"Carga ({P_dem:.1f} MW) próxima al SIL ({SIL_v:.1f} MW): "
                           "perfil de tensión prácticamente plano.")

    st.download_button("⬇ Descargar perfil (CSV)", pd.DataFrame({
        "x_desde_generador_km": x_gen, "V_magnitud_kV": Vmag,
        "V_angulo_deg": np.degrees(np.angle(V_x)), "I_magnitud_A": Imag,
        "I_angulo_deg": np.degrees(np.angle(I_x)),
    }).round(4).to_csv(index=False).encode("utf-8"),
        file_name="perfil_linea.csv", mime="text/csv")

# ------------------------------------------------------------------
# TAB 2 — Diagrama fasorial
# ------------------------------------------------------------------
with tabs[2]:
    st.subheader("Diagrama fasorial")
    st.caption(f"Tensiones de fase en kV y corrientes escaladas. El {etq_otro} "
               "(tensión dato) está tomado como referencia 0°.")

    v_kv = [abs(r[k]) / 1e3 for r in RES.values() for k in ("V_s", "V_r")]
    i_a = [abs(r[k]) for r in RES.values() for k in ("I_s", "I_r")]
    escala_i = (max(v_kv) / max(i_a) * 0.55) if max(i_a) > 1e-9 else 1.0

    figf = go.Figure()

    def add_fasor(z, nombre, color, escala=1.0, dash="solid"):
        figf.add_trace(go.Scatter(
            x=[0, z.real * escala], y=[0, z.imag * escala], mode="lines+markers",
            name=nombre, line=dict(color=color, width=2.5, dash=dash),
            marker=dict(size=[0, 9], color=color, symbol="arrow-bar-up", angleref="previous"),
            customdata=[[abs(z), np.degrees(np.angle(z))]] * 2,
            hovertemplate=f"{nombre}<br>%{{customdata[0]:.3f}} ∠ %{{customdata[1]:.2f}}°<extra></extra>"))

    COL_MOD = {"Corta": "#d62728", "Media (π nominal)": "#9467bd",
               "Larga (distribuida)": "#22a884"}
    if invertido:
        add_fasor(EXACTO["V_s"] / 1e3, "Vs (generador, dato)", "#ffffff")
        for n, r in RES.items():
            add_fasor(r["V_r"] / 1e3, f"Vr — {n}", COL_MOD[n])
        add_fasor(EXACTO["I_s"], "Is — Larga", "#7ad151", escala_i, "dot")
        add_fasor(EXACTO["I_r"], "Ir — Larga", "#e69f00", escala_i, "dot")
    else:
        add_fasor(EXACTO["V_r"] / 1e3, "Vr (demanda, dato)", "#ffffff")
        for n, r in RES.items():
            add_fasor(r["V_s"] / 1e3, f"Vs — {n}", COL_MOD[n])
        add_fasor(EXACTO["I_r"], "Ir (demanda)", "#e69f00", escala_i, "dot")
        add_fasor(EXACTO["I_s"], "Is — Larga", "#7ad151", escala_i, "dot")

    lim = max(max(v_kv), max(i_a) * escala_i) * 1.2
    figf.update_layout(
        xaxis=dict(title="Real", range=[-lim * 0.35, lim], zeroline=True,
                   zerolinecolor="rgba(128,128,128,0.5)"),
        yaxis=dict(title="Imaginario", range=[-lim * 0.6, lim * 0.6], scaleanchor="x",
                   scaleratio=1, zeroline=True, zerolinecolor="rgba(128,128,128,0.5)"),
        height=520, legend=dict(font=dict(size=10)),
        margin=dict(l=20, r=20, t=30, b=40))
    st.plotly_chart(figf, width='stretch', config={"displaylogo": False})

    delta = np.degrees(np.angle(EXACTO["V_s"]) - np.angle(EXACTO["V_r"]))
    st.caption(f"Ángulo de carga δ (entre Vs y Vr, modelo exacto): **{delta:.2f}°**. "
               f"Corrientes dibujadas con factor {escala_i:.4f} kV/A.")

# ------------------------------------------------------------------
# TAB 3 — Error de los modelos
# ------------------------------------------------------------------
with tabs[3]:
    st.subheader("Error de las aproximaciones respecto del modelo exacto")
    st.caption(f"Se compara la magnitud calculada ({etq_calc}); el otro extremo es dato "
               "y por definición coincide en los tres modelos.")

    kV, kI = ("V_s", "I_s") if not invertido else ("V_r", "I_r")
    ref = EXACTO
    df_err = pd.DataFrame([{
        "Modelo": n,
        f"Error |V {etq_calc}| (%)": (abs(r[kV]) - abs(ref[kV])) / abs(ref[kV]) * 100,
        f"Error ∠V {etq_calc} (°)": np.degrees(np.angle(r[kV]) - np.angle(ref[kV])),
        f"Error |I {etq_calc}| (%)": ((abs(r[kI]) - abs(ref[kI])) / abs(ref[kI]) * 100
                                      if abs(ref[kI]) > 1e-9 else np.nan),
        "Error pérdidas P (%)": ((r["perdidas_P"] - ref["perdidas_P"]) / ref["perdidas_P"] * 100
                                 if abs(ref["perdidas_P"]) > 1e-6 else np.nan),
        "Error regulación (p.p.)": r["regulacion"] - ref["regulacion"],
    } for n, r in RES.items() if n != "Larga (distribuida)"])
    if len(df_err):
        fmt_err = {c: ("{:+.3f}" if "°" in c or "p.p." in c else "{:+.4f}")
                   for c in df_err.columns if c != "Modelo"}
        st.dataframe(df_err.style.format(fmt_err),
                     width='stretch', hide_index=True)
    else:
        st.info("Ningún modelo aproximado tiene solución para esta carga, así que no hay "
                "nada que comparar en este punto de operación.")

    st.markdown("**Cómo crece el error con la longitud** (mismos parámetros por km y misma carga):")
    longitudes = np.linspace(5, max(600.0, length_km * 1.5), 60)
    err = {"Corta": [], "Media (π nominal)": []}
    for Lk in longitudes:
        cte = constantes_linea(z_km, y_km, Lk)
        mods = abcd_modelos(*cte)
        base = resolver(*mods["Larga (distribuida)"], V_dato, S_ph, invertido)
        for n in err:
            r = resolver(*mods[n], V_dato, S_ph, invertido)
            if base["convergio"] and r["convergio"] and abs(base[kV]) > 1e-9:
                err[n].append((abs(r[kV]) - abs(base[kV])) / abs(base[kV]) * 100)
            else:
                err[n].append(np.nan)

    fige = go.Figure()
    for n, color in [("Corta", "#d62728"), ("Media (π nominal)", "#9467bd")]:
        fige.add_trace(go.Scatter(x=longitudes, y=err[n], mode="lines", name=n,
                                  line=dict(color=color, width=2.5)))
    fige.add_hline(y=0, line=dict(color="#888", width=1))
    for lv, txt in [(1.0, "1 %"), (-1.0, None)]:
        fige.add_hline(y=lv, line=dict(color="#666", dash="dot", width=1),
                       annotation_text=txt, annotation_position="top left")
    fige.add_vline(x=length_km, line=dict(color="#22a884", dash="dash", width=2),
                   annotation_text=f"longitud actual ({length_km:.0f} km)",
                   annotation_position="top right")
    fige.update_layout(xaxis_title="Longitud de línea (km)",
                       yaxis_title=f"Error en |V {etq_calc}| respecto del exacto (%)",
                       height=420, hovermode="x unified",
                       margin=dict(l=20, r=20, t=30, b=40))
    st.plotly_chart(fige, width='stretch', config={"displaylogo": False})

    st.caption("Criterio habitual: hasta ~80 km alcanza el modelo corto; entre ~80 y ~250 km "
               "el π nominal; por encima conviene el distribuido. El indicador independiente "
               "de la longitud es |γℓ|: por debajo de ~0.05 el π nominal es adecuado. "
               "Los tramos sin curva corresponden a longitudes donde la carga supera el "
               "máximo transmisible.")

# ------------------------------------------------------------------
# TAB 4 — Esquemas unifilares
# ------------------------------------------------------------------
with tabs[4]:
    st.subheader("Esquemas unifilares")
    COL_LINEA, COL_TXT = "#9aa0a6", "#c9d1d9"

    def _cap(fig, x, y_top, y_bot):
        y_mid = (y_top + y_bot) / 2
        fig.add_shape(type="line", x0=x, x1=x, y0=y_top, y1=y_mid + 0.035,
                      line=dict(color=COL_LINEA, width=2))
        for dy in (0.035, 0.0):
            fig.add_shape(type="line", x0=x - 0.035, x1=x + 0.035,
                          y0=y_mid + dy, y1=y_mid + dy, line=dict(color=COL_LINEA, width=3))
        fig.add_shape(type="line", x0=x, x1=x, y0=y_mid, y1=y_bot + 0.05,
                      line=dict(color=COL_LINEA, width=2))
        for i, w in enumerate([0.045, 0.030, 0.015]):
            yy = y_bot + 0.05 - i * 0.022
            fig.add_shape(type="line", x0=x - w, x1=x + w, y0=yy, y1=yy,
                          line=dict(color=COL_LINEA, width=2))

    def esquema(nombre, r):
        fig = go.Figure()
        Y_L, Y_G = 0.68, 0.18
        fig.add_shape(type="line", x0=0.10, x1=0.90, y0=Y_L, y1=Y_L,
                      line=dict(color=COL_LINEA, width=3))
        for x in (0.10, 0.90):
            fig.add_shape(type="line", x0=x, x1=x, y0=Y_L - 0.13, y1=Y_L + 0.13,
                          line=dict(color=COL_LINEA, width=5))
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
                    fig.add_annotation(x=x, y=Y_L - 0.10, showarrow=False,
                                       text=f"Y/2 = {abs(Y)/2*1e6:.2f} µS",
                                       font=dict(size=11, color=COL_TXT))
        else:
            if Y_nulo:
                Zp, Yp2 = Z, 0.0 + 0j
            elif Z_nulo:
                Zp, Yp2 = 0.0 + 0j, Y / 2
            else:
                Zp, Yp2 = Zc * np.sinh(gamma_l), np.tanh(gamma_l / 2) / Zc
            z_txt = f"Z' = {abs(Zp):.2f} ∠{np.degrees(np.angle(Zp)):.1f}° Ω"
            sub = ("π equivalente exacto: Z' = Zc·senh(γℓ), Y'/2 = tgh(γℓ/2)/Zc. "
                   "Reproduce la línea distribuida sin error.")
            if not Y_nulo:
                for x in (0.26, 0.74):
                    _cap(fig, x, Y_L, Y_G)
                    fig.add_annotation(x=x, y=Y_L - 0.10, showarrow=False,
                                       text=f"Y'/2 = {abs(Yp2)*1e6:.2f} µS",
                                       font=dict(size=11, color=COL_TXT))

        fig.add_annotation(x=0.50, y=Y_L + 0.11, showarrow=False, text=z_txt,
                           font=dict(size=12, color=COL_TXT))
        for x0, x1, val, ang in [(0.16, 0.30, abs(r["I_s"]), np.degrees(np.angle(r["I_s"]))),
                                 (0.70, 0.84, abs(r["I_r"]), np.degrees(np.angle(r["I_r"])))]:
            fig.add_annotation(x=x1, y=Y_L + 0.05, ax=x0, ay=Y_L + 0.05,
                               axref="x", ayref="y", xref="x", yref="y",
                               arrowhead=3, arrowcolor="#e15759", arrowwidth=2,
                               text=f"{val:.1f} ∠{ang:.1f}° A",
                               font=dict(size=11, color="#e15759"), yshift=16)

        vs, vr = r["V_s"], r["V_r"]
        gen = f"<b>Generador</b><br>Vph = {abs(vs)/1e3:.2f} ∠{np.degrees(np.angle(vs)):.1f}° kV"
        dem = f"<b>Demanda</b><br>Vph = {abs(vr)/1e3:.2f} ∠{np.degrees(np.angle(vr)):.1f}° kV"
        if tipo_sistema == "Trifásico":
            gen += f"<br>Vll = {abs(vs)*np.sqrt(3)/1e3:.2f} ∠{np.degrees(np.angle(vs))+30:.1f}° kV"
            dem += f"<br>Vll = {abs(vr)*np.sqrt(3)/1e3:.2f} ∠{np.degrees(np.angle(vr))+30:.1f}° kV"
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
            borderpad=6, font=dict(size=11, color=COL_TXT))

        fig.update_xaxes(visible=False, range=[0, 1])
        fig.update_yaxes(visible=False, range=[0, 1])
        fig.update_layout(title_text=nombre, title_x=0.5, height=430,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          margin=dict(l=5, r=5, t=40, b=5))
        return fig, sub

    for st_tab, (nombre, r) in zip(st.tabs(list(RES.keys())), RES.items()):
        with st_tab:
            f_, sub = esquema(nombre, r)
            st.plotly_chart(f_, width='stretch', config={"displaylogo": False})
            st.caption(sub)

# ------------------------------------------------------------------
# TAB 5 — Verificación
# ------------------------------------------------------------------
with tabs[5]:
    st.subheader("Verificación del modelo")

    st.markdown("**1. Reciprocidad de la red de dos puertos: AD − BC = 1**")
    ok_todos = True
    for n, r in RES.items():
        e = abs(r["det"] - 1)
        ok_todos &= e < 1e-9
        st.write(f"{'✅' if e < 1e-9 else '❌'} {n}: AD − BC = "
                 f"{r['det'].real:.12f} {r['det'].imag:+.2e}j  (error {e:.2e})")
    if ok_todos:
        st.success("Las tres matrices ABCD son recíprocas, como corresponde a una red "
                   "pasiva y bilateral. Además A = D en las tres, por simetría de la línea.")

    if invertido:
        st.markdown("**2. Cierre del flujo de carga inverso**")
        for n, r in RES.items():
            res = abs(r["A"] * r["V_r"] + r["B"] * r["I_r"] - r["V_s"]) / abs(r["V_s"])
            st.write(f"{'✅' if res < 1e-9 else '⚠️'} {n}: |A·Vr + B·Ir − Vs| / |Vs| = {res:.2e}")
        st.caption("Se resuelve por Newton sobre (Re Vr, Im Vr) con continuación en la carga.")

    st.markdown(f"**{'3' if invertido else '2'}. Balance de potencia**")
    st.write(f"P generador − P demanda = {EXACTO['perdidas_P']/1e6:.3f} MW "
             f"({'consumo' if EXACTO['perdidas_P'] > 0 else 'aporte'} neto de la línea)")
    st.write(f"Q generador − Q demanda = {EXACTO['perdidas_Q']/1e6:+.3f} Mvar")

    st.markdown(f"**{'4' if invertido else '3'}. Coherencia entre modelos**")
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
                 r"z = R + jX, \quad y = G + jB")
        st.markdown("**Sentido inverso** — con Vs como dato, Vr es incógnita y la ecuación "
                    "deja de ser lineal:")
        st.latex(r"A\,V_r + B\,\overline{\left(\frac{S_r}{V_r}\right)} = V_s")
        st.markdown("**Regulación de tensión** y **rendimiento**:")
        st.latex(r"RV\% = \frac{|V_s|/|A| - |V_r|}{|V_r|} \times 100, \qquad "
                 r"\eta\% = \frac{P_r}{P_s} \times 100")
        st.markdown(
            "Los parámetros $z$ e $y$ son por unidad de longitud; $Z = z\\ell$ e "
            "$Y = y\\ell$ son los totales. $\\gamma\\ell = \\sqrt{ZY}$ es adimensional y "
            "$Z_c = \\sqrt{Z/Y} = \\sqrt{z/y}$ no depende de la longitud."
        )
