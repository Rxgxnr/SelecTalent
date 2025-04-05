import streamlit as st
from openai import OpenAI
import fitz
import os
import pandas as pd
from io import BytesIO
from docx import Document

st.set_page_config(page_title="AI CV Matcher", layout="centered")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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

def crear_archivo_excel(datos):
    df = pd.DataFrame(datos, columns=["Nombre CV", "Cargo", "Nota de Afinidad"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output

def crear_archivo_word(resultados):
    doc = Document()
    for nombre_cv, resultado in resultados.items():
        doc.add_heading(f"Resultado para {nombre_cv}", level=1)
        doc.add_paragraph(resultado)
        doc.add_page_break()
    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output

st.title("🤖 Análisis de CV con IA")

if "archivos_cv" not in st.session_state:
    st.session_state.archivos_cv = []
if "resultados" not in st.session_state:
    st.session_state.resultados = {}
if "datos_excel" not in st.session_state:
    st.session_state.datos_excel = []

modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])

descriptor = ""

if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt o .pdf", type=["txt", "pdf"], key="descriptor")
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

if st.session_state.get("descriptor", "").strip():
    descriptor = st.session_state["descriptor"]
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
            st.session_state.resultados.clear()
            st.session_state.datos_excel.clear()
            for archivo in st.session_state.archivos_cv:
                texto = extraer_texto_pdf(archivo)
                if texto.startswith("❌"):
                    st.error(f"{archivo.name}: {texto}")
                else:
                    with st.spinner(f"Analizando {archivo.name}..."):
                        resultado = analizar_cv(descriptor, texto)

                    st.markdown(f"### 📋 Resultado para {archivo.name}")
                    st.code(resultado, language="markdown")
                    st.session_state.resultados[archivo.name] = resultado

                    nota_linea = [line for line in resultado.split("\n") if "Nota de afinidad" in line]
                    nota = "".join(filter(str.isdigit, nota_linea[0])) if nota_linea else "0"
                    if nota:
                        try:
                            nota = int(nota)
                            nota = min(max(nota, 0), 100)
                        except:
                            nota = 0
                    st.session_state.datos_excel.append([archivo.name, p1 if modo == "💬 Hacer Preguntas" else "Cargo", f"{nota}/100"])

        if st.session_state.resultados:
            st.divider()
            st.subheader("📥 Descarga los resultados")
            col1, col2 = st.columns(2)
            with col1:
                excel_file = crear_archivo_excel(st.session_state.datos_excel)
                st.download_button("📊 Descargar Excel", data=excel_file, file_name="resumen_cvs.xlsx")
            with col2:
                word_file = crear_archivo_word(st.session_state.resultados)
                st.download_button("📝 Descargar Word", data=word_file, file_name="analisis_postulantes.docx")

            st.divider()
            if st.button("🔄 Consultar Otro Cargo"):
                st.session_state.clear()
                st.experimental_rerun()
