# Guía de Configuración Multi-usuario (Red Local)

Esta guía explica cómo configurar el sistema "Kardex Valorizado" para que funcione en múltiples computadoras dentro de una misma red local, compartiendo la base de datos y los archivos multimedia.

## Requisitos Previos

1.  **Computadora Principal (Servidor):** Una PC que estará encendida mientras los demás usen el sistema.
2.  **Red Local:** Todas las computadoras deben estar conectadas al mismo router (WiFi o Cable).
3.  **PostgreSQL:** Motor de base de datos robusto para múltiples usuarios.

---

## Paso 1: Configurar el Servidor (PC Principal)

### 1.1 Instalar PostgreSQL
1.  Descargue e instale PostgreSQL desde [postgresql.org](https://www.postgresql.org/download/windows/).
2.  Durante la instalación, establezca una contraseña para el usuario `postgres` (ej: `admin123`). **¡No la olvide!**
3.  Termine la instalación.

### 1.2 Crear la Base de Datos
1.  Abra **pgAdmin 4** (se instala con PostgreSQL).
2.  Conéctese al servidor (pedirá la contraseña del paso anterior).
3.  Click derecho en `Databases` -> `Create` -> `Database...`
4.  Nombre: `kardex_db`
5.  Click en `Save`.

### 1.3 Permitir Conexiones Remotas
1.  Busque la carpeta de instalación (ej: `C:\Program Files\PostgreSQL\16\data`).
2.  Abra el archivo `pg_hba.conf` con el Bloc de Notas (como Administrador).
3.  Agregue esta línea al final:
    ```
    host    all             all             0.0.0.0/0            scram-sha-256
    ```
4.  Abra el archivo `postgresql.conf` en la misma carpeta.
5.  Busque la línea `listen_addresses = 'localhost'` y cámbiela a:
    ```
    listen_addresses = '*'
    ```
6.  Reinicie el servicio de PostgreSQL (o reinicie la PC).

### 1.4 Compartir Carpeta Multimedia
1.  Cree una carpeta llamada `KardexMedia` en una ubicación accesible (ej: `C:\KardexMedia`).
2.  Click derecho -> Propiedades -> Pestaña **Compartir**.
3.  Click en **Compartir...** -> Seleccione "Todos" (o los usuarios específicos) -> Click en **Agregar**.
4.  Cambie el nivel de permiso a **Lectura y escritura**.
5.  Click en **Compartir**.
6.  Anote la ruta de red (ej: `\\NOMBRE-PC\KardexMedia` o `\\192.168.1.10\KardexMedia`).

---

## Paso 2: Configurar los Clientes (Otras PCs)

En cada computadora que usará el sistema (incluida la principal si se usa como cliente):

### 2.1 Instalar el Sistema
Copie la carpeta del programa a la computadora cliente.

### 2.2 Configurar `config.json`
En la carpeta raíz del programa, cree o edite el archivo `config.json` con los siguientes datos:

```json
{
    "DB_URL": "postgresql+pg8000://postgres:CONTRASEÑA@IP_SERVIDOR/kardex_db",
    "MEDIA_ROOT": "\\\\IP_SERVIDOR\\KardexMedia"
}
```

*   **Reemplazos:**
    *   `postgres`: Usuario de la base de datos (por defecto es postgres).
    *   `CONTRASEÑA`: La contraseña que puso al instalar PostgreSQL.
    *   `IP_SERVIDOR`: La dirección IP de la PC Principal (ej: `192.168.1.10`).
    *   `kardex_db`: El nombre de la base de datos creada.
    *   `\\\\IP_SERVIDOR\\KardexMedia`: La ruta de la carpeta compartida. (Note las barras dobles escapadas en JSON).

### 2.3 Instalar Driver de Base de Datos
Si no está instalado, necesitará el driver de PostgreSQL para Python. Abra una terminal en la carpeta del proyecto y ejecute:
```bash
pip install pg8000
```
*(El sistema está configurado para usar `pg8000` o `psycopg2` si se especifica en la URL).*

---

## Paso 3: Iniciar el Sistema

1.  Ejecute `main.py`.
2.  El sistema detectará la nueva configuración y creará las tablas en PostgreSQL automáticamente la primera vez.
3.  Inicie sesión con el usuario administrador por defecto (`admin` / `admin123`).

---

## Solución de Problemas

*   **Error de conexión:** Verifique que el Firewall de Windows en el Servidor permita el puerto 5432 (PostgreSQL).
*   **Error de archivos:** Verifique que la carpeta compartida tenga permisos de "Lectura y Escritura" para todos.
*   **IP Dinámica:** Si la IP del servidor cambia, tendrá que actualizar el `config.json` en todas las PCs. Se recomienda configurar una IP Fija en el servidor.
