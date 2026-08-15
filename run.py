from __future__ import annotations
import argparse
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.orchestrator import run_monitor, finalize


def _hay_procesos_previos():
    if os.name != "nt":
        return False
    ps = r"""
$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like '*ejecutar_paralelo.py*' -or
        $_.CommandLine -like '*pasarela_worker.py*' -or
        $_.CommandLine -like '*payu_worker.py*' -or
        $_.CommandLine -like '*monitores*aws*main.py*'
    )
}
if ($procs) { exit 10 } else { exit 0 }
"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return r.returncode == 10


def _esperar_previos(timeout_seg=1200):
    inicio = time.time()
    while _hay_procesos_previos():
        if time.time() - inicio >= timeout_seg:
            print("GENERAL NO PUBLICADO: Pasarelas/AWS aÃºn siguen activos.")
            return False
        print("Esperando Pasarelas/AWS antes de generar Dashboard General...")
        time.sleep(10)
    return True


def main():
    p = argparse.ArgumentParser(description="Monitoreo Compensar unificado")
    p.add_argument("--monitor", choices=["todos", "pasarelas", "aws", "hercules"], default="todos")
    p.add_argument("--modo", choices=["actual", "acumulado-hoy", "dia-anterior", "fecha"], default="actual")
    p.add_argument("--fecha")
    p.add_argument("--corte", choices=["09", "13", "17"], default="09")
    p.add_argument("--hora-inicio", default="00:00")
    p.add_argument("--hora-fin", default="23:59")
    p.add_argument("--no-finalize", action="store_true")
    a = p.parse_args()

    mons = ["PASARELAS", "AWS", "HERCULES"] if a.monitor == "todos" else [a.monitor.upper()]
    with ThreadPoolExecutor(max_workers=len(mons)) as ex:
        futs = [
            ex.submit(run_monitor, m, a.modo, a.corte, a.fecha, a.hora_inicio, a.hora_fin)
            for m in mons
        ]
        for f in as_completed(futs):
            f.result()

    if a.no_finalize:
        print("Monitor finalizado. Dashboard General pendiente hasta terminar el corte completo.")
        return

    if a.monitor == "hercules" and not _esperar_previos():
        return

    deleted, dash, excel = finalize()
    print(f"Limpieza={deleted}; dashboard={dash}; excel={excel}")


if __name__ == "__main__":
    main()
