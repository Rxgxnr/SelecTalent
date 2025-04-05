import streamlit as st
from openai import OpenAI
import fitz
import pandas as pd
from docx import Document
from io import BytesIO
import plotly.express as px
import re

st.set_page_config(page_title="SelecTalent", layout="centered")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Funciones
def extraer_texto_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        texto = ""
        for page in doc:
            texto += page.get_text()
        return texto
    except Exception as e:
        return f"❌ Error al leer PDF: {e}"

def generar_descriptor(p1, p2, p3):
    prompt = f"""
Actúa como reclutador profesional. Redacta un descriptor para:
- Cargo: {p1}
- Habilidades técnicas: {p2}
- Perfil humano: {p3}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def analizar_cv(descriptor, texto_cv):
    prompt = f"""
Analiza este CV según el siguiente descriptor:

{descriptor}

CV:
{texto_cv}

Formato:
Fortalezas:
-
Debilidades:
-
Nota de afinidad con el cargo (1-100):
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def extraer_nota(texto):
    match = re.search(r"Nota de afinidad.*?(\d+)", texto)
    return int(match.group(1)) if match else 0

def generar_word(resultados, nombre_cargo):
    doc = Document()
    doc.add_heading(f"Detalle de Análisis para el Cargo: {nombre_cargo}", level=1)
    doc.add_paragraph("Este documento contiene el análisis individual generado por la IA para cada postulante.\n")
    doc.add_page_break()
    for r in resultados:
        doc.add_heading(r["nombre"], level=2)
        doc.add_paragraph(r["resultado"])
        doc.add_page_break()
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer, f"Detalle ({nombre_cargo}).docx"

def mostrar_grafico_ranking(resumen):
    df = pd.DataFrame(resumen)
    df["Nota 1-10"] = (df["Nota de Afinidad"] / 10).round(1).clip(upper=10)
    fig = px.bar(df.sort_values("Nota 1-10", ascending=False), x="Nombre CV", y="Nota 1-10", color="Nota 1-10", text="Nota 1-10", title="Ranking de Afinidad (Escala 1-10)")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

# Estado inicial
if "favoritos" not in st.session_state:
    st.session_state.favoritos = []
if "resultados" not in st.session_state:
    st.session_state.resultados = []
if "resumen" not in st.session_state:
    st.session_state.resumen = []

# Reiniciar app
if st.button("🔄 Consultar Otro Cargo"):
    st.session_state.clear()
    st.rerun()

# App
st.title("🤖 SelecTalent")

modo = st.radio("¿Quieres cargar un descriptor o generarlo?", ["📂 Cargar", "💬 Generar con IA"])

if modo == "📂 Cargar":
    archivo = st.file_uploader("Sube descriptor (.txt o .pdf)", type=["txt", "pdf"])
    if archivo:
        if archivo.type == "text/plain":
            descriptor = archivo.read().decode("utf-8")
        else:
            descriptor = extraer_texto_pdf(archivo)
        st.session_state.descriptor = descriptor
        st.session_state.nombre_cargo = archivo.name.replace(".pdf", "").replace(".txt", "")
        st.success("✅ Descriptor cargado correctamente.")
else:
    with st.form("formulario"):
        p1 = st.text_input("¿Qué cargo buscas?")
        p2 = st.text_input("¿Qué habilidades técnicas necesita?")
        p3 = st.text_input("¿Qué perfil humano o experiencia previa es deseable?")
        enviar = st.form_submit_button("Generar descriptor")
    if enviar:
        descriptor = generar_descriptor(p1, p2, p3)
        st.session_state.descriptor = descriptor
        st.session_state.nombre_cargo = p1
        st.success("✅ Descriptor generado correctamente.")

# Mostrar descriptor
if "descriptor" in st.session_state:
    descriptor = st.session_state.descriptor
    nombre_cargo = st.session_state.get("nombre_cargo", "Cargo")
    st.subheader("📋 Descriptor del Cargo")
    st.text_area("Contenido:", descriptor, height=150)

    # Cargar y analizar CVs
    st.subheader("📄 Cargar CVs")
    archivos_cv = st.file_uploader("Sube los CVs en PDF", type=["pdf"], accept_multiple_files=True)
    if archivos_cv:
        resultados = []
        resumen = []
        for archivo in archivos_cv:
            texto = extraer_texto_pdf(archivo)
            resultado = analizar_cv(descriptor, texto)
            nota = extraer_nota(resultado)
            resultados.append({"nombre": archivo.name, "resultado": resultado, "nota": nota})
            resumen.append({"Nombre CV": archivo.name, "Nota de Afinidad": nota})
            st.success(f"✅ {archivo.name} analizado correctamente")
        st.session_state.resultados = resultados
        st.session_state.resumen = resumen

# Mostrar resultados
if st.session_state.get("resumen"):
    st.subheader("⭐ Marcar Favoritos")
    for r in st.session_state.resultados:
        fav = st.checkbox(f"Marcar {r['nombre']} como favorito", key=f"fav_{r['nombre']}")
        if fav and r["nombre"] not in st.session_state.favoritos:
            st.session_state.favoritos.append(r["nombre"])

    mostrar_grafico_ranking(st.session_state.resumen)

    st.subheader("🆚 Comparar Candidatos")
    seleccionados = st.multiselect("Selecciona hasta 2 candidatos", [r["nombre"] for r in st.session_state.resultados])
    if len(seleccionados) == 2:
        a = next(r for r in st.session_state.resultados if r["nombre"] == seleccionados[0])
        b = next(r for r in st.session_state.resultados if r["nombre"] == seleccionados[1])
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### {a['nombre']}")
            st.text(a["resultado"])
        with col2:
            st.markdown(f"### {b['nombre']}")
            st.text(b["resultado"])

    st.subheader("📤 Exportar Resultados")
    df = pd.DataFrame(st.session_state.resumen)
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    st.download_button("📊 Descargar Excel", excel_buffer, file_name=f"Notas {st.session_state.get('nombre_cargo')}.xlsx")

    word_data, word_name = generar_word(st.session_state.resultados, st.session_state.get("nombre_cargo", "Cargo"))
    st.download_button("📄 Descargar Word", word_data, file_name=word_name)
