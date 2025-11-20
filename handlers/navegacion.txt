# handlers/navigation.py

from configuracion.constantes import ESTADO_NIVEL
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import logging

logger = logging.getLogger("AlertasTempranasBot")
from telegram.ext import (
    ContextTypes,
    ConversationHandler
    )
from .utils import (
    crear_menu_alerta, merge_keyboard_with_navigation,crear_botones_navegacion,opciones_evento_critico,
    opciones_evento_verde_operacional,opciones_evento_verde_comunicacional,borrar_pregunta_anterior)

from configuracion.constantes import (
    ESTADO_CEDULA,ESTADO_NIVEL, ESTADO_TIPO_REPORTE, ESTADO_VERDE_OP_DESC, ESTADO_VERDE_OP_ACCIONES,
    ESTADO_VERIFICADO,ESTADO_OBSERVACIONES,ESTADO_ESPERANDO_MULTIMEDIA,ESTADO_VIOLENCIA,ESTADO_TIPO_EVENTO_TEXTO_ROJA,
    ESTADO_TIPO_EVENTO,ESTADO_TIPO_EVENTO_COMUNICACIONAL,ESTADO_DESCRIPCION_COMUNICACIONAL, ESTADO_TIPO_MEDIO,
    ESTADO_DESCRIPCION, ESTADO_ACCIONES_TOMADAS,ESTADO_RECURSOS,ESTADO_MEDIO_ESPECIFICO,ESTADO_CONTENIDO_DIFUNDIDO,ESTADO_AUDIENCIA_AFECTADA,
    ESTADO_AMENAZA,ESTADO_ACTORES_CLAVE,ESTADO_FECHA_PUBLICACION,ESTADO_ACCIONES
)
from .conversacion import (
    manejar_cedula, manejar_nivel, manejar_tipo_reporte, manejar_tipo_evento,
    manejar_descripcion, manejar_recursos, manejar_acciones,
    manejar_tipo_evento_comunicacional, manejar_descripcion_comunicacional,
    manejar_medio_especifico, manejar_contenido_difundido, manejar_audiencia_afectada,
    manejar_violencia, manejar_amenaza, manejar_verificado, manejar_observaciones,
    manejar_multimedia,start,manejar_tipo_medio
)

estado_funciones = {
    ESTADO_CEDULA: manejar_cedula,
    ESTADO_NIVEL: manejar_nivel,
    ESTADO_TIPO_REPORTE: manejar_tipo_reporte,
    ESTADO_TIPO_EVENTO: manejar_tipo_evento,
    ESTADO_DESCRIPCION: manejar_descripcion,
    ESTADO_RECURSOS: manejar_recursos,
    ESTADO_ACCIONES_TOMADAS: manejar_acciones,
    ESTADO_TIPO_EVENTO_COMUNICACIONAL: manejar_tipo_evento_comunicacional,
    ESTADO_DESCRIPCION_COMUNICACIONAL: manejar_descripcion_comunicacional,
    ESTADO_TIPO_MEDIO:manejar_tipo_medio,
    ESTADO_MEDIO_ESPECIFICO: manejar_medio_especifico,
    ESTADO_CONTENIDO_DIFUNDIDO: manejar_contenido_difundido,
    ESTADO_AUDIENCIA_AFECTADA: manejar_audiencia_afectada,
    ESTADO_VIOLENCIA: manejar_violencia,
    ESTADO_AMENAZA: manejar_amenaza,
    ESTADO_VERIFICADO: manejar_verificado,
    ESTADO_OBSERVACIONES: manejar_observaciones,
    ESTADO_ESPERANDO_MULTIMEDIA: manejar_multimedia,
}



# --- FUNCIONES AUXILIARES DE TECLADO ---

#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< cancelar_reporte >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

