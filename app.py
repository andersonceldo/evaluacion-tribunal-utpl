import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2 import service_account
import os

# === CONFIGURACIÓN ===
ESTUDIANTES_FILE = "estudiantes.csv"
EVALUADORES_FILE = "evaluadores.csv"
GOOGLE_SHEET_ID = "1OhYdsqSuDCrPuO8TxzbTbGqY3nyrJjJwQaCgV_cvjOU"

# Cargar datos
@st.cache_data
def cargar_estudiantes():
    if os.path.exists(ESTUDIANTES_FILE):
        df = pd.read_csv(ESTUDIANTES_FILE, encoding='utf-8')
        # Normalizar correos
        df['CORREO PRESIDENTE'] = df['CORREO PRESIDENTE'].str.strip().str.lower()
        return df
    else:
        st.error("Archivo 'estudiantes.csv' no encontrado.")
        return pd.DataFrame()

@st.cache_data
def cargar_evaluadores():
    if os.path.exists(EVALUADORES_FILE):
        df = pd.read_csv(EVALUADORES_FILE)
        return df["correo"].str.strip().str.lower().tolist()
    return []

# Conectar a Google Sheets
@st.cache_resource
def conectar_sheets():
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    except:
        # Para pruebas locales
        credentials = service_account.Credentials.from_service_account_file(
            "service_account.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    client = gspread.authorize(credentials)
    return client.open_by_key(GOOGLE_SHEET_ID).sheet1

# Inicializar estado
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.correo = ""
    st.session_state.estudiantes_asignados = []
    st.session_state.estudiante_seleccionado = None

# === PANTALLA DE LOGIN ===
if not st.session_state.autenticado:
    st.title("🔐 Sistema de Evaluación - Tribunal UTPL")
    st.subheader("Ingrese con su correo institucional (@utpl.edu.ec)")

    correo = st.text_input("Correo institucional")
    if st.button("Ingresar"):
        evaluadores = cargar_evaluadores()
        correo_limpio = correo.strip().lower()
        if correo_limpio in evaluadores and correo_limpio.endswith("@utpl.edu.ec"):
            st.session_state.autenticado = True
            st.session_state.correo = correo_limpio

            # Filtrar estudiantes asignados a este presidente
            df_estudiantes = cargar_estudiantes()
            asignados = df_estudiantes[df_estudiantes['CORREO PRESIDENTE'] == correo_limpio]

            if len(asignados) == 0:
                st.warning("No tiene estudiantes asignados.")
            else:
                st.session_state.estudiantes_asignados = asignados.to_dict('records')
                st.rerun()
        else:
            st.error("❌ Acceso denegado. Solo presidentes del tribunal pueden ingresar.")

else:
    # === SELECCIÓN DE ESTUDIANTE ===
    st.title("📋 Evaluación del Trabajo de Integración Curricular")
    st.markdown(f"**Evaluador:** {st.session_state.correo}")

    if len(st.session_state.estudiantes_asignados) == 0:
        st.info("No tiene estudiantes asignados para evaluar.")
        if st.button("Cerrar sesión"):
            st.session_state.autenticado = False
            st.session_state.correo = ""
            st.session_state.estudiantes_asignados = []
            st.rerun()
    else:
        # Mostrar lista de estudiantes
        nombres_estudiantes = [
            f"{row['APELLIDOS Y NOMBRES']} - {row['TITULACION']} ({row['HORA']})"
            for row in st.session_state.estudiantes_asignados
        ]

        seleccion = st.selectbox("Seleccione el estudiante a evaluar:", nombres_estudiantes)
        indice = nombres_estudiantes.index(seleccion)
        estudiante = st.session_state.estudiantes_asignados[indice]

        st.markdown("### 🧑‍🎓 Estudiante seleccionado")
        st.write(f"**Nombre:** {estudiante['APELLIDOS Y NOMBRES']}")
        st.write(f"**Cédula:** {estudiante['CEDULA']}")
        st.write(f"**Titulación:** {estudiante['TITULACION']}")
        st.write(f"**Hora:** {estudiante['HORA']}")
        st.write(f"**Fecha:** {estudiante['FECHA']}")

        # Rúbrica
        criterios = [
            ("Calidad y adecuada utilización del material de apoyo audiovisual o gráfico presentado", 0.05),
            ("Precisión y clara exposición oral", 0.25),
            ("Centra su intervención sobre los aspectos fundamentales del trabajo de integración curricular", 0.3),
        ]
        subcriterios = [
            ("a) Introducción/Antecedentes, justificación y objetivos", 0.1),
            ("b) Metodología", 0.1),
            ("c) Resultados, discusión, conclusiones y recomendaciones", 0.2),
        ]

        calificaciones = {}
        total = 0.0

        st.markdown("### 📊 Criterios de evaluación")
        for nombre, peso in criterios:
            valor = st.slider(f"{nombre} (peso: {peso})", 0.0, 10.0, 5.0, 0.1, key=nombre)
            calificaciones[nombre] = valor
            total += valor * peso

        for nombre, peso in subcriterios:
            valor = st.slider(f"{nombre} (peso: {peso})", 0.0, 10.0, 5.0, 0.1, key=nombre)
            calificaciones[nombre] = valor
            total += valor * peso

        st.markdown("### 📈 Resultado Final")
        st.metric("Calificación Total", f"{total:.2f}/10.00")

        # Botones
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Guardar en Google Sheets"):
                try:
                    sheet = conectar_sheets()

                    # Encabezados (solo primera vez)
                    if not sheet.acell("A1").value:
                        headers = [
                            "correo_evaluador", "cedula", "nombre_estudiante", "titulacion", "hora", "fecha",
                            "calidad_material", "precision_exposicion", "centrado_tema",
                            "introduccion", "metodologia", "resultados", "calificacion_total"
                        ]
                        sheet.append_row(headers)

                    # Datos
                    fila = [
                        st.session_state.correo,
                        estudiante['CEDULA'],
                        estudiante['APELLIDOS Y NOMBRES'],
                        estudiante['TITULACION'],
                        estudiante['HORA'],
                        estudiante['FECHA']
                    ]
                    # Agregar calificaciones en orden
                    fila.extend([
                        calificaciones.get("Calidad y adecuada utilización del material de apoyo audiovisual o gráfico presentado", 0),
                        calificaciones.get("Precisión y clara exposición oral", 0),
                        calificaciones.get("Centra su intervención sobre los aspectos fundamentales del trabajo de integración curricular", 0),
                        calificaciones.get("a) Introducción/Antecedentes, justificación y objetivos", 0),
                        calificaciones.get("b) Metodología", 0),
                        calificaciones.get("c) Resultados, discusión, conclusiones y recomendaciones", 0),
                        round(total, 2)
                    ])

                    sheet.append_row(fila)
                    st.success("✅ Evaluación guardada correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")

        with col2:
            if st.button("🚪 Regresar al menú inicial"):
                st.session_state.autenticado = False
                st.session_state.correo = ""
                st.session_state.estudiantes_asignados = []
                st.session_state.estudiante_seleccionado = None
                st.rerun()
