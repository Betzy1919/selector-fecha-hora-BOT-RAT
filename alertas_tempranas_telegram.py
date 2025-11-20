import logging
from dotenv import load_dotenv
import os
import warnings
import telegram 
from telegram.warnings import PTBUserWarning
from telegram import Update
from flask import Flask, request

from telegram.ext import (
    Application, CommandHandler, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)


# --- IMPORTS DE MÓDULOS REORGANIZADOS ---
from configuracion.constantes import (
    

    # --- CONSTANTES DE NAVEGACIÓN ---

    CALLBACK_INICIO,
    CALLBACK_FINALIZAR,
    CALLBACK_ANTERIOR,
    CALLBACK_ENVIAR_REPORTE,
    CALLBACK_MODIFICAR_REPORTE,
    CALLBACK_CANCELAR_REPORTE,

# Estados del ConversationHandler

    ESTADO_CEDULA,
    ESTADO_NIVEL,
    ESTADO_TIPO_REPORTE,
    ESTADO_TIPO_EVENTO,
    ESTADO_DESCRIPCION,
    ESTADO_RECURSOS,
    ESTADO_ACCIONES,
    ESTADO_VERIFICADO,
    ESTADO_VIOLENCIA,
    ESTADO_AMENAZA,
    ESTADO_OBSERVACIONES,
    ESTADO_ESPERANDO_MULTIMEDIA,

# Estados para flujo comunicacional

    ESTADO_TIPO_EVENTO_COMUNICACIONAL,
    ESTADO_DESCRIPCION_COMUNICACIONAL,
    ESTADO_TIPO_MEDIO,
    ESTADO_MEDIO_ESPECIFICO,
    ESTADO_CONTENIDO_DIFUNDIDO,
    ESTADO_AUDIENCIA_AFECTADA,
    ESTADO_FECHA_PUBLICACION,
# Estados para flujo operacional
    
    ESTADO_DESCRIPCION_EVENTO,
    ESTADO_ACCIONES_TOMADAS,

# Estados para alerta roja

    ESTADO_TIPO_EVENTO_TEXTO_ROJA,

# Estados especiales

    ESTADO_RESUMEN,
    ESTADO_MODIFICAR,
    ESTADO_REINICIAR,
    ESTADO_CONFIRMACION_MODIFICACION,
    ESTADO_VERDE_OP_DESC,
    ESTADO_VERDE_OP_ACCIONES,
    ESTADO_VERDE_OP_VERIFICACION,
    ESTADO_ACTORES_CLAVE,
   


)



from handlers.resumen import (
    pasar_a_resumen,manejar_modificar_reporte,manejar_modificacion,mostrar_resumen,continuar_a_resumen
)


from handlers.conversacion import (
    start, manejar_nivel,manejar_cedula,reintentar_cedula,manejar_tipo_reporte,manejar_tipo_evento,
    manejar_recursos,manejar_acciones,manejar_tipo_medio,manejar_tipo_evento_comunicacional, 
    manejar_medio_especifico,manejar_audiencia_afectada,
    manejar_tipo_evento_texto_roja,manejar_violencia,manejar_amenaza,manejar_verificado,
    manejar_observaciones,manejar_observaciones,manejar_multimedia,cancelar,
    manejar_acciones_tomadas,continuar_multimedia, manejar_descripcion_evento, manejar_descripcion_comunicacional,
    manejar_actores_clave,manejar_verificacion_verde_op,manejar_contenido_difundido,
    manejar_fecha_manual,manejar_tipo_medio,manejar_datos_webapp
)

from handlers.navegacion import (
    regresar_al_inicio, finalizar_reporte,regresar_a_pregunta_anterior, finalizar_reporte,cancelar_reporte,reiniciar_o_finalizar,
)
from handlers.utils import (
    obtener_conexion_db,confirmar_envio,
)




print(f"Versión de python-telegram-bot: {telegram.__version__}")

