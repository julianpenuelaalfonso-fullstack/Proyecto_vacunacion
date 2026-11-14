"""ETL + KPIs + dashboard: cobertura de vacunación en Bogotá D.C.

Consulta en vivo la API CKAN del Portal de Datos Abiertos de Bogotá (Secretaría
Distrital de Salud / Observatorio de Salud - SaluData), limpia los datos, genera la
base consolidada (Excel + CSV), calcula los KPI y construye dashboard.html.

Uso:  python etl.py          (cada ejecución trae los datos más recientes)
"""
import json
import sys
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd

API = "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search"
RES_SECTORES = "e519cce2-9951-41de-afbc-005d1e1d24dd"  # Seguimiento cobertura vacunación - sectores
RES_MENSUAL = "1910589c-2836-41d3-aba4-00488bb5e5f3"   # Cobertura vacunación en Bogotá D.C. (mensual)
META = 95.0  # meta PAI - Ministerio de Salud
EXE = getattr(sys, "frozen", False)  # True cuando corre como .exe (PyInstaller)
RECURSOS = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # plantilla y Chart.js empaquetados
OUT = (Path(sys.executable).parent if EXE else Path(__file__).parent) / "salidas"

ZONAS = {  # agrupación geográfica usada en DIM_LOCALIDAD
    "Usaquén": "Norte", "Chapinero": "Norte", "Suba": "Norte", "Barrios Unidos": "Norte", "Teusaquillo": "Norte",
    "Santa Fe": "Centro", "Los Mártires": "Centro", "La Candelaria": "Centro", "Antonio Nariño": "Centro",
    "Puente Aranda": "Centro",
    "Usme": "Sur", "Tunjuelito": "Sur", "San Cristóbal": "Sur", "Rafael Uribe Uribe": "Sur",
    "Ciudad Bolívar": "Sur", "Sumapaz": "Rural",
    "Bosa": "Occidente", "Kennedy": "Occidente", "Fontibón": "Occidente", "Engativá": "Occidente",
}


def consultar_api(resource_id):
    """Trae todos los registros de un recurso CKAN, paginando."""
    filas, offset = [], 0
    while True:
        url = f"{API}?resource_id={resource_id}&limit=1000&offset={offset}"
        with urllib.request.urlopen(url, timeout=60) as r:
            res = json.load(r)
        if not res.get("success"):
            raise RuntimeError(f"API respondió error para {resource_id}: {res.get('error')}")
        lote = res["result"]["records"]
        filas += lote
        offset += len(lote)
        if not lote or offset >= res["result"]["total"]:
            return pd.DataFrame(filas).drop(columns="_id")


def num_es(valor):
    """'98.914' -> 98914.0 ; ' 7,8 ' -> 7.8 ; None/'' -> NaN (formato numérico colombiano)."""
    if valor is None or str(valor).strip() == "":
        return float("nan")
    return float(str(valor).strip().replace(".", "").replace(",", "."))


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def grupo_biologico(b):
    b = sin_tildes(b).lower()
    if "covid" in b:
        return "COVID-19"
    if "papiloma" in b:
        return "VPH (9-17 años)"
    if any(k in b for k in ("influenza", "neumococo")):
        return "Adulto mayor"
    if any(k in b for k in ("pentavalente", "triple viral", "difteria")):
        return "Primera infancia"
    return "Escolar / otros"


