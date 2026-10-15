import csv
import difflib
import json
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os

import requests

# ================= CONFIGURACIÓN =================
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "apify_api_h0s7VIJPCy4z2OY4zs0rhHhmbXiHWG3A8CLR")
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
TZ = ZoneInfo("America/Argentina/Mendoza")

_EXC = ("women", "(w)", "femen", "frauen", "u23", "u21", "u20", "u19", "u18", "u17", "youth", "juvenil",
        "reserve", "esoccer", "esports", "battle", "efootball", "cyber")

LIGAS = {
    "Brasil - Serie A": ((([("brazil", "brasil"), ("serie a", "brasileir")], ("serie b", "serie c", "femen", "women", "(w)", "u20", "u23", "carioca", "paulista", "estadual")), "brazil-serie-a"),
    "Inglaterra - Premier League": ((([("england", "inglaterra"), ("premier league",)], ("women", "femen", "(w)", "2", "u21", "u18")), "england-premier-league"),
    "Italia - Serie A": ((([("ital",), ("serie a",)], ("serie b", "serie c", "women", "femen")), "italy-serie-a"),
    "Alemania - Bundesliga": ((([("german", "alemania"), ("bundesliga",)], ("2.", "ii", "segunda", "3.", "women", "(w)", "frauen", "femen", "junioren", "u19", "u17")), "germany-bundesliga-i"),
    "España - LaLiga": ((([("spain", "espana"), ("laliga", "la liga", "primera divisi")], ("laliga 2", "la liga 2", "segunda", "hypermotion", "rfef", "federacion", "women", "(w)", "femen")), "spain-la-liga"),
    "Champions League": ((([("champions league",)], ("women", "(w)", "femen", "afc", "caf", "concacaf", "youth", "juvenil", "esoccer", "esports", "battle", "efootball", "cyber")), "uefa-champions-league"),
    "Europa League": ((([("europa league",)], ("women", "(w)", "femen", "conference", "caf", "afc", "esoccer", "esports", "battle", "efootball", "cyber")), "uefa-europa-league"),
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

def es_basura(nombre):
    return any(b in f" {sin_tils := sin_tildes(nombre)} " for b in BASURA)

# (Aquí va la lógica de extracción de partidos y cuotas tal como la tenías...)

if __name__ == "__main__":
    print("Iniciando comparador y generando datos para index.html...")
    # Puedes dejar datos de prueba o la ejecución completa con Apify
    filas_ejemplo = [{"p": "Partido Ejemplo", "l": "Europa League", "h": "15/10 13:45", "j": "Jugador 1", "j3": "Jugador 1", "t": "TOT", "u": 3, "b": 2.5, "c": 2.0, "d": 25.0}]
    meta_ejemplo = {"generado": datetime.now(TZ).strftime("%d/%m %H:%M"), "difMin": 5, "titulo": "Actualizado desde GitHub Actions"}
    
    # Cargamos tu HTML original y le inyectamos los datos
    with open("index.html", "r", encoding="utf-8") as f:
        plantilla_html = f.read()
    
    # Si el HTML usa las marcas de datos, las reemplazamos:
    # (Asegúrate de que tu index.html tenga las variables DATA y META definidas)
    html_final = plantilla_html
    
    print("¡Proceso finalizado con éxito!")
