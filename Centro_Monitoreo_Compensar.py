from __future__ import annotations
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from core.orchestrator import load_config, run_monitor, finalize, output_root

ORANGE = "#ED5123"; BLUE = "#0057B8"; GREEN = "#65B32E"; BG = "#EEF3F8"; DARK = "#243647"

class ProgressRing(tk.Canvas):
    def __init__(self,master,size=64):
        super().__init__(master,width=size,height=size,bg="white",highlightthickness=0); self.size=size
        self.create_oval(7,7,size-7,size-7,outline="#E6EDF4",width=7)
        self.arc=self.create_arc(7,7,size-7,size-7,start=90,extent=0,style="arc",outline=ORANGE,width=7)
        self.txt=self.create_text(size/2,size/2,text="0%",fill=BLUE,font=("Segoe UI",10,"bold"))
    def set(self,p,done=False,error=False):
        p=max(0,min(100,int(p))); c="#D93636" if error else (GREEN if done else ORANGE)
        self.itemconfigure(self.arc,extent=-(p/100)*360,outline=c); self.itemconfigure(self.txt,text=("✕" if error else ("✓" if done else f"{p}%")),fill=(c if done or error else BLUE),font=("Segoe UI",17 if done or error else 10,"bold"))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Centro de Monitoreo Compensar")
        self.geometry("1280x790")
        self.minsize(1050, 680)
        self.configure(bg=BG)
        self.q = queue.Queue()
        self.running = False
        self.last_selected = tuple()
        self.active_processes = []
        self.cancel_requested = False
        self.vars = {m: tk.BooleanVar(value=True) for m in ["PASARELAS", "AWS", "HERCULES"]}
        self.modo = tk.StringVar(value="actual")
        self.corte = tk.StringVar(value="09")
        self.fecha = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.historico_tipo = tk.StringVar(value="completo")
        self.hora_inicio = tk.StringVar(value="00:00")
        self.hora_fin = tk.StringVar(value="23:59")
        self.status = {m: tk.StringVar(value="Listo") for m in self.vars}
        self.progress = {m: 0 for m in self.vars}
        self.rings = {}
        self.final_labels = {}
        self.logo_img = None
        self._build()
        self.after(120, self._poll)

    def _build(self):
        self._build_header()
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=20, pady=16)

        top = tk.Frame(main, bg=BG)
        top.pack(fill="x")
        execf = tk.LabelFrame(top, text=" Ejecutar monitoreo ", bg="white", fg=DARK, font=("Segoe UI", 11, "bold"), bd=0, highlightthickness=1, highlightbackground="#D9E5EF")
        execf.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._build_exec_panel(execf)

        cfgf = tk.LabelFrame(top, text=" Configuración de este equipo ", bg="white", fg=DARK, font=("Segoe UI", 11, "bold"), bd=0, highlightthickness=1, highlightbackground="#D9E5EF")
        cfgf.pack(side="right", fill="both", padx=(10, 0))
        self._build_cfg_panel(cfgf)

        stat = tk.Frame(main, bg=BG)
        stat.pack(fill="x", pady=14)
        for m in self.vars:
            card=tk.Frame(stat,bg="white",bd=0,highlightthickness=1,highlightbackground="#D9E5EF"); card.pack(side="left",fill="x",expand=True,padx=5)
            tk.Frame(card,bg=ORANGE,height=5).pack(fill="x")
            inner=tk.Frame(card,bg="white"); inner.pack(fill="both",expand=True,padx=14,pady=10)
            left=tk.Frame(inner,bg="white"); left.pack(side="left",fill="both",expand=True)
            tk.Label(left,text=m,bg="white",fg=BLUE,font=("Segoe UI",15,"bold")).pack(anchor="w")
            tk.Label(left,textvariable=self.status[m],bg="white",fg=DARK,font=("Segoe UI",9),wraplength=300,justify="left").pack(anchor="w",pady=(7,0))
            right=tk.Frame(inner,bg="white"); right.pack(side="right",padx=(10,0))
            ring=ProgressRing(right); ring.pack(); self.rings[m]=ring
            lab=tk.Label(right,text="",bg="white",fg=GREEN,font=("Segoe UI",10,"bold")); lab.pack(pady=(2,0)); self.final_labels[m]=lab

        lf = tk.LabelFrame(main, text=" Actividad ", bg="white", fg=DARK, font=("Segoe UI", 11, "bold"), bd=0, highlightthickness=1, highlightbackground="#D9E5EF")
        lf.pack(fill="both", expand=True)
        self.log = tk.Text(lf, bg="#0F1720", fg="#DCE8F4", insertbackground="white", font=("Consolas", 9), bd=0, relief="flat")
        self.log.pack(fill="both", expand=True, padx=1, pady=1)
        self.write("Listo. Los monitores son independientes y el consolidado se actualiza al final.")

    def _build_header(self):
        header = tk.Frame(
            self,
            bg=ORANGE,
            height=90
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        wrap = tk.Frame(
            header,
            bg=ORANGE
        )
        wrap.pack(
            fill="both",
            expand=True,
            padx=26,
            pady=12
        )

        brand = tk.Frame(
            wrap,
            bg=ORANGE
        )
        brand.pack(
            side="left",
            anchor="w"
        )

        # --------------------------------------------------
        # LOGO COMPENSAR ESTILIZADO EN FORMA DE "C"
        # --------------------------------------------------

        logo = tk.Canvas(
            brand,
            width=76,
            height=66,
            bg=ORANGE,
            highlightthickness=0,
            bd=0
        )
        logo.pack(
            side="left",
            padx=(0, 12)
        )

        # Distribución tipo C / C curva
        #          ●   ●
        #      ●   ●
        #          ●   ●
        #
        # Mantiene el centro abierto hacia la derecha.

        r = 10

        centros = [
            (31, 13),   # arriba izquierda
            (53, 13),   # arriba derecha
            (18, 32),   # izquierda
            (38, 32),   # centro
            (31, 52),   # abajo izquierda
            (53, 52),   # abajo derecha
        ]

        for cx, cy in centros:
            logo.create_oval(
                cx-r,
                cy-r,
                cx+r,
                cy+r,
                fill="white",
                outline="white"
            )

        textos = tk.Frame(
            brand,
            bg=ORANGE
        )
        textos.pack(
            side="left",
            anchor="center"
        )

        tk.Label(
            textos,
            text="compensar",
            bg=ORANGE,
            fg="white",
            font=("Segoe UI", 12, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            textos,
            text="CENTRO DE MONITOREO",
            bg=ORANGE,
            fg="white",
            font=("Segoe UI", 20, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            textos,
            text="AWS  ·  Pasarelas  ·  Hércules  ·  Histórico unificado",
            bg=ORANGE,
            fg="#FFF4EE",
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        right = tk.Frame(
            wrap,
            bg=ORANGE
        )
        right.pack(
            side="right",
            anchor="e",
            pady=7
        )

        tk.Label(
            right,
            text="MONITOREO OPERATIVO",
            bg="#D94318",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=7
        ).pack()

        tk.Label(
            right,
            text="09:00  ·  13:00  ·  17:00",
            bg=ORANGE,
            fg="#FFF4EE",
            font=("Segoe UI", 8)
        ).pack(
            pady=(4, 0)
        )

    def _build_exec_panel(self, execf):
        row = tk.Frame(execf, bg="white")
        row.pack(fill="x", padx=18, pady=14)
        for text, val in [("Corte programado", "actual"), ("Ahora · 00:00 a hora actual", "acumulado-hoy"), ("Día anterior", "dia-anterior"), ("Fecha específica", "fecha")]:
            tk.Radiobutton(row, text=text, variable=self.modo, value=val, bg="white", activebackground="white", font=("Segoe UI", 10)).pack(side="left", padx=(0, 18))
        tk.Entry(row, textvariable=self.fecha, width=12, font=("Segoe UI", 10), relief="solid", bd=1).pack(side="left")
        tk.Label(row, text="  Corte:", bg="white", fg=DARK, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(20, 4))
        ttk.Combobox(row, textvariable=self.corte, values=["09", "13", "17"], width=5, state="readonly").pack(side="left")

        hist = tk.Frame(execf, bg="#F7FAFD")
        hist.pack(fill="x", padx=18, pady=(0, 10))
        tk.Label(hist, text="Para día anterior / fecha específica:", bg="#F7FAFD", fg=DARK, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 12), pady=8)
        tk.Radiobutton(hist, text="Día completo 00:00 â†’ 23:59", variable=self.historico_tipo, value="completo", bg="#F7FAFD", activebackground="#F7FAFD").pack(side="left")
        tk.Radiobutton(hist, text="Rango:", variable=self.historico_tipo, value="rango", bg="#F7FAFD", activebackground="#F7FAFD").pack(side="left", padx=(12, 4))
        tk.Entry(hist, textvariable=self.hora_inicio, width=6, justify="center", relief="solid", bd=1).pack(side="left")
        tk.Label(hist, text="â†’", bg="#F7FAFD").pack(side="left", padx=4)
        tk.Entry(hist, textvariable=self.hora_fin, width=6, justify="center", relief="solid", bd=1).pack(side="left")

        mons = tk.Frame(execf, bg="white")
        mons.pack(fill="x", padx=18, pady=(0, 12))
        for m in self.vars:
            tk.Checkbutton(mons, text=m, variable=self.vars[m], bg="white", activebackground="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 24))

        buttons = tk.Frame(execf, bg="white")
        buttons.pack(fill="x", padx=18, pady=(0, 16))
        self.runbtn = tk.Button(buttons, text="EJECUTAR", command=self.start, bg=BLUE, fg="white", activebackground="#00468f", activeforeground="white", font=("Segoe UI", 12, "bold"), bd=0, padx=28, pady=12)
        self.runbtn.pack(side="left")

        self.cancelbtn = tk.Button(
            buttons,
            text="■ CANCELAR TODO",
            command=self.cancel_all,
            bg="#D93636",
            fg="white",
            activebackground="#B92323",
            activeforeground="white",
            font=("Segoe UI", 11, "bold"),
            bd=0,
            padx=22,
            pady=12,
            state="disabled"
        )
        self.cancelbtn.pack(
            side="left",
            padx=(8, 0)
        )
        self.openbtn = tk.Button(buttons, text="Abrir carpeta", command=self.open_result_folder, bg="#EAF2FB", fg=BLUE, bd=0, padx=18, pady=12, font=("Segoe UI", 10)).pack(side="left", padx=8)
        tk.Button(buttons, text="Ver dashboard", command=self.refresh_dash, bg="#E9F6DF", fg="#397A15", bd=0, padx=18, pady=12, font=("Segoe UI", 10)).pack(side="left")

    def _build_cfg_panel(self, cfgf):
        cfg = load_config()
        self.pathvar = tk.StringVar(value=cfg["output_root"])
        tk.Label(cfgf, text="Carpeta raíz de salida", bg="white", fg=DARK, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        tk.Entry(cfgf, textvariable=self.pathvar, width=52, relief="solid", bd=1).pack(padx=14)
        tk.Button(cfgf, text="Cambiar carpeta", command=self.change_path, bg="#EAF2FB", fg=BLUE, bd=0, pady=8, padx=16).pack(anchor="w", padx=14, pady=10)
        tk.Button(cfgf, text="Usuarios, claves y sesiones", command=self.credentials_window, bg=ORANGE, fg="white", bd=0, padx=16, pady=10, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(2, 10))
        tk.Label(cfgf, text="41605 JAVA y 41610 RED se abren visibles\nen procesos separados para no bloquear el resto.", justify="left", bg="white", fg="#5C6773", font=("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(2, 14))

    def write(self, msg):
        self.log.insert("end", f"[{datetime.now():%H:%M:%S}] {msg}\n")
        self.log.see("end")

    def _infer_progress(self, name, state, detail):
        t = (detail or "").lower()
        cur = self.progress.get(name, 0)

        if state == "ERROR":
            return 100, False, True
        if state == "OK":
            return 100, True, False
        if state == "CANCELADO":
            return cur, False, False

        if state == "PREPARANDO":
            if "sesiÃ³n ecollect preparada" in t or "sesion ecollect preparada" in t:
                return max(cur, 10), False, False
            if "sesiones de pasarelas listas" in t:
                return max(cur, 12), False, False
            return max(cur, 5), False, False

        if name == "PASARELAS":
            if "iniciando..." in t:
                cur = max(cur, 15)
            elif "payu: abriendo" in t or "payu: formulario" in t or "payu: sesiÃ³n" in t or "payu: sesion" in t:
                cur = max(cur, 20)
            elif "payu: fecha inicio" in t or "payu: fechas diligenciadas" in t:
                cur = max(cur, 24)
            elif "payu: iniciando descarga" in t or "botÃ³n download" in t or "boton download" in t:
                cur = max(cur, 28)
            elif "payu: descarga directa detectada" in t or "archivo guardado correctamente" in t:
                cur = max(cur, 34)
            elif "[fast]" in t and "consultas" in t:
                cur = max(cur, 30)
            elif "[41605_java]" in t or "[41610_red]" in t:
                cur = max(cur, 34)
            elif "csv descargado" in t:
                cur = min(82, max(cur + 3, 38))
            elif "sin_datos" in t or "sin datos" in t:
                cur = min(82, max(cur + 2, 38))
            elif "trabajos iniciados en paralelo" in t:
                cur = max(cur, 45)
            elif "finalizado con cÃ³digo 0" in t or "finalizado con codigo 0" in t:
                cur = min(90, max(cur + 4, 72))
            elif "html generado" in t:
                cur = max(cur, 94)
            elif "excel generado" in t:
                cur = max(cur, 97)
            elif "consolidado pasarelas" in t:
                cur = max(cur, 99)

        elif name == "AWS":
            if "iniciando" in t:
                cur = max(cur, 8)
            elif "monitoreando:" in t or "rango:" in t:
                cur = max(cur, 18)
            elif t.strip().startswith("-"):
                cur = min(88, max(cur + 2, 22))
            elif "excel:" in t:
                cur = max(cur, 94)
            elif "html:" in t:
                cur = max(cur, 97)

        elif name == "HERCULES":
            if "iniciando navegador" in t:
                cur = max(cur, 10)
            elif "entrando al reporte" in t:
                cur = max(cur, 18)
            elif "fechas configuradas" in t:
                cur = max(cur, 30)
            elif "torneos" in t:
                cur = max(cur, 38)
            elif "gimnasios" in t:
                cur = max(cur, 48)
            elif "turnos" in t:
                cur = max(cur, 58)
            elif "citas" in t:
                cur = max(cur, 68)
            elif "materiales" in t:
                cur = max(cur, 78)
            elif "generar reporte" in t:
                cur = max(cur, 84)
            elif "archivo descargado" in t:
                cur = max(cur, 90)
            elif "resumen excel generado" in t:
                cur = max(cur, 94)
            elif "dashboard" in t:
                cur = max(cur, 98)

        return cur, False, False

    def cb(self, name, state, detail):

        try:
            progreso = self._progress_from_message(
                monitor, estado, detalle
            )
            if progreso is not None:
                try:
                    self.progress_value[monitor] = progreso
                except Exception:
                    pass
        except Exception:
            pass
        self.q.put((name, state, detail))
    def _poll(self):
        try:
            while True:
                name, state, detail = self.q.get_nowait()
                if name in self.status:
                    self.status[name].set(f"{state}: {detail[:180]}")
                    pct,done,err=self._infer_progress(name,state,detail); self.progress[name]=pct
                    if name in self.rings: self.rings[name].set(pct,done,err)
                    if name in self.final_labels: self.final_labels[name].config(text=("FINALIZADO" if done else ("ERROR" if err else "")),fg=(GREEN if done else "#D93636"))
                self.write(f"{name} · {state} · {detail}")
        except queue.Empty:
            pass
        self.after(120, self._poll)

    def start(self):
        # -----------------------------------------------------
        # No permitir dos ejecuciones simultáneas desde la UI
        # -----------------------------------------------------
        if self.running:
            messagebox.showwarning(
                "Monitoreo en ejecución",
                "Ya existe un monitoreo ejecutándose.\n\n"
                "Espera a que finalice o utiliza CANCELAR TODO."
            )
            return

        # Captura INMUTABLE de la selección en este instante.
        selected = tuple(
            m
            for m, variable in self.vars.items()
            if variable.get() is True
        )

        # Recordar qué monitores fueron seleccionados en
        # la ejecución actual.
        self.last_selected = selected

        if not selected:
            messagebox.showwarning(
                "Monitoreo",
                "Selecciona al menos un monitor."
            )
            return

        # -----------------------------------------------------
        # Validar fecha/rango
        # -----------------------------------------------------
        if self.modo.get() == "fecha":
            try:
                datetime.strptime(
                    self.fecha.get(),
                    "%Y-%m-%d"
                )
            except ValueError:
                messagebox.showerror(
                    "Fecha",
                    "Usa formato YYYY-MM-DD."
                )
                return

        if (
            self.modo.get() in ("dia-anterior", "fecha")
            and self.historico_tipo.get() == "rango"
        ):
            try:
                hi = datetime.strptime(
                    self.hora_inicio.get().strip(),
                    "%H:%M"
                )

                hf = datetime.strptime(
                    self.hora_fin.get().strip(),
                    "%H:%M"
                )

                if hf <= hi:
                    raise ValueError

            except ValueError:
                messagebox.showerror(
                    "Rango horario",
                    "Usa horas HH:MM y asegúrate de que "
                    "la hora final sea mayor que la inicial."
                )
                return

        # -----------------------------------------------------
        # Reiniciar visualmente las tarjetas
        # -----------------------------------------------------
        for monitor in self.status:

            if monitor in selected:
                self.status[monitor].set(
                    "EN COLA · 0%"
                )
            else:
                self.status[monitor].set(
                    "NO SELECCIONADO"
                )

                # El indicador gráfico se limpia después en el
                # refresco visual; no debe conservar el ✓ anterior.
                try:
                    self.progress_value[monitor] = 0
                except Exception:
                    pass

        self.write(
            "SYSTEM · SELECCIÓN · "
            + ", ".join(selected)
        )

        self.last_selected = tuple(selected)

        # Limpiar el resultado visual de la ejecuciÃ³n anterior.
        for monitor in self.status:
            self.progress[monitor] = 0
            if monitor in self.rings:
                self.rings[monitor].set(0, False, False)
            if monitor in self.final_labels:
                self.final_labels[monitor].config(text="")

        self._pasarelas_csv_count = 0
        self.running = True
        self.cancel_requested = False

        self.runbtn.config(
            state="disabled"
        )

        self.cancelbtn.config(
            state="normal",
            text="■ CANCELAR TODO"
        )

        # La tupla selected ya no puede cambiar aunque el
        # usuario toque los checkboxes después.
        threading.Thread(
            target=self._run_all,
            args=(selected,),
            daemon=True
        ).start()



    def _progress_from_message(self, monitor, estado, detalle):
        """
        Calcula progreso aproximado usando hitos REALES del log.
        No es un temporizador.
        """
        m = (monitor or "").upper()
        e = (estado or "").upper()
        d = (detalle or "").lower()

        if e == "OK":
            return 100

        if e in ("ERROR", "CANCELADO"):
            return None

        if m == "PASARELAS":
            if "primera ejecución" in d or "preparando sesión" in d:
                return 5
            if "sesión ecollect preparada correctamente" in d:
                return 10
            if "iniciando" in d:
                return 15
            if "trabajos iniciados en paralelo" in d:
                return 25
            if "payu:" in d and "descarga directa detectada" in d:
                return 35
            if "payu:" in d and "archivo guardado correctamente" in d:
                return 40
            if "[fast]" in d:
                return 45
            if "csv descargado" in d:
                # Va progresando conforme aparecen archivos.
                actual = getattr(
                    self,
                    "_pasarelas_csv_count",
                    0
                ) + 1

                self._pasarelas_csv_count = actual

                return min(
                    45 + actual * 2,
                    82
                )

            if "41605_java" in d and "finalizado con código 0" in d:
                return 86

            if "41610_red" in d and "finalizado con código 0" in d:
                return 89

            if "ecollect_rapido" in d and "finalizado con código 0" in d:
                return 91

            if "payu" in d and "finalizado con código 0" in d:
                return 93

            if "html generado" in d:
                return 96

            if "excel generado" in d:
                return 98

            if "consolidado pasarelas" in d:
                return 99

        if m == "AWS":
            if "iniciando" in d:
                return 5
            if "monitoreando:" in d:
                return 20
            if "rango:" in d:
                return 30
            if "excel:" in d:
                return 85
            if "html:" in d:
                return 92
            if "alertas:" in d:
                return 97

        if m == "HERCULES":
            if "primera ejecución" in d:
                return 5
            if "sesión creada correctamente" in d:
                return 10
            if "iniciando navegador" in d:
                return 15
            if "configurando fechas" in d:
                return 25
            if "marcando cuadros principales" in d:
                return 35
            if "torneos" in d and "checkbox marcado" in d:
                return 45
            if "gimnasios" in d and "checkbox marcado" in d:
                return 55
            if "turnos" in d and "checkbox marcado" in d:
                return 65
            if "citas" in d and "checkbox marcado" in d:
                return 72
            if "materiales" in d and "checkbox marcado" in d:
                return 80
            if "generar reporte" in d:
                return 88
            if "archivo descargado" in d:
                return 94
            if "dashboard html generado" in d:
                return 98

        return None

    def _run_all(self, selected):
        try:
            threads = []

            def one(m):
                if self.cancel_requested:
                    return

                try:
                    run_monitor(
                        m,
                        self.modo.get(),
                        self.corte.get(),
                        self.fecha.get()
                        if self.modo.get() == "fecha"
                        else None,
                        "00:00"
                        if self.historico_tipo.get() == "completo"
                        else self.hora_inicio.get().strip(),
                        "23:59"
                        if self.historico_tipo.get() == "completo"
                        else self.hora_fin.get().strip(),
                        self.cb,
                    )
                except Exception as exc:
                    if not self.cancel_requested:
                        self.q.put(
                            (
                                m,
                                "ERROR",
                                str(exc)
                            )
                        )

            for m in selected:

                if self.cancel_requested:
                    break

                t = threading.Thread(
                    target=one,
                    args=(m,),
                    daemon=True
                )

                t.start()
                threads.append(t)

            # Espera controlada para poder reaccionar
            # correctamente a CANCELAR TODO.
            while any(t.is_alive() for t in threads):

                if self.cancel_requested:
                    break

                for t in threads:
                    t.join(timeout=0.25)

            # MUY IMPORTANTE:
            # después de una cancelación no se genera consolidado
            # ni se puede informar SYSTEM OK.
            if self.cancel_requested:

                self.q.put(
                    (
                        "SYSTEM",
                        "CANCELADO",
                        "Ejecución cancelada por el usuario."
                    )
                )

                return

            # Si no se canceló, terminamos de unir hilos.
            for t in threads:
                t.join()

            # Doble validación antes de consolidar.
            if self.cancel_requested:
                return

            deleted, dash, excel = finalize()

            if self.cancel_requested:
                return

            self.q.put(
                (
                    "SYSTEM",
                    "OK",
                    (
                        f"Monitoreo finalizado. "
                        f"Limpieza: {deleted} archivos. "
                        f"Dashboard: {dash.name}. "
                        f"Excel: "
                        f"{excel.name if excel else 'pendiente'}"
                    )
                )
            )

        except Exception as exc:

            if not self.cancel_requested:

                self.q.put(
                    (
                        "SYSTEM",
                        "ERROR",
                        str(exc)
                    )
                )

        finally:

            self.running = False

            self.after(
                0,
                lambda: self.runbtn.config(
                    state="normal"
                )
            )

            self.after(
                0,
                lambda: self.cancelbtn.config(
                    state="disabled",
                    text="■ CANCELAR TODO"
                )
            )


    def cancel_all(self):
        """
        Cancela todos los procesos relacionados con esta
        ejecución de monitoreo.

        Esto incluye:
        - run.py / monitores principales
        - PayU worker
        - eCollect worker rápido
        - 41605 JAVA
        - 41610 RED
        - Hércules
        - AWS
        """

        if not self.running:
            return

        self.cancel_requested = True

        self.cancelbtn.config(
            state="disabled",
            text="CANCELANDO..."
        )

        self.write(
            "SYSTEM · CANCELANDO · "
            "Deteniendo todos los procesos activos..."
        )

        for m in self.status:
            actual = self.status[m].get()

            if (
                "OK" not in actual
                and "ERROR" not in actual
            ):
                self.status[m].set(
                    "CANCELANDO..."
                )

        def matar():
            try:
                if os.name == "nt":

                    # Buscar procesos Python/PowerShell/CMD
                    # relacionados exclusivamente con este proyecto.

                    proyecto = str(ROOT)

                    cmd = [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        (
                            "Get-CimInstance Win32_Process | "
                            "Where-Object { "
                            "$_.CommandLine -like "
                            f"'*{proyecto.replace(chr(92), chr(92)+chr(92))}*' "
                            "-and "
                            "$_.ProcessId -ne $PID "
                            "} | "
                            "ForEach-Object { "
                            "Stop-Process "
                            "-Id $_.ProcessId "
                            "-Force "
                            "-ErrorAction SilentlyContinue "
                            "}"
                        )
                    ]

                    subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=20
                    )

                self.after(
                    0,
                    self._cancel_finished
                )

            except Exception as exc:

                self.q.put(
                    (
                        "SYSTEM",
                        "ERROR",
                        f"No pude cancelar todo: {exc}"
                    )
                )

                self.after(
                    0,
                    self._cancel_finished
                )

        threading.Thread(
            target=matar,
            daemon=True
        ).start()


    def _cancel_finished(self):
        for m in self.status:
            actual = self.status[m].get()

            if (
                "OK" not in actual
                and "ERROR" not in actual
            ):
                self.status[m].set(
                    "CANCELADO"
                )

        self.write(
            "SYSTEM · CANCELADO · "
            "Todos los procesos del monitoreo fueron detenidos."
        )

        self.cancelbtn.config(
            text="■ CANCELAR TODO",
            state="disabled"
        )

        self.runbtn.config(
            state="normal"
        )

        self.running = False

    def _read_env(self, path):
        p = Path(path)
        return dict(dotenv_values(p)) if p.exists() else {}

    def _write_env(self, path, values):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        old = self._read_env(p)
        old.update(values)
        lines = []
        for k, v in old.items():
            if v is None:
                v = ""
            lines.append(f"{k}={str(v).replace(chr(10), ' ').replace(chr(13), ' ')}")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def credentials_window(self):
        w = tk.Toplevel(self)
        w.title("Credenciales y sesiones")
        w.geometry("900x650")
        w.minsize(820, 600)
        w.configure(bg=BG)
        w.transient(self)
        w.grab_set()

        # =========================================================
        # CABECERA
        # =========================================================

        header = tk.Frame(
            w,
            bg=ORANGE,
            height=64
        )
        header.pack(
            side="top",
            fill="x"
        )
        header.pack_propagate(False)

        tk.Label(
            header,
            text="USUARIOS, CLAVES Y SESIONES",
            bg=ORANGE,
            fg="white",
            font=("Segoe UI", 17, "bold")
        ).pack(
            expand=True
        )

        # =========================================================
        # FOOTER FIJO
        # =========================================================

        footer = tk.Frame(
            w,
            bg="white",
            height=70,
            highlightthickness=1,
            highlightbackground="#D9E5EF"
        )
        footer.pack(
            side="bottom",
            fill="x"
        )
        footer.pack_propagate(False)

        status_var = tk.StringVar(
            value="Sin cambios pendientes"
        )

        tk.Label(
            footer,
            textvariable=status_var,
            bg="white",
            fg="#53606C",
            font=("Segoe UI", 9)
        ).pack(
            side="left",
            padx=16
        )

        # =========================================================
        # CUERPO
        # =========================================================

        body = tk.Frame(
            w,
            bg=BG
        )
        body.pack(
            side="top",
            fill="both",
            expand=True,
            padx=16,
            pady=14
        )

        pe = self._read_env(
            ROOT / "monitores" / "pasarelas" / ".env"
        )

        he = self._read_env(
            ROOT / "monitores" / "hercules" / ".env"
        )

        vals = {}

        fields = [
            (
                "e_user",
                "eCollect · Usuario",
                pe.get("ECOLLECT_USER", ""),
                False
            ),
            (
                "e_pass",
                "eCollect · Clave",
                pe.get("ECOLLECT_PASSWORD", ""),
                True
            ),
            (
                "p_user",
                "PayU · Usuario",
                pe.get("PAYU_USER", ""),
                False
            ),
            (
                "p_pass",
                "PayU · Clave",
                pe.get("PAYU_PASSWORD", ""),
                True
            ),
            (
                "h_user",
                "Hércules · Usuario",
                he.get("HERCULES_USERNAME", ""),
                False
            ),
            (
                "h_pass",
                "Hércules · Clave",
                he.get("HERCULES_PASSWORD", ""),
                True
            ),
        ]

        form = tk.LabelFrame(
            body,
            text=" Credenciales locales ",
            bg="white",
            fg=DARK,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            highlightthickness=1,
            highlightbackground="#D9E5EF"
        )

        form.pack(
            fill="x"
        )

        dirty = {
            "value": False
        }

        password_entries = []

        def mark_dirty(*_):
            dirty["value"] = True
            status_var.set(
                "Cambios sin guardar"
            )

        for i, (
            key,
            label,
            value,
            secret
        ) in enumerate(fields):

            tk.Label(
                form,
                text=label,
                bg="white",
                fg=DARK,
                font=("Segoe UI", 10, "bold")
            ).grid(
                row=i,
                column=0,
                sticky="w",
                padx=(16, 12),
                pady=10
            )

            variable = tk.StringVar(
                value=value
            )

            vals[key] = variable

            variable.trace_add(
                "write",
                mark_dirty
            )

            entry = tk.Entry(
                form,
                textvariable=variable,
                show="*" if secret else "",
                font=("Segoe UI", 10),
                relief="solid",
                bd=1
            )

            entry.grid(
                row=i,
                column=1,
                sticky="ew",
                padx=(0, 16),
                pady=10,
                ipady=4
            )

            if secret:
                password_entries.append(
                    entry
                )

        form.columnconfigure(
            1,
            weight=1
        )

        # =========================================================
        # MOSTRAR CLAVES
        # =========================================================

        show = tk.BooleanVar(
            value=False
        )

        def toggle_passwords():
            for entry in password_entries:
                entry.config(
                    show="" if show.get() else "*"
                )

        tk.Checkbutton(
            body,
            text="Mostrar claves",
            variable=show,
            command=toggle_passwords,
            bg=BG,
            activebackground=BG,
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            pady=(10, 6)
        )

        # =========================================================
        # SESIONES
        # =========================================================

        sessions = tk.LabelFrame(
            body,
            text=" Sesiones del navegador ",
            bg="white",
            fg=DARK,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            highlightthickness=1,
            highlightbackground="#D9E5EF"
        )

        sessions.pack(
            fill="x",
            pady=(6, 0)
        )

        tk.Label(
            sessions,
            text=(
                "Después de guardar las credenciales puedes "
                "crear o renovar la sesión de cada portal."
            ),
            bg="white",
            fg="#53606C",
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            padx=14,
            pady=(10, 8)
        )

        session_buttons = tk.Frame(
            sessions,
            bg="white"
        )

        session_buttons.pack(
            fill="x",
            padx=14,
            pady=(0, 12)
        )

        # =========================================================
        # GUARDADO
        # =========================================================

        def save(show_message=True):

            self._write_env(
                ROOT
                / "monitores"
                / "pasarelas"
                / ".env",
                {
                    "ECOLLECT_URL":
                    "https://www.e-collect.com/app_express/admin/eCollectIndex.aspx",

                    "ECOLLECT_USER":
                    vals["e_user"].get().strip(),

                    "ECOLLECT_PASSWORD":
                    vals["e_pass"].get(),

                    "PAYU_URL":
                    "https://secure.payulatam.com/login.zul",

                    "PAYU_USER":
                    vals["p_user"].get().strip(),

                    "PAYU_PASSWORD":
                    vals["p_pass"].get(),

                    "HEADLESS":
                    "true",

                    "USAR_SESION":
                    "true",

                    "LOGIN_AUTOMATICO":
                    "true",

                    "TIMEOUT_CARGA_SEGUNDOS":
                    "480",

                    "REINTENTOS_CONSULTA":
                    "4",

                    "SHAREPOINT_SALIDA":
                    str(
                        output_root()
                        / "ECOLLECT"
                    )
                }
            )

            self._write_env(
                ROOT
                / "monitores"
                / "hercules"
                / ".env",
                {
                    "HERCULES_URL":
                    "https://sistemahercules.bienestarcompensar.com/",

                    "HERCULES_REPORT_URL":
                    "https://sistemahercules.bienestarcompensar.com/sistema.php/reportes/estadisticas#/",

                    "HERCULES_USERNAME":
                    vals["h_user"].get().strip(),

                    "HERCULES_PASSWORD":
                    vals["h_pass"].get(),

                    "AUTO_LOGIN":
                    "true",

                    "HEADLESS":
                    "true",

                    "SHAREPOINT_SYNC_DIR":
                    str(
                        output_root()
                        / "HERCULES"
                    )
                }
            )

            dirty["value"] = False

            status_var.set(
                "✓ Credenciales guardadas correctamente"
            )

            self.write(
                "Credenciales eCollect, PayU y Hércules "
                "guardadas localmente."
            )

            if show_message:
                messagebox.showinfo(
                    "Credenciales guardadas",
                    "Las credenciales quedaron guardadas "
                    "correctamente en este equipo.",
                    parent=w
                )

        # =========================================================
        # GUARDAR SESIONES
        # =========================================================

        def launch_session(which):

            save(
                show_message=False
            )

            py = (
                ROOT
                / ".venv"
                / "Scripts"
                / "python.exe"
            )

            pycmd = (
                str(py)
                if py.exists()
                else sys.executable
            )

            if which == "ECOLLECT":

                cmd = [
                    pycmd,
                    str(
                        ROOT
                        / "monitores"
                        / "pasarelas"
                        / "src"
                        / "main.py"
                    ),
                    "--modo",
                    "guardar-sesion-ecollect"
                ]

                cwd = (
                    ROOT
                    / "monitores"
                    / "pasarelas"
                )

            elif which == "PAYU":

                cmd = [
                    pycmd,
                    str(
                        ROOT
                        / "monitores"
                        / "pasarelas"
                        / "src"
                        / "main.py"
                    ),
                    "--modo",
                    "guardar-sesion-payu"
                ]

                cwd = (
                    ROOT
                    / "monitores"
                    / "pasarelas"
                )

            else:

                cmd = [
                    pycmd,
                    str(
                        ROOT
                        / "monitores"
                        / "hercules"
                        / "src"
                        / "guardar_sesion.py"
                    )
                ]

                cwd = (
                    ROOT
                    / "monitores"
                    / "hercules"
                )

            subprocess.Popen(
                cmd,
                cwd=str(cwd),
                creationflags=(
                    subprocess.CREATE_NEW_CONSOLE
                    if os.name == "nt"
                    else 0
                )
            )

            status_var.set(
                f"Capturando sesión {which}..."
            )

            self.write(
                f"Abierta ventana para guardar "
                f"sesión de {which}."
            )

        for name in [
            "ECOLLECT",
            "PAYU",
            "HERCULES"
        ]:

            tk.Button(
                session_buttons,
                text=f"Guardar sesión {name}",
                command=lambda n=name:
                    launch_session(n),
                bg="#EAF2FB",
                fg=BLUE,
                activebackground="#DCEAF8",
                bd=0,
                padx=14,
                pady=9,
                font=("Segoe UI", 9, "bold")
            ).pack(
                side="left",
                padx=(0, 8)
            )

        # =========================================================
        # BOTONES INFERIORES
        # =========================================================

        def save_close():
            save(
                show_message=False
            )
            w.destroy()

        def cancel():
            if dirty["value"]:
                if not messagebox.askyesno(
                    "Cambios sin guardar",
                    "Hay cambios sin guardar.\n\n"
                    "¿Quieres cerrar sin guardarlos?",
                    parent=w
                ):
                    return

            w.destroy()

        tk.Button(
            footer,
            text="CANCELAR",
            command=cancel,
            bg="#E8EDF2",
            fg=DARK,
            activebackground="#DCE3E9",
            bd=0,
            padx=18,
            pady=10,
            font=("Segoe UI", 9, "bold")
        ).pack(
            side="right",
            padx=(6, 16)
        )

        tk.Button(
            footer,
            text="GUARDAR Y CERRAR",
            command=save_close,
            bg=GREEN,
            fg="white",
            activebackground="#559927",
            activeforeground="white",
            bd=0,
            padx=18,
            pady=10,
            font=("Segoe UI", 10, "bold")
        ).pack(
            side="right",
            padx=6
        )

        tk.Button(
            footer,
            text="GUARDAR",
            command=lambda: save(True),
            bg=BLUE,
            fg="white",
            activebackground="#00468F",
            activeforeground="white",
            bd=0,
            padx=22,
            pady=10,
            font=("Segoe UI", 10, "bold")
        ).pack(
            side="right",
            padx=6
        )

        w.protocol(
            "WM_DELETE_WINDOW",
            cancel
        )

    def change_path(self):
        p = filedialog.askdirectory(title="Selecciona carpeta raíz de Monitoreo diario")
        if not p: return
        cfg = load_config(); cfg["output_root"] = p
        (ROOT / "config" / "app.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        self.pathvar.set(p); self.write("Carpeta de salida actualizada.")

    def _selection_for_results(self):
        if getattr(self, "last_selected", None):
            return tuple(self.last_selected)
        return tuple(m for m, v in self.vars.items() if v.get())

    def _result_folder(self):
        selected = self._selection_for_results()
        root = output_root()
        if len(selected) == 1:
            monitor = selected[0]
            return {
                "PASARELAS": root / "ECOLLECT",
                "AWS": root / "AWS",
                "HERCULES": root / "HERCULES",
            }.get(monitor, root)
        if len(selected) > 1:
            return root / "GENERAL"
        return root

    def open_result_folder(self):
        p = self._result_folder()
        p.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(p))

    def _dashboard_path(self):
        selected = self._selection_for_results()
        root = output_root()
        if len(selected) == 1:
            monitor = selected[0]
            candidates = {
                "PASARELAS": [
                    root / "ECOLLECT" / "dashboard_verticales.html",
                    ROOT / "monitores" / "pasarelas" / "data" / "salida" / "reporte_verticales_diario_ultimo.html",
                ],
                "AWS": [
                    root / "AWS" / "Dashboard_AWS.html",
                ],
                "HERCULES": [
                    root / "HERCULES" / "DASHBOARD_HERCULES.html",
                    root / "HERCULES" / "dashboard_hercules.html",
                    ROOT / "monitores" / "hercules" / "reports" / "dashboard_hercules.html",
                ],
            }.get(monitor, [])
            for p in candidates:
                if p.exists():
                    return p
            return candidates[0] if candidates else None
        return root / "GENERAL" / "Dashboard_General.html"

    def _selection_for_results(self):
        if getattr(self, "last_selected", None):
            return tuple(self.last_selected)
        return tuple(m for m, v in self.vars.items() if v.get())

    def _result_folder(self):
        selected = self._selection_for_results()
        root = output_root()
        if len(selected) == 1:
            monitor = selected[0]
            return {
                "PASARELAS": root / "ECOLLECT",
                "AWS": root / "AWS",
                "HERCULES": root / "HERCULES",
            }.get(monitor, root)
        if len(selected) > 1:
            return root / "GENERAL"
        return root

    def open_result_folder(self):
        p = self._result_folder()
        p.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(p))

    def _dashboard_path(self):
        selected = self._selection_for_results()
        root = output_root()
        if len(selected) == 1:
            monitor = selected[0]
            candidates = {
                "PASARELAS": [
                    root / "ECOLLECT" / "dashboard_verticales.html",
                    ROOT / "monitores" / "pasarelas" / "data" / "salida" / "reporte_verticales_diario_ultimo.html",
                ],
                "AWS": [
                    root / "AWS" / "Dashboard_AWS.html",
                ],
                "HERCULES": [
                    root / "HERCULES" / "DASHBOARD_HERCULES.html",
                    root / "HERCULES" / "dashboard_hercules.html",
                    ROOT / "monitores" / "hercules" / "reports" / "dashboard_hercules.html",
                ],
            }.get(monitor, [])
            for p in candidates:
                if p.exists():
                    return p
            return candidates[0] if candidates else None
        return root / "GENERAL" / "Dashboard_General.html"

    def open_general(self):
        # Compatibilidad con instalaciones anteriores.
        self.open_result_folder()

    def refresh_dash(self):
        selected = self._selection_for_results()

        # Si se ejecutÃ³ un solo monitor, abre SOLO su HTML.
        if len(selected) == 1:
            p = self._dashboard_path()
            if p and p.exists():
                self.write(f"Abriendo dashboard {selected[0]}: {p}")
                if os.name == "nt":
                    os.startfile(str(p))
                return

            carpeta = self._result_folder()
            messagebox.showwarning(
                "Dashboard",
                f"TodavÃ­a no encuentro el HTML de {selected[0]}.\n\n"
                f"Revisa la carpeta:\n{carpeta}"
            )
            self.open_result_folder()
            return

        # Si fueron varios monitores, usa el consolidado GENERAL.
        d, e, x = finalize()
        self.write(f"Dashboard general actualizado. Limpieza: {d}")
        if os.name == "nt":
            os.startfile(str(e))

if __name__ == "__main__":
    App().mainloop()

