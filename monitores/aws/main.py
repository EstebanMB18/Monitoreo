from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "src"))

from monitoreo_aws.core.alerts import evaluar
from monitoreo_aws.core.windows import obtener_ventana
from monitoreo_aws.demo import datos_demo
from monitoreo_aws.reports.excel import generar_excel
from monitoreo_aws.reports.html import generar_html
from monitoreo_aws.services.collector import recolectar


def _ruta_oficial(cfg: dict) -> Path:
    """Resuelve y crea la carpeta oficial de OneDrive configurada."""
    raw = str(cfg["app"].get("salida_oficial", "")).strip()
    if not raw:
        raise RuntimeError("No está configurada app.salida_oficial en config/config.yaml.")

    output_dir = Path(os.path.expandvars(raw)).expanduser()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"No fue posible crear o usar la carpeta oficial: {output_dir}. "
            "Verifica que OneDrive esté conectado y que tengas permisos."
        ) from exc
    return output_dir


def _reemplazar_archivo(temporal: Path, destino: Path) -> None:
    """Reemplaza el archivo oficial sin acumular versiones anteriores."""
    try:
        temporal.replace(destino)
    except PermissionError as exc:
        raise RuntimeError(
            f"No fue posible reemplazar {destino.name}. Cierra el archivo si está abierto "
            "en Excel, Chrome o Edge y vuelve a ejecutar el monitoreo."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitoreo AWS automático")
    parser.add_argument("--corte", default="auto", choices=["auto", "1", "2", "3", "dia", "rango"])
    parser.add_argument("--fecha", help="YYYY-MM-DD")
    parser.add_argument("--hora-inicio", default="00:00", help="HH:MM para rango histórico")
    parser.add_argument("--hora-fin", default="23:59", help="HH:MM para rango histórico")
    parser.add_argument("--demo", action="store_true", help="Genera reportes sin conectarse a AWS")
    parser.add_argument("--no-abrir", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load((BASE / "config/config.yaml").read_text(encoding="utf-8"))
    ventana = obtener_ventana(args.corte, args.fecha, cfg["app"]["timezone"], args.hora_inicio, args.hora_fin)
    print(f"Monitoreando: {ventana.nombre}\nRango: {ventana.texto}")

    data = datos_demo() if args.demo else recolectar(cfg, ventana)
    alertas = evaluar(cfg, ventana, data)
    stamp = f"{ventana.fin:%Y-%m-%d}_corte_{ventana.corte}"

    if args.demo:
        # La demostración permanece separada y no modifica el tablero oficial.
        excel_path = BASE / f"salida/demo/excel/aws_reporte_demo_{stamp}.xlsx"
        html_path = BASE / f"salida/demo/html/aws_reporte_demo_{stamp}.html"
        excel = generar_excel(excel_path, cfg, ventana, data, alertas)
        html = generar_html(html_path, cfg, ventana, data, alertas)
    else:
        # Los reportes reales usan nombres fijos y se sobrescriben en cada ejecución.
        output_dir = _ruta_oficial(cfg)
        excel_path = output_dir / cfg["app"].get("nombre_excel_oficial", "Monitoreo_AWS.xlsx")
        html_path = output_dir / cfg["app"].get("nombre_html_oficial", "Dashboard_AWS.html")

        # Se generan temporales en la misma carpeta y luego se reemplazan de forma segura.
        excel_tmp = output_dir / ".Monitoreo_AWS.tmp.xlsx"
        html_tmp = output_dir / ".Dashboard_AWS.tmp.html"
        generar_excel(excel_tmp, cfg, ventana, data, alertas)
        generar_html(html_tmp, cfg, ventana, data, alertas)
        _reemplazar_archivo(excel_tmp, excel_path)
        _reemplazar_archivo(html_tmp, html_path)
        excel, html = excel_path, html_path

    print(f"Excel: {excel}\nHTML: {html}\nAlertas: {len(alertas)}")
    print("Los archivos oficiales se reemplazan en cada monitoreo; no se acumulan versiones.")

    if cfg["app"].get("abrir_html_al_final", True) and not args.no_abrir:
        webbrowser.open(html.as_uri())


if __name__ == "__main__":
    main()
