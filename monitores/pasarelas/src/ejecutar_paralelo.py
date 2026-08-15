
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import config
from src.main import procesar_archivos, cargar_verticales, rango_hoy

SLOW = {("41605", "JAVA"), ("41610", "RED")}


def _fecha_range(fecha: str | None, corte: str, modo: str, hora_inicio: str = "00:00", hora_fin: str = "23:59"):
    if modo == "acumulado-hoy":
        now = datetime.now()
        return now.strftime("%d/%m/%Y 00:00"), now.strftime("%d/%m/%Y %H:%M")
    if modo == "dia-anterior":
        d = datetime.now() - timedelta(days=1)
        return d.strftime(f"%d/%m/%Y {hora_inicio}"), d.strftime(f"%d/%m/%Y {hora_fin}")
    if modo == "fecha":
        if not fecha:
            raise SystemExit("--fecha es obligatorio en modo fecha")
        d = datetime.strptime(fecha, "%Y-%m-%d")
        return d.strftime(f"%d/%m/%Y {hora_inicio}"), d.strftime(f"%d/%m/%Y {hora_fin}")
    return rango_hoy(corte)


def _copy_state(name: str) -> str:
    src = config.STORAGE / "ecollect_session.json"
    dst = config.STORAGE / f"ecollect_session_{name}.json"
    if src.exists():
        shutil.copy2(src, dst)
    return str(dst)


def _worker_cmd(items, fi, ff, worker_name, visible):
    # Use a dedicated process so one slow query never blocks the other workers.
    script = ROOT / "src" / "pasarela_worker.py"
    item_text = ",".join(f"{c}:{t}" for c, t in items)
    env = os.environ.copy()
    env["HEADLESS"] = "false" if visible else "true"
    env["ECOLLECT_STATE_PATH"] = _copy_state(worker_name)
    env["PYTHONPATH"] = str(ROOT)
    cmd = [
        sys.executable, str(script),
        "--items", item_text,
        "--fecha-inicio", fi,
        "--fecha-fin", ff,
        "--worker", worker_name,
    ]
    return cmd, env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["actual", "acumulado-hoy", "dia-anterior", "fecha"], default="actual")
    ap.add_argument("--fecha")
    ap.add_argument("--corte", choices=["09", "13", "17"], default="09")
    ap.add_argument("--hora-inicio", default="00:00")
    ap.add_argument("--hora-fin", default="23:59")
    args = ap.parse_args()

    # Clean only temporary downloads before the run. History/monthly is never touched.
    for p in config.DESCARGAS.glob("*"):
        if p.is_file():
            try: p.unlink()
            except OSError: pass

    fi, ff = _fecha_range(args.fecha, args.corte, args.modo, args.hora_inicio, args.hora_fin)
    verticales = cargar_verticales()
    eco_items = verticales[verticales.origen.eq("ECOLLECT")][["codigo","tipo_reporte"]].drop_duplicates()
    all_items = [(str(r.codigo), str(r.tipo_reporte).upper()) for r in eco_items.itertuples(index=False)]

    fast_items = [x for x in all_items if x not in SLOW]
    workers = []

    # PayU starts immediately in its own process.
    payu = subprocess.Popen(
        [sys.executable, str(ROOT / "src" / "payu_worker.py"),
         "--fecha-inicio", fi, "--fecha-fin", ff],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    workers.append(("PAYU", payu))

    # Fast eCollect batch continues headless.
    if fast_items:
        cmd, env = _worker_cmd(fast_items, fi, ff, "fast", visible=False)
        workers.append(("ECOLLECT_RAPIDO", subprocess.Popen(cmd, cwd=str(ROOT), env=env)))

    # Slow workers get their own visible browser and independent process.
    for codigo, tipo in sorted(SLOW):
        if (codigo, tipo) in all_items:
            name = f"{codigo}_{tipo}"
            cmd, env = _worker_cmd([(codigo, tipo)], fi, ff, name, visible=True)
            workers.append((name, subprocess.Popen(cmd, cwd=str(ROOT), env=env)))

    print("\nTrabajos iniciados en paralelo:")
    for name, proc in workers:
        print(f"  - {name}: PID {proc.pid}")
    print("Los lentos 41605 JAVA y 41610 RED quedan visibles sin frenar PayU ni el resto de eCollect.\n")

    failed = []
    for name, proc in workers:
        rc = proc.wait()
        print(f"{name}: finalizado con código {rc}")
        if rc != 0:
            failed.append(name)

    # Build one consolidated result from whatever was downloaded successfully.
    df, html, excel = procesar_archivos(corte=args.corte)
    print(f"\nConsolidado Pasarelas: {html}\nExcel: {excel}")
    if failed:
        print("ADVERTENCIA: workers con error: " + ", ".join(failed))
        # Do not hide partial data; caller can see warning while other results remain usable.


if __name__ == "__main__":
    main()
