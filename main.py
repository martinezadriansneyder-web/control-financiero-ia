import csv
import datetime
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# ----------------------------
# Config / Env
# ----------------------------
ARCHIVO = "gastos.csv"
CATEGORIAS_VALIDAS = {"Comida", "Transporte",
                      "Hogar", "Entretenimiento", "Salud", "Otros"}

env_path = Path(__file__).with_name(".env")
load_dotenv(env_path, override=True)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("❌ No se encontró OPENAI_API_KEY en .env")
    print(f"➡️ Revisa este archivo: {env_path}")
    print('➡️ Debe verse así: OPENAI_API_KEY=sk-proj-.... (tu key real completa)')
    raise SystemExit(1)

client = OpenAI(api_key=API_KEY)


# ----------------------------
# Helpers
# ----------------------------
def crear_archivo():
    """Crea el CSV si no existe."""
    if not os.path.exists(ARCHIVO):
        with open(ARCHIVO, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Fecha", "Monto", "Categoria", "Descripcion"])


def _extraer_json(texto: str) -> str:
    """
    Si el modelo devuelve texto extra (ej: 'Aquí está el JSON: {...}'),
    intenta extraer el primer objeto JSON {...}.
    """
    texto = texto.strip()

    # Intento directo
    if texto.startswith("{") and texto.endswith("}"):
        return texto

    # Busca el primer bloque {...} (simple pero efectivo)
    match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
    if match:
        return match.group(0).strip()

    # Si no encontró nada, devuelve tal cual para que el parser falle y lo veamos
    return texto


def _normalizar_categoria(cat: str) -> str:
    if not isinstance(cat, str):
        return "Otros"
    cat = cat.strip()
    # Normalizaciones comunes
    mapping = {
        "Comida": "Comida",
        "Alimentacion": "Comida",
        "Alimentación": "Comida",
        "Transporte": "Transporte",
        "Hogar": "Hogar",
        "Entretenimiento": "Entretenimiento",
        "Salud": "Salud",
        "Otros": "Otros",
    }
    # Si ya viene bien:
    if cat in CATEGORIAS_VALIDAS:
        return cat
    # Si viene raro:
    return mapping.get(cat, "Otros")


def _normalizar_monto(monto) -> float:
    """
    Acepta números o strings como "45", "45.5", "$45", "45,20"
    """
    if isinstance(monto, (int, float)):
        return float(monto)

    if isinstance(monto, str):
        s = monto.strip()
        s = s.replace("$", "").replace("USD", "").strip()
        s = s.replace(",", ".")
        # Deja solo números y punto
        s = re.sub(r"[^0-9.]", "", s)
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    return 0.0


# ----------------------------
# IA / Parsing
# ----------------------------
def clasificar_con_ia(texto_usuario: str) -> dict:
    """
    Devuelve un dict con: Monto (float), Categoria (str), Descripcion (str)
    """
    prompt = (
        "Extrae la siguiente información del texto y responde SOLO con JSON.\n"
        "Campos obligatorios: Monto (numero), Categoria (string), Descripcion (string).\n"
        f"Categorias permitidas: {', '.join(sorted(CATEGORIAS_VALIDAS))}.\n\n"
        f"Texto: {texto_usuario}\n"
    )

    # 1) Intento “fuerte”: forzar salida JSON con response_format
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
    except Exception:
        # 2) Plan B: sin response_format (por si tu cuenta/modelo lo rechaza)
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = resp.choices[0].message.content

    # Parse robusto
    raw_json = _extraer_json(raw)
    try:
        data = json.loads(raw_json)
    except Exception:
        # Si aún falla, devolvemos algo seguro para que NO se rompa la app
        return {"Monto": 0.0, "Categoria": "Otros", "Descripcion": texto_usuario}

    # Normaliza campos
    monto = _normalizar_monto(data.get("Monto", 0))
    categoria = _normalizar_categoria(data.get("Categoria", "Otros"))
    descripcion = data.get("Descripcion", texto_usuario)

    if not isinstance(descripcion, str) or not descripcion.strip():
        descripcion = texto_usuario

    return {"Monto": monto, "Categoria": categoria, "Descripcion": descripcion.strip()}


# ----------------------------
# App
# ----------------------------
def agregar_gasto_ia():
    texto = input("Escribe gasto (Ej: 45 McDonalds): ").strip()
    if not texto:
        print("⚠️ No ingresaste nada.\n")
        return

    datos = clasificar_con_ia(texto)

    fecha = datetime.datetime.now().strftime("%Y-%m-%d")

    with open(ARCHIVO, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [fecha, datos["Monto"], datos["Categoria"], datos["Descripcion"]])

    print(
        f"🧾 Gasto guardado: {datos['Monto']} | {datos['Categoria']} | {datos['Descripcion']}\n")


def menu():
    crear_archivo()

    while True:
        print("==== CONTROL FINANCIERO IA ====")
        print("1) Agregar gasto con IA")
        print("2) Salir")
        opcion = input("Opción: ").strip()

        if opcion == "1":
            agregar_gasto_ia()
        elif opcion == "2":
            print("Adiós 👋")
            break
        else:
            print("Opción inválida.\n")


if __name__ == "__main__":
    menu()
