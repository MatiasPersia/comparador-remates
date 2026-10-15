import csv
import difflib
import json
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
import os

import requests

# ================= CONFIGURACIÓN =================
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
HORAS = 48
MAX_PARTIDOS = 80
MODO = "buscador"
CACHE_SEG = 300
DIF_MIN = 5.0
CUOTA_MAX = 20.0
CSV_SALIDA = "resultados_remates.csv"
CAPTURAR = True
CAPTURAR_N = 3
DEBUG = True
# =================================================

BETANO = "https://blackfalcondata--betano-odds-api.apify.actor"
B365 = "https://zen-studio--bet365-real-time-odds.apify.actor"
TZ = timezone(timedelta(hours=-3))

_EXC = ("women", "(w)", "femen", "frauen", "u23", "u21", "u20", "u19", "u18", "u17", "youth", "juvenil",
        "reserve", "esoccer", "esports", "battle", "efootball", "cyber")

LIGAS = {
    "Brasil - Serie A": (([("brazil", "brasil"), ("serie a", "brasileir")], ("serie b", "serie c", "femen", "women", "(w)", "u20", "u23", "carioca", "paulista", "estadual")), "brazil-serie-a"),
    "Inglaterra - Premier League": (([("england", "inglaterra"), ("premier league",)], ("women", "femen", "(w)", "2", "u21", "u18")), "england-premier-league"),
    "Italia - Serie A": (([("ital",), ("serie a",)], ("serie b", "serie c", "women", "femen")), "italy-serie-a"),
    "Alemania - Bundesliga": (([("german", "alemania"), ("bundesliga",)], ("2.", "ii", "segunda", "3.", "women", "(w)", "frauen", "femen", "junioren", "u19", "u17")), "germany-bundesliga-i"),
    "España - LaLiga": (([("spain", "espana"), ("laliga", "la liga", "primera divisi")], ("laliga 2", "la liga 2", "segunda", "hypermotion", "rfef", "federacion", "women", "(w)", "femen")), "spain-la-liga"),
    "Champions League": (([("champions league",)], ("women", "(w)", "femen", "afc", "caf", "concacaf", "youth", "juvenil", "esoccer", "esports", "battle", "efootball", "cyber")), "uefa-champions-league"),
    "Europa League": (([("europa league",)], ("women", "(w)", "femen", "conference", "caf", "afc", "esoccer", "esports", "battle", "efootball", "cyber")), "uefa-europa-league"),
}

ALIAS = {
    "clube atletico mg": "atletico mineiro", "atletico mg": "atletico mineiro",
    "cologne": "koln", "monchengladbach": "gladbach", "m gladbach": "gladbach",
    "mgladbach": "gladbach", "nottm": "nottingham", "man city": "manchester city",
    "man utd": "manchester united", "man united": "manchester united",
}
BASURA = ("u17", "u18", "u19", "u20", "u21", "u23", "(esports)", "esoccer", "(w)", " ii ", "reserves")
RUIDO = {"fc", "cf", "ac", "as", "sc", "cd", "ca", "club", "clube", "de", "the", "afc", "fk", "sk"}
EXCLUIR_MERCADO = ("headed", "outside", "box", "team", "match", "half", "1st", "2nd", "first", "last", "goalkeeper", "saves", "blocked", "offside")
ETIQUETA = {"SOT": "Remates al arco", "TOT": "Remates totales"}

def get(base, path, **params):
    params["token"] = APIFY_TOKEN
    try:
        resp = requests.get(base + path, params=params, timeout=120)
        data = resp.json()
    except Exception as e:
        print(f"  Error de red/JSON en {path}: {e}")
        return None
    if resp.status_code >= 400 or (isinstance(data, dict) and (data.get("ok") is False or "error" in data)):
        print(f"  ERROR de la API en {path} (HTTP {resp.status_code}): {str(data)[:300]}")
    return data

def sin_tildes(s):
    s = unicodedata.normalize("NFD", str(s))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()

def dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from dicts(v)

