# RETOMAR_ANALISIS

## Objetivo de este archivo
Bitácora operativa de continuidad para este proyecto.

Debe actualizarse cada vez que:
- se cambie lógica del dashboard
- se regenere el HTML
- se modifique autenticación o servidor
- se haga commit
- se publique o verifique algo en GitHub o Render

Sirve para retomar trabajo sin perder contexto técnico, funcional ni operativo.

## Proyecto
- Nombre: Dashboard Reciclean de registros operacionales
- Carpeta local: `/Users/cesarmora/Library/CloudStorage/OneDrive-RECICLADORARECICLEANSPA/Gestion Rep Chile/Registros Repchile plataforma-virtual.com`
- Repo GitHub: `https://github.com/cesarmoraa/dashboard-reciclean.git`
- Producción Render: `https://dashboard-reciclean.onrender.com/`
- App local: `http://localhost:3000/`

## Estado actual
- Autenticación por password única: activa
- Login: `/login`
- Backend: `server.js`
- Password por entorno: `ACCESS_PASSWORD`
- Dashboard protegido por cookie `HttpOnly`: sí
- Logout: sí
- Deploy GitHub: operativo
- Deploy Render: operativo y verificado
- Dashboard sincronizado con publicación y con el Excel más reciente disponible

## Regla vigente de datos
- El generador usa siempre el archivo más reciente `vales_detallada_*.xlsx`
- Archivo más reciente al cierre de esta bitácora: `vales_detallada_2026-05-14_17-28-21.xlsx`
- El dashboard hoy expone una ventana seleccionable de:
  - `Febrero 2026`
  - `Marzo 2026`
  - `Abril 2026`
  - `Mayo 2026`
- La ventana general reconocida por el archivo es: `Febrero a mayo 2026`
- El criterio de selección del archivo se corrigió para usar el timestamp del nombre (`vales_detallada_YYYY-MM-DD_HH-MM-SS.xlsx`) y no el `mtime` del archivo, porque OneDrive podía dejar un corte más nuevo fuera del dashboard.

## Estructura importante
- `server.js`
  Servidor Node.js con login, sesión por cookie y protección de rutas
- `public/login.html`
  Pantalla de acceso privada
- `build_reciclean_dashboard.py`
  Generador del HTML final
- `dashboard_reciclean_registros_mes_actual.html`
  Dashboard generado y servido por backend
- `docs/chat-crear-dashboard-de-registros.md`
  Documentación larga del proyecto

## Cambios funcionales acumulados

### 1. Autenticación privada
- Se creó acceso por password única, sin usuario
- Validación solo en backend
- Variable requerida:
  - `ACCESS_PASSWORD`
- Cookie:
  - `HttpOnly`
  - `Path=/`
  - `SameSite=Lax`
  - `Secure` en producción

### 2. Publicación
- Repo Git fue creado en esta carpeta
- Remote GitHub conectado
- Push a `main` operativo
- Render quedó conectado y responde correctamente

### 3. Dashboard y datos
- Se mantuvo el frontend base y se trabajó sobre la estructura existente
- Se mejoró responsive para móvil
- Se agregó selector global de sucursal en el hero
- Se agregó selector global de período en el hero
- El selector `Mes analizado` ahora es desplegable real
- El selector `Vista sucursal` ahora vive en el hero y no como bloque duplicado lateral

### 4. Detalle operativo
- El filtro `Sucursal` del bloque `Detalle operativo` quedó independiente del selector superior `Vista sucursal`
- La vista ejecutiva superior controla:
  - KPIs
  - gráficos
  - rankings
  - insights
- El detalle inferior filtra sobre todo el mes activo, no sobre la sucursal activa del hero

### 5. Tabs analíticas generadas en local
- Se creó una estructura nueva por tabs sin rehacer el frontend base:
  - `Resumen Ejecutivo`
  - `Histórico y Tendencias`
  - `Riesgos e Inconsistencias`
  - `Calidad y Brechas`
- Todo está pensado para salir solo de la información disponible en los Excel actuales.
- Estado de esta parte:
  - generado en `build_reciclean_dashboard.py`
  - regenerado en `dashboard_reciclean_registros_mes_actual.html`
  - publicado y verificado en Render

### 6. Exportes V1
- Se agregaron dos acciones nuevas en el hero autenticado:
  - `Exportar Excel`
  - `Exportar PDF`