async def cancelar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela el proceso de reporte y termina la conversación."""
       # eliminar_mensaje_anterior

    await borrar_pregunta_anterior(context, update)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❌ El reporte ha sido cancelado. Puedes iniciar uno nuevo con cualquier tecla.")
    context.user_data.clear()  # Limpiar los datos del reporte
    return ConversationHandler.END

#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< reiniciar_o_finalizar >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
async def reiniciar_o_finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la opción de reiniciar o finalizar, volviendo al estado de alerta si se desea."""
    query = update.callback_query
    await query.answer()

    # --- 1. 🔑 RESCATE DE DATOS DEL USUARIO (ANTES DE LIMPIAR) ---
    # 1.1 Intentamos obtener los datos de la estructura anidada y el nivel superior
    datos_anidados = context.user_data.get("datos_personales", {})
    cedula_guardada = context.user_data.get("cedula")
    
    # 1.2 Extracción exhaustiva del NOMBRE
    posibles_nombres = [
        datos_anidados.get("nombre_usuario"),
        datos_anidados.get("nombre"),
        context.user_data.get("nombre_usuario"),
        context.user_data.get("nombre"),
        context.user_data.get("nombre_completo"), 
        context.user_data.get("full_name"),      
        context.user_data.get("user_name"),      
        datos_anidados.get("full_name"),         
    ]
    nombre_guardado = next((n for n in posibles_nombres if n), None)

    # 1.3 Extracción exhaustiva del ESTADO
    posibles_estados = [
        datos_anidados.get("estado"),
        datos_anidados.get("estado_persona"),
        context.user_data.get("estado"),
        context.user_data.get("estado_persona"),
    ]
    estado_guardado = next((e for e in posibles_estados if e), None)
    
    # -----------------------------------------------------------

    if query.data == "si_otro_reporte":
        
        # 2. 🧹 LIMPIAR TODO el contexto del reporte anterior
        logger.info("Limpiando context.user_data para nuevo reporte.")
        context.user_data.clear() 
        
        # 3. 🔄 RESTAURAR los datos de identificación
        
        # 3.1 Restauración para el Resumen (Estructura anidada 'datos_personales')
        datos_usuario_final = {
            "nombre_usuario": nombre_guardado if nombre_guardado else "N/D",
            "estado": estado_guardado if estado_guardado else "N/D",
        }
        context.user_data["datos_personales"] = datos_usuario_final
            
        # 3.2 Restaurar Cédula a nivel superior
        if cedula_guardada:
             context.user_data["cedula"] = cedula_guardada
             
        # 3.3 🚨 CORRECCIÓN CLAVE: Restaurar Nombre y Estado a nivel superior.
        # Esto satisface a la función de validación/envío que te está dando el error.
        if nombre_guardado:
            # Asumimos que la función busca una de estas claves
            context.user_data["nombre_usuario"] = nombre_guardado
            context.user_data["nombre"] = nombre_guardado
        if estado_guardado:
            # La validación probablemente busca esta clave
            context.user_data["estado"] = estado_guardado 
             
        # 4. 🆕 INICIALIZAR ESTRUCTURAS DE DATOS VACÍAS PARA EL NUEVO REPORTE
        context.user_data["reporte"] = {}
        context.user_data["historial"] = []
        context.user_data["multimedia_path"] = []
        context.user_data["pregunta_id"] = None
        context.user_data["observaciones"] = ""

        # 5. Limpiar mensajes anteriores
        await borrar_pregunta_anterior(context, update) 

        # --- Flujo del Nuevo Reporte (Nivel de Alerta) ---
        
        personalized_welcome = "Por favor, selecciona el **Nivel de Alerta**:"
        keyboard = [
            [InlineKeyboardButton("🟢 Verde", callback_data="Verde")],
            [InlineKeyboardButton("🟡 Amarilla", callback_data="Amarilla")],
            [InlineKeyboardButton("🟠 Naranja", callback_data="Naranja")],
            [InlineKeyboardButton("🚨 Roja", callback_data="Roja")],
        ]
        
        # Obtenemos los datos para mostrar en el mensaje (usando la clave anidada restaurada)
        nombre_display = context.user_data["datos_personales"].get('nombre_usuario', 'N/D')
        estado_display = context.user_data["datos_personales"].get('estado', 'N/D')
        
        reply_markup = InlineKeyboardMarkup(merge_keyboard_with_navigation(keyboard))
        
        # Enviar el mensaje que inicia el nuevo reporte
        mensaje = await query.message.reply_text(
            "✅ **Reporte anterior finalizado. Iniciando nuevo reporte.**\n\n"
            f"{personalized_welcome}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        context.user_data["pregunta_id"] = mensaje.message_id
        
        return ESTADO_NIVEL 
        
    elif query.data == "no_otro_reporte":
        await query.message.edit_text(
            "Gracias por usar el sistema de Alertas Tempranas. ¡Hasta pronto!"
        )
        context.user_data.clear()
        return ConversationHandler.END

    return ConversationHandler.END
    
#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< finalizar_reporte >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


async def finalizar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finaliza el reporte y cancela la conversación."""
    query = update.callback_query
    await query.answer("Reporte finalizado.")
    
    # Edita el mensaje final
    await query.edit_message_text(
        "❌ Reporte Cancelado. ¡Gracias por usar el sistema de Alertas Tempranas!\n\n"
        "¡Los datos no fueron guardados!\n\n"
        "Escribe cualquier letra o número para comenzar un nuevo reporte.",
        parse_mode='Markdown'
    )
    
    context.user_data.clear() 
    return ConversationHandler.END


# --- MANEJADORES DE NAVEGACIÓN UNIVERSAL  ---ç

#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< regresar_al_inicio >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


async def regresar_al_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejador para regresar al inicio (a la selección de nivel de alerta)."""
    query = update.callback_query
    await query.answer("Regresando al inicio...")
    
    # 1. Limpia todos los datos de la conversación
    context.user_data.clear() 
    context.user_data['history_stack'] = [] # Limpiamos también la pila de historial
    
    # 2. Regenera el mensaje de inicio (Bienvenida)
    welcome_message = (
        "👋 *Conversación reiniciada.*\n\n"
        "¿Qué nivel tiene el reporte?:"
    )
    
    # Ahora sí, la función crear_menu_alerta está definida
    reply_markup = InlineKeyboardMarkup(merge_keyboard_with_navigation(crear_menu_alerta(), es_inicio=True))
    
    # Usamos query.edit_message_text para modificar el mensaje donde se presionó el botón
    await query.edit_message_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # 3. Retorna el estado inicial
    return ESTADO_NIVEL

#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< regresar_a_pregunta_anterior >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

async def regresar_a_pregunta_anterior(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if 'history_stack' not in context.user_data or len(context.user_data['history_stack']) < 2:
        await query.edit_message_text(
            "⚠️ Historial vacío o insuficiente. Regresando a la selección del Nivel de Alerta.",
            parse_mode='Markdown'
        )
        context.user_data['history_stack'] = []
        return await start(update, context)

    previous_state = context.user_data['history_stack'].pop()

    # ✅ Activamos bandera para distinguir origen
    context.user_data["modificando_por_anterior"] = True

    return await mostrar_pregunta_por_estado(update, context, previous_state)


#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< mostrar_pregunta_por_estado >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

async def mostrar_pregunta_por_estado(update, context, estado):
    query = update.callback_query
    await query.answer()

    # Mensaje de transición
    await query.edit_message_text(
        "🔙 *Regresando al paso anterior..*",
        parse_mode='Markdown'
    )

    context.user_data["en_modo_modificacion"] = True

    # Estados que esperan texto
    preguntas_texto = {
        ESTADO_CEDULA: "Por favor, ingresa tu número de cédula:",
        ESTADO_DESCRIPCION: "Por favor, ingresa la descripción del evento:",
        ESTADO_RECURSOS: "Por favor, ingresa los recursos comprometidos:",
        ESTADO_DESCRIPCION_COMUNICACIONAL: "Por favor, ingresa la descripción del evento:",
        ESTADO_MEDIO_ESPECIFICO: "Por favor, ingresa el nombre del medio específico:",
        ESTADO_CONTENIDO_DIFUNDIDO: "Por favor, ingresa el contenido difundido:",
        ESTADO_AUDIENCIA_AFECTADA: "Por favor, ingresa la audiencia afectada:",
        ESTADO_ACTORES_CLAVE: "Por favor, ingresa los actores clave:",
        ESTADO_FECHA_PUBLICACION: "🗓️ Por favor, escribe la fecha y hora del evento en este formato:<br><br><code>27/10/2025 11:00 AM</code>",
        ESTADO_ACCIONES: "Por favor, ingresa las acciones tomadas:",

 }

    # Estados que esperan botones
    preguntas_botones = {
        ESTADO_NIVEL: {
            "texto": "¿Qué nivel tiene el reporte?",
            "teclado": [
                [InlineKeyboardButton("🟢 Verde", callback_data="Verde")],
                [InlineKeyboardButton("🟡 Amarilla", callback_data="Amarilla")],
                [InlineKeyboardButton("🟠 Naranja", callback_data="Naranja")],
                [InlineKeyboardButton("🚨 Roja", callback_data="Roja")]
            ]
        },
        ESTADO_TIPO_REPORTE: {
            "texto": "Por favor, Seleccione el *Tipo de Reporte*:",
            "teclado": [
                [InlineKeyboardButton("1. Operacional", callback_data="operacional")],
                [InlineKeyboardButton("2. Comunicacional", callback_data="comunicacional")]
            ]
        },
        ESTADO_VERIFICADO: {
            "texto": "¿El evento está verificado?",
            "teclado": [
                [InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]
            ]
        },
        ESTADO_VIOLENCIA: {
            "texto": "¿Hubo violencia?",
            "teclado": [
                [InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]
            ]
        },
        ESTADO_AMENAZA: {
            "texto": "¿Hubo amenaza a la vida?",
            "teclado": [
                [InlineKeyboardButton("✅ Sí", callback_data="si"), InlineKeyboardButton("❌ No", callback_data="no")]
            ]
        },
        ESTADO_TIPO_MEDIO: {
            "texto": "Por favor, Seleccione el tipo de medio:",
            "teclado": [
                [InlineKeyboardButton("Red Social", callback_data="red_social")],
                [InlineKeyboardButton("Prensa", callback_data="prensa")],
                [InlineKeyboardButton("Radio", callback_data="radio")],
                [InlineKeyboardButton("Televisión", callback_data="television")]
            ]
        },

        ESTADO_OBSERVACIONES: {
            "texto": "Por favor, ingrese sus observaciones:o presiona 'Continuar'.",
            "teclado": [
                    [InlineKeyboardButton("No tengo observaciones, continuar", callback_data="no_observaciones")]
            ]
        },
        ESTADO_ESPERANDO_MULTIMEDIA: {
            "texto": "Por favor, Adjunte hasta 5 archivos o presiona 'Continuar'.",
            "teclado": [
                [InlineKeyboardButton("➡️ Continuar", callback_data="continuar_multimedia")]
            ]
        },

        ESTADO_TIPO_EVENTO: {
            "texto": "Por favor, ingrese el tipo de evento:",
            "teclado": opciones_evento_critico  # Puedes ajustar dinámicamente si quieres
        },
        ESTADO_TIPO_EVENTO_COMUNICACIONAL: {
            "texto": "Por favor, ingrese el tipo de evento:",
            "teclado": opciones_evento_critico  # O usar las verdes si el nivel es Verde
        },


    }

    # Mostrar pregunta de texto
    if estado in preguntas_texto:
        await query.message.reply_text(
            preguntas_texto[estado],
            reply_markup=InlineKeyboardMarkup(crear_botones_navegacion())
        )
        return estado

    # Mostrar pregunta con botones
    if estado in preguntas_botones:
        pregunta = preguntas_botones[estado]
        reply_markup = InlineKeyboardMarkup(merge_keyboard_with_navigation(pregunta["teclado"]))
        await query.message.reply_text(pregunta["texto"], reply_markup=reply_markup)
        return estado

    # Fallback genérico
    await query.message.reply_text(
        "Por favor, ingresa el dato requerido:",
        reply_markup=InlineKeyboardMarkup(crear_botones_navegacion())
    )
    return estado