# Ignorar la advertencia específica de python-telegram-bot
warnings.filterwarnings("ignore", category=PTBUserWarning)
# Carga las variables de entorno desde el archivo .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TU_TOKEN_AQUI")



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

    
# --- DEFINICIÓN DE HANDLERS DE NAVEGACIÓN UNIVERSAL (Añadir antes del conv_handler) ---

    NavegacionHandlers = [
        CallbackQueryHandler(regresar_al_inicio, pattern=f"^{CALLBACK_INICIO}$"),
        CallbackQueryHandler(finalizar_reporte, pattern=f"^{CALLBACK_FINALIZAR}$"),
        CallbackQueryHandler(regresar_a_pregunta_anterior, pattern=f"^{CALLBACK_ANTERIOR}$"),
        CallbackQueryHandler(confirmar_envio, pattern=f"^{CALLBACK_ENVIAR_REPORTE}$"),
        CallbackQueryHandler(manejar_modificar_reporte, pattern=f"^{CALLBACK_MODIFICAR_REPORTE}$"),
        CallbackQueryHandler(cancelar_reporte, pattern=f"^{CALLBACK_CANCELAR_REPORTE}$"),
        ]

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, start),
            CallbackQueryHandler(reintentar_cedula, pattern="^reintentar_cedula$")

        ],
        states={
            
            ESTADO_CEDULA: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_cedula),
            *NavegacionHandlers,
             ],
            ESTADO_NIVEL: [CallbackQueryHandler(manejar_nivel, pattern="^Verde|Amarilla|Naranja|Roja$"),
            *NavegacionHandlers,
            ],
            ESTADO_TIPO_REPORTE: [CallbackQueryHandler(manejar_tipo_reporte, pattern="^operacional|comunicacional$"),
            *NavegacionHandlers,
            ],
            # --- ESTADO DE DESCRIPCIÓN (ESPERA TEXTO Y NAVEGACIÓN) ---
            ESTADO_VERDE_OP_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ESTADO_VERDE_OP_DESC), 
            *NavegacionHandlers,
            ],

            # --- ESTADO DE ACCIONES TOMADAS (ESPERA TEXTO Y NAVEGACIÓN) ---
            ESTADO_VERDE_OP_ACCIONES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ESTADO_VERDE_OP_ACCIONES),
            *NavegacionHandlers,
            ],
            # Flujo de reporte operacional
            ESTADO_TIPO_EVENTO: [
            CallbackQueryHandler(manejar_tipo_evento),
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_tipo_evento),
            *NavegacionHandlers,
        ],
        

            ESTADO_TIPO_EVENTO_COMUNICACIONAL: [
            CallbackQueryHandler(manejar_tipo_evento_comunicacional),
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_tipo_evento_comunicacional),
            *NavegacionHandlers,
        ],
            ESTADO_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_descripcion_evento),
            *NavegacionHandlers,
            ],
            ESTADO_DESCRIPCION_EVENTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_descripcion_evento),
            *NavegacionHandlers,
        ],

            ESTADO_RECURSOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_recursos),
            *NavegacionHandlers,
            ],
            ESTADO_ACCIONES: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_acciones),
            *NavegacionHandlers,
            ],
            ESTADO_VERDE_OP_VERIFICACION: [CallbackQueryHandler(manejar_verificacion_verde_op, pattern="^si_verificado|no_verificado"),
            *NavegacionHandlers,
            ],
           
            # Flujo de reporte comunicacional
            ESTADO_CONTENIDO_DIFUNDIDO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_contenido_difundido),
            *NavegacionHandlers,
        ],
            ESTADO_DESCRIPCION_COMUNICACIONAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_descripcion_comunicacional),
            *NavegacionHandlers,
            ],
            ESTADO_TIPO_MEDIO: [CallbackQueryHandler(manejar_tipo_medio, pattern="^red_social|prensa|radio|television$"),
            *NavegacionHandlers,
            ],
            ESTADO_MEDIO_ESPECIFICO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_medio_especifico),
            CallbackQueryHandler(manejar_medio_especifico), 
            *NavegacionHandlers,
              ],              
           
            ESTADO_FECHA_PUBLICACION: [
            # 🔑 CLAVE 2: Nuevo manejador para los datos de la WebApp
            MessageHandler(filters.StatusUpdate.WEB_APP_DATA, manejar_datos_webapp), 
            
            # Mantener el manejador de texto manual por si acaso
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_fecha_manual), 
            
            *NavegacionHandlers,
        ],
            ESTADO_ACTORES_CLAVE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_actores_clave),
            *NavegacionHandlers,
            ],
            ESTADO_AUDIENCIA_AFECTADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_audiencia_afectada),
            *NavegacionHandlers,
            ],
            
            
            # Nuevo estado para la alerta roja
            ESTADO_TIPO_EVENTO_TEXTO_ROJA: [
            CallbackQueryHandler(manejar_tipo_evento_texto_roja),
            MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_tipo_evento_texto_roja),
            *NavegacionHandlers,
              ],

            # Flujo compartido
            ESTADO_VIOLENCIA: [CallbackQueryHandler(manejar_violencia, pattern="^si|no$"),
            *NavegacionHandlers,
            ],
            ESTADO_AMENAZA: [CallbackQueryHandler(manejar_amenaza, pattern="^si|no$"),
            *NavegacionHandlers,
            ],
            ESTADO_VERIFICADO: [CallbackQueryHandler(manejar_verificado, pattern="^si|no$"),
            *NavegacionHandlers,
            ],
            ESTADO_OBSERVACIONES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_observaciones),
                CallbackQueryHandler(manejar_observaciones, pattern="^no_observaciones$"),
                *NavegacionHandlers,

            ],
            ESTADO_ACCIONES_TOMADAS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_acciones_tomadas),
                *NavegacionHandlers,
            ],
                        # Estado compartido para multimedia y resumen
            ESTADO_ESPERANDO_MULTIMEDIA: [
                MessageHandler(filters.ALL, manejar_multimedia),
                CallbackQueryHandler(pasar_a_resumen, pattern="^continuar_sin_multimedia$"),
                CallbackQueryHandler(continuar_multimedia, pattern="^continuar_multimedia$"),
                *NavegacionHandlers,
            ],
            ESTADO_RESUMEN: [
                CallbackQueryHandler(confirmar_envio, pattern="^enviar_reporte$"),
                CallbackQueryHandler(manejar_modificar_reporte, pattern="^modificar_reporte$"),
                CallbackQueryHandler(cancelar_reporte, pattern="^cancelar_reporte$"),
                *NavegacionHandlers,

            ],
            ESTADO_REINICIAR: [
                CallbackQueryHandler(reiniciar_o_finalizar, pattern="^si_otro_reporte|no_otro_reporte$"),
                *NavegacionHandlers,
                ],
            
            # --- Corrección para el flujo de modificación ---
            ESTADO_MODIFICAR: [
                # Este manejador dirigirá a la función que pide el nuevo valor
                CallbackQueryHandler(manejar_modificacion, pattern="^mod_.*$"),
                CallbackQueryHandler(continuar_a_resumen, pattern='^continuar_a_resumen$'),
                CallbackQueryHandler(mostrar_resumen, pattern="^cancelar_modificacion$"),
                *NavegacionHandlers,

            ],
            #  Estado de confirmación (no necesita cambios)
            ESTADO_CONFIRMACION_MODIFICACION: [
                CallbackQueryHandler(manejar_modificar_reporte, pattern="^seguir_modificando$"),
                CallbackQueryHandler(mostrar_resumen, pattern="^continuar_a_resumen$"),
                *NavegacionHandlers,

            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    application.add_handler(conv_handler)
    
 # Iniciar el bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)




if __name__ == "__main__":
    main()  