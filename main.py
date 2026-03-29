# ============================================
# MÓDULO 3 · INFORMACIÓN PARTICULAR DEL ESTUDIANTADO
# Resumen individual + resumen del módulo 2 + acciones recomendadas + PDF
# ============================================

import io
import textwrap
import streamlit as st
import pandas as pd
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

# -----------------------------------
# CONFIG STREAMLIT
# -----------------------------------
st.set_page_config(page_title="Información particular • CHASIDE", layout="wide")
st.title("📘 Información particular del estudiantado – CHASIDE")
st.caption(
    "Seleccione una carrera y un estudiante para consultar el resumen individual, "
    "las recomendaciones de acción y descargar el reporte en PDF."
)

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

# Sí/No → 1/0
df_items = (
    df[columnas_items]
      .astype(str).apply(lambda col: col.str.strip().str.lower())
      .replace({
          'sí': 1, 'si': 1, 's': 1, '1': 1, 'true': 1, 'verdadero': 1, 'x': 1,
          'no': 0, 'n': 0, '0': 0, 'false': 0, 'falso': 0, '': 0, 'nan': 0
      })
      .apply(pd.to_numeric, errors='coerce')
      .fillna(0)
      .astype(int)
)
df[columnas_items] = df_items

# Desviación intrapersona
df['Desv_Intrapersona'] = df[columnas_items].std(axis=1)
umbral_intrapersonal = df['Desv_Intrapersona'].quantile(0.10)
df['Respondio_Siempre_Igual'] = df['Desv_Intrapersona'] <= umbral_intrapersonal

# Mapeo CHASIDE
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

def col_item(i: int) -> str:
    return columnas_items[i - 1]

for a in areas:
    df[f'INTERES_{a}'] = df[[col_item(i) for i in intereses_items[a]]].sum(axis=1)
    df[f'APTITUD_{a}'] = df[[col_item(i) for i in aptitudes_items[a]]].sum(axis=1)

peso_intereses, peso_aptitudes = 0.8, 0.2
for a in areas:
    df[f'PUNTAJE_COMBINADO_{a}'] = df[f'INTERES_{a}'] * peso_intereses + df[f'APTITUD_{a}'] * peso_aptitudes
    df[f'TOTAL_{a}'] = df[f'INTERES_{a}'] + df[f'APTITUD_{a}']

df['Area_Fuerte_Ponderada'] = df.apply(
    lambda r: max(areas, key=lambda a: r[f'PUNTAJE_COMBINADO_{a}']),
    axis=1
)

score_cols = [f'PUNTAJE_COMBINADO_{a}' for a in areas]
df['Score'] = df[score_cols].max(axis=1)

# Perfiles de carrera
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
    if not p:
        return 'Sin perfil definido'
    if area_chaside in p.get('Fuerte', []):
        return 'Coherente'
    if area_chaside in p.get('Baja', []):
        return 'Requiere Orientación'
    return 'Neutral'

df['Coincidencia_Ponderada'] = df.apply(
    lambda r: evaluar(r['Area_Fuerte_Ponderada'], r[columna_carrera]),
    axis=1
)

def carrera_mejor(r):
    if r['Respondio_Siempre_Igual']:
        return 'Información no confiable'
    a = r['Area_Fuerte_Ponderada']
    c_actual = str(r[columna_carrera]).strip()
    sugeridas = [c for c, p in perfil_carreras.items() if a in p.get('Fuerte', [])]
    return c_actual if c_actual in sugeridas else (', '.join(sugeridas) if sugeridas else 'Sin sugerencia clara')

def diagnostico(r):
    if r['Carrera_Mejor_Perfilada'] == 'Información no confiable':
        return 'Información no confiable'
    if str(r[columna_carrera]).strip() == str(r['Carrera_Mejor_Perfilada']).strip():
        return 'Perfil adecuado'
    if r['Carrera_Mejor_Perfilada'] == 'Sin sugerencia clara':
        return 'Sin sugerencia clara'
    return f"Sugerencia: {r['Carrera_Mejor_Perfilada']}"

