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
- Nueva versión en trabajo local: tabs analíticas y exportes sobre el dashboard existente

## Regla vigente de datos
- El generador usa siempre el archivo más reciente `vales_detallada_*.xlsx`
- Archivo más reciente al cierre de esta bitácora: `vales_detallada_2026-05-06_02-47-54.xlsx`
- El dashboard hoy expone una ventana seleccionable de:
  - `Febrero 2026`
  - `Marzo 2026`
  - `Abril 2026`
  - `Mayo 2026`
- La ventana general reconocida por el archivo es: `Febrero a mayo 2026`

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
- `Exportar PDF` abre una vista imprimible del tab activo con:
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
  - pendiente de commit/push/publicación al momento de esta actualización

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

### Cambio local no publicado aún
- Exportes V1:
  - Excel del detalle filtrado
  - PDF imprimible del tab activo con filtros
- Pendiente de commit/push si se aprueba

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
- Publicar la mejora de exportes V1 en GitHub/Render si se aprueba
- Seguir actualizando esta bitácora después de cada cambio o publicación

## Regla de mantenimiento para futuras sesiones
Antes de cerrar cualquier cambio relevante:
1. actualizar `RETOMAR_ANALISIS.md`
2. regenerar el HTML si cambió el generador
3. revisar `git status`
4. hacer commit con mensaje claro
5. hacer push si corresponde
6. verificar local o Render según el alcance del cambio
