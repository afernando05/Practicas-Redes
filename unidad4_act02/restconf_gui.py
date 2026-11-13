
import ipaddress
import json
import queue
import threading
import tkinter as tk

from tkinter import messagebox, ttk
from urllib.parse import quote

import requests

# ==========================================
# CONFIGURACION GENERAL
# ==========================================

requests.packages.urllib3.disable_warnings()

ALUMNO = "José Fernando Alfaro Almanza"
IP_ROUTER = "10.10.20.48"
INTERFAZ_PRUEBA = "Loopback99"

BASE_RESTCONF = "/restconf/data/ietf-interfaces:interfaces"

HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json"
}

AZUL = "#1565C0"
VERDE = "#217A37"
ROJO = "#B3261E"
FONDO = "#F4F6FA"


# ==========================================
# INTERPRETAR RESPUESTAS RESTCONF
# ==========================================

def extraer_interfaz(datos, nombre):

    if not isinstance(datos, dict):
        return None

    info = datos.get(
        "ietf-interfaces:interface",
        datos.get("interface")
    )

    if info is None:
        contenedor = datos.get(
            "ietf-interfaces:interfaces",
            datos.get("interfaces", {})
        )

        if isinstance(contenedor, dict):
            info = contenedor.get("interface")

    # Corregir respuestas tipo lista
    if isinstance(info, list):
        return next(
            (
                item for item in info
                if isinstance(item, dict)
                and item.get("name") == nombre
            ),
            None
        )

    if isinstance(info, dict):
        if info.get("name", nombre) == nombre:
            return info

    return None


def mostrar_interfaz(info, nombre, codigo):

    ipv4 = info.get(
        "ietf-ip:ipv4",
        info.get("ipv4", {})
    )

    if not isinstance(ipv4, dict):
        ipv4 = {}

    direcciones = ipv4.get("address", [])

    if isinstance(direcciones, dict):
        direcciones = [direcciones]

    direccion = {}

    if isinstance(direcciones, list) and direcciones:
        if isinstance(direcciones[0], dict):
            direccion = direcciones[0]

    mascara = direccion.get("netmask")

    if not mascara:
        prefijo = direccion.get("prefix-length")

        if prefijo is not None:
            try:
                mascara = str(
                    ipaddress.IPv4Network(
                        f"0.0.0.0/{prefijo}"
                    ).netmask
                )
            except ValueError:
                mascara = None

    habilitada = info.get("enabled")

    if habilitada is True:
        estado_admin = "Habilitada"

    elif habilitada is False:
        estado_admin = "Deshabilitada"

    else:
        estado_admin = "No disponible"

    estado_operativo = info.get(
        "oper-status",
        "No disponible en esta consulta"
    )

    return (
        f"Interfaz: {info.get('name', nombre)}\n"
        f"Descripción: {info.get('description', 'Sin descripción')}\n"
        f"Dirección IP: {direccion.get('ip', 'Sin IP')}\n"
        f"Máscara: {mascara or 'No disponible'}\n"
        f"Estado administrativo: {estado_admin}\n"
        f"Estado operativo: {estado_operativo}\n"
        f"Código HTTP: {codigo}"
    )


# ==========================================
# CLASE PRINCIPAL DE LA APLICACION
# ==========================================

