import os
import webbrowser
import pyautogui
from datetime import datetime
import urllib.request
import urllib.parse
import re

# === NUEVAS LIBRERÍAS INTEGRADAS ===
import asyncio
import edge_tts
import pygame
import requests
import feedparser

class ControladorSistema:
    def __init__(self):
        # Configuramos una voz en español altamente realista
        # Opciones recomendadas: 'es-MX-DaliaNeural' o 'es-ES-AlvaroNeural'
        self.voz_seleccionada = "es-MX-DaliaNeural"
        self.archivo_audio_temp = "friday_voz.mp3"
        
        self.ciudad_defecto = self._autodetectar_ubicacion()
        print(f"[SISTEMA] Ubicación establecida por defecto: {self.ciudad_defecto}")

    def _autodetectar_ubicacion(self):
        """Detecta la ciudad del usuario usando su IP pública."""
        try:
            # Usamos un servicio gratuito y rápido de geolocalización por IP
            respuesta = requests.get("https://ipapi.co/json/", timeout=4)
            if respuesta.status_code == 200:
                datos = respuesta.json()
                ciudad = datos.get("city")
                region = datos.get("region")
                # Si encuentra Morales, Izabal, devolverá algo como "Morales"
                if ciudad:
                    return ciudad
            return "Guatemala"  # Respaldo si falla el servicio
        except Exception:
            return "Guatemala"  # Respaldo por si no hay internet temporalmente


    def hablar(self, texto):
        """Genera un archivo de audio con voz humana y lo reproduce dinámicamente."""
        async def generar_audio():
            communicate = edge_tts.Communicate(texto, self.voz_seleccionada)
            await communicate.save(self.archivo_audio_temp)

        try:
            # Generamos el audio MP3 asíncronamente
            asyncio.run(generar_audio())

            # Reproducimos usando Pygame
            if os.path.exists(self.archivo_audio_temp):
                pygame.mixer.init()
                pygame.mixer.music.load(self.archivo_audio_temp)
                pygame.mixer.music.play()
                
                # Espera a que termine para que no se corte
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    
                pygame.mixer.music.unload()
                pygame.mixer.quit()
                
                # Opcional: borra el archivo para no dejar basura temporal
                os.remove(self.archivo_audio_temp)
        except Exception as e:
            print(f"Error en la reproducción de voz: {e}")

 
    def obtener_clima(self, ciudad=None):
        """Consulta el clima actual usando la API gratuita y estable de Open-Meteo."""
        ciudad_consulta = ciudad if ciudad else self.ciudad_defecto
        
        try:
            # 1. Obtener coordenadas (Latitud y Longitud) de la ciudad mediante geocodificación gratuita
            url_geo = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(ciudad_consulta)}&count=1&language=es"
            res_geo = requests.get(url_geo, timeout=5)
            
            if res_geo.status_code != 200:
                return "Lo siento, el servicio de localización no está respondiendo."
                
            datos_geo = res_geo.json()
            if not datos_geo.get("results"):
                return f"No he podido encontrar la ubicación geográfica de {ciudad_consulta}."
            
            # Extraemos los datos de la ubicación
            location = datos_geo["results"][0]
            lat = location["latitude"]
            lon = location["longitude"]
            nombre_exacto = location["name"]
            
            # 2. Consultar el clima actual con las coordenadas obtenidas
            url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
            res_clima = requests.get(url_clima, timeout=5)
            
            if res_clima.status_code == 200:
                datos_clima = res_clima.json()
                clima_actual = datos_clima["current_weather"]
                temp = clima_actual["temperature"]
                viento = clima_actual["windspeed"]
                
                # Convertimos el código del clima (WMO) a texto amigable en español
                codigo_clima = clima_actual["weathercode"]
                estado_clima = self._interpretar_codigo_clima(codigo_clima)
                
                return f"El clima actual en {nombre_exacto} es {estado_clima}, con una temperatura de {temp} grados centígrados y vientos de {viento} kilómetros por hora."
            else:
                return "No he podido obtener los datos meteorológicos en este momento."
                
        except Exception as e:
            print(f"Error al obtener clima: {e}")
            return "Lo siento, ha ocurrido un error al conectar con el servidor de clima."

    def _interpretar_codigo_clima(self, codigo):
        """Traduce los códigos WMO de Open-Meteo a español."""
        codigos = {
            0: "cielo despejado",
            1: "principalmente despejado", 2: "parcialmente nublado", 3: "nublado",
            45: "con niebla", 48: "con niebla de escarcha",
            51: "llovizna ligera", 53: "llovizna moderada", 55: "llovizna densa",
            61: "lluvia ligera", 63: "lluvia moderada", 65: "lluvia fuerte",
            71: "nevada ligera", 73: "nevada moderada", 75: "nevada fuerte",
            80: "lluvias ligeras intermitentes", 81: "lluvias moderadas", 82: "lluvias violentas",
            95: "tormenta eléctrica", 96: "tormenta con granizo ligero", 99: "tormenta con granizo fuerte"
        }
        return codigos.get(codigo, "un clima no especificado")

    def obtener_noticias(self):
        """Lee los titulares más recientes desde un feed RSS de noticias."""
        # Usamos un RSS confiable en español (ej. BBC Mundo)
        rss_url = "https://feeds.bbci.co.uk/mundo/rss.xml"
        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                return "No he podido obtener noticias en este momento."
            
            titulares = []
            # Tomamos las 3 noticias principales
            for i, entrada in enumerate(feed.entries[:3], 1):
                titulares.append(f"Noticia {i}: {entrada.title}.")
            
            resultado = "Estas son las tres noticias principales del momento: " + " ".join(titulares)
            return resultado
        except Exception:
            return "Ocurrió un error al intentar conectarme al servicio de noticias."

    # ==========================================
    # MÉTODOS EXISTENTES DEL CONTROLADOR
    # ==========================================
    def _obtener_rutas_usuario(self):
        """Detecta dinámicamente las rutas del sistema del usuario, con o sin OneDrive."""
        ruta_base = os.path.expanduser("~")
        opciones = {
            "escritorio": [
                os.path.join(ruta_base, "OneDrive", "Escritorio"),
                os.path.join(ruta_base, "OneDrive", "Desktop"),
                os.path.join(ruta_base, "Escritorio"),
                os.path.join(ruta_base, "Desktop")
            ],
            "descargas": [
                os.path.join(ruta_base, "OneDrive", "Descargas"),
                os.path.join(ruta_base, "Descargas"),
                os.path.join(ruta_base, "Downloads")
            ],
            "documentos": [
                os.path.join(ruta_base, "OneDrive", "Documentos"),
                os.path.join(ruta_base, "OneDrive", "Documents"),
                os.path.join(ruta_base, "Documentos"),
                os.path.join(ruta_base, "Documents")
            ]
        }
        
        rutas_finales = {}
        for clave, lista_rutas in opciones.items():
            rutas_finales[clave] = lista_rutas[-1]
            for ruta in lista_rutas:
                if os.path.exists(ruta):
                    rutas_finales[clave] = ruta
                    break
        return rutas_finales

    def esta_aplicacion_ejecutandose(self, nombre_ejecutable):
        """Consulta en tiempo real la tabla de procesos de Windows."""
        try:
            resultado = os.popen(f'tasklist /FI "IMAGENAME eq {nombre_ejecutable}"').read()
            return nombre_ejecutable.lower() in resultado.lower()
        except Exception:
            return False

    def ejecutar_abrir_word(self):
        os.system("start winword")

    def ejecutar_abrir_excel(self):
        os.system("start excel")

    def ejecutar_abrir_powerpoint(self):
        os.system("start powerpnt")

    def ejecutar_abrir_fotos(self):
        os.system("start ms-photos:")

    def ejecutar_cerrar_programa(self, nombre_ejecutable):
        """Fuerza el cierre seguro de un proceso en Windows."""
        try:
            os.system(f'taskkill /IM "{nombre_ejecutable}" /F')
            return True
        except Exception:
            return False

    def ejecutar_crear_nota(self, contenido):
        """Crea un archivo de texto en el Escritorio con la marca de tiempo actual."""
        rutas = self._obtener_rutas_usuario()
        nombre_archivo = f"Nota_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        ruta_completa = os.path.join(rutas["escritorio"], nombre_archivo)
        
        with open(ruta_completa, "w", encoding="utf-8") as f:
            f.write(contenido)
        return ruta_completa

    def ejecutar_buscar_archivo(self, nombre_archivo):
        """Busca hasta 5 archivos que coincidan en Escritorio, Descargas y Documentos (raíz y nivel 1)."""
        rutas = self._obtener_rutas_usuario()
        carpetas_objetivo = [rutas["escritorio"], rutas["descargas"], rutas["documentos"]]
        nombre_lower = nombre_archivo.lower()
        
        coincidencias = []

        for carpeta in carpetas_objetivo:
            if not os.path.exists(carpeta):
                continue
            try:
                # Nivel 1: Elementos directos en la carpeta
                for elemento in os.listdir(carpeta):
                    ruta_elemento = os.path.join(carpeta, elemento)
                    if os.path.isfile(ruta_elemento) and nombre_lower in elemento.lower():
                        ruta_abs = os.path.abspath(ruta_elemento)
                        if (elemento, ruta_abs) not in coincidencias:
                            coincidencias.append((elemento, ruta_abs))
                        if len(coincidencias) >= 5:
                            return coincidencias

                # Nivel 2: Solo carpetas directas hijas
                for elemento in os.listdir(carpeta):
                    ruta_elemento = os.path.join(carpeta, elemento)
                    if os.path.isdir(ruta_elemento):
                        try:
                            for sub_elemento in os.listdir(ruta_elemento):
                                ruta_sub = os.path.join(ruta_elemento, sub_elemento)
                                if os.path.isfile(ruta_sub) and nombre_lower in sub_elemento.lower():
                                    ruta_abs_sub = os.path.abspath(ruta_sub)
                                    if (sub_elemento, ruta_abs_sub) not in coincidencias:
                                        coincidencias.append((sub_elemento, ruta_abs_sub))
                                    if len(coincidencias) >= 5:
                                        return coincidencias
                        except Exception:
                            continue
            except Exception:
                continue
                
        return coincidencias

    def ejecutar_bloquear_pc(self):
        os.system("rundll32.exe user32.dll,LockWorkStation")

    def ejecutar_buscar_internet(self, consulta_busqueda):
        url = f"https://www.google.com/search?q={consulta_busqueda}"
        webbrowser.open(url)

    def ejecutar_buscar_youtube(self, consulta_video):
        consulta_formateada = urllib.parse.quote(consulta_video)
        url_busqueda = f"https://www.youtube.com/results?search_query={consulta_formateada}"
        try:
            peticion = urllib.request.Request(
                url_busqueda, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            html = urllib.request.urlopen(peticion).read().decode()
            video_ids = re.findall(r"watch\?v=(\S{11})", html)
            if video_ids:
                webbrowser.open(f"https://www.youtube.com/watch?v={video_ids[0]}")
            else:
                webbrowser.open(url_busqueda)
        except Exception:
            webbrowser.open(url_busqueda)

    def ejecutar_control_multimedia(self, accion):
        if accion == "pausar_reproducir":
            pyautogui.press("playpause")
            pyautogui.press("space") 
        elif accion == "siguiente":
            pyautogui.press("nexttrack")
        elif accion == "anterior":
            pyautogui.press("prevtrack")
        elif accion == "subir_volumen":
            for _ in range(5): pyautogui.press("volumeup")
        elif accion == "bajar_volumen":
            for _ in range(5): pyautogui.press("volumedown")
        elif accion == "subir_brillo":
            os.system("powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, ((Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness + 20))")
        elif accion == "bajar_brillo":
            os.system("powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, ((Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness - 20))")

    def obtener_hora_actual(self):
        return datetime.now().strftime("Son las %I y %M %p")

    def obtener_fecha_actual(self):
        ahora = datetime.now()
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        return f"Hoy es {dias[ahora.weekday()]} {ahora.day} de {meses[ahora.month - 1]} del {ahora.year}"

    def ejecutar_captura_pantalla(self):
        rutas = self._obtener_rutas_usuario()
        nombre_archivo = f"Captura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ruta_completa = os.path.join(rutas["escritorio"], nombre_archivo)
        captura = pyautogui.screenshot()
        captura.save(ruta_completa)
        return ruta_completa