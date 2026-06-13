import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Metabolic Training Hub", layout="wide")
st.title("🏃‍♂️ Metabolic Training Hub")

# --- FILE PATHS ---
RUN_LOG = 'seasonal_log.csv'
LACTATE_LOG = 'lactate_log.csv'

# --- HELPER FUNCTIONS ---
def load_data(filepath):
    if os.path.exists(filepath):
        try:
            return pd.read_csv(filepath)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def save_data(df, filepath):
    df.to_csv(filepath, index=False)

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
menu = st.sidebar.radio("Go to:", ["📊 Dashboard", "➕ Add Manual Run", "🩸 Log Lactate Test"])

# ==========================================
# 📊 DASHBOARD VIEW
# ==========================================
if menu == "📊 Dashboard":
    st.subheader("Seasonal Volume Trends")
    runs_df = load_data(RUN_LOG)
    
    if not runs_df.empty and 'Date' in runs_df.columns:
        runs_df['Date'] = pd.to_datetime(runs_df['Date'])
        runs_df = runs_df.sort_values('Date')
        
        # Plot stacked bar chart for zones
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(runs_df['Date'].dt.strftime('%m-%d'), runs_df['Recovery_Min'], label='Recovery', color='gray', alpha=0.6)
        
        # Stack others if columns exist
        bottom_val = runs_df['Recovery_Min'].copy()
        if 'LT1_Min' in runs_df.columns:
            ax.bar(runs_df['Date'].dt.strftime('%m-%d'), runs_df['LT1_Min'], bottom=bottom_val, label='LT1', color='green', alpha=0.6)
            bottom_val += runs_df['LT1_Min']
        if 'LT2_Min' in runs_df.columns:
            ax.bar(runs_df['Date'].dt.strftime('%m-%d'), runs_df['LT2_Min'], bottom=bottom_val, label='LT2', color='orange', alpha=0.8)
        
        ax.set_ylabel("Minutes")
        ax.legend()
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        st.dataframe(runs_df.tail(5))
    else:
        st.info("📊 Your training log is currently empty. Go to 'Add Manual Run' or sync a workout to see your charts build up!")

    st.divider()
    
    st.subheader("Lactate Curve Profile")
    lac_df = load_data(LACTATE_LOG)
    
    if not lac_df.empty and 'Heart_Rate' in lac_df.columns:
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.plot(lac_df['Heart_Rate'], lac_df['Lactate_mmol'], marker='o', color='red', linewidth=2)
        ax2.axhline(y=2.0, color='green', linestyle='--', alpha=0.5, label='LT1 Baseline (2.0 mmol)')
        ax2.axhline(y=4.0, color='orange', linestyle='--', alpha=0.5, label='LT2 Baseline (4.0 mmol)')
        ax2.set_xlabel("Heart Rate (BPM)")
        ax2.set_ylabel("Blood Lactate (mmol/L)")
        ax2.legend()
        ax2.grid(True, linestyle=':', alpha=0.6)
        st.pyplot(fig2)
        
        st.dataframe(lac_df)
    else:
        st.info("🩸 No blood lactate tests logged yet. Head over to the sidebar menu to log your first step-test interval values.")

# ==========================================
# ➕ ADD MANUAL RUN
# ==========================================
elif menu == "➕ Add Manual Run":
    st.subheader("Log a Treadmill or Untracked Workout")
    
    with st.form("manual_run_form"):
        date = st.date_input("Date")
        name = st.text_input("Workout Name", "Treadmill Recovery")
        rec_min = st.number_input("Recovery Minutes", min_value=0.0, step=1.0)
        lt1_min = st.number_input("LT1 Minutes", min_value=0.0, step=1.0)
        lt2_min = st.number_input("LT2 Minutes", min_value=0.0, step=1.0)
        vo2_min = st.number_input("VO2 Minutes", min_value=0.0, step=1.0)
        
        submitted = st.form_submit_button("Save Workout")
        
        if submitted:
            new_run = pd.DataFrame([{
                'Date': str(date), 'Activity_ID': 'Manual', 'Name': name,
                'Recovery_Min': rec_min, 'LT1_Min': lt1_min, 'LT2_Min': lt2_min, 'VO2_Min': vo2_min
            }])
            existing_runs = load_data(RUN_LOG)
            updated_runs = pd.concat([existing_runs, new_run], ignore_index=True)
            save_data(updated_runs, RUN_LOG)
            st.success("Manual run added to the database! Refresh the dashboard to see changes.")

# ==========================================
# 🩸 LOG LACTATE TEST
# ==========================================
elif menu == "🩸 Log Lactate Test":
    st.subheader("Input Blood Step-Test Data")
    
    with st.form("lactate_form"):
        date = st.date_input("Test Date")
        phase = st.text_input("Phase (e.g., Step 1, Step 2)", "Step 1")
        pace = st.text_input("Pace (e.g., 6:30)", "6:00")
        hr = st.number_input("Heart Rate (BPM)", min_value=40, max_value=220, step=1)
        lactate = st.number_input("Lactate (mmol/L)", min_value=0.0, step=0.1)
        
        submitted = st.form_submit_button("Save Data Point")
        
        if submitted:
            new_lac = pd.DataFrame([{
                'Date': str(date), 'Test_Phase': phase, 'Pace': pace, 'Heart_Rate': hr, 'Lactate_mmol': lactate
            }])
            existing_lac = load_data(LACTATE_LOG)
            updated_lac = pd.concat([existing_lac, new_lac], ignore_index=True)
            save_data(updated_lac, LACTATE_LOG)
            st.success(f"Logged {lactate} mmol/L at {hr} BPM!")