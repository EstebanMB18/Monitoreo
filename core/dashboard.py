from __future__ import annotations
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path


def _esc(x):
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _load_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _mode_banner(now: datetime):
    wd = now.weekday()
    if wd >= 5:
        return {
            "title": "Modo fin de semana / festivo",
            "subtitle": "Vista resumida para compartir el consolidado y los enlaces principales.",
            "class": "weekend",
            "items": [
                "Compartir el dashboard general y verificar rápidamente los tres monitores.",
                "Usar los botones de detalle si necesitas bajar al nivel AWS, Pasarelas o Hércules.",
                "El movimiento mensual solo cuenta ejecuciones históricas validadas del día anterior.",
            ],
        }
    return {
        "title": "Modo entre semana",
        "subtitle": "Operación orientada a cortes 09 / 13 / 17 y seguimiento rápido por monitor.",
        "class": "weekday",
        "items": [
            "Revisar cortes programados y comparar el último estado de AWS, Pasarelas y Hércules.",
            "Abrir el detalle individual cuando una novedad requiera análisis puntual.",
            "El consolidado mensual no mezcla pruebas manuales ni monitoreos por hora del mismo día.",
        ],
    }


def _latest_by_monitor(exec_rows):
    latest = {}
    for row in exec_rows:
        latest[row.get("monitor", "")] = row
    return latest


def _pill_class(status: str):
    return "ok" if str(status).upper() == "OK" else "err"


def generate_dashboard(output_root: Path):
    general = output_root / "GENERAL"
    general.mkdir(parents=True, exist_ok=True)
    exec_rows = _load_csv(general / "historico_ejecuciones.csv")
    month_rows = _load_csv(general / "historico_mensual.csv")

    now = datetime.now()
    month = now.strftime("%Y-%m")
    monthly = [r for r in month_rows if str(r.get("fecha", "")).startswith(month)]
    ok = sum(1 for r in monthly if r.get("estado") == "OK")
    errors = sum(1 for r in monthly if r.get("estado") != "OK")
    by_monitor = Counter(r.get("monitor", "") for r in monthly)
    latest = _latest_by_monitor(exec_rows)
    recent_month = monthly[-15:][::-1]
    banner = _mode_banner(now)

    monitor_cards = []
    for m, title, link in [
        ("PASARELAS", "Pasarelas", "../ECOLLECT/dashboard_verticales.html"),
        ("AWS", "AWS", "../AWS/Dashboard_AWS.html"),
        ("HERCULES", "Hércules", "../HERCULES/dashboard_hercules.html"),
    ]:
        row = latest.get(m, {})
        st = row.get("estado", "Sin ejecución")
        monitor_cards.append(f"""
        <div class="monitor-card">
          <div class="monitor-top"><h3>{title}</h3><span class="pill {_pill_class(st)}">{_esc(st)}</span></div>
          <div class="monitor-meta">
            <div><b>Última fecha</b><span>{_esc(row.get('fecha', '-'))}</span></div>
            <div><b>Modo</b><span>{_esc(row.get('modo', '-'))}</span></div>
            <div><b>Detalle</b><span>{_esc(row.get('detalle', 'Aún no hay ejecución registrada'))}</span></div>
          </div>
          <div class="monitor-actions"><a href="{link}">Ver dashboard</a></div>
        </div>
        """)

    latest_html = "".join(
        "<tr>" + "".join(f"<td>{_esc(r.get(k,''))}</td>" for k in ["fecha","corte","monitor","modo","estado","duracion_seg","detalle"]) + "</tr>"
        for r in recent_month
    ) or '<tr><td colspan="7">Aún no hay ejecuciones históricas validadas del día anterior.</td></tr>'

    banner_items = "".join(f"<li>{_esc(item)}</li>" for item in banner["items"])
    cards = "".join(
        f'<div class="metric"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in [
            ("Pasarelas validadas", by_monitor.get("PASARELAS", 0)),
            ("AWS validadas", by_monitor.get("AWS", 0)),
            ("Hércules validadas", by_monitor.get("HERCULES", 0)),
            ("Ejecuciones OK", ok),
            ("Novedades", errors),
        ]
    )

    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Dashboard Monitoreo Compensar</title>
