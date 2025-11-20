import logging
import os
import psycopg2
import warnings
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from telegram.warnings import PTBUserWarning
from datetime import datetime
import telegram
print(f"Versión de python-telegram-bot: {telegram.__version__}")

# Ignorar la advertencia específica de python-telegram-bot
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración del Bot y la Base de Datos ---
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#                                  MUY IMPORTANTE
# DEBES REEMPLAZAR EL TEXTO "TU_TOKEN_AQUI" CON EL TOKEN REAL QUE OBTUVISTE
# DE BOTFATHER EN TELEGRAM. SI NO USAS UN ARCHIVO .env, DEJA EL TOKEN AQUÍ.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TU_TOKEN_AQUI")

# Configuración de la conexión a PostgreSQL
config_db = {
    "dbname": os.getenv("DB_DATABASE"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432")
}

# Configuración del contacto de emergencia para alertas rojas
# Puedes cambiar estos valores por los reales
CONTACTO_EMERGENCIA_NOMBRE = "Ana María Pérez"
CONTACTO_EMERGENCIA_TEL = "+58 412-1234567"

# Habilitar el registro
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# --- Funciones de Base de Datos ---
def obtener_conexion_db():
    """Establece una conexión a la base de datos PostgreSQL."""
    try:
        conn = psycopg2.connect(**config_db)
        return conn
    except psycopg2.Error as err:
        logger.error(f"Error al conectar con la base de datos: {err}")
        return None

def verificar_cedula_en_db(cedula):
    """Verifica si la cédula existe en la tabla 'usuarios' de la base de datos."""
    conn = obtener_conexion_db()
    if conn is None:
        return False
    
    try:
        with conn.cursor() as cursor:
            # Reemplaza 'usuarios' y 'cedula' si los nombres de la tabla o columna son diferentes
            query = "SELECT cedula FROM usuarios WHERE cedula = %s;"
            cursor.execute(query, (cedula,))
            resultado = cursor.fetchone()
            return resultado is not None
    except psycopg2.Error as err:
        logger.error(f"Error al verificar la cédula en la base de datos: {err}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def generar_codigo_reporte(nivel, tipo_reporte):
    """
    Genera un código de reporte con el formato: 
    primera letra del nivel + primera letra del tipo + aammddhhmm
    """
    nivel_map = {
        "verde": "V",
        "amarilla": "A",
        "naranja": "N",
        "roja": "R",
    }
    tipo_map = {
        "operacional": "O",
        "comunicacional": "C",
    }

    primera_letra_nivel = nivel_map.get(nivel.lower(), "X")
    primera_letra_tipo = tipo_map.get(tipo_reporte.lower(), "X")

    fecha_hora_str = datetime.now().strftime('%y%m%d%H%M')
    return f"{primera_letra_nivel}{primera_letra_tipo}-{fecha_hora_str}"


def guardar_reporte_en_db(data):
    """Guarda los datos del reporte en la tabla correspondiente, adaptándose a los nombres de columna del usuario."""
    conn = obtener_conexion_db()
    if conn is None:
        return False

    tipo_reporte = data.get("tipo_reporte", "").lower()
    
    # Convierte las respuestas de texto a booleanos
    violencia = data.get("violencia", "No").capitalize() == "Si"
    amenaza_vida = data.get("amenaza_vida", "No").capitalize() == "Si"
    verificado = data.get("verificado", "No").capitalize() == "Si"
    codigo = data.get("codigo_reporte")
    
    # CAMBIO CRÍTICO: Usar el valor tal cual viene del botón, que ya es correcto.
    nivel_alerta = data.get("nivel")

    try:
        with conn.cursor() as cursor:
            if tipo_reporte == "operacional":
                query = """
                INSERT INTO reportes_operacionales (
                    cedula_usuario, nivel_alerta, tipo_evento, descripcion_tecnica, 
                    recursos_comprometidos, acciones_ejecutadas, incluye_violencia, amenaza_a_la_vida, 
                    confirmacion_veracidad, observaciones, recursos_multimedia, fecha_hora, codigo_reporte
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                params = (
                    data["cedula"], nivel_alerta, data.get("tipo_evento", ""), data.get("descripcion", ""), 
                    data.get("recursos", ""), data.get("acciones", ""), violencia, amenaza_vida, 
                    verificado, data.get("observaciones", ""), json.dumps(data.get("recursos_multimedia", [])), 
                    datetime.now(), codigo
                )
            elif tipo_reporte == "comunicacional":
                query = """
                INSERT INTO reportes_comunicacionales (
                    cedula_usuario, nivel_alerta, tipo_evento, tipo_medio, medio_especifico,
                    contenido_difundido, audiencia_afectada, incluye_violencia, amenaza_a_la_vida,
                    confirmacion_veracidad, observaciones, recursos_multimedia, fecha_hora, codigo_reporte
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                params = (
                    data["cedula"], nivel_alerta, data.get("tipo_evento", ""), data.get("tipo_medio", ""), data.get("medio_especifico", ""), 
                    data.get("contenido_difundido", ""), data.get("audiencia_afectada", ""), violencia, amenaza_vida, 
                    verificado, data.get("observaciones", ""), json.dumps(data.get("recursos_multimedia", [])), 
                    datetime.now(), codigo
                )
            else:
                logger.error(f"Tipo de reporte desconocido: {tipo_reporte}")
                return False

            cursor.execute(query, params)
        conn.commit()
        return True
    except psycopg2.Error as err:
        logger.error(f"Error al guardar el reporte en la base de datos: {err}")
        conn.rollback()
        return False
    finally:
        if 'conn' in locals() and conn:
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()
            print("Conexión a la base de datos cerrada.")

# --- Definir estados de la conversación ---
(
    ESTADO_CEDULA,
    ESTADO_NIVEL,
    ESTADO_TIPO_REPORTE,
    ESTADO_TIPO_EVENTO_COMUN,
    ESTADO_OTRO_EVENTO_COMUN,
    ESTADO_VERDE_OP_DESC,
    ESTADO_VERDE_COM_DESC,
    ESTADO_DESCRIPCION,
    ESTADO_RECURSOS,
    ESTADO_ACCIONES,
    ESTADO_VIOLENCIA,
    ESTADO_AMENAZA,
    ESTADO_VERIFICADO,
    ESTADO_OBSERVACIONES,
    ESTADO_ESPERANDO_MULTIMEDIA,
    ESTADO_TIPO_MEDIO,
    ESTADO_MEDIO_ESPECIFICO,
    ESTADO_CONTENIDO_DIFUNDIDO,
    ESTADO_AUDIENCIA_AFECTADA,
    ESTADO_RESUMEN,
    ESTADO_REINICIAR,
    ESTADO_MODIFICAR,
    # Nuevos estados para la alerta roja
    ESTADO_ACCION_INMEDIATA,
    # Nuevos estados para el flujo comunicacional
    ESTADO_DESCRIPCION_COMUNICACIONAL,
    # Nuevos estados para modificacion de reportes
    ESTADO_DESCRIPCION_EVENTO,
    ESTADO_ACCIONES_TOMADAS,
    ESTADO_RECURSOS_COMPROMETIDOS,
    ESTADO_NOMBRE_MEDIO,
    ESTADO_CONFIRMACION_MODIFICACION,
) = range(29)
# --- Funciones de manejo de estados ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación y pide la cédula."""
    context.user_data.clear()
    welcome_message = "Bienvenido al sistema automatizado de Reportes de alertas tempranas de FONPESCA. Este canal es exclusivo para personal autorizado.\n\nPor favor, ingresa tu número de cédula para continuar."
    await update.message.reply_text(welcome_message)
    return ESTADO_CEDULA

async def manejar_cedula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la cédula y pide el nivel de reporte, previa autenticación."""
    cedula_input = update.message.text
    
    # Creamos el keyboard de reintento para ambos casos de error
    keyboard = [[InlineKeyboardButton("🔄 Intentar de nuevo", callback_data="reintentar_cedula")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Valida que la cédula sea un número
    if not cedula_input.isdigit():
        await update.message.reply_text("❌ Cédula inválida. Por favor, ingresa solo números.", reply_markup=reply_markup)
        return ESTADO_CEDULA # Se mantiene en el mismo estado para que pueda reintentar
    
    # Autenticación basada en la cédula, consultando la base de datos
    conn = obtener_conexion_db()
    nombre_usuario = None  # Inicializamos a None
    
    if conn:
        try:
            with conn.cursor() as cursor:
                # Consulta para verificar la cédula
                query = "SELECT nombre FROM usuarios WHERE cedula = %s;"
                cursor.execute(query, (cedula_input,))
                result = cursor.fetchone()
                
                if result:
                    nombre_usuario = result[0]
                else:
                    await update.message.reply_text("❌ Acceso denegado. La cédula ingresada no está autorizada.", reply_markup=reply_markup)
                    context.user_data.clear() # Limpia los datos de la conversación
                    conn.close()
                    return ConversationHandler.END # Opcional: Se podría enviar a un estado de reintento
        except psycopg2.Error as err:
            logger.error(f"Error al verificar la cédula en la base de datos: {err}")
            await update.message.reply_text("Ocurrió un error al verificar tu cédula. Por favor, inténtalo de nuevo más tarde.")
            context.user_data.clear()
            if conn:
                conn.close()
            return ConversationHandler.END
        finally:
            if conn:
                conn.close()
    
    # Si la autenticación es exitosa, se guarda la cédula y se continúa
    if nombre_usuario:
        context.user_data["cedula"] = cedula_input
        personalized_welcome = f"¡Hola, {nombre_usuario}! Autenticación exitosa. ¿Qué nivel tiene el reporte?"
        
        keyboard_nivel = [
            [InlineKeyboardButton("🟢 Verde", callback_data="Verde")],
            [InlineKeyboardButton("🟡 Amarilla", callback_data="Amarilla")],
            [InlineKeyboardButton("🟠 Naranja", callback_data="Naranja")],
            [InlineKeyboardButton("🚨 Roja", callback_data="Roja")],
        ]
        reply_markup_nivel = InlineKeyboardMarkup(keyboard_nivel)
        
        await update.message.reply_text(personalized_welcome, reply_markup=reply_markup_nivel)
        return ESTADO_NIVEL
    else:
        # Esto se ejecuta si la cédula no se encuentra y el flujo no terminó antes.
        # En el caso de cédula inválida, el bot ya se queda en ESTADO_CEDULA y vuelve a pedirla.
        # Este else maneja el caso de que la cédula no esté en la base de datos
        await update.message.reply_text("❌ Acceso denegado. La cédula ingresada no está autorizada.", reply_markup=reply_markup)
        return ConversationHandler.END

async def reintentar_cedula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el botón de reintentar y reinicia la conversación."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    
    await query.edit_message_text("Ingrese nuevamente la cédula ")
    return ESTADO_CEDULA

# ---  manejar_nivel ( ---
async def manejar_nivel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    nivel = query.data.lower()
    context.user_data["nivel"] = nivel
    
    await query.edit_message_text(f"✅ Nivel de Alerta **{nivel.title()}** guardado.")
    
    # El flujo ahora es: guardar nivel -> MOSTRAR menú Tipo de Reporte (llamando a la función) -> esperar respuesta en ESTADO_TIPO_REPORTE
    # Llama a la función que muestra el siguiente menú y retorna el estado donde se espera la respuesta.
    await pedir_tipo_reporte(update, context) 
    
    # El estado retornado debe ser el estado donde se espera la respuesta del menú de Tipo de Reporte.
    return ESTADO_TIPO_REPORTE

async def pedir_tipo_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el menú para seleccionar el Tipo de Reporte (Operacional o Comunicacional)."""
    
    # Si viene de un CallbackQuery (botón), usa query, sino usa update.message
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # EL TECLADO DE TIPO DE REPORTE
        keyboard = [
            [InlineKeyboardButton("1. Operacional", callback_data="operacional")],
            [InlineKeyboardButton("2. Comunicacional", callback_data="comunicacional")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("Paso 2. Selecciona el **Tipo de Reporte**:", reply_markup=reply_markup, parse_mode='Markdown')
        
    else:
        # En el caso de que venga de un comando o mensaje inicial (menos común en este punto)
        # Esto es solo un fallback si el flujo lo permite.
        keyboard = [
            [InlineKeyboardButton("1. Operacional", callback_data="operacional")],
            [InlineKeyboardButton("2. Comunicacional", callback_data="comunicacional")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Paso 2. Selecciona el **Tipo de Reporte**:", reply_markup=reply_markup, parse_mode='Markdown')

    return ESTADO_TIPO_REPORTE
  # --- lista de opciones de evento ---

# --- 1. FUNCIÓN AUXILIAR: Crea el teclado Inline del Tipo de Evento ---
def crear_menu_tipo_evento():
    """Genera el teclado Inline para seleccionar el Tipo de Evento."""
    opciones = [
        ("Pescadores y acuicultores", "evento_pesca_acui"),
        ("CONPPA", "evento_conppa"),
        ("Político / Conflicto Social", "evento_politico"),
        ("Desastres naturales", "evento_desastre"),
        ("5. Otros (Describir)", "evento_otro")
    ]
    keyboard = [[InlineKeyboardButton(texto, callback_data=data)] for texto, data in opciones]
    return InlineKeyboardMarkup(keyboard)

# --- 2. FUNCIÓN: Muestra el Menú Tipo de Evento (Llamada desde ESTADO_TIPO_REPORTE) ---

async def pedir_tipo_evento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    
    await query.answer() 
    context.user_data['tipo_reporte'] = query.data 
    await query.edit_message_text(
        f"✅ Reporte **{context.user_data['tipo_reporte'].title()}** seleccionado.\n\nPaso 3. Selecciona el **Tipo de Evento**:",
        reply_markup=crear_menu_tipo_evento(),
        parse_mode='Markdown'
    )
    
    return ESTADO_TIPO_EVENTO_COMUN

# --- 3. FUNCIÓN: Maneja la selección y RAMIFICA al flujo específico (Descripción, Violencia, etc.) ---
def manejar_tipo_evento_y_ramificar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección del Tipo de Evento y avanza al primer paso del flujo de Alerta (e.g., Descripción)."""
    query = update.callback_query
    query.answer()
    seleccion = query.data
    
    # Recuperar datos cruciales para la ramificación
    alerta = context.user_data.get('nivel', '').lower()       # Ej: 'verde', 'amarilla', 'roja'
    tipo_reporte = context.user_data.get('tipo_reporte', '')  # Ej: 'operacional', 'comunicacional'
    
    mapeo_eventos = { # Usado para guardar el texto legible
        "evento_pesca_acui": "Pescadores y acuicultores", "evento_conppa": "CONPPA", 
        "evento_politico": "Político / Conflicto Social", "evento_desastre": "Desastres naturales"
    }

    if seleccion == "evento_otro":
        query.edit_message_text("Has seleccionado 'Otros'. Por favor, **escribe a continuación** el tipo de evento:")
        return ESTADO_OTRO_EVENTO_COMUN # Espera la entrada de texto
    
    # Guardar la selección
    context.user_data['tipo_evento'] = mapeo_eventos.get(seleccion)
    mensaje_exito = f"✅ Tipo de Evento: **{context.user_data['tipo_evento']}** guardado."
    
    # --- LÓGICA DE RAMIFICACIÓN AL PRIMER PASO ESPECÍFICO ---
    
    # Alerta VERDE (Paso siguiente es Descripción, ESTADO_VERDE_OP_DESC / ESTADO_VERDE_COM_DESC)
    if alerta == 'verde':
        destino_estado = ESTADO_VERDE_OP_DESC if tipo_reporte == 'operacional' else ESTADO_VERDE_COM_DESC
        texto_pregunta = "Flujo VERDE.\n\nPor favor, ingresa la **descripción del evento**:"
    
    # Alerta AMARILLA / NARANJA (Paso siguiente es Descripción, ESTADO_AMARILLA_NARANJA_OP_DESC / COM_DESC)
    elif alerta in ['amarilla', 'naranja']:
        # *AQUÍ DEBES USAR TUS CONSTANTES DEFINIDAS para la ALERTA AMARILLA/NARANJA*
        # Ejemplo:
        # destino_estado = ESTADO_AMARILLA_OP_DESC if tipo_reporte == 'operacional' else ESTADO_AMARILLA_COM_DESC
        # texto_pregunta = "Flujo AMARILLA/NARANJA.\n\nPor favor, ingresa la **descripción del evento**:"
        
        # Como no tengo tus constantes exactas, usaremos un placeholder de error
        query.edit_message_text(f"⚠️ **{alerta.upper()}** - Faltan estados de destino. Contacte al desarrollador.")
        return ConversationHandler.END
    
    # Alerta ROJA (Paso siguiente es ¿Hubo violencia?, ESTADO_ROJA_OP_VIOLENCIA / COM_VIOLENCIA)
    elif alerta == 'roja':
        # *AQUÍ DEBES USAR TUS CONSTANTES DEFINIDAS para la ALERTA ROJA*
        # Ejemplo:
        # destino_estado = ESTADO_ROJA_OP_VIOLENCIA if tipo_reporte == 'operacional' else ESTADO_ROJA_COM_VIOLENCIA
        # texto_pregunta = "Flujo ROJA.\n\n**Pregunta de Emergencia:** ¿Hubo violencia en el evento?"
        
        # Como no tengo tus constantes exactas, usaremos un placeholder de error
        query.edit_message_text(f"⚠️ **ROJA** - Faltan estados de destino. Contacte al desarrollador.")
        return ConversationHandler.END
        
    else:
        query.edit_message_text("⚠️ Error de flujo: El nivel de alerta es desconocido.")
        return ConversationHandler.END

    # Ejecutar la transición (solo si Alerta es Verde, si no, se fue por el error arriba)
    query.edit_message_text(f"{mensaje_exito}\n\n{texto_pregunta}", parse_mode='Markdown')
    return destino_estado

# --- 4. FUNCIÓN: Maneja la entrada de texto "Otros" y Avanza ---
def guardar_otro_evento_y_ramificar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el texto de 'Otro' y llama a la función de ramificación para avanzar."""
    context.user_data['tipo_evento'] = update.message.text
    update.message.reply_text(f"✅ Tipo de Evento: **{context.user_data['tipo_evento']}** guardado.", parse_mode='Markdown')
    
    # Crear un objeto dummy para simular el CallbackQuery y reutilizar la lógica de ramificación
    class DummyQuery:
        def __init__(self, data): self.data = data
        def answer(self): pass
        def edit_message_text(self, text, reply_markup=None, parse_mode=None):
            # Usar update.message.reply_text en lugar de query.edit
            update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    # Llamar a la función de ramificación con una selección simulada (que luego se ignora)
    # y simular el objeto de consulta para que la función maneje_tipo_evento_y_ramificar funcione.
    update.callback_query = DummyQuery(data="evento_dummy")
    return manejar_tipo_evento_y_ramificar(update, context)
async def manejar_tipo_evento_roja(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el tipo de evento para la alerta roja y pide el siguiente dato."""
    context.user_data["tipo_evento"] = update.message.text
    
    # Asigna valores predeterminados para que no se soliciten más adelante
    context.user_data["descripcion"] = "Alerta de máxima alerta"
    context.user_data["recursos"] = "No aplica (Alerta Roja)"
    context.user_data["acciones"] = "No aplica (Alerta Roja)"
    context.user_data["observaciones"] = "Alerta de máxima alerta"
    
    keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¿Hubo violencia?", reply_markup=reply_markup)
    return ESTADO_VIOLENCIA


#------fin de la lista de opciones---

async def manejar_tipo_evento_texto_roja(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el tipo de evento (texto libre) y continúa el flujo de la alerta roja."""
    context.user_data["tipo_evento"] = update.message.text
    
    keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¿Hubo violencia?", reply_markup=reply_markup)
    return ESTADO_VIOLENCIA


# --- Flujo para Alerta Roja ---
async def manejar_evento_roja(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la descripción del evento en una alerta Roja."""
    context.user_data["tipo_evento"] = update.message.text
    context.user_data["descripcion"] = update.message.text
    context.user_data["observaciones"] = "Alerta de máxima "
    context.user_data["violencia"] = "si"
    context.user_data["amenaza_vida"] = "si"
    context.user_data["verificado"] = "no"
    
    await update.message.reply_text("Por favor, adjunta archivos de imágenes o videos. Si no tienes archivos, selecciona 'Continuar'.",
    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data="continuar_multimedia")]]))
    context.user_data["recursos_multimedia"] = []
    return ESTADO_ESPERANDO_MULTIMEDIA

async def manejar_tipo_evento_comunicacional(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el tipo de evento comunicacional y pide la descripción."""
    context.user_data['tipo_evento_comunicacional'] = update.message.text
    await update.message.reply_text("Por favor, ingresa la descripción del evento:")
    return ESTADO_DESCRIPCION_COMUNICACIONAL
    
async def manejar_descripcion_comunicacional(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la descripción comunicacional y pasa al siguiente estado."""
    context.user_data['descripcion_comunicacional'] = update.message.text
        # <<<<<<<<<<<<<<<< BLOQUE MODIFICACIÓN >>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        del context.user_data["en_modo_modificacion"]  # Desactivamos la bandera
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL BLOQUE MODIFICACIÓN >>>>>>>>>>>>>>>>>
    pregunta = "Seleccione el tipo de medio:"
    keyboard = [
        [InlineKeyboardButton("Red Social", callback_data="red_social")],
        [InlineKeyboardButton("Prensa", callback_data="prensa")],
        [InlineKeyboardButton("Radio", callback_data="radio")],
        [InlineKeyboardButton("Televisión", callback_data="television")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(pregunta, reply_markup=reply_markup)
    return ESTADO_TIPO_MEDIO
# --- Flujo para Reporte Operacional (Verde, Amarillo, Naranja) ---
async def manejar_tipo_evento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el tipo de evento."""

      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["tipo_evento"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

    context.user_data["tipo_evento"] = update.message.text
    await update.message.reply_text("Por favor, ingresa la descripción del evento:")
    return ESTADO_DESCRIPCION

async def manejar_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la descripción y salta la pregunta de recursos para la alerta Verde."""
   
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["descripcion"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

   
    context.user_data["descripcion"] = update.message.text
    
    if context.user_data.get("nivel") == "Verde" and context.user_data.get("tipo_reporte") == "operacional":
        # Asigna un valor predeterminado y salta a la siguiente pregunta
        context.user_data["recursos"] = "No aplica (Alerta Verde)"
        await update.message.reply_text("Por favor, ingresa las acciones tomadas:")
        return ESTADO_ACCIONES
    else:
        await update.message.reply_text("Por favor, ingresa los recursos comprometidos:")
        return ESTADO_RECURSOS

async def manejar_recursos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los recursos."""
            
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["recursos"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

    context.user_data["recursos"] = update.message.text
    await update.message.reply_text("Por favor, ingresa las acciones tomadas:")
    return ESTADO_ACCIONES

async def manejar_acciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las acciones y transita al estado compartido de violencia."""
               
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["acciones"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

   
    context.user_data["acciones"] = update.message.text
           
    if context.user_data["nivel"] == "Verde":
        # Salta preguntas de violencia y amenaza
        context.user_data["violencia"] = "No"
        context.user_data["amenaza_vida"] = "No"
        keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("¿El evento está verificado?", reply_markup=reply_markup)
        return ESTADO_VERIFICADO
    else:
        keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("¿Hubo violencia?", reply_markup=reply_markup)
        return ESTADO_VIOLENCIA

# --- Flujo para Reporte Comunicacional (Verde, Amarillo, Naranja) ---
async def manejar_tipo_medio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el tipo de medio en reportes comunicacionales."""
                    
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["tipo_medio"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

   
    query = update.callback_query
    await query.answer()
    
    # Se corrige el flujo asignando el tipo de medio a tipo_evento para la BD
    context.user_data["tipo_evento"] = query.data.replace("_", " ").capitalize()
    context.user_data["tipo_medio"] = query.data.replace("_", " ").capitalize()

    # Se agrega el tipo de medio seleccionado al mensaje
    await query.edit_message_text(f"Por favor, ingresa el nombre del medio específico: ({context.user_data['tipo_medio']})")
    return ESTADO_MEDIO_ESPECIFICO

async def manejar_medio_especifico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el nombre del medio específico."""
                       
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["medio_especifico"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

  
    context.user_data["medio_especifico"] = update.message.text
    await update.message.reply_text("Por favor, ingresa el contenido difundido:")
    return ESTADO_CONTENIDO_DIFUNDIDO

async def manejar_contenido_difundido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el contenido difundido y omite las preguntas de violencia para la alerta Verde."""
                        
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["contenido_difundido"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

  
    context.user_data["contenido_difundido"] = update.message.text
 
    if context.user_data.get("nivel") == "Verde":
        # Asigna valores predeterminados y salta directamente a la verificación.
        context.user_data["audiencia_afectada"] = "No aplica (Alerta Verde)"
        context.user_data["violencia"] = "No"
        context.user_data["amenaza_vida"] = "No"
        keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("¿El evento está verificado?", reply_markup=reply_markup)
        return ESTADO_VERIFICADO
    else:
        # Para alertas Amarilla y Naranja, el flujo sigue normal.
        await update.message.reply_text("Por favor, ingresa la audiencia afectada:")
        return ESTADO_AUDIENCIA_AFECTADA

async def manejar_audiencia_afectada(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la audiencia afectada y transita al estado compartido de violencia."""
                           
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["audiencia_afectada"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

  
    context.user_data["audiencia_afectada"] = update.message.text
       
    if context.user_data["nivel"] == "Verde":
        # Si es Alerta Verde, saltamos las preguntas de violencia y amenaza.
        context.user_data["violencia"] = "No"
        context.user_data["amenaza_vida"] = "No"
        keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("¿El evento está verificado?", reply_markup=reply_markup)
        return ESTADO_VERIFICADO
    else:
        # Si no es Verde, se pregunta por violencia.
        keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("¿Hubo violencia?", reply_markup=reply_markup)
        return ESTADO_VIOLENCIA

# --- Flujo compartido para ambos tipos de Reporte (excepto alerta roja) ---
async def manejar_violencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la respuesta sobre la violencia."""
                               
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["violencia"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

  
    query = update.callback_query
    await query.answer()
    context.user_data["violencia"] = query.data.capitalize()
    
    keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("¿Hubo amenaza a la vida?", reply_markup=reply_markup)
    return ESTADO_AMENAZA

async def manejar_amenaza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la respuesta sobre amenaza a la vida y finaliza con la pregunta de verificación."""
                            
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["amenaza_vida"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

    query = update.callback_query
    await query.answer()
    context.user_data["amenaza_vida"] = query.data
    pregunta = "¿El evento está verificado?"
    keyboard = [[InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(pregunta, reply_markup=reply_markup)
    return ESTADO_VERIFICADO
    
async def manejar_verificado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la respuesta de la verificación y pasa a las observaciones."""
                                      
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["verificado"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

    query = update.callback_query
    await query.answer()
    context.user_data["verificado"] = query.data

    pregunta = "Por favor, ingrese sus observaciones:"
    keyboard = [[InlineKeyboardButton("No tengo observaciones, continuar", callback_data="no_observaciones")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if context.user_data["verificado"] == "si":
        # Si el usuario respondió que sí, se muestra solo la pregunta con el botón
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
    else:
        # Si el usuario respondió que no, se muestra el mismo mensaje
        await query.edit_message_text(pregunta, reply_markup=reply_markup)

    return ESTADO_OBSERVACIONES

async def manejar_observaciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las observaciones y pide multimedia."""
                                    
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["observaciones"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

   
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        context.user_data["observaciones"] = "Sin observaciones."
        await query.edit_message_text("Por favor, adjunta hasta un máximo de 5 archivos de imágenes o videos. Si no tienes archivos, selecciona 'Continuar'.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data="continuar_multimedia")]]))
        context.user_data["recursos_multimedia"] = []
        return ESTADO_ESPERANDO_MULTIMEDIA
    else:
        context.user_data["observaciones"] = update.message.text
        await update.message.reply_text("Por favor, adjunta hasta un máximo de 5 archivos de imágenes o videos. Si no tienes archivos, selecciona 'Continuar'.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data="continuar_multimedia")]]))
        context.user_data["recursos_multimedia"] = []
        return ESTADO_ESPERANDO_MULTIMEDIA
    
async def manejar_multimedia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la subida de archivos multimedia, documentos y audios."""
                                     
      # <<<<<<<<<<<<<<<< BLOQUE GUARDAR MODIFICADO>>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        context.user_data["recursos_multimedia"] = update.message.text
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL  BLOQUE GUARDAR MODIFICADO >>>>>>>>>>>>>>>>>

   
       # Asegura que el array exista
    if "recursos_multimedia" not in context.user_data:
        context.user_data["recursos_multimedia"] = []
        
    # Limita la cantidad de archivos a 5
    if len(context.user_data["recursos_multimedia"]) >= 5:
        await update.message.reply_text("⚠️ Has alcanzado el límite de 5 archivos. Presiona 'Continuar' para seguir.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data="continuar_multimedia")]]))
        return ESTADO_ESPERANDO_MULTIMEDIA
    
    # Obtiene el ID del archivo, ahora incluyendo documentos y audios
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id # Guarda la foto de mayor resolución
    elif update.message.video:
        file_id = update.message.video.file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    elif update.message.audio:
        file_id = update.message.audio.file_id
    else:
        await update.message.reply_text("Por favor, envía solo imágenes, videos, documentos o audios.")
        return ESTADO_ESPERANDO_MULTIMEDIA
    
    context.user_data["recursos_multimedia"].append(file_id)
    
    if len(context.user_data["recursos_multimedia"]) < 5:
        await update.message.reply_text(f"✅ Archivo recibido. Puedes adjuntar {5 - len(context.user_data['recursos_multimedia'])} más, o presiona 'Continuar' para seguir.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ Continuar", callback_data="continuar_multimedia")]]))
        
    return ESTADO_ESPERANDO_MULTIMEDIA

async def pasar_a_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el botón de continuar y pasa al resumen."""
            # <<<<<<<<<<<<<<<< BLOQUE MODIFICACIÓN >>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        del context.user_data["en_modo_modificacion"]  # Desactivamos la bandera
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL BLOQUE MODIFICACIÓN >>>>>>>>>>>>>>>>>
    query = update.callback_query
    await query.answer()
    
    # Genera el código del reporte solo una vez antes de mostrar el resumen
    if "codigo_reporte" not in context.user_data:
        context.user_data["codigo_reporte"] = generar_codigo_reporte(
            context.user_data["nivel"], context.user_data["tipo_reporte"]
        )

    return await mostrar_resumen(update, context)

async def mostrar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el resumen del reporte con datos condicionales y los botones para confirmar o modificar."""
    datos_reporte = context.user_data
    
    # Construir el mensaje de resumen
    resumen_text = "<b>Resumen del Reporte</b>\n\n"
    
    # 1. Agregar el nombre y estado del usuario (visualización)
    resumen_text += "<b>Datos del Usuario</b>\n"
    resumen_text += f"<b>Nombre:</b> {datos_reporte.get('nombre_usuario', 'N/A')}\n"
    resumen_text += f"<b>Estado:</b> {datos_reporte.get('estado', 'N/A')}\n\n"
    
    # 2. Resumen del reporte (condicional por nivel y tipo)
    resumen_text += "<b>Datos del Reporte</b>\n"
    resumen_text += f"<b>Número de reporte:</b> {datos_reporte.get('numero_reporte', 'N/A')}\n"
    resumen_text += f"<b>Nivel de alerta:</b> {datos_reporte.get('nivel', 'N/A').capitalize()}\n"
    resumen_text += f"<b>Tipo de reporte:</b> {datos_reporte.get('tipo_reporte', 'N/A').capitalize()}\n"
    resumen_text += f"<b>Tipo de evento:</b> {datos_reporte.get('tipo_evento', 'N/A').capitalize()}\n"
    
    if datos_reporte.get("tipo_reporte") == "operacional":
        if datos_reporte.get("nivel_alerta") == "verde":
            resumen_text += f"<b>Descripción del evento:</b> {datos_reporte.get('descripcion_evento', 'N/A')}\n"
            resumen_text += f"<b>Acciones tomadas:</b> {datos_reporte.get('acciones_tomadas', 'N/A')}\n"
        elif datos_reporte.get("nivel_alerta") in ["amarilla", "naranja"]:
            resumen_text += f"<b>Descripción del evento:</b> {datos_reporte.get('descripcion_evento', 'N/A')}\n"
            resumen_text += f"<b>Recursos comprometidos:</b> {datos_reporte.get('recursos_comprometidos', 'N/A')}\n"
            resumen_text += f"<b>Acciones tomadas:</b> {datos_reporte.get('acciones_tomadas', 'N/A')}\n"
            resumen_text += f"<b>Hubo violencia:</b> {datos_reporte.get('violencia', 'N/A')}\n"
            resumen_text += f"<b>Hubo amenaza de vida:</b> {datos_reporte.get('amenaza', 'N/A')}\n"
        elif datos_reporte.get("nivel_alerta") == "roja":
            resumen_text += f"<b>Hubo violencia:</b> {datos_reporte.get('violencia', 'N/A')}\n"
            resumen_text += f"<b>Hubo amenaza de vida:</b> {datos_reporte.get('amenaza', 'N/A')}\n"
    else: # Flujo comunicacional
        if datos_reporte.get("nivel_alerta") == "verde":
            resumen_text += f"<b>Descripción del evento:</b> {datos_reporte.get('descripcion_evento', 'N/A')}\n"
            resumen_text += f"<b>Tipo de medio:</b> {datos_reporte.get('tipo_medio', 'N/A')}\n"
            resumen_text += f"<b>Nombre de medio:</b> {datos_reporte.get('nombre_medio', 'N/A')}\n"
            resumen_text += f"<b>Contenido difundido:</b> {datos_reporte.get('contenido_difundido', 'N/A')}\n"
        elif datos_reporte.get("nivel_alerta") in ["amarilla", "naranja"]:
            resumen_text += f"<b>Descripción del evento:</b> {datos_reporte.get('descripcion_evento', 'N/A')}\n"
            resumen_text += f"<b>Tipo de medio:</b> {datos_reporte.get('tipo_medio', 'N/A')}\n"
            resumen_text += f"<b>Nombre de medio:</b> {datos_reporte.get('nombre_medio', 'N/A')}\n"
            resumen_text += f"<b>Contenido difundido:</b> {datos_reporte.get('contenido_difundido', 'N/A')}\n"
            resumen_text += f"<b>Audiencia afectada:</b> {datos_reporte.get('audiencia_afectada', 'N/A')}\n"
            resumen_text += f"<b>Hubo violencia:</b> {datos_reporte.get('violencia', 'N/A')}\n"
            resumen_text += f"<b>Hubo amenaza de vida:</b> {datos_reporte.get('amenaza', 'N/A')}\n"
        elif datos_reporte.get("nivel_alerta") == "roja":
            resumen_text += f"<b>Hubo violencia:</b> {datos_reporte.get('violencia', 'N/A')}\n"
            resumen_text += f"<b>Hubo amenaza de vida:</b> {datos_reporte.get('amenaza', 'N/A')}\n"
            
    resumen_text += f"<b>Evento verificado:</b> {datos_reporte.get('verificado', 'N/A')}\n"
    resumen_text += f"<b>Observaciones:</b> {datos_reporte.get('observaciones', 'Sin observaciones')}\n"
    resumen_text += f"<b>Contenido multimedia:</b> {'Sí' if datos_reporte.get('multimedia_path') else 'No'}\n"

    # 3. Botones para Enviar, Editar y Cancelar
    keyboard = [
        [InlineKeyboardButton("✅ Enviar Reporte", callback_data="enviar_reporte")],
        [InlineKeyboardButton("✏️ Modificar Reporte", callback_data="modificar_reporte")],
        [InlineKeyboardButton("❌ Cancelar Reporte", callback_data="cancelar_reporte")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            resumen_text, 
            reply_markup=reply_markup, 
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            resumen_text, 
            reply_markup=reply_markup, 
            parse_mode="HTML"
        )
    
    return ESTADO_RESUMEN

async def manejar_modificar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la acción de modificar el reporte y muestra las opciones según el tipo y nivel de reporte."""
    query = update.callback_query
    await query.answer()
    context.user_data["en_modo_modificacion"] = True

    tipo_reporte = context.user_data.get("tipo_reporte")
    nivel = context.user_data.get("nivel")
    
    # Lista de botones base que siempre se muestran
    keyboard = [
          [InlineKeyboardButton("Tipo de evento", callback_data="mod_tipo_evento")],

    ]
    
    # Agregar preguntas según el flujo (operacional vs comunicacional)
    if tipo_reporte == "operacional":
        if nivel == "Verde":
            keyboard.extend([
                [InlineKeyboardButton("Descripción del evento", callback_data="mod_descripcion_evento")],
                [InlineKeyboardButton("Acciones tomadas", callback_data="mod_acciones_tomadas")],
            ])
        elif nivel in ["Amarilla", "Naranja"]:
            keyboard.extend([
                [InlineKeyboardButton("Descripción del evento", callback_data="mod_descripcion_evento")],
                [InlineKeyboardButton("Recursos comprometidos", callback_data="mod_recursos_comprometidos")],
                [InlineKeyboardButton("Acciones tomadas", callback_data="mod_acciones_tomadas")],
                [InlineKeyboardButton("Violencia", callback_data="mod_violencia")],
                [InlineKeyboardButton("Amenaza de vida", callback_data="mod_amenaza")],
            ])
        elif nivel == "Roja":
            keyboard.extend([
                [InlineKeyboardButton("Violencia", callback_data="mod_violencia")],
                [InlineKeyboardButton("Amenaza de vida", callback_data="mod_amenaza")],
            ])
    elif tipo_reporte == "comunicacional":
        if nivel == "Verde":
            keyboard.extend([
                [InlineKeyboardButton("Descripción del evento", callback_data="mod_descripcion_evento")],
                [InlineKeyboardButton("Tipo de medio", callback_data="mod_tipo_medio")],
                [InlineKeyboardButton("Nombre de medio", callback_data="mod_nombre_medio")],
                [InlineKeyboardButton("Contenido difundido", callback_data="mod_contenido_difundido")],
            ])
        elif nivel in ["Amarilla", "Naranja"]:
            keyboard.extend([
                [InlineKeyboardButton("Descripción del evento", callback_data="mod_descripcion_evento")],
                [InlineKeyboardButton("Tipo de medio", callback_data="mod_tipo_medio")],
                [InlineKeyboardButton("Nombre de medio", callback_data="mod_nombre_medio")],
                [InlineKeyboardButton("Contenido difundido", callback_data="mod_contenido_difundido")],
                [InlineKeyboardButton("Audiencia afectada", callback_data="mod_audiencia_afectada")],
                [InlineKeyboardButton("Violencia", callback_data="mod_violencia")],
                [InlineKeyboardButton("Amenaza de vida", callback_data="mod_amenaza")],
            ])
        elif nivel == "Roja":
            keyboard.extend([
                [InlineKeyboardButton("Violencia", callback_data="mod_violencia")],
                [InlineKeyboardButton("Amenaza de vida", callback_data="mod_amenaza")],
            ])

    # Agregar preguntas comunes a todos los reportes al final
    keyboard.extend([
        [InlineKeyboardButton("Verificado", callback_data="mod_verificado")],
        [InlineKeyboardButton("Observaciones", callback_data="mod_observaciones")],
        [InlineKeyboardButton("Contenido multimedia", callback_data="mod_multimedia")],
        [InlineKeyboardButton("Cancelar modificación", callback_data="cancelar_modificacion")],
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("Seleccione la pregunta que desea modificar:", reply_markup=reply_markup)
    return ESTADO_MODIFICAR

async def manejar_modificacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de la pregunta a modificar y redirige al estado correcto."""
            # <<<<<<<<<<<<<<<< BLOQUE MODIFICACIÓN >>>>>>>>>>>>>>>>>
    if context.user_data.get("en_modo_modificacion"):
        del context.user_data["en_modo_modificacion"]  # Desactivamos la bandera
        return await manejar_confirmacion_modificacion(update, context)
    # <<<<<<<<<<<<<<<< FIN DEL BLOQUE MODIFICACIÓN >>>>>>>>>>>>>>>>>
    query = update.callback_query
    await query.answer()
    
    opcion = query.data.replace("mod_", "") 
    
    if opcion == "nivel":
        pregunta = "Seleccione el nuevo nivel de alerta:"
        keyboard = [[InlineKeyboardButton("🟢 Verde", callback_data="verde")], [InlineKeyboardButton("🟡 Amarilla", callback_data="amarilla")], [InlineKeyboardButton("🟠 Naranja", callback_data="naranja")], [InlineKeyboardButton("🔴 Roja", callback_data="roja")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_NIVEL
    elif opcion == "tipo_reporte":
        pregunta = "Seleccione el nuevo tipo de reporte:"
        keyboard = [[InlineKeyboardButton("Operacional", callback_data="operacional")], [InlineKeyboardButton("Comunicacional", callback_data="comunicacional")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_TIPO_REPORTE
    elif opcion == "tipo_evento":
        pregunta = "Seleccione el nuevo tipo de evento:"
        keyboard = [[InlineKeyboardButton("Fluvial", callback_data="fluvial")], [InlineKeyboardButton("Maritimo", callback_data="maritimo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_TIPO_EVENTO_COMUN
    elif opcion == "descripcion_evento":
        pregunta = "Por favor, ingrese la nueva descripción del evento:"
        await query.edit_message_text(pregunta)
        return ESTADO_DESCRIPCION_EVENTO
    elif opcion == "acciones_tomadas":
        pregunta = "Por favor, ingrese las nuevas acciones tomadas:"
        await query.edit_message_text(pregunta)
        return ESTADO_ACCIONES_TOMADAS
    elif opcion == "recursos_comprometidos":
        pregunta = "Por favor, ingrese los nuevos recursos comprometidos:"
        await query.edit_message_text(pregunta)
        return ESTADO_RECURSOS_COMPROMETIDOS
    elif opcion == "tipo_medio":
        pregunta = "Por favor, ingrese el nuevo tipo de medio:"
        await query.edit_message_text(pregunta)
        return ESTADO_TIPO_MEDIO
    elif opcion == "nombre_medio":
        pregunta = "Por favor, ingrese el nuevo nombre del medio:"
        await query.edit_message_text(pregunta)
        return ESTADO_NOMBRE_MEDIO
    elif opcion == "contenido_difundido":
        pregunta = "Por favor, ingrese el nuevo contenido difundido:"
        await query.edit_message_text(pregunta)
        return ESTADO_CONTENIDO_DIFUNDIDO
    elif opcion == "audiencia_afectada":
        pregunta = "Por favor, ingrese la nueva audiencia afectada:"
        await query.edit_message_text(pregunta)
        return ESTADO_AUDIENCIA_AFECTADA
    elif opcion == "violencia":
        pregunta = "¿Hubo violencia?"
        keyboard = [[InlineKeyboardButton("Si", callback_data="si")], [InlineKeyboardButton("No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_VIOLENCIA
    elif opcion == "amenaza":
        pregunta = "¿Hubo amenaza de vida?"
        keyboard = [[InlineKeyboardButton("Si", callback_data="si")], [InlineKeyboardButton("No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_AMENAZA
    elif opcion == "verificado":
        pregunta = "¿El evento fue verificado?"
        keyboard = [[InlineKeyboardButton("Si", callback_data="si")], [InlineKeyboardButton("No", callback_data="no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_VERIFICADO
    elif opcion == "observaciones":
        pregunta = "Por favor, ingrese sus nuevas observaciones. Si no tiene, puede continuar."
        keyboard = [[InlineKeyboardButton("No tengo observaciones, continuar", callback_data="no_observaciones")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_OBSERVACIONES
    elif opcion == "multimedia":
        pregunta = "Por favor, adjunta hasta un máximo de 5 archivos de imágenes o videos. Si no tienes, selecciona 'Continuar'."
        keyboard = [[InlineKeyboardButton("Continuar", callback_data="continuar_multimedia")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(pregunta, reply_markup=reply_markup)
        return ESTADO_ESPERANDO_MULTIMEDIA
    elif opcion == "cancelar_modificacion":
        await query.edit_message_text("Modificación cancelada. Volviendo al resumen...")
        return await mostrar_resumen(update, context)

    await query.edit_message_text("Opción no válida. Por favor, intente de nuevo.")
    return ESTADO_MODIFICAR                 

async def manejar_confirmacion_modificacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra un mensaje de confirmación después de una modificación."""
    # Desactivamos el modo de modificación para que no se aplique a los siguientes pasos
    context.user_data["en_modo_modificacion"] = False
    
    # Manejar el caso de MessageHandler (para respuestas de texto)
    if update.message:
        await update.message.reply_text(
            "✅ Se ha modificado su respuesta.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("¿Desea seguir modificando?", callback_data="seguir_modificando")],
                [InlineKeyboardButton("Continuar", callback_data="continuar_a_resumen")]
            ])
        )
    # Manejar el caso de CallbackQueryHandler (para botones)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text="✅ Se ha modificado su respuesta. ¿Desea seguir modificando o continuar?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("¿Desea seguir modificando?", callback_data="seguir_modificando")],
                [InlineKeyboardButton("Continuar", callback_data="continuar_a_resumen")]
            ])
        )
    return ESTADO_CONFIRMACION_MODIFICACION


async def confirmar_y_enviar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma el reporte, lo envía y pregunta si desea hacer otro."""
    query = update.callback_query
    await query.answer()

    try:
        # Genera el número de reporte y lo guarda para el resumen final
        numero_reporte = "VO-" + datetime.now().strftime("%d%m%Y%H%M")
        context.user_data["numero_reporte"] = numero_reporte
        
        # Genera el resumen final para mostrar
        datos_reporte = context.user_data
        resumen_final_text = "<b>Reporte Enviado</b>\n\n"
        resumen_final_text += f"<b>Número de reporte:</b> {datos_reporte.get('numero_reporte', 'N/A')}\n"
        resumen_final_text += f"<b>Nivel de alerta:</b> {datos_reporte.get('nivel_alerta', 'N/A')}\n"
        resumen_final_text += f"<b>Tipo de reporte:</b> {datos_reporte.get('tipo_reporte', 'N/A')}\n"
        resumen_final_text += f"<b>Tipo de evento:</b> {datos_reporte.get('tipo_evento', 'N/A')}\n"
        # Añade aquí más campos si deseas que se muestren en el resumen final

        # 1. Enviar mensaje de éxito y el resumen final
        await query.edit_message_text(
            f"✅ ¡Reporte enviado exitosamente! Numero de Reporte: {numero_reporte}"
        )

        # 2. Preguntar si desea realizar otro reporte
        keyboard = [
            [InlineKeyboardButton("✅ Sí", callback_data="si_otro_reporte")],
            [InlineKeyboardButton("❌ No", callback_data="no_otro_reporte")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "¿Desea realizar otro reporte?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ocurrió un error al enviar el reporte: {e}")

    return ESTADO_REINICIAR


async def cancelar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela el proceso de reporte y termina la conversación."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❌ El reporte ha sido cancelado. Puedes iniciar uno nuevo con cualquier tecla.")
    context.user_data.clear()  # Limpiar los datos del reporte
    return ConversationHandler.END

async def reiniciar_o_finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la opción de reiniciar o finalizar, volviendo al estado de alerta si se desea."""
    query = update.callback_query
    await query.answer()

    if query.data == "si_otro_reporte":
        # Se guarda la cédula del usuario y se limpia el resto de la información del reporte anterior
        cedula = context.user_data.get("cedula")
        context.user_data.clear()
        context.user_data["cedula"] = cedula

        # Se dirige al usuario directamente a la selección del nivel de alerta
        personalized_welcome = "¿Qué nivel tiene el reporte?"
        keyboard = [
            [InlineKeyboardButton("🟢 Verde", callback_data="Verde")],
            [InlineKeyboardButton("🟡 Amarilla", callback_data="Amarilla")],
            [InlineKeyboardButton("🟠 Naranja", callback_data="Naranja")],
            [InlineKeyboardButton("🚨  Roja", callback_data="Roja")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("Ok, reiniciando el proceso.")
        await query.message.reply_text(personalized_welcome, reply_markup=reply_markup)
        
        return ESTADO_NIVEL
    else:
        await query.edit_message_text("Gracias por usar el sistema de alertas. ¡Hasta la próxima!")
        context.user_data.clear()
        return ConversationHandler.END

async def generar_resumen_final(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Genera una cadena de texto con el resumen completo del reporte para visualización."""
    datos_personales = context.user_data.get("datos_personales", {})
    datos_reporte = context.user_data.get("reporte", {})
    numero_reporte = context.user_data.get("numero_reporte", "N/A")
    
    # Formateo de datos personales
    nombre = datos_personales.get("nombre", "N/A")
    cedula = datos_personales.get("cedula", "N/A")
    estado_persona = datos_personales.get("estado", "N/A")
    
    # Formateo de datos del reporte
    nivel_alerta = datos_reporte.get("nivel_alerta", "N/A")
    tipo_reporte = datos_reporte.get("tipo_reporte", "N/A")
    tipo_evento = datos_reporte.get("tipo_evento", "N/A")
    descripcion_evento = datos_reporte.get("descripcion_evento", "N/A")
    acciones_tomadas = datos_reporte.get("acciones_tomadas", "N/A")
    recursos_comprometidos = datos_reporte.get("recursos_comprometidos", "N/A")
    violencia = datos_reporte.get("violencia", "N/A")
    amenaza = datos_reporte.get("amenaza", "N/A")
    tipo_medio = datos_reporte.get("tipo_medio", "N/A")
    nombre_medio = datos_reporte.get("nombre_medio", "N/A")
    contenido_difundido = datos_reporte.get("contenido_difundido", "N/A")
    audiencia_afectada = datos_reporte.get("audiencia_afectada", "N/A")
    verificado = datos_reporte.get("verificado", "N/A")
    observaciones = datos_reporte.get("observaciones", "N/A")
    multimedia_info = "Sí" if context.user_data.get("multimedia_path") else "No"

    # Generar la cadena de texto
    resumen = (
        f"**Datos personales:**\n"
        f"1. **Nombre:** {nombre}\n"
        f"2. **Cédula:** {cedula}\n"
        f"3. **Estado:** {estado_persona}\n\n"
        f"**Datos del reporte:**\n"
        f"1. **Número del reporte:** {numero_reporte}\n"
        f"2. **Nivel de Alerta:** {nivel_alerta}\n"
        f"3. **Tipo de Reporte:** {tipo_reporte}\n"
        f"4. **Tipo de Evento:** {tipo_evento}\n"
        f"5. **Descripción del Evento:** {descripcion_evento}\n"
        f"6. **Acciones Tomadas:** {acciones_tomadas}\n"
        f"7. **Recursos Comprometidos:** {recursos_comprometidos}\n"
        f"8. **Violencia:** {violencia}\n"
        f"9. **Amenaza:** {amenaza}\n"
        f"10. **Tipo de Medio:** {tipo_medio}\n"
        f"11. **Nombre del Medio:** {nombre_medio}\n"
        f"12. **Contenido Difundido:** {contenido_difundido}\n"
        f"13. **Audiencia Afectada:** {audiencia_afectada}\n"
        f"14. **Verificado:** {verificado}\n"
        f"15. **Observaciones:** {observaciones}\n"
        f"16. **Multimedia:** {multimedia_info}\n"
    )
    return resumen
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación."""
    await update.message.reply_text("Conversación cancelada. Puedes empezar de nuevo con cualquier tecla", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None:
    """Inicia el bot."""
    print("Bot iniciado. Esperando mensajes...")
    
    # Comprobamos la conexión a la base de datos para depuración
    conn = obtener_conexion_db()
    if conn:
        print("✅ Conexión a la base de datos exitosa.")
        conn.close()
    else:
        print("❌ Error: No se pudo conectar a la base de datos. Por favor, revisa tus credenciales en el archivo .env.")

    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, start),
            CallbackQueryHandler(reintentar_cedula, pattern="^reintentar_cedula$")

        ],
        states={
            ESTADO_CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_cedula)],
            ESTADO_NIVEL: [CallbackQueryHandler(manejar_nivel, pattern="^Verde|Amarilla|Naranja|Roja$")],
            ESTADO_TIPO_REPORTE: [CallbackQueryHandler(pedir_tipo_evento, pattern='^operacional$|^comunicacional$'),],
            
            # ESTADO: Muestra el menú de Tipo de Evento y espera la selección
            ESTADO_TIPO_EVENTO_COMUN: [CallbackQueryHandler(manejar_tipo_evento_y_ramificar, pattern='^evento_.*$'),],
        
            # ESTADO: Espera el texto de "Otros"
            ESTADO_OTRO_EVENTO_COMUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_otro_evento_y_ramificar)],
            # Flujo de reporte operacional
            ESTADO_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_descripcion)],
            ESTADO_RECURSOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_recursos)],
            ESTADO_ACCIONES: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_acciones)],

            # Flujo de reporte comunicacional
            ESTADO_DESCRIPCION_COMUNICACIONAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_descripcion_comunicacional)],
            ESTADO_TIPO_MEDIO: [CallbackQueryHandler(manejar_tipo_medio, pattern="^red_social|prensa|radio|television$")],
            ESTADO_MEDIO_ESPECIFICO: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_medio_especifico)],
            ESTADO_CONTENIDO_DIFUNDIDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_contenido_difundido)],
            ESTADO_AUDIENCIA_AFECTADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_audiencia_afectada)],
            

            # Flujo compartido
            ESTADO_VIOLENCIA: [CallbackQueryHandler(manejar_violencia, pattern="^si|no$")],
            ESTADO_AMENAZA: [CallbackQueryHandler(manejar_amenaza, pattern="^si|no$")],
            ESTADO_VERIFICADO: [CallbackQueryHandler(manejar_verificado, pattern="^si|no$")],
            ESTADO_OBSERVACIONES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_observaciones),
                CallbackQueryHandler(manejar_observaciones, pattern="^no_observaciones$")
            ],
            
            # Estado compartido para multimedia y resumen
            ESTADO_ESPERANDO_MULTIMEDIA: [
                MessageHandler(filters.PHOTO | filters.VIDEO, manejar_multimedia),
                CallbackQueryHandler(pasar_a_resumen, pattern="^continuar_multimedia$")
            ],
            ESTADO_RESUMEN: [
                CallbackQueryHandler(confirmar_y_enviar, pattern="^enviar_reporte$"),
                CallbackQueryHandler(manejar_modificar_reporte, pattern="^modificar_reporte$"),
                CallbackQueryHandler(cancelar_reporte, pattern="^cancelar_reporte$") # <--- AÑADE ESTA LÍNEA
            ],
            ESTADO_REINICIAR: [
                CallbackQueryHandler(reiniciar_o_finalizar, pattern="^si_otro_reporte|no_otro_reporte$")
            ],
            
            # --- Corrección para el flujo de modificación ---
            ESTADO_MODIFICAR: [
                # Este manejador dirigirá a la función que pide el nuevo valor
                CallbackQueryHandler(manejar_modificacion, pattern="^mod_.*$"),
                CallbackQueryHandler(mostrar_resumen, pattern="^cancelar_modificacion$")
            ],
            #  Estado de confirmación (no necesita cambios)
            ESTADO_CONFIRMACION_MODIFICACION: [
                CallbackQueryHandler(manejar_modificar_reporte, pattern="^seguir_modificando$"),
                CallbackQueryHandler(mostrar_resumen, pattern="^continuar_a_resumen$")
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    application.add_handler(conv_handler)
    
 # Iniciar el bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()  