def semaforo(r):
    diag = r['Diagnóstico Primario Vocacional']
    if diag == 'Información no confiable':
        return 'Respondió siempre igual'
    if diag == 'Sin sugerencia clara':
        return 'Sin sugerencia'
    match = r['Coincidencia_Ponderada']
    if diag == 'Perfil adecuado':
        return {'Coherente':'Verde','Neutral':'Amarillo','Requiere Orientación':'Rojo'}.get(match, 'Sin sugerencia')
    if isinstance(diag, str) and diag.startswith('Sugerencia:'):
        return {'Coherente':'Verde','Neutral':'Amarillo','Requiere Orientación':'Rojo'}.get(match, 'Sin sugerencia')
    return 'Sin sugerencia'

df['Carrera_Mejor_Perfilada'] = df.apply(carrera_mejor, axis=1)
df['Diagnóstico Primario Vocacional'] = df.apply(diagnostico, axis=1)
df['Semáforo Vocacional'] = df.apply(semaforo, axis=1)

df['Carrera_Corta'] = (
    df[columna_carrera]
    .astype(str)
    .str.replace('Ingeniería', 'Ing.', regex=False)
)

# ============================================
# 3) INTENSIDAD VOCACIONAL (módulo 2 resumido)
# ============================================
df_intensidad = df[df['Semáforo Vocacional'].isin(['Verde', 'Amarillo'])].copy()

def asignar_niveles_por_carrera(grupo):
    grupo = grupo.copy()
    grupo['Nivel_Intensidad'] = np.nan

    amar = grupo[grupo['Semáforo Vocacional'] == 'Amarillo'].copy()
    ver = grupo[grupo['Semáforo Vocacional'] == 'Verde'].copy()

    if len(amar) > 0:
        amar = amar.sort_values('Score', ascending=True).copy()
        amar['rank_pct'] = (np.arange(len(amar)) + 1) / len(amar)
        amar['Nivel_Intensidad'] = np.where(
            amar['rank_pct'] <= 0.25,
            'Sin perfil',
            'Perfil en riesgo'
        )
        grupo.loc[amar.index, 'Nivel_Intensidad'] = amar['Nivel_Intensidad']

    if len(ver) > 0:
        ver = ver.sort_values('Score', ascending=True).copy()
        ver['rank_pct'] = (np.arange(len(ver)) + 1) / len(ver)
        ver['Nivel_Intensidad'] = np.where(
            ver['rank_pct'] > 0.75,
            'Jóven promesa',
            'Perfil en transición'
        )
        grupo.loc[ver.index, 'Nivel_Intensidad'] = ver['Nivel_Intensidad']

    return grupo

if not df_intensidad.empty:
    df_intensidad = (
        df_intensidad
        .groupby(columna_carrera, group_keys=False)
        .apply(asignar_niveles_por_carrera)
        .copy()
    )

# ============================================
# 4) DESTINO VOCACIONAL COMPATIBLE (módulo 2 resumido)
# ============================================
def letras_carrera(carrera):
    perfil = perfil_carreras.get(str(carrera).strip(), {})
    return perfil.get('Fuerte', [])

def puntaje_promedio_carrera(row, carrera):
    letras = letras_carrera(carrera)
    if not letras:
        return np.nan
    vals = [row[f'PUNTAJE_COMBINADO_{l}'] for l in letras]
    return np.mean(vals)

def carreras_compatibles(carrera_origen):
    letras_origen = set(letras_carrera(carrera_origen))
    compatibles = []

    for carrera_destino in perfil_carreras.keys():
        if carrera_destino == carrera_origen:
            continue
        letras_destino = set(letras_carrera(carrera_destino))
        inter = letras_origen.intersection(letras_destino)
        if len(inter) >= 2:
            compatibles.append(carrera_destino)

    return compatibles

def mejor_destino_compatible(row, carrera_origen):
    score_origen = puntaje_promedio_carrera(row, carrera_origen)
    candidatas = carreras_compatibles(carrera_origen)

    mejor_carrera = carrera_origen
    mejor_score = score_origen

    for c in candidatas:
        score_c = puntaje_promedio_carrera(row, c)
        if pd.notna(score_c) and score_c > mejor_score:
            mejor_score = score_c
            mejor_carrera = c

    return mejor_carrera

df['Destino_Compatible'] = df.apply(
    lambda row: mejor_destino_compatible(row, str(row[columna_carrera]).strip()),
    axis=1
)

