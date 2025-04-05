import streamlit as st
from openai import OpenAI
import fitz
import pandas as pd
from docx import Document
from docx.shared import Pt
import os

# Configuración de la app
st.set_page_config(page_title="AI CV Matcher", layout="centered")

# Carga de API Key desde secrets (seguro)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Función para leer PDF
def extraer_texto_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        texto = ""
        for page in doc:
            texto += page.get_text()
        return texto
    except Exception as e:
        return f"❌ Error al leer PDF: {e}"

# Función para generar descriptor a partir de preguntas
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

# Función para analizar el CV
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

# 🧠 Interfaz
st.title("🤖 Análisis de CV con IA")

if "archivos_cv" not in st.session_state:
    st.session_state.archivos_cv = []

# Modo de entrada
modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])
descriptor = ""

if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt", type=["txt"])
    if archivo:
        descriptor = archivo.read().decode("utf-8")
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

if "descriptor" in st.session_state:
    descriptor = st.session_state.descriptor
    st.text_area("📝 Descriptor generado:", st.session_state.descriptor, height=150)

if descriptor:
    st.divider()
    st.subheader("📄 Carga los CVs en PDF")

    archivos_cv = st.file_uploader("Selecciona uno o varios archivos", type=["pdf"], accept_multiple_files=True, key="file_uploader")

    if archivos_cv:
        st.session_state.archivos_cv = archivos_cv

    if st.session_state.archivos_cv:
        if st.button("🔍 Analizar CVs"):
            resultados = []
            doc = Document()

            for archivo in st.session_state.archivos_cv:
                texto = extraer_texto_pdf(archivo)
                if texto.startswith("❌"):
                    st.error(f"{archivo.name}: {texto}")
                else:
                    with st.spinner(f"Analizando {archivo.name}..."):
                        resultado = analizar_cv(descriptor, texto)
                        st.markdown(f"### 📋 Resultado para {archivo.name}")
                        st.code(resultado, language="markdown")

                        # Agregar al Word
                        doc.add_heading(f"Resultado para {archivo.name}", level=1)
                        for linea in resultado.split("\n"):
                            doc.add_paragraph(linea).style.font.size = Pt(11)
                        doc.add_page_break()

                        # Extraer nota del análisis
                        nota = ""
                        for linea in resultado.split("\n"):
                            if "Nota de afinidad" in linea:
                                nota = ''.join(filter(str.isdigit, linea))

                        resultados.append({
                            "CV": archivo.name,
                            "Cargo": p1 if modo == "💬 Hacer Preguntas" else "Cargado",
                            "Nota": nota
                        })

            # Guardar Word
            doc.save("analisis_candidatos.docx")
            with open("analisis_candidatos.docx", "rb") as f:
                st.download_button("📄 Descargar Word con análisis", f, file_name="analisis_candidatos.docx")

            # Guardar Excel
            df = pd.DataFrame(resultados)
            df.to_excel("resultados.xlsx", index=False)
            with open("resultados.xlsx", "rb") as f:
                st.download_button("📊 Descargar resumen en Excel", f, file_name="resultados.xlsx")

