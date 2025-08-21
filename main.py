# ============================================
# MÓDULO 3 · INFORMACIÓN PARTICULAR DEL ESTUDIANTADO
# ============================================
# Uso: streamlit run modulo3_info_particular.py

# 📌 IMPORTS
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px

# 📌 CONFIG
st.set_page_config(page_title="Información particular • CHASIDE", layout="wide")
st.title("📘 Información particular del estudiantado – CHASIDE")

# ============================================
# 1) CARGA DE DATOS
# ============================================
st.caption("Este módulo procesa CHASIDE y permite evaluar una carrera específica.")

url = st.text_input(
    "URL de Google Sheets (CSV export)",
    "https://docs.google.com/spreadsheets/d/1BNAeOSj2F378vcJE5-T8iJ8hvoseOleOHr-I7mVfYu4/export?format=csv"
)

@st.cache_data(show_spinner=False)
def load_data(u):
    df = pd.read_csv(u)
    return df

try:
    df = load_data(url)
except Exception as e:
    st.error(f"❌ No pude cargar el archivo: {e}")
    st.stop()

# ============================================
# 2) PREPROCESAMIENTO CHASIDE (igual a tu guía)
# ============================================
columnas_items = df.columns[5:103]
columna_carrera = '¿A qué carrera desea ingresar?'
columna_nombre  = 'Ingrese su nombre completo'

faltantes = [c for c in [columna_carrera, columna_nombre] if c not in df.columns]
if faltantes:
    st.error(f"❌ Faltan columnas requeridas: {faltantes}")
    st.stop()

# Sí/No → 1/0 (robusto)
df_items = (
    df[columnas_items]
    .astype(str).apply(lambda c: c.str.strip().str.lower())
    .replace({
        'sí':1,'si':1,'s':1,'1':1,'true':1,'verdadero':1,'x':1,
        'no':0,'n':0,'0':0,'false':0,'falso':0,'':'0','nan':0
    })
    .apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
)
df[columnas_items] = df_items

# Coincidencia sospechosa
suma_si = df[columnas_items].sum(axis=1)
total_items = len(columnas_items)
pct_si  = np.where(total_items==0, 0, suma_si/total_items)
pct_no  = 1 - pct_si
df['Coincidencia'] = np.maximum(pct_si, pct_no)

# Mapas CHASIDE
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

# Ponderación (control rápido)
with st.sidebar:
    st.subheader("⚖️ Ponderación")
    peso_intereses = st.slider("Peso Intereses", 0.0, 1.0, 0.8, 0.05)
peso_aptitudes = 1 - peso_intereses

for a in areas:
    df[f'PUNTAJE_COMBINADO_{a}'] = df[f'INTERES_{a}']*peso_intereses + df[f'APTITUD_{a}']*peso_aptitudes
df['Area_Fuerte_Ponderada'] = df.apply(lambda r: max(areas, key=lambda a: r[f'PUNTAJE_COMBINADO_{a}']), axis=1)

# Perfiles de carrera (coherencia)
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
    'Ingeniería en Sistemas Computacionales': {'Fuerte': ['I','E']},
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
    if diag=='Sin sugerencia clara':     return 'Sin sugerencia'
    match=r['Coincidencia_Ponderada']
    if diag=='Perfil adecuado':
        return {'Coherente':'Verde','Neutral':'Amarillo','Requiere Orientación':'Rojo'}.get(match,'Sin sugerencia')
    if diag.startswith('Sugerencia:'):
        return {'Coherente':'Verde','Neutral':'Amarillo','Requiere Orientación':'Rojo'}.get(match,'Sin sugerencia')
    return 'Sin sugerencia'

df['Carrera_Mejor_Perfilada']     = df.apply(carrera_mejor, axis=1)
df['Diagnóstico Primario Vocacional'] = df.apply(diagnostico, axis=1)
df['Semáforo Vocacional']         = df.apply(semaforo, axis=1)

# Un score simple para ordenar/analizar
score_cols = [f'PUNTAJE_COMBINADO_{a}' for a in areas]
df['Score'] = df[score_cols].max(axis=1)

# ============================================
# 3) PESTAÑA: ELEGIR CARRERA A EVALUAR
# ============================================
st.markdown("### 🧭 Evaluar una carrera")
tabs = st.tabs(["Seleccionar carrera"])
with tabs[0]:
    carreras = sorted(df[columna_carrera].dropna().unique())
    if not carreras:
        st.warning("No hay carreras en el archivo.")
        st.stop()

    carrera_sel = st.selectbox("Elige la carrera a evaluar:", carreras, index=0)

    # Subconjunto de la carrera
    d = df[df[columna_carrera] == carrera_sel].copy()
    n_total = len(d)
    if n_total == 0:
        st.info("No hay estudiantes para esta carrera.")
        st.stop()

    # KPIs rápidos
    k_verde   = int((d['Semáforo Vocacional']=='Verde').sum())
    k_amar    = int((d['Semáforo Vocacional']=='Amarillo').sum())
    k_sin     = int((d['Semáforo Vocacional']=='Sin sugerencia').sum())
    k_noacc   = int((d['Semáforo Vocacional']=='No aceptable').sum())

    c1,c2,c3,c4,c5 = st.columns([1.2,1,1,1,1])
    c1.metric("👩‍🎓 Estudiantes", n_total)
    c2.metric("🟢 Verde", k_verde)
    c3.metric("🟡 Amarillo", k_amar)
    c4.metric("⚪️ Sin sugerencia", k_sin)
    c5.metric("🔴 No aceptable", k_noacc)

    # Pastel solo de esa carrera (opcional, ayuda a visualizar)
    resumen = (
        d['Semáforo Vocacional']
        .value_counts()
        .reindex(['Verde','Amarillo','Sin sugerencia','No aceptable'], fill_value=0)
        .reset_index()
        .rename(columns={'index':'Categoría','Semáforo Vocacional':'N'})
    )
    fig = px.pie(
        resumen, names='Categoría', values='N', hole=0.35,
        color='Categoría',
        color_discrete_map={'Verde':'#22c55e','Amarillo':'#f59e0b','Sin sugerencia':'#94a3b8','No aceptable':'#ef4444'},
        title=f"Distribución por categoría – {carrera_sel}"
    )
    fig.update_traces(textposition='inside', texttemplate='%{label}<br>%{percent:.1%} (%{value})')
    st.plotly_chart(fig, use_container_width=True)

    # Tabla ejecutiva de estudiantes de la carrera
    cols_tabla = [
        columna_nombre, 'Semáforo Vocacional', 'Area_Fuerte_Ponderada', 'Score',
        'Carrera_Mejor_Perfilada', 'Diagnóstico Primario Vocacional'
    ]
    st.subheader("📄 Estudiantes y diagnóstico")
    st.dataframe(
        d[cols_tabla].sort_values(['Semáforo Vocacional','Score'], ascending=[True, False]),
        use_container_width=True
    )

    # Descarga
    st.download_button(
        "⬇️ Descargar reporte de la carrera (CSV)",
        data=d[cols_tabla].to_csv(index=False).encode('utf-8'),
        file_name=f"reporte_{carrera_sel.replace(' ','_')}.csv",
        mime="text/csv"
    )
