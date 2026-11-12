# Cliente RESTCONF con interfaz gráfica (Tkinter)
# Unidad 4 - Actividad 2: GET, PUT, DELETE, barra de estado y conexión SSH

import json                         # Manejo de datos JSON
import threading                    # Evita que la ventana se congele con SSH
import requests                     # Peticiones HTTP/REST
import tkinter as tk                # Interfaz gráfica
from tkinter import ttk, messagebox
from urllib.parse import quote      # Codifica nombres como 1/0/1
from netmiko import ConnectHandler  # Conexión SSH a equipos Cisco

# Oculta advertencias SSL (certificado autofirmado)
requests.packages.urllib3.disable_warnings()

# Encabezados RESTCONF
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-type": "application/yang-data+json"
}

# Colores de la barra de estado
VERDE = "#2e7d32"
ROJO = "#c62828"
AZUL = "#1565c0"
GRIS = "#616161"

# Comandos que se ejecutan por SSH al conectar
COMANDOS_SSH = [
    "show version | include Version|uptime|Model|Serial",
    "show ip interface brief",
]


# ---------- Datos capturados en la GUI ----------
def base_url():
    return "https://{}/restconf/data/ietf-interfaces:interfaces".format(
        entry_host.get().strip())


def credenciales():
    return (entry_user.get().strip(), entry_pass.get())


def es_loopback(nombre):
    # El formulario crea interfaces softwareLoopback, así que solo se
    # permiten nombres Loopback (protege los puertos físicos del switch)
    return nombre.lower().startswith("loopback")


# ---------- Barra de estado ----------
def poner_estado(texto, color):
    barra_estado.config(text=texto, bg=color)
    ventana.update_idletasks()


def texto_por_codigo(codigo):
    mensajes = {
        400: "Error 400: petición incorrecta (revisa los datos)",
        401: "Error 401: usuario o contraseña incorrectos",
        403: "Error 403: sin permisos para esta operación",
        404: "Error 404: interfaz no encontrada",
        409: "Error 409: conflicto con la configuración existente",
        500: "Error 500: error interno del switch",
    }
    return mensajes.get(codigo, "Error {}: respuesta inesperada".format(codigo))


def texto_por_excepcion(error):
    if isinstance(error, requests.exceptions.Timeout):
        return "Tiempo agotado: el switch no responde (¿VPN conectada?)"
    if isinstance(error, requests.exceptions.ConnectionError):
        return "Sin conexión con el switch (¿VPN conectada?)"
    return "Error inesperado: {}".format(error)


# ---------- Conexión SSH y datos del switch ----------
def mostrar_info(texto):
    txt_info.config(state="normal")
    txt_info.delete("1.0", "end")
    txt_info.insert("end", texto)
    txt_info.config(state="disabled")


def abrir_conexion_ssh(host, usuario, clave):
    # Primer intento: negociación normal
    dispositivo = {
        "device_type": "cisco_xe",
        "host": host,
        "username": usuario,
        "password": clave,
        "conn_timeout": 30,
        "banner_timeout": 30,
        "auth_timeout": 30,
        "timeout": 30,
        "fast_cli": False,
    }
    try:
        return ConnectHandler(**dispositivo)
    except Exception as primer_error:
        # Si fue un problema de credenciales o de red, no tiene caso reintentar
        nombre = type(primer_error).__name__
        if "Authentication" in nombre or "Timeout" in nombre:
            raise
        print("Primer intento SSH falló:", repr(primer_error))

    # Segundo intento: cifrados antiguos que algunos switches Cisco requieren
    dispositivo["disabled_algorithms"] = {}
    dispositivo["ssh_config_file"] = None
    return ConnectHandler(**dispositivo)


def conectar_ssh():
    host = entry_host.get().strip()
    usuario, clave = credenciales()
    if host == "" or usuario == "" or clave == "":
        messagebox.showwarning("Aviso", "Captura IP, usuario y contraseña del switch")
        return

    boton_ssh.config(state="disabled")      # Evita abrir dos sesiones a la vez
    poner_estado("Conectando por SSH a {}...".format(host), AZUL)

    def tarea():
        # Se ejecuta en un hilo aparte para que la ventana no se congele
        resultado = None
        mensaje_error = None
        try:
            conexion = abrir_conexion_ssh(host, usuario, clave)
            partes = []
            for comando in COMANDOS_SSH:
                partes.append("# {}\n{}".format(comando, conexion.send_command(comando)))
            conexion.disconnect()
            resultado = "\n".join(partes)
        except Exception as error:
            # Se guarda el texto ahora: 'error' deja de existir al salir del except
            print("Error SSH:", repr(error))
            detalle = str(error).strip().splitlines()
            mensaje_error = "SSH: {} {}".format(
                type(error).__name__, detalle[0][:110] if detalle else "")

        def terminar():
            boton_ssh.config(state="normal")
            if mensaje_error:
                poner_estado(mensaje_error, ROJO)
            else:
                mostrar_info(resultado)
                poner_estado("Conectado por SSH a {}".format(host), VERDE)

        ventana.after(0, terminar)

    threading.Thread(target=tarea, daemon=True).start()


def limpiar_info():
    mostrar_info("")
    poner_estado("Listo", GRIS)


# ---------- Consultar Interfaz (Desafío 1) ----------
def consultar_interfaz(evento=None):
    nombre = entry_nombre.get().strip()
    if nombre == "":
        messagebox.showwarning("Aviso", "Escribe el nombre de una interfaz")
        return

    for fila in tabla.get_children():
        tabla.delete(fila)

    url = base_url() + "/interface=" + quote(nombre, safe="")
    poner_estado("Consultando...", AZUL)

    try:
        resp = requests.get(url, auth=credenciales(), headers=HEADERS,
                            verify=False, timeout=10)
        print("GET", url, "->", resp.status_code)

        if resp.status_code != 200:
            poner_estado(texto_por_codigo(resp.status_code), ROJO)
            return

        datos = resp.json()["ietf-interfaces:interface"]
        if isinstance(datos, list):
            datos = datos[0]

        estado = "Activa" if datos.get("enabled") else "Inactiva"

        ip = "Sin IP"
        mascara = "-"
        direcciones = datos.get("ietf-ip:ipv4", {}).get("address", [])
        if direcciones:
            ip = direcciones[0].get("ip", "Sin IP")
            mascara = direcciones[0].get("netmask", "-")

        tabla.insert("", "end", values=(datos.get("name", nombre), ip, mascara, estado))
        poner_estado("Operación exitosa (código {})".format(resp.status_code), VERDE)

    except Exception as error:
        print("Error:", error)
        poner_estado(texto_por_excepcion(error), ROJO)


# ---------- Crear/Actualizar Interfaz (Desafío 2) ----------
def crear_interfaz():
    nombre = entry_f_nombre.get().strip()
    ip = entry_f_ip.get().strip()
    mascara = entry_f_mascara.get().strip()
    descripcion = entry_f_desc.get().strip()

    if nombre == "" or ip == "" or mascara == "":
        messagebox.showwarning("Aviso", "Nombre, IP y máscara son obligatorios")
        return

    if not es_loopback(nombre):
        messagebox.showwarning(
            "Aviso", "Este formulario solo crea interfaces Loopback.\n"
                     "Usa un nombre como Loopback99.")
        return

    # Arma dinámicamente el diccionario yangConfig con los datos del formulario
    yangConfig = {
        "ietf-interfaces:interface": {
            "name": nombre,
            "description": descripcion,
            "type": "iana-if-type:softwareLoopback",
            "enabled": True,
            "ietf-ip:ipv4": {
                "address": [
                    {
                        "ip": ip,
                        "netmask": mascara
                    }
                ]
            },
            "ietf-ip:ipv6": {}
        }
    }

    url = base_url() + "/interface=" + quote(nombre, safe="")
    poner_estado("Enviando configuración...", AZUL)

    try:
        resp = requests.put(url, data=json.dumps(yangConfig), auth=credenciales(),
                            headers=HEADERS, verify=False, timeout=10)
        print("PUT", url, "->", resp.status_code)

        if resp.status_code in (200, 201, 204):
            poner_estado("Operación exitosa (código {})".format(resp.status_code), VERDE)
            messagebox.showinfo("Éxito", "Interfaz {} creada/actualizada.\nCódigo: {}"
                                .format(nombre, resp.status_code))
        else:
            poner_estado(texto_por_codigo(resp.status_code), ROJO)

    except Exception as error:
        print("Error:", error)
        poner_estado(texto_por_excepcion(error), ROJO)