def fecha(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def equipo_norm(nombre):
    t = re.sub(r"[^a-z0-9 ]", " ", sin_tildes(nombre))
    t = " ".join(t.split())
    for a, b in ALIAS.items():
        t = t.replace(a, b)
    return " ".join(w for w in t.split() if w not in RUIDO)

def sim(a, b):
    a, b = equipo_norm(a), equipo_norm(b)
    if not a or not b:
        return 0.0
    r = difflib.SequenceMatcher(None, a, b).ratio()
    return max(r, 0.85) if (a in b or b in a) else r

PLANTILLA_HTML = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Comparador de remates: Betano y Bet365</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Sora:wght@400;600;700&display=swap">
<style>
:root{
  --bg:#0e0c22; --surface:#17143b; --line:#2c2862; --text:#f3f1ff; --muted:#9b97c4;
  --accent:#c6f24e; --accent-ink:#13230a; --focus:#9a96ff; --danger:#ff8585;
  --sans:"Sora",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color-scheme:dark; box-sizing:border-box;
}
:root[data-theme="light"]{
  --bg:#f6f5fc; --surface:#ffffff; --line:#d9d5ee; --text:#1b1840; --muted:#625e8a;
  --accent:#4d8a00; --accent-ink:#ffffff; --focus:#4b46d6; --danger:#b3261e; color-scheme:light;
}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:15px;line-height:1.45}
.wrap{max-width:760px;margin:0 auto;padding:22px 16px 24px}
.cab{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
h1{font-size:26px;margin:0;font-weight:700}
.sub{margin:6px 0 0;color:var(--muted)}
.tema{width:38px;height:38px;border-radius:50%;border:1px solid var(--line);background:transparent;cursor:pointer;color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;gap:4px 18px;margin:14px 0 0;font-family:var(--mono);font-size:12px;color:var(--muted)}
.filtros{margin:22px 0 0;display:grid;gap:12px;grid-template-columns:1fr 1fr}
.filtros .ancho{grid-column:1/-1}
.campo{display:grid;gap:5px;font-size:12px;color:var(--muted)}
.campo select,.campo input{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--text)}
.lista{list-style:none;margin:0;padding:0;display:grid;gap:12px;margin-top:18px}
.tarjeta{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px}
.tarjeta-header{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:8px}
.tarjeta-titulo{font-weight:600;font-size:16px;color:var(--text);margin-bottom:12px}
.cuotas-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:center}
.cuota-box{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:10px;text-align:center}
.cuota-box.mejor{border-color:var(--accent)}
.valor{font-size:20px;font-weight:700;font-family:var(--mono)}
.valor.mejor{color:var(--accent)}
</style>
</head>
<body>
<div class="wrap">
  <header class="cab">
    <div><h1>Remates por jugador</h1><p class="sub">Betano vs Bet365</p></div>
    <button class="tema" id="tema">◐</button>
  </header>
  <p class="meta" id="meta"></p>
  
  <div class="filtros">
    <div class="campo ancho">
      <label>Buscar jugador o partido</label>
      <input type="text" id="buscador" placeholder="Ej: Vinicius, Real Madrid...">
    </div>
  </div>

  <ul class="lista" id="lista"></ul>
</div>

<script>
var DATA = /*__DATA__*/[];
var META = /*__META__*/{};

function render() {
  const lista = document.getElementById('lista');
  const filtro = document.getElementById('buscador').value.toLowerCase();
  lista.innerHTML = '';

  const filtrados = DATA.filter(item => 
    item.j.toLowerCase().includes(filtro) || item.p.toLowerCase().includes(filtro) || item.l.toLowerCase().includes(filtro)
  );

  if(filtrados.length === 0) {
    lista.innerHTML = '<p style="color:var(--muted);text-align:center;padding:20px;">No se encontraron resultados con ese criterio.</p>';
    return;
  }

  filtrados.forEach(item => {
    const li = document.createElement('li');
    li.className = 'tarjeta';
    li.innerHTML = `
      <div class="tarjeta-header">
        <span>${item.l} • ${item.h}</span>
        <span><b>${item.t}</b> (Line: ${item.u})</span>
      </div>
      <div class="tarjeta-titulo">${item.p}</div>
      <div style="font-size:14px;margin-bottom:10px;color:var(--muted)">Jugador: <b>${item.j}</b></div>
      <div class="cuotas-grid">
        <div class="cuota-box ${item.b > item.c ? 'mejor' : ''}">
          <div style="font-size:12px">Betano</div>
          <div class="valor ${item.b > item.c ? 'mejor' : ''}">${item.b.toFixed(2)}</div>
        </div>
        <div class="cuota-box ${item.c > item.b ? 'mejor' : ''}">
          <div style="font-size:12px">Bet365</div>
          <div class="valor ${item.c > item.b ? 'mejor' : ''}">${item.c.toFixed(2)}</div>
        </div>
      </div>
    `;
    lista.appendChild(li);
  });

  document.getElementById('meta').innerText = `Actualizado: ${META.generado || 'Reciente'} | Total partidos: ${DATA.length}`;
}

document.getElementById('buscador').addEventListener('input', render);
document.getElementById('tema').addEventListener('click', () => {
  const root = document.documentElement;
  root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
});

render();
</script>
</body>
</html>
'''

if __name__ == "__main__":
    print("Ejecutando comparador para generar index.html...")
    
    filas_ejemplo = [
        {"p": "Real Madrid vs Barcelona", "l": "España - LaLiga", "h": "Hoy 16:00", "j": "Kylian Mbappé", "t": "TOT", "u": 1.5, "b": 1.85, "c": 1.72, "d": 7.5},
        {"p": "Arsenal vs Chelsea", "l": "Inglaterra - Premier League", "h": "Mañana 14:30", "j": "Cole Palmer", "t": "SOT", "u": 0.5, "b": 2.10, "c": 1.95, "d": 7.6}
    ]
    meta_ejemplo = {"generado": datetime.now(TZ).strftime("%d/%m %H:%M"), "difMin": 5}
    
    html_final = PLANTILLA_HTML.replace("/*__DATA__*/[]", json.dumps(filas_ejemplo, ensure_ascii=False)) \
                               .replace("/*__META__*/{}", json.dumps(meta_ejemplo, ensure_ascii=False))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_final)
    print("¡index.html generado con éxito!")
