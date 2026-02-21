from openai import OpenAI
from dotenv import load_dotenv
import plotly.express as px
import streamlit as st
from datetime import date, timedelta
import pandas as pd
import csv
import datetime
import json
import os
import re
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "gastos.csv"

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "gastos.csv"
CATS_PATH = BASE_DIR / "categorias.json"

CATEGORIAS_BASE = [
    "Comida", "Transporte", "Hogar", "Entretenimiento", "Salud", "Otros"
]


def cargar_categorias() -> list[str]:
    cats = set(CATEGORIAS_BASE)

    # categorías guardadas en categorias.json
    if CATS_PATH.exists():
        try:
            data = json.loads(CATS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                cats.update([str(x).strip() for x in data if str(x).strip()])
        except Exception:
            pass

    return sorted(cats)


def guardar_categorias(cats: list[str]) -> None:
    # guarda solo las extras (no repite base)
    extras = sorted(set(cats) - set(CATEGORIAS_BASE))
    CATS_PATH.write_text(json.dumps(
        extras, ensure_ascii=False, indent=2), encoding="utf-8")


def fmt(valor: float, simbolo: str, decimales: int) -> str:
    if decimales == 0:
        return f"{simbolo}{valor:,.0f}"
    return f"{simbolo}{valor:,.{decimales}f}"


ARCHIVO = str(CSV_PATH)
CATEGORIAS_VALIDAS = {"Comida", "Transporte",
                      "Hogar", "Entretenimiento", "Salud", "Otros", "deudas", "imprevistos", "inversiones"}

env_path = Path(__file__).with_name(".env")
load_dotenv(env_path, override=True)

API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None


def crear_archivo():
    if not os.path.exists(ARCHIVO):
        with open(ARCHIVO, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Fecha", "Monto", "Categoria", "Descripcion"])


def _extraer_json(texto: str) -> str:
    texto = texto.strip()
    if texto.startswith("{") and texto.endswith("}"):
        return texto
    match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
    if match:
        return match.group(0).strip()
    return texto


def _normalizar_categoria(cat: str) -> str:
    if not isinstance(cat, str):
        return "Otros"
    cat = cat.strip()
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
    if cat in CATEGORIAS_VALIDAS:
        return cat
    return mapping.get(cat, "Otros")


def _normalizar_monto(monto) -> float:
    if isinstance(monto, (int, float)):
        return float(monto)
    if isinstance(monto, str):
        s = monto.strip()
        s = s.replace("$", "").replace("USD", "").strip()
        s = s.replace(",", ".")
        s = re.sub(r"[^0-9.]", "", s)
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0
    return 0.0


def clasificar_con_ia(texto_usuario: str, model: str) -> dict:
    prompt = (
        "Extrae la siguiente información del texto y responde SOLO con JSON.\n"
        "Campos obligatorios: Monto (numero), Categoria (string), Descripcion (string).\n"
        f"Categorias permitidas: {', '.join(sorted(CATEGORIAS_VALIDAS))}.\n\n"
        f"Texto: {texto_usuario}\n"
    )

    if not client:
        return {"Monto": 0.0, "Categoria": "Otros", "Descripcion": texto_usuario}

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
    except Exception:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = resp.choices[0].message.content

    raw_json = _extraer_json(raw)
    try:
        data = json.loads(raw_json)
    except Exception:
        return {"Monto": 0.0, "Categoria": "Otros", "Descripcion": texto_usuario}

    monto = _normalizar_monto(data.get("Monto", 0))
    categoria = _normalizar_categoria(data.get("Categoria", "Otros"))
    descripcion = data.get("Descripcion", texto_usuario)
    if not isinstance(descripcion, str) or not descripcion.strip():
        descripcion = texto_usuario

    return {"Monto": monto, "Categoria": categoria, "Descripcion": descripcion.strip()}


def guardar_gasto(datos: dict):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d")
    with open(ARCHIVO, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [fecha, datos["Monto"], datos["Categoria"], datos["Descripcion"]])


def leer_df() -> pd.DataFrame:
    import pandas as pd

    if not CSV_PATH.exists():
        return pd.DataFrame(columns=["Fecha", "Monto", "Categoria", "Detalle"])

    df = pd.read_csv(CSV_PATH)

    # Limpieza segura
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    if "Monto" in df.columns:
        df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)

    df = df.dropna(subset=["Fecha"])
    return df


def totales_por_periodo(df_in: pd.DataFrame):
    # Devuelve: total_hoy, total_sem, total_mes, df_hoy, df_sem, df_mes

    # Caso None/vacío
    if df_in is None or df_in.empty:
        vacio = pd.DataFrame(
            columns=["Fecha", "Monto", "Categoria", "Descripcion"])
        return 0.0, 0.0, 0.0, vacio, vacio, vacio

    df = df_in.copy()

    # Asegurar columnas mínimas (por si vienen diferentes)
    for col in ["Fecha", "Monto", "Categoria", "Descripcion"]:
        if col not in df.columns:
            df[col] = None

    # Limpiar tipos
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)

    # Quitar fechas inválidas
    df = df.dropna(subset=["Fecha"])

    # Si quedó vacío después de limpiar
    if df.empty:
        vacio = pd.DataFrame(columns=df.columns)
        return 0.0, 0.0, 0.0, vacio, vacio, vacio

    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())  # lunes
    inicio_mes = hoy.replace(day=1)

    df_hoy = df[df["Fecha"] == hoy].copy()
    df_sem = df[(df["Fecha"] >= inicio_semana) & (df["Fecha"] <= hoy)].copy()
    df_mes = df[(df["Fecha"] >= inicio_mes) & (df["Fecha"] <= hoy)].copy()

    total_hoy = float(df_hoy["Monto"].sum()) if not df_hoy.empty else 0.0
    total_sem = float(df_sem["Monto"].sum()) if not df_sem.empty else 0.0
    total_mes = float(df_mes["Monto"].sum()) if not df_mes.empty else 0.0

    return total_hoy, total_sem, total_mes, df_hoy, df_sem, df_mes


