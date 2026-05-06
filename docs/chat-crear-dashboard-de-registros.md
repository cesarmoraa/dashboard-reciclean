# Crear dashboard de registros

## Objetivo
Publicar el dashboard de registros operacionales de Reciclean con acceso privado por una sola password global, validada en backend, manteniendo el HTML actual y dejando un flujo claro para operación local y despliegue en Render.

## Arquitectura
- `server.js`
  Backend mínimo en Node.js sin dependencias externas.
- `dashboard_reciclean_registros_mes_actual.html`
  Dashboard principal existente, ahora pensado para ser servido solo detrás de sesión válida.
- `public/login.html`
  Pantalla de acceso por password única.
- `build_reciclean_dashboard.py`
  Generador del HTML del dashboard a partir del Excel más reciente `vales_detallada_*.xlsx`.
- `render.yaml`
  Blueprint base para Render.
- `package.json`
  Punto de arranque para local y producción.

## Decisiones tomadas
- No se rehízo el frontend del dashboard.
- La autenticación se resolvió en backend, no en frontend.
- No se usa username ni email.
- La sesión se maneja con cookie `HttpOnly`, `Path=/`, `SameSite=Lax` y `Secure` en producción.
- El dashboard se sirve desde `/`, `/dashboard` y `/dashboard_reciclean_registros_mes_actual.html`, siempre protegidos.
- La pantalla `/login` queda pública.
- No se publican ni exponen los archivos Excel por rutas HTTP.
- El generador toma siempre el archivo `vales_detallada_*.xlsx` más reciente y arma el dashboard con la ventana de los dos meses más recientes disponibles en ese archivo.

## Cómo funciona el acceso por password
- La password se lee desde `ACCESS_PASSWORD`.
- La validación ocurre en `POST /api/login`.
- Si la password es correcta:
  - se genera una cookie de sesión firmada
  - se habilita acceso a las rutas privadas
- Si la password es incorrecta:
  - se responde con mensaje genérico
  - no se revelan reglas internas
- `GET /api/session`
  - confirma si la sesión sigue vigente
- `POST /api/logout`
  - elimina la cookie y devuelve al login

## Variable de entorno
Variable requerida en Render:

```env
ACCESS_PASSWORD=RepRepChile2026
```

Se puede cambiar más adelante sin tocar la lógica, solo actualizando la variable en Render.

## Ejecución local
Desde esta carpeta:

```bash
ACCESS_PASSWORD=RepRepChile2026 npm start
```

Luego abrir:

```text
http://localhost:3000
```

## Despliegue en Render
### Opción 1. Web Service conectado a GitHub
- Subir esta carpeta a un repositorio GitHub.
- Crear un Web Service en Render apuntando a ese repo.
- Configurar:
  - Build Command: `npm install`
  - Start Command: `npm start`
  - Environment Variable: `ACCESS_PASSWORD=RepRepChile2026`

### Opción 2. Blueprint con `render.yaml`
- Mantener `render.yaml` en la raíz.
- Conectar el repo en Render usando Blueprint.
- Definir `ACCESS_PASSWORD` desde el panel de variables.

## Flujo local + GitHub + Render
1. Actualizar el Excel o regenerar el dashboard con `build_reciclean_dashboard.py`.
2. Probar en local con `ACCESS_PASSWORD=... npm start`.
3. Confirmar login, sesión, logout y carga del dashboard en `http://localhost:3000`.
4. Subir cambios al repo GitHub.
5. Render redeploya automáticamente si el servicio está conectado al repo.

## Regla de actualización de datos
- El dashboard no queda fijo a un solo mes.
- En cada regeneración se busca el `vales_detallada_*.xlsx` más reciente de la carpeta.
- Sobre ese archivo se detectan los períodos con datos válidos.
- Se usan los dos meses más recientes disponibles.
- Si el archivo solo trae un mes, se muestra solo ese mes.
- Con el archivo actual más reciente, la ventana consolidada es `Abril y mayo 2026`.

## Errores encontrados
- La carpeta actual no estaba dentro de un repositorio Git al inicio del trabajo.
- El proyecto original era un HTML local abierto por `file://`, lo que no sirve para autenticación real.
- Fue necesario introducir backend para validar password y mantener sesión por cookie.
- El resumen original del dashboard estaba pensado para un solo mes, por lo que hubo que ajustar el generador para soportar una ventana de dos meses sin romper KPIs, series ni filtros.

## Aprendizajes reutilizables
- No confiar en pruebas desde `file://` cuando hay autenticación.
- Para acceso privado simple, backend mínimo con cookie firmada es suficiente y más mantenible que esconder lógica en frontend.
- Si el dashboard se genera desde script, conviene aplicar cambios persistentes también en el generador para no perderlos al recalcular.
- Render funciona bien con Node.js puro cuando el proyecto no necesita dependencias pesadas.

## Estado actual
- Login por password única: listo
- Backend validando `ACCESS_PASSWORD`: listo
- Sesión por cookie: listo
- Dashboard protegido: listo
- Logout: listo
- Estructura para Render: lista
- Repositorio Git local inicializado: listo
- Remote GitHub configurado: listo
- Repositorio GitHub conectado: `https://github.com/cesarmoraa/dashboard-reciclean.git`
- Deploy en Render operativo: `https://dashboard-reciclean.onrender.com/`
- Verificación local en `http://127.0.0.1:3000`: realizada
- Verificación de deploy en Render: realizada

## Verificación local realizada
- `GET /` sin sesión redirige a `/login`
- `GET /login` entrega la pantalla de acceso
- `POST /api/login` con password incorrecta responde `401`
- `POST /api/login` con password correcta crea cookie `HttpOnly`
- `GET /api/session` con cookie válida responde autenticado
- `GET /` con cookie válida entrega el dashboard protegido
- `POST /api/logout` elimina la cookie
- `GET /` después de logout vuelve a redirigir a `/login`