def limpiar_sectores(df):
    log = {"filas_originales": len(df)}
    df = df.rename(columns=str.lower).copy()
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["fecha_reporte"] = pd.to_datetime(df["fecha_reporte"], format="%d/%m/%Y")
    for c in ("dosis_aplicada", "denominador", "cobertura"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # La API publica la cobertura x10 sin separador decimal (708 = 70,8 %).
    df["cobertura_reportada"] = df.pop("cobertura") / 10
    df["cobertura_recalculada"] = (df["dosis_aplicada"] / df["denominador"].where(df["denominador"] > 0) * 100).round(1)
    df["flag_inconsistencia"] = (df["cobertura_reportada"] - df["cobertura_recalculada"]).abs() > 0.1
    df["flag_sobre_100"] = df["cobertura_recalculada"] > 100
    log["filas_cobertura_inconsistente"] = int(df["flag_inconsistencia"].sum())
    log["filas_sobre_100"] = int(df["flag_sobre_100"].sum())

    loc = df.pop("nombre_localidad").str.extract(r"^(\d+)\s*-\s*(.+)$")
    df["cod_localidad"] = pd.to_numeric(loc[0], errors="coerce")
    df["localidad"] = loc[1]
    validas = df["localidad"].isin(ZONAS)
    log["filas_localidad_no_valida"] = int((~validas).sum())  # 'NO ACTUALIZADO' y 'Localidad Desconocida'
    df = df[validas].copy()
    df["zona"] = df["localidad"].map(ZONAS)

    df["institucion"] = df["institucion"].replace({"INTERACIÓN VEJÉZ": "INTEGRACIÓN VEJEZ"}).str.title()
    df = df.rename(columns={"biologico_edad": "biologico"})
    df["grupo_biologico"] = df["biologico"].map(grupo_biologico)
    df["cumple_meta"] = df["cobertura_recalculada"] >= META
    df["brecha_meta"] = (META - df["cobertura_recalculada"]).clip(lower=0).round(1)

    antes = len(df)
    df = df.drop_duplicates(["fecha_reporte", "localidad", "biologico", "institucion"])
    log["duplicados_eliminados"] = antes - len(df)
    log["filas_finales"] = len(df)
    cols = ["fecha_reporte", "cod_localidad", "localidad", "zona", "institucion", "grupo_biologico", "biologico",
            "dosis_aplicada", "denominador", "cobertura_reportada", "cobertura_recalculada", "brecha_meta",
            "cumple_meta", "flag_inconsistencia", "flag_sobre_100"]
    return df[cols].sort_values(["cod_localidad", "institucion", "biologico"]), log


def limpiar_mensual(df):
    log = {"filas_originales": len(df)}
    df = df.rename(columns={"Biologico": "biologico", "Ano": "anio", "Orden mes": "mes_num", "Mes": "mes",
                            "Meta": "poblacion_meta", "Vacunados": "vacunados_mes"})
    df["biologico"] = df["biologico"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["anio"] = df["anio"].astype(int)
    df["mes_num"] = df["mes_num"].astype(int)
    totales = df["mes_num"] == 13
    log["filas_total_eliminadas"] = int(totales.sum())  # la fila 'Total' se recalcula, en 2026 viene errada
    df = df[~totales].copy()
    for c in ("poblacion_meta", "vacunados_mes", "Cobertura", "Column7"):
        df[c] = df[c].map(num_es)
    log["meses_sin_reporte"] = int(df["vacunados_mes"].isna().sum())
    df = df.drop(columns=["Column7", "Cobertura"])  # acumulado y % se recalculan a partir de los datos base
    df = df.sort_values(["biologico", "anio", "mes_num"])
    df["reportado"] = df["vacunados_mes"].notna()
    df["vacunados_acum"] = df.groupby(["biologico", "anio"])["vacunados_mes"].cumsum()
    df["cobertura_acum"] = (df["vacunados_acum"] / df["poblacion_meta"] * 100).round(1)
    log["filas_finales"] = len(df)
    return df, log


def anual(mensual):
    g = mensual[mensual["reportado"]].groupby(["biologico", "anio"])
    a = g.agg(poblacion_meta=("poblacion_meta", "max"), vacunados=("vacunados_mes", "sum"),
              meses_reportados=("mes_num", "count")).reset_index()
    a["cobertura"] = (a["vacunados"] / a["poblacion_meta"] * 100).round(1)
    a["anio_completo"] = a["meses_reportados"] == 12
    # Para el año en curso se proyecta a 12 meses al ritmo observado.
    a["cobertura_proyectada"] = (a["cobertura"] * 12 / a["meses_reportados"]).round(1)
    a["brecha_meta"] = (META - a["cobertura"]).clip(lower=0).round(1)
    return a


def cobertura(df, por):
    g = df.groupby(por)[["dosis_aplicada", "denominador"]].sum().reset_index()
    g["cobertura"] = (g["dosis_aplicada"] / g["denominador"] * 100).round(1)
    return g


def calcular_kpis(sec, anu):
    infancia = sec[sec["grupo_biologico"] == "Primera infancia"]
    por_loc = cobertura(infancia, ["localidad", "zona"]).sort_values("cobertura")
    cerrados = anu[anu["anio_completo"]]
    ult = cerrados["anio"].max()
    tv1 = cerrados[(cerrados["biologico"] == "Triple viral 1 año") & (cerrados["anio"] == ult)]["cobertura"].iloc[0]
    tv5 = cerrados[(cerrados["biologico"].str.startswith("Triple viral R1 o DPT")) & (cerrados["anio"] == ult)]["cobertura"].iloc[0]
    validos = sec["denominador"] > 0
    return {
        "fecha_corte_sectores": sec["fecha_reporte"].max().strftime("%Y-%m-%d"),
        "ultimo_anio_cerrado": int(ult),
        "cobertura_global_sectores": round(sec["dosis_aplicada"].sum() / sec["denominador"].sum() * 100, 1),
        "cobertura_primera_infancia_sectores": round(infancia["dosis_aplicada"].sum() / infancia["denominador"].sum() * 100, 1),
        "pct_registros_cumplen_meta": round(sec.loc[validos, "cumple_meta"].mean() * 100, 1),
        "localidades_bajo_meta_infancia": int((por_loc["cobertura"] < META).sum()),
        "localidad_menor_cobertura": por_loc.iloc[0]["localidad"],
        "localidad_menor_cobertura_valor": float(por_loc.iloc[0]["cobertura"]),
        "tv_1anio_ult": float(tv1),
        "tv_5anios_ult": float(tv5),
        "caida_esquema_1a5": round(float(tv1 - tv5), 1),
        "biologicos_cumplen_meta_ult": int((cerrados[cerrados["anio"] == ult]["cobertura"] >= META).sum()),
        "biologicos_total_ult": int((cerrados["anio"] == ult).sum()),
        "dosis_faltantes_meta_infancia": int(max(0, (infancia["denominador"].sum() * META / 100) - infancia["dosis_aplicada"].sum())),
    }


def construir_dashboard(sec, anu, mens, kpis, logs):
    anio_actual = int(anu["anio"].max())
    datos = {
        "kpis": kpis,
        "meta": META,
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "logs": logs,
        "anual": anu.to_dict("records"),
        "mensual_actual": mens[mens["anio"] == anio_actual][["biologico", "mes_num", "cobertura_acum"]].dropna().to_dict("records"),
        "anio_actual": anio_actual,
        "loc_infancia": cobertura(sec[sec["grupo_biologico"] == "Primera infancia"], ["localidad", "zona"])
            .sort_values("cobertura").to_dict("records"),
        "institucion": cobertura(sec, ["institucion"]).sort_values("cobertura").to_dict("records"),
        "grupo": cobertura(sec, ["grupo_biologico"]).sort_values("cobertura").to_dict("records"),
        "zona": cobertura(sec, ["zona"]).sort_values("cobertura").to_dict("records"),
        "heat": cobertura(sec, ["localidad", "institucion"]).to_dict("records"),
    }
    plantilla = (RECURSOS / "dashboard_template.html").read_text(encoding="utf-8")
    html = (plantilla.replace("/*__CHARTJS__*/", (RECURSOS / "chart.umd.min.js").read_text(encoding="utf-8"))
            .replace("/*__DATOS__*/null", json.dumps(datos, ensure_ascii=False, default=str)))
    (OUT / "dashboard.html").write_text(html, encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    print("Consultando API de Datos Abiertos Bogotá...")
    raw_sec, raw_men = consultar_api(RES_SECTORES), consultar_api(RES_MENSUAL)
    raw_sec.to_csv(OUT / "crudo_sectores.csv", index=False, encoding="utf-8-sig")
    raw_men.to_csv(OUT / "crudo_mensual.csv", index=False, encoding="utf-8-sig")

    sec, log_sec = limpiar_sectores(raw_sec)
    mens, log_men = limpiar_mensual(raw_men)
    anu = anual(mens)
    kpis = calcular_kpis(sec, anu)
    logs = {"sectores": log_sec, "mensual": log_men}

    dim_loc = pd.DataFrame([{"localidad": l, "zona": z} for l, z in ZONAS.items()])
    with pd.ExcelWriter(OUT / "base_consolidada.xlsx") as xw:
        sec.to_excel(xw, sheet_name="HECHOS_SECTORES", index=False)
        mens.to_excel(xw, sheet_name="HECHOS_MENSUAL", index=False)
        anu.to_excel(xw, sheet_name="COBERTURA_ANUAL", index=False)
        dim_loc.to_excel(xw, sheet_name="DIM_LOCALIDAD", index=False)
        sec[["grupo_biologico", "biologico"]].drop_duplicates().to_excel(xw, sheet_name="DIM_BIOLOGICO", index=False)
        pd.DataFrame(kpis.items(), columns=["kpi", "valor"]).to_excel(xw, sheet_name="KPI", index=False)
        pd.DataFrame([(f, k, v) for f, d in logs.items() for k, v in d.items()],
                     columns=["fuente", "paso", "valor"]).to_excel(xw, sheet_name="LOG_LIMPIEZA", index=False)
    sec.to_csv(OUT / "hechos_sectores.csv", index=False, encoding="utf-8-sig")
    anu.to_csv(OUT / "cobertura_anual.csv", index=False, encoding="utf-8-sig")
    (OUT / "kpis.json").write_text(json.dumps({"kpis": kpis, "limpieza": logs}, ensure_ascii=False, indent=2), encoding="utf-8")
    construir_dashboard(sec, anu, mens, kpis, logs)
    print(json.dumps(kpis, ensure_ascii=False, indent=2))
    print(f"Listo. Archivos en {OUT}")


if __name__ == "__main__":
    main()
