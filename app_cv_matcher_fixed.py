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

def extraer_texto_txt(file):
    try:
        return file.read().decode("utf-8")
    except Exception as e:
        return f"❌ Error al leer TXT: {e}"

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

# App
st.title("🤖 Análisis de CV con IA")

if "archivos_cv" not in st.session_state:
    st.session_state.archivos_cv = []
if "analisis" not in st.session_state:
    st.session_state.analisis = []
if "descriptor" not in st.session_state:
    st.session_state.descriptor = ""

modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])

descriptor = ""

if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt o .pdf", type=["txt", "pdf"])
    if archivo:
        if archivo.type == "text/plain":
            descriptor = extraer_texto_txt(archivo)
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

if st.session_state.get("descriptor", "").strip():
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
            st.session_state.analisis = []
            for archivo in st.session_state.archivos_cv:
                texto = extraer_texto_pdf(archivo)
                if texto.startswith("❌"):
                    st.error(f"{archivo.name}: {texto}")
                else:
                    with st.spinner(f"Analizando {archivo.name}..."):
                        resultado = analizar_cv(descriptor, texto)
                        st.session_state.analisis.append({
                            "nombre": archivo.name,
                            "resultado": resultado,
                            "nota": extraer_nota(resultado),
                            "cargo": p1 if modo == "💬 Hacer Preguntas" else "-"
                        })
            st.session_state.procesado = True

    if st.session_state.get("procesado"):
        for analisis in st.session_state.analisis:
            st.markdown(f"### 📋 Resultado para {analisis['nombre']}")
            st.code(analisis["resultado"], language="markdown")

        # Botones de descarga
        df = pd.DataFrame([{
            "Nombre CV": a["nombre"],
            "Cargo": a["cargo"],
            "Nota de Afinidad": f"{a['nota']}/100"
        } for a in st.session_state.analisis])

        output_excel = BytesIO()
        df.to_excel(output_excel, index=False)
        st.download_button("📥 Descargar resumen en Excel", data=output_excel.getvalue(), file_name="resumen_cv.xlsx")

        doc = Document()
        for a in st.session_state.analisis:
            doc.add_heading(f"Resultado para {a['nombre']}", level=1)
            for linea in a["resultado"].split("\n"):
                doc.add_paragraph(linea)
            doc.add_page_break()

        output_word = BytesIO()
        doc.save(output_word)
        st.download_button("📥 Descargar informe en Word", data=output_word.getvalue(), file_name="analisis_cv.docx")

        if st.button("🔁 Consultar Otro Cargo"):
            st.session_state.clear()
            st.experimental_rerun()

# Utilidad

def extraer_nota(texto):
    import re
    match = re.search(r"(\d{1,3})\s*/?\s*100", texto)
    if match:
        return int(match.group(1))
    else:
        match = re.search(r"(\d{1,3})", texto)
        return int(match.group(1)) if match else 0
