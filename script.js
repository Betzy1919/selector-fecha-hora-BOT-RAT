// script.js (VERSIÓN FINAL CON SELECTOR DE HORA EN 12H, CENTRADO Y RANGO DE AÑOS)

const seleccion = {
  // Estos campos se llenarán con la hora actual
  dia: "",
  mes: "",
  anio: "",
  hora: "", // Se almacena en 24h internamente (00-23)
  minuto: "",
  ampm: "" // AM o PM
};

const meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];


// --- 1. Inicializar con Fecha/Hora Actual (24H Interna) ---
function inicializarValoresActuales() {
  // La hora actual es: 26 Oct 2025 15:55:37 (ejemplo del contexto)
  const now = new Date();
  
  // Obtener la hora actual en formato 24h (0-23)
  const currentHour24 = now.getHours(); 
  
  seleccion.dia = String(now.getDate()).padStart(2, "0");
  seleccion.mes = meses[now.getMonth()];
  seleccion.anio = String(now.getFullYear());
  seleccion.minuto = String(now.getMinutes()).padStart(2, "0");
  
  // Almacenar en 24h y establecer AM/PM inicial
  seleccion.ampm = currentHour24 >= 12 ? 'PM' : 'AM';
  seleccion.hora = String(currentHour24).padStart(2, "0"); 
}


// --- 2. FUNCIONES DE GENERACIÓN CÍCLICA (360°) ---

/** Genera ciclos para Día y Minuto (00-59 o 01-31). */
function generarValoresCiclicos(max, startFromOne) {
const list = [];
const start = startFromOne ? 1 : 0;
for (let j = 0; j < 5; j++) {
  for (let i = 0; i < max; i++) {
    list.push(String(start + i).padStart(2, "0"));
  }
}
return list;
}

/** CLAVE: Genera ciclos para Hora en formato 12H (01-12). */
function generarValoresCiclicosHora12() {
  const list = [];
  const horas12 = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, "0")); // Genera 01, 02... 12
  for (let j = 0; j < 5; j++) {
      list.push(...horas12);
  }
  return list;
}

/** Genera ciclos para Mes y Año. */
function generarValoresCiclicosMes() {
  const list = [];
  for (let j = 0; j < 5; j++) {
      list.push(...meses); 
  }
  return list;
}

/** Genera ciclos para Año (2025 hasta 2035). */
function generarValoresCiclicosAnio() {
  const list = [];
  const startYear = 2025; 
  const endYear = 2035; 
  const anios = Array.from({ length: endYear - startYear + 1 }, (_, i) => String(startYear + i)); 
  
  for (let j = 0; j < 5; j++) {
      list.push(...anios);
  }
  return list;
}


// --- 3. MANEJO DE LISTAS Y SELECCIÓN ---

function generarLista(id, valores) {
const ul = document.getElementById(id);
ul.innerHTML = "";
valores.forEach(valor => {
  const li = document.createElement("li");
  li.textContent = valor;
  li.onclick = () => {
      seleccionarValor(id, valor);
      li.parentElement.scrollTop = li.offsetTop - (li.parentElement.offsetHeight / 2) + (li.offsetHeight / 2);
  };
  ul.appendChild(li);
});
}

function seleccionarValor(campo, valor) {
if (campo === 'hora') {
    // Si el usuario selecciona la hora en el selector de 12h, debemos recalcular la hora 24h interna.
    let hora12 = parseInt(valor, 10);
    let hora24;
    
    if (seleccion.ampm === 'PM') {
        hora24 = hora12 === 12 ? 12 : hora12 + 12; // 12 PM es 12h, 1-11 PM es 13-23h
    } else { // AM
        hora24 = hora12 === 12 ? 0 : hora12; // 12 AM es 00h (medianoche), 1-11 AM es 1-11h
    }
    seleccion.hora = String(hora24).padStart(2, "0");
    
} else {
    seleccion[campo] = valor;
}

actualizarResumen();
document.querySelectorAll(`#${campo} li`).forEach(li => {
  li.classList.toggle("selected", li.textContent.trim() === valor);
});
}

