const seleccion = {
  dia: "25",
  mes: "Oct",
  anio: "2025",
  hora: "17",
  minuto: "34"
};

const meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

function generarLista(id, valores) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  valores.forEach(valor => {
    const li = document.createElement("li");
    li.textContent = valor;
    if (valor === seleccion[id]) li.classList.add("selected");
    ul.appendChild(li);
  });
}

function seleccionarValor(campo, valor) {
  seleccion[campo] = valor;
  actualizarResumen();
  document.querySelectorAll(`#${campo} li`).forEach(li => {
    li.classList.toggle("selected", li.textContent === valor);
  });
}

function actualizarResumen() {
  const texto = `${seleccion.dia} ${seleccion.mes} ${seleccion.anio} - ${seleccion.hora}:${seleccion.minuto}`;
  document.getElementById("seleccion").textContent = texto;
}

function confirmar() {
  const texto = document.getElementById("seleccion").textContent;
  Telegram.WebApp.sendData(texto);
}

function restablecer() {
  seleccion.dia = "25";
  seleccion.mes = "Oct";
  seleccion.anio = "2025";
  seleccion.hora = "17";
  seleccion.minuto = "34";
  inicializar();
}

function inicializar() {
  // Generar listas
  generarLista("dia", Array.from({ length: 31 }, (_, i) => String(i + 1).padStart(2, "0")));
  generarLista("mes", ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]);
  generarLista("anio", Array.from({ length: 11 }, (_, i) => String(2020 + i)));
  generarLista("hora", Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0")));
  generarLista("minuto", Array.from({ length: 60 }, (_, i) => String(i).padStart(2, "0")));

  // Actualizar resumen inicial
  actualizarResumen();

  // Detectar y actualizar automáticamente el valor centrado
  ["dia", "mes", "anio", "hora", "minuto"].forEach(id => {
    const ul = document.getElementById(id);

    // Detectar el valor centrado al cargar
    setTimeout(() => detectarElementoCentral(id), 200);

    // Detectar el valor centrado al hacer scroll
    ul.addEventListener("scroll", () => {
      clearTimeout(ul._scrollTimeout);
      ul._scrollTimeout = setTimeout(() => detectarElementoCentral(id), 100);
    });
  });
}

  


document.addEventListener("DOMContentLoaded", inicializar);

function detectarElementoCentral(id) {
  const ul = document.getElementById(id);
  const items = Array.from(ul.children);
  const ulRect = ul.getBoundingClientRect();

  const centro = ulRect.top + ulRect.height / 2;
  let seleccionado = null;

  items.forEach(li => {
    const liRect = li.getBoundingClientRect();
    const liCentro = liRect.top + liRect.height / 2;

    if (Math.abs(liCentro - centro) < liRect.height / 2) {
      seleccionado = li.textContent;
    }
  });

  if (seleccionado) {
    seleccion[id] = seleccionado;
    actualizarResumen();

    items.forEach(li => {
      li.classList.toggle("selected", li.textContent === seleccionado);
    });
  }
}
