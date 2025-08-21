# ============================================
# MÓDULO 3 · INFORMACIÓN PARTICULAR DEL ESTUDIANTADO (REPORTE EJECUTIVO)
# ============================================
# Uso: streamlit run modulo3_info_particular.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -----------------------------------
# CONFIG STREAMLIT
# -----------------------------------
st.set_page_config(page_title="Información particular • CHASIDE", layout="wide")
st.title("📘 Información particular del estudiantado – CHASIDE")
st.caption("Selecciona una carrera y un estudiante para consultar su reporte ejecutivo.")

# ============================================
# 1) CARGA DE DATOS
# ============================================
url = st.text_input(
    "URL de Google Sheets (CSV export)",
    "https://docs.google.com/spreadsheets/d/1BNAeOSj2F378vcJE5-T8iJ8hvoseOleOHr-I7mVfYu4/export?format=csv"
)

@st.cache_data(show_spinner=False)
def load_data(u):
    return pd.read_csv(u)

try:
    df = load_data(url)
except Exception as e:
    st.error(f"❌ No pude cargar el archivo: {e}")
    st.stop()

# ============================================
# 2) PREPROCESAMIENTO CHASIDE
# ============================================
columnas_items = df.columns[5:103]
columna_carrera = '¿A qué carrera desea ingresar?'
columna_nombre  = 'Ingrese su nombre completo'

# Validación básica
faltantes = [c for c in [columna_carrera, columna_nombre] if c not in df.columns]
if faltantes:
    st.error(f"❌ Faltan columnas requeridas: {faltantes}")
    st.stop()

# Sí/No → 1/0 (robusto)
df_items = (
    df[columnas_items]
      .astype(str).apply(lambda col: col.str.strip().str.lower())
      .replace({
          'sí':1, 'si':1, 's':1, '1':1, 'true':1, 'verdadero':1, 'x':1,
          'no':0, 'n':0, '0':0, 'false':0, 'falso':0, '':'0', 'nan':0
      })
      .apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
)
df[columnas_items] = df_items

# Coincidencia (sesgo Sí/No)
suma_si = df[columnas_items].sum(axis=1)
total_items = len(columnas_items)
pct_si = np.where(total_items==0, 0, suma_si/total_items)
pct_no = 1 - pct_si
df['Coincidencia'] = np.maximum(pct_si, pct_no)

# Mapeos CHASIDE
areas = ['C','H','A','S','I','D','E']
intereses_items = {
    'C':[1,12,20,53,64,71,78,85,91,98],
    'H':[9,25,34,41,56,67,74,80,89,95],
    'A':[3,11,21,28,36,45,50,57,81,96],
    'S':[8,16,23,33,44,52,62,70,87,92],
    'I':[6,19,27,38,47,54,60,75,83,97],
    'D':[5,14,24,31,37,48,58,65,73,84],
    'E':[17,32,35,42,49,61,68,77,88,93]
}
aptitudes_items = {
    'C':[2,15,46,51],
    'H':[30,63,72,86],
    'A':[22,39,76,82],
    'S':[4,29,40,69],
    'I':[10,26,59,90],
    'D':[13,18,43,66],
    'E':[7,55,79,94]
}
def col_item(i:int)->str: return columnas_items[i-1]

for a in areas:
    df[f'INTERES_{a}']  = df[[col_item(i) for i in intereses_items[a]]].sum(axis=1)
    df[f'APTITUD_{a}'] = df[[col_item(i) for i in aptitudes_items[a]]].sum(axis=1)

# Ponderación fija (puedes exponerla si quieres)
peso_intereses, peso_aptitudes = 0.8, 0.2
for a in areas:
    df[f'PUNTAJE_COMBINADO_{a}'] = df[f'INTERES_{a}']*peso_intereses + df[f'APTITUD_{a}']*peso_aptitudes

df['Area_Fuerte_Ponderada'] = df.apply(lambda r: max(areas, key=lambda a: r[f'PUNTAJE_COMBINADO_{a}']), axis=1)

# Perfiles carrera (coherencia)
perfil_carreras = {
    'Arquitectura': {'Fuerte': ['A','I','C']},
    'Contador Público': {'Fuerte': ['C','D']},
    'Licenciatura en Administración': {'Fuerte': ['C','D']},
    'Ingeniería Ambiental': {'Fuerte': ['I','C','E']},
    'Ingeniería Bioquímica': {'Fuerte': ['I','C','E']},
    'Ingeniería en Gestión Empresarial': {'Fuerte': ['C','D','H']},
    'Ingeniería Industrial': {'Fuerte': ['C','D','H']},
    'Ingeniería en Inteligencia Artificial': {'Fuerte': ['I','E']},
    'Ingeniería Mecatrónica': {'Fuerte': ['I','E']},
    'Ingeniería en Sistemas Computacionales': {'Fuerte': ['I','E']}
}
def evaluar(area_chaside, carrera):
    p = perfil_carreras.get(str(carrera).strip())
    if not p: return 'Sin perfil definido'
    if area_chaside in p.get('Fuerte',[]): return 'Coherente'
    if area_chaside in p.get('Baja',[]):   return 'Requiere Orientación'
    return 'Neutral'

