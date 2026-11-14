"""Pruebas de las reglas de limpieza (sin red). Ejecutar: python test_etl.py"""
import math

import pandas as pd

from etl import anual, grupo_biologico, limpiar_mensual, limpiar_sectores, num_es

assert num_es(" 98.914 ") == 98914 and num_es(" 7,8 ") == 7.8 and math.isnan(num_es(None))
assert grupo_biologico("Triple viral (1 año de edad)") == "Primera infancia"
assert grupo_biologico("Virus de Papiloma Humano primera dosis (de 9 años de edad) - Mujeres") == "VPH (9-17 años)"

sec, log = limpiar_sectores(pd.DataFrame([
    {"FECHA_REPORTE": "26/08/2025", "NOMBRE_LOCALIDAD": "05 - Usme", "BIOLOGICO_EDAD": "Triple viral (1 año de edad)",
     "INSTITUCION": "ICBF", "DOSIS_APLICADA": "17", "DENOMINADOR": "24", "COBERTURA": "708"},
    {"FECHA_REPORTE": "26/08/2025", "NOMBRE_LOCALIDAD": "NO ACTUALIZADO", "BIOLOGICO_EDAD": "Influenza",
     "INSTITUCION": "INTERACIÓN VEJÉZ", "DOSIS_APLICADA": "1", "DENOMINADOR": "1", "COBERTURA": "1000"},
]))
r = sec.iloc[0]
assert len(sec) == 1 and log["filas_localidad_no_valida"] == 1
assert r.cobertura_reportada == 70.8 and r.cobertura_recalculada == 70.8 and r.zona == "Sur" and not r.cumple_meta

raw = [{"Biologico": " Penta <1año ", "Ano": "2025", "Orden mes": str(m), "Mes": "x", "Meta": " 1.200 ",
        "Vacunados": " 100 ", "Column7": None, "Cobertura": "0"} for m in range(1, 13)]
raw.append({**raw[0], "Orden mes": "13", "Vacunados": "999"})  # fila Total que debe descartarse
a = anual(limpiar_mensual(pd.DataFrame(raw))[0]).iloc[0]
assert a.vacunados == 1200 and a.cobertura == 100 and a.anio_completo
print("OK")
