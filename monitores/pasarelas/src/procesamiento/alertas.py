import pandas as pd
from src import config

def aplicar_alertas(df, corte='09'):
    prom_path=config.CONFIG / ('promedios_09.csv' if str(corte).startswith('09') or str(corte).lower().startswith('man') else 'promedios_17.csv')
    proms=pd.read_csv(prom_path) if prom_path.exists() else pd.DataFrame(columns=['vertical','medio_pago','promedio'])
    df=df.copy()
    df=df.merge(proms, left_on=['vertical','medio_salida'], right_on=['vertical','medio_pago'], how='left', suffixes=('','_prom'))
    df['promedio']=pd.to_numeric(df.get('promedio'), errors='coerce').fillna(0)
    def estado(r):
        if r.promedio < config.PROMEDIO_MINIMO_ALERTA:
            return 'NORMAL'
        if r.cantidad_ok == 0 and r.cantidad_total > 0 and r.cantidad_fallida >= r.promedio*0.25:
            return 'ALERTA'
        ratio = r.cantidad_ok / r.promedio if r.promedio else 1
        if ratio < config.UMBRAL_ALERTA: return 'ALERTA'
        if ratio < config.UMBRAL_BAJA: return 'BAJA TRANSACCIÓN'
        return 'NORMAL'
    df['estado']=df.apply(estado, axis=1)
    def obs(r):
        if r.estado=='ALERTA': return f'Por debajo del promedio de corte o posible afectación. Última OK: {r.ultima_ok}'
        if r.estado=='BAJA TRANSACCIÓN': return 'Transacción por debajo del promedio esperado para este corte.'
        return 'Comportamiento dentro de rango operativo.'
    df['observacion']=df.apply(obs, axis=1)
    return df
