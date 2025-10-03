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

# === CARGA DE DATOS ===
@st.cache_data
def cargar_evaluadores():
    if os.path.exists(EVALUADORES_FILE):
        try:
            df = pd.read_csv(EVALUADORES_FILE, encoding='utf-8')
        except Exception:
            df = pd.read_csv(EVALUADORES_FILE, encoding='latin-1')
        return df["correo"].str.strip().str.lower().tolist()
    return []

@st.cache_data
def cargar_estudiantes():
    if os.path.exists(ESTUDIANTES_FILE):
        try:
            df = pd.read_csv(
                ESTUDIANTES_FILE,
                sep=";",
                encoding='utf-8',
                skipinitialspace=True,
                quotechar='"'
            )
        except Exception:
            try:
                df = pd.read_csv(
                    ESTUDIANTES_FILE,
                    sep=";",
                    encoding='latin-1',
                    skipinitialspace=True,
                    quotechar='"'
                )
            except Exception as e:
                st.error(f"Error al leer estudiantes.csv: {e}")
                return pd.DataFrame()
        
        # Limpiar nombres de columnas
        df.columns = df.columns.str.strip()
        
        # Manejar el salto de línea en el encabezado problemático
        for col in df.columns:
            if "OPCION DE TITULACION" in col.upper():
                df.rename(columns={col: "OPCION DE TITULACION"}, inplace=True)
                break
        
        if "CORREO PRESIDENTE" not in df.columns:
            st.error(f"❌ Columnas disponibles: {list(df.columns)}")
            return pd.DataFrame()
        
        df["CORREO PRESIDENTE"] = df["CORREO PRESIDENTE"].astype(str).str.strip().str.lower()
        return df
    else:
        st.error("Archivo 'estudiantes.csv' no encontrado.")
        return pd.DataFrame()

@st.cache_data(ttl=30)
def cargar_evaluaciones_guardadas(correo_evaluador):
    """Carga las evaluaciones ya guardadas por este evaluador desde Google Sheets"""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if "correo_evaluador" in df.columns:
            return df[df["correo_evaluador"] == correo_evaluador]
        return pd.DataFrame()
    except Exception as e:
        st.warning("No se pudieron cargar evaluaciones previas.")
        return pd.DataFrame()

@st.cache_resource
def conectar_sheets():
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]  # ← sin espacios
        )
        client = gspread.authorize(credentials)
        return client.open_by_key(GOOGLE_SHEET_ID).sheet1
    except Exception as e:
        st.error(f"❌ Error de autenticación: {str(e)}")
        st.info("Verifique que los Secrets estén correctamente configurados.")
        return None

# === INICIALIZAR SESIÓN ===
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.correo = ""
    st.session_state.estudiantes_asignados = []

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

            # Cargar estudiantes asignados
            df_estudiantes = cargar_estudiantes()
            if df_estudiantes.empty:
                st.error("No se pudieron cargar los datos de estudiantes.")
                st.session_state.autenticado = False
            else:
                asignados = df_estudiantes[df_estudiantes['CORREO PRESIDENTE'] == correo_limpio].copy()

                # Excluir ya calificados
                evaluaciones_hechas = cargar_evaluaciones_guardadas(correo_limpio)
                if not evaluaciones_hechas.empty and not asignados.empty:
                    cedulas_hechas = set(evaluaciones_hechas["cedula"].astype(str))
                    asignados = asignados[~asignados["CEDULA"].astype(str).isin(cedulas_hechas)]

                st.session_state.estudiantes_asignados = asignados.to_dict('records')
                st.rerun()
        else:
            st.error("❌ Acceso denegado. Solo presidentes del tribunal pueden ingresar.")
else:
    # === PANEL PRINCIPAL ===
    st.title("📋 Evaluación del Trabajo de Integración Curricular")
    st.markdown(f"**Evaluador:** {st.session_state.correo}")

    # Botón para ver evaluaciones anteriores
    if st.button("📊 Ver evaluaciones ya calificadas"):
        evaluaciones_hechas = cargar_evaluaciones_guardadas(st.session_state.correo)
        if evaluaciones_hechas.empty:
            st.info("No ha calificado a ningún estudiante aún.")
        else:
            st.subheader("Evaluaciones realizadas")
            cols_mostrar = ["nombre_estudiante", "titulacion", "hora", "fecha", "calificacion_total"]
            if all(col in evaluaciones_hechas.columns for col in cols_mostrar):
                st.dataframe(
                    evaluaciones_hechas[cols_mostrar].sort_values("fecha", ascending=False),
                    use_container_width=True
                )
            else:
                st.write(evaluaciones_hechas)

    # Mostrar estudiantes pendientes
    if len(st.session_state.estudiantes_asignados) == 0:
        st.info("No tiene estudiantes pendientes por evaluar.")
    else:
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
                sheet = conectar_sheets()
                if sheet is None:
                    st.error("No se puede guardar: error de conexión.")
                else:
                    try:
                        if not sheet.acell("A1").value:
                            headers = [
                                "correo_evaluador", "cedula", "nombre_estudiante", "titulacion", "hora", "fecha",
                                "calidad_material", "precision_exposicion", "centrado_tema",
                                "introduccion", "metodologia", "resultados", "calificacion_total"
                            ]
                            sheet.append_row(headers)

                        fila = [
                            st.session_state.correo,
                            str(estudiante['CEDULA']),
                            estudiante['APELLIDOS Y NOMBRES'],
                            estudiante['TITULACION'],
                            estudiante['HORA'],
                            estudiante['FECHA']
                        ]
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
                        # Eliminar estudiante de la lista actual
                        st.session_state.estudiantes_asignados = [
                            e for e in st.session_state.estudiantes_asignados
                            if e['CEDULA'] != estudiante['CEDULA']
                        ]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")

        with col2:
            if st.button("🚪 Regresar al menú inicial"):
                st.session_state.autenticado = False
                st.session_state.correo = ""
                st.session_state.estudiantes_asignados = []
                st.rerun()
