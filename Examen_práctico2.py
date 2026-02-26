import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="Sistema de Inventario TechZone", layout="wide")
st.title("Sistema de Gestión y Análisis Inteligente de Inventario — TechZone S.R.L.")

# Utilidades
CATEGORIAS_BASE = ["Laptop", "Monitor", "Accesorio", "Periférico", "Componente"]
ESTADOS_BASE = ["Disponible", "Agotado", "Descontinuado", "Crítico"]

def estado_por_stock(stock, descontinuado=False):
    if descontinuado: 
        return "Descontinuado"
    if stock == 0:
        return "Agotado"
    if stock < 5:
        return "Crítico"
    return "Disponible" 

def generar_codigo_unico():
    return f"TZ-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

def normalizar_columnas(df):
    mapeo = {
        "Producto": "Nombre",
        "Categoría": "Categoria",
        "Fecha de ingreso": "FechaIngreso",
    }
    for k, v in mapeo.items():
        if k in df.columns and v not in df.columns:
            df.rename(columns={k: v}, inplace=True)
    return df

# Pregunta 1: Carga del archivo
st.header("Carga inicial y estructura del inventario")
ruta_excel = "InventarioTechZone.xlsx"

try:
    df = pd.read_excel(ruta_excel)
except FileNotFoundError:
    st.error(f"No se encontró el archivo '{ruta_excel}'. Verifica la ruta y el nombre.")
    st.stop()
except Exception as e:
    st.error(f"Error al abrir el archivo: {e}")
    st.stop()

# Normalizar nombres de columnas
df = normalizar_columnas(df)

# Pregunta 2: FechaIngreso a datetime y tipos
if "FechaIngreso" in df.columns:
    # Mantener dtype datetime (no formatear a string)
    df["FechaIngreso"] = pd.to_datetime(df["FechaIngreso"], errors="coerce")
else:
    st.warning("No se encontró la columna 'FechaIngreso'.")
for col in ["Precio", "Stock"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Si no existe 'Estado', derivarlo desde 'Stock'
if "Estado" not in df.columns and "Stock" in df.columns:
    df["Estado"] = df["Stock"].apply(lambda s: estado_por_stock(s))

# Inicializar y sincronizar Session State ANTES de usarlo
if "inventario_df" not in st.session_state:
    st.session_state.inventario_df = df.copy()
else:
    st.session_state.inventario_df = normalizar_columnas(st.session_state.inventario_df)
    if "FechaIngreso" in st.session_state.inventario_df.columns:
        st.session_state.inventario_df["FechaIngreso"] = pd.to_datetime(
            st.session_state.inventario_df["FechaIngreso"], errors="coerce"
        )

# Usar siempre la copia en sesión
df = st.session_state.inventario_df

st.subheader("Inventario (tabla completa)")
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "FechaIngreso": st.column_config.DatetimeColumn("FechaIngreso", format="YYYY-MM-DD HH:mm:ss")
    }
)

# Preguntas 3–7: Filtros interactivos
st.header("Filtros del inventario")

# Categorías
if "Categoria" in df.columns:
    categorias_existentes = sorted([c for c in df["Categoria"].dropna().unique().tolist()]) or CATEGORIAS_BASE
else:
    categorias_existentes = CATEGORIAS_BASE
sel_categorias = st.multiselect("Filtrar por categoría", categorias_existentes, default=categorias_existentes)

# Estado
if "Estado" in df.columns:
    estados_existentes = sorted([e for e in df["Estado"].dropna().unique().tolist()])
    # Asegurar estados base si faltan
    for e in ESTADOS_BASE:
        if e not in estados_existentes:
            estados_existentes.append(e)
else:
    estados_existentes = ESTADOS_BASE
sel_estados = st.multiselect("Filtrar por estado", estados_existentes,default=estados_existentes)

# Rango de precios
if "Precio" in df.columns and df["Precio"].notna().any():
    p_min = float(df["Precio"].min())
    p_max = float(df["Precio"].max())
else:
    p_min, p_max = 0.0, 1000.0
rango_precio = st.slider("Rango de precios", min_value=float(p_min), max_value=float(p_max), value=(float(p_min), float(p_max)))

# Búsqueda por nombre / palabra clave
col_busqueda = "Nombre" if "Nombre" in df.columns else None
keyword = st.text_input("Buscar por nombre o palabra clave", value="")

# Stock mínimo mediante checkbox
aplicar_stock_min = st.checkbox("Aplicar filtro de stock mínimo")
stock_min = st.number_input("Stock mínimo", min_value=0, step=1, value=0) if aplicar_stock_min else None

# Aplicación de filtros
df_filtrado = df.copy()

if "Categoria" in df_filtrado.columns and sel_categorias:
    df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(sel_categorias)]

if "Estado" in df_filtrado.columns and sel_estados:
    df_filtrado = df_filtrado[df_filtrado["Estado"].isin(sel_estados)]

if "Precio" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Precio"].between(rango_precio[0], rango_precio[1])]

if col_busqueda and keyword.strip():
    kw = keyword.strip()
    df_filtrado = df_filtrado[df_filtrado[col_busqueda].astype(str).str.contains(kw, case=False, na=False)]

if aplicar_stock_min and stock_min is not None and "Stock" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Stock"] >= stock_min]

st.subheader("Inventario filtrado")
st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# Pregunta 8–9: Registro de nuevos productos (validaciones + estado automático)
st.header("Registro de nuevos productos")

with st.form("form_registro"):
    nombre = st.text_input("Nombre del producto")
    categoria = st.selectbox("Categoría", CATEGORIAS_BASE)
    precio = st.number_input("Precio unitario", min_value=0.0, step=0.01, format="%.2f")
    stock = st.number_input("Stock disponible", min_value=0, step=1)
    fecha_ingreso = st.date_input("Fecha de ingreso", value=datetime.date.today())
    hora_ingreso = st.time_input("Hora de ingreso", value=datetime.datetime.now().time())  
    marcar_descontinuado = st.checkbox("Marcar como descontinuado")
    submitted = st.form_submit_button("Registrar")

if submitted:
    errores = []
    if not nombre.strip():
        errores.append("El nombre no puede estar vacío.")
    if precio <= 0:
        errores.append("El precio debe ser mayor que 0.")
    if stock < 0:
        errores.append("El stock debe ser mayor o igual a 0.")
    if fecha_ingreso > datetime.date.today():
        errores.append("La fecha de ingreso no puede ser futura.")

    if errores:
        for msg in errores:
            st.error(msg)
    else:
        estado = estado_por_stock(stock, descontinuado=marcar_descontinuado)
        codigo = generar_codigo_unico()
        fecha_dt=datetime.datetime.combine(fecha_ingreso,hora_ingreso)
        nuevo = {
            "Codigo": codigo,
            "Nombre": nombre.strip(),
            "Categoria": categoria,
            "Precio": float(precio),
            "Stock": int(stock),
            "FechaIngreso": fecha_dt,
            "Estado": estado,
        }
        st.session_state.inventario_df = pd.concat([st.session_state.inventario_df, pd.DataFrame([nuevo])], ignore_index=True)
        df = st.session_state.inventario_df
        st.success(f"Producto registrado: {nombre} — Código {codigo}") 
        st.rerun()
        
def estado_por_stock(stock, descontinuado=False):
    if descontinuado:
        return "Descontinuado"
    if stock == 0:
        return "Agotado"
    if stock < 5:
        return "Crítico"
    return "Disponible"

# Persistir en sesión
if "inventario_df" not in st.session_state:
    st.session_state.inventario_df = df.copy()
else:
    st.session_state.inventario_df = normalizar_columnas(st.session_state.inventario_df)
    if "FechaIngreso" in st.session_state.inventario_df.columns:
        st.session_state.inventario_df["FechaIngreso"] = pd.to_datetime(
            st.session_state.inventario_df["FechaIngreso"], errors="coerce"
        )

# Usar siempre la copia en sesión
df = st.session_state.inventario_df
st.subheader("Inventario filtrado")
st.dataframe(df, use_container_width=True, hide_index=True)

# Pregunta 10: Cálculos y métricas avanzadas
st.header("Cálculos y métricas avanzadas")

df_calc = df.copy()
hoy = pd.Timestamp(datetime.date.today())

if "Precio" in df_calc.columns and "Stock" in df_calc.columns:
    df_calc["ValorTotal"] = df_calc["Precio"] * df_calc["Stock"]
else:
    df_calc["ValorTotal"] = np.nan

df_calc["MargenGanancia"] = df_calc["Precio"] * 0.12 if "Precio" in df_calc.columns else np.nan
if "FechaIngreso" in df_calc.columns:
    df_calc["DiasEnInventario"] = (hoy - pd.to_datetime(df_calc["FechaIngreso"], errors="coerce")).dt.days
else:
    df_calc["DiasEnInventario"] = np.nan

st.write("Tabla con columnas calculadas (ValorTotal, MargenGanancia, DiasEnInventario)")
st.dataframe(df_calc, use_container_width=True, hide_index=True)

# Pregunta 11: Gráficos
st.header("Gráficos de inventario")

# Barras: cantidad por categoría y Pie: valor total por categoría (misma figura, lado a lado)
if "Categoria" in df_calc.columns:
    conteo_cat = df_calc.groupby("Categoria", dropna=True).size().sort_values(ascending=False)
else:
    conteo_cat = pd.Series(dtype=int)