- `Exportar Excel` descarga el detalle operativo filtrado en formato `.xls`
- `Exportar PDF` usa impresión directa del navegador sobre una vista interna preparada, sin depender de ventanas emergentes, con:
  - hero
  - filtros activos
  - contenido de la pestaña visible
- Ambos exportes arrastran:
  - período activo
  - vista sucursal
  - filtros del bloque `Detalle operativo`
- Estado:
  - implementado en el generador
  - HTML regenerado
  - validado en local
  - publicado

### 7. Ajuste de armonía visual e interacción
- Se corrigió el bloque superior para recuperar mejor simetría:
  - tabs en ancho completo y distribución uniforme
  - acciones del hero en grilla consistente
  - mensaje de estado breve para feedback del usuario
- Se corrigió el problema reportado en publicación donde el PDF podía percibirse como "no hace nada" por depender de `window.open`
- Estado:
  - implementado
  - publicado

## Historial cronológico resumido

### Commit `9940c9f`
- `Add private dashboard auth and Render setup`
- Se implementó backend mínimo, login, sesión, logout y estructura para Render

### Commit `7b1a0d1`
- `Document repo status and deployment blockers`
- Se registró estado de repo, despliegue y bloqueos iniciales

### Commit `8949a52`
- `Improve mobile-first login and dashboard layout`
- Se mejoró UX móvil del login y del dashboard

### Commit `641530a`
- `Use latest vales file with April-May window`
- Se dejó el dashboard tomando automáticamente el último `vales_detallada_*.xlsx`
- En ese momento la ventana quedó consolidada en abril y mayo

### Commit `37c1fa8`
- `Add month selector and independent detail filters`
- Se agregó selector de período con febrero, marzo, abril y mayo
- Se desacopló el filtro `Sucursal` del detalle respecto de `Vista sucursal`
- Se integró el selector superior en el hero

### Commit `5f2c8e2`
- `Add export actions for filtered dashboard views`
- Se agregaron exportes V1 a Excel y PDF sobre la vista filtrada

### Commit `94f2683`
- `Polish dashboard layout and print export flow`
- Se mejoró la simetría visual del hero y tabs
- Se reemplazó la exportación PDF basada en popup por impresión directa

## Errores encontrados y solución

### 1. Falso 404 en Render
Problema:
- Se interpretó que Render estaba caído porque `curl -I` devolvía `404`

Causa real:
- El servidor maneja `GET`, no `HEAD`

Solución:
- Verificar con `GET /login`, `GET /health` y login real por cookie

Estado:
- Resuelto

### 2. Python local sin `pandas`
Problema:
- `python3 build_reciclean_dashboard.py` falló por falta de `pandas`

Solución:
- Usar el runtime del workspace:
  - `/Users/cesarmora/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`

Estado:
- Resuelto

### 3. Selector de sucursal duplicado
Problema:
- Existía chip informativo arriba y selector lateral aparte

Solución:
- Se dejó un único selector de `Vista sucursal` integrado en el hero

Estado:
- Resuelto

### 4. Filtro de sucursal del detalle dependía de la vista superior
Problema:
- En `Detalle operativo`, el filtro `Sucursal` heredaba la restricción del selector `Vista sucursal`

Solución:
- Separar la fuente de datos del detalle para que use todo el período activo

Estado:
- Resuelto

### 5. El dashboard original estaba quedando muy cargado en una sola pantalla
Problema:
- El alcance nuevo del gerente no conviene mezclarlo completo con la vista ejecutiva actual

Solución aplicada:
- Se comenzó una estructura por tabs para separar:
  - resumen
  - histórico
  - riesgos
  - calidad

Estado:
- Generado localmente
- Publicado

### 6. Warning por cierre de script en la plantilla del PDF
Problema:
- El generador mostró un warning por `invalid escape sequence '\/'`

Causa real:
- La plantilla de `exportPdf()` estaba cerrando el tag `<script>` con `\<\/script>` dentro del string

Solución:
- Reemplazar el cierre por `</script>` dentro de la plantilla final
- Regenerar el HTML y validar sintaxis del script embebido

Estado:
- Resuelto

### 7. Exportación PDF percibida como inactiva en publicación
Problema:
- En Render el botón de PDF podía parecer inactivo o silencioso

Causa real:
- Dependía de abrir una ventana emergente para imprimir
- Eso degrada la experiencia en algunos navegadores o contextos embebidos

Solución:
- Reemplazar el flujo por impresión directa sobre una vista interna preparada para `window.print()`
- Agregar feedback visual con un estado corto en el hero

Estado:
- Resuelto

### 8. Cálculo incorrecto en "Clientes inactivos 30+ días"
Problema:
- La tabla podía mostrar clientes con menos de 30 días reales de inactividad
- Ejemplo detectado: última visita `30/04/2026` apareciendo como `31` días en mayo parcial

Causa real:
- El cálculo estaba usando un corte temporal inconsistente con la data visible del mes

Solución:
- Calcular `daysInactive` contra la última fecha real cargada del período activo
- Filtrar para mostrar solo clientes con `30` días o más de inactividad efectiva

Estado:
- Resuelto en local
- Pendiente de publicación al momento de esta actualización

## Verificaciones realizadas

### Local
- `http://localhost:3000/login` funcional
- Login correcto con password
- Sesión persistente
- Dashboard protegido en `/`
- Logout funcional
- Selector de período visible
- Selector de sucursal superior visible
- Filtro de sucursal del detalle independiente
- Validación de sintaxis JS del HTML generado: OK
- Validación estructural del HTML generado con tabs nuevas: OK
- Exportar Excel V1: implementado
- Exportar PDF V1: implementado
- Filtros activos incluidos en exportes: OK

### Producción
- `GET /health` responde `{"ok":true,"status":"ok"}`
- `GET /login` carga
- `POST /api/login` responde `{"ok":true}`
- `GET /` autenticado entrega el dashboard actualizado
- Producción verificada con título:
  - `Dashboard Reciclean | Febrero a mayo 2026`
- Producción verificada con:
  - tabs visibles
  - exportes visibles
  - flujo PDF corregido
  - fuente actualizada al Excel más reciente

## Variables de entorno
- Requerida:
  - `ACCESS_PASSWORD=RepRepChile2026`

## Comando de inicio
- `npm start`

## Cómo cambiar la password
- Cambiar solo la variable `ACCESS_PASSWORD` en Render
- No requiere tocar lógica ni frontend

## Pendientes recomendados
- Hacer una pasada visual final mobile sobre producción
- Decidir si conviene agregar un selector global de tipo de servicio
- Seguir actualizando esta bitácora después de cada cambio o publicación

## Avance reciente: análisis de comportamiento por cliente

### 9. Nueva capa ejecutiva de frecuencia y comportamiento
Objetivo:
- Agregar una lectura ejecutiva en `Histórico y Tendencias` para detectar cambios relevantes por cliente en:
  - frecuencia de visitas
  - kilos operados
  - monto operado
  - material dominante

Implementado:
- Bloque nuevo `Patrones y cambios de comportamiento`
- Resumen superior con:
  - clientes con caída
  - clientes con alza
  - cambio de material
  - clientes reactivados
- Tabla con:
  - cliente
  - tendencia
  - visitas actual vs promedio previo
  - kilos actual vs promedio previo
  - monto actual vs promedio previo
  - material dominante actual y previo
  - cambio detectado
  - nivel de alerta

Ajustes técnicos aplicados para reducir ruido:
- La comparación usa una ventana de hasta `3 meses previos`
- Para comportamiento se usan montos y kilos por `magnitud operada`, evitando distorsión por signos negativos
- Se endurecieron umbrales para no elevar alertas irrelevantes en clientes pequeños
- Se redujo la sensibilidad de `alzas` y `caídas` para que la tabla quede más gerencial
- La columna `Tendencia` se hizo explícita por dimensión, por ejemplo:
  - `Frecuencia a la baja`
  - `Kilos al alza`
  - `Monto a la baja`
  - `Cambio de mix`

Estado:
- Implementado en local
- Publicado en GitHub y Render
- Commit de referencia: `453e4e9` `Add executive client behavior analysis`

## Regla de mantenimiento para futuras sesiones
Antes de cerrar cualquier cambio relevante:
1. actualizar `RETOMAR_ANALISIS.md`
2. regenerar el HTML si cambió el generador
3. revisar `git status`
4. hacer commit con mensaje claro
5. hacer push si corresponde
6. verificar local o Render según el alcance del cambio
