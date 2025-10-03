import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Sistema de Evaluación - Tribunal", layout="centered")

# Credenciales (solo presidente puede entrar)
USUARIO_VALIDO = "presidente"
CONTRASEÑA_VALIDA = "12345"  # Cambia esto por una más segura si lo deseas

# Estado de autenticación
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Pantalla de login
if not st.session_state.autenticado:
    st.title("🔐 Acceso Restringido")
    st.subheader("Solo para el Presidente del Tribunal")
    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario == USUARIO_VALIDO and contraseña == CONTRASEÑA_VALIDA:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
else:
    # === Pantalla principal de evaluación ===
    st.title("📋 Evaluación del Trabajo de Integración Curricular")
    st.markdown("### CRITERIOS DE EVALUACIÓN")

    # Definir criterios: (nombre, peso)
    criterios = [
        ("Calidad y adecuada utilización del material de apoyo audiovisual o gráfico presentado", 0.05),
        ("Dominio, comprensión y seguridad del tema", 0.0),  # Sin peso explícito → asumimos 0.0 (no se califica numéricamente)
        ("Precisión y clara exposición oral", 0.25),
        ("Centra su intervención sobre los aspectos fundamentales del trabajo de integración curricular", 0.3),
        ("Exactitud en la interpretación de las preguntas del equipo evaluador y seguridad de las respuestas", 0.0),  # Sin peso
        ("¿Las respuestas son adecuadas y correctas?", 0.0),  # Contiene subcriterios
    ]

    # Subcriterios con pesos
    subcriterios = [
        ("a) Introducción/Antecedentes, justificación y objetivos", 0.1),
        ("b) Metodología", 0.1),
        ("c) Resultados, discusión, conclusiones y recomendaciones", 0.2),
    ]

    calificaciones = {}
    total = 0.0

    # Criterios principales con peso
    st.markdown("#### Criterios generales")
    for nombre, peso in criterios:
        if peso > 0:
            valor = st.slider(
                f"{nombre} (peso: {peso})",
                min_value=0.0,
                max_value=10.0,
                value=5.0,
                step=0.1,
                key=nombre
            )
            ponderado = valor * peso
            calificaciones[nombre] = ponderado
            total += ponderado
            st.write(f"**Puntuación ponderada**: {ponderado:.2f}")
            st.divider()

    # Subcriterios
    st.markdown("#### Evaluación de respuestas (subcriterios)")
    for nombre, peso in subcriterios:
        valor = st.slider(
            f"{nombre} (peso: {peso})",
            min_value=0.0,
            max_value=10.0,
            value=5.0,
            step=0.1,
            key=nombre
        )
        ponderado = valor * peso
        calificaciones[nombre] = ponderado
        total += ponderado
        st.write(f"**Puntuación ponderada**: {ponderado:.2f}")
        st.divider()

    # Mostrar calificación total
    st.markdown("### 📊 Resultado Final")
    st.metric(label="Calificación Total", value=f"{total:.2f}/10.00")

    # Botón para cerrar sesión
    if st.button("Cerrar sesión"):
        st.session_state.autenticado = False
        st.rerun()