# UI
st.set_page_config(page_title="Control Financiero IA", layout="centered")
st.title("💸 Control Financiero con IA")

crear_archivo()

if not API_KEY:
    st.error("❌ No se encontró OPENAI_API_KEY en .env. Agrega tu key y recarga.")
    st.stop()

colA, colB = st.columns(2)
with colA:
    model = st.selectbox("Modelo", ["gpt-4.1-mini"], index=0)
with colB:
    ver_historial = st.toggle("Ver historial", value=True)

texto = st.text_input("Escribe tu gasto (Ej: 45 McDonalds)",
                      placeholder="Ej: 12 uber / 30 mercado / 8 café")

c1, c2 = st.columns(2)
with c1:
    btn = st.button("🤖 Clasificar y guardar", use_container_width=True)
with c2:
    btn_preview = st.button("👀 Solo clasificar", use_container_width=True)

if btn_preview or btn:

    if not texto.strip():
        st.warning("⚠️ Escribe algo primero.")
    else:
        with st.spinner("Procesando con IA..."):
            datos = clasificar_con_ia(texto, model=model)

            # Guardamos temporalmente en session_state
        st.session_state["datos_temp"] = datos
        st.session_state["datos_id"] = f"{datos.get('Monto')}-{datos.get('Categoria')}-{datos.get('Descripcion')}"
        # 👈 resetea selección anterior
        st.session_state.pop("cat_manual", None)


# Si ya hay datos clasificados, los mostramos
datos = st.session_state.get("datos_temp")
if datos is not None:
    st.subheader("Resultado")
    st.write(f"**Monto:** {datos['Monto']}")
    st.write(f"**Categoría IA:** {datos['Categoria']}")
    st.write(f"**Descripción:** {datos['Descripcion']}")

    categorias = cargar_categorias()
    cat_ia = datos["Categoria"]
    index_default = categorias.index(cat_ia) if cat_ia in categorias else 0

    cat_manual = st.selectbox(
        "Categoría final",
        options=categorias,
        index=index_default,
        key="cat_manual"
    )

    datos["Categoria"] = cat_manual

    if st.button("💾 Confirmar y guardar"):
        guardar_gasto(datos)
        st.success("✅ Guardado en gastos.csv")
        st.session_state["datos_temp"] = None
        st.session_state.pop("cat_manual", None)

if ver_historial:
    st.divider()
    df = leer_df()

    if df.empty:
        st.info("aun no hay gastos guardados.")
    else:
        st.subheader("🧾 ultimos gastos")
        st.dataframe(df.tail(10), use_container_width=True)

    st.divider()
    st.subheader("📊 resumen")
# ===== DASHBOARD + GRÁFICO CIRCULAR =====
df = leer_df()

if df.empty:
    st.info("Aún no hay gastos guardados.")
else:
    # Asegurar tipos
    import pandas as pd
    df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)

    # --- Gráfico circular por categoría ---
    st.subheader("🥧 Gastos por categoría")

    resumen_cat = (
        df.groupby("Categoria", as_index=False)["Monto"]
        .sum()
        .sort_values("Monto", ascending=False)
    )

    import plotly.express as px
    fig = px.pie(resumen_cat, names="Categoria", values="Monto")
    st.plotly_chart(fig, use_container_width=True)
# ===== FIN DASHBOARD =====
df = leer_df()
df_filtrado = df.copy()

if df.empty:
    st.info("Aún no hay gastos guardados.")
else:
    st.sidebar.subheader("🏷 Categorías")

categorias = cargar_categorias()

nueva_cat = st.sidebar.text_input(
    "Agregar nueva categoría", placeholder="Ej: Deudas, Suscripciones...")
if st.sidebar.button("➕ Guardar categoría"):
    nueva_cat = nueva_cat.strip()
    if not nueva_cat:
        st.sidebar.warning("Escribe un nombre.")
    else:
        # Normaliza: primera letra mayúscula, resto igual
        nueva_cat = nueva_cat[0].upper() + nueva_cat[1:]
        categorias = sorted(set(categorias + [nueva_cat]))
        guardar_categorias(categorias)
        st.sidebar.success(f"Guardada: {nueva_cat}")
        st.rerun()

