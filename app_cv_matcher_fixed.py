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
  * Condiciones laborales (opcional)

Ejemplo de formato esperado:
"Descriptor para: Asistente Administrativo
Objetivo: Gestionar procesos administrativos...
Funciones:
1. Manejo de documentación (Alta importancia)
2. Atención al cliente (Muy Alta importancia)
...
Requisitos:
- Técnico en administración (Muy Alta relevancia)
- 2 años experiencia (Alta relevancia)..." """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7  # Para balancear creatividad y estructura
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
- Perfil ideal resumido

Ejemplo de formato requerido:
"Resumen: Analista de Datos
Funciones clave:
- Limpieza de datos (Prioridad: Muy Alta)
- Reportes mensuales (Prioridad: Alta)
Requisitos esenciales:
- Python (Relevancia: Muy Alta)
- SQL (Relevancia: Alta)
Perfil ideal: Profesional meticuloso con..." """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5  # Más estructurado que el descriptor completo
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
    return {
        "texto": texto,
        "nota": nota
    }
    
def extraer_nota(texto):
    # Buscar primero si ya existe una categoría textual
    categorias = ["Muy Alta", "Alta", "Media", "Baja", "Muy Baja"]
    for cat in categorias:
        if cat.lower() in texto.lower():
            return cat
    
    # Si no encuentra categoría textual, buscar nota numérica y convertir
    patrones_numericos = [
        r"(\d+)\s*\/\s*100",  # 60/100
        r"Nota\s*:\s*(\d+)",   # Nota: 6
        r"(\d+)\s*\/\s*10",    # 6/10
        r"\b(\d+)\b"           # 6
    ]
    
    for patron in patrones_numericos:
        match = re.search(patron, texto)
        if match:
            nota_num = float(match.group(1))
            # Convertir a categoría textual
            if "/100" in texto or "/ 100" in texto:
                nota_num = nota_num / 10  # Convertir escala 100 a 10
            
            if nota_num >= 9: return "Muy Alta"
            elif nota_num >= 7.5: return "Alta"
            elif nota_num >= 6: return "Media"
            elif nota_num >= 4: return "Baja"
            else: return "Muy Baja"
    
    return "Sin Clasificar"

def generar_word(resultados, nombre_cargo):
    doc = Document()
    doc.add_heading(f"Reporte de Análisis - {nombre_cargo}", level=1)
    
    # Orden de categorías para ordenar los resultados
    orden_afinidad = {"Muy Alta": 0, "Alta": 1, "Media": 2, "Baja": 3, "Muy Baja": 4}
    resultados_ordenados = sorted(resultados, key=lambda x: orden_afinidad.get(x["nota"], 5))
    
    for r in resultados_ordenados:
        doc.add_heading(r["nombre"], level=2)
        
        # Añadir categoría de afinidad con estilo destacado
        nivel_afinidad = r["nota"]
        doc.add_paragraph(f"Nivel de Afinidad: {nivel_afinidad}", style='Intense Quote')
        
        # Limpiar el texto si contiene notas numéricas
        texto_limpio = re.sub(r'\d+\s*\/\s*\d+', '', r["resultado"])  # Eliminar 60/100
        texto_limpio = re.sub(r'Nota\s*:\s*\d+', '', texto_limpio)    # Eliminar Nota: 6
        doc.add_paragraph(texto_limpio)
        
        doc.add_page_break()
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer, f"Reporte de Análisis - {nombre_cargo}.docx"

def mostrar_grafico_ranking(resumen):
    # Convertir a DataFrame y asegurar el orden categórico
    df = pd.DataFrame(resumen)
    orden_categorias = ["Muy Alta", "Alta", "Media", "Baja", "Muy Baja"]
    df["Nota de Afinidad"] = pd.Categorical(df["Nota de Afinidad"], categories=orden_categorias, ordered=True)
    
    # Crear el gráfico
    fig = px.bar(
        df.sort_values("Nota de Afinidad"),
        x="Nota de Afinidad",
        y="Nombre CV",
        color="Nota de Afinidad",
        color_discrete_map={
            "Muy Alta": "#2ecc71",
            "Alta": "#27ae60",
            "Media": "#f39c12",
            "Baja": "#e74c3c",
            "Muy Baja": "#c0392b"
        },
        orientation='h',
        title="Ranking de Afinidad por Categoría"
    )
    fig.update_layout(showlegend=False)
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
if st.session_state.archivos_cv:
    if st.button("🔍 Analizar CVs"):
        resultados, resumen = [], []
        for archivo in st.session_state.archivos_cv:
            texto = extraer_texto_pdf(archivo)
            if texto.startswith("❌"):
                st.error(f"{archivo.name}: {texto}")
                continue
            with st.spinner(f"Analizando {archivo.name}..."):
                analisis = analizar_cv(st.session_state.descriptor, texto)
                resultados.append({
                    "nombre": archivo.name,
                    "resultado": analisis["texto"],
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

# --- Exportación y Visualización ---
if st.session_state.resultados:
    st.divider()
    st.subheader("📊 Ranking Visual de Afinidad (Muy Alta → Muy Baja)")
    mostrar_grafico_ranking(st.session_state.resumen)

    st.divider()
    st.subheader("📥 Exportar Resultados")
    col1, col2 = st.columns(2)

    # EXCEL
    with col1:
        df = pd.DataFrame([
            {
                "Nombre CV": r["nombre"],
                "Cargo": st.session_state.nombre_cargo,
                "Nota de Afinidad": r["nota"]
            } for r in st.session_state.resultados
        ])
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            "📊 Descargar Excel",
            excel_buffer,
            file_name=f"Resumen Afinidad - {st.session_state.nombre_cargo}.xlsx"
        )

    # WORD
    with col2:
        word_data, word_name = generar_word(st.session_state.resultados, st.session_state.nombre_cargo)
        st.download_button(
            "📄 Descargar Word",
            word_data,
            file_name=word_name
        )
