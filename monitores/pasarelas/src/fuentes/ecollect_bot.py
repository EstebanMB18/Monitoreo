import os
import csv
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from src import config

load_dotenv(config.ROOT / '.env')

ECOLLECT_USER = os.getenv('ECOLLECT_USER', '')
ECOLLECT_PASSWORD = os.getenv('ECOLLECT_PASSWORD', '')

URL_RED = 'https://www.e-collect.com/app_express/admin/payreport.aspx'
URL_JAVA = 'https://www.e-collect.com/app_express/admin/payreportJ.aspx'
SELECTOR_ENTIDAD = '#ctl00_lstEntidades'


def _state_path():
    override = os.getenv('ECOLLECT_STATE_PATH', '').strip()
    return Path(override) if override else (config.STORAGE / 'ecollect_session.json')


def diagnostico(page, nombre):
    """Guarda HTML y screenshot cuando eCollect queda en una pantalla inesperada."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    base = config.LOGS / f'{nombre}_{ts}'
    try:
        (base.with_suffix('.html')).write_text(page.content(), encoding='utf-8', errors='ignore')
    except Exception:
        pass
    try:
        page.screenshot(path=str(base.with_suffix('.png')), full_page=True)
    except Exception:
        pass
    return str(base)


def cerrar_modal_publicidad(page):
    """eCollect a veces muestra promoción sin X visible; se cierra con clic en zona gris."""
    try:
        for _ in range(6):
            if page.locator('#modalNotify, #modalImage, .modal-body, .modal-content, .modal-backdrop').count() > 0:
                page.mouse.click(80, 80)
                page.wait_for_timeout(1000)
            else:
                break
    except Exception:
        pass




def es_sitio_publico_o_fuera_admin(page):
    """Detecta cuando eCollect redirecciona al sitio público/landing y no al administrador."""
    try:
        txt = page.locator('body').inner_text(timeout=2500).upper()
        url = page.url.lower()
    except Exception:
        return False
    señales_publicas = [
        'IR AL CONTENIDO PRINCIPAL', 'CLIENTES HABLEMOS', 'INTEGRA TODOS LOS CANALES',
        'PLANES', 'MEDIOS DE PAGO', 'BLOG'
    ]
    return any(x in txt for x in señales_publicas) or ('/app_express/admin/' not in url and 'e-collect.com' in url)


def cerrar_calendarios(page):
    """Cierra calendarios flotantes que quedan encima del botón Consultar."""
    try:
        page.keyboard.press('Escape')
        page.mouse.click(20, 20)
        page.evaluate("""
            () => {
                document.querySelectorAll('[id*=calendar], [id*=Calendar], [id*=caltxt], .ajax__calendar').forEach(e => {
                    e.style.display = 'none';
                    e.style.visibility = 'hidden';
                });
            }
        """)
    except Exception:
        pass




def formulario_reporte_listo(page):
    """Detecta el formulario real de reporte eCollect ASP.NET, incluyendo JAVA/RED."""
    try:
        return page.locator(
            '#adm_payreport1_btnGetreport, '
            'input[name="adm_payreport1$btnGetreport"], '
            '#adm_payreport1_txtfromDate, '
            'input[name="adm_payreport1$txtfromDate"]'
        ).count() > 0
    except Exception:
        return False


def es_pagina_admin_vacia(page):
    """Pantalla bug de eCollect: cabecera admin visible, pero sin entidades/contenido real."""
    try:
        body = page.locator('body').inner_text(timeout=2000).upper()
    except Exception:
        return False
    return ('MÓDULO ADMINISTRATIVO' in body or 'MODULO ADMINISTRATIVO' in body) and 'MENÚ PRINCIPAL' in body and 'SALIR' in body and not formulario_reporte_listo(page) and page.locator(SELECTOR_ENTIDAD).count() == 0

def asegurar_admin_real(page):
    """Si caímos al sitio público o a una sesión incompleta, vuelve al admin y reintenta login."""
    if es_sitio_publico_o_fuera_admin(page):
        print('eCollect: detecté sitio público/landing. Volviendo al módulo administrativo...')
        page.goto(config.ECOLLECT_URL, wait_until='domcontentloaded', timeout=90000)
        page.wait_for_timeout(2500)
        cerrar_modal_publicidad(page)
        login_si_necesario(page)
        cerrar_modal_publicidad(page)
    if esta_pantalla_vacia_o_sin_entidades(page):
        salir_y_relogin(page)


def login_si_necesario(page):
    cerrar_modal_publicidad(page)
    password_selector = '#Adm_users1_AccordionPane1_content_txtPasswodLogin'
    tiene_pass = page.locator(password_selector).count() > 0 or page.locator('input[type="password"]').count() > 0
    if not tiene_pass:
        return
    if not config.LOGIN_AUTOMATICO:
        input('Login automático desactivado. Inicia sesión y presiona ENTER...')
        return
    if not ECOLLECT_USER or not ECOLLECT_PASSWORD:
        raise RuntimeError('Faltan ECOLLECT_USER / ECOLLECT_PASSWORD en .env')
    print('eCollect: login automático...')
    user_selectors = [
        '#Adm_users1_AccordionPane1_content_txtLogin',
        '#Adm_users1_AccordionPane1_content_txtUserLogin',
        '#Adm_users1_AccordionPane1_content_txtEmailLogin',
        'input[type="email"]',
        'input[type="text"]',
    ]
    usuario_puesto = False
    for sel in user_selectors:
        try:
            if page.locator(sel).count() > 0 and page.locator(sel).first.is_visible():
                page.locator(sel).first.fill(ECOLLECT_USER)
                usuario_puesto = True
                break
        except Exception:
            pass
    if not usuario_puesto:
        try:
            page.locator('input[type="text"]').first.fill(ECOLLECT_USER)
        except Exception:
            pass

    if page.locator(password_selector).count() > 0:
        page.locator(password_selector).fill(ECOLLECT_PASSWORD)
    else:
        page.locator('input[type="password"]').first.fill(ECOLLECT_PASSWORD)

    clicked = False
    for txt in ['Ingresar', 'Entrar', 'Login', 'Aceptar']:
        try:
            btn = page.get_by_role('button', name=re.compile(txt, re.I))
            if btn.count() > 0:
                btn.first.click()
                clicked = True
                break
        except Exception:
            pass
    if not clicked:
        page.keyboard.press('Enter')
    page.wait_for_load_state('domcontentloaded', timeout=90000)
    page.wait_for_timeout(3500)
    cerrar_modal_publicidad(page)


def esta_pantalla_vacia_o_sin_entidades(page):
    """Detecta la pantalla rara de eCollect: se ve Módulo Administrativo, pero no carga entidades ni menú."""
    try:
        html = page.content().upper()
        body = page.locator('body').inner_text(timeout=2000).upper()
    except Exception:
        return False
    sin_combo = page.locator(SELECTOR_ENTIDAD).count() == 0
    menu_vacio = ('ID="CONT" STYLE="DISPLAY: NONE;"' in html or 'ID="CONT"' in html) and 'REPORTE TRANSACCIONES' not in body
    sin_contenido = 'MENÚ PRINCIPAL' in body and 'SALIR' in body and 'REPORTE TRANSACCIONES' not in body and 'USUARIOS ADMINISTRADORES' not in body
    return sin_combo and (menu_vacio or sin_contenido)


def salir_y_relogin(page):
    """Fuerza salida cuando eCollect queda en sesión rara sin entidades, y vuelve a ingresar."""
    print('eCollect: pantalla sin entidades. Forzando Salir y nuevo login...')
    try:
        link = page.get_by_role('link', name=re.compile('Salir', re.I))
        if link.count() > 0:
            link.first.click()
        else:
            page.locator('a[href*="LinkQuit"], a:has-text("Salir")').first.click()
        page.wait_for_load_state('domcontentloaded', timeout=90000)
        page.wait_for_timeout(2500)
    except Exception:
        try:
            page.goto(config.ECOLLECT_URL, wait_until='domcontentloaded', timeout=90000)
        except Exception:
            pass
    cerrar_modal_publicidad(page)
    login_si_necesario(page)
    cerrar_modal_publicidad(page)
    page.wait_for_timeout(4000)


def asegurar_inicio(page):
    """
    Deja eCollect en la pantalla principal con el combo de entidades disponible.
    Si eCollect queda en la pantalla vacía de 'Módulo Administrativo' sin entidades,
    fuerza Salir y hace login nuevamente. Esto corrige la sesión incompleta.
    """
    limite_ms = config.ECOLLECT_SELECTOR_TIMEOUT_SEGUNDOS * 1000
    paso_ms = 1000
    transcurrido = 0
    relogin_hecho = False

    page.goto(config.ECOLLECT_URL, wait_until='domcontentloaded', timeout=90000)
    page.wait_for_timeout(2500)

    while transcurrido < limite_ms:
        try:
            cerrar_modal_publicidad(page)
            login_si_necesario(page)
            cerrar_modal_publicidad(page)

            if page.locator(SELECTOR_ENTIDAD).count() > 0:
                try:
                    page.locator(SELECTOR_ENTIDAD).wait_for(state='attached', timeout=5000)
                except Exception:
                    pass
                return True

            # Caso real detectado: Módulo Administrativo visible, pero menú/entidades vacíos.
            # En esa pantalla toca salir y volver a iniciar; si no, nunca aparece ctl00_lstEntidades.
            if esta_pantalla_vacia_o_sin_entidades(page) and not relogin_hecho:
                salir_y_relogin(page)
                relogin_hecho = True
                transcurrido = 0
                continue

            # Si aparece login luego de salir o de expirar sesión, loguear.
            if page.locator('input[type="password"]').count() > 0:
                login_si_necesario(page)
                page.wait_for_timeout(3500)
                continue

        except Exception:
            pass

        if transcurrido and transcurrido % 60000 == 0:
            print(f'  esperando pantalla principal eCollect: {transcurrido//1000}s...')

        page.wait_for_timeout(paso_ms)
        transcurrido += paso_ms

    base = diagnostico(page, 'ecollect_sin_combo_entidades')
    raise RuntimeError(f'No apareció el combo de entidades {SELECTOR_ENTIDAD}. Guardé diagnóstico en {base}.html/.png')

def seleccionar_entidad(page, codigo):
    asegurar_inicio(page)
    asegurar_admin_real(page)
    # Selección normal. Si Playwright se queja por visibilidad, usamos JS como respaldo.
    try:
        page.locator(SELECTOR_ENTIDAD).select_option(str(codigo), timeout=30000)
    except Exception:
        page.eval_on_selector(
            SELECTOR_ENTIDAD,
            "(el, value) => { el.value = value; el.dispatchEvent(new Event('change', {bubbles:true})); }",
            str(codigo),
        )
    page.wait_for_load_state('domcontentloaded', timeout=90000)
    page.wait_for_timeout(2200)
    asegurar_admin_real(page)


def ir_reporte(page, tipo):
    url = URL_JAVA if str(tipo).upper() == 'JAVA' else URL_RED
    page.goto(url, wait_until='domcontentloaded', timeout=90000)
    page.wait_for_timeout(2500)
    cerrar_modal_publicidad(page)
    asegurar_admin_real(page)

    # Esperar a que el formulario ASP.NET real cargue.
    for i in range(60):
        try:
            cerrar_modal_publicidad(page)
            if es_sitio_publico_o_fuera_admin(page):
                print('eCollect: redirigió al sitio público. Reabriendo reporte admin...')
                page.goto(url, wait_until='domcontentloaded', timeout=90000)
                page.wait_for_timeout(2500)
            if formulario_reporte_listo(page):
                return True
            if es_pagina_admin_vacia(page):
                salir_y_relogin(page)
                page.goto(url, wait_until='domcontentloaded', timeout=90000)
                page.wait_for_timeout(2500)
        except Exception:
            pass
        page.wait_for_timeout(2000)
    base = diagnostico(page, f'ecollect_reporte_no_cargo_{tipo}')
    raise RuntimeError(f'No cargó el formulario de reporte {tipo}. Diagnóstico: {base}.html/.png')

def llenar_fechas(page, fecha_inicio, fecha_fin):
    """
    eCollect recibe fechas dd/MM/yyyy en estos reportes. No se debe meter hora en los campos,
    porque el calendario viejo queda abierto y puede tapar el botón Consultar.
    """
    fi = str(fecha_inicio).split()[0]
    ff = str(fecha_fin).split()[0]

    pares = [
        ('#adm_payreport1_txtfromDate', fi),
        ('#adm_payreport1_txtToDate', ff),
        ('input[name="adm_payreport1$txtfromDate"]', fi),
        ('input[name="adm_payreport1$txtToDate"]', ff),
    ]

    usados = 0
    for sel, val in pares:
        try:
            if page.locator(sel).count() > 0:
                page.eval_on_selector(sel, """
                    (el, value) => {
                        el.value = value;
                        el.dispatchEvent(new Event('input', {bubbles:true}));
                        el.dispatchEvent(new Event('change', {bubbles:true}));
                        el.blur();
                    }
                """, val)
                usados += 1
        except Exception:
            pass

    # Respaldo: si los IDs cambian, llenar los dos primeros inputs visibles de fecha.
    if usados < 2:
        visibles = []
        locs = page.locator('input[type="text"], input')
        try:
            total = min(locs.count(), 40)
        except Exception:
            total = 0
        for i in range(total):
            try:
                inp = locs.nth(i)
                if inp.is_visible() and inp.is_enabled():
                    ident = ((inp.get_attribute('id') or '') + ' ' + (inp.get_attribute('name') or '')).lower()
                    if 'date' in ident or 'fecha' in ident or 'txtfrom' in ident or 'txtto' in ident:
                        visibles.append(inp)
            except Exception:
                pass
        for inp, val in zip(visibles[:2], [fi, ff]):
            try:
                inp.fill(val)
                inp.evaluate("el => { el.dispatchEvent(new Event('change', {bubbles:true})); el.blur(); }")
            except Exception:
                pass

    cerrar_calendarios(page)
    try:
        page.locator('body').click(position={'x': 20, 'y': 20}, timeout=2000)
    except Exception:
        pass
    cerrar_calendarios(page)
    page.wait_for_timeout(700)

def click_consultar(page):
    """Clic robusto para páginas ASP.NET viejas de eCollect.
    Primero usa JavaScript directo porque los calendarios flotantes pueden tapar el botón.
    """
    cerrar_calendarios(page)
    try:
        page.locator('body').click(position={'x': 20, 'y': 20}, timeout=2000)
    except Exception:
        pass
    cerrar_calendarios(page)
    page.wait_for_timeout(700)

    # Método principal: DOM directo por ID/nombre real confirmado en diagnóstico.
    try:
        ok = page.evaluate("""
            () => {
                const btn = document.querySelector('#adm_payreport1_btnGetreport, input[name="adm_payreport1$btnGetreport"], input[value="Consultar"]');
                if (!btn) return false;
                btn.disabled = false;
                btn.removeAttribute('disabled');
                btn.scrollIntoView({block:'center'});
                btn.click();
                return true;
            }
        """)
        if ok:
            page.wait_for_timeout(1500)
            return True
    except Exception:
        pass

    selectores = [
        '#adm_payreport1_btnGetreport',
        'input[name="adm_payreport1$btnGetreport"]',
        'input[value="Consultar"]',
        'button:has-text("Consultar")',
        'a:has-text("Consultar")',
    ]
    for sel in selectores:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                try:
                    loc.first.scroll_into_view_if_needed(timeout=5000)
                except Exception:
                    pass
                loc.first.click(timeout=20000, force=True)
                page.wait_for_timeout(1500)
                return True
        except Exception:
            pass

    # Último recurso: submit del formulario ASP.NET.
    try:
        ok = page.evaluate("""
            () => {
                const f = document.querySelector('form');
                if (!f) return false;
                if (typeof __doPostBack === 'function') {
                    const btn = document.querySelector('#adm_payreport1_btnGetreport');
                    if (btn) { btn.click(); return true; }
                }
                f.submit();
                return true;
            }
        """)
        page.wait_for_timeout(1500)
        return bool(ok)
    except Exception:
        return False

def leer_texto_body(page):
    """Lee el texto visible de forma más robusta que locator('body').inner_text.
    En eCollect ASP.NET a veces inner_text por locator falla aunque la tabla ya esté pintada.
    """
    try:
        txt = page.evaluate("""
            () => {
                if (!document || !document.body) return '';
                return (document.body.innerText || document.body.textContent || '');
            }
        """)
        return (txt or '').upper()
    except Exception:
        try:
            return page.locator('body').inner_text(timeout=2500).upper()
        except Exception:
            return ''


def hay_tabla_con_resultados(page):
    """Detecta resultados reales del reporte eCollect.
    No depende solo del texto; valida la tabla y filas del reporte.
    """
    try:
        return bool(page.evaluate("""
            () => {
                const txt = (document.body && (document.body.innerText || document.body.textContent) || '').toUpperCase();
                if (txt.includes('TOTAL MONTO') || txt.includes('TOTAL TRANSACCIONES')) return true;
                if (txt.includes('# TRANS') && txt.includes('FECHA / HORA') && txt.includes('ESTADO')) return true;
                const rows = Array.from(document.querySelectorAll('table tr'));
                return rows.some(r => {
                    const t = (r.innerText || '').toUpperCase();
                    return t.includes('# TRANS') && t.includes('VALOR') && t.includes('ESTADO');
                });
            }
        """))
    except Exception:
        return False

def hay_mensaje_sin_datos(page):
    """Detecta rápido la respuesta roja de eCollect 'No se encontraron registros...'."""
    try:
        return bool(page.evaluate("""
            () => {
                const txt = (document.body && (document.body.innerText || document.body.textContent) || '').toUpperCase();
                return txt.includes('NO SE ENCONTRARON REGISTROS')
                    || txt.includes('NO SE ENCONTRARON DATOS')
                    || txt.includes('NO SE ENCUENTRAN DATOS')
                    || txt.includes('NO HAY REGISTROS');
            }
        """))
    except Exception:
        return False


def esperar_resultado(page, codigo='', tipo=''):

    """
    Espera una sola consulta hasta que eCollect termine.
    No vuelve a dar clic en Consultar.

    v7.7:
    - Detecta tabla real con JavaScript aunque Playwright no pueda leer body.inner_text.
    - Si ve Total Monto / Total Transacciones / # TRANS => DATOS.
    - Si ve 'No se encontraron registros que cumplan este criterio' => SIN_DATOS.
    - Si la tabla aparece tarde, no marca timeout por texto vacío.
    """
    limite_ms = config.TIMEOUT_CARGA_SEGUNDOS * 1000
    paso_ms = 1000
    transcurrido = 0
    esperado = ['TOTAL MONTO', 'TOTAL TRANSACCIONES', '# TRANS', '# CONFIRMACION', '# CONFIRMACIÓN', 'FECHA / HORA']
    sin_datos = [
        'NO SE ENCONTRARON DATOS',
        'NO SE ENCUENTRAN DATOS',
        'NO SE ENCONTRARON REGISTROS',
        'NO SE ENCONTRARON REGISTROS QUE CUMPLAN ESTE CRITERIO',
        'NO HAY REGISTROS',
    ]
    ultimo_texto = ''
    sin_datos_desde = None
    espera_sin_datos_ms = int(os.getenv('ECOLLECT_ESPERA_SIN_DATOS_SEGUNDOS', '1')) * 1000

    while transcurrido < limite_ms:
        try:
            if es_sitio_publico_o_fuera_admin(page):
                txt_publico = leer_texto_body(page)
                return 'FUERA_ADMIN:' + txt_publico[:250].replace('\n', ' ')

            if hay_mensaje_sin_datos(page):
                if sin_datos_desde is None:
                    sin_datos_desde = transcurrido
                    print(f'  {codigo} {tipo}: eCollect respondió sin registros; confirmando {espera_sin_datos_ms//1000}s...')
                elif transcurrido - sin_datos_desde >= espera_sin_datos_ms:
                    return 'SIN_DATOS'

            if hay_tabla_con_resultados(page):
                return 'DATOS'

            txt = leer_texto_body(page)
            ultimo_texto = txt[:5000]

            if any(x in txt for x in esperado):
                return 'DATOS'

            if any(x in txt for x in sin_datos):
                if sin_datos_desde is None:
                    sin_datos_desde = transcurrido
                    print(f'  {codigo} {tipo}: eCollect respondió sin registros; confirmando {espera_sin_datos_ms//1000}s...')
                elif transcurrido - sin_datos_desde >= espera_sin_datos_ms:
                    return 'SIN_DATOS'
            else:
                sin_datos_desde = None
        except Exception:
            pass

        if transcurrido and transcurrido % 60000 == 0:
            print(f'  esperando {codigo} {tipo}: {transcurrido//1000}s sin reiniciar consulta...')

        page.wait_for_timeout(paso_ms)
        transcurrido += paso_ms

    # Última validación antes de declarar timeout.
    if hay_tabla_con_resultados(page):
        return 'DATOS'
    txt_final = leer_texto_body(page)
    if any(x in txt_final for x in sin_datos):
        return 'SIN_DATOS'
    if any(x in txt_final for x in esperado):
        return 'DATOS'
    if sin_datos_desde is not None:
        return 'SIN_DATOS'
    return 'TIMEOUT:' + (txt_final or ultimo_texto)[:250].replace('\n', ' ')


def crear_csv_sin_datos(codigo, tipo):
    """Marcador CSV controlado para reportes que eCollect respondió sin registros.
    No usamos HTML porque la página no siempre muestra toda la información.
    """
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = config.DESCARGAS / f'ecollect_{codigo}_{tipo}_{ts}_SIN_DATOS.csv'
    target.write_text('SIN_DATOS\n', encoding='utf-8')
    return target



def detectar_codigos_en_csv(path, max_filas=120):
    p = Path(path)
    codigos = set()
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        try:
            with p.open("r", encoding=enc, errors="ignore", newline="") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i >= max_filas:
                        break
                    for cell in row:
                        s = str(cell or "").strip()
                        if re.fullmatch(r"416\d{2}", s):
                            codigos.add(s)
            if codigos:
                break
        except Exception:
            continue
    return codigos


def validar_codigo_csv_descargado(path, codigo_esperado):
    p = Path(path)
    if "SIN_DATOS" in p.name.upper():
        return True

    esperado = str(codigo_esperado).strip()
    codigos = detectar_codigos_en_csv(p)
    if not codigos:
        raise RuntimeError(
            f"No pude validar el comercio del CSV {p.name}: no encontrÃ© un cÃ³digo 416xx en el contenido."
        )

    otros = sorted(c for c in codigos if c != esperado)
    if esperado not in codigos or otros:
        detectados = ", ".join(sorted(codigos))
        raise RuntimeError(
            f"CSV INCORRECTO. Solicitado={esperado}; contenido detectado={detectados}. "
            "Se descarta y se reintenta la consulta."
        )

    print(f"  VALIDACIÃ“N CSV OK: solicitado {esperado} / contenido {esperado}")
    return True

def descargar_reporte_actual(page, codigo, tipo, permitir_sin_datos=False):
    """Descarga obligatoriamente CSV de eCollect.

    IMPORTANTE: no guardamos HTML como resultado operativo, porque eCollect pagina
    y el HTML no siempre contiene todo el reporte. Si no hay registros, generamos
    un CSV marcador SIN_DATOS; si hay datos y no se logra CSV, se levanta error
    para reintentar desde el link principal.
    """
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    if permitir_sin_datos:
        return crear_csv_sin_datos(codigo, tipo)

    cerrar_calendarios(page)
    selectores_csv = [
        'a:has-text("Exportar a CSV")',
        'text=/Exportar\s+a\s+CSV/i',
        'a[href*="CSV"]',
        'a[href*="csv"]',
    ]
    errores = []
    for sel in selectores_csv:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                with page.expect_download(timeout=300000) as dlinfo:
                    loc.first.click(timeout=30000, force=True)
                d = dlinfo.value
                target = config.DESCARGAS / f'ecollect_{codigo}_{tipo}_{ts}.csv'
                d.save_as(str(target))
                try:
                    validar_codigo_csv_descargado(target, codigo)
                except Exception:
                    try:
                        target.unlink()
                    except Exception:
                        pass
                    raise
                print(f'  CSV descargado {codigo} {tipo}: {target.name}')
                return target
        except Exception as e:
            errores.append(f'{sel}: {e}')

    # Respaldo ASP.NET: buscar cualquier link cuyo texto contenga CSV por JS y hacer click.
    try:
        ok = page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a'));
                const a = links.find(x => (x.innerText || x.textContent || '').toUpperCase().includes('CSV'));
                if (!a) return false;
                a.scrollIntoView({block:'center'});
                a.click();
                return true;
            }
        """)
        if ok:
            # Si el click JS dispara descarga, Playwright solo la captura si se armó antes;
            # por eso este método es diagnóstico, no definitivo.
            page.wait_for_timeout(4000)
    except Exception as e:
        errores.append(f'js_csv: {e}')

    base = diagnostico(page, f'ecollect_no_csv_{codigo}_{tipo}')
    raise RuntimeError(f'No se pudo descargar CSV para {codigo} {tipo}. No se guardará HTML como resultado. Diagnóstico: {base}.html/.png. Errores: {errores[:2]}')


def ordenar_items(items):
    """Deja reportes lentos al final para que el resto del monitoreo avance primero."""
    lentos = {('41604', 'RED'), ('41604', 'JAVA'), ('41605', 'RED'), ('41605', 'JAVA')}
    vistos = []
    for item in items:
        codigo = str(item['codigo'])
        tipo = str(item['tipo_reporte']).upper()
        key = (codigo, tipo)
        if key not in vistos:
            vistos.append(key)
    return sorted(vistos, key=lambda k: (k in lentos, k[0], k[1]))


def resetear_ecollect(page, tipo=None):
    """Vuelve al link principal cuando eCollect saca la sesión a landing/página diferente."""
    try:
        page.goto(config.ECOLLECT_URL, wait_until='domcontentloaded', timeout=90000)
        page.wait_for_timeout(2500)
        cerrar_modal_publicidad(page)
        login_si_necesario(page)
        cerrar_modal_publicidad(page)
        asegurar_inicio(page)
        if tipo:
            ir_reporte(page, tipo)
        return True
    except Exception:
        return False


def descargar_ecollect(fecha_inicio, fecha_fin, items):
    descargados = []
    p = sync_playwright().start()
    browser = None
    try:
        state = _state_path()
        browser = p.chromium.launch(headless=config.HEADLESS)
        browser_visible = not config.HEADLESS
        context = browser.new_context(accept_downloads=True, storage_state=str(state) if config.USAR_SESION and state.exists() else None)
        page = context.new_page()
        page.set_default_timeout(90000)
        resetear_ecollect(page)
        context.storage_state(path=str(state))

        for codigo, tipo in ordenar_items(items):
            # 41605 JAVA suele quedarse cargando; cuando está en modo oculto,
            # abrimos SOLO esta parte visible para poder ver qué hace eCollect.
            visible_41605_java = os.getenv('ECOLLECT_VISIBLE_41605_JAVA', 'true').lower() == 'true'
            if str(codigo) == '41605' and str(tipo).upper() == 'JAVA' and config.HEADLESS and visible_41605_java and not browser_visible:
                print('eCollect: 41605 JAVA detectado. Cambio temporal a navegador visible para revisar la carga...')
                try:
                    context.storage_state(path=str(state))
                except Exception:
                    pass
                try:
                    context.close()
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass
                browser = p.chromium.launch(headless=False)
                browser_visible = True
                context = browser.new_context(accept_downloads=True, storage_state=str(state) if config.USAR_SESION and state.exists() else None)
                page = context.new_page()
                page.set_default_timeout(90000)
                resetear_ecollect(page)

            print(f'eCollect: descargando {codigo} {tipo}...')
            ultimo = None
            intentos_item = int(os.getenv('ECOLLECT_REINTENTOS_ITEM', '3'))
            for intento in range(1, intentos_item + 1):
                try:
                    if intento > 1:
                        print(f'  reintentando {codigo} {tipo} desde link principal ({intento}/{intentos_item})...')
                        resetear_ecollect(page, tipo=None)

                    seleccionar_entidad(page, codigo)
                    ir_reporte(page, tipo)
                    llenar_fechas(page, fecha_inicio, fecha_fin)
                    if not click_consultar(page):
                        raise RuntimeError('No encontré botón Consultar')

                    estado = esperar_resultado(page, codigo, tipo)
                    print(f'  resultado {codigo} {tipo}: {estado}')

                    if estado in ['DATOS', 'SIN_DATOS']:
                        ultimo = descargar_reporte_actual(page, codigo, tipo, permitir_sin_datos=(estado == 'SIN_DATOS'))
                        break

                    if estado.startswith('FUERA_ADMIN:'):
                        base = diagnostico(page, f'ecollect_fuera_admin_{codigo}_{tipo}')
                        print(f'  eCollect sacó la sesión o abrió landing para {codigo} {tipo}; diagnóstico: {base}.html/.png')
                        # no guardar ese HTML; reiniciar y reintentar el mismo ítem
                        continue

                    if estado.startswith('TIMEOUT:'):
                        # Última defensa: si la tabla está visible, intentar CSV; si no, diagnóstico.
                        if hay_tabla_con_resultados(page):
                            print(f'  {codigo} {tipo}: tabla visible al cierre del timeout; intentando descarga CSV.')
                            ultimo = descargar_reporte_actual(page, codigo, tipo, permitir_sin_datos=False)
                            break
                        base = diagnostico(page, f'ecollect_timeout_{codigo}_{tipo}')
                        print(f'  timeout {codigo} {tipo}; diagnóstico: {base}.html/.png')
                        break

                except Exception as e:
                    print(f'  error {codigo} {tipo}: {e}')
                    base = diagnostico(page, f'ecollect_error_{codigo}_{tipo}')
                    print(f'  diagnóstico: {base}.html/.png')
                    # Si eCollect quedó en landing/sesión dañada, reintentar desde cero.
                    if intento < intentos_item:
                        continue
                    break

            if ultimo:
                descargados.append(ultimo)

        context.storage_state(path=str(state))
        return descargados
    finally:
        try:
            if browser:
                browser.close()
        finally:
            p.stop()

def guardar_sesion_ecollect():
    p=sync_playwright().start(); browser=None
    try:
        browser=p.chromium.launch(headless=False); context=browser.new_context(accept_downloads=True); page=context.new_page()
        page.goto(config.ECOLLECT_URL,wait_until="domcontentloaded",timeout=90000); cerrar_modal_publicidad(page); login_si_necesario(page); asegurar_inicio(page)
        context.storage_state(path=str(_state_path())); print(f"Sesión eCollect guardada automáticamente en {_state_path()}")
    finally:
        try:
            if browser: browser.close()
        finally: p.stop()
