import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF
import os
import pandas as pd
from docx import Document
from io import BytesIO

st.set_page_config(page_title="AI CV Matcher", layout="centered")

# Inicializar cliente OpenAI
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

# Interfaz
st.title("🤖 Análisis de CV con IA")

if "archivos_cv" not in st.session_state:
    st.session_state.archivos_cv = []

modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])

# Obtener descriptor
descriptor = ""
if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt o .pdf", type=["txt", "pdf"])
    if archivo:
        descriptor = ""
        if archivo.type == "text/plain":
            descriptor = archivo.read().decode("utf-8")
        elif archivo.type == "application/pdf":
            try:
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                for page in doc:
                    descriptor += page.get_text()
            except Exception as e:
                st.error(f"❌ Error al leer el PDF: {e}")
        else:
            st.warning("⚠️ Formato no compatible.")

        if descriptor:
            st.success("✅ Descriptor cargado correctamente.")
            st.session_state.descriptor = descriptor

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

if "descriptor" in st.session_state:
    descriptor = st.session_state.descriptor
    st.text_area("📝 Descriptor generado:", descriptor, height=150)

if descriptor:
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
            doc_word = Document()

            for archivo in st.session_state.archivos_cv:
                texto = extraer_texto_pdf(archivo)
                if texto.startswith("❌"):
                    st.error(f"{archivo.name}: {texto}")
                else:
                    with st.spinner(f"Analizando {archivo.name}..."):
                        resultado = analizar_cv(descriptor, texto)

                    st.markdown(f"### 📋 Resultado para {archivo.name}")
                    st.code(resultado, language="markdown")

                    nota = 0
                    for line in resultado.splitlines():
                        if "afinidad" in line.lower():
                            try:
                                nota = int(''.join(filter(str.isdigit, line)))
                            except:
                                nota = 0

                    resultados.append({
                        "Nombre CV": archivo.name,
                        "Cargo": p1 if modo == "💬 Hacer Preguntas" else "-",
                        "Nota de Afinidad": nota
                    })

                    doc_word.add_heading(f"Resultado para {archivo.name}", level=1)
                    doc_word.add_paragraph(resultado)
                    doc_word.add_page_break()

            df = pd.DataFrame(resultados)
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)

            word_buffer = BytesIO()
            doc_word.save(word_buffer)
            word_buffer.seek(0)

            st.download_button("⬇️ Descargar resumen en Excel", excel_buffer, file_name="resumen_cv.xlsx")
            st.download_button("⬇️ Descargar informe en Word", word_buffer, file_name="informe_detallado.docx")