# ============================================
# 5) ESTRATEGIAS CHASIDE
# ============================================
estrategias_chaside = {
    "C": {
        "area": "Administrativo",
        "estrategia": (
            "Fortalecer actividades de organización, planeación, seguimiento de instrucciones, "
            "gestión del tiempo y resolución estructurada de problemas."
        )
    },
    "H": {
        "area": "Humanidades y Sociales",
        "estrategia": (
            "Promover comunicación oral y escrita, argumentación, comprensión de textos, "
            "análisis de casos y trabajo colaborativo."
        )
    },
    "A": {
        "area": "Artístico",
        "estrategia": (
            "Incorporar ejercicios de creatividad, diseño, visualización de ideas, "
            "prototipos y solución innovadora de problemas."
        )
    },
    "S": {
        "area": "Ciencias de la Salud",
        "estrategia": (
            "Favorecer observación, precisión, estudio de casos, empatía profesional "
            "y actividades con orientación al servicio."
        )
    },
    "I": {
        "area": "Enseñanzas Técnicas",
        "estrategia": (
            "Reforzar pensamiento lógico, modelado, cálculo, uso de herramientas, "
            "prácticas guiadas y resolución técnica de problemas."
        )
    },
    "D": {
        "area": "Defensa y Seguridad",
        "estrategia": (
            "Impulsar liderazgo, disciplina, trabajo en equipo, responsabilidad "
            "y toma de decisiones en contextos estructurados."
        )
    },
    "E": {
        "area": "Ciencias Experimentales",
        "estrategia": (
            "Estimular observación sistemática, experimentación, interpretación de datos, "
            "método y pensamiento crítico."
        )
    }
}

descripcion_intensidad = {
    "Sin perfil": "Estudiante cuya elección de carrera no muestra correspondencia con su perfil vocacional. Se recomienda reevaluación vocacional y posible cambio de carrera.",
    "Perfil en riesgo": "Estudiante cuyo perfil vocacional presenta una coincidencia mínima con la carrera elegida. Existe alto riesgo de dificultades en asignaturas específicas de la carrera.",
    "Perfil en transición": "Estudiante cuya elección profesional y perfil vocacional presentan congruencia, aunque aún en proceso de consolidación.",
    "Jóven promesa": "Estudiante con alta congruencia entre su perfil vocacional y la carrera elegida, con condiciones favorables para un desempeño sólido."
}

# ============================================
# 6) RESUMEN DE PRIORIDADES CHASIDE POR CARRERA
# ============================================
def calcular_prioridades_carrera(df_base, carrera_sel):
    if df_intensidad.empty:
        return pd.DataFrame()

    sub = df_intensidad[df_intensidad[columna_carrera] == carrera_sel].copy()
    riesgo = sub[sub['Nivel_Intensidad'] == 'Perfil en riesgo'].copy()
    promesa = sub[sub['Nivel_Intensidad'] == 'Jóven promesa'].copy()

    if riesgo.empty or promesa.empty:
        return pd.DataFrame()

    total_cols = [f"TOTAL_{a}" for a in areas]

    prom_riesgo = riesgo[total_cols].mean()
    prom_promesa = promesa[total_cols].mean()

    resultados = []
    for a in areas:
        meta = prom_promesa[f"TOTAL_{a}"]
        medido = prom_riesgo[f"TOTAL_{a}"]

        if meta == 0:
            error_pct = 0
        else:
            error_pct = ((meta - medido) / meta) * 100

        error_pct = max(error_pct, 0)

        resultados.append({
            'Letra': a,
            'Área': estrategias_chaside[a]['area'],
            'Meta': float(meta),
            'Medido': float(medido),
            'Error_Porcentual': float(error_pct)
        })

    df_plot = pd.DataFrame(resultados).sort_values('Error_Porcentual', ascending=False).reset_index(drop=True)

    total_error = df_plot['Error_Porcentual'].sum()
    if total_error == 0:
        df_plot['Porcentaje_Relativo'] = 0.0
        df_plot['Acumulado'] = 0.0
    else:
        df_plot['Porcentaje_Relativo'] = df_plot['Error_Porcentual'] / total_error * 100
        df_plot['Acumulado'] = df_plot['Porcentaje_Relativo'].cumsum()

    df_plot['Dentro_80'] = False
    acumulado_tmp = 0.0
    for idx in df_plot.index:
        if acumulado_tmp < 80:
            df_plot.at[idx, 'Dentro_80'] = True
            acumulado_tmp = df_plot.at[idx, 'Acumulado']

    return df_plot
    