/** Conversión de 24h (almacenada) a 12h (visualizada en el resumen) */
function actualizarResumen() {
let hora24 = parseInt(seleccion.hora, 10);

if (isNaN(hora24) || seleccion.minuto === "" || seleccion.ampm === "") {
    document.getElementById("seleccion").textContent = "Error de formato de hora.";
    return;
}

// La hora12 ya está en la variable "hora" del selector cuando el usuario interactúa
// Pero para el resumen, la hora12 siempre es el valor de la hora actual en el selector.
let hora12 = hora24 % 12;
hora12 = hora12 === 0 ? 12 : hora12; 

const horaStr = String(hora12).padStart(2, "0");
const ampmStr = seleccion.ampm;

const texto = `${seleccion.dia.trim()} ${seleccion.mes.trim()} ${seleccion.anio.trim()} - ${horaStr}:${seleccion.minuto.trim()} ${ampmStr.trim()}`;
document.getElementById("seleccion").textContent = texto;
}

/** Manejo de la selección del botón AM/PM. */
function seleccionarAMPM(mode) {
  // Si el modo cambia, debemos recalcular la hora 24h interna
  if (seleccion.ampm !== mode) {
      seleccion.ampm = mode;
      
      let currentHour24 = parseInt(seleccion.hora, 10);
      
      // Convertir la hora 24h interna para que coincida con el nuevo AM/PM
      if (mode === 'PM' && currentHour24 < 12) {
          currentHour24 = currentHour24 + 12; // 10 AM (10h) -> 10 PM (22h)
      } else if (mode === 'AM' && currentHour24 >= 12) {
          currentHour24 = currentHour24 - 12; // 10 PM (22h) -> 10 AM (10h)
      }
      
      seleccion.hora = String(currentHour24).padStart(2, "0");
      
      // CLAVE: El centrado de la HORA debe actualizarse para mostrar el mismo valor 12h 
      // pero con la nueva selección AM/PM.
      centrarSeleccionInicialCampo('hora'); 
  }
  
  // Marcar el botón clickeado en azul
  document.getElementById('btn-am').classList.toggle('selected', mode === 'AM');
  document.getElementById('btn-pm').classList.toggle('selected', mode === 'PM');
  
  actualizarResumen();
}

window.seleccionarAMPM = seleccionarAMPM; 


// --- 4. LÓGICA DE SCROLL Y CENTRADO (itemHeight = 40px) ---

/** Centra el valor de la hora/fecha actual en el recuadro azul. */
function centrarSeleccionInicialCampo(campo) {
  const itemHeight = 40; // CLAVE: Coincide con el CSS
  const ul = document.getElementById(campo);
  let valorSeleccionado = seleccion[campo];
  
  // CLAVE: Si es el campo 'hora', necesitamos el valor en 12h para centrar.
  if (campo === 'hora') {
      let hora24 = parseInt(valorSeleccionado, 10);
      let hora12 = hora24 % 12;
      hora12 = hora12 === 0 ? 12 : hora12; 
      valorSeleccionado = String(hora12).padStart(2, "0");
  }

  const lis = Array.from(ul.children);
  let indexToCenter = -1;
  let count = 0;

  for (let i = 0; i < lis.length; i++) {
      if (lis[i].textContent.trim() === valorSeleccionado) {
          // Buscamos el tercer ciclo para centrar la navegación 360°
          count++;
          if (count === 3) { 
              indexToCenter = i;
              break;
          }
      }
  }
  
  // Para Mes/Año (no cíclicos completos)
  if (indexToCenter === -1) {
      const firstMatchIndex = lis.findIndex(li => li.textContent.trim() === valorSeleccionado);
      if (firstMatchIndex !== -1) {
           indexToCenter = firstMatchIndex;
      }
  }

  if (indexToCenter !== -1) {
      // Offset 1: posiciona el elemento en la segunda línea (el centro del recuadro)
      const centerIndexOffset = 1; 
      const scrollTopValue = (indexToCenter - centerIndexOffset) * itemHeight;
      ul.scrollTop = scrollTopValue;
      
      seleccionarValor(campo, valorSeleccionado);
  }
}

/** Reinicia el scroll cuando llega a los límites para simular el giro 360°. */
function manejarScrollCiclico(id, ul) {
const itemHeight = 40; 
const itemCount = ul.children.length; 
const threshold = 5 * itemHeight; 
const centerPosition = Math.floor(itemCount / 2.5) * itemHeight;

if (ul.scrollTop < threshold) {
  ul.scrollTop = centerPosition;
} else if (ul.scrollTop > (itemCount * itemHeight) - threshold) {
  ul.scrollTop = centerPosition;
}
}

