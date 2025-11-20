// Asegúrate de que este script esté enlazado en tu index.html
// <script src="script.js"></script>

// --- 1. Inicializar con Fecha/Hora Actual y Listeners ---
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
    
    // 1. Establecer el valor inicial
    input.value = valorInicial;
    
    // 2. Agregar el listener 'change' (detecta la selección del usuario)
    input.addEventListener('change', actualizarResumen);
}

// --- 2. Función de Actualización (Habilita/Deshabilita el MainButton) ---
function actualizarResumen() {
    if (!window.Telegram || !Telegram.WebApp) return;

    const input = document.getElementById("fechaHora");
    const valor = input.value; // Formato: YYYY-MM-DDTHH:MM
    
    if (valor) {
        // Formato para mostrar al usuario
        const [fecha, hora] = valor.split('T'); 
        
        const texto = `✅ Seleccionado: ${fecha.trim()} a las ${hora.trim()}`;
        document.getElementById("seleccion").textContent = texto;
        
        // HABILITAR el MainButton si hay un valor válido
        Telegram.WebApp.MainButton.enable();
    } else {
        document.getElementById("seleccion").textContent = "Error: Por favor, selecciona la fecha y hora.";
        // DESHABILITAR el MainButton si no hay valor
        Telegram.WebApp.MainButton.disable();
    }
}


// --- 3. LÓGICA DE CONFIRMACIÓN FINAL (Envío de Datos y Cierre Reforzado) ---
function inicializarMainButton() {
    if (window.Telegram && Telegram.WebApp) {
        
        Telegram.WebApp.ready();
        
        // 🔑 CLAVE 1: Mostrar el botón inmediatamente para garantizar su visibilidad
        Telegram.WebApp.MainButton.setText("✅ Confirmar Cita").show(); 
        
        // La habilitación/deshabilitación inicial se hace después por 'actualizarResumen()'

        Telegram.WebApp.MainButton.onClick(() => {
            
            Telegram.WebApp.MainButton.showProgress(); // Muestra el spinner
            
            const valorInput = document.getElementById("fechaHora").value; 
            
            if (!valorInput) {
                Telegram.WebApp.showAlert("⚠️ Por favor, selecciona la fecha y hora.");
                Telegram.WebApp.MainButton.hideProgress();
                return;
            }

            // El payload va con fecha y hora separadas, en formato ISO (YYYY-MM-DD y HH:MM)
            const [fecha, hora] = valorInput.split('T'); 
            const payload = { fecha, hora }; 
            
            // 1. Enviar los datos.
            Telegram.WebApp.sendData(JSON.stringify(payload));
            
            document.getElementById("seleccion").textContent = "✅ Enviando datos... Cerrando WebApp...";

            Telegram.WebApp.MainButton.hideProgress();
            
            // 2. 🔑 CLAVE 2: Retraso de 1.5 segundos para la App nativa de Telegram
            setTimeout(() => {
                Telegram.WebApp.close();
            }, 1500); 

        });
    }
}


// --- 5. INICIALIZACIÓN PRINCIPAL ---

function inicializar() {
    if (window.Telegram && Telegram.WebApp) {
        
        // 1. Inicializa el campo nativo con la fecha actual y configura el listener 'change'
        inicializarValoresActuales(); 
        
        // 2. Llama a la función que define el MainButton y el evento de clic
        inicializarMainButton(); 
        
        // 3. Llama a actualizarResumen para establecer el texto de inicio 
        // y el estado inicial del MainButton (disabled/enabled)
        actualizarResumen(); 
    }
}

// Inicia todo al cargar el contenido de la página
document.addEventListener("DOMContentLoaded", inicializar);
