
# 🤖 SelecTalent - Análisis Inteligente de CVs con IA

**SelecTalent** es una aplicación creada para agilizar el proceso de reclutamiento y selección, utilizando inteligencia artificial para analizar currículums, compararlos con el perfil del cargo y entregar un ranking visual de afinidad en escala 1 a 10.  

Desarrollada con ❤️ en Python + Streamlit + OpenAI.

---

## ✨ Funcionalidades

✅ Subir uno o varios CVs en PDF  
✅ Cargar un descriptor de cargo (PDF o TXT) o generarlo mediante preguntas  
✅ Análisis automatizado: Fortalezas, Debilidades y Nota de Afinidad  
✅ Exportación de resultados a Excel 📊 y Word 📄  
✅ Ranking visual por afinidad (1–10)  
✅ Botón de reinicio para evaluar otro cargo 🔁  

---

## 🛠️ Requisitos

- Python 3.8 o superior
- Cuenta en [OpenAI](https://platform.openai.com) con API Key
- Librerías:
  - `streamlit`
  - `openai`
  - `PyMuPDF`
  - `pandas`
  - `python-docx`
  - `plotly`

Instalación rápida:

```bash
pip install -r requirements.txt
```

---

## 🚀 ¿Cómo usar?

1. Clona el repositorio:
```bash
git clone https://github.com/tuusuario/selec-talent.git
cd selec-talent
```

2. Crea el archivo de configuración `secrets.toml`:

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "tu-api-key-de-openai"
```

3. Corre la app:
```bash
streamlit run app_cv_matcher_fixed.py
```

---

## 📦 Exports

- **Excel**: resumen con nombre del CV, cargo, nota de afinidad  
- **Word**: análisis completo, dividido por candidato en páginas separadas

---

## 💡 Inspiración

Esta herramienta fue creada para resolver un dolor clásico en el reclutamiento: **revisar decenas o cientos de CVs manualmente**. Con SelecTalent, ahorras tiempo y tomas decisiones basadas en datos.

---

## 🤝 Contribuye

¿Tienes ideas para mejorarla? ¿Quieres integraciones con LinkedIn o guardar candidatos en base de datos? ¡Abramos un issue o un pull request!

---

## 🧠 Desarrollado por

Enzo Giraud · [@enzogiraud](https://github.com/enzogiraud)  
Mentoría IA: ChatGPT + cariño chileno 🇨🇱