/** Detecta qué elemento está visible en el centro del recuadro al hacer scroll. */
function detectarElementoCentral(id) {
const ul = document.getElementById(id);
const items = Array.from(ul.children);
const itemHeight = 40; 

const centralIndex = Math.round(ul.scrollTop / itemHeight) + 1; 

if (items[centralIndex]) {
  seleccionarValor(id, items[centralIndex].textContent.trim());
}
}


// --- 5. INICIALIZACIÓN GENERAL ---

// --- 5. INICIALIZACIÓN GENERAL (MODIFICAR AQUÍ) ---

function inicializar() {

  // Paso 1: Establecer la fecha/hora actual
  inicializarValoresActuales(); 

  // Paso 2: Generación de Listas Cíclicas (360° en todos los campos)
  generarLista("dia", generarValoresCiclicos(31, true)); 
  generarLista("mes", generarValoresCiclicosMes()); 
  generarLista("anio", generarValoresCiclicosAnio()); 
  generarLista("hora", generarValoresCiclicosHora12()); 
  generarLista("minuto", generarValoresCiclicos(60, false));

  // Paso 3: Centrar la selección inicial (fecha/hora actual)
  ['dia', 'mes', 'anio', 'hora', 'minuto'].forEach(centrarSeleccionInicialCampo);
  seleccionarAMPM(seleccion.ampm); 

  actualizarResumen();

  // Paso 4: Añadir listeners de scroll (mantener tu lógica de scroll)
  ['dia', 'mes', 'anio', 'hora', 'minuto'].forEach(id => {
    const ul = document.getElementById(id);
    ul.addEventListener("scroll", () => {
      clearTimeout(ul._scrollTimeout);
      ul._scrollTimeout = setTimeout(() => {
        detectarElementoCentral(id);
        manejarScrollCiclico(id, ul); 
      }, 100);
    });
  });
  
  // 🔑 CLAVE: Inicializar el botón de Telegram al final
  inicializarMainButton(); 
}

document.addEventListener("DOMContentLoaded", inicializar);-

function inicializarMainButton() {
  if (window.Telegram && Telegram.WebApp) {
      // 1. Indicar que el WebApp está listo y mostrar el botón principal
      Telegram.WebApp.ready();
      Telegram.WebApp.MainButton.setText("✅ Confirmar Cita").show();
      
      // 2. Definir la acción al hacer clic en el MainButton
      Telegram.WebApp.MainButton.onClick(() => {
          // El MainButton es más confiable en clientes nativos.
          // Toda la lógica de extracción, validación, envío y cierre va aquí,
          // SIN NECESIDAD DE setTimeout.

          const texto = document.getElementById("seleccion").textContent;
          
          // Separar fecha y hora
          const partes = texto.split(" - ");
          const fechaTexto = partes[0]?.trim(); // Ej: "19 Nov 2025"
          const hora = partes[1]?.trim();       // Ej: "02:25 AM"
      
          // Validar que ambas partes existan
          if (!fechaTexto || !hora || fechaTexto.includes("Error")) {
               Telegram.WebApp.showAlert("⚠️ Por favor, selecciona la fecha y hora correctamente.");
               return;
          }
      
          // Convertir "19 Nov 2025" → "19/11/2025"
          const [dia, mesTexto, anio] = fechaTexto.split(" ");
          const mesesMap = {
              Ene: "01", Feb: "02", Mar: "03", Abr: "04", May: "05", Jun: "06",
              Jul: "07", Ago: "08", Sep: "09", Oct: "10", Nov: "11", Dic: "12"
          };
          const mes = mesesMap[mesTexto] || "00";
          const fecha = `${dia}/${mes}/${anio}`; // Ej: "19/11/2025"
      
          // Validación final
          if (mes === "00") {
              Telegram.WebApp.showAlert("⚠️ Mes inválido. Verifica tu selección.");
              return;
          }
      
          // 3. Enviar al bot como JSON válido
          const payload = { fecha, hora };
          console.log("✅ Enviando a Telegram (MainButton):", payload);
          
          Telegram.WebApp.sendData(JSON.stringify(payload));
          
          document.getElementById("seleccion").textContent = "✅ Fecha confirmada";
          
          // 4. Cerrar la WebApp (inmediato, sin setTimeout)
          Telegram.WebApp.close();
      });
  }
}
// ------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", inicializar);