# ============================================
# 7) SELECCIÓN CARRERA → ESTUDIANTE
# ============================================
st.markdown("### 🧭 Selección de carrera y estudiante")

carreras = sorted(df[columna_carrera].dropna().astype(str).unique())
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

al = alumno.iloc[0]

# Nivel intensidad del alumno
nivel_alumno = None
if not df_intensidad.empty and alumno.index[0] in df_intensidad.index:
    nivel_alumno = df_intensidad.loc[alumno.index[0], 'Nivel_Intensidad']

# ============================================
# 8) REPORTE INDIVIDUAL
# ============================================
st.markdown("## 🧾 Resumen individual")

cat_map_largo = {
    'Verde': 'El perfil coincide con la carrera elegida',
    'Amarillo': 'El perfil NO va acorde con la carrera elegida',
    'Rojo': 'No se observa un perfil prioritario',
    'Sin sugerencia': 'No se observa un perfil prioritario',
    'Respondió siempre igual': 'Respondió siempre igual'
}

categoria = al['Semáforo Vocacional']
categoria_larga = cat_map_largo.get(categoria, categoria)
cat_color = {
    "Verde": "#22c55e",
    "Amarillo": "#f59e0b",
    "Rojo": "#6b7280",
    "Sin sugerencia": "#6b7280",
    "Respondió siempre igual": "#ef4444"
}.get(categoria, "#64748b")

cat_count_carrera = int((d_carrera['Semáforo Vocacional'] == categoria).sum())
cat_pct_carrera = (cat_count_carrera / len(d_carrera) * 100) if len(d_carrera) else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"**Estudiante:** {est_sel}")
    st.markdown(f"**Carrera:** {carrera_sel}")
with c2:
    st.markdown(f"**Perfil identificado:** <span style='color:{cat_color}; font-weight:bold'>{categoria_larga}</span>", unsafe_allow_html=True)
    st.markdown(f"**Área fuerte CHASIDE:** {al['Area_Fuerte_Ponderada']}")
with c3:
    st.markdown(f"**Estudiantes con este perfil en la carrera:** {cat_count_carrera} ({cat_pct_carrera:.1f}%)")
    st.markdown(f"**Intensidad vocacional:** {nivel_alumno if pd.notna(nivel_alumno) else 'No disponible'}")

st.divider()

# ============================================
# 9) RESUMEN DEL MÓDULO 2
# ============================================
st.markdown("## 📌 Resumen relacionado con el módulo 2")

# Distribución carrera
conteo_carrera = d_carrera['Semáforo Vocacional'].value_counts()
verde_n = int(conteo_carrera.get('Verde', 0))
amarillo_n = int(conteo_carrera.get('Amarillo', 0))
rojo_n = int(conteo_carrera.get('Rojo', 0))
sinsug_n = int(conteo_carrera.get('Sin sugerencia', 0))
azar_n = int(conteo_carrera.get('Respondió siempre igual', 0))

st.markdown(
    f"""
En **{carrera_sel}**, la distribución general observada fue la siguiente:
- **Perfil coincide con la carrera elegida:** {verde_n}
- **Perfil NO va acorde con la carrera elegida:** {amarillo_n}
- **No se observa un perfil prioritario:** {rojo_n + sinsug_n}
- **Respondió siempre igual:** {azar_n}
"""
)

# Transición compatible individual
destino_compatible = al['Destino_Compatible']
if destino_compatible == carrera_sel:
    st.markdown("**Transición vocacional compatible:** el perfil del estudiante se mantiene dentro de la carrera elegida.")
else:
    st.markdown(f"**Transición vocacional compatible:** el perfil del estudiante presenta mayor ajuste hacia **{destino_compatible}**.")

# Prioridades de la carrera
df_prioridades = calcular_prioridades_carrera(df, carrera_sel)

if df_prioridades.empty:
    st.info("No fue posible calcular prioridades CHASIDE de la carrera bajo el criterio Perfil en riesgo vs Jóven promesa.")
else:
    criticas = df_prioridades[df_prioridades['Dentro_80']].copy()
    letras_criticas = criticas['Letra'].tolist()

    st.markdown(
        f"**Prioridades CHASIDE de la carrera (criterio 80-20):** {', '.join(letras_criticas)}"
    )

