# ============================================
# MÓDULO 3 · INFORMACIÓN PARTICULAR DEL ESTUDIANTADO (REPORTE EJECUTIVO, SIN RADAR)
# ============================================

import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------------
# CONFIG STREAMLIT
# -----------------------------------
st.set_page_config(page_title="Información particular • CHASIDE", layout="wide")
st.title("📘 Información particular del estudiantado – CHASIDE")
st.caption("Seleccione una carrera y un estudiante para consultar el reporte ejecutivo individual.")

# ============================================
# 1) CARGA DE DATOS
# ============================================
url = st.text_input(
    "URL de Google Sheets (CSV export)",
    "https://docs.google.com/spreadsheets/d/1BNAeOSj2F378vcJE5-T8iJ8hvoseOleOHr-I7mVfYu4/export?format=csv"
)

@st.cache_data(show_spinner=False)
def load_data(u: str) -> pd.DataFrame:
    return pd.read_csv(u)

try:
    df = load_data(url)
except Exception as e:
    st.error(f"❌ No fue posible cargar el archivo: {e}")
    st.stop()

# ============================================
# 2) PREPROCESAMIENTO CHASIDE
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

# Ponderación fija
peso_intereses, peso_aptitudes = 0.8, 0.2
for a in areas:
    df[f'PUNTAJE_COMBINADO_{a}'] = df[f'INTERES_{a}']*peso_intereses + df[f'APTITUD_{a}']*peso_aptitudes

df['Area_Fuerte_Ponderada'] = df.apply(lambda r: max(areas, key=lambda a: r[f'PUNTAJE_COMBINADO_{a}']), axis=1)

# Perfiles y coherencia
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

# ============================================
# 3) UI: SELECCIÓN CARRERA → ESTUDIANTE
# ============================================
st.markdown("### 🧭 Seleccione carrera y estudiante")

carreras = sorted(df[columna_carrera].dropna().unique())
if not carreras:
    st.warning("No hay carreras disponibles en el archivo.")
    st.stop()

carrera_sel = st.selectbox("Carrera a evaluar:", carreras, index=0)

d_carrera = df[df[columna_carrera] == carrera_sel].copy()
if d_carrera.empty:
    st.warning("No hay estudiantes para esta carrera.")
    st.stop()

nombres = sorted(d_carrera[columna_nombre].astype(str).unique())
est_sel = st.selectbox("Estudiante:", nombres, index=0)

alumno_mask = (df[columna_carrera] == carrera_sel) & (df[columna_nombre].astype(str) == est_sel)
alumno = df[alumno_mask].copy()
if alumno.empty:
    st.warning("No se encontró el estudiante seleccionado.")
    st.stop()

# ============================================
# 📌 REPORTE EJECUTIVO INDIVIDUAL
# ============================================

st.header("📑 Reporte ejecutivo individual")

# Selección carrera
carreras_disp = sorted(df[columna_carrera].dropna().unique())
carrera_sel = st.selectbox("Seleccione la carrera", carreras_disp)

if carrera_sel:
    sub = df[df[columna_carrera] == carrera_sel].copy()

    # Selección estudiante
    alumnos = sorted(sub[columna_nombre].dropna().unique())
    alumno_sel = st.selectbox("Seleccione el estudiante", alumnos)

    if alumno_sel:
        alumno = sub[sub[columna_nombre] == alumno_sel].iloc[0]

        # Datos básicos
        categoria = alumno['Semáforo Vocacional']
        total_cat = (df['Semáforo Vocacional'] == categoria).sum()

        st.markdown(f"""
        ### Informe del estudiante
        **Nombre completo:** {alumno_sel}  
        **Carrera elegida:** {carrera_sel}  
        **Categoría obtenida:** <span style='color:{"#22c55e" if categoria=="Verde" else "#f59e0b" if categoria=="Amarillo" else "#6b7280"}; font-weight:bold'>{categoria}</span>  
        **Número de estudiantes en esta categoría:** {total_cat}
        """, unsafe_allow_html=True)

        # Joven promesa o en riesgo
        df_scores = df.copy()
        df_scores['Score'] = df_scores[[f'PUNTAJE_COMBINADO_{a}' for a in areas]].max(axis=1)

        top_verde = (
            df_scores[df_scores['Semáforo Vocacional'] == 'Verde']
            .nlargest(5, 'Score')[columna_nombre].tolist()
        )
        bottom_amarillo = (
            df_scores[df_scores['Semáforo Vocacional'] == 'Amarillo']
            .nsmallest(5, 'Score')[columna_nombre].tolist()
        )

        if alumno_sel in top_verde:
            st.success("🌟 Estatus: **Joven promesa** (Top 5 en Verde)")
        elif alumno_sel in bottom_amarillo:
            st.warning("⚠️ Estatus: **Joven en riesgo** (Bottom 5 en Amarillo)")

        # Coincidencia carrera vs perfil
        mejor = alumno['Carrera_Mejor_Perfilada']
        if mejor == carrera_sel:
            st.success(f"✅ La carrera elegida **{carrera_sel}** coincide con el perfil CHASIDE del estudiante.")
        else:
            st.warning(f"❌ La carrera elegida **{carrera_sel}** no coincide plenamente con su perfil. "
                       f"Podría desenvolverse mejor en: **{mejor}**")

        # Comparar alumno vs grupo verde de la carrera
        grupo_ref = sub[sub['Semáforo Vocacional'] == 'Verde']
        if not grupo_ref.empty:
            # Totales por letra
            for a in areas:
                df[f'TOTAL_{a}'] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

            alumno_vec = alumno[[f'TOTAL_{a}' for a in areas]].astype(float)
            grupo_vec  = grupo_ref[[f'TOTAL_{a}' for a in areas]].mean().astype(float)

            diffs = (alumno_vec - grupo_vec).sort_values()

            st.markdown("### Áreas por reforzar (principales brechas)")
            for letra, delta in diffs.head(3).items():
                letra_real = letra.replace("TOTAL_","")
                st.markdown(f"- **{letra_real}**: puntaje menor al promedio del grupo Verde en {abs(delta):.2f} puntos.")
                # ============================================
# 5) COMPARATIVO VS PROMEDIO DEL GRUPO (SIN GRÁFICA)
#    ***FIX***: calcular referencia SIEMPRE desde `df` con máscaras,
#    no desde `d_carrera`/`grupo_ref` ya que podrían no tener TOTAL_*.
# ============================================

# Asegurar columnas TOTAL_* (INTERES + APTITUD) en df
for a in areas:
    if f'TOTAL_{a}' not in df.columns:
        df[f'TOTAL_{a}'] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

# Máscaras para referencia
mask_carrera = df[columna_carrera] == carrera_sel
mask_verde   = df['Semáforo Vocacional'] == 'Verde'

ref_cols = [f'TOTAL_{a}' for a in areas]

if df.loc[mask_carrera & mask_verde, ref_cols].empty:
    ref_df = df.loc[mask_carrera, ref_cols]
    referencia = "Promedio general de la carrera (no hay estudiantes Verde)"
else:
    ref_df = df.loc[mask_carrera & mask_verde, ref_cols]
    referencia = "Promedio del grupo Verde de la carrera"

grupo_vec  = ref_df.mean().astype(float)
alumno_vec = df.loc[alumno_mask, ref_cols].iloc[0].astype(float)

df_comp = pd.DataFrame({
    "Letra": areas,
    "Alumno": [alumno_vec[f"TOTAL_{a}"] for a in areas],
    "Promedio grupo": [grupo_vec[f"TOTAL_{a}"] for a in areas]
})
df_comp["Diferencia (Alumno - Grupo)"] = df_comp["Alumno"] - df_comp["Promedio grupo"]

st.markdown(f"### Comparativo por dimensión CHASIDE  \n_Referencia:_ **{referencia}**")
st.dataframe(df_comp.set_index("Letra"), use_container_width=True)