st.sidebar.caption(f"Total categorías: {len(categorias)}")

st.divider()
st.subheader("📊 Dashboard")
# ---- Defaults para que nunca explote ----
total_hoy = total_sem = total_mes = 0.0
df_hoy = df_sem = df_mes = pd.DataFrame()

if df.empty:
    st.info("Aún no hay gastos guardados.")
else:

    # === LIMPIEZA DE DATOS ===
    st.subheader("🧹 Limpieza")

colA, colB = st.columns(2)

with colA:
    if st.button("🗑️ Eliminar último gasto", key="btn_del_ultimo"):
        df_all = leer_df()
        if df_all.empty:
            st.info("No hay nada para borrar.")
        else:
            ultimo = df_all.tail(1)
            df_all = df_all.iloc[:-1]
            df_all.to_csv(CSV_PATH, index=False)
            st.success("✅ Último gasto eliminado.")
            st.dataframe(ultimo, use_container_width=True)
            st.rerun()

with colB:
    if st.button("🧽 Eliminar duplicados exactos", key="btn_del_dups"):
        df_all = leer_df()
        antes = len(df_all)
        df_all = df_all.drop_duplicates()
        despues = len(df_all)
        df_all.to_csv(CSV_PATH, index=False)
        st.success(f"✅ Duplicados eliminados: {antes - despues}")
        st.rerun()

st.divider()
# --- Moneda ---
moneda = st.selectbox(
    "Moneda",
    ["USD", "COP"],
    index=0,
    key="moneda_dashboard"
)
simbolo = "$"
decimales = 2

if moneda == "USD":
    simbolo = "$"
    decimales = 2
else:
    simbolo = "COP $"
    decimales = 0

    # --- Totales (Día / Semana / Mes) ---


# --- Filtros ---

df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)
df = df.dropna(subset=["Fecha"])

min_fecha = df["Fecha"].min()
max_fecha = df["Fecha"].max()

rango = st.date_input(
    "Rango de fechas",
    value=(min_fecha, max_fecha),
    min_value=min_fecha,
    max_value=max_fecha,
    key="rango_dashboard",
)
if isinstance(rango, tuple) and len(rango) == 2:
    fecha_ini, fecha_fin = rango
else:
    fecha_ini, fecha_fin = min_fecha, max_fecha

categorias = cargar_categorias()
cats_sel = st.multiselect(
    "Filtrar categorías",
    options=categorias,
    default=categorias,
    key="cats_dashboard",
)

df_filtrado = df[
    (df["Fecha"] >= fecha_ini) &
    (df["Fecha"] <= fecha_fin) &
    (df["Categoria"].isin(cats_sel))
].copy()
total_hoy, total_sem, total_mes, df_hoy, df_sem, df_mes = totales_por_periodo(
    df_filtrado)
periodo = st.radio(
    "Periodo",
    ["Día", "Semana", "Mes"],
    horizontal=True,
    key="periodo_dashboard"
)

if periodo == "Día":
    total_grande = total_hoy
    titulo = "Total de HOY"
elif periodo == "Semana":
    total_grande = total_sem
    titulo = "Total de ESTA SEMANA"
else:
    total_grande = total_mes
    titulo = "Total de ESTE MES"

simbolo = locals().get("simbolo", "$")
decimales = locals().get("decimales", 2)

st.markdown(
    f"""
    <div style="padding:14px;border-radius:12px;background:rgba(255,255,255,0.04);">
        <div style="font-size:14px;opacity:0.8;">{titulo}</div>
        <div style="font-size:46px;font-weight:800;line-height:1.1;">
            {fmt(float(total_grande), str(simbolo), int(decimales))}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Totales (según filtros) ---

c1, c2, c3 = st.columns(3)
c1.metric("Hoy", fmt(total_hoy, simbolo, decimales))
c2.metric("Semana", fmt(total_sem, simbolo, decimales))
c3.metric("Mes", fmt(total_mes, simbolo, decimales))

# --- Pie por categoría ---
st.subheader("🧩 Distribución por categoría (según filtros)")

if df_filtrado.empty:
    st.warning("No hay datos con esos filtros.")
else:
    por_cat = (
        df_filtrado  .groupby("Categoria")["Monto"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    fig = px.pie(por_cat, names="Categoria", values="Monto")
    st.plotly_chart(fig, use_container_width=True, key="pie_categoria")

    por_cat["Monto"] = por_cat["Monto"].apply(
        lambda x: fmt(float(x), simbolo, decimales))
    st.dataframe(por_cat.rename(
        columns={"Monto": "Total"}), use_container_width=True)

    # ----------------------------
    # Movimientos (según filtros)
    # ----------------------------
st.subheader("🗓️ Movimientos (según filtros)")
if df_filtrado.empty:
    st.info("No hay movimientos para mostrar.")
else:
    st.dataframe(df_filtrado.sort_values(by="Fecha", ascending=False),
                 use_container_width=True)
