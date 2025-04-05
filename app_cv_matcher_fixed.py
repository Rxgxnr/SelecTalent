import streamlit as st
from openai import OpenAI
import fitz
import pandas as pd
from docx import Document
from io import BytesIO

# Configuracion inicial
st.set_page_config(page_title="AI CV Matcher", layout="centered")
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
Actúa como un reclutador profesional con experiencia en distintas industrias. A partir de las siguientes respuestas del usuario, redacta un descriptor profesional del cargo, listo para usarse en una oferta laboral. El texto debe ser claro, atractivo y formal, y debe incluir:

- Propósito del cargo  
- Principales funciones o responsabilidades  
- Habilidades técnicas requeridas  
- Perfil humano o experiencia deseable

Respuestas del Usuario
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
        lineas = texto.split("\n")
        for linea in reversed(lineas):
            if "Nota de afinidad" in linea:
                return int(''.join(filter(str.isdigit, linea.strip().split(":")[-1])))
    except:
        return 0
    return 0

def generar_excel(resumen, nombre_cargo):
    df = pd.DataFrame(resumen)
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return excel_buffer, f"Nota ({nombre_cargo}).xlsx"

def generar_word(resultados, nombre_cargo):
    doc = Document()
    for r in resultados:
        doc.add_heading(r["nombre"], level=2)
        doc.add_paragraph(r["resultado"])
        doc.add_page_break()
    word_buffer = BytesIO()
    doc.save(word_buffer)
    word_buffer.seek(0)
    return word_buffer, f"Detalle ({nombre_cargo}).docx"

# Inicio de app
st.title("🤖 Análisis de CV con IA")
if "archivos_cv" not in st.session_state:
    st.session_state.archivos_cv = []
if "resultados" not in st.session_state:
    st.session_state.resultados = []
if "resumen" not in st.session_state:
    st.session_state.resumen = []
if "descriptor" not in st.session_state:
    st.session_state.descriptor = ""

modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])

nombre_cargo = ""

if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt o .pdf", type=["txt", "pdf"])
    if archivo:
        if archivo.type == "text/plain":
            descriptor = archivo.read().decode("utf-8")
        elif archivo.type == "application/pdf":
            descriptor = extraer_texto_pdf(archivo)
        st.session_state.descriptor = descriptor
        st.session_state.nombre_cargo = archivo.name.replace(".txt", "").replace(".pdf", "")
        st.success("✅ Descriptor cargado correctamente.")

elif modo == "💬 Hacer Preguntas":
    with st.form("formulario"):
        p1 = st.text_input("¿Qué tipo de cargo buscas?")
        p2 = st.text_input("¿Qué habilidades o conocimientos debe tener?")
        p3 = st.text_input("¿Qué perfil humano o experiencia previa es deseable?")
        enviar = st.form_submit_button("Generar descriptor")
    if enviar:
        descriptor_generado = generar_descriptor(p1, p2, p3)
        st.session_state.descriptor = descriptor_generado
        nombre_cargo = p1
        st.session_state.nombre_cargo = nombre_cargo
        st.success("✅ Descriptor generado correctamente")

if st.session_state.get("descriptor"):
    descriptor = st.session_state.descriptor
    nombre_cargo = st.session_state.get("nombre_cargo", "")
    st.subheader(f"📝 Descriptor: {nombre_cargo}")
    if descriptor.strip():
        st.text_area("Contenido del descriptor:", descriptor, height=150)

    st.divider()
    st.subheader("📄 Carga los CVs en PDF")
    archivos_cv = st.file_uploader("Selecciona uno o varios archivos", type=["pdf"], accept_multiple_files=True)
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
                    resultados.append({"nombre": archivo.name, "resultado": resultado})
                    resumen.append({
                        "Nombre CV": archivo.name,
                        "Cargo": nombre_cargo,
                        "Nota de Afinidad": extraer_nota(resultado)
                    })
                    st.success(f"✅ CV '{archivo.name}' analizado con éxito")

            st.session_state.resultados = resultados
            st.session_state.resumen = resumen

if st.session_state.get("resumen"):
    st.divider()
    st.subheader("📥 Exportar Resultados")
    col1, col2 = st.columns(2)

    with col1:
        excel_data, excel_name = generar_excel(st.session_state.resumen, st.session_state.get("nombre_cargo", "Cargo"))
        st.download_button("📊 Descargar Excel", excel_data, file_name=excel_name)

    with col2:
        word_data, word_name = generar_word(st.session_state.resultados, st.session_state.get("nombre_cargo", "Cargo"))
        st.download_button("📄 Descargar Word", word_data, file_name=word_name)

    st.divider()
    if st.button("🔄 Consultar Otro Cargo"):
        st.session_state.clear()
        st.rerun()
