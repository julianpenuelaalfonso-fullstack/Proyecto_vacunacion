"""Genera las gráficas (graficas/*.png) y el informe Word con los 21 puntos a partir de salidas/ (correr etl.py antes)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

BASE = Path(__file__).parent
SAL, GRA, EVI = BASE / "salidas", BASE / "graficas", BASE / "evidencias"
GRA.mkdir(exist_ok=True)
AZUL, NARANJA, VERDE, AMARILLO, ROSA, ROJO, GRIS = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#d03b3b", "#898781"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#c3c2b7", "axes.grid": True, "grid.color": "#e1e0d9", "axes.axisbelow": True})

K = json.loads((SAL / "kpis.json").read_text(encoding="utf-8"))
KP, LOG = K["kpis"], K["limpieza"]
anu = pd.read_csv(SAL / "cobertura_anual.csv")
sec = pd.read_csv(SAL / "hechos_sectores.csv")
cerr = anu[anu["anio_completo"]]
ULT, ACT = KP["ultimo_anio_cerrado"], int(anu["anio"].max())


def cob(df, por):
    g = df.groupby(por)[["dosis_aplicada", "denominador"]].sum()
    g["cobertura"] = (g["dosis_aplicada"] / g["denominador"] * 100).round(1)
    return g.sort_values("cobertura")


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(GRA / nombre, dpi=200)
    plt.close(fig)


# G1 serie anual
fig, ax = plt.subplots(figsize=(7.5, 3.6))
for b, c in zip(cerr["biologico"].unique(), [AZUL, NARANJA, VERDE, AMARILLO, ROSA]):
    d = cerr[cerr["biologico"] == b]
    ax.plot(d["anio"], d["cobertura"], marker="o", lw=2, ms=4, color=c, label=b)
ax.axhline(95, ls="--", color=ROJO, lw=1.2)
ax.text(cerr["anio"].max(), 95.8, "Meta PAI 95 %", color=ROJO, fontsize=8, ha="right")
ax.set_ylabel("Cobertura (%)")
ax.legend(fontsize=7.5, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.38), frameon=False)
ax.set_title("Cobertura anual por biológico – Bogotá D.C.", loc="left", fontweight="bold")
guardar(fig, "g1_serie_anual.png")

# G2 localidades primera infancia
loc = cob(sec[sec["grupo_biologico"] == "Primera infancia"], "localidad")
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.barh(loc.index, loc["cobertura"], color=AZUL, height=0.7)
ax.axvline(95, ls="--", color=ROJO, lw=1.2)
for y, v in enumerate(loc["cobertura"]):
    ax.text(v + 0.8, y, f"{v}", va="center", fontsize=7.5)
ax.set_xlim(0, 100)
ax.set_xlabel("Cobertura (%)")
ax.set_title("Primera infancia: cobertura por localidad (sectores, corte %s)" % KP["fecha_corte_sectores"], loc="left", fontweight="bold")
ax.grid(axis="y", visible=False)
guardar(fig, "g2_localidades.png")

# G3 sector institucional y grupo biológico
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.5, 2.8))
for ax, por, t in ((a1, "institucion", "Por sector institucional"), (a2, "grupo_biologico", "Por grupo de biológico")):
    g = cob(sec, por)
    ax.barh(g.index, g["cobertura"], color=AZUL, height=0.6)
    ax.axvline(95, ls="--", color=ROJO, lw=1.2)
    for y, v in enumerate(g["cobertura"]):
        ax.text(v + 1, y, f"{v}", va="center", fontsize=7.5)
    ax.set_xlim(0, 100)
    ax.set_title(t, loc="left", fontweight="bold")
    ax.grid(axis="y", visible=False)
guardar(fig, "g3_sector_grupo.png")

# G4 abandono del esquema: triple viral 1 año vs refuerzo 5 años
tv1 = cerr[cerr["biologico"] == "Triple viral 1 año"].set_index("anio")["cobertura"]
tv5 = cerr[cerr["biologico"].str.startswith("Triple viral R1 o DPT")].set_index("anio")["cobertura"]
anios = tv1.index.intersection(tv5.index)
fig, ax = plt.subplots(figsize=(7.5, 3.2))
for a in anios:
    ax.plot([a, a], [tv1[a], tv5[a]], color=GRIS, lw=1.5, zorder=1)
ax.scatter(anios, tv1[anios], color=AZUL, s=40, label="Triple viral 1 año", zorder=2)
ax.scatter(anios, tv5[anios], color=NARANJA, s=40, label="Refuerzo 5 años", zorder=2)
for a in anios:
    ax.text(a + 0.12, (tv1[a] + tv5[a]) / 2, f"{tv5[a] - tv1[a]:+.1f}", fontsize=7.5, va="center")
ax.axhline(95, ls="--", color=ROJO, lw=1.2)
ax.set_ylabel("Cobertura (%)")
ax.legend(fontsize=8, frameon=False, loc="lower left")
ax.set_title("Brecha entre la dosis de 1 año y el refuerzo de 5 años", loc="left", fontweight="bold")
guardar(fig, "g4_abandono.png")

# G5 año en curso vs ritmo necesario
men = pd.read_excel(SAL / "base_consolidada.xlsx", sheet_name="HECHOS_MENSUAL")
cur = men[(men["anio"] == ACT) & men["reportado"]]
fig, ax = plt.subplots(figsize=(7.5, 3.2))
for b, c in zip(cerr["biologico"].unique(), [AZUL, NARANJA, VERDE, AMARILLO, ROSA]):
    d = cur[cur["biologico"] == b]
    ax.plot(d["mes_num"], d["cobertura_acum"], marker="o", ms=3, lw=2, color=c, label=b)
ax.plot(range(1, 13), [95 * m / 12 for m in range(1, 13)], ls="--", color=GRIS, label="Ritmo para 95 %")
ax.set_xticks(range(1, 13), list("EFMAMJJASOND"))
ax.set_ylabel("Cobertura acumulada (%)")
ax.legend(fontsize=7, frameon=False, ncol=2)
ax.set_title(f"Avance {ACT} frente al ritmo necesario", loc="left", fontweight="bold")
guardar(fig, "g5_avance_actual.png")

# ---------------- Documento ----------------
doc = Document()
st = doc.styles["Normal"]
st.font.name, st.font.size = "Times New Roman", Pt(12)
st.paragraph_format.line_spacing = 1.5
for s in doc.sections:
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.54)


def p(texto, negrita=False, centro=False):
    par = doc.add_paragraph()
    r = par.add_run(texto)
    r.bold = negrita
    if centro:
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return par


def h(texto, nivel=1):
    doc.add_heading(texto, level=nivel)


def viñetas(items):
    for i in items:
        doc.add_paragraph(i, style="List Bullet")


def tabla(filas, encabezado):
    t = doc.add_table(rows=1, cols=len(encabezado))
    t.style = "Light Grid Accent 1"
    for c, txt in zip(t.rows[0].cells, encabezado):
        c.text = str(txt)
    for f in filas:
        for c, txt in zip(t.add_row().cells, f):
            c.text = str(txt)
    doc.add_paragraph()


def figura(archivo, n, titulo, nota=None, ancho=16):
    p(f"Figura {n}", negrita=True)
    doc.add_paragraph().add_run(titulo).italic = True
    doc.add_picture(str(archivo), width=Cm(ancho))
    if nota:
        doc.add_paragraph().add_run("Nota. " + nota).font.size = Pt(10)


# Portada
for _ in range(3):
    doc.add_paragraph()
p("Cobertura de vacunación infantil en Bogotá D.C.: solución de Inteligencia de Negocios con datos abiertos en tiempo real", True, True)
doc.add_paragraph()
for n in ("Daniel Felipe Rojas González", "Julián Andrés Peñuela Alfonso", "Valery Michell Herrera Roca"):
    p(n, centro=True)
doc.add_paragraph()
p("Facultad de Ingeniería, Universidad Manuela Beltrán", centro=True)
p("Inteligencia de Negocios", centro=True)
p("Docente: Juan José Osorio Tabares", centro=True)
p("Noviembre de 2026", centro=True)
doc.add_page_break()

h("1. Título del proyecto")
p("Cobertura de vacunación infantil en Bogotá D.C.: solución de Inteligencia de Negocios con datos abiertos en tiempo real "
  "para priorizar campañas de la Secretaría Distrital de Salud.")

h("2. Descripción de la problemática")
p("El Programa Ampliado de Inmunizaciones (PAI) del Ministerio de Salud y Protección Social fija una meta de cobertura del 95 % "
  "para cada biológico del esquema. En Bogotá la información existe, pero está dispersa en tableros y archivos del "
  "Observatorio de Salud (SaluData) y del Portal de Datos Abiertos, con formatos inconsistentes (separadores de miles con punto, "
  "decimales con coma, porcentajes multiplicados por diez, filas de totales mezcladas con los meses y localidades sin asignar). "
  "Además, el registro depende en parte del carné físico, lo que genera subregistro.")
p(f"Como consecuencia, los tomadores de decisión no tienen una vista única y actualizada que responda: ¿qué tan lejos está la "
  f"ciudad de la meta?, ¿en qué vacuna del esquema se empieza a perder cobertura?, ¿en qué localidades y en qué sectores "
  f"institucionales (colegios, ICBF, integración social) está el mayor rezago? Con los datos de la API se observa que ninguna "
  f"de las 20 localidades alcanza el 95 % en primera infancia y que entre la triple viral de 1 año y el refuerzo de 5 años se "
  f"pierden {KP['caida_esquema_1a5']} puntos porcentuales ({ULT}).")
p("Pregunta de investigación: ¿en qué punto del esquema de vacunación de primera infancia y en qué localidades y sectores presenta "
  "Bogotá el mayor rezago frente a la meta del 95 %, y cuánto cae la cobertura entre el año 1 y los 5 años?", negrita=True)

h("3. Caracterización de la población seleccionada")
p("La población objeto son los niños, niñas y adolescentes residentes en las 20 localidades de Bogotá D.C. que deben recibir "
  "los biológicos trazadores del esquema del PAI, con énfasis en la primera infancia (menores de 6 años). Se caracteriza así:")
tabla([
    ("Ubicación", "Bogotá D.C., 20 localidades agrupadas en 5 zonas (Norte, Centro, Sur, Occidente y Rural – Sumapaz)"),
    ("Edades", "Menores de 1 año (pentavalente), 1 año (triple viral), 18 meses–4 años y 5 años (refuerzos), 4–17 años "
               "(sarampión-rubéola, VPH, COVID-19) y adultos mayores (influenza, neumococo)"),
    ("Sectores institucionales", "Colegios oficiales, colegios privados, ICBF, Integración Social e Integración Vejez"),
    ("Cohorte de nacidos (meta anual)", f"≈ {int(cerr[cerr['anio'] == ULT]['poblacion_meta'].min()):,} niños en {ULT}, "
                                        f"frente a ≈ 99 000 en 2019 (descenso de la natalidad)".replace(",", ".")),
    ("Entidad responsable", "Secretaría Distrital de Salud (SDS) – Observatorio de Salud de Bogotá (SaluData)"),
], ["Característica", "Descripción"])

h("4. Objetivo general")
p("Diseñar e implementar una solución de Inteligencia de Negocios que consulte de forma automática la API de Datos Abiertos de "
  "Bogotá, limpie e integre los datos de cobertura de vacunación y los presente en un tablero con indicadores clave, para "
  "identificar en qué biológicos, localidades y sectores se concentra la brecha frente a la meta del 95 % y apoyar la "
  "priorización de campañas de la Secretaría Distrital de Salud.")

h("5. Objetivos específicos")
viñetas([
    "Construir un programa ETL en Python que extraiga los datos directamente de la API CKAN del Portal de Datos Abiertos de Bogotá, "
    "garantizando que cada ejecución use la versión más reciente publicada.",
    "Aplicar reglas de limpieza y validación documentadas (tipos, formatos, duplicados, valores fuera de rango, localidades no "
    "válidas) y dejar trazabilidad de cada paso.",
    "Consolidar la información en un modelo dimensional (hechos y dimensiones) exportado a Excel y CSV.",
    "Definir y calcular KPI que midan la distancia a la meta, el abandono del esquema y el avance del año en curso.",
    "Desarrollar un tablero de Inteligencia de Negocios interactivo y publicarlo con actualización diaria automática.",
    "Formular recomendaciones de priorización de campañas basadas en los hallazgos.",
])

h("6. Descripción y justificación de la población y muestra")
p(f"Se trabaja con datos administrativos secundarios, por lo que no se toma una muestra probabilística sino el universo "
  f"publicado (censo de registros). Se usan dos conjuntos de datos complementarios:")
tabla([
    ("Seguimiento cobertura vacunación – sectores", "e519cce2-9951-41de-afbc-005d1e1d24dd",
     f"{LOG['sectores']['filas_originales']} registros (localidad × biológico × sector), corte {KP['fecha_corte_sectores']}",
     "Permite comparar localidades y sectores institucionales"),
    ("Cobertura vacunación en Bogotá D.C.", "1910589c-2836-41d3-aba4-00488bb5e5f3",
     f"{LOG['mensual']['filas_originales']} registros (biológico × año × mes), 2019–{ACT}",
     "Permite ver la tendencia histórica y el avance del año en curso"),
], ["Conjunto de datos", "ID de recurso (API)", "Tamaño", "Justificación"])
p(f"Tras la limpieza quedan {LOG['sectores']['filas_finales']} registros de sectores (20 localidades × 5 sectores × hasta 15 "
  f"biológicos) y {LOG['mensual']['filas_finales']} registros mensuales. Se justifica usar el universo completo porque: (a) la "
  f"fuente es oficial y cubre el 100 % de las localidades; (b) el volumen es manejable; y (c) evita el error muestral, de modo "
  f"que las diferencias entre localidades reflejan la realidad administrativa y no la variación de una muestra. El análisis "
  f"principal se enfoca en la primera infancia (pentavalente, triple viral y refuerzos), donde la meta del PAI es más exigente.")

h("7. Diseño y aplicación del instrumento de recolección de datos")
p("Al tratarse de fuentes secundarias, el instrumento de recolección es una ficha de extracción automatizada implementada como "
  "programa: un cliente de la API DataStore de CKAN que consulta el endpoint datastore_search con paginación de 1 000 registros "
  "y valida la respuesta (campo success). El instrumento se diseñó con los siguientes componentes:")
tabla([
    ("Endpoint", "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search"),
    ("Parámetros", "resource_id, limit=1000, offset (paginación hasta completar el total)"),
    ("Variables – sectores", "FECHA_REPORTE, NOMBRE_LOCALIDAD, BIOLOGICO_EDAD, INSTITUCION, DOSIS_APLICADA, DENOMINADOR, COBERTURA"),
    ("Variables – mensual", "Biologico, Ano, Orden mes, Mes, Meta, Vacunados, Column7 (acumulado), Cobertura"),
    ("Validación", "Respuesta success=true, conteo igual al total informado por la API, tipos numéricos, rango 0–100 %"),
    ("Frecuencia de aplicación", "Cada ejecución del programa y automáticamente una vez al día (GitHub Actions)"),
    ("Almacenamiento del crudo", "salidas/crudo_sectores.csv y salidas/crudo_mensual.csv (copia fiel antes de transformar)"),
], ["Elemento", "Definición"])
p("Ejemplo de consulta que cualquier integrante o el docente puede abrir en el navegador para verificar la fuente:")
p("https://datosabiertos.bogota.gov.co/api/3/action/datastore_search?resource_id=e519cce2-9951-41de-afbc-005d1e1d24dd&limit=5")

h("8. Base de datos consolidada")
p("La base consolidada se genera en salidas/base_consolidada.xlsx siguiendo un modelo en estrella:")
tabla([
    ("HECHOS_SECTORES", "Hecho", "localidad + sector + biológico + fecha", "dosis_aplicada, denominador, cobertura_reportada, "
     "cobertura_recalculada, brecha_meta, cumple_meta, flags de calidad"),
    ("HECHOS_MENSUAL", "Hecho", "biológico + año + mes", "poblacion_meta, vacunados_mes, vacunados_acum, cobertura_acum, reportado"),
    ("COBERTURA_ANUAL", "Agregado", "biológico + año", "cobertura, anio_completo, cobertura_proyectada, brecha_meta"),
    ("DIM_LOCALIDAD", "Dimensión", "localidad", "zona"),
    ("DIM_BIOLOGICO", "Dimensión", "biológico", "grupo_biologico"),
    ("KPI", "Resumen", "indicador", "valor calculado en la última ejecución"),
    ("LOG_LIMPIEZA", "Auditoría", "paso del ETL", "registros afectados"),
], ["Hoja", "Tipo", "Granularidad", "Campos clave"])

h("9. Proceso de preparación y limpieza de los datos")
p("Las reglas se implementaron en etl.py (funciones limpiar_sectores y limpiar_mensual) y se verifican con test_etl.py:")
tabla([
    ("Espacios y texto", "Recorte de espacios y espacios dobles en todos los campos de texto", "Todos"),
    ("Escala de cobertura", "La API publica la cobertura ×10 sin decimal (708 → 70,8 %); se divide entre 10", "Sectores"),
    ("Recalcular cobertura", "cobertura = dosis / denominador × 100 y comparación con la reportada",
     f"{LOG['sectores']['filas_cobertura_inconsistente']} diferencia por redondeo"),
    ("Valores > 100 %", "Se marcan con flag_sobre_100 (no se eliminan)", f"{LOG['sectores']['filas_sobre_100']} registros"),
    ("Localidad", "Separar código y nombre; excluir 'NO ACTUALIZADO' y 'Localidad Desconocida'",
     f"{LOG['sectores']['filas_localidad_no_valida']} excluidos"),
    ("Errores de digitación", "'INTERACIÓN VEJÉZ' → 'Integración Vejez'", "Sector"),
    ("Duplicados", "Clave localidad + sector + biológico + fecha", f"{LOG['sectores']['duplicados_eliminados']} eliminados"),
    ("Formato numérico colombiano", "'98.914' → 98914; '7,8' → 7.8", "Mensual"),
    ("Filas 'Total'", f"Se eliminan y se recalculan; en {ACT} la fila Total venía con un valor erróneo",
     f"{LOG['mensual']['filas_total_eliminadas']} eliminadas"),
    ("Meses sin reporte", "Se marcan como no reportados; el año en curso se proyecta a 12 meses",
     f"{LOG['mensual']['meses_sin_reporte']} meses"),
    ("Enriquecimiento", "Zona por localidad, grupo de biológico, cumple_meta y brecha_meta", "Todos"),
], ["Paso", "Regla aplicada", "Registros afectados"])

h("10. Análisis e interpretación de los datos")
fila = lambda b: cerr[(cerr["biologico"] == b) & (cerr["anio"] == ULT)]["cobertura"].iloc[0]
p(f"Tendencia histórica. Entre 2019 y 2022 todas las coberturas cayeron (efecto de la pandemia): la triple viral de 1 año pasó de "
  f"92,6 % a 69,4 %. Desde 2023 hay recuperación y en {ULT} la pentavalente llega a {fila('Penta <1año')} % y la Tdap gestante a "
  f"{fila('Tdap gestante')} %, ambas sobre la meta; la triple viral de 1 año queda en {KP['tv_1anio_ult']} %, cerca pero por debajo.")
p(f"Abandono del esquema. El refuerzo de los 5 años no se ha recuperado: {KP['tv_5anios_ult']} % en {ULT}, es decir "
  f"{KP['caida_esquema_1a5']} puntos menos que la dosis de 1 año. Entre 2019 y 2022 la relación era la inversa (el refuerzo estaba por encima porque la caída de la pandemia golpeó primero a los más pequeños); desde 2023 la dosis de 1 año se recuperó y el refuerzo no. Hay que tener en cuenta que en un mismo año se comparan cohortes distintas, por lo que el indicador mide pérdida del esquema a nivel poblacional y no el seguimiento de los mismos niños. Lo mismo ocurre con el refuerzo de 18 meses "
  f"({fila('Triple viral R1 18 meses')} %). Mientras más crecen los niños, menos cobertura tienen: el problema no es iniciar el "
  f"esquema sino completarlo.")
p(f"Localidades. En el seguimiento por sectores ninguna localidad alcanza el 95 % en primera infancia. La menor es "
  f"{KP['localidad_menor_cobertura']} ({KP['localidad_menor_cobertura_valor']} %), seguida de Teusaquillo y Sumapaz; por volumen de "
  f"niños sin vacunar pesan más Bosa, Kennedy y Suba, con coberturas cercanas al 73–75 % sobre denominadores grandes. Las "
  f"localidades del sur (Usme, San Cristóbal, Tunjuelito) presentan las coberturas relativamente más altas.")
inst = cob(sec, "institucion")["cobertura"]
p(f"Sectores. Los colegios privados ({inst['Colegios Privados']} %) y oficiales ({inst['Colegios Oficiales']} %) superan a ICBF "
  f"({inst['Icbf']} %) e Integración Social ({inst['Integración']} %). Los biológicos de adolescentes (VPH, segundas dosis de "
  f"COVID-19) muestran las brechas más amplias.")
p(f"Calidad del dato. La Tdap gestante 2024 supera el 100 % (106,8 %) porque la población meta es una proyección que subestima la "
  f"real; por eso el modelo conserva el dato original y lo marca, en lugar de recortarlo.")

h("11. Gráficas y visualizaciones de los resultados")
figura(GRA / "g1_serie_anual.png", 1, "Cobertura anual por biológico, Bogotá D.C.", "Elaboración propia con datos de la SDS (API Datos Abiertos Bogotá).")
figura(GRA / "g4_abandono.png", 2, "Brecha entre la triple viral de 1 año y el refuerzo de 5 años", "Valores negativos = pérdida de cobertura.")
figura(GRA / "g2_localidades.png", 3, "Cobertura de primera infancia por localidad", "Seguimiento por sectores (colegios, ICBF, integración).")
figura(GRA / "g3_sector_grupo.png", 4, "Cobertura por sector institucional y por grupo de biológico")
figura(GRA / "g5_avance_actual.png", 5, f"Avance {ACT} frente al ritmo necesario para cerrar en 95 %")

h("12. Indicadores y KPI definidos")
tabla([
    ("Cobertura por biológico", "vacunados / población meta × 100", "≥ 95 %", f"{KP['tv_1anio_ult']} % (TV 1 año, {ULT})"),
    ("Brecha frente a la meta", "max(0; 95 − cobertura)", "0 pts", f"{round(95 - KP['cobertura_primera_infancia_sectores'], 1)} pts (primera infancia)"),
    ("Caída del esquema 1→5 años", "cobertura TV 1 año − cobertura refuerzo 5 años", "≤ 0 pts", f"{KP['caida_esquema_1a5']} pts"),
    ("Localidades bajo la meta", "conteo de localidades con cobertura < 95 %", "0", f"{KP['localidades_bajo_meta_infancia']} de 20"),
    ("Dosis faltantes", "denominador × 0,95 − dosis aplicadas", "0", f"{KP['dosis_faltantes_meta_infancia']:,}".replace(",", ".")),
    ("Biológicos que cumplen", "biológicos con cobertura ≥ 95 % en el último año cerrado", "100 %", f"{KP['biologicos_cumplen_meta_ult']} de {KP['biologicos_total_ult']}"),
    ("Cobertura proyectada año en curso", "cobertura acumulada × 12 / meses reportados", "≥ 95 %", "ver tablero"),
    ("% registros que cumplen", "registros localidad-sector-biológico ≥ 95 %", "100 %", f"{KP['pct_registros_cumplen_meta']} %"),
], ["KPI", "Fórmula", "Meta", f"Valor actual"])

h("13. Desarrollo e implementación del programa")
p("El programa se entrega como una aplicación de escritorio para Windows, CoberturaVacunacion.exe, que no requiere instalar nada: "
  "el ejecutable incluye Python, las librerías y el motor de gráficas. Al abrirlo muestra su propia ventana, consulta la API, "
  "limpia y consolida los datos, calcula los KPI y presenta el tablero dentro de la misma ventana (usa WebView2, el motor web "
  "incluido en Windows 10 y 11). Solo necesita conexión a internet para traer los datos más recientes.")
p("Arquitectura: API Datos Abiertos Bogotá (fuente) → etl.py en Python (extracción, limpieza, transformación) → base_consolidada.xlsx "
  "y CSV (almacenamiento / modelo en estrella) → tablero en la ventana de CoberturaVacunacion.exe (herramienta BI) → "
  "Secretaría Distrital de Salud o alcaldías locales (usuario final). Se eligió Python + pandas por ser gratuito, reproducible "
  "y versionable en GitHub, lo que deja trazabilidad de los aportes de cada integrante. El mismo endpoint puede conectarse a "
  "Power BI (Obtener datos → Web).")
tabla([
    ("dist/CoberturaVacunacion.exe", "Aplicación de escritorio lista para usar (doble clic); no requiere instalación"),
    ("app.py", "Punto de entrada de la aplicación: abre la ventana, ejecuta el ETL y muestra el tablero"),
    ("etl.py", "Consulta la API con paginación, limpia, consolida, calcula KPI y genera el tablero"),
    ("dashboard_template.html", "Plantilla del tablero; el ETL inyecta los datos"),
    ("chart.umd.min.js", "Librería de gráficas Chart.js 4.4.1 incluida en el programa (no se descarga al ejecutar)"),
    ("test_etl.py", "Pruebas automáticas de las reglas de limpieza"),
    ("informe.py", "Genera las gráficas y este documento a partir de los resultados"),
    (".github/workflows/actualizar.yml", "Opcional: ejecuta el ETL a diario y publica el tablero en GitHub Pages"),
    ("requirements.txt", "Dependencias para desarrollo: pandas, openpyxl"),
], ["Archivo", "Función"])
p("Uso para el usuario final: doble clic en CoberturaVacunacion.exe. La primera vez Windows puede mostrar «Windows protegió su PC» "
  "porque el ejecutable no está firmado digitalmente; se continúa con «Más información» → «Ejecutar de todas formas». "
  "El programa crea junto al .exe la carpeta salidas con la base consolidada en Excel y los CSV.")
p("Uso para desarrollo:  pip install -r requirements.txt  →  python test_etl.py  →  python etl.py. "
  "El ejecutable se compila con PyInstaller a partir de app.py (comando documentado en el README).")

h("14. Dashboard o tablero de Inteligencia de Negocios")
p("El tablero se muestra dentro de la ventana de CoberturaVacunacion.exe y contiene: cuatro tarjetas KPI (cobertura de primera infancia, caída 1→5 años, localidades bajo "
  "la meta y dosis faltantes); la serie anual por biológico con la línea de meta; el avance del año en curso contra el ritmo "
  "necesario; el ranking de localidades; la cobertura por sector institucional y por grupo de biológico; un mapa de calor "
  "localidad × sector y la tabla de trazabilidad de la limpieza. Todos los gráficos muestran el detalle al pasar el cursor y "
  "el encabezado indica la fecha y hora de la última consulta a la API. Cada vez que se abre el programa el tablero se "
  "reconstruye con los datos vigentes. Además, el archivo salidas/dashboard.html queda como copia del último tablero generado.")
p("Enlace de descarga del programa (carpeta del proyecto): ______________________")

h("15. Resultados obtenidos")
viñetas([
    "Aplicación de escritorio (CoberturaVacunacion.exe) que funciona sin instalar nada y consume la API oficial en cada apertura; no depende de descargas manuales de datos.",
    f"Base consolidada con {LOG['sectores']['filas_finales']} registros de sectores y {LOG['mensual']['filas_finales']} registros mensuales limpios.",
    f"Ninguna de las 20 localidades alcanza la meta del 95 % en primera infancia; la más rezagada es {KP['localidad_menor_cobertura']} ({KP['localidad_menor_cobertura_valor']} %).",
    f"La cobertura cae {KP['caida_esquema_1a5']} puntos entre la triple viral de 1 año ({KP['tv_1anio_ult']} %) y el refuerzo de 5 años ({KP['tv_5anios_ult']} %).",
    f"Solo {KP['biologicos_cumplen_meta_ult']} de {KP['biologicos_total_ult']} biológicos trazadores cumplieron la meta en {ULT} (pentavalente y Tdap gestante).",
    f"Faltan cerca de {KP['dosis_faltantes_meta_infancia']:,} dosis de primera infancia para llevar a la meta a la población reportada por los sectores.".replace(",", "."),
    "ICBF e Integración Social tienen coberturas 12–20 puntos menores que los colegios.",
])

h("16. Conclusiones")
viñetas([
    "Bogotá recuperó las coberturas de las primeras dosis después de la caída de 2020–2022, pero no ha recuperado los refuerzos: "
    "el reto principal es completar el esquema, no iniciarlo.",
    "La brecha es generalizada (todas las localidades bajo la meta), aunque su magnitud cambia; esto permite priorizar por "
    "cobertura (Chapinero, Teusaquillo, Sumapaz) o por volumen de niños sin vacunar (Bosa, Kennedy, Suba).",
    "Los sectores con población más vulnerable (ICBF, Integración Social) presentan la menor cobertura.",
    "Los datos abiertos tienen problemas de calidad (formatos, totales erróneos, coberturas sobre 100 %); un proceso ETL "
    "documentado y automatizado es indispensable para confiar en los indicadores.",
    "Consumir la API en lugar de archivos descargados garantiza que el tablero refleje siempre la última publicación oficial.",
])

h("17. Recomendaciones")
viñetas([
    "Diseñar campañas de seguimiento a los refuerzos de 18 meses y 5 años (recordatorios por SMS, vacunación en jardines y "
    "colegios en transición) en lugar de concentrar el esfuerzo en las dosis del primer año.",
    "Priorizar brigadas en Bosa, Kennedy y Suba por número de niños sin vacunar, y en Chapinero, Teusaquillo y Sumapaz por porcentaje.",
    "Articular con ICBF e Integración Social jornadas de vacunación en sus unidades de servicio.",
    "Migrar el carné físico a un registro digital nominal para reducir el subregistro y mejorar los denominadores.",
    "Solicitar a la SDS publicar los datos por sectores con serie histórica (hoy solo hay un corte) y corregir las filas de totales.",
    "Mantener el flujo automático y revisar mensualmente el KPI de cobertura proyectada del año en curso.",
])

h("18. Evidencias del funcionamiento del programa")
p("La aplicación se probó copiando CoberturaVacunacion.exe a una carpeta vacía (el ejecutable trae su propio Python y no usa el del equipo): abrió su "
  "propia ventana, consultó la API, generó la carpeta salidas (base_consolidada.xlsx, CSV, kpis.json) y mostró el tablero. "
  "Las pruebas automáticas de limpieza (test_etl.py) se ejecutaron sin errores.")
figura(EVI / "app_exe.png", 6, "Aplicación CoberturaVacunacion.exe ejecutándose en su propia ventana", ancho=15)
p("Ejecución del ETL desde la terminal (modo desarrollo):")
codigo = doc.add_paragraph()
r = codigo.add_run("$ python test_etl.py\nOK\n$ python etl.py\nConsultando API de Datos Abiertos Bogotá...\n" + json.dumps(KP, ensure_ascii=False, indent=1))
r.font.name, r.font.size = "Consolas", Pt(8)
for n, (f, t) in enumerate([("dashboard_1.jpg", "Tablero: KPI, serie anual y avance del año"),
                            ("dashboard_2.jpg", "Tablero: localidades, sectores y mapa de calor"),
                            ("dashboard_3.jpg", "Tablero: mapa de calor y trazabilidad de la limpieza")], start=7):
    if (EVI / f).exists():
        figura(EVI / f, n, t, ancho=15)

h("19. Video de presentación del proyecto (máximo 6 minutos)")
p("Enlace del video: ______________________")
p("Guion sugerido:")
tabla([
    ("0:00–0:45", "Problema y pregunta de investigación", "Integrante 1"),
    ("0:45–1:45", "Fuente de datos, API y población", "Integrante 2"),
    ("1:45–3:00", "Demostración del programa: ejecución de etl.py y limpieza", "Integrante 3"),
    ("3:00–4:45", "Recorrido por el tablero y KPI", "Integrante 4"),
    ("4:45–6:00", "Resultados, conclusiones y recomendaciones", "Todos"),
], ["Tiempo", "Contenido", "Responsable"])

h("20. Referencias bibliográficas")
refs = [
    "CKAN. (s. f.). DataStore extension: API reference. https://docs.ckan.org/en/latest/maintaining/datastore.html",
    "Kimball, R., & Ross, M. (2013). The data warehouse toolkit: The definitive guide to dimensional modeling (3.ª ed.). Wiley.",
    "McKinney, W. (2022). Python for data analysis (3.ª ed.). O'Reilly Media.",
    "Ministerio de Salud y Protección Social. (s. f.). Programa Ampliado de Inmunizaciones (PAI). "
    "https://www.minsalud.gov.co/salud/publica/Vacunacion/Paginas/pai.aspx",
    "Observatorio de Salud de Bogotá. (2025). Cobertura de vacunación por sectores [Indicador]. Secretaría Distrital de Salud. "
    "https://saludata.saludcapital.gov.co/osb/indicadores/cobertura-vacunacion-sectores/",
    "Parmenter, D. (2015). Key performance indicators: Developing, implementing, and using winning KPIs (3.ª ed.). Wiley.",
    "Secretaría Distrital de Salud. (2025). Seguimiento cobertura vacunación – sectores [Conjunto de datos]. Datos Abiertos Bogotá. "
    "https://datosabiertos.bogota.gov.co/dataset/seguimiento-cobertura-vacunacion-sectores",
    "Secretaría Distrital de Salud. (2026). Cobertura vacunación en Bogotá D.C. [Conjunto de datos]. Datos Abiertos Bogotá. "
    "https://datosabiertos.bogota.gov.co/dataset/coberturas-de-vacunacion",
    "World Health Organization. (2020). Immunization agenda 2030: A global strategy to leave no one behind. "
    "https://www.who.int/publications/m/item/immunization-agenda-2030-a-global-strategy-to-leave-no-one-behind",
]
for ref in refs:
    par = doc.add_paragraph(ref)
    par.paragraph_format.left_indent = Cm(1.27)
    par.paragraph_format.first_line_indent = Cm(-1.27)

h("21. Enlace de trabajo colaborativo")
p("Carpeta compartida (Google Drive / OneDrive): ______________________")
p("Repositorio del código: https://github.com/julianpenuelaalfonso-fullstack/Proyecto_vacunacion")
p("Nota: el repositorio de las entregas anteriores quedó a cargo de un integrante que se retiró del proyecto; "
  "este repositorio continúa el trabajo del grupo a partir de noviembre de 2026.")
p("La carpeta contiene este documento, el programa CoberturaVacunacion.exe, la base consolidada, el código, las gráficas y las evidencias. El historial de versiones "
  "de Drive/OneDrive y los commits de GitHub permiten verificar el aporte de cada integrante.")

doc.save(BASE / "Proyecto_Final_Cobertura_Vacunacion.docx")
print("Informe generado")
