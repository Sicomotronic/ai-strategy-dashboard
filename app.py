import os
import json
import time
from datetime import datetime
import streamlit as st
from google import genai

# 1. Setup API Authentication
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
client = genai.Client()

PROFILES_FILE = "user_profiles_streamlit.json"

# --- Database Helper Functions ---
def load_all_profiles():
    if not os.path.exists(PROFILES_FILE):
        return {}
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_all_profiles(profiles):
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=4, ensure_ascii=False)

def cleanup_profile(username):
    profiles = load_all_profiles()
    if username in profiles and profiles[username].get("metadata", {}).get("is_temporary", False):
        del profiles[username]
        save_all_profiles(profiles)

def check_topic_relevance(original_topic, follow_up_prompt):
    verification_prompt = (
        f"Analyze if this follow-up message is relevant to the core topic of: '{original_topic}'.\n"
        f"Follow-up message: '{follow_up_prompt}'.\n"
        f"Respond with exactly one word: 'YES' if it is relevant, or 'NO' if it goes off topic."
    )
    try:
        res = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=verification_prompt,
        )
        return "YES" in res.text.upper()
    except Exception:
        return True

# --- Initialize App Session State Variables ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "active_strategy" not in st.session_state:
    st.session_state.active_strategy = None
if "questions_left" not in st.session_state:
    st.session_state.questions_left = 5
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- UI Layout Layout ---
st.set_page_config(page_title="AI Custom Control Engine", layout="centered")
st.title("⚡ AI Control Dashboard & Strategy Engine")

# --- App Explanation Header ---
with st.expander("ℹ️ Click to see how this system works behind the scenes"):
    st.markdown("""
    * **Multi-Profile Core:** Tracks assets dynamically per user name.
    * **Asset Matrix Injection:** Constrains the AI to only build strategies with gear you actually own.
    * **Guardrail Tracking Loop:** Evaluates context and gives you a strict 5-question limit per strategy thread.
    """)

# --- Sidebar: User Authentication ---
st.sidebar.header("👤 Profile Connection Portal")

profiles = load_all_profiles()
permanent_users = [u for u, d in profiles.items() if not d.get("metadata", {}).get("is_temporary", False)]

login_option = st.sidebar.radio("Navigation Actions", ["Log In", "Create Permanent Profile", "Guest Session (One-Time)"])

if login_option == "Log In":
    if not permanent_users:
        st.sidebar.warning("No permanent accounts stored locally.")
    else:
        selected_user = st.sidebar.selectbox("Choose Profile", permanent_users)
        if st.sidebar.button("Connect Session"):
            st.session_state.current_user = selected_user
            st.session_state.active_strategy = None
            st.session_state.chat_history = []
            st.session_state.questions_left = 5
            st.sidebar.success(f"Connected to {selected_user}!")

elif login_option == "Create Permanent Profile":
    new_name = st.sidebar.text_input("Unique Username").strip()
    new_age = st.sidebar.text_input("Age")
    new_loc = st.sidebar.text_input("Location (e.g., Barcelona, Spain)")
    new_cap = st.sidebar.text_input("Starting Capital (e.g., 10 euros)")
    new_goal = st.sidebar.text_input("Financial Target (e.g., 10k)")
    new_time = st.sidebar.text_input("Timeframe (e.g., one month)")
    
    st.sidebar.markdown("**Asset Inventory Checklist:**")
    has_laptop = st.sidebar.checkbox("Laptop/Computer Access")
    has_phone = st.sidebar.checkbox("Smartphone Access")
    has_net = st.sidebar.checkbox("Stable High-Speed Internet")
    has_wheels = st.sidebar.checkbox("Micro-Mobility (Bike/Escooter/Motorbike)")
    has_pass = st.sidebar.checkbox("Public Transport Card")

    if st.sidebar.button("Compile & Save Profile"):
        if new_name and new_name not in profiles:
            profiles[new_name] = {
                "metadata": {
                    "age": new_age, "location": new_loc, "starting_capital": new_cap,
                    "target_goal": new_goal, "timeframe": new_time, "is_temporary": False,
                    "assets": {
                        "has_laptop": has_laptop, "has_phone": has_phone,
                        "has_stable_internet": has_net, "has_bike_or_escooter": has_wheels,
                        "has_transport_card": has_pass
                    }
                },
                "logs": []
            }
            save_all_profiles(profiles)
            st.session_state.current_user = new_name
            st.sidebar.success(f"Profile '{new_name}' Compiled!")
        else:
            st.sidebar.error("Invalid name or username already exists.")

elif login_option == "Guest Session (One-Time)":
    st.sidebar.info("Data will be fully wiped from cache upon exiting.")
    g_age = st.sidebar.text_input("Age (Guest)")
    g_loc = st.sidebar.text_input("Location (Guest)")
    g_cap = st.sidebar.text_input("Capital (Guest)")
    g_goal = st.sidebar.text_input("Target (Guest)")
    g_time = st.sidebar.text_input("Timeframe (Guest)")
    
    has_laptop = st.sidebar.checkbox("Laptop/Computer Access (Guest)")
    has_phone = st.sidebar.checkbox("Smartphone Access (Guest)")
    has_net = st.sidebar.checkbox("Stable Internet (Guest)")
    has_wheels = st.sidebar.checkbox("Micro-Mobility (Guest)")
    has_pass = st.sidebar.checkbox("Public Transport Card (Guest)")

    if st.sidebar.button("Launch Guest Engine"):
        g_name = f"guest_{int(time.time())}"
        profiles[g_name] = {
            "metadata": {
                "age": g_age, "location": g_loc, "starting_capital": g_cap,
                "target_goal": g_goal, "timeframe": g_time, "is_temporary": True,
                "assets": {
                    "has_laptop": has_laptop, "has_phone": has_phone,
                    "has_stable_internet": has_net, "has_bike_or_escooter": has_wheels,
                    "has_transport_card": has_pass
                }
            },
            "logs": []
        }
        save_all_profiles(profiles)
        st.session_state.current_user = g_name
        st.session_state.active_strategy = None
        st.session_state.chat_history = []
        st.session_state.questions_left = 5
        st.sidebar.success("Guest Engine Fired!")

# --- Disconnect / Logout Action ---
if st.session_state.current_user:
    if st.sidebar.button("🔴 Disconnect Session"):
        cleanup_profile(st.session_state.current_user)
        st.session_state.current_user = None
        st.session_state.active_strategy = None
        st.session_state.chat_history = []
        st.rerun()

# --- Main Dynamic Panel Code ---
if not st.session_state.current_user:
    st.warning("⚠️ Access Denied. Please connect or compile a profile in the sidebar portal to boot operations.")
else:
    st.info(st.session_state.current_user)
    
    # Action 1: Core Engine Execution Trigger
    if st.button("🚀 Run Strategy Engine Generation"):
        active_profiles = load_all_profiles()
        meta = active_profiles[st.session_state.current_user]["metadata"]
        assets = meta["assets"]
        
        asset_summary = (
            f"- Laptop/Computer: {'Yes' if assets['has_laptop'] else 'No'}\n"
            f"- Smartphone: {'Yes' if assets['has_phone'] else 'No'}\n"
            f"- High Speed Connection: {'Yes' if assets['has_stable_internet'] else 'No'}\n"
            f"- Personal Wheels/Micro-Mobility: {'Yes' if assets['has_bike_or_escooter'] else 'No'}\n"
            f"- Transport Pass Availability: {'Yes' if assets['has_transport_card'] else 'No'}"
        )
        
        user_prompt = (
            f"Tell me a business strategy to legitimately convert {meta['starting_capital']} "
            f"into {meta['target_goal']} in {meta['timeframe']} as a {meta['age']} year old guy living in {meta['location']}.\n\n"
            f"CRITICAL ASSET ENVIRONMENT CONSTRAINTS:\n"
            f"The user ONLY has the following tools and logistical assets available to deploy:\n{asset_summary}\n\n"
            f"Do not suggest strategies requiring tools marked as 'No'."
        )
        
        with st.spinner("Streaming calculations from engine matrix..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_prompt,
                )
                st.session_state.active_strategy = response.text
                st.session_state.questions_left = 5
                st.session_state.chat_history = []
            except Exception as e:
                st.error(f"Execution Error: {e}")

    # Display Strategy Output & Handle Follow-up Telemetry Thread Loops
    if st.session_state.active_strategy:
        st.subheader("📋 Generated Business Strategy Architecture")
        st.write(st.session_state.active_strategy)
        
        st.markdown("---")
        st.subheader("💬 Contextual Telemetry Thread")
        st.write(f"Remaining Questions Allowed: **{st.session_state.questions_left}**")
        
        # Render historical messages in thread layout style
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["text"])
                
        if st.session_state.questions_left > 0:
            follow_up_input = st.text_input("Ask a follow-up question regarding this strategy context:", key="follow_up_input_field")
            
            if st.button("Submit Context Question"):
                if follow_up_input:
                    # Guardrail check verification loop logic
                    is_relevant = check_topic_relevance(st.session_state.active_strategy[:200], follow_up_input)
                    
                    if not is_relevant:
                        st.error("🛑 Guardrail Warning: Off-topic detection triggered. Please reframe input to match active strategy parameters.")
                    else:
                        st.session_state.chat_history.append({"role": "user", "text": follow_up_input})
                        
                        contextual_prompt = (
                            f"Context of original business strategy:\n{st.session_state.active_strategy}\n\n"
                            f"User's specific follow-up question:\n{follow_up_input}"
                        )
                        
                        with st.spinner("Processing thread response..."):
                            try:
                                response = client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=contextual_prompt,
                                )
                                st.session_state.chat_history.append({"role": "assistant", "text": response.text})
                                st.session_state.questions_left -= 1
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            st.success("🔒 Topic session lock achieved. Max query limits filled successfully.")
            if st.button("Reset Strategy Framework Thread"):
                st.session_state.active_strategy = None
                st.session_state.chat_history = []
                st.session_state.questions_left = 5
                st.rerun()
