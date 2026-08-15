# Centro de Monitoreo Compensar

Aplicación unificada para ejecutar y consolidar los monitoreos de **Pasarelas (eCollect + PayU)**, **AWS** y **Hércules**.

> Este README está pensado para usuarios que no necesitan saber Python, PowerShell ni programación. Si sigues los pasos en orden, puedes instalar y usar el programa desde cero.

---

## 1. ¿Qué hace este programa?

Desde una sola ventana puedes:

- Ejecutar uno, dos o los tres monitoreos.
- Ejecutar el corte programado del día.
- Consultar desde las 00:00 hasta la hora actual.
- Ejecutar el día anterior completo.
- Consultar una fecha específica.
- Guardar usuarios y claves localmente.
- Preparar automáticamente las sesiones de los portales.
- Ver el estado de cada monitoreo.
- Cancelar una ejecución.
- Abrir la carpeta donde quedaron los resultados.
- Consultar los dashboards HTML.
- Mantener un histórico mensual sin mezclar pruebas o cortes del mismo día.

**Importante:** contraseñas, sesiones del navegador y archivos temporales no deben subirse a GitHub.

---

## 2. Antes de empezar

Necesitas:

- Windows 10 u 11.
- Internet.
- Acceso autorizado a los portales que vayas a monitorear.
- Python 3.12 instalado.
- Google Chrome instalado.
- Permiso para ejecutar archivos `.bat` y PowerShell.
- Permisos de administrador únicamente para instalar las tareas automáticas de Windows.

Git es opcional si vas a descargar el proyecto como ZIP.

---

## 3. Descargar el programa

### Opción A — La más fácil: descargar ZIP

1. Entra a: `https://github.com/EstebanMB18/Monitoreo`
2. Selecciona la rama **main**.
3. Pulsa **Code → Download ZIP**.
4. Descomprime el ZIP.

Ejemplo de carpeta:

```text
C:\Dev\Monitoreos\Monitoreo
```

> No ejecutes el programa directamente dentro del ZIP. Primero debes descomprimirlo.

### Opción B — Con Git

```powershell
git clone -b main https://github.com/EstebanMB18/Monitoreo.git
cd Monitoreo
```

---

## 4. Instalar por primera vez

Dentro de la carpeta del programa busca:

```text
INSTALAR.bat
```

Haz doble clic.

El instalador prepara el entorno de Python y las dependencias necesarias.

Cuando termine, no necesitas ejecutar comandos de Python manualmente.

---

## 5. Abrir el programa

Haz doble clic en:

```text
ABRIR_MONITOREO.bat
```

Se abrirá el **Centro de Monitoreo Compensar**.

La aplicación tiene tres monitores:

```text
PASARELAS   |   AWS   |   HÉRCULES
```

Puedes marcar únicamente los que necesites.

Ejemplo:

```text
[X] PASARELAS
[ ] AWS
[ ] HÉRCULES
```

En ese caso **solo debe ejecutarse Pasarelas**.

---

## 6. Configuración inicial

Antes de la primera ejecución entra a:

**Usuarios, claves y sesiones**

Allí encontrarás:

- eCollect · Usuario
- eCollect · Clave
- PayU · Usuario
- PayU · Clave
- Hércules · Usuario
- Hércules · Clave

Completa las credenciales que te correspondan y pulsa **GUARDAR** o **GUARDAR Y CERRAR**.

Las credenciales se guardan localmente en el computador.

> No compartas archivos `.env`, sesiones `.json` ni contraseñas por GitHub, Teams, correo o chats.

---

## 7. Sesiones del navegador

Normalmente **no tienes que guardar sesiones manualmente**.

En la primera ejecución el sistema intenta prepararlas automáticamente.

Ejemplos:

```text
PASARELAS · PREPARANDO · Preparando sesión eCollect automáticamente...
PASARELAS · PREPARANDO · Sesión preparada correctamente
```

```text
HÉRCULES · PREPARANDO · Creando sesión automáticamente...
```

Si una sesión expira, el sistema puede volver a prepararla.

Los botones de sesión de la ventana de credenciales quedan disponibles para soporte o casos especiales.

---

## 8. Elegir el periodo

### Corte programado

Usa los rangos operativos de los cortes:

```text
09:00
13:00
17:00
```

### Ahora · 00:00 a hora actual

Consulta desde las 00:00 hasta el momento de ejecución.

### Día anterior

Consulta el día anterior. Para el histórico normalmente se usa:

```text
00:00 → 23:59
```

### Fecha específica

Formato obligatorio:

```text
AAAA-MM-DD
```

Ejemplo:

```text
2026-08-15
```

También puedes escoger día completo o un rango de horas.

---

## 9. Ejecutar un monitoreo

1. Marca los monitores que necesitas.
2. Selecciona el modo.
3. Pulsa **EJECUTAR**.

Los estados pueden ser:

```text
PREPARANDO
EJECUTANDO
FINALIZADO
ERROR
CANCELADO
NO SELECCIONADO
```

---

## 10. ¿Qué significa el porcentaje?

El porcentaje es una referencia visual basada en fases reales, no solo en tiempo.

Puede avanzar cuando ocurre algo como:

- Preparación de sesión.
- Inicio del navegador.
- Descarga de información.
- Procesamiento.
- Generación de Excel.
- Generación de HTML.
- Consolidación final.

Pasarelas puede tardar más porque trabaja con varios procesos:

```text
PayU
eCollect rápido
41605 JAVA
41610 RED
```

Los procesos **41605 JAVA** y **41610 RED** pueden tardar más que los demás.

---

