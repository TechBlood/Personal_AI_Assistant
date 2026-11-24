import tkinter as tk
import customtkinter as ctk
import speech_recognition as sr
import threading
import time
import queue
import sys
import os
import json  # <-- NUEVO: Para procesar las lecturas offline de Vosk
from PIL import Image, ImageSequence
from cerebro_ia import CerebroInteligente
from acciones import ControladorSistema

# Intentar importar librerías offline; si no están, se lo advertimos al usuario
try:
    import sounddevice as sd
    from vosk import Model, KaldiRecognizer
    VOSK_DISPONIBLE = True
except ImportError:
    VOSK_DISPONIBLE = False

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AplicacionAsistente(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Asistente Virtual Inteligente")
        self.geometry("650x560")
        self.resizable(False, False)
        self.configure(fg_color="#0A0B0D")

        self.cerebro = CerebroInteligente()
        self.controlador = ControladorSistema()
        self.cola_voz = queue.Queue()
        
        self.nombre_asistente = "friday"
        self.ultimo_tiempo_actividad = time.time()
        self.asistente_activo = True
        
        self.frames_gif = []
        self.indice_frame = 0
        self.ruta_avatar = "avatar.gif"
        
        threading.Thread(target=self._procesador_hilo_voz, daemon=True).start()
        
        # --- DISEÑO DE LA INTERFAZ ---
        self.marco_titulo = ctk.CTkFrame(self, fg_color="#111318", corner_radius=8, border_width=1, border_color="#1E222B")
        self.marco_titulo.pack(pady=(15, 5), fill="x", padx=45)

        self.etiqueta_titulo = ctk.CTkLabel(
            self.marco_titulo, 
            text=f"SISTEMA IA HÍBRIDO LOCAL - {self.nombre_asistente.upper()}", 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#00D2FF"
        )
        self.etiqueta_titulo.pack(pady=8)

        self.marco_avatar_interno = ctk.CTkFrame(self, fg_color="transparent", width=140, height=140)
        self.marco_avatar_interno.pack(pady=8)
        self.marco_avatar_interno.pack_propagate(False)

        self.etiqueta_avatar = ctk.CTkLabel(self.marco_avatar_interno, text="IA", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#1E222B")
        self.etiqueta_avatar.pack(expand=True)

        threading.Thread(target=self.cargar_frames_avatar_background, daemon=True).start()

        # === CAMBIO: Texto inicial en modo espera local ===
        self.etiqueta_microfono = ctk.CTkLabel(
            self, 
            text="Iniciando sistema de escucha...", 
            text_color="#00FF66", 
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic", weight="bold")
        )
        self.etiqueta_microfono.pack(pady=3)

        self.caja_texto_estado = ctk.CTkTextbox(
            self, 
            width=560, 
            height=150, 
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#050608",
            border_width=1,
            border_color="#1E222B",
            corner_radius=8,
            text_color="#D1D5DB"
        )
        self.caja_texto_estado.pack(pady=8)
        self.caja_texto_estado.insert("0.0", f"[SISTEMA] >> {self.nombre_asistente.capitalize()}: Núcleo operativo inicializado correctamente.\n\n")
        self.caja_texto_estado.configure(state="disabled")

        self.marco_entrada = ctk.CTkFrame(self, fg_color="transparent")
        self.marco_entrada.pack(pady=10, fill="x", padx=45)

        self.campo_texto = ctk.CTkEntry(
            self.marco_entrada, 
            placeholder_text=f"Escribe '{self.nombre_asistente.capitalize()} [comando]' aquí...", 
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#111318",
            border_color="#232833",
            height=38,
            corner_radius=8
        )
        self.campo_texto.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.campo_texto.bind("<Return>", lambda evento: self.procesar_entrada_texto())

        self.boton_enviar = ctk.CTkButton(
            self.marco_entrada, 
            text="EJECUTAR", 
            width=110, 
            height=38,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#007ACC",
            hover_color="#005999",
            corner_radius=8,
            command=self.procesar_entrada_texto
        )
        self.boton_enviar.pack(side="right")

        threading.Thread(target=self.bucle_escucha_voz, daemon=True).start()

        # === BIENVENIDA AUDIBLE AL INICIAR ===
        self.after(1000, lambda: self.decir_texto(f"Hola, soy {self.nombre_asistente.capitalize()}, tu asistente virtual inteligente. ¿En qué puedo ayudarte hoy?"))

    def cargar_frames_avatar_background(self):
        if os.path.exists(self.ruta_avatar):
            try:
                img_gif = Image.open(self.ruta_avatar)
                temp_frames = []
                for frame in ImageSequence.Iterator(img_gif):
                    frame_redimensionado = frame.resize((140, 140), Image.Resampling.BILINEAR)
                    ctk_img = ctk.CTkImage(light_image=frame_redimensionado, dark_image=frame_redimensionado, size=(140, 140))
                    temp_frames.append(ctk_img)
                self.frames_gif = temp_frames
                if self.frames_gif:
                    self.after(0, lambda: self.etiqueta_avatar.configure(text=""))
                    self.after(0, self.animar_avatar)
            except Exception as e:
                print(f"[ERROR AVATAR]: {e}")

    def animar_avatar(self):
        if self.asistente_activo and self.frames_gif:
            self.indice_frame = (self.indice_frame + 1) % len(self.frames_gif)
            self.etiqueta_avatar.configure(image=self.frames_gif[self.indice_frame])
            self.after(50, self.animar_avatar)

    def registrar_log(self, remitente, mensaje):
        self.caja_texto_estado.configure(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.caja_texto_estado.insert(tk.END, f"[{timestamp}] [{remitente.upper()}] >> {mensaje}\n\n")
        self.caja_texto_estado.see(tk.END)
        self.caja_texto_estado.configure(state="disabled")

    def decir_texto(self, texto):
        texto_estricto = str(texto)
        self.registrar_log(self.nombre_asistente, texto_estricto)
        self.cola_voz.put(texto_estricto)

    def _procesador_hilo_voz(self):
        while self.asistente_activo:
            try:
                texto_a_decir = self.cola_voz.get(timeout=0.5)
                self.after(0, lambda: self.etiqueta_microfono.configure(text="Friday está hablando...", text_color="#FFCC00"))
                
                self.controlador.hablar(texto_a_decir)
                
                self.cola_voz.task_done()
                # Volvemos a colocar el indicador en modo espera silenciosa
                self.after(0, lambda: self.etiqueta_microfono.configure(text=f"En espera ('{self.nombre_asistente.capitalize()}')...", text_color="#00FF66"))
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ERROR CRÍTICO EN TTS]: {e}")
                try: self.cola_voz.task_done()
                except: pass
                continue

    def procesar_entrada_texto(self):
        texto_usuario = self.campo_texto.get().strip()
        if texto_usuario:
            self.campo_texto.delete(0, tk.END)
            self.ultimo_tiempo_actividad = time.time()
            self.registrar_log("Usuario", texto_usuario)
            
            if self.nombre_asistente not in texto_usuario.lower():
                self.registrar_log("Sistema", f"Comando omitido. Requiere palabra clave de activación ('{self.nombre_asistente.capitalize()}').")
                return
                
            instruccion_limpia = texto_usuario.lower().replace(self.nombre_asistente, "").strip()
            self.evaluar_y_ejecutar_logica(instruccion_limpia)

    # === NUEVO BUCLE DE ESCUCHA LOCAL (VOSK) ===
    def bucle_escucha_voz(self):
        time.sleep(2)
        
        if not VOSK_DISPONIBLE:
            self.registrar_log("SISTEMA ERROR", "Faltan las dependencias 'vosk' o 'sounddevice'. Instálalas con: pip install vosk sounddevice")
            self.after(0, lambda: self.etiqueta_microfono.configure(text="Error de dependencias (Vosk)", text_color="#FF3333"))
            return

        if not os.path.exists("model"):
            self.registrar_log("SISTEMA ERROR", "No se encontró la carpeta 'model'. Descarga un modelo de Vosk en Español y nómbralo 'model'.")
            self.after(0, lambda: self.etiqueta_microfono.configure(text="Falta el modelo offline ('model')", text_color="#FF3333"))
            return

        
        try:
            modelo_vosk = Model("model")
            reconocedor_vosk = KaldiRecognizer(modelo_vosk, 16000)
        except Exception as e:
            self.registrar_log("ERROR VOSK", f"No se pudo cargar Vosk: {e}")
            return

        cola_audio = queue.Queue()

        def callback_audio(indata, frames, time_info, status):
            if status:
                sys.stderr.write(f"Status: {status}\n")
            cola_audio.put(bytes(indata))

        self.after(0, lambda: self.etiqueta_microfono.configure(text=f"En espera ('{self.nombre_asistente.capitalize()}')...", text_color="#00FF66"))

        try:
            # Capturamos audio en un flujo local de bajo consumo de CPU
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                                   channels=1, callback=callback_audio):
                
                while self.asistente_activo:
                    datos = cola_audio.get()
                    if reconocedor_vosk.AcceptWaveform(datos):
                        resultado = json.loads(reconocedor_vosk.Result())
                        texto_detectado = resultado.get("text", "")
                        
                        # Si en el flujo offline se detecta "friday"
                        if self.nombre_asistente in texto_detectado:
                            self.ultimo_tiempo_actividad = time.time()
                            
                            # Cambiamos visualmente a modo escucha activa y llamamos a Google para procesar el comando
                            self.after(0, lambda: self.etiqueta_microfono.configure(text="¿Sí? Te escucho...", text_color="#FF3366"))
                            self.registrar_log("SISTEMA", f"Palabra clave '{self.nombre_asistente.capitalize()}' detectada localmente.")
                            
                            self.capturar_comando_completo()
                            
                            # Al terminar el comando, restablecer interfaz a modo reposo
                            self.after(0, lambda: self.etiqueta_microfono.configure(text=f"En espera ('{self.nombre_asistente.capitalize()}')...", text_color="#00FF66"))
                            
        except Exception as e:
            self.registrar_log("ERROR AUDIO", f"Ocurrió un fallo en el flujo de grabación: {e}")

    # === NUEVO MÉTODO PARA CAPTURAR LA ORDEN TRAS ACTIVARSE ===
    def capturar_comando_completo(self):
        reconocedor = sr.Recognizer()
        try:
            with sr.Microphone() as origen:
                # Ajuste rápido de ruido ambiente para optimizar el tiempo de reacción (0.5s)
                reconocedor.adjust_for_ambient_noise(origen, duration=0.5)
                # Escuchamos solo durante un margen de tiempo cerrado
                audio = reconocedor.listen(origen, timeout=4, phrase_time_limit=5)
                
            texto_transcrito = reconocedor.recognize_google(audio, language="es-ES")
            self.registrar_log("Usuario (Voz)", texto_transcrito)
            
            # Limpiamos e invocamos la acción
            instruccion_limpia = texto_transcrito.lower().replace(self.nombre_asistente, "").strip()
            self.evaluar_y_ejecutar_logica(instruccion_limpia)
            
        except sr.WaitTimeoutError:
            self.registrar_log("SISTEMA", "No detecté ningún comando. Volviendo a modo de espera.")
        except sr.UnknownValueError:
            self.registrar_log("SISTEMA", "No logré procesar el comando. Volviendo a modo de espera.")
        except Exception as e:
            self.registrar_log("SISTEMA", f"Error al procesar el comando por voz: {e}")

    def evaluar_y_ejecutar_logica(self, instruccion):
        if not instruccion:
            self.decir_texto("Hola, ¿en qué puedo ayudarte?")
            return

        intencion = self.cerebro.comprender_intencion(instruccion)

        # --- LÓGICA DE NUEVAS INTENCIONES ---
        if intencion == "crear_nota":
            cuerpo = instruccion
            for r in ["crear nota", "crea una nota", "escribe una nota", "nueva nota", "escribir nota"]:
                cuerpo = cuerpo.replace(r, "")
            cuerpo = cuerpo.strip()
            
            if cuerpo.startswith("que diga"): cuerpo = cuerpo.replace("que diga", "", 1).strip()
            elif cuerpo.startswith("de"): cuerpo = cuerpo.replace("de", "", 1).strip()
            
            if cuerpo:
                self.controlador.ejecutar_crear_nota(cuerpo)
                self.decir_texto("Entendido, he guardado tu nota de texto directamente en el Escritorio.")
            else:
                self.decir_texto("No logré entender el contenido de la nota. Por favor intenta de nuevo indicando el texto.")

        elif intencion == "buscar_archivo":
            nombre_fichero = instruccion
            for r in ["buscar archivo", "busca el archivo", "encuentra el archivo", "buscar un archivo"]:
                nombre_fichero = nombre_fichero.replace(r, "")
            nombre_fichero = nombre_fichero.replace("que se llama", "").replace("llamado", "").strip()
            
            if nombre_fichero:
                self.decir_texto(f"Buscando el archivo {nombre_fichero} en tus carpetas personales...")
                
                def tarea_busqueda_asincrona():
                    coincidencias = self.controlador.ejecutar_buscar_archivo(nombre_fichero)
                    if coincidencias:
                        self.decir_texto(f"¡Lo encontré! He detectado {len(coincidencias)} coincidencias. He colocado las rutas completas en el registro.")
                        for i, (nombre_base, ruta_completa) in enumerate(coincidencias, 1):
                            self.registrar_log("BÚSQUEDA", f"[{i}] Archivo: {nombre_base}\n    Ruta completa: {ruta_completa}")
                    else:
                        self.decir_texto(f"He concluido la búsqueda superficial y no encontré ningún archivo llamado {nombre_fichero}.")
                
                threading.Thread(target=tarea_busqueda_asincrona, daemon=True).start()
            else:
                self.decir_texto("Por favor dime qué archivo deseas que busque.")

        elif intencion == "cerrar_word":
            if self.controlador.esta_aplicacion_ejecutandose("WINWORD.EXE"):
                self.decir_texto("Cerrando Microsoft Word.")
                self.controlador.ejecutar_cerrar_programa("WINWORD.EXE")
            else:
                self.decir_texto("Word no se está ejecutando actualmente.")

        elif intencion == "cerrar_excel":
            if self.controlador.esta_aplicacion_ejecutandose("EXCEL.EXE"):
                self.decir_texto("Cerrando la hoja de cálculo de Excel.")
                self.controlador.ejecutar_cerrar_programa("EXCEL.EXE")
            else:
                self.decir_texto("Excel ya está cerrado.")

        elif intencion == "cerrar_powerpoint":
            if self.controlador.esta_aplicacion_ejecutandose("POWERPNT.EXE"):
                self.decir_texto("Procedo a cerrar PowerPoint.")
                self.controlador.ejecutar_cerrar_programa("POWERPNT.EXE")
            else:
                self.decir_texto("No detecto a PowerPoint abierto.")

        elif intencion == "cerrar_fotos":
            if self.controlador.esta_aplicacion_ejecutandose("Microsoft.Photos.exe"):
                self.decir_texto("Cerrando la galería de fotos.")
                self.controlador.ejecutar_cerrar_programa("Microsoft.Photos.exe")
            else:
                self.decir_texto("El visor de fotos de Windows no está en ejecución.")

        elif intencion == "bloquear_pc":
            self.decir_texto("Entendido, procedo a bloquear el equipo de inmediato.")
            self.after(1500, self.controlador.ejecutar_bloquear_pc)

        elif intencion == "abrir_word":
            if self.controlador.esta_aplicacion_ejecutandose("WINWORD.EXE"):
                self.decir_texto("La aplicación Word ya se encuentra abierta en el sistema.")
            else:
                self.decir_texto("Abriendo Microsoft Word.")
                self.controlador.ejecutar_abrir_word()

        elif intencion == "abrir_excel":
            if self.controlador.esta_aplicacion_ejecutandose("EXCEL.EXE"):
                self.decir_texto("La aplicación Excel ya se encuentra abierta en el sistema.")
            else:
                self.decir_texto("Abriendo la hoja de cálculo de Excel.")
                self.controlador.ejecutar_abrir_excel()

        elif intencion == "abrir_powerpoint":
            if self.controlador.esta_aplicacion_ejecutandose("POWERPNT.EXE"):
                self.decir_texto("La aplicación PowerPoint ya se encuentra abierta en el sistema.")
            else:
                self.decir_texto("Abriendo PowerPoint para tus presentaciones.")
                self.controlador.ejecutar_abrir_powerpoint()

        elif intencion == "abrir_fotos":
            if self.controlador.esta_aplicacion_ejecutandose("Microsoft.Photos.exe"):
                self.decir_texto("El visor de fotos ya está en ejecución.")
            else:
                self.decir_texto("Abriendo la galería de imágenes.")
                self.controlador.ejecutar_abrir_fotos()

        elif intencion == "buscar_internet":
            termino = instruccion.replace("buscar en internet", "").replace("buscar", "").replace("busca", "").replace("en la web", "").replace("en google", "").strip()
            self.decir_texto(f"Buscando {termino} en internet.")
            self.controlador.ejecutar_buscar_internet(termino)

        elif intencion == "buscar_youtube":
            remociones = ["buscar en youtube", "reproducir", "pon un video de", "pon", "abre youtube y busca", "abre youtube", "busca", "videos de", "video de"]
            termino_video = instruccion
            for palabra in remociones:
                termino_video = termino_video.replace(palabra, "")
            termino_video = termino_video.strip()
            self.decir_texto(f"Buscando {termino_video} en YouTube.")
            self.controlador.ejecutar_buscar_youtube(termino_video)

        elif intencion == "subir_volumen":
            self.decir_texto("Subiendo el nivel del volumen.")
            self.controlador.ejecutar_control_multimedia("subir_volumen")

        elif intencion == "bajar_volumen":
            self.decir_texto("Bajando el nivel del volumen.")
            self.controlador.ejecutar_control_multimedia("bajar_volumen")

        elif intencion == "subir_brillo":
            self.decir_texto("Aumentando el brillo de la pantalla.")
            self.controlador.ejecutar_control_multimedia("subir_brillo")

        elif intencion == "bajar_brillo":
            self.decir_texto("Disminuyendo el brillo de la pantalla.")
            self.controlador.ejecutar_control_multimedia("bajar_brillo")

        elif intencion == "detener_musica":
            self.decir_texto("Deteniendo la reproducción multimedia.")
            self.controlador.ejecutar_control_multimedia("pausar_reproducir")

        elif intencion == "reproducir_musica":
            self.decir_texto("Iniciando la reproducción multimedia.")
            self.controlador.ejecutar_control_multimedia("pausar_reproducir")

        elif intencion == "siguiente_cancion":
            self.decir_texto("Saltando a la siguiente pista.")
            self.controlador.ejecutar_control_multimedia("siguiente")

        elif intencion == "anterior_cancion":
            self.decir_texto("Regresando a la pista anterior.")
            self.controlador.ejecutar_control_multimedia("anterior")

        elif intencion == "captura_pantalla":
            self.decir_texto("Tomando captura de pantalla.")
            self.controlador.ejecutar_captura_pantalla()
            self.after(1000, lambda: self.decir_texto("Captura guardada en su escritorio."))

        elif intencion == "obtener_hora":
            self.decir_texto(self.controlador.obtener_hora_actual())

        elif intencion == "obtener_fecha":
            self.decir_texto(self.controlador.obtener_fecha_actual())

        elif intencion == "obtener_clima":
            self.decir_texto("Consultando el clima actual en tu ubicación...")
            clima_resultado = self.controlador.obtener_clima()
            self.decir_texto(clima_resultado)

        elif intencion == "obtener_noticias":
            self.decir_texto("Buscando las noticias más recientes del día...")
            noticias_resultado = self.controlador.obtener_noticias()
            self.decir_texto(noticias_resultado)

        elif intencion == "despedida":
            self.decir_texto("Nos vemos pronto. ¡Que tengas un excelente día!")
            self.asistente_activo = False
            self.after(2000, self.destroy)

        elif intencion == "modo_conversacion_libre":
            self.registrar_log(self.nombre_asistente.capitalize(), "Pensando respuesta...")
            def procesar_charla():
                try:
                    respuesta_ia = self.cerebro.generar_respuesta_libre(instruccion)
                    self.decir_texto(respuesta_ia)
                except Exception:
                    self.decir_texto("Disculpa, experimenté un percance en mi red conversacional.")
            threading.Thread(target=procesar_charla, daemon=True).start()


if __name__ == "__main__":
    app = AplicacionAsistente()
    app.mainloop()