df['Coincidencia_Ponderada'] = df.apply(lambda r: evaluar(r['Area_Fuerte_Ponderada'], r[columna_carrera]), axis=1)

def carrera_mejor(r):
    if r['Coincidencia'] >= 0.75: return 'Información no aceptable'
    a = r['Area_Fuerte_Ponderada']
    c_actual = str(r[columna_carrera]).strip()
    sugeridas = [c for c,p in perfil_carreras.items() if a in p.get('Fuerte',[])]
    return c_actual if c_actual in sugeridas else (', '.join(sugeridas) if sugeridas else 'Sin sugerencia clara')

def diagnostico(r):
    if r['Carrera_Mejor_Perfilada']=='Información no aceptable': return 'Información no aceptable'
    if str(r[columna_carrera]).strip()==str(r['Carrera_Mejor_Perfilada']).strip(): return 'Perfil adecuado'
    if r['Carrera_Mejor_Perfilada']=='Sin sugerencia clara': return 'Sin sugerencia clara'
    return f"Sugerencia: {r['Carrera_Mejor_Perfilada']}"

def semaforo(r):
    diag=r['Diagnóstico Primario Vocacional']
    if diag=='Información no aceptable': return 'No aceptable'
    if diag=='Sin sugerencia clara': return 'Sin sugerencia'
    match=r['Coincidencia_Ponderada']
    if diag=='Perfil adecuado':
        return {'Coherente':'Verde','Neutral':'Amarillo','Requiere Orientación':'Rojo'}.get(match,'Sin sugerencia')
    if diag.startswith('Sugerencia:'):
        return {'Coherente':'Verde','Neutral':'Amarillo','Requiere Orientación':'Rojo'}.get(match,'Sin sugerencia')
    return 'Sin sugerencia'

df['Carrera_Mejor_Perfilada']         = df.apply(carrera_mejor, axis=1)
df['Diagnóstico Primario Vocacional'] = df.apply(diagnostico, axis=1)
df['Semáforo Vocacional']             = df.apply(semaforo, axis=1)

# Score (para rankings tipo violín)
score_cols = [f'PUNTAJE_COMBINADO_{a}' for a in areas]
df['Score'] = df[score_cols].max(axis=1)

# Columna EMAIL (detección robusta)
def detectar_email_column(columns):
    lowered = [c.lower() for c in columns]
    for i, c in enumerate(lowered):
        if ('correo' in c) or ('email' in c) or ('e-mail' in c):
            return columns[i]
    return None
columna_email = detectar_email_column(df.columns)

# ============================================
# 3) UI: SELECCIÓN CARRERA → ESTUDIANTE
# ============================================
st.markdown("### 🧭 Selecciona carrera y estudiante")

carreras = sorted(df[columna_carrera].dropna().unique())
if not carreras:
    st.warning("No hay carreras disponibles en el archivo.")
    st.stop()

carrera_sel = st.selectbox("Carrera a evaluar:", carreras, index=0)

d_carrera = df[df[columna_carrera] == carrera_sel].copy()
if d_carrera.empty:
    st.warning("No hay estudiantes para esta carrera.")
    st.stop()

# Lista alfabética de estudiantes
nombres = sorted(d_carrera[columna_nombre].astype(str).unique())
est_sel = st.selectbox("Estudiante:", nombres, index=0)

# Registro del estudiante
alumno = d_carrera[d_carrera[columna_nombre].astype(str) == est_sel].copy()
if alumno.empty:
    st.warning("No se encontró el estudiante seleccionado.")
    st.stop()

# ============================================
# 4) REPORTE EJECUTIVO DEL ESTUDIANTE
# ============================================
st.markdown("## 🧾 Reporte ejecutivo")

# Datos base
nombre_full = est_sel
email = alumno.iloc[0][columna_email] if columna_email and columna_email in alumno.columns else "—"
categoria = alumno.iloc[0]['Semáforo Vocacional']

# Tamaño de la categoría dentro de la carrera
cat_count = int((d_carrera['Semáforo Vocacional'] == categoria).sum())

# KPIs ejecutivos
c1,c2,c3 = st.columns([2,1,1])
with c1:
    st.metric("Nombre completo", nombre_full)
with c2:
    st.metric("Categoría", categoria)
with c3:
    st.metric("Personas en esta categoría (carrera)", cat_count)