class AdministradorRESTCONF:

    def __init__(self):

        self.ventana = tk.Tk()

        self.ventana.title(
            "Administrador RESTCONF - Unidad 4"
        )

        self.ventana.geometry("820x740")
        self.ventana.minsize(720, 650)
        self.ventana.configure(bg=FONDO)

        self.cola = queue.Queue()
        self.ocupado = False
        self.formulario = None
        self.botones_formulario = []

        self.crear_ventana()

        self.ventana.after(
            100,
            self.revisar_respuestas
        )

    # ======================================
    # CREAR VENTANA PRINCIPAL
    # ======================================

    def crear_ventana(self):

        cabecera = tk.Frame(
            self.ventana,
            bg=FONDO
        )

        cabecera.pack(
            fill="x",
            padx=18,
            pady=(14, 7)
        )

        tk.Label(
            cabecera,
            text="Administrador de Interfaces RESTCONF",
            font=("Arial", 19, "bold"),
            bg=FONDO
        ).pack()

        tk.Label(
            cabecera,
            text="Cisco Catalyst 8000v - Python + Tkinter",
            font=("Arial", 11),
            bg=FONDO
        ).pack(pady=3)

        # Nombre del alumno
        tk.Label(
            cabecera,
            text=f"Realizado por: {ALUMNO}",
            font=("Arial", 12, "bold"),
            bg=FONDO,
            fg=AZUL
        ).pack(pady=4)

        # ==================================
        # DATOS DE CONEXION
        # ==================================

        conexion = ttk.LabelFrame(
            self.ventana,
            text="DATOS DE CONEXIÓN",
            padding=12
        )

        conexion.pack(
            fill="x",
            padx=20,
            pady=5
        )

        conexion.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            conexion,
            text="IP del router:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=6,
            pady=5
        )

        self.entrada_host = ttk.Entry(
            conexion,
            width=38
        )

        self.entrada_host.insert(
            0,
            IP_ROUTER
        )

        self.entrada_host.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6,
            pady=5
        )

        ttk.Label(
            conexion,
            text="Usuario:"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=6,
            pady=5
        )

        self.entrada_usuario = ttk.Entry(
            conexion
        )

        self.entrada_usuario.insert(
            0,
            "developer"
        )

        self.entrada_usuario.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=6,
            pady=5
        )

        ttk.Label(
            conexion,
            text="Contraseña:"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=6,
            pady=5
        )

        self.entrada_password = ttk.Entry(
            conexion,
            show="*"
        )

        self.entrada_password.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=6,
            pady=5
        )

        # ==================================
        # ADMINISTRACION DE INTERFACES
        # ==================================

        controles = ttk.LabelFrame(
            self.ventana,
            text="ADMINISTRACIÓN DE INTERFACES",
            padding=12
        )

        controles.pack(
            fill="x",
            padx=20,
            pady=7
        )

        fila_interfaz = ttk.Frame(
            controles
        )

        fila_interfaz.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            fila_interfaz,
            text="Nombre de interfaz:"
        ).pack(side="left")

        self.entrada_interfaz = ttk.Entry(
            fila_interfaz,
            width=35
        )

        self.entrada_interfaz.insert(
            0,
            INTERFAZ_PRUEBA
        )

        self.entrada_interfaz.pack(
            side="left",
            padx=12,
            fill="x",
            expand=True
        )

        # ==================================
        # BOTONES PRINCIPALES
        # ==================================

        fila_botones = ttk.Frame(
            controles
        )

        fila_botones.pack(fill="x")

        # GET
        self.boton_get = tk.Button(
            fila_botones,
            text="Consultar (GET)",
            command=self.consultar,
            bg=AZUL,
            fg="white",
            font=("Arial", 10, "bold"),
            width=20
        )

        self.boton_get.pack(
            side="left",
            expand=True,
            padx=4
        )

        # POST / PUT
        self.boton_formulario = tk.Button(
            fila_botones,
            text="Crear / Actualizar",
            command=self.abrir_formulario,
            bg=VERDE,
            fg="white",
            font=("Arial", 10, "bold"),
            width=20
        )

        self.boton_formulario.pack(
            side="left",
            expand=True,
            padx=4
        )

        # DELETE
        self.boton_delete = tk.Button(
            fila_botones,
            text="Eliminar (DELETE)",
            command=self.eliminar,
            bg=ROJO,
            fg="white",
            font=("Arial", 10, "bold"),
            width=20
        )

        self.boton_delete.pack(
            side="left",
            expand=True,
            padx=4
        )

        # ==================================
        # AREA DE RESULTADOS
        # ==================================

        panel_resultados = ttk.LabelFrame(
            self.ventana,
            text="RESULTADOS",
            padding=10
        )

        panel_resultados.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(4, 8)
        )

        panel_resultados.columnconfigure(
            0,
            weight=1
        )

        panel_resultados.rowconfigure(
            0,
            weight=1
        )

        self.resultado = tk.Text(
            panel_resultados,
            wrap="word",
            font=("Consolas", 10),
            height=10,
            state="disabled"
        )

        self.resultado.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        barra = ttk.Scrollbar(
            panel_resultados,
            command=self.resultado.yview
        )

        barra.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.resultado.config(
            yscrollcommand=barra.set
        )

        # ==================================
        # INDICADOR DE ESTADO
        # ==================================

        self.estado = tk.Label(
            self.ventana,
            text="Listo para consultar",
            font=("Arial", 11, "bold"),
            bg="#E3EEFF",
            fg=AZUL,
            pady=9
        )

        self.estado.pack(
            fill="x",
            padx=20,
            pady=(0, 14)
        )

    # ======================================
    # MOSTRAR RESULTADOS
    # ======================================

    def escribir(self, texto):

        self.resultado.config(
            state="normal"
        )

        self.resultado.delete(
            "1.0",
            tk.END
        )

        self.resultado.insert(
            tk.END,
            texto
        )

        self.resultado.config(
            state="disabled"
        )

    # ======================================
    # INDICADOR DE ESTADO
    # ======================================

    def indicar_estado(
        self,
        mensaje,
        correcto=None
    ):

        if correcto is True:
            fondo = "#E1F4E5"
            letra = VERDE

        elif correcto is False:
            fondo = "#FFE8E6"
            letra = ROJO

        else:
            fondo = "#E3EEFF"
            letra = AZUL

        self.estado.config(
            text=mensaje,
            bg=fondo,
            fg=letra
        )

    # ======================================
    # OBTENER DATOS DE CONEXION
    # ======================================

    def conexion(self):

        host = self.entrada_host.get().strip()
        usuario = self.entrada_usuario.get().strip()
        password = self.entrada_password.get()

        if not (host and usuario and password):

            messagebox.showwarning(
                "Faltan datos",
                "Escribe la IP, el usuario y la contraseña.",
                parent=self.ventana
            )

            return None

        try:
            ipaddress.IPv4Address(host)

        except ValueError:

            messagebox.showerror(
                "IP inválida",
                "Escribe una dirección IPv4 válida.",
                parent=self.ventana
            )

            return None

        return host, (usuario, password)

    # ======================================
    # BLOQUEAR BOTONES DURANTE PETICIONES
    # ======================================

    def bloquear_botones(self, bloquear):

        self.ocupado = bloquear

        estado = (
            "disabled" if bloquear
            else "normal"
        )

        botones = [
            self.boton_get,
            self.boton_formulario,
            self.boton_delete,
            *self.botones_formulario
        ]

        for boton in botones:

            if boton.winfo_exists():
                boton.config(state=estado)

    # ======================================
    # ENVIAR PETICIONES RESTCONF
    # ======================================

    def enviar(
        self,
        metodo,
        recurso,
        configuracion=None,
        al_terminar=None
    ):

        if self.ocupado:
            return

        datos = self.conexion()

        if datos is None:
            return

        host, autenticacion = datos

        url = (
            f"https://{host}"
            f"{BASE_RESTCONF}"
            f"{recurso}"
        )

        self.bloquear_botones(True)

        self.indicar_estado(
            f"Procesando {metodo}..."
        )

        # Ejecutar peticion sin congelar Tkinter
        def tarea():

            try:
                respuesta = requests.request(
                    metodo,
                    url,
                    auth=autenticacion,
                    headers=HEADERS,
                    json=configuracion,
                    verify=False,
                    timeout=(5, 20)
                )

                try:
                    contenido = respuesta.json()

                except ValueError:
                    contenido = respuesta.text

                self.cola.put((
                    "respuesta",
                    metodo,
                    respuesta.status_code,
                    contenido,
                    al_terminar
                ))

            except requests.exceptions.RequestException as error:

                self.cola.put((
                    "error",
                    metodo,
                    str(error),
                    None,
                    None
                ))

        threading.Thread(
            target=tarea,
            daemon=True
        ).start()

    # ======================================
    # PROCESAR RESPUESTAS DEL ROUTER
    # ======================================

    def revisar_respuestas(self):

        try:

            while True:

                (
                    tipo,
                    metodo,
                    codigo,
                    contenido,
                    al_terminar
                ) = self.cola.get_nowait()

                self.bloquear_botones(False)

                if tipo == "error":

                    self.indicar_estado(
                        "Error de conexión",
                        correcto=False
                    )

                    self.escribir(
                        f"No se pudo completar {metodo}:\n"
                        f"{codigo}"
                    )

                    continue

                # Manejar errores HTTP
                if not (200 <= codigo < 300):

                    explicaciones = {
                        400: "Datos de solicitud inválidos.",
                        401: "Usuario o contraseña incorrectos.",
                        403: "No tienes permisos.",
                        404: "La interfaz no existe.",
                        405: "Método no permitido.",
                        409: "La interfaz ya existe o hay conflicto.",
                        500: "Error interno del router."
                    }

                    resumen = explicaciones.get(
                        codigo,
                        "Falló la solicitud RESTCONF."
                    )

                    if isinstance(
                        contenido,
                        (dict, list)
                    ):
                        detalle = json.dumps(
                            contenido,
                            ensure_ascii=False
                        )
                    else:
                        detalle = str(contenido)

                    self.indicar_estado(
                        f"Error HTTP {codigo}: {resumen}",
                        False
                    )

                    self.escribir(
                        f"Método: {metodo}\n"
                        f"HTTP: {codigo}\n"
                        f"{resumen}\n\n"
                        f"Detalles del router:\n"
                        f"{detalle[:800]}"
                    )

                    continue

                # Respuesta correcta
                self.indicar_estado(
                    f"Operación {metodo} aceptada - HTTP {codigo}",
                    True
                )

                if al_terminar is not None:
                    al_terminar(
                        codigo,
                        contenido
                    )

        except queue.Empty:
            pass

        self.ventana.after(
            100,
            self.revisar_respuestas
        )

    # ======================================
    # CONSULTAR INTERFAZ - GET
    # ======================================

    def consultar(self):

        nombre = self.entrada_interfaz.get().strip()

        if not nombre:

            messagebox.showwarning(
                "Falta interfaz",
                "Escribe el nombre de la interfaz.",
                parent=self.ventana
            )

            return

        recurso = (
            "/interface="
            + quote(nombre, safe="")
        )

        def mostrar(codigo, contenido):

            if not isinstance(contenido, dict):

                self.escribir(
                    "El router no devolvió un JSON válido."
                )

                self.indicar_estado(
                    "Respuesta inesperada",
                    False
                )

                return

            info = extraer_interfaz(
                contenido,
                nombre
            )

            if info is None:

                self.escribir(
                    "No se encontró información de la interfaz."
                )

                self.indicar_estado(
                    "Datos no disponibles",
                    False
                )

                return

            self.escribir(
                mostrar_interfaz(
                    info,
                    nombre,
                    codigo
                )
            )

        self.enviar(
            "GET",
            recurso,
            al_terminar=mostrar
        )

    # ======================================
    # FORMULARIO DE CONFIGURACION
    # ======================================

    def abrir_formulario(self):

        if self.formulario is not None:

            if self.formulario.winfo_exists():
                self.formulario.lift()
                return

        form = tk.Toplevel(
            self.ventana
        )

        self.formulario = form

        form.title(
            "Crear / Actualizar interfaz"
        )

        form.geometry("510x480")
        form.resizable(False, False)
        form.configure(bg=FONDO)
        form.transient(self.ventana)

        tk.Label(
            form,
            text="CONFIGURACIÓN DE INTERFAZ",
            font=("Arial", 15, "bold"),
            bg=FONDO
        ).pack(pady=(15, 5))

        # Nombre del alumno
        tk.Label(
            form,
            text=f"Alumno: {ALUMNO}",
            font=("Arial", 11, "bold"),
            fg=AZUL,
            bg=FONDO
        ).pack(pady=(0, 12))

        caja = ttk.Frame(
            form,
            padding=10
        )

        caja.pack(
            fill="x",
            padx=16
        )

        caja.columnconfigure(
            1,
            weight=1
        )

        entradas = {}

        campos = [
            ("Nombre", "Loopback99"),
            ("Dirección IP", "99.99.99.99"),
            ("Máscara", "255.255.255.0"),
            ("Descripción", "Interfaz de prueba")
        ]

        for fila, (etiqueta, inicial) in enumerate(campos):

            ttk.Label(
                caja,
                text=f"{etiqueta}:"
            ).grid(
                row=fila,
                column=0,
                sticky="w",
                padx=7,
                pady=10
            )

            entrada = ttk.Entry(
                caja,
                width=34
            )

            entrada.insert(
                0,
                inicial
            )

            entrada.grid(
                row=fila,
                column=1,
                sticky="ew",
                padx=7,
                pady=10
            )

            entradas[etiqueta] = entrada

        tk.Label(
            form,
            text="Por seguridad, solo se modifica Loopback99.",
            bg=FONDO,
            fg=ROJO,
            font=("Arial", 10)
        ).pack(pady=6)

        fila_botones = ttk.Frame(
            form
        )

        fila_botones.pack(pady=10)

        # Boton POST
        boton_post = tk.Button(
            fila_botones,
            text="Crear (POST)",
            bg=AZUL,
            fg="white",
            font=("Arial", 10, "bold"),
            width=19,
            command=lambda: self.guardar_interfaz(
                "POST",
                entradas
            )
        )

        boton_post.pack(
            side="left",
            padx=5
        )

        # Boton PUT
        boton_put = tk.Button(
            fila_botones,
            text="Crear / Actualizar (PUT)",
            bg=VERDE,
            fg="white",
            font=("Arial", 10, "bold"),
            width=22,
            command=lambda: self.guardar_interfaz(
                "PUT",
                entradas
            )
        )

        boton_put.pack(
            side="left",
            padx=5
        )

        self.botones_formulario = [
            boton_post,
            boton_put
        ]

        def cerrar():

            self.botones_formulario = []
            self.formulario = None

            form.destroy()

        form.protocol(
            "WM_DELETE_WINDOW",
            cerrar
        )

    # ======================================
    # CREAR / ACTUALIZAR - POST / PUT
    # ======================================

    def guardar_interfaz(
        self,
        metodo,
        entradas
    ):

        nombre = entradas["Nombre"].get().strip()

        direccion = entradas[
            "Dirección IP"
        ].get().strip()

        mascara = entradas[
            "Máscara"
        ].get().strip()

        descripcion = entradas[
            "Descripción"
        ].get().strip()

        if not all((
            nombre,
            direccion,
            mascara,
            descripcion
        )):

            messagebox.showwarning(
                "Campos incompletos",
                "Completa los cuatro campos.",
                parent=self.formulario
            )

            return

        # Proteger interfaces importantes
        if nombre != INTERFAZ_PRUEBA:

            messagebox.showwarning(
                "Interfaz protegida",
                "Solo se permite modificar Loopback99.",
                parent=self.formulario
            )

            return

        # Validar IP y mascara
        try:

            ipaddress.IPv4Address(
                direccion
            )

            mascara = str(
                ipaddress.IPv4Network(
                    f"0.0.0.0/{mascara}"
                ).netmask
            )

        except ValueError:

            messagebox.showerror(
                "IP o máscara inválida",
                "Verifica la dirección IP y la máscara.",
                parent=self.formulario
            )

            return

        # Confirmar configuracion
        confirmar = messagebox.askyesno(
            "Confirmar operación",
            f"¿Enviar {metodo} para configurar {nombre}?",
            parent=self.formulario
        )

        if not confirmar:
            return

        # Crear diccionario YANG
        yangConfig = {
            "ietf-interfaces:interface": {
                "name": nombre,
                "description": descripcion,
                "type": "iana-if-type:softwareLoopback",
                "enabled": True,
                "ietf-ip:ipv4": {
                    "address": [
                        {
                            "ip": direccion,
                            "netmask": mascara
                        }
                    ]
                },
                "ietf-ip:ipv6": {}
            }
        }

        # POST crea en la coleccion
        # PUT crea o actualiza interfaz
        if metodo == "POST":
            recurso = ""

        else:
            recurso = (
                "/interface="
                + quote(nombre, safe="")
            )

        def mostrar_exito(
            codigo,
            contenido
        ):

            self.entrada_interfaz.delete(
                0,
                tk.END
            )

            self.entrada_interfaz.insert(
                0,
                nombre
            )

            self.escribir(
                f"Interfaz: {nombre}\n"
                f"Operación: {metodo}\n"
                f"IP enviada: {direccion}\n"
                f"Máscara: {mascara}\n"
                f"Descripción: {descripcion}\n"
                f"HTTP: {codigo}\n\n"
                "Presiona Consultar (GET) "
                "para verificar los datos."
            )

            messagebox.showinfo(
                "Operación aceptada",
                f"El router aceptó {metodo} de {nombre}.\n"
                f"HTTP: {codigo}",
                parent=self.ventana
            )

        self.enviar(
            metodo,
            recurso,
            yangConfig,
            mostrar_exito
        )

    # ======================================
    # ELIMINAR INTERFAZ - DELETE
    # ======================================

    def eliminar(self):

        nombre = self.entrada_interfaz.get().strip()

        # Proteger interfaces fisicas
        if nombre != INTERFAZ_PRUEBA:

            messagebox.showwarning(
                "Interfaz protegida",
                "Solo se permite eliminar Loopback99.\n"
                "No modificaremos GigabitEthernet1.",
                parent=self.ventana
            )

            return

        # Confirmar eliminacion
        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Seguro que deseas eliminar {nombre}?",
            icon="warning",
            parent=self.ventana
        )

        if not confirmar:
            return

        recurso = (
            "/interface="
            + quote(nombre, safe="")
        )

        def mostrar_exito(
            codigo,
            contenido
        ):

            self.escribir(
                f"DELETE solicitado para: {nombre}\n"
                f"HTTP: {codigo}\n\n"
                "Presiona Consultar (GET) "
                "para confirmar que ya no existe."
            )

            messagebox.showinfo(
                "Solicitud de eliminación aceptada",
                f"DELETE {nombre}: HTTP {codigo}\n"
                "Verifica la eliminación con GET.",
                parent=self.ventana
            )

        self.enviar(
            "DELETE",
            recurso,
            al_terminar=mostrar_exito
        )

    # ======================================
    # INICIAR APLICACION
    # ======================================

    def iniciar(self):
        self.ventana.mainloop()


# ==========================================
# EJECUCION PRINCIPAL
# ==========================================

if __name__ == "__main__":
    AdministradorRESTCONF().iniciar()

