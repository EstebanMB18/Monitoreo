# Centro de Monitoreo Compensar · FINAL

Versión unificada para **AWS + Pasarelas + Hércules** con:

- ejecución independiente o conjunta;
- interfaz gráfica mejorada;
- credenciales locales por equipo;
- dashboard general más visual y ordenado;
- acumulado mensual **solo** con ejecuciones de **día anterior**;
- tarea adicional `Compensar Monitoreo DIA_ANTERIOR` que corre al iniciar sesión una sola vez al día;
- limpieza automática de temporales y logs.

## Cambios principales de esta entrega

1. **Pantalla principal renovada** con estilo más elegante y soporte visual de marca Compensar.
2. **Dashboard general rediseñado** con vista unificada, modo entre semana / fin de semana y accesos rápidos.
3. **Histórico técnico separado del histórico mensual**:
   - `historico_ejecuciones.csv`: registra todo.
   - `historico_mensual.csv`: solo alimenta el acumulado del mes con el proceso de día anterior.
4. **Excel mensual** basado únicamente en el consolidado validado.
5. **Programación automática** de las 9 tareas de corte + 1 tarea diaria de día anterior.

## Carpeta de salida por defecto

`C:\Users\esteban\OneDrive - Compensar\COORDINACION SOPORTE SOLUCIONES - Monitoreo diario`

## Tareas programadas

- `Compensar Monitoreo PASARELAS 09 / 13 / 17`
- `Compensar Monitoreo AWS 09 / 13 / 17`
- `Compensar Monitoreo HERCULES 09 / 13 / 17`
- `Compensar Monitoreo DIA_ANTERIOR`

## Instalación rápida

1. Ejecutar `INSTALAR.bat`
2. Ejecutar `CONFIGURAR_TAREAS.bat`
3. Abrir `ABRIR_MONITOREO.bat`
4. Guardar credenciales y sesiones desde la interfaz.
