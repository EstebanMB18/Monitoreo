from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.orchestrator import run_monitor, finalize


def main():
    p = argparse.ArgumentParser(description="Monitoreo Compensar unificado")
    p.add_argument("--monitor", choices=["todos", "pasarelas", "aws", "hercules"], default="todos")
    p.add_argument("--modo", choices=["actual", "acumulado-hoy", "dia-anterior", "fecha"], default="actual")
    p.add_argument("--fecha")
    p.add_argument("--corte", choices=["09", "13", "17"], default="09")
    p.add_argument("--hora-inicio", default="00:00")
    p.add_argument("--hora-fin", default="23:59")
    a = p.parse_args()
    mons = ["PASARELAS", "AWS", "HERCULES"] if a.monitor == "todos" else [a.monitor.upper()]
    with ThreadPoolExecutor(max_workers=len(mons)) as ex:
        futs = [ex.submit(run_monitor, m, a.modo, a.corte, a.fecha, a.hora_inicio, a.hora_fin) for m in mons]
        for f in as_completed(futs):
            f.result()
    deleted, dash, excel = finalize()
    print(f"Limpieza={deleted}; dashboard={dash}; excel={excel}")


if __name__ == "__main__":
    main()
