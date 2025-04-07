import streamlit as st
from openai import OpenAI
import fitz
import pandas as pd
from docx import Document
from io import BytesIO
import plotly.express as px
import re

# --- Configuración Inicial ---
st.set_page_config(page_title="Bienvenido/a a SelecTalent", layout="centered")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Inicialización de Estados ---
for key in ["archivos_cv", "resultados", "descriptor", "nombre_cargo", "resumen_descriptor"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "cv" in key or key == "resultados" else ""

# --- Funciones Clave ---
def extraer_texto_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join([page.get_text() for page in doc])
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
    categorias = ["Muy Alta", "Alta", "Media", "Baja", "Muy Baja"]
    for cat in categorias:
        if cat.lower() in texto.lower():
            return cat
    return "Sin Clasificar"

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

    orden_afinidad = ["Muy Alta", "Alta", "Media", "Baja", "Muy Baja"]
    mapa_numerico = {"Muy Alta": 5, "Alta": 4, "Media": 3, "Baja": 2, "Muy Baja": 1}

    df["Nivel Afinidad"] = pd.Categorical(df["Nota de Afinidad"], categories=orden_afinidad, ordered=True)
    df = df.sort_values("Nivel Afinidad")
    df["Afinidad Numérica"] = df["Nota de Afinidad"].map(mapa_numerico)

    fig = px.bar(
        df,
        x="Nombre CV",
        y="Afinidad Numérica",
        color="Nota de Afinidad",
        text="Nota de Afinidad",
        title="Ranking de Afinidad (Categorías)",
        category_orders={"Nota de Afinidad": orden_afinidad}
    )
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- Botón para reiniciar ---
if st.button("🔄 Consultar Otro Cargo"):
    st.session_state.clear()
    st.rerun()

# --- Título Principal ---
st.title("🤖 SelecTalent: Análisis de CV con IA")

# --- Entrada de Descriptor ---
modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])

if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt o .pdf", type=["txt", "pdf"])
    if archivo:
        descriptor = archivo.read().decode("utf-8") if archivo.type == "text/plain" else extraer_texto_pdf(archivo)
        st.session_state.descriptor = descriptor
        st.session_state.nombre_cargo = archivo.name.rsplit(".", 1)[0]
        if not st.session_state.resumen_descriptor:
            st.session_state.resumen_descriptor = generar_resumen_descriptor(descriptor)
        st.success("✅ Descriptor cargado correctamente.")

elif modo == "💬 Hacer Preguntas":
    with st.form("formulario"):
        p1 = st.text_input("¿Qué tipo de cargo buscas?")
        p2 = st.text_input("¿Qué habilidades o conocimientos debe tener?")
        p3 = st.text_input("¿Qué perfil humano o experiencia previa es deseable?")
        enviar = st.form_submit_button("Generar descriptor")
    if enviar:
        st.session_state.descriptor = generar_descriptor(p1, p2, p3)
        st.session_state.nombre_cargo = p1
        st.session_state.resumen_descriptor = generar_resumen_descriptor(st.session_state.descriptor)
        st.success("✅ Descriptor generado correctamente.")

# --- Análisis de CVs ---
if st.session_state.descriptor:
    st.subheader(f"📝 Descriptor: {st.session_state.nombre_cargo}")
    st.text_area("Contenido del descriptor:", st.session_state.descriptor, height=150)
    st.info(f"📌 **Resumen del Descriptor:**\n{st.session_state.resumen_descriptor}")

    st.divider()
    st.subheader("📄 Carga los CVs en PDF")
    archivos_cv = st.file_uploader("Selecciona uno o varios archivos", type=["pdf"], accept_multiple_files=True)
    if archivos_cv:
        st.session_state.archivos_cv = archivos_cv

    if st.session_state.archivos_cv:
        if st.button("🔍 Analizar CVs"):
            resultados, resumen = [], []
            for archivo in st.session_state.archivos_cv:
                texto = extraer_texto_pdf(archivo)
                if texto.startswith("❌"):
                    st.error(f"{archivo.name}: {texto}")
                    continue
                with st.spinner(f"Analizando {archivo.name}..."):
                    resultado = analizar_cv(st.session_state.descriptor, texto)
                nota = extraer_nota(resultado)
                resultados.append({"nombre": archivo.name, "resultado": resultado, "nota": nota})
                resumen.append({
    "Nombre CV": archivo.name,
    "Cargo": nombre_cargo,
    "Nota de Afinidad": nota  # ← esto será "Alta", "Media", etc.
})
                st.success(f"✅ CV '{archivo.name}' analizado con éxito")
            st.session_state.resultados = resultados
            st.session_state.resumen = resumen

# --- Exportación y Visualización ---
if st.session_state.resultados:
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
        st.download_button("📊 Descargar Excel", excel_buffer, file_name=f"Nota ({st.session_state.nombre_cargo}).xlsx")

    with col2:
        word_data, word_name = generar_word(st.session_state.resultados, st.session_state.nombre_cargo)
        st.download_button("📄 Descargar Word", word_data, file_name=word_name)
