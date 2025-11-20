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
// --- 4. LÓGICA DE CONFIRMACIÓN FINAL ---
function inicializarMainButton() {
    if (window.Telegram && Telegram.WebApp) {
        
        Telegram.WebApp.ready();
        
        // 🔑 CLAVE: ESTA LÍNEA MUESTRA EL BOTÓN FISICAMENTE
        Telegram.WebApp.MainButton.setText("✅ Confirmar Cita").show(); 
        
        // El resto del código de onClick() es para manejar la acción
        Telegram.WebApp.MainButton.onClick(() => {
            // ... (Lógica de showProgress, getElementById("fechaHora").value, sendData, y setTimeout(close)) ...
        });
    }
}


// --- 5. INICIALIZACIÓN PRINCIPAL ---

// --- 3. INICIALIZACIÓN PRINCIPAL ---

function inicializar() {
    // Es crucial verificar si Telegram WebApp está disponible
    if (window.Telegram && Telegram.WebApp) {
        
        // 1. Inicializa el campo nativo y sus listeners
        inicializarValoresActuales(); 
        
        // 2. 🔑 CLAVE: Define y muestra el MainButton de Telegram
        inicializarMainButton(); 
        
        // 3. Establece el estado inicial del botón (visible, pero deshabilitado hasta seleccionar algo)
        actualizarResumen(); 
    } else {
        // Mensaje de fallback si no está en Telegram
        console.error("Telegram WebApp API no disponible. Ejecutar en el bot.");
        document.getElementById("seleccion").textContent = "Error: Carga esta página dentro de Telegram.";
    }
}

// Inicia todo al cargar el contenido de la página
document.addEventListener("DOMContentLoaded", inicializar);

