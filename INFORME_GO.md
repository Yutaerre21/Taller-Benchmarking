# Informe individual — Go + PostgreSQL

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
| 20261117-231114-10-users | 10 | 76799 | 7.07 | 17 | 1281.31 | 0.0 |
| 20261117-231114-50-users | 50 | 102890 | 26.46 | 45 | 1716.09 | 0.0 |
| 20261117-231114-100-users | 100 | 234210 | 23.4 | 51 | 3844.87 | 0.0 |
| 20261117-231114-20-users | 20 | 165605 | 6.54 | 13 | 2761.83 | 0.0 |
| 20261117-231114-70-users | 70 | 220949 | 17.26 | 40 | 3685.37 | 0.0 |
| 20261117-231114-150-users | 150 | 241125 | 34.06 | 88 | 4019.89 | 0.0 |
| 20261117-231814-20-users | 20 | 92927 | 5.8 | 7 | 3099.12 | 0.0 |
| 20261117-231851-40-users | 40 | 124852 | 8.6 | 12 | 4172.58 | 0.0 |
| 20261117-231928-60-users | 60 | 111610 | 14.55 | 31 | 3728.91 | 0.0 |
| 20261117-232004-80-users | 80 | 68296 | 31.89 | 78 | 2280.49 | 0.0 |

## Consumo de contenedores

Promedio y máximo de las muestras de `docker stats`, aproximadamente cada 4 segundos (incluye el tiempo de consulta); no son máximos instantáneos continuos. CPU puede superar 100% al utilizar varios núcleos. No incluye el consumo del generador JMeter.

| Ejecución | Contenedor | Muestras | CPU media % | CPU máx % | RAM media MiB | RAM máx MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| 20261117-231114-10-users | tallerbench-api-1 | 15 | 124.99 | 202.99 | 9.08 | 10.23 |
| 20261117-231114-10-users | tallerbench-db-1 | 15 | 70.44 | 127.33 | 96.40 | 111.70 |
| 20261117-231114-50-users | tallerbench-api-1 | 15 | 168.26 | 253.13 | 12.38 | 13.40 |
| 20261117-231114-50-users | tallerbench-db-1 | 15 | 112.21 | 166.45 | 151.65 | 174.90 |
| 20261117-231114-100-users | tallerbench-api-1 | 16 | 268.76 | 444.05 | 15.13 | 16.46 |
| 20261117-231114-100-users | tallerbench-db-1 | 16 | 214.41 | 318.21 | 218.40 | 240.70 |
| 20261117-231114-20-users | tallerbench-api-1 | 15 | 245.11 | 403.11 | 11.50 | 15.33 |
| 20261117-231114-20-users | tallerbench-db-1 | 15 | 145.26 | 230.87 | 243.50 | 246.40 |
| 20261117-231114-70-users | tallerbench-api-1 | 15 | 273.11 | 443.48 | 13.91 | 15.43 |
| 20261117-231114-70-users | tallerbench-db-1 | 15 | 204.00 | 311.45 | 285.85 | 300.40 |
| 20261117-231114-150-users | tallerbench-api-1 | 15 | 279.47 | 445.15 | 18.03 | 20.01 |
| 20261117-231114-150-users | tallerbench-db-1 | 15 | 202.77 | 331.73 | 350.89 | 359.40 |
| 20261117-231814-20-users | tallerbench-api-1 | 8 | 238.75 | 421.13 | 12.75 | 18.50 |
| 20261117-231814-20-users | tallerbench-db-1 | 8 | 139.43 | 224.53 | 424.61 | 426.60 |
| 20261117-231851-40-users | tallerbench-api-1 | 8 | 307.99 | 457.71 | 12.97 | 14.03 |
| 20261117-231851-40-users | tallerbench-db-1 | 8 | 199.56 | 313.55 | 461.45 | 483.90 |
| 20261117-231928-60-users | tallerbench-api-1 | 8 | 237.32 | 439.89 | 13.91 | 14.29 |
| 20261117-231928-60-users | tallerbench-db-1 | 8 | 188.87 | 333.84 | 486.36 | 489.80 |
| 20261117-232004-80-users | tallerbench-api-1 | 8 | 187.54 | 302.38 | 14.71 | 16.20 |
| 20261117-232004-80-users | tallerbench-db-1 | 8 | 131.71 | 213.56 | 585.69 | 596.00 |

## Evidencias y entrega

Se guardaron muestras crudas JTL, dashboards HTML, métricas, lista de contenedores y consumo de recursos. Las capturas de Summary Report, Aggregate Report, JMeter durante carga, docker ps y htop deben añadirse siguiendo README.md; no se presentan estos archivos de texto como pantallazos. En WSL solamente se encontró la distribución interna docker-desktop, sin una distribución de usuario preparada para htop; esa evidencia está pendiente.

Los tests unitarios verifican totales, precisión decimal, límites de NUMERIC y entradas inválidas. También se ejecutó go vet y se comprobó que el pedido del ejemplo produce una cabecera de 26.00, 3 unidades y 2 líneas en PostgreSQL.

## Interpretación y comparación grupal

En las seis pruebas de 60 segundos no se observaron errores. En la tabla individual, 10/50/100 usuarios produjeron P95 de 17/45/51 ms. El promedio de 100 usuarios fue menor que el de 50 y el throughput aumentó: la relación no fue monotónica. Esto exige repetir los escenarios antes de generalizar; no se aisló la causa de esa variación. La carga alternativa de 150 usuarios registró P95 de 88 ms sin errores, por debajo del umbral absoluto de estrés elegido.

Estas mediciones describen este entorno, configuración y duración. La latencia de una prueba corta no demuestra comportamiento sostenido de producción. Para atribuir límites a CPU, disco, pool o GC se requieren mediciones adicionales; un aumento de latencia por sí solo no identifica la causa.

No se puede determinar el stack ganador, ni el más estable, ni recomendar uno para producción comparativamente sin los resultados equivalentes de Flask, NestJS y Spring Boot. El grupo debe incorporar las filas de Go y comparar cada métrica con la misma carga y metodología. Las cifras ilustrativas del PDF no se usaron como resultados.

## Resultado del barrido de estrés

Se aumentó de 20 en 20 hasta 80 usuarios, con 30 segundos por nivel y rampa de 5 segundos incluida. Resultado: Dos incrementos consecutivos: mejora throughput <=5% y crecimiento P95 >=25%. Este barrido es exploratorio; se recomienda repetir y prolongar las mediciones para confirmar el comportamiento.

En el barrido inicial, de 40 a 60 y a 80 usuarios, el throughput pasó de 4172.58 a 3728.91 y a 2280.49 req/s, mientras P95 pasó de 12 a 31 y a 78 ms. No se alcanzaron 500 ms de P95 ni se observaron errores. Como la prueba previa de 150 usuarios obtuvo mejores resultados, no se puede afirmar que 80 sea la capacidad máxima: hay variabilidad entre ejecuciones y no se aisló su causa.
