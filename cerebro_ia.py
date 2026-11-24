import spacy
import urllib.request
import urllib.parse
import json

class CerebroInteligente:
    def __init__(self):
        self.nlp = spacy.load("es_core_news_sm")
        print("[IA] Conectado exitosamente al núcleo conversacional local (Ollama)...")

    def comprender_intencion(self, texto_usuario):
        texto_usuario_lower = texto_usuario.lower().strip()
        doc = self.nlp(texto_usuario_lower)
        lemas = [token.lemma_ for token in doc]
        texto_limpio = " ".join(lemas)
        
        todo_el_texto = f"{texto_usuario_lower} {texto_limpio}"
        
        # --- FILTRO PRIORITARIO: CERRAR PROGRAMAS ESPECÍFICOS ---
        if any(w in todo_el_texto for w in ["cerrar", "cierra", "quitar", "quita"]):
            if any(w in todo_el_texto for w in ["word", "world"]): return "cerrar_word"
            if "excel" in todo_el_texto: return "cerrar_excel"
            if any(w in todo_el_texto for w in ["powerpoint", "diapositiva", "powerpnt"]): return "cerrar_powerpoint"
            if any(w in todo_el_texto for w in ["foto", "imagen", "galería", "galeria", "fotos"]): return "cerrar_fotos"

        # --- FILTROS DE NUEVAS INTENCIONES ---
        if any(w in todo_el_texto for w in ["crear nota", "crea una nota", "escribe una nota", "nueva nota", "escribir nota"]):
            return "crear_nota"

        if any(w in todo_el_texto for w in ["buscar archivo", "busca el archivo", "encuentra el archivo", "buscar un archivo"]):
            return "buscar_archivo"

        # --- FILTROS PREEXISTENTES ---
        if any(w in todo_el_texto for w in ["bloquear", "suspender", "bloquea"]):
            return "bloquear_pc"
            
        if any(w in todo_el_texto for w in ["word", "world"]):
            return "abrir_word"
            
        if "excel" in todo_el_texto:
            return "abrir_excel"
            
        if any(w in todo_el_texto for w in ["powerpoint", "diapositiva", "powerpnt"]):
            return "abrir_powerpoint"
            
        if any(w in todo_el_texto for w in ["volumen", "sonido", "audio"]):
            if any(w in todo_el_texto for w in ["subir", "aumentar", "más", "mas"]): return "subir_volumen"
            if any(w in todo_el_texto for w in ["bajar", "disminuir", "menos"]): return "bajar_volumen"
            
        if any(w in todo_el_texto for w in ["brillo", "iluminación", "iluminacion"]):
            if any(w in todo_el_texto for w in ["subir", "aumentar", "más", "mas"]): return "subir_brillo"
            if any(w in todo_el_texto for w in ["bajar", "disminuir", "menos"]): return "bajar_brillo"
                
        if any(w in todo_el_texto for w in ["captura", "pantalla"]):
            return "captura_pantalla"

        if any(w in todo_el_texto for w in ["foto", "imagen", "galería", "galeria"]):
            return "abrir_fotos"

        if any(w in todo_el_texto for w in ["fecha", "día es hoy", "dia es hoy", "qué día es"]):
            return "obtener_fecha"
        
        if any(w in todo_el_texto for w in ["hora", "tiempo", "qué hora es", "que hora es"]):
            return "obtener_hora"

        if any(w in todo_el_texto for w in ["en la web", "en google", "buscar en internet"]):
            return "buscar_internet"
            
        if "youtube" in todo_el_texto or "video" in todo_el_texto:
            return "buscar_youtube"
            
        if any(w in todo_el_texto for w in ["google", "internet", "navegar", "buscar", "busca"]):
            return "buscar_internet"
            
        if any(w in todo_el_texto for w in ["pausar", "detener", "parar", "deten", "pausa", "para"]):
            return "detener_musica"
            
        if any(w in todo_el_texto for w in ["reproducir", "reproduce", "reproducción", "reproduccion"]):
            return "reproducir_musica"

        if any(w in todo_el_texto for w in ["siguiente", "avanzar", "cambiar", "pista"]):
            return "siguiente_cancion"
            
        if any(w in todo_el_texto for w in ["anterior", "regresar", "atrás", "atras"]):
            return "anterior_cancion"
            
        if any(w in todo_el_texto for w in ["adiós", "adios", "terminar", "cerrar", "cierra", "cierrate", "ciérrate", "nos vemos", "apagar", "apaga", "apagate", "apágate"]):
            return "despedida"
        
        if any(w in todo_el_texto for w in ["clima", "temperatura", "tiempo hoy", "hace frío", "hace calor"]):
            return "obtener_clima"

        if any(w in todo_el_texto for w in ["noticias", "titulares", "noticiero", "qué pasa en el mundo"]):
            return "obtener_noticias"
        
        return "modo_conversacion_libre"

    def generar_respuesta_libre(self, pregunta_usuario):
        """Envía la pregunta al servidor local de Ollama usando el modelo Llama 3.2."""
        url = "http://localhost:11434/api/generate"
        
        # Configuramos el prompt de sistema y los parámetros directo en la petición
        payload = {
            "model": "llama3.2",
            "prompt": f"Instrucción de sistema: Eres Friday, una IA concisa. Responde en español de forma directa y natural (máximo 15 palabras). No inventes historias.\nUsuario: {pregunta_usuario}",
            "stream": False,
            "options": {
                "temperature": 0.5,
                "num_predict": 40
            }
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                respuesta_ia = res.get("response", "").strip()
                return respuesta_ia
        except Exception as e:
            print(f"[ERROR OLLAMA]: {e}")
            return "Lo siento, no he podido conectar con mi servidor conversacional local."