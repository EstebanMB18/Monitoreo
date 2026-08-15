import pandas as pd
import re
from pathlib import Path
from bs4 import BeautifulSoup
from src.utils.limpieza import numero, normalizar_medio, limpiar_texto

PUBLIC_MARKERS = [
    'IR AL CONTENIDO PRINCIPAL', 'CLIENTES HABLEMOS', 'INTEGRA TODOS LOS CANALES',
    'WIX.COM WEBSITE BUILDER', 'PLANES MEDIOS DE PAGO BLOG', 'ASPXERRORPATH'
]
SIN_DATOS_MARKERS = [
    'NO SE ENCONTRARON DATOS', 'NO SE ENCUENTRAN DATOS',
    'NO SE ENCONTRARON REGISTROS', 'NO SE ENCONTRARON REGISTROS QUE CUMPLAN ESTE CRITERIO',
    'NO HAY REGISTROS', 'SIN DATOS'
]
OK_ESTADOS = ['OK', 'APROBADA', 'APROBADO', 'APPROVED']


def leer_texto_archivo(path, max_chars=None):
    data = Path(path).read_bytes()
    for enc in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']:
        try:
            txt = data.decode(enc, errors='ignore')
            return txt if max_chars is None else txt[:max_chars]
        except Exception:
            pass
    txt = data.decode('latin1', errors='ignore')
    return txt if max_chars is None else txt[:max_chars]


def archivo_publico_o_error(path):
    txt = limpiar_texto(leer_texto_archivo(path, 25000))
    return any(m in txt for m in PUBLIC_MARKERS)


def archivo_sin_datos(path):
    txt = limpiar_texto(leer_texto_archivo(path, 25000))
    return any(m in txt for m in SIN_DATOS_MARKERS)


def leer_csv_ecollect(path):
    mejores = []
    for enc in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']:
        for sep in [',', ';', '\t']:
            try:
                df = pd.read_csv(path, sep=sep, header=None, encoding=enc, dtype=str, engine='python', on_bad_lines='skip')
                if df.shape[1] > 5 and df.shape[0] > 0:
                    mejores.append((df.shape[1], df.shape[0], df))
            except Exception:
                pass
    if not mejores:
        return pd.DataFrame()
    mejores.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return mejores[0][2]


def inferir_columnas(df, tipo='RED'):
    tipo = str(tipo or '').upper()
    cols = set(df.columns)
    def tiene(col, opciones):
        if col not in cols:
            return False
        joined = ' | '.join(df[col].dropna().astype(str).map(limpiar_texto).head(100).tolist())
        return any(o in joined for o in opciones)

    if tipo == 'JAVA' or tiene(27, ['PSE', 'TARJ', 'AUTOSERVICIO', 'SAC', 'REDES']) or tiene(17, OK_ESTADOS + ['BANK', 'NOT_AUTHORIZED', 'EXPIRED']):
        return {'valor': 4 if 4 in cols else 2, 'estado': 17 if 17 in cols else 10, 'medio': 27 if 27 in cols else 23, 'fecha': 25 if 25 in cols else (13 if 13 in cols else None)}
    return {'valor': 2 if 2 in cols else 4, 'estado': 10 if 10 in cols else 17, 'medio': 23 if 23 in cols else 27, 'fecha': 18 if 18 in cols else (19 if 19 in cols else (7 if 7 in cols else None))}


def normalizar_celda_medio(x):
    t = limpiar_texto(x)
    if not t or t in ['NAN', 'NONE', '0', '0.0', '0.00']:
        return ''
    if t == 'TUP':
        return 'TUP'
    if t in ['PSE', 'PSE_AVANZA']:
        return 'PSE'
    if 'AUTOSERVICIO' in t:
        return 'MODULOS AUTOSERVICIO'
    if t in ['SAC', 'SAP', 'SAP5'] or 'SAC (COMPENSAR)' in t or 'SAP5' in t:
        return 'SAP'
    if t == 'REDES' or t == 'REDES /SAC':
        return 'REDES'
    if t == 'CUPOYA':
        return 'CUPOYA'
    if 'TARJ. CREDITO' in t or 'TARJETA_CREDITO' in t or 'TARJETA CREDITO' in t:
        return 'TARJETA_CREDITO'
    return ''


def detectar_estado_fila(row):
    estados_no_ok = {
        'BANK', 'NOT_AUTHORIZED', 'NOT AUTHORIZED', 'EXPIRED', 'CREATED',
        'DECLINED', 'REJECTED', 'FAILED', 'PENDING', 'ERROR', 'CANCELLED',
        'CANCELED', 'ABANDONED'
    }
    for x in row.values:
        t = limpiar_texto(x)
        if t in OK_ESTADOS:
            return t
    for x in row.values:
        t = limpiar_texto(x)
        if t in estados_no_ok:
            return t
    return ''




def clasificar_estado_resumen(estado):
    t = limpiar_texto(estado)
    if t in OK_ESTADOS:
        return 'OK'
    if 'EXPIRED' in t or 'VENCID' in t:
        return 'EXPIRED'
    if t in ['REJECTED', 'DECLINED', 'NOT_AUTHORIZED', 'NOT AUTHORIZED', 'BANK']:
        return 'RECHAZADA'
    if t in ['FAILED', 'ERROR', 'CANCELLED', 'CANCELED']:
        return 'FALLIDA'
    if t in ['CREATED', 'PENDING', 'ABANDONED']:
        return 'PENDIENTE'
    if not t:
        return 'SIN_ESTADO'
    return 'OTRA'


def detectar_medio_fila(row, medio_col=None):
    """Clasifica el medio de pago de una fila eCollect de forma tolerante a columnas corridas.

    Importante:
    - La selección de aprobadas se hace DESPUÉS por _estado = OK/APROBADA.
    - Para 41610 RED, eCollect puede mover el medio entre columnas vecinas.
    - "TUP", "Tarjeta Compensar", "Bolsillo Subsidio" y "Bolsillo Bonos" se consideran TUP.
    - Se revisan explícitamente la columna inferida y sus dos vecinas, además de toda la fila.
    """
    candidatos = []

    # Prioridad 1: columna de medio inferida y sus vecinas (las "dos columnas" que suelen moverse).
    if medio_col is not None:
        for idx in [medio_col - 1, medio_col, medio_col + 1]:
            if idx in row.index:
                candidatos.append(row.get(idx))

    # Prioridad 2: columnas conocidas del formato RED/JAVA y alrededores.
    for idx in [22, 23, 24, 25, 26, 27, 28, 8, 9]:
        if idx in row.index:
            candidatos.append(row.get(idx))

    # Prioridad 3: fila completa como defensa ante CSV con comas/desplazamientos.
    candidatos.extend(list(row.values))

    encontrados = []
    for x in candidatos:
        t = limpiar_texto(x)
        if not t:
            continue

        if (
            t == 'TUP'
            or 'TARJETA COMPENSAR' in t
            or 'TARJETA UNICA' in t
            or 'TARJETA ÚNICA' in t
            or 'BOLSILLO SUBSIDIO' in t
            or 'BOLSILLO BONOS' in t
        ):
            encontrados.append('TUP')
            continue

        # El código/autorizador 17 es una defensa adicional observada en estos CSV.
        if t == '17':
            encontrados.append('TUP')
            continue

        m = normalizar_celda_medio(x)
        if m:
            encontrados.append(m)

    # TUP debe ganar cuando la fila trae textos auxiliares que también contienen PSE/Tarjeta.
    for prioridad in [
        'TUP', 'MODULOS AUTOSERVICIO', 'SAP', 'REDES', 'CUPOYA',
        'PSE', 'TARJETA_CREDITO'
    ]:
        if prioridad in encontrados:
            return prioridad

    return ''

def detectar_fecha_fila(row, fecha_col=None):
    if fecha_col is not None and fecha_col in row.index:
        val = row.get(fecha_col)
        if limpiar_texto(val):
            return str(val)
    patron = re.compile(r'\d{1,2}/\d{1,2}/\d{4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]\.?M\.?)?)?', re.I)
    for x in row.values:
        s = '' if pd.isna(x) else str(x)
        if patron.search(s):
            return s
    return ''