<style>
:root{{--orange:#f58220;--blue:#0057b8;--bg:#eef3f8;--ink:#182635;--soft:#6d7a88;--red:#d93636;--card:#ffffff;--shadow:0 18px 40px rgba(17,39,66,.10);}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:linear-gradient(135deg,#f6f9fc,#eef3f8 45%,#fef7ef);color:var(--ink)}}
header{{background:linear-gradient(120deg,var(--orange),#ff9d3c 65%,#ffd7aa);color:white;padding:28px 32px;box-shadow:0 14px 35px rgba(245,130,32,.24)}}
header .top{{display:flex;justify-content:space-between;gap:18px;align-items:center;flex-wrap:wrap}} h1{{margin:0;font-size:34px;letter-spacing:.3px}} .sub{{margin-top:6px;opacity:.96}}
.logo{{display:flex;align-items:center;gap:14px;background:rgba(255,255,255,.16);padding:12px 16px;border-radius:18px;backdrop-filter:blur(5px)}}
.logo .mark{{display:grid;grid-template-columns:repeat(2,18px);grid-template-rows:repeat(2,18px);gap:6px}} .logo .mark span{{display:block;width:18px;height:18px;background:#fff;border-radius:50%}} .logo .mark span:last-child{{grid-column:1/3;justify-self:center}}
.logo strong{{display:block;font-size:21px}} .logo small{{display:block;font-size:12px;opacity:.96}}
.wrap{{max-width:1650px;margin:auto;padding:22px}}
.metric-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:16px}} .metric{{background:var(--card);border-radius:22px;padding:18px;box-shadow:var(--shadow);border:1px solid #e3ebf3;position:relative;overflow:hidden}} .metric:before{{content:"";position:absolute;left:0;top:0;bottom:0;width:6px;background:var(--blue)}} .metric span{{display:block;color:var(--soft);font-size:13px;font-weight:700}} .metric strong{{display:block;margin-top:10px;font-size:34px;color:var(--blue)}}
.banner{{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;margin-bottom:18px}} .panel{{background:var(--card);border-radius:24px;padding:22px;box-shadow:var(--shadow);border:1px solid #e3ebf3}} .panel h2{{margin:0 0 8px;font-size:26px;color:#18385f}} .panel p{{margin:0 0 12px;color:var(--soft);line-height:1.5}} .panel ul{{margin:0;padding-left:18px;color:#415263;line-height:1.6}} .mode.weekday{{background:linear-gradient(135deg,#eef7ff,#ffffff)}} .mode.weekend{{background:linear-gradient(135deg,#fff7ec,#ffffff)}}
.monitor-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:18px}} .monitor-card{{background:linear-gradient(145deg,#ffffff,#f8fbff);border:1px solid #e3ebf3;border-radius:24px;padding:20px;box-shadow:var(--shadow)}} .monitor-top{{display:flex;justify-content:space-between;align-items:center;gap:10px}} .monitor-top h3{{margin:0;font-size:22px;color:#0f3864}} .monitor-meta{{display:grid;gap:10px;margin-top:14px}} .monitor-meta div{{background:#f7fbff;border:1px solid #e6eef6;border-radius:16px;padding:12px}} .monitor-meta b{{display:block;font-size:12px;color:var(--soft);margin-bottom:4px;text-transform:uppercase;letter-spacing:.04em}} .monitor-meta span{{font-size:14px;line-height:1.4}} .monitor-actions{{margin-top:14px}} .monitor-actions a,.report-links a{{display:inline-block;padding:10px 14px;border-radius:999px;background:var(--blue);color:white;text-decoration:none;font-weight:700;box-shadow:0 10px 24px rgba(0,87,184,.18)}}
.report-links a{{margin-right:8px;margin-top:8px}} .pill{{display:inline-block;padding:6px 10px;border-radius:999px;font-size:12px;font-weight:800}} .pill.ok{{background:#e5f6d8;color:#2e7d1e}} .pill.err{{background:#fee4e4;color:var(--red)}}
.table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse;font-size:13px}} th{{background:#edf4fb;color:#23466c;text-align:left}} th,td{{padding:10px;border-bottom:1px solid #e7edf5;vertical-align:top}} tr:nth-child(even) td{{background:#fbfdff}}
.note{{font-size:13px;color:var(--soft)}}
@media(max-width:1200px){{.metric-grid{{grid-template-columns:1fr 1fr 1fr}} .banner,.monitor-grid{{grid-template-columns:1fr}}}}
@media(max-width:700px){{.metric-grid{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<header><div class="top"><div><h1>Centro de Monitoreo Compensar</h1><div class="sub">Dashboard general unificado · {now:%d/%m/%Y %H:%M}</div></div><div class="logo"><div class="mark"><span></span><span></span><span></span></div><div><strong>Compensar</strong><small>AWS · Pasarelas · Hércules</small></div></div></div></header>
<div class="wrap">
  <section class="metric-grid">{cards}</section>
  <section class="banner">
    <div class="panel mode {banner['class']}"><h2>{_esc(banner['title'])}</h2><p>{_esc(banner['subtitle'])}</p><ul>{banner_items}</ul></div>
    <div class="panel report-links"><h2>Accesos rápidos</h2><p>Detalle individual y archivos oficiales compartidos.</p><a href="../AWS/Dashboard_AWS.html">AWS</a><a href="../ECOLLECT/dashboard_verticales.html">Pasarelas</a><a href="../HERCULES/dashboard_hercules.html">Hércules</a></div>
  </section>
  <section class="monitor-grid">{''.join(monitor_cards)}</section>
  <section class="panel"><h2>Movimiento mensual validado</h2><p class="note">Aquí solo aparecen ejecuciones históricas validadas del proceso de día anterior. Los cortes del mismo día y las pruebas manuales se registran aparte en la bitácora técnica para no contaminar el acumulado.</p><div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Corte</th><th>Monitor</th><th>Modo</th><th>Estado</th><th>Duración s</th><th>Detalle</th></tr></thead><tbody>{latest_html}</tbody></table></div></section>
</div></body></html>"""
    path = general / "Dashboard_General.html"
    path.write_text(html, encoding="utf-8")
    return path
