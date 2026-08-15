import pandas as pd
from pathlib import Path
from src.utils.limpieza import numero, normalizar_medio, limpiar_texto


def leer_payu(path):
    for enc in ['utf-8-sig', 'latin1', 'cp1252']:
        for sep in [';', ',']:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str)
                if df.shape[1] > 5:
                    return df
            except Exception:
                continue
    return pd.read_csv(path, dtype=str)


def resumir_payu(path, vertical='41621 RED TIENDA'):
    df = leer_payu(path)
    cols = {limpiar_texto(c): c for c in df.columns}
    estado_col = cols.get('ESTADO')
    medio_col = cols.get('MEDIO DE PAGO')
    valor_col = cols.get('VALOR TRANSACCIÓN') or cols.get('VALOR TRANSACCION')
    fecha_col = cols.get('FECHA DE CREACIÓN') or cols.get('FECHA DE CREACION') or cols.get('FECHA OPERACIÓN') or cols.get('FECHA OPERACION') or cols.get('FECHA ÚLTIMA ACTUALIZACIÓN') or cols.get('FECHA ULTIMA ACTUALIZACION')

    if not all([estado_col, medio_col, valor_col]):
        raise ValueError(f'No encontré columnas PayU esperadas. Columnas: {list(df.columns)}')

    d = df.copy()
    d['_estado'] = d[estado_col].map(limpiar_texto)
    d['_medio'] = d[medio_col].map(normalizar_medio)
    d['_valor'] = d[valor_col].map(numero)
    d['_fecha'] = d[fecha_col] if fecha_col else ''

    ok = d[d['_estado'].isin(['APPROVED', 'APROBADO', 'OK'])].copy()

    # Regla del usuario: PSE = PSE/PSE_AVANZA; TARJETA = todo lo aprobado restante.
    pse_ok = ok[ok['_medio'].eq('PSE')]
    tarjeta_ok = ok[~ok['_medio'].eq('PSE')]
    pse_total = d[d['_medio'].eq('PSE')]
    tarjeta_total = d[~d['_medio'].eq('PSE')]

    resultados = []
    for medio, etiqueta, sub_ok, sub_total in [
        ('PSE', 'PSE (PAYU)', pse_ok, pse_total),
        ('TARJETA_CREDITO', 'TARJ. CREDITO (PAYU)', tarjeta_ok, tarjeta_total),
    ]:
        resultados.append({
            'vertical': vertical,
            'codigo': '41621',
            'origen': 'PAYU',
            'tipo_reporte': 'PAYU',
            'medio_pago': medio,
            'medio_salida': etiqueta,
            'cantidad_ok': int(len(sub_ok)),
            'valor_ok': float(sub_ok['_valor'].sum()),
            'ultima_ok': str(sub_ok['_fecha'].max()) if not sub_ok.empty else 'Sin aprobadas en el archivo actual',
            'cantidad_total': int(len(sub_total)),
            'cantidad_fallida': int(len(sub_total) - len(sub_ok)),
        })
    return pd.DataFrame(resultados)