if "Categoria" in df_calc.columns and "ValorTotal" in df_calc.columns:
    valor_por_cat = df_calc.groupby("Categoria", dropna=True)["ValorTotal"].sum().sort_values(ascending=False)
else:
    valor_por_cat = pd.Series(dtype=float)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Barras (cantidad)
ax1.bar(conteo_cat.index, conteo_cat.values, color="#1f77b4")
ax1.set_title("Cantidad de productos por categoría")
ax1.set_ylabel("Cantidad")
ax1.set_xticklabels(conteo_cat.index, rotation=20, ha="right")

# Pie (valor total)
if not valor_por_cat.empty and valor_por_cat.sum() > 0:
    ax2.pie(valor_por_cat.values, labels=valor_por_cat.index, autopct="%1.1f%%", startangle=90)
    ax2.set_title("Distribución del valor total por categoría")
else:
    ax2.text(0.5, 0.5, "Sin datos de valor total", ha="center", va="center")
    ax2.axis("off")

plt.tight_layout()
st.pyplot(fig)

# TOP 5 más valiosos
st.subheader("TOP 5 productos más valiosos (por ValorTotal)")
if "ValorTotal" in df_calc.columns and "Nombre" in df_calc.columns:
    top5 = df_calc.sort_values("ValorTotal", ascending=False).head(5)
    fig_top, ax_top = plt.subplots(figsize=(8, 4))
    ax_top.bar(top5["Nombre"].astype(str), top5["ValorTotal"].astype(float), color="#ff7f0e")
    ax_top.set_ylabel("Valor total")
    ax_top.set_title("TOP 5 por ValorTotal")
    ax_top.set_xticklabels(top5["Nombre"].astype(str), rotation=20, ha="right")
    st.pyplot(fig_top)
else:
    st.info("No hay suficientes datos para calcular el TOP 5.")
    
# Preguntas 3–7: Filtros interactivos
st.header("Filtros del inventario")

# Categorías
if "Categoria" in df.columns:
    categorias_existentes = sorted([c for c in df["Categoria"].dropna().unique().tolist()]) or CATEGORIAS_BASE
else:
    categorias_existentes = CATEGORIAS_BASE
sel_categorias = st.multiselect("Filtrar por categoría", categorias_existentes, default=categorias_existentes)

# Estado
if "Estado" in df.columns:
    estados_existentes = sorted([e for e in df["Estado"].dropna().unique().tolist()])
    # Asegurar estados base si faltan
    for e in ESTADOS_BASE:
        if e not in estados_existentes:
            estados_existentes.append(e)
else:
    estados_existentes = ESTADOS_BASE
sel_estados = st.multiselect("Filtrar por estado", estados_existentes,default=estados_existentes)

# Rango de precios
if "Precio" in df.columns and df["Precio"].notna().any():
    p_min = float(df["Precio"].min())
    p_max = float(df["Precio"].max())
else:
    p_min, p_max = 0.0, 1000.0
rango_precio = st.slider("Rango de precios", min_value=float(p_min), max_value=float(p_max), value=(float(p_min), float(p_max)))

# Búsqueda por nombre / palabra clave
col_busqueda = "Nombre" if "Nombre" in df.columns else None
keyword = st.text_input("Buscar por nombre o palabra clave", value="")

# Stock mínimo mediante checkbox
aplicar_stock_min = st.checkbox("Aplicar filtro de stock mínimo")
stock_min = st.number_input("Stock mínimo", min_value=0, step=1, value=0) if aplicar_stock_min else None

# Aplicación de filtros
df_filtrado = df.copy()

if "Categoria" in df_filtrado.columns and sel_categorias:
    df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(sel_categorias)]

if "Estado" in df_filtrado.columns and sel_estados:
    df_filtrado = df_filtrado[df_filtrado["Estado"].isin(sel_estados)]

if "Precio" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Precio"].between(rango_precio[0], rango_precio[1])]

if col_busqueda and keyword.strip():
    kw = keyword.strip()
    df_filtrado = df_filtrado[df_filtrado[col_busqueda].astype(str).str.contains(kw, case=False, na=False)]

if aplicar_stock_min and stock_min is not None and "Stock" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Stock"] >= stock_min]

st.subheader("Inventario filtrado")
st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# Pregunta 8–9: Registro de nuevos productos (validaciones + estado automático)
st.header("Registro de nuevos productos")

with st.form("form_registro"):
    nombre = st.text_input("Nombre del producto")
    categoria = st.selectbox("Categoría", CATEGORIAS_BASE)
    precio = st.number_input("Precio unitario", min_value=0.0, step=0.01, format="%.2f")
    stock = st.number_input("Stock disponible", min_value=0, step=1)
    fecha_ingreso = st.date_input("Fecha de ingreso", value=datetime.date.today())
    hora_ingreso = st.time_input("Hora de ingreso", value=datetime.datetime.now().time())  
    marcar_descontinuado = st.checkbox("Marcar como descontinuado")
    submitted = st.form_submit_button("Registrar")

if submitted:
    errores = []
    if not nombre.strip():
        errores.append("El nombre no puede estar vacío.")
    if precio <= 0:
        errores.append("El precio debe ser mayor que 0.")
    if stock < 0:
        errores.append("El stock debe ser mayor o igual a 0.")
    if fecha_ingreso > datetime.date.today():
        errores.append("La fecha de ingreso no puede ser futura.")

    if errores:
        for msg in errores:
            st.error(msg)
    else:
        estado = estado_por_stock(stock, descontinuado=marcar_descontinuado)
        codigo = generar_codigo_unico()
        fecha_dt=datetime.datetime.combine(fecha_ingreso,hora_ingreso)
        nuevo = {
            "Codigo": codigo,
            "Nombre": nombre.strip(),
            "Categoria": categoria,
            "Precio": float(precio),
            "Stock": int(stock),
            "FechaIngreso": fecha_dt,
            "Estado": estado,
        }
        st.session_state.inventario_df = pd.concat([st.session_state.inventario_df, pd.DataFrame([nuevo])], ignore_index=True)
        df = st.session_state.inventario_df
        st.success(f"Producto registrado: {nombre} — Código {codigo}") 
        st.rerun()
        
def estado_por_stock(stock, descontinuado=False):
    if descontinuado:
        return "Descontinuado"
    if stock == 0:
        return "Agotado"
    if stock < 5:
        return "Crítico"
    return "Disponible"

# Pregunta 10: Cálculos y métricas avanzadas
st.header("Cálculos y métricas avanzadas")

df_calc = df.copy()
hoy = pd.Timestamp(datetime.date.today())

if "Precio" in df_calc.columns and "Stock" in df_calc.columns:
    df_calc["ValorTotal"] = df_calc["Precio"] * df_calc["Stock"]
else:
    df_calc["ValorTotal"] = np.nan

df_calc["MargenGanancia"] = df_calc["Precio"] * 0.12 if "Precio" in df_calc.columns else np.nan
if "FechaIngreso" in df_calc.columns:
    df_calc["DiasEnInventario"] = (hoy - pd.to_datetime(df_calc["FechaIngreso"], errors="coerce")).dt.days
else:
    df_calc["DiasEnInventario"] = np.nan

st.write("Tabla con columnas calculadas (ValorTotal, MargenGanancia, DiasEnInventario)")
st.dataframe(df_calc, use_container_width=True, hide_index=True)

# Pregunta 11: Gráficos
st.header("Gráficos de inventario")

# Barras: cantidad por categoría y Pie: valor total por categoría (misma figura, lado a lado)
if "Categoria" in df_calc.columns:
    conteo_cat = df_calc.groupby("Categoria", dropna=True).size().sort_values(ascending=False)
else:
    conteo_cat = pd.Series(dtype=int)

if "Categoria" in df_calc.columns and "ValorTotal" in df_calc.columns:
    valor_por_cat = df_calc.groupby("Categoria", dropna=True)["ValorTotal"].sum().sort_values(ascending=False)
else:
    valor_por_cat = pd.Series(dtype=float)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Barras (cantidad)
ax1.bar(conteo_cat.index, conteo_cat.values, color="#1f77b4")
ax1.set_title("Cantidad de productos por categoría")
ax1.set_ylabel("Cantidad")
ax1.set_xticklabels(conteo_cat.index, rotation=20, ha="right")

# Pie (valor total)
if not valor_por_cat.empty and valor_por_cat.sum() > 0:
    ax2.pie(valor_por_cat.values, labels=valor_por_cat.index, autopct="%1.1f%%", startangle=90)
    ax2.set_title("Distribución del valor total por categoría")
else:
    ax2.text(0.5, 0.5, "Sin datos de valor total", ha="center", va="center")
    ax2.axis("off")

plt.tight_layout()
st.pyplot(fig)

# TOP 5 más valiosos
st.subheader("TOP 5 productos más valiosos (por ValorTotal)")
if "ValorTotal" in df_calc.columns and "Nombre" in df_calc.columns:
    top5 = df_calc.sort_values("ValorTotal", ascending=False).head(5)
    fig_top, ax_top = plt.subplots(figsize=(8, 4))
    ax_top.bar(top5["Nombre"].astype(str), top5["ValorTotal"].astype(float), color="#ff7f0e")
    ax_top.set_ylabel("Valor total")
    ax_top.set_title("TOP 5 por ValorTotal")
    ax_top.set_xticklabels(top5["Nombre"].astype(str), rotation=20, ha="right")
    st.pyplot(fig_top)
else:
    st.info("No hay suficientes datos para calcular el TOP 5.")