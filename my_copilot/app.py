from dotenv import load_dotenv, find_dotenv
import os

# Load environment variables from current or parent directories
load_dotenv(find_dotenv())

# Page config
st.set_page_config(
    page_title="Мой Второй Пилот",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for mobile-like feel
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        height: 60px;
        border-radius: 15px;
        font-size: 20px;
        font-weight: bold;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    h1 {
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 20px;
    }
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Navigation
if 'page' not in st.session_state:
    st.session_state.page = "advisor"

def navigate_to(page):
    st.session_state.page = page

# Sidebar
with st.sidebar:
    st.title("Меню")
    if st.button("🧠 Умный Советчик"):
        navigate_to("advisor")
    if st.button("👁️ Зоркий Глаз"):
        navigate_to("vision")
    if st.button("🧘 Спокойный Маршрут"):
        navigate_to("route")

# Main Content
if st.session_state.page == "advisor":
    st.title("🧠 Умный Советчик")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Что случилось?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            try:
                from utils.ai_text import get_text_advice
                # Prepare history for API (exclude system prompt if it's handled in get_text_advice)
                # We pass the full history to the function
                response = get_text_advice(prompt, st.session_state.messages[:-1])
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except ImportError:
                 st.error("Ошибка импорта AI модуля.")
            except Exception as e:
                 st.error(f"Ошибка: {e}")

elif st.session_state.page == "vision":
    st.title("👁️ Зоркий Глаз")
    st.write("Сфотографируй приборную панель.")
    
    picture = st.camera_input("Сделать фото")
    
    if picture:
        st.image(picture, caption="Снимок")
        with st.spinner("Анализирую приборную панель..."):
            try:
                from utils.ai_vision import analyze_dashboard
                result = analyze_dashboard(picture)
                if "СТОП" in result:
                    st.error(result)
                else:
                    st.success(result)
            except ImportError:
                st.error("Ошибка импорта модуля Vision.")
            except Exception as e:
                st.error(f"Ошибка: {e}")

elif st.session_state.page == "route":
    st.title("🧘 Спокойный Маршрут")
    st.write("Куда едем спокойно?")
    
    start = st.text_input("Откуда", placeholder="Например: Дом")
    end = st.text_input("Куда", placeholder="Например: Работа")
    
    if st.button("Построить маршрут"):
        if start and end:
            with st.spinner("Прокладываю самый спокойный путь..."):
                try:
                    from utils.navigation import get_calm_route_advice
                    advice, link = get_calm_route_advice(start, end)
                    
                    st.success("Маршрут готов!")
                    st.write(advice)
                    
                    if link:
                        st.link_button("🗺️ Открыть в Google Картах", link)
                        
                except ImportError:
                    st.error("Ошибка импорта модуля навигации.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        else:
            st.warning("Пожалуйста, введите обе точки маршрута.")