st.divider()

# ============================================
# 10) FORTALEZAS INDIVIDUALES Y ÁREAS A REFORZAR
# ============================================
st.markdown("## ✅ Fortalezas y áreas a reforzar")

ref_cols = [f'TOTAL_{a}' for a in areas]
mask_carrera = df[columna_carrera] == carrera_sel
mask_verde = df['Semáforo Vocacional'] == 'Verde'

if df.loc[mask_carrera & mask_verde, ref_cols].empty:
    ref_df = df.loc[mask_carrera, ref_cols]
    referencia = "Promedio general de la carrera"
else:
    ref_df = df.loc[mask_carrera & mask_verde, ref_cols]
    referencia = "Promedio del grupo con perfil congruente"

grupo_vec = ref_df.mean().astype(float)
alumno_vec = df.loc[alumno_mask, ref_cols].iloc[0].astype(float)

df_comp = pd.DataFrame({
    "Letra": areas,
    "Alumno": [alumno_vec[f"TOTAL_{a}"] for a in areas],
    "Referencia": [grupo_vec[f"TOTAL_{a}"] for a in areas],
})
df_comp["Delta"] = df_comp["Alumno"] - df_comp["Referencia"]

fortalezas = df_comp[df_comp["Delta"] > 0].sort_values("Delta", ascending=False)
debilidades = df_comp[df_comp["Delta"] < 0].copy()
debilidades["Brecha"] = debilidades["Delta"].abs()
debilidades = debilidades.sort_values("Brecha", ascending=False)

st.markdown(f"**Referencia utilizada:** {referencia}")

colf, cold = st.columns(2)

with colf:
    st.markdown("### Fortalezas destacadas")
    if fortalezas.empty:
        st.info("No se observaron letras por encima de la referencia.")
    else:
        for _, row in fortalezas.iterrows():
            letra = row['Letra']
            st.markdown(
                f"- **{letra} ({estrategias_chaside[letra]['area']})**: "
                f"{row['Delta']:.2f} puntos por arriba de la referencia."
            )

with cold:
    st.markdown("### Áreas por reforzar")
    if debilidades.empty:
        st.info("No se observaron brechas por debajo de la referencia.")
    else:
        for _, row in debilidades.head(3).iterrows():
            letra = row['Letra']
            st.markdown(
                f"- **{letra} ({estrategias_chaside[letra]['area']})**: "
                f"{row['Brecha']:.2f} puntos por debajo de la referencia."
            )

st.divider()

# ============================================
# 11) ACCIONES RECOMENDADAS
# ============================================
st.markdown("## 🛠️ Acciones recomendadas")

acciones = []

# Acción por categoría
if categoria == 'Respondió siempre igual':
    acciones.append(
        "Reaplicar el instrumento CHASIDE en condiciones controladas, ya que las respuestas actuales no permiten una interpretación vocacional confiable."
    )
elif categoria == 'Rojo' or categoria == 'Sin sugerencia':
    acciones.append(
        "Programar entrevista de orientación vocacional individual para explorar intereses, expectativas de carrera y alternativas académicas compatibles."
    )
elif categoria == 'Amarillo':
    acciones.append(
        "Dar seguimiento tutorial focalizado durante el primer semestre para prevenir dificultades de ajuste vocacional y académico."
    )
elif categoria == 'Verde':
    acciones.append(
        "Mantener acompañamiento preventivo y reforzar hábitos de estudio y permanencia, especialmente en el primer semestre."
    )

# Acción por intensidad
if pd.notna(nivel_alumno):
    acciones.append(descripcion_intensidad.get(nivel_alumno, ""))

# Acción por destino compatible
if destino_compatible != carrera_sel:
    acciones.append(
        f"Explorar la compatibilidad del perfil con **{destino_compatible}**, ya que el análisis de ajuste muestra mejor correspondencia vocacional hacia esa opción."
    )

# Acción por debilidades individuales
if not debilidades.empty:
    for _, row in debilidades.head(2).iterrows():
        letra = row['Letra']
        acciones.append(
            f"Trabajar el área **{letra} ({estrategias_chaside[letra]['area']})**. Estrategia sugerida: {estrategias_chaside[letra]['estrategia']}"
        )

