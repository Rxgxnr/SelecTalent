import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF
import os
import re
import pandas as pd
from io import BytesIO
from docx import Document

st.set_page_config(page_title="AI CV Matcher", layout="centered")

# Cargar API key desde los secrets
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
Actúa como reclutador experto. Con base en estas respuestas, genera un descriptor profesional del cargo:

1. ¿Qué tipo de cargo buscas?: {p1}
2. ¿Qué conocimientos técnicos o habilidades necesita?: {p2}
3. ¿Qué perfil humano o experiencia previa es deseable?: {p3}

Redáctalo de forma clara y profesional.
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def analizar_cv(descriptor, texto_cv):
    prompt = f"""Analiza el siguiente CV en base al descriptor de cargo.

Descriptor del cargo:
{descriptor}

Currículum del candidato:
{texto_cv}

Entregar análisis en este formato:
Fortalezas:
-
Debilidades:
-
Nota de afinidad con el cargo (de 1 a 100):"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def extraer_nota(texto):
    try:
        match = re.search(r"Nota de afinidad.*?(\d{1,3})", texto)
        if match:
            nota = int(match.group(1))
            return min(nota, 100)
        else:
            return 0
    except:
        return 0

def generar_excel(data):
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return output

def generar_word(resultados):
    doc = Document()
    for resultado in resultados:
        doc.add_heading(resultado['nombre'], level=2)
        doc.add_paragraph(resultado['analisis'])
        doc.add_page_break()
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# Interfaz principal
st.title("🤖 Análisis de CV con IA")

if "archivos_cv" not in st.session_state:
    st.session_state.archivos_cv = []
if "resultados" not in st.session_state:
    st.session_state.resultados = []

modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])
descriptor = ""

if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt o .pdf", type=["txt", "pdf"])
    if archivo:
        if archivo.type == "text/plain":
            descriptor = archivo.read().decode("utf-8")
        elif archivo.type == "application/pdf":
            descriptor = extraer_texto_pdf(archivo)
        st.session_state.descriptor = descriptor
        st.success("✅ Descriptor cargado correctamente.")

elif modo == "💬 Hacer Preguntas":
    with st.form("formulario"):
        p1 = st.text_input("1. ¿Qué tipo de cargo buscas?")
        p2 = st.text_input("2. ¿Qué habilidades o conocimientos debe tener?")
        p3 = st.text_input("3. ¿Qué perfil humano o experiencia previa es deseable?")
        enviar = st.form_submit_button("Generar descriptor")

    if enviar:
        descriptor_generado = generar_descriptor(p1, p2, p3)
        st.session_state.descriptor = descriptor_generado
        st.success("✅ Descriptor generado correctamente")

if "descriptor" in st.session_state and st.session_state.descriptor.strip():
    descriptor = st.session_state.descriptor
    st.text_area("📝 Descriptor generado:", descriptor, height=150)

    st.divider()
    st.subheader("📄 Carga los CVs en PDF")

    archivos_cv = st.file_uploader(
        "Selecciona uno o varios archivos", 
        type=["pdf"], 
        accept_multiple_files=True,
        key="file_uploader"
    )

    if archivos_cv:
        st.session_state.archivos_cv = archivos_cv

    if st.session_state.archivos_cv:
        if st.button("🔍 Analizar CVs"):
            resultados = []
            resumen = []
            for archivo in st.session_state.archivos_cv:
                texto = extraer_texto_pdf(archivo)
                if texto.startswith("❌"):
                    st.error(f"{archivo.name}: {texto}")
                else:
                    with st.spinner(f"Analizando {archivo.name}..."):
                        resultado = analizar_cv(descriptor, texto)
                    st.markdown(f"### 📋 Resultado para {archivo.name}")
                    st.code(resultado, language="markdown")

                    resumen.append({
                        "Nombre CV": archivo.name,
                        "Cargo": p1 if modo == "💬 Hacer Preguntas" else "Descriptor Cargado",
                        "Nota de Afinidad": extraer_nota(resultado)
                    })
                    resultados.append({
                        "nombre": archivo.name,
                        "analisis": resultado
                    })
            st.session_state.resultados = resultados
            st.session_state.resumen = resumen

if st.session_state.get("resumen"):
    st.divider()
    st.subheader("📥 Exportar Resultados")
    col1, col2 = st.columns(2)

    with col1:
        excel_data = generar_excel(st.session_state.resumen)
        st.download_button("📊 Descargar Excel", excel_data, file_name="resumen_cv.xlsx")

    with col2:
        word_data = generar_word(st.session_state.resultados)
        st.download_button("📄 Descargar Word", word_data, file_name="analisis_cv.docx")

    st.divider()
    if st.button("🔄 Consultar Otro Cargo"):
        st.rerun()

