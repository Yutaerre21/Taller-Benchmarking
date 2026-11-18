# Taller de benchmarking — Go + PostgreSQL

Implementación individual del taller. API con `net/http`, pool `pgx`, PostgreSQL 16 y JMeter 5.6.3. No requiere instalar Go: compila y ejecuta las pruebas unitarias dentro de Docker.

## Clonar el repositorio

```powershell
git clone https://github.com/Yutaerre21/Taller-Benchmarking.git
cd Taller-Benchmarking
```

El repositorio incluye código, informe, CSV consolidado, resúmenes por escenario y muestras de consumo de contenedores. Las muestras crudas JTL, dashboards y logs quedan guardados localmente y se regeneran al ejecutar las pruebas; no se suben a Git. Tampoco se incluye la instalación de JMeter.

## Iniciar y probar

Con Docker Desktop iniciado, desde esta carpeta:

```powershell
docker compose up -d --build
Invoke-RestMethod http://localhost:5001/health
$body = Get-Content examples/order.json -Raw
Invoke-RestMethod http://localhost:5001/api/orders -Method Post -ContentType application/json -Body $body
```

Respuesta HTTP 201, con un identificador y fecha distintos para cada pedido:

```json
{"orderId":"identificador-generado","totalAmount":26.00,"itemsCount":3,"processedAt":"2026-11-18T00:00:00Z"}
```

`totalAmount = sum(quantity * price)`. Se usan centavos enteros y se rechazan precios con fracciones de centavo. `itemsCount = sum(quantity)` (3 unidades, 2 líneas en el ejemplo). El PDF no define esa distinción: acuerden la misma interpretación entre los cuatro stacks.

El pedido y sus líneas se insertan en una transacción: si una inserción falla, ninguna queda confirmada. Los errores de entrada devuelven 400. La fecha proviene de `created_at` y se devuelve en UTC. No se utiliza ORM ni se agregan índices al esquema solicitado. El pool tiene 20 conexiones; toda la configuración está en `docker-compose.yml`.

```powershell
docker compose ps
docker compose exec -T db psql -U postgres -d orders_db -c "SELECT * FROM orders ORDER BY id DESC LIMIT 5;"
docker compose exec -T db psql -U postgres -d orders_db -c "SELECT * FROM order_items ORDER BY id DESC LIMIT 10;"
python scripts/verify.py
```

## JMeter

Requiere Java, Python 3 y JMeter. En esta máquina la copia local queda en `tools/apache-jmeter-5.6.3`. Después de clonar en otra máquina, descargar [JMeter](https://jmeter.apache.org/download_jmeter.cgi) y extraerlo en `tools/apache-jmeter-5.6.3`, o pasar su ruta al script:

```powershell
& ./scripts/benchmark.ps1 -JMeter 'C:\ruta\apache-jmeter-5.6.3\bin\jmeter.bat'
```

El PDF es inconsistente: sección 5 pide 20/70/150 usuarios, y resultados individuales pide 10/50/100. Se incluyen ambos conjuntos. Para comparar al grupo deben usar los mismos parámetros, duración, JSON, criterio de conteo y hardware documentado.

```powershell
# Tabla individual: 60 segundos por escenario, rampa incluida de 10 segundos
powershell -ExecutionPolicy Bypass -File scripts/benchmark.ps1
```

Para pasar arrays desde PowerShell de forma fiable, invocar directamente el script:

```powershell
& ./scripts/benchmark.ps1 -Users @(20,70,150) -Duration 60 -Ramp 10
```

Cada ejecución crea una carpeta nueva en `results/` con muestras JTL, log, dashboard HTML, métricas JSON/CSV, contenedores activos y muestras de CPU/RAM de API y DB. El resumen incluye la rampa y todas las solicitudes, incluso errores. P95 usa rango más cercano; throughput = solicitudes / tiempo entre inicio de primera y fin de última. El dashboard de JMeter puede redondear percentiles de otra manera.

Para actualizar el informe después de nuevas mediciones: `python scripts/report.py`.

Para estrés, aumentar de 20 en 20 y revisar cada resultado antes de continuar:

```powershell
& ./scripts/benchmark.ps1 -Users @(20,40,60,80,100,120,140,160,180,200) -Duration 60 -Ramp 10
```

Criterio de estrés sugerido (declarado para este proyecto, no impuesto por el PDF): P95 >= 500 ms o errores >= 1%. El script `scripts/stress.ps1` también detiene el barrido al observar dos incrementos consecutivos con mejora de throughput <=5% y crecimiento de P95 >=25%, como indicador de saturación. Si no se alcanza, registrar «no alcanzado» y continuar con otro rango. No confundir esos criterios con capacidad máxima universal.

```powershell
& ./scripts/stress.ps1 -MaxUsers 200 -Duration 60 -Ramp 10
```

## Evidencias visuales para la entrega

Abrir el plan:

```powershell
& ./tools/apache-jmeter-5.6.3/bin/jmeter.bat -t ./jmeter/orders.jmx
```

1. Seleccionar Summary Report y cargar `samples.jtl` del escenario; tomar captura.
2. Repetir con Aggregate Report (P90 por defecto; P95 también está en el resumen y dashboard).
3. Para la captura durante carga, ejecutar una prueba breve en la interfaz. Las mediciones principales se hacen por CLI, como [recomienda Apache](https://jmeter.apache.org/usermanual/get-started.html).
4. Capturar `docker compose ps` y `docker stats` durante la prueba. Los archivos de texto/JSON guardados son evidencia adicional, no reemplazan los pantallazos solicitados.
5. `htop` es de Linux: abrirlo en una distribución WSL que lo tenga instalado y capturar durante la prueba. Aclarar que observa procesos de esa distribución; usar `docker stats` para los contenedores y Administrador de tareas para Windows. No afirmar que sus cifras cubren el mismo conjunto de procesos.

## Entrega y límites

Consultar `INFORME_GO.md` para resultados reales y limitaciones. Entregar código, Compose, SQL, JMX, informe, resultados y capturas. Las conclusiones comparativas requieren las mediciones de los otros tres integrantes; las cifras de ejemplo del PDF no son resultados reales.

El volumen conserva pedidos entre pruebas, por lo que la tabla crece. Reportar el orden de escenarios y evitar otras cargas en la máquina. API, DB y JMeter comparten hardware. Para detener conservando datos: `docker compose down`.

Referencia del controlador: [pgxpool](https://pkg.go.dev/github.com/jackc/pgx/v5/pgxpool).
