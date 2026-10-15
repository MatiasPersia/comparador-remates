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

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
HORAS = 48
TZ = ZoneInfo("America/Argentina/Mendoza")

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
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:15px;line-height:1.45}
.wrap{max-width:760px;margin:0 auto;padding:22px 16px 24px}
</style>
</head>
<body>
<div class="wrap"><h1>Remates por jugador</h1></div>
<script>
var DATA = /*__DATA__*/[];
var META = /*__META__*/{};
</script>
</body>
</html>
'''

if __name__ == "__main__":
    print("Generando index.html...")
    filas_ejemplo = [{"p": "Partido Ejemplo", "j": "Jugador 1", "t": "TOT", "u": 3, "b": 2.5, "c": 2.0, "d": 25.0}]
    meta_ejemplo = {"generado": datetime.now(TZ).strftime("%d/%m %H:%M"), "difMin": 5}
    
    html_final = PLANTILLA_HTML.replace("/*__DATA__*/[]", json.dumps(filas_ejemplo, ensure_ascii=False)) \
                               .replace("/*__META__*/{}", json.dumps(meta_ejemplo, ensure_ascii=False))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_final)
    print("¡Listo!")