# Acción por prioridades de carrera
if not df_prioridades.empty:
    criticas = df_prioridades[df_prioridades['Dentro_80']].copy()
    for _, row in criticas.head(2).iterrows():
        letra = row['Letra']
        acciones.append(
            f"Como acción institucional para **{carrera_sel}**, conviene reforzar la dimensión **{letra} ({row['Área']})**, ya que forma parte del 80% de la brecha prioritaria de la carrera."
        )

# Limpieza de duplicados preservando orden
acciones_finales = []
vistos = set()
for a in acciones:
    a_clean = a.strip()
    if a_clean and a_clean not in vistos:
        acciones_finales.append(a_clean)
        vistos.add(a_clean)

for i, accion in enumerate(acciones_finales, start=1):
    st.markdown(f"**{i}.** {accion}")

st.divider()

# ============================================
# 12) RESUMEN EN PDF
# ============================================
def build_pdf_report(
    estudiante: str,
    carrera: str,
    categoria_larga: str,
    intensidad: str,
    area_fuerte: str,
    destino: str,
    resumen_carrera_txt: str,
    fortalezas_txt: list[str],
    debilidades_txt: list[str],
    acciones_txt: list[str],
    prioridades_txt: list[str]
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TitleBlue',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F766E"),
        alignment=TA_LEFT,
        spaceAfter=10
    ))
    styles.add(ParagraphStyle(
        name='HeadingTeal',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0F766E"),
        spaceBefore=8,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='BodySmall',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        spaceAfter=6
    ))

    story = []

    story.append(Paragraph("Reporte individual CHASIDE", styles['TitleBlue']))
    story.append(Paragraph(f"<b>Estudiante:</b> {estudiante}", styles['BodySmall']))
    story.append(Paragraph(f"<b>Carrera:</b> {carrera}", styles['BodySmall']))
    story.append(Paragraph(f"<b>Perfil identificado:</b> {categoria_larga}", styles['BodySmall']))
    story.append(Paragraph(f"<b>Intensidad vocacional:</b> {intensidad}", styles['BodySmall']))
    story.append(Paragraph(f"<b>Área fuerte CHASIDE:</b> {area_fuerte}", styles['BodySmall']))
    story.append(Paragraph(f"<b>Destino vocacional compatible:</b> {destino}", styles['BodySmall']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Resumen del módulo 2", styles['HeadingTeal']))
    story.append(Paragraph(resumen_carrera_txt, styles['BodySmall']))

    story.append(Paragraph("Fortalezas destacadas", styles['HeadingTeal']))
    if fortalezas_txt:
        for item in fortalezas_txt:
            story.append(Paragraph(f"- {item}", styles['BodySmall']))
    else:
        story.append(Paragraph("No se identificaron fortalezas por encima de la referencia.", styles['BodySmall']))

    story.append(Paragraph("Áreas por reforzar", styles['HeadingTeal']))
    if debilidades_txt:
        for item in debilidades_txt:
            story.append(Paragraph(f"- {item}", styles['BodySmall']))
    else:
        story.append(Paragraph("No se identificaron brechas por debajo de la referencia.", styles['BodySmall']))

    story.append(Paragraph("Prioridades CHASIDE de la carrera", styles['HeadingTeal']))
    if prioridades_txt:
        for item in prioridades_txt:
            story.append(Paragraph(f"- {item}", styles['BodySmall']))
    else:
        story.append(Paragraph("No fue posible identificar prioridades CHASIDE para la carrera.", styles['BodySmall']))

    story.append(Paragraph("Acciones recomendadas", styles['HeadingTeal']))
    for i, item in enumerate(acciones_txt, start=1):
        story.append(Paragraph(f"{i}. {item}", styles['BodySmall']))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Textos para PDF
resumen_carrera_txt = (
    f"En {carrera_sel}, la distribución general observada fue: "
    f"{verde_n} estudiantes con perfil congruente, "
    f"{amarillo_n} con perfil no acorde, "
    f"{rojo_n + sinsug_n} sin perfil prioritario claro y "
    f"{azar_n} con respuestas poco confiables. "
    f"Para este estudiante, el destino vocacional compatible calculado fue: {destino_compatible}."
)

fortalezas_pdf = []
if not fortalezas.empty:
    for _, row in fortalezas.iterrows():
        letra = row['Letra']
        fortalezas_pdf.append(
            f"{letra} ({estrategias_chaside[letra]['area']}): {row['Delta']:.2f} puntos por arriba de la referencia."
        )

debilidades_pdf = []
if not debilidades.empty:
    for _, row in debilidades.head(3).iterrows():
        letra = row['Letra']
        debilidades_pdf.append(
            f"{letra} ({estrategias_chaside[letra]['area']}): {row['Brecha']:.2f} puntos por debajo de la referencia."
        )

prioridades_pdf = []
if not df_prioridades.empty:
    criticas = df_prioridades[df_prioridades['Dentro_80']].copy()
    for _, row in criticas.iterrows():
        prioridades_pdf.append(
            f"{row['Letra']} ({row['Área']}): error porcentual de {row['Error_Porcentual']:.2f}%."
        )

pdf_bytes = build_pdf_report(
    estudiante=est_sel,
    carrera=carrera_sel,
    categoria_larga=categoria_larga,
    intensidad=nivel_alumno if pd.notna(nivel_alumno) else "No disponible",
    area_fuerte=al['Area_Fuerte_Ponderada'],
    destino=destino_compatible,
    resumen_carrera_txt=resumen_carrera_txt,
    fortalezas_txt=fortalezas_pdf,
    debilidades_txt=debilidades_pdf,
    acciones_txt=acciones_finales,
    prioridades_txt=prioridades_pdf
)

st.download_button(
    label="⬇️ Descargar perfil identificado en PDF",
    data=pdf_bytes,
    file_name=f"perfil_CHASIDE_{est_sel.replace(' ', '_')}.pdf",
    mime="application/pdf",
    use_container_width=True
)

# ============================================
# 9) UBICACIÓN DEL ESTUDIANTE EN EL ANÁLISIS DEL MÓDULO 2
# ============================================
st.markdown("## 📍 Ubicación del estudiante dentro del análisis general")

# Etiquetas largas
cat_map_largo = {
    'Verde': 'El perfil coincide con la carrera elegida',
    'Amarillo': 'El perfil NO va acorde con la carrera elegida',
    'Rojo': 'No se observa un perfil prioritario',
    'Sin sugerencia': 'No se observa un perfil prioritario',
    'Respondió siempre igual': 'Respondió siempre igual'
}

categoria_larga = cat_map_largo.get(al['Semáforo Vocacional'], al['Semáforo Vocacional'])

# 1. Ubicación en pastel general
conteo_global = df['Semáforo Vocacional'].value_counts()
n_global_cat = int(conteo_global.get(al['Semáforo Vocacional'], 0))
pct_global_cat = (n_global_cat / len(df) * 100) if len(df) else 0

# 2. Ubicación en carrera
conteo_carrera = d_carrera['Semáforo Vocacional'].value_counts()
n_carrera_cat = int(conteo_carrera.get(al['Semáforo Vocacional'], 0))
pct_carrera_cat = (n_carrera_cat / len(d_carrera) * 100) if len(d_carrera) else 0

# 3. Intensidad vocacional
if pd.notna(nivel_alumno):
    texto_intensidad = descripcion_intensidad.get(nivel_alumno, nivel_alumno)
else:
    texto_intensidad = "No fue posible determinar el nivel de intensidad vocacional para este estudiante."

# 4. Transición compatible
if destino_compatible == carrera_sel:
    texto_transicion = "El perfil del estudiante se mantiene dentro de la carrera elegida."
else:
    texto_transicion = f"El perfil del estudiante presenta mejor ajuste hacia la carrera **{destino_compatible}**."

st.markdown(
    f"""
- **Distribución general del estudiantado:** el estudiante pertenece a la categoría **{categoria_larga}**, 
la cual concentra **{n_global_cat} estudiantes ({pct_global_cat:.1f}%)** del total evaluado.

- **Distribución por carrera y categoría:** dentro de **{carrera_sel}**, el estudiante se ubica en la categoría 
**{categoria_larga}**, grupo conformado por **{n_carrera_cat} estudiantes ({pct_carrera_cat:.1f}%)** de su carrera.

- **Intensidad del perfil vocacional por carrera:** el estudiante fue clasificado como **{nivel_alumno if pd.notna(nivel_alumno) else 'No disponible'}**.  
  {texto_intensidad}

- **Transición vocacional compatible por carrera:** {texto_transicion}
"""
)
