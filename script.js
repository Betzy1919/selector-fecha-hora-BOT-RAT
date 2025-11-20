// --- 1. Inicializar con Fecha/Hora Actual ---
function inicializarValoresActuales() {
    const input = document.getElementById("fechaHora");
    const now = new Date();
    
    // Formato requerido por <input type="datetime-local"> es YYYY-MM-DDTHH:MM
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0'); // Mesi: 0-11
    const dd = String(now.getDate()).padStart(2, '0');
    const hh = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    
    const valorInicial = `${yyyy}-${mm}-${dd}T${hh}:${min}`;
    
    input.value = valorInicial;
    
    // Establecer listeners para actualizar el resumen inmediatamente
    input.addEventListener('change', actualizarResumen);
    actualizarResumen();
}

// --- 2. Función de Actualización (Mucho más simple) ---
function actualizarResumen() {
    const valor = document.getElementById("fechaHora").value; // Formato: YYYY-MM-DDTHH:MM
    
    if (valor) {
        // Opcional: convertir a un formato legible para el usuario
        const partes = valor.split('T'); // ["YYYY-MM-DD", "HH:MM"]
        const fecha = partes[0];
        const hora = partes[1];
        
        // 🚨 Formato de envío (Lo enviaremos como YYYY-MM-DD HH:MM)
        const texto = `Seleccionado: ${fecha.trim()} ${hora.trim()}`;
        document.getElementById("seleccion").textContent = texto;
        Telegram.WebApp.MainButton.enable();
    } else {
        document.getElementById("seleccion").textContent = "Error: Por favor, selecciona la fecha y hora.";
        Telegram.WebApp.MainButton.disable();
    }
}

// --- 3. Inicialización Principal (manteniendo la llamada al MainButton) ---
function inicializar() {
    inicializarValoresActuales(); 
    // ... (Mantener la configuración de listeners de scroll si tienes otros elementos)
    
    inicializarMainButton(); // CLAVE: Configurar el botón de Telegram
}
// document.addEventListener("DOMContentLoaded", inicializar);


// --- 4. LÓGICA DE CONFIRMACIÓN FINAL (LA MISMA QUE SOLUCIONÓ TU PROBLEMA) ---
function inicializarMainButton() {
    if (window.Telegram && Telegram.WebApp) {
        
        Telegram.WebApp.ready();
        Telegram.WebApp.MainButton.setText("✅ Confirmar Cita").disable(); // Inicia deshabilitado
        
        Telegram.WebApp.MainButton.onClick(() => {
            
            Telegram.WebApp.MainButton.showProgress(); 
            
            const valorInput = document.getElementById("fechaHora").value; // YYYY-MM-DDTHH:MM

            if (!valorInput) {
                Telegram.WebApp.showAlert("⚠️ Por favor, selecciona la fecha y hora.");
                Telegram.WebApp.MainButton.hideProgress();
                return;
            }

            // El formato es simple: lo separamos en fecha y hora
            const [fecha, hora] = valorInput.split('T'); 
            
            // 1. Enviar los datos. (¡Usamos el nuevo formato!)
            // Revisa que tu bot en Python sepa parsear 'YYYY-MM-DD' y 'HH:MM'
            const payload = { fecha, hora }; 
            Telegram.WebApp.sendData(JSON.stringify(payload));
            
            document.getElementById("seleccion").textContent = "✅ Fecha confirmada. Enviando y cerrando...";

            Telegram.WebApp.MainButton.hideProgress();
            
            // 2. Retraso crucial para la App nativa de Telegram
            setTimeout(() => {
                Telegram.WebApp.close();
            }, 1500); 

        });
    }
}
