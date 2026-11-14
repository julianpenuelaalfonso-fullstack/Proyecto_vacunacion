# Cobertura de vacunación · Bogotá D.C. (Inteligencia de Negocios)

Programa ETL + KPI + dashboard que consulta **en vivo** la API CKAN del Portal de Datos Abiertos de Bogotá
(Secretaría Distrital de Salud / SaluData). Cada ejecución trae los datos más recientes.

| Fuente | Recurso API |
|---|---|
| Seguimiento cobertura vacunación – sectores | `e519cce2-9951-41de-afbc-005d1e1d24dd` |
| Cobertura vacunación en Bogotá D.C. (mensual 2019–hoy) | `1910589c-2836-41d3-aba4-00488bb5e5f3` |

Ejemplo de consulta directa:
`https://datosabiertos.bogota.gov.co/api/3/action/datastore_search?resource_id=e519cce2-9951-41de-afbc-005d1e1d24dd&limit=5`

## Integrantes y aportes
Universidad Manuela Beltrán · Inteligencia de Negocios · Docente: Juan José Osorio Tabares

| Integrante | GitHub | Aportes |
|---|---|---|
| Julián Andrés Peñuela Alfonso | [@julianpenuelaalfonso-fullstack](https://github.com/julianpenuelaalfonso-fullstack) | Programa ETL y consumo de la API, dashboard, aplicación de escritorio (.exe), repositorio |
| Valery Michell Herrera Roca | [@Codeforgeettttt](https://github.com/Codeforgeettttt) | Redacción y reescritura del informe, pruebas del programa, entregas anteriores (guías y póster) |
| Daniel Felipe Rojas González | [@Dani2026403](https://github.com/Dani2026403) | Redacción y reescritura del informe, pruebas del programa, entregas anteriores (guías y póster) |

El repositorio de las entregas anteriores quedó a cargo de un integrante que se retiró del proyecto; este repositorio
continúa el trabajo del grupo desde noviembre de 2026. Los commits en los que participó el equipo incluyen a los
integrantes como coautores (`Co-authored-by`).

## Uso
```
pip install -r requirements.txt
python test_etl.py      # pruebas de las reglas de limpieza
python etl.py           # descarga, limpia, calcula KPI y genera salidas/
python informe.py       # gráficas (graficas/) y documento Word con los 21 puntos
```
Salidas en `salidas/`: `base_consolidada.xlsx` (hechos, dimensiones, KPI, log de limpieza), CSV crudos y limpios,
`kpis.json` y `dashboard.html`.

## Actualización automática
`.github/workflows/actualizar.yml` ejecuta el ETL todos los días y publica el dashboard en GitHub Pages
(activar en Settings → Pages → Source: GitHub Actions).

## Power BI (opcional)
Obtener datos → Web → pegar la URL de la API con `&limit=5000` → expandir `result.records`.
Al pulsar *Actualizar* en Power BI se traen los datos nuevos.

## Ejecutable para Windows (sin instalar nada)
`dist/CoberturaVacunacion.exe` es una aplicación de escritorio: incluye Python y todas las librerías y muestra el
dashboard en su propia ventana (motor WebView2, incluido en Windows 10/11). Al abrirlo consulta la API
(requiere internet) y guarda el Excel y los CSV en `salidas/`, junto al .exe.

Para recompilarlo (`app.py` es el punto de entrada):
```
pip install pyinstaller pywebview==5.3.2
pyinstaller --onefile --windowed --name CoberturaVacunacion --add-data "dashboard_template.html;." --add-data "chart.umd.min.js;." app.py
```