st.caption(f"Email: **{email}**" if email != "—" else "Email: — (no detectado)")

# ============================================
# 5) BANDERAS: Joven promesa / Joven en riesgo
#    - Top 5 VERDE (score alto) de la carrera → 'Joven promesa'
#    - Bottom 5 AMARILLO (score bajo) de la carrera → 'Joven en riesgo de reprobar'
# ============================================
verde_carrera   = d_carrera[d_carrera['Semáforo Vocacional']=='Verde'].copy()
amarillo_carrera= d_carrera[d_carrera['Semáforo Vocacional']=='Amarillo'].copy()

banderas = []
if not verde_carrera.empty:
    top5_verde = verde_carrera.sort_values('Score', ascending=False).head(5)[columna_nombre].astype(str).tolist()
    if nombre_full in top5_verde:
        banderas.append("🟢 Joven promesa (Top 5 Verde de su carrera)")
if not amarillo_carrera.empty:
    bottom5_amar = amarillo_carrera.sort_values('Score', ascending=True).head(5)[columna_nombre].astype(str).tolist()
    if nombre_full in bottom5_amar:
        banderas.append("🟠 Joven en riesgo de reprobar (Bottom 5 Amarillo de su carrera)")

if banderas:
    for b in banderas:
        st.success(b) if "promesa" in b else st.warning(b)
else:
    st.info("Sin banderas especiales para este estudiante.")

# ============================================
# 6) RADAR: Alumno vs Promedio Verde de su carrera
#     - Perfil por letra = INTERES + APTITUD
#     - Se listan las 3 letras con mayor brecha (Promedio Verde – Alumno)
# ============================================
st.markdown("## 🕸️ Radar: Alumno vs promedio de estudiantes Verdes (misma carrera)")

# Construir totales por letra para todo el DF
for a in areas:
    # Ya tenemos INTERES_* y APTITUD_*, sumamos para perfil total por letra
    df[f'TOTAL_{a}'] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

# Subconjuntos
promedio_verde = d_carrera[d_carrera['Semáforo Vocacional']=='Verde']
if promedio_verde.empty:
    st.warning("No hay estudiantes 'Verde' en esta carrera para comparar el radar.")
else:
    # Vector alumno
    alumno_vec = alumno[[f'TOTAL_{a}' for a in areas]].iloc[0].astype(float)
    # Promedio Verde
    verde_vec = promedio_verde[[f'TOTAL_{a}' for a in areas]].mean().astype(float)

    # Data para radar
    df_radar = pd.DataFrame({
        'Área': areas,
        'Alumno': [alumno_vec[f'TOTAL_{a}'] for a in areas],
        'Promedio Verde': [verde_vec[f'TOTAL_{a}'] for a in areas]
    })

    # Plot
    fig_radar = px.line_polar(
        df_radar.melt(id_vars='Área', value_vars=['Alumno','Promedio Verde'], var_name='Serie', value_name='Valor'),
        r='Valor', theta='Área', color='Serie',
        line_close=True, markers=True,
        color_discrete_map={'Alumno':'#2563eb', 'Promedio Verde':'#22c55e'},
        title=f"Perfil CHASIDE – {nombre_full} vs Promedio Verde ({carrera_sel})"
    )
    fig_radar.update_traces(fill='toself', opacity=0.75)
    st.plotly_chart(fig_radar, use_container_width=True)

    # Top 3 letras a reforzar (donde el alumno está por debajo del promedio Verde)
    brechas = (verde_vec.values - alumno_vec.values)
    diffs = pd.Series(brechas, index=areas).sort_values(ascending=False)
    top3 = diffs.head(3)

    # Descripciones breves para recomendaciones
    descripciones_chaside = {
        "C": "Organización, orden, análisis/síntesis, colaboración, cálculo.",
        "H": "Precisión verbal, relación de hechos, justicia, persuasión.",
        "A": "Creatividad, detalle, intuición; habilidades visuales/auditivas/manuales.",
        "S": "Investigación, precisión, percepción, análisis; altruismo y paciencia.",
        "I": "Cálculo, pensamiento científico/crítico, exactitud, planificación.",
        "D": "Justicia, equidad, colaboración, liderazgo; toma de decisiones.",
        "E": "Investigación, análisis y síntesis, cálculo numérico, observación, método."
    }

    st.subheader("🔎 Áreas por reforzar (vs promedio Verde)")
    if (top3 <= 0).all():
        st.info("El alumno está a la par o por encima del promedio Verde en todas las letras.")
    else:
        for letra, delta in top3.items():
            if delta > 0:
                st.markdown(f"- **{letra}** (brecha {delta:.2f}): {descripciones_chaside[letra]}")

# ============================================
# FIN DEL MÓDULO
# ============================================
