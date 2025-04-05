import streamlit as st
from openai import OpenAI
import fitz
import pandas as pd
from docx import Document
from io import BytesIO
import re
import plotly.express as px

# Configuracion inicial
st.set_page_config(page_title="Bienvenido/a a SelecTalent", layout="centered")
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

def generar_resumen_descriptor(descriptor):
    prompt = f"""
Lee el siguiente descriptor de cargo y entrega un resumen breve de su contenido. El resumen debe explicar qué perfil se busca, qué conocimientos y habilidades se requieren, y cualquier detalle relevante:

{descriptor}
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
    contenido = response.choices[0].message.content.strip()
    fortalezas = extraer_bloque(contenido, "Fortalezas")
    debilidades = extraer_bloque(contenido, "Debilidades")
    nota = extraer_nota(contenido)
    return {
        "texto": contenido,
        "fortalezas": fortalezas,
        "debilidades": debilidades,
        "nota": nota
    }

def extraer_bloque(texto, titulo):
    patron = rf"{titulo}:\n(.*?)\n(?:\w|\Z)"
    match = re.search(patron, texto, re.DOTALL)
    return match.group(1).strip() if match else ""

def extraer_nota(texto):
    match = re.search(r"Nota de afinidad.*?(\d+)", texto)
    return int(match.group(1)) if match else 0

def generar_word(resultados, nombre_cargo):
    doc = Document()
    doc.add_heading(f"Detalle de Análisis para el Cargo: {nombre_cargo}", level=1)
    doc.add_paragraph("Este documento contiene el análisis individual de los postulantes evaluados por la IA.\n")
    doc.add_page_break()
    for r in resultados:
        doc.add_heading(r["nombre"], level=2)
        doc.add_paragraph(r["texto"])
        doc.add_page_break()
    word_buffer = BytesIO()
    doc.save(word_buffer)
    word_buffer.seek(0)
    return word_buffer, f"Detalle ({nombre_cargo}).docx"

def chat_asesor():
    st.subheader("💬 Asesor IA para Reclutadores")
    st.markdown("Escribe una pregunta relacionada con el proceso de selección y la IA responderá como si fuera un experto en reclutamiento.")
    consulta = st.text_input("¿En qué necesitas ayuda?")
    if st.button("🤖 Consultar IA") and consulta.strip():
        with st.spinner("Analizando tu consulta..."):
            prompt = f"Actúa como un asesor experto en reclutamiento y responde a la siguiente pregunta de forma clara, útil y profesional: {consulta}"
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            st.success("✅ Respuesta generada")
            st.info(response.choices[0].message.content.strip())

# Interfaz Chat Asesor al final
if st.session_state.get("descriptor") and st.session_state.get("resultados"):
    st.divider()
    chat_asesor()