def detectar_valor_fila(row, valor_col=None):
    if valor_col is not None and valor_col in row.index:
        return numero(row.get(valor_col))
    for idx in [2, 4, 3, 5]:
        if idx in row.index:
            v = numero(row.get(idx))
            if v:
                return v
    return 0.0


def resumir_desde_dataframe_tabular(df, medios, vertical, codigo, origen, tipo):
    cols = inferir_columnas(df, tipo)
    d = df.copy()
    valor_col = cols.get('valor')
    medio_col = cols.get('medio')
    fecha_col = cols.get('fecha')

    d['_estado'] = d.apply(lambda r: detectar_estado_fila(r), axis=1)
    d['_valor'] = d.apply(lambda r: detectar_valor_fila(r, valor_col), axis=1)
    d['_medio'] = d.apply(lambda r: detectar_medio_fila(r, medio_col), axis=1)
    d['_fecha'] = d.apply(lambda r: detectar_fecha_fila(r, fecha_col), axis=1)

    ok = d[d['_estado'].isin(OK_ESTADOS)].copy()
    out = []
    for m in medios:
        mn = normalizar_medio(m)
        sub = ok[ok['_medio'].eq(mn)]
        total = d[d['_medio'].eq(mn)]
        fall = total[~total['_estado'].isin(OK_ESTADOS)]
        clases = total['_estado'].map(clasificar_estado_resumen) if not total.empty else pd.Series(dtype=str)
        out.append({
            'vertical': vertical, 'codigo': codigo, 'origen': origen, 'tipo_reporte': tipo,
            'medio_pago': mn, 'medio_salida': m,
            'cantidad_ok': int(len(sub)), 'valor_ok': float(sub['_valor'].sum()),
            'ultima_ok': str(sub['_fecha'].max()) if not sub.empty else 'Sin aprobadas en el archivo actual',
            'cantidad_total': int(len(total)), 'cantidad_fallida': int(len(fall)),
            'conteo_expired': int((clases == 'EXPIRED').sum()),
            'conteo_rechazada': int((clases == 'RECHAZADA').sum()),
            'conteo_fallida_tecnica': int((clases == 'FALLIDA').sum()),
            'conteo_pendiente': int((clases == 'PENDIENTE').sum()),
            'conteo_otra': int((clases == 'OTRA').sum() + (clases == 'SIN_ESTADO').sum()),
        })
    return pd.DataFrame(out)


def resumir_ecollect(path, medios, vertical='', codigo='', origen='ECOLLECT', tipo='RED'):
    medios = list(medios)
    p = Path(path)
    if archivo_publico_o_error(p):
        return pd.DataFrame([fila_cero(vertical, codigo, tipo, m, 'Archivo público/error de sesión; no usar como dato') for m in medios])
    if archivo_sin_datos(p):
        return pd.DataFrame([fila_cero(vertical, codigo, tipo, m, 'Sin registros en eCollect') for m in medios])
    if p.suffix.lower() in ['.html', '.htm', '.txt']:
        return pd.DataFrame([fila_cero(vertical, codigo, tipo, m, 'HTML no usado como fuente; se requiere CSV') for m in medios])
    df = leer_csv_ecollect(p)
    if df.empty:
        return pd.DataFrame([fila_cero(vertical, codigo, tipo, m, 'CSV vacío/no leído') for m in medios])
    return resumir_desde_dataframe_tabular(df, medios, vertical, codigo, origen, tipo)


def fila_cero(vertical, codigo, tipo, m, motivo=''):
    return {'vertical': vertical, 'codigo': codigo, 'origen': 'ECOLLECT', 'tipo_reporte': tipo,
            'medio_pago': normalizar_medio(m), 'medio_salida': m, 'cantidad_ok': 0,
            'valor_ok': 0.0, 'ultima_ok': motivo or 'Sin aprobadas en el archivo actual',
            'cantidad_total': 0, 'cantidad_fallida': 0,
            'conteo_expired': 0, 'conteo_rechazada': 0, 'conteo_fallida_tecnica': 0,
            'conteo_pendiente': 0, 'conteo_otra': 0}