## 11. Cancelar todo

Si necesitas detener una ejecución pulsa:

```text
CANCELAR TODO
```

El sistema intentará detener los procesos asociados y debe finalizar con estado:

```text
CANCELADO
```

---

## 12. Ver resultados

Después de ejecutar puedes usar:

```text
Abrir carpeta
```

Si ejecutaste un solo monitor, se abre su carpeta de resultados. Si ejecutaste varios, se puede abrir el consolidado general.

También puedes usar:

```text
Ver dashboard
```

Si ejecutaste un único monitor, abre su dashboard. Si ejecutaste varios, abre el dashboard general.

---

## 13. ¿Dónde quedan los archivos?

La carpeta de salida se configura desde la aplicación.

En equipos de Compensar normalmente se usa una ruta dentro de:

```text
OneDrive - Compensar
```

Ejemplo:

```text
...\COORDINACION SOPORTE SOLUCIONES - Monitoreo diario
```

Dentro se manejan carpetas como:

```text
AWS
ECOLLECT
HERCULES
GENERAL
```

---

## 14. Tareas automáticas de Windows

Para configurar las tareas automáticas busca:

```text
CONFIGURAR_TAREAS.bat
```

Haz clic derecho y selecciona **Ejecutar como administrador**.

Programación operativa:

| Monitor | Corte 09 | Corte 13 | Corte 17 |
|---|---:|---:|---:|
| Pasarelas | 08:45 | 12:45 | 16:45 |
| AWS | 08:52 | 12:52 | 16:52 |
| Hércules | 08:57 | 12:57 | 16:57 |

También existe:

```text
Compensar Monitoreo DIA ANTERIOR
```

Se activa al iniciar sesión y procesa el día anterior completo. El sistema controla que no se repita innecesariamente durante el mismo día.

---

## 15. Histórico mensual

El acumulado mensual se alimenta principalmente con ejecuciones validadas de **día anterior**.

Las pruebas manuales y cortes del mismo día no deben contaminar ese histórico.

---

## 16. Si algo sale mal

### Error de credenciales

Entra a **Usuarios, claves y sesiones**, revisa usuario y clave y guarda nuevamente.

### Sesión vencida

Vuelve a ejecutar. El programa intentará preparar la sesión otra vez cuando corresponda.

### Un monitor tarda mucho

No cierres inmediatamente el programa. En Pasarelas, 41605 JAVA y 41610 RED pueden tardar más.

### Necesito detener todo

Pulsa **CANCELAR TODO**.

### No aparecen resultados

Pulsa **Abrir carpeta** y revisa también la ruta de salida configurada.

### No abre el programa

Ejecuta otra vez:

```text
INSTALAR.bat
```

Luego:

```text
ABRIR_MONITOREO.bat
```

Si continúa el problema, copia el error completo y envíalo al responsable técnico.

---

## 17. Qué NO debes hacer

- No borres archivos `.py`.
- No edites `.env` si no sabes qué estás modificando.
- No compartas contraseñas.
- No subas archivos de sesión a GitHub.
- No ejecutes varias copias del programa al mismo tiempo.
- No cambies tareas programadas sin validación.
- No cierres 41605 JAVA o 41610 RED mientras estén trabajando.
- No uses `git push --force` si no sabes exactamente qué estás haciendo.

---

## 18. Ramas de Git

El repositorio usa:

```text
develop  → desarrollo
testing  → pruebas
main     → producción estable
```

Para un usuario normal, la versión que debe descargar es:

```text
main
```

No instales `develop` o `testing` en un equipo operativo salvo que estés haciendo una prueba controlada.

---

## 19. Actualizar si instalaste con Git

```powershell
git switch main
git pull
```

Si cambiaron dependencias, vuelve a ejecutar:

```text
INSTALAR.bat
```

---

## 20. Estructura rápida

```text
Monitoreo/
│
├── ABRIR_MONITOREO.bat
├── CONFIGURAR_TAREAS.bat
├── INSTALAR.bat
├── Centro_Monitoreo_Compensar.py
├── README.md
│
├── core/
├── monitores/
│   ├── aws/
│   ├── hercules/
│   └── pasarelas/
├── scripts/
└── config/
```

Un usuario normal debería usar principalmente:

```text
INSTALAR.bat
ABRIR_MONITOREO.bat
CONFIGURAR_TAREAS.bat
```

---

## 21. Instalación resumida en 1 minuto

```text
1. Descarga MAIN como ZIP.
2. Descomprime la carpeta.
3. Instala Python 3.12 si no lo tienes.
4. Ejecuta INSTALAR.bat.
5. Ejecuta ABRIR_MONITOREO.bat.
6. Abre Usuarios, claves y sesiones.
7. Guarda tus credenciales.
8. Configura la carpeta de salida.
9. Selecciona el monitor.
10. Pulsa EJECUTAR.
```

Si el equipo debe ejecutar automáticamente:

```text
11. Ejecuta CONFIGURAR_TAREAS.bat como administrador.
```

---

## 22. Cómo reportar una falla

No envíes solamente:

```text
"No funciona"
```

Envía:

1. Monitor ejecutado.
2. Modo seleccionado.
3. Hora aproximada.
4. Captura de pantalla.
5. Últimas líneas del log.
6. Mensaje de error completo.

Ejemplo:

```text
Monitor: Pasarelas
Modo: Ahora
Hora: 11:35
Estado: ERROR
Mensaje: [copiar aquí el error completo]
```

Esto permite encontrar el problema mucho más rápido.

---

**Centro de Monitoreo Compensar**  
AWS · Pasarelas · Hércules
