import streamlit as st
from openai import OpenAI
import fitz
import pandas as pd
from docx import Document
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Bienvenido/a a SelecTalent", layout="centered")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Funciones ---
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
    prompt = f"""Actúa como un Agente de Recursos Humanos experto.
Solicita al usuario información sobre la empresa, el área que contratará, el objetivo general del puesto, principales funciones, requisitos académicos, experiencia laboral deseada, habilidades técnicas y competencias blandas.
Con esta información, genera un Descriptor de Cargo completo, siguiendo el formato estándar:
1. ¿Qué tipo de cargo buscas?: {p1}
2. ¿Qué conocimientos técnicos o habilidades necesita?: {p2}
3. ¿Qué perfil humano o experiencia previa es deseable?: {p3}
El descriptor debe ser claro, formal y ordenado, listo para usarse en procesos de reclutamiento."""
    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content.strip()

def generar_resumen_descriptor(descriptor):
    prompt = f"""Actúa como un Agente de Recursos Humanos experto.
Si el usuario ya tiene un Descriptor de Cargo (por ejemplo, en formato PDF o Word), solicita que lo adjunte.
Una vez recibido, haz un resumen ejecutivo del Descriptor,
{descriptor} El resumen debe ser breve, directo y servir como base para evaluar CVs."""
    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content.strip()

def analizar_cv(descriptor, texto_cv):
    prompt = f"""Actúa como un Agente de Recursos Humanos experto.
Analiza los CVs adjuntos en función del Descriptor de Cargo resumido.
Descriptor del cargo: {descriptor}
Currículum del candidato: {texto_cv}
Para cada candidato, entrega:
Evaluación de Formación Académica
Evaluación de Experiencia Laboral
Evaluación de Habilidades Técnicas
Evaluación de Competencias Blandas
Fortalezas
Debilidades
Nota de Afinidad al Cargo (Muy Alta, Alta, Media, Baja, Muy Baja)
Presenta la información de forma ordenada y profesional, recomendando si el candidato debería avanzar a entrevista o no."""
    response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content.strip()

def extraer_nota(texto):
    import re
    match = re.search(r"Nota de afinidad.*?(\d+)", texto)
    return int(match.group(1)) if match else 0

def generar_word(resultados, nombre_cargo):
    doc = Document()
    doc.add_heading(f"Detalle de Análisis para el Cargo: {nombre_cargo}", level=1)
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
    fig = px.bar(
        df.sort_values("Nota 1-10", ascending=False),
        x="Nombre CV",
        y="Nota 1-10",
        color="Nota 1-10",
        text="Nota 1-10",
        title="Ranking de Afinidad (Escala 1-10)"
    )
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- Reinicio de app ---
if st.button("🔄 Consultar Otro Cargo"):
    st.session_state.clear()
    st.rerun()

# --- Inicio ---
st.title("🤖 SelecTalent: Análisis de CV con IA")

if "archivos_cv" not in st.session_state:
    st.session_state.archivos_cv = []
if "resultados" not in st.session_state:
    st.session_state.resultados = []
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
        if "resumen_descriptor" not in st.session_state:
            resumen_desc = generar_resumen_descriptor(descriptor)
            st.session_state.resumen_descriptor = resumen_desc
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
        resumen_desc = generar_resumen_descriptor(descriptor_generado)
        st.session_state.resumen_descriptor = resumen_desc
        st.success("✅ Descriptor generado correctamente")

# --- Análisis y carga de CVs ---
if st.session_state.get("descriptor"):
    descriptor = st.session_state.descriptor
    nombre_cargo = st.session_state.get("nombre_cargo", "")
    resumen_descriptor = st.session_state.get("resumen_descriptor", "")

    st.subheader(f"📝 Descriptor: {nombre_cargo}")
    st.text_area("Contenido del descriptor:", descriptor, height=150)
    if resumen_descriptor:
        st.info(f"📌 **Resumen del Descriptor:**\n{resumen_descriptor}")

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
                    nota = extraer_nota(resultado)
                    resultados.append({"nombre": archivo.name, "resultado": resultado, "nota": nota})
                    resumen.append({"Nombre CV": archivo.name, "Cargo": nombre_cargo, "Nota de Afinidad": nota})
                    st.success(f"✅ CV '{archivo.name}' analizado con éxito")

            st.session_state.resultados = resultados
            st.session_state.resumen = resumen

# --- Exportación y Ranking ---
if st.session_state.get("resultados"):
    st.divider()
    st.subheader("📊 Ranking Visual de Afinidad (1 a 10)")
    mostrar_grafico_ranking(st.session_state.resumen)

    st.divider()
    st.subheader("📥 Exportar Resultados")
    col1, col2 = st.columns(2)

    with col1:
        df = pd.DataFrame(st.session_state.resumen)
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button("📊 Descargar Excel", excel_buffer, file_name=f"Nota ({nombre_cargo}).xlsx")

    with col2:
        word_data, word_name = generar_word(st.session_state.resultados, nombre_cargo)
        st.download_button("📄 Descargar Word", word_data, file_name=word_name)
