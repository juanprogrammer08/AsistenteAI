# YERUZZA STUDIO - Documentación del Proyecto

Este proyecto es una aplicación full-stack que incluye un frontend en React 18 y un backend en FastAPI. Está diseñado para ser desplegado fácilmente con Docker Compose y soporta autenticación JWT, roles de usuario, y persistencia en base de datos PostgreSQL con fallback a SQLite.

---

## Índice

- [Requisitos Previos](#requisitos-previos)
- [Levantando el Proyecto Localmente](#levantando-el-proyecto-localmente)
- [Cuentas de Prueba](#cuentas-de-prueba)
- [Despliegue en Dokploy](#despliegue-en-dokploy)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Notas y Recomendaciones](#notas-y-recomendaciones)

---

## Requisitos Previos

Para trabajar con este proyecto necesitas tener instalado:

- [Docker](https://docs.docker.com/get-docker/) (versión reciente)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Node.js](https://nodejs.org/) (v16 o superior recomendado)
- [npm](https://www.npmjs.com/get-npm)

---

## Levantando el Proyecto Localmente

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_PROYECTO>
```

### 2. Levantar la API y la base de datos con Docker Compose

```bash
docker-compose up --build
```

Esto construirá la imagen del backend y levantará los servicios:

- **api**: Backend FastAPI en `http://localhost:8000`
- **db**: Base de datos PostgreSQL con usuario `studio`, contraseña `studio`, base `producto`

El backend intentará conectarse a PostgreSQL y si no está disponible usará SQLite local (`./app.db`).

### 3. Instalar y levantar el frontend React

En otra terminal, dentro del directorio raíz:

```bash
npm install
npm run dev
```

Esto levantará el frontend en modo desarrollo en `http://localhost:5173` (o el puerto que indique Vite).

### 4. Acceder a la aplicación

Abre tu navegador en:

```
http://localhost:5173
```

La aplicación se comunicará con la API en `http://localhost:8000/api`.

---

## Cuentas de Prueba

Para facilitar pruebas, el backend incluye estas cuentas iniciales:

| Usuario       | Email               | Contraseña | Rol   |
|---------------|---------------------|------------|-------|
| admin         | admin@yeruzza.com   | admin123   | admin |
| usuario       | user@yeruzza.com    | user123    | user  |

Puedes usar estas credenciales para iniciar sesión en la aplicación.

---

## Despliegue en Dokploy

Para desplegar en Dokploy, sigue estos pasos:

1. **Configura variables de entorno** en Dokploy:

   - `AUTH_SECRET`: Clave secreta para JWT (recomendada)
   - `DATABASE_URL`: URL de conexión a la base de datos PostgreSQL

2. **Sube el repositorio** a tu repositorio Git remoto (GitHub, GitLab, etc.)

3. **Configura Dokploy** para que use el `docker-compose.yml` del proyecto.

4. **Despliega** la aplicación desde Dokploy.

Dokploy levantará los servicios `api` y `db` según el `docker-compose.yml`. Asegúrate que la base de datos PostgreSQL esté accesible y que las variables de entorno estén correctamente configuradas.

---

## Estructura del Proyecto

```
/
├── README.md
├── docker-compose.yml
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── App.jsx
│   ├── main.jsx
│   └── style.css
└── api/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        └── main.py
```

---

## Notas y Recomendaciones

- **Autenticación**: El backend usa JWT con roles `admin` y `user`. El token se guarda en `localStorage` y se envía en cada petición con el header `Authorization: Bearer <token>`.

- **Persistencia**: Se usa PostgreSQL por defecto, pero si no está disponible, el backend cae a SQLite para facilitar desarrollo local sin dependencias externas.

- **Frontend**: El frontend maneja rutas protegidas y muestra formularios de login y registro. En caso de fallo de conexión con la API, usa datos de ejemplo para mantener funcionalidad básica.

- **Extensibilidad**: El proyecto está preparado para agregar módulos como pasarelas de pago o bots de chat, que pueden integrarse como microservicios o módulos independientes.

- **Variables de entorno importantes**:

  - `AUTH_SECRET` o `JWT_SECRET`: Clave para firmar tokens JWT.
  - `DATABASE_URL`: Cadena de conexión a la base de datos PostgreSQL.

- **Pruebas**: Se recomienda probar la API con herramientas como Postman o curl para verificar autenticación y rutas CRUD.

---

Si tienes dudas o necesitas soporte, contacta con el equipo de YERUZZA STUDIO. ¡Gracias por usar nuestro producto!