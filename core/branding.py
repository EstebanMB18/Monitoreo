from pathlib import Path
CSS="""<style id="comp-brand">:root{--brand:#ED5123!important;--brandblue:#0057B8!important}body{font-family:Segoe UI,Arial,sans-serif!important;background:linear-gradient(135deg,#f6f9fc,#eef3f8 55%,#fff6ef)!important}.compbar{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;background:linear-gradient(120deg,#ED5123,#F46D3F);color:white;box-shadow:0 12px 28px rgba(237,81,35,.22)}.compbar b{font-size:20px}.compbar span{font-size:12px;opacity:.95}.kpi,.panel,.card,.monitor-card,.vcard,.state,.alert,.cap-board,.mini-panel{border-radius:20px!important;box-shadow:0 14px 34px rgba(31,52,75,.09)!important;border-color:#e2e9f1!important}th{background:#0057B8!important;color:white!important}</style>"""
BAR="<div class='compbar'><div><b>Compensar - Centro de Monitoreo</b><br><span>AWS - Pasarelas - Hercules</span></div><strong>MONITOREO OPERATIVO</strong></div>"
def brand(path:Path):
    if not path.exists(): return
    t=path.read_text(encoding='utf-8',errors='replace')
    if 'id="comp-brand"' in t: return
    if '</head>' in t: t=t.replace('</head>',CSS+'</head>',1)
    i=t.find('<body')
    if i>=0:
        j=t.find('>',i)
        if j>=0: t=t[:j+1]+BAR+t[j+1:]
    path.write_text(t,encoding='utf-8')
def apply_branding(root:Path):
    for p in [root/'GENERAL'/'Dashboard_General.html',root/'AWS'/'Dashboard_AWS.html',root/'ECOLLECT'/'dashboard_verticales.html',root/'HERCULES'/'dashboard_hercules.html',root/'HERCULES'/'DASHBOARD_HERCULES.html']: brand(p)
