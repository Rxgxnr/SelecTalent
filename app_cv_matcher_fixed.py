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
for key in ["archivos_cv", "resultados", "descriptor", "nombre_cargo", "resumen_descriptor", "resumen"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["archivos_cv", "resultados", "resumen"] else ""

# --- Funciones Clave ---
def extraer_texto_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join([page.get_text() for page in doc])
    except Exception as e:
        return f"❌ Error al leer PDF: {e}"

def generar_descriptor(p1, p2, p3):
    prompt = f"""Actúa como un Agente de Recursos Humanos experto. Necesito que generes un Descriptor de Cargo completo basado en:
1. Tipo de cargo: {p1}
2. Habilidades técnicas necesarias: {p2}
3. Perfil humano deseable: {p3}

Instrucciones específicas:
- Usa EXCLUSIVAMENTE categorías textuales (Muy Alta, Alta, Media, Baja, Muy Baja) para cualquier evaluación
- NO uses escalas numéricas (1-10, 1-100, porcentajes)
- El formato debe incluir:
  * Nombre del cargo
  * Objetivo principal
  * Funciones clave (lista numerada)
  * Requisitos académicos
  * Experiencia requerida (especificando "Muy Alta/Alta/Media/Baja relevancia")
  * Habilidades técnicas (clasificadas por importancia)
  * Competencias blandas requeridas
  * Condiciones laborales (opcional)"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def generar_resumen_descriptor(descriptor):
    prompt = f"""Actúa como un especialista en Recursos Humanos. Resume este descriptor de cargo manteniendo:
{descriptor}

Instrucciones estrictas:
1. Usa SOLO categorías textuales (Muy Alta, Alta, Media, Baja) para prioridades
2. Prohibido usar números, porcentajes o escalas
3. Estructura el resumen en:
- Cargo y objetivo (1 línea)
- 3-5 funciones CRÍTICAS (indicar "Prioridad: [Muy Alta/Alta]")
- 3-5 requisitos ESENCIALES (indicar "Relevancia: [Muy Alta/Alta]")
- Perfil ideal resumido"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content.strip()

def analizar_cv(descriptor, texto_cv):
    prompt = f"""Actúa como un Agente de Recursos Humanos experto.
Analiza los CVs adjuntos en función del Descriptor de Cargo resumido.
Descriptor del cargo: {descriptor}
Currículum del candidato: {texto_cv}

Para cada candidato, entrega:
1. Evaluación de Formación Académica
2. Evaluación de Experiencia Laboral
3. Evaluación de Habilidades Técnicas
4. Evaluación de Competencias Blandas
5. Fortalezas
6. Debilidades
7. Nota de Afinidad al Cargo (Usar EXCLUSIVAMENTE una de estas categorías: Muy Alta, Alta, Media, Baja, Muy Baja)

Presenta la información de forma ordenada y profesional, recomendando si el candidato debería avanzar a entrevista o no.
NO uses escalas numéricas (1-10 o 1-100), solo las categorías textuales mencionadas."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    texto = response.choices[0].message.content.strip()
    nota = extraer_nota(texto)
    return {"texto": texto, "nota": nota}

def extraer_nota(texto):
    categorias = ["Muy Alta", "Alta", "Media", "Baja", "Muy Baja"]
    for cat in categorias:
        if cat.lower() in texto.lower():
            return cat
    return "Sin Clasificar"

def generar_word(resultados, nombre_cargo):
    doc = Document()
    doc.add_heading(f"Reporte de Análisis - {nombre_cargo}", level=1)
    orden = {"Muy Alta": 0, "Alta": 1, "Media": 2, "Baja": 3, "Muy Baja": 4}
    ordenados = sorted(resultados, key=lambda x: orden.get(x["nota"], 5))
    for r in ordenados:
        doc.add_heading(r["nombre"], level=2)
        doc.add_paragraph(f"Nota de Afinidad: {r['nota']}", style='Intense Quote')
        doc.add_paragraph(r["texto"])
        doc.add_page_break()
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer, f"Reporte de Análisis - {nombre_cargo}.docx"

def mostrar_grafico_ranking(resumen):
    df = pd.DataFrame(resumen)
    orden = ["Muy Alta", "Alta", "Media", "Baja", "Muy Baja"]
    df["Nota de Afinidad"] = pd.Categorical(df["Nota de Afinidad"], categories=orden, ordered=True)
    fig = px.bar(
        df.sort_values("Nota de Afinidad"),
        x="Nombre CV",
        y="Nota de Afinidad",
        color="Nota de Afinidad",
        color_discrete_map={
            "Muy Alta": "#2ecc71", "Alta": "#27ae60", "Media": "#f39c12",
            "Baja": "#e74c3c", "Muy Baja": "#c0392b"
        },
        text="Nota de Afinidad",
        title="Ranking de Afinidad por Categoría"
    )
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- Botón para reiniciar ---
if st.button("🔄 Consultar Otro Cargo"):
    st.session_state.clear()
    st.rerun()

# --- Inicio de la App ---
st.title("🤖 SelecTalent: Análisis de CV con IA")

if st.session_state.get('descriptor'):
    st.sidebar.success(f"Cargo actual: {st.session_state.nombre_cargo}")

modo = st.radio("¿Quieres cargar un descriptor o prefieres que te ayude?", ["📂 Cargar Descriptor", "💬 Hacer Preguntas"])

if modo == "📂 Cargar Descriptor":
    archivo = st.file_uploader("Sube un descriptor en .txt o .pdf", type=["txt", "pdf"])
    if archivo:
        descriptor = archivo.read().decode("utf-8") if archivo.type == "text/plain" else extraer_texto_pdf(archivo)
        st.session_state.descriptor = descriptor
        st.session_state.nombre_cargo = archivo.name.rsplit(".", 1)[0]
        with st.spinner("Generando resumen del descriptor..."):
            st.session_state.resumen_descriptor = generar_resumen_descriptor(descriptor)
        st.success("✅ Descriptor cargado correctamente.")
        st.experimental_rerun()

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
        st.experimental_rerun()

if st.session_state.get("descriptor"):
    st.subheader(f"📝 Descriptor: {st.session_state.nombre_cargo}")
    with st.expander("Ver descriptor completo"):
        st.text_area("", st.session_state.descriptor, height=150, label_visibility="collapsed")
    st.info(f"📌 **Resumen del Descriptor:**
{st.session_state.resumen_descriptor}")

    st.divider()
    st.subheader("📄 Carga los CVs en PDF")
    archivos_cv = st.file_uploader("Selecciona uno o varios archivos", type=["pdf"], accept_multiple_files=True)

    if archivos_cv:
        st.session_state.archivos_cv = archivos_cv
        if st.button("🔍 Analizar CVs"):
            resultados, resumen = [], []
            for archivo in archivos_cv:
                texto = extraer_texto_pdf(archivo)
                if texto.startswith("❌"):
                    st.error(f"{archivo.name}: {texto}")
                    continue
                with st.spinner(f"Analizando {archivo.name}..."):
                    analisis = analizar_cv(st.session_state.descriptor, texto)
                    resultados.append({
                        "nombre": archivo.name,
                        "texto": analisis["texto"],
                        "nota": analisis["nota"]
                    })
                    resumen.append({
                        "Nombre CV": archivo.name,
                        "Cargo": st.session_state.nombre_cargo,
                        "Nota de Afinidad": analisis["nota"]
                    })
                st.success(f"✅ CV '{archivo.name}' analizado con éxito")
            st.session_state.resultados = resultados
            st.session_state.resumen = resumen
            st.experimental_rerun()

if st.session_state.get("resultados"):
    st.divider()
    st.subheader("📊 Ranking Visual de Afinidad")
    mostrar_grafico_ranking(st.session_state.resumen)

    st.divider()
    st.subheader("📥 Exportar Resultados")
    col1, col2 = st.columns(2)
    with col1:
        df = pd.DataFrame(st.session_state.resumen)
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button("📊 Descargar Excel", excel_buffer, file_name=f"Resumen Afinidad - {st.session_state.nombre_cargo}.xlsx")
    with col2:
        word_data, word_name = generar_word(st.session_state.resultados, st.session_state.nombre_cargo)
        st.download_button("📄 Descargar Word", word_data, file_name=word_name)