# Fortalezas y Áreas por reforzar
fortalezas = df_comp[df_comp["Diferencia (Alumno - Grupo)"] > 0].sort_values(
    "Diferencia (Alumno - Grupo)", ascending=False
)[["Letra","Diferencia (Alumno - Grupo)"]]

brechas = (df_comp["Promedio grupo"] - df_comp["Alumno"])
top3_reforzar = brechas.sort_values(ascending=False).head(3)
top3_tabla = pd.DataFrame({"Letra": top3_reforzar.index, "Brecha (Grupo - Alumno)": top3_reforzar.values})

st.markdown("### Fortalezas destacadas (por encima del promedio de referencia)")
if fortalezas.empty:
    st.info("No se observan letras por encima del promedio de referencia.")
else:
    st.table(fortalezas.set_index("Letra"))

st.markdown("### Áreas por reforzar (principales brechas)")
if (top3_reforzar <= 0).all():
    st.info("El estudiante está a la par o por encima del promedio del grupo en todas las letras.")
else:
    st.table(top3_tabla.set_index("Letra"))

st.divider()

# ============================================
# 6) COHERENCIA VOCACIONAL (ELECCIÓN VS PERFIL CHASIDE)
# ============================================
st.markdown("## 🎯 Coherencia vocacional (elección vs perfil CHASIDE)")

area_fuerte = alumno.iloc[0]['Area_Fuerte_Ponderada']
carrera_elegida = carrera_sel

perfil_sel = perfil_carreras.get(str(carrera_elegida).strip())
if perfil_sel:
    if area_fuerte in perfil_sel.get('Fuerte', []):
        coincidencia = "Coherente"
    elif area_fuerte in perfil_sel.get('Baja', []):
        coincidencia = "Requiere orientación"
    else:
        coincidencia = "Neutral"
else:
    coincidencia = "Sin perfil definido"

# Sugerencias si NO es coherente
sugeridas = [c for c, p in perfil_carreras.items() if area_fuerte in p.get('Fuerte', [])]

st.markdown(
    f"""
**Área fuerte ponderada del estudiante (CHASIDE):** **{area_fuerte}**  
**Evaluación de coherencia con la carrera elegida:** **{coincidencia}**
"""
)
if coincidencia != "Coherente":
    if sugeridas:
        st.markdown("**Carreras con mayor afinidad al perfil CHASIDE del estudiante:** " + ", ".join(sugeridas))
    else:
        st.markdown("_No se encontraron sugerencias basadas en el área fuerte._")

# ============================================
# 7) DESCARGAS
# ============================================
st.markdown("## ⬇️ Descargas")

st.download_button(
    "Descargar comparativo por letra (CSV)",
    data=df_comp.to_csv(index=False).encode("utf-8"),
    file_name=f"comparativo_letras_{est_sel}.csv",
    mime="text/csv"
)

resumen_dict = {
    "Estudiante": est_sel,
    "Carrera": carrera_elegida,
    "Categoría": categoria,
    "Tamaño categoría (carrera)": cat_count,
    "Área fuerte CHASIDE": area_fuerte,
    "Coherencia elección": coincidencia,
    "Referencia comparativa": referencia,
}
resumen_dict["Fortalezas (>0)"] = "; ".join([f"{r.Letra}:{r['Diferencia (Alumno - Grupo)']:.2f}" for _, r in fortalezas.iterrows()]) if not fortalezas.empty else "-"
resumen_dict["Top3 a reforzar"] = "; ".join([f"{k}:{v:.2f}" for k, v in top3_reforzar.items() if v>0]) if not (top3_reforzar<=0).all() else "-"

resumen_df = pd.DataFrame([resumen_dict])
st.download_button(
    "Descargar resumen ejecutivo (CSV)",
    data=resumen_df.to_csv(index=False).encode("utf-8"),
    file_name=f"reporte_ejecutivo_{est_sel}.csv",
    mime="text/csv"
)
