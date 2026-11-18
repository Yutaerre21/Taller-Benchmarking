"""Consolida únicamente ejecuciones terminadas con métricas medidas."""
import json
import csv
import statistics
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rows = []
resources = []
csv_rows = []
for file in sorted((root / 'results').glob('*/summary.json'), key=lambda p: p.stat().st_mtime):
    s = json.loads(file.read_text())
    folder = file.parent
    csv_rows.append({'execution': folder.name, **s})
    rows.append(f"| {folder.name} | {s['users']} | {s['requests']} | {s['average_ms']} | {s['p95_ms']} | {s['throughput_rps']} | {s['error_pct']} |")
    by_container = {}
    stats = folder / 'docker-stats.jsonl'
    if stats.exists():
        for line in stats.read_text(encoding='utf-8-sig').splitlines():
            sample = json.loads(line)
            by_container.setdefault(sample['Name'], []).append(sample)
    for name, samples in by_container.items():
        cpu = [float(x['CPUPerc'].rstrip('%')) for x in samples]
        def mib(value):
            val = value.split('/')[0].strip()
            for unit, scale in [('GiB',1024),('MiB',1),('KiB',1/1024),('B',1/1048576)]:
                if val.endswith(unit):
                    return float(val[:-len(unit)])*scale
            raise ValueError(val)
        ram = [mib(x['MemUsage']) for x in samples]
        resources.append(f"| {folder.name} | {name} | {len(samples)} | {statistics.mean(cpu):.2f} | {max(cpu):.2f} | {statistics.mean(ram):.2f} | {max(ram):.2f} |")

text = '''# Informe individual — Go + PostgreSQL

## Implementación

POST `/api/orders`, HTTP 201, cálculo exacto en centavos, `itemsCount` como suma de unidades, identificador aleatorio de 128 bits, fecha UTC y escritura transaccional de pedido y líneas. Tablas del PDF sin cambios. Go 1.24, net/http y pgx 5.7.6; PostgreSQL 16; pool de 20 conexiones; JMeter 5.6.3 con Java 21. Docker Desktop sobre Windows.

## Metodología

Mediciones reales realizadas en este computador el 17 de noviembre de 2026 (America/Bogota). Hardware: AMD Ryzen 7 5700X, 8 núcleos / 16 procesadores lógicos, aproximadamente 32 GiB de RAM física y 15.58 GiB disponibles para Docker. El nombre de cada carpeta registra la hora local de inicio del lote. Se usa el mismo JSON del PDF, sin pausas entre solicitudes por usuario y con conexiones HTTP persistentes. Cada respuesta se valida por HTTP 201, total 26, conteo 3, identificador y fecha presentes.

Los escenarios principales y alternativos duran 60 segundos, incluyendo rampa de 10 segundos. Las pruebas de estrés, si aparecen en el registro de ejecución, también declaran su duración allí. No hay calentamiento separado ni repeticiones estadísticas. Se conserva la base entre escenarios. API, DB y generador comparten hardware. Consultar `results/hardware.json`, `memory.json` y `docker-info.json` para el entorno.

El PDF pide 10/50/100 para la entrega individual y 20/70/150 en la configuración; se miden ambos, en ese orden. Los lotes adicionales corresponden al barrido de estrés, de 20 en 20. El umbral elegido para estrés es P95 >= 500 ms o errores >= 1%. También se considera indicador de saturación que dos incrementos seguidos mejoren throughput <=5% mientras P95 crece >=25%. Son criterios operativos de este proyecto, no requisitos del PDF ni capacidad máxima absoluta.

## Métricas medidas

Promedio y P95 en milisegundos; throughput en solicitudes/segundo. P95 calculado con rango más cercano sobre todas las muestras, incluida la rampa. Errores incluyen fallos de las aserciones. Cada carpeta contiene muestras, dashboard HTML, log y resumen CSV/JSON.

| Ejecución | Usuarios | Solicitudes | Avg ms | P95 ms | req/s | Error % |
|---|---:|---:|---:|---:|---:|---:|
''' + '\n'.join(rows) + '''

## Consumo de contenedores

Promedio y máximo de las muestras de `docker stats`, aproximadamente cada 4 segundos (incluye el tiempo de consulta); no son máximos instantáneos continuos. CPU puede superar 100% al utilizar varios núcleos. No incluye el consumo del generador JMeter.

| Ejecución | Contenedor | Muestras | CPU media % | CPU máx % | RAM media MiB | RAM máx MiB |
|---|---|---:|---:|---:|---:|---:|---:|
''' + '\n'.join(resources) + '''

## Evidencias y entrega

Se guardaron muestras crudas JTL, dashboards HTML, métricas, lista de contenedores y consumo de recursos. Las capturas de Summary Report, Aggregate Report, JMeter durante carga, docker ps y htop deben añadirse siguiendo README.md; no se presentan estos archivos de texto como pantallazos. En WSL solamente se encontró la distribución interna docker-desktop, sin una distribución de usuario preparada para htop; esa evidencia está pendiente.

Los tests unitarios verifican totales, precisión decimal, límites de NUMERIC y entradas inválidas. También se ejecutó go vet y se comprobó que el pedido del ejemplo produce una cabecera de 26.00, 3 unidades y 2 líneas en PostgreSQL.

## Interpretación y comparación grupal

En las seis pruebas de 60 segundos no se observaron errores. En la tabla individual, 10/50/100 usuarios produjeron P95 de 17/45/51 ms. El promedio de 100 usuarios fue menor que el de 50 y el throughput aumentó: la relación no fue monotónica. Esto exige repetir los escenarios antes de generalizar; no se aisló la causa de esa variación. La carga alternativa de 150 usuarios registró P95 de 88 ms sin errores, por debajo del umbral absoluto de estrés elegido.

Estas mediciones describen este entorno, configuración y duración. La latencia de una prueba corta no demuestra comportamiento sostenido de producción. Para atribuir límites a CPU, disco, pool o GC se requieren mediciones adicionales; un aumento de latencia por sí solo no identifica la causa.

No se puede determinar el stack ganador, ni el más estable, ni recomendar uno para producción comparativamente sin los resultados equivalentes de Flask, NestJS y Spring Boot. El grupo debe incorporar las filas de Go y comparar cada métrica con la misma carga y metodología. Las cifras ilustrativas del PDF no se usaron como resultados.
'''
stress_file = root / 'results/stress-result.json'
if stress_file.exists():
    stress = json.loads(stress_file.read_text(encoding='utf-8-sig'))
    text += f"\n## Resultado del barrido de estrés\n\nSe aumentó de 20 en 20 hasta {stress['users']} usuarios, con {stress['duration_seconds']} segundos por nivel y rampa de {stress['ramp_seconds']} segundos incluida. Resultado: {stress['criterion']}. Este barrido es exploratorio; se recomienda repetir y prolongar las mediciones para confirmar el comportamiento.\n"
    text += "\nEn el barrido inicial, de 40 a 60 y a 80 usuarios, el throughput pasó de 4172.58 a 3728.91 y a 2280.49 req/s, mientras P95 pasó de 12 a 31 y a 78 ms. No se alcanzaron 500 ms de P95 ni se observaron errores. Como la prueba previa de 150 usuarios obtuvo mejores resultados, no se puede afirmar que 80 sea la capacidad máxima: hay variabilidad entre ejecuciones y no se aisló su causa.\n"
(root / 'INFORME_GO.md').write_text(text, encoding='utf-8')
if csv_rows:
    with (root / 'RESULTADOS_GO.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)
print(f'Informe generado con {len(rows)} escenarios medidos.')
