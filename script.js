body {
    background-color: var(--tg-theme-bg-color, #ffffff); /* Usa el color de fondo de Telegram */
    color: var(--tg-theme-text-color, #000000); /* Usa el color de texto de Telegram */
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
    padding: 20px;
}

/* Estilos para el contenedor del input */
.input-container {
    text-align: center;
    margin-bottom: 25px;
}

.input-label {
    display: block;
    font-size: 1.1em;
    font-weight: 600;
    color: var(--tg-theme-hint-color, #999); /* Color de pista de Telegram */
    margin-bottom: 10px;
}

/* Estilo principal para el input nativo */
.native-datetime-input {
    width: 90%; /* Ancho responsivo */
    max-width: 350px;
    padding: 15px;
    font-size: 1.2em;
    border: 2px solid var(--tg-theme-button-color, #5ac8fa); /* Borde con color de botón de Telegram */
    border-radius: 12px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    background-color: var(--tg-theme-secondary-bg-color, #f0f0f0); /* Fondo secundario de Telegram */
    color: var(--tg-theme-text-color, #000000);
    text-align: center;
    /* Esto es importante para que el texto se vea centrado */
    line-height: 1.5;
}

/* Estilos para el resumen/estado */
.summary-box {
    margin-top: 20px;
    padding: 10px;
    border: 1px dashed var(--tg-theme-link-color, #007aff);
    border-radius: 8px;
    text-align: center;
    font-weight: 500;
    color: var(--tg-theme-text-color, #000000);
}
