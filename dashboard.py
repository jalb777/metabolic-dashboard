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

def calculate_metabolic_fitness(df):
    """Calculates Chronic Load (Fitness), Acute Load (Fatigue), and TSB (Form)"""
    if df.empty or 'Recovery_Min' not in df.columns:
        return pd.DataFrame()

    df_copy = df.copy()
    
    # Custom Load Multipliers (Adjust these based on how your legs feel!)
    df_copy['Training_Load'] = (
        df_copy.get('Recovery_Min', 0) * 1.0 +
        df_copy.get('LT1_Min', 0) * 2.0 +
        df_copy.get('LT2_Min', 0) * 4.0 +
        df_copy.get('VO2_Min', 0) * 6.0
    )

    daily_log = df_copy.groupby('Date')['Training_Load'].sum().reset_index()
    daily_log['Date'] = pd.to_datetime(daily_log['Date'])
    daily_log.set_index('Date', inplace=True)

    # Fill empty days with 0 load so fatigue naturally decays on rest days
    if not daily_log.empty:
        idx = pd.date_range(daily_log.index.min(), daily_log.index.max())
        daily_log = daily_log.reindex(idx, fill_value=0)

    # Exponentially Weighted Moving Averages
    daily_log['Fitness'] = daily_log['Training_Load'].ewm(span=42, adjust=False).mean()
    daily_log['Fatigue'] = daily_log['Training_Load'].ewm(span=7, adjust=False).mean()
    daily_log['Form'] = daily_log['Fitness'] - daily_log['Fatigue']

    return daily_log.reset_index().rename(columns={'index': 'Date'})

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
menu = st.sidebar.radio("Go to:", ["📊 Dashboard", "➕ Add Manual Run", "🩸 Log Lactate Test"])

# ==========================================
# 📊 DASHBOARD VIEW
# ==========================================
if menu == "📊 Dashboard":
    runs_df = load_data(RUN_LOG)
    
    if not runs_df.empty and 'Date' in runs_df.columns:
        runs_df['Date'] = pd.to_datetime(runs_df['Date'])
        runs_df = runs_df.sort_values('Date')
        
        # --- CHART 1: METABOLIC VOLUME ---
        st.subheader("Seasonal Volume Trends")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(runs_df['Date'].dt.strftime('%m-%d'), runs_df['Recovery_Min'], label='Recovery', color='gray', alpha=0.6)
        
        bottom_val = runs_df['Recovery_Min'].copy()
        if 'LT1_Min' in runs_df.columns:
            ax.bar(runs_df['Date'].dt.strftime('%m-%d'), runs_df['LT1_Min'], bottom=bottom_val, label='LT1', color='green', alpha=0.6)
            bottom_val += runs_df['LT1_Min']
        if 'LT2_Min' in runs_df.columns:
            ax.bar(runs_df['Date'].dt.strftime('%m-%d'), runs_df['LT2_Min'], bottom=bottom_val, label='LT2', color='orange', alpha=0.8)
        
        ax.set_ylabel("Minutes")
        ax.legend(loc='upper left')
        plt.xticks(rotation=45)
        st.pyplot(fig)
        
        st.divider()

        # --- CHART 2: FITNESS & FRESHNESS MODEL ---
        st.subheader("Impulse-Response Model (Fitness & Form)")
        fitness_df = calculate_metabolic_fitness(runs_df)
        
        if not fitness_df.empty:
            fig_fit, ax_fit = plt.subplots(figsize=(10, 5))
            
            # Plot the engine and the fatigue
            ax_fit.plot(fitness_df['Date'], fitness_df['Fitness'], label='Fitness (42-Day)', color='blue', linewidth=2)
            ax_fit.plot(fitness_df['Date'], fitness_df['Fatigue'], label='Fatigue (7-Day)', color='red', linewidth=1.5, linestyle='--')
            
            # Shade the Form (Training Stress Balance)
            ax_fit.fill_between(fitness_df['Date'], 0, fitness_df['Form'], where=(fitness_df['Form'] >= 0), color='green', alpha=0.3, label='Fresh (Ready to Race)')
            ax_fit.fill_between(fitness_df['Date'], 0, fitness_df['Form'], where=(fitness_df['Form'] < 0), color='orange', alpha=0.3, label='Tired (Heavy Training)')
            
            ax_fit.axhline(0, color='black', linewidth=1)
            ax_fit.set_ylabel("Training Load Score")
            ax_fit.legend(loc='upper left')
            plt.xticks(rotation=45)
            st.pyplot(fig_fit)
        
    else:
        st.info("📊 Your training log is currently empty. Go to 'Add Manual Run' or sync a workout to see your charts build up!")

    st.divider()
    
    # --- CHART 3: LACTATE CURVE ---
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