# ---------- Eliminar Interfaz (Desafío 3) ----------
def eliminar_interfaz():
    nombre = entry_f_nombre.get().strip()
    if nombre == "":
        nombre = entry_nombre.get().strip()

    if nombre == "":
        messagebox.showwarning("Aviso", "Escribe el nombre de la interfaz a eliminar")
        return

    if not es_loopback(nombre):
        messagebox.showwarning(
            "Aviso", "Por seguridad solo se pueden eliminar interfaces Loopback.\n"
                     "No se borrarán puertos físicos del switch.")
        return

    confirmar = messagebox.askyesno(
        "Confirmar eliminación",
        "¿Seguro que deseas eliminar la interfaz {}?\nEsta acción no se puede deshacer."
        .format(nombre))

    if not confirmar:
        poner_estado("Eliminación cancelada", GRIS)
        return

    url = base_url() + "/interface=" + quote(nombre, safe="")
    poner_estado("Eliminando...", AZUL)

    try:
        resp = requests.delete(url, auth=credenciales(), headers=HEADERS,
                               verify=False, timeout=10)
        print("DELETE", url, "->", resp.status_code)

        if resp.status_code in (200, 204):
            poner_estado("Operación exitosa (código {})".format(resp.status_code), VERDE)
            messagebox.showinfo("Éxito", "Interfaz {} eliminada.\nCódigo: {}"
                                .format(nombre, resp.status_code))
        else:
            poner_estado(texto_por_codigo(resp.status_code), ROJO)

    except Exception as error:
        print("Error:", error)
        poner_estado(texto_por_excepcion(error), ROJO)


# ---------- Ventana principal ----------
ventana = tk.Tk()
ventana.title("Cliente RESTCONF - Catalyst 9300")
ventana.geometry("760x860")

# Barra de estado (se empaqueta primero para que quede abajo)
barra_estado = tk.Label(ventana, text="Listo", bg=GRIS, fg="white",
                        font=("Arial", 10, "bold"), anchor="w", padx=10, pady=6)
barra_estado.pack(side="bottom", fill="x")

tk.Label(ventana, text="Cliente RESTCONF", font=("Arial", 16, "bold")).pack(pady=8)

# Sección: Conexión al switch (credenciales desde la GUI)
marco_conexion = tk.LabelFrame(ventana, text="Conexión al switch")
marco_conexion.pack(fill="x", padx=15, pady=5)

tk.Label(marco_conexion, text="Dispositivo:").grid(row=0, column=0, padx=5, pady=5)
entry_dev_nombre = tk.Entry(marco_conexion, width=10)
entry_dev_nombre.insert(0, "Cat9k.2")
entry_dev_nombre.grid(row=0, column=1)

tk.Label(marco_conexion, text="IP:").grid(row=0, column=2, padx=5)
entry_host = tk.Entry(marco_conexion, width=14)
entry_host.insert(0, "10.10.20.181")
entry_host.grid(row=0, column=3)

tk.Label(marco_conexion, text="Usuario:").grid(row=0, column=4, padx=5)
entry_user = tk.Entry(marco_conexion, width=12)
entry_user.insert(0, "developer")
entry_user.grid(row=0, column=5)

tk.Label(marco_conexion, text="Contraseña:").grid(row=0, column=6, padx=5)
entry_pass = tk.Entry(marco_conexion, width=14, show="*")
entry_pass.insert(0, "C1sco12345")
entry_pass.grid(row=0, column=7)

marco_ssh_btn = tk.Frame(marco_conexion)
marco_ssh_btn.grid(row=1, column=0, columnspan=8, pady=5)
boton_ssh = tk.Button(marco_ssh_btn, text="Conectar SSH", command=conectar_ssh)
boton_ssh.pack(side="left", padx=5)
tk.Button(marco_ssh_btn, text="Limpiar datos", command=limpiar_info).pack(side="left", padx=5)

# Sección: Consulta (Desafío 1)
marco_consulta = tk.LabelFrame(ventana, text="Consultar interfaz")
marco_consulta.pack(fill="x", padx=15, pady=5)

tk.Label(marco_consulta, text="Nombre (ej. Loopback99, GigabitEthernet1/0/1):").pack()
entry_nombre = tk.Entry(marco_consulta, width=30)
entry_nombre.pack(pady=5)
entry_nombre.bind("<Return>", consultar_interfaz)   # Enter también consulta

tk.Button(marco_consulta, text="Consultar Interfaz", command=consultar_interfaz).pack(pady=5)

columnas = ("Interfaz", "IP", "Máscara", "Estado")
tabla = ttk.Treeview(marco_consulta, columns=columnas, show="headings", height=3)
for col in columnas:
    tabla.heading(col, text=col)
    tabla.column(col, width=150, anchor="center")
tabla.pack(pady=8, padx=10)

# Sección: Formulario (Desafíos 2 y 3)
marco_form = tk.LabelFrame(ventana, text="Crear / Actualizar / Eliminar interfaz (Loopback)")
marco_form.pack(fill="x", padx=15, pady=5)

tk.Label(marco_form, text="Nombre de interfaz:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
entry_f_nombre = tk.Entry(marco_form, width=30)
entry_f_nombre.grid(row=0, column=1, pady=3)

tk.Label(marco_form, text="Dirección IP:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
entry_f_ip = tk.Entry(marco_form, width=30)
entry_f_ip.grid(row=1, column=1, pady=3)

tk.Label(marco_form, text="Máscara:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
entry_f_mascara = tk.Entry(marco_form, width=30)
entry_f_mascara.grid(row=2, column=1, pady=3)

tk.Label(marco_form, text="Descripción:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
entry_f_desc = tk.Entry(marco_form, width=30)
entry_f_desc.grid(row=3, column=1, pady=3)

marco_botones = tk.Frame(marco_form)
marco_botones.grid(row=4, column=0, columnspan=2, pady=8)
tk.Button(marco_botones, text="Crear/Actualizar Interfaz",
          command=crear_interfaz).pack(side="left", padx=5)
tk.Button(marco_botones, text="Eliminar Interfaz",
          command=eliminar_interfaz).pack(side="left", padx=5)

# Sección: Datos del switch obtenidos por SSH
marco_info = tk.LabelFrame(ventana, text="Datos del switch (SSH)")
marco_info.pack(fill="both", expand=True, padx=15, pady=5)

barra_scroll = tk.Scrollbar(marco_info)
barra_scroll.pack(side="right", fill="y")
txt_info = tk.Text(marco_info, height=10, font=("Consolas", 9), state="disabled",
                   yscrollcommand=barra_scroll.set)
txt_info.pack(side="left", fill="both", expand=True, padx=5, pady=3)
barra_scroll.config(command=txt_info.yview)

# Mantiene la ventana abierta y atenta a eventos
ventana.mainloop()