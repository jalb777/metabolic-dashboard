import pandas as pd
import numpy as np
from stravalib.client import Client

# 1. HARDWIRE YOUR CREDENTIALS
# Paste your actual details below!
CLIENT_ID = 256747  # No quotes
CLIENT_SECRET = '812d2a7b01d0e2efb084139152f1997db1a092cd' # Keep the quotes
REFRESH_TOKEN = '18eeeefcc8cdfab3f254cb0e2c05708cbe8a7510' # Keep the quotes

print("Generating a brand new access token...")

try:
    client = Client()
    # 2. Force a token refresh
    refresh_response = client.refresh_access_token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        refresh_token=REFRESH_TOKEN
    )
    
    # 3. Connect using the fresh token
    client.access_token = refresh_response['access_token']
    print("Connecting to Strava...")
    
    # --- SMART SEARCH LOGIC ---
    print("Scanning recent runs for physiological data...")
    activities = client.get_activities(limit=10)
    
    target_activity = None
    for act in activities:
        # Stop at the first activity that actually has HR sensor data
        if getattr(act, 'has_heartrate', False):
            target_activity = act
            break 
            
    if target_activity is None:
        print("\n--- FAILURE ---")
        print("Could not find any recent runs with heart rate data.")
        exit()
        
    print(f"\n--- SENSOR DATA FOUND ---")
    print(f"Targeting Activity: {target_activity.name} (ID: {target_activity.id})")
    
    # 4. Extract the telemetry streams
    print("Extracting second-by-second telemetry...")
    types = ['time', 'heartrate', 'watts', 'velocity_smooth']
    streams = client.get_activity_streams(target_activity.id, types=types)
    
    if streams:
        data_dict = {}
        for stream_type in types:
            if stream_type in streams:
                data_dict[stream_type] = streams[stream_type].data
                
        # Build the DataFrame
        df = pd.DataFrame(data_dict)
        
        if 'time' in df.columns:
            df.set_index('time', inplace=True)
            
        # --- PHYSIOLOGICAL ZONE ANALYSIS ---
        print("\n--- METABOLIC ZONE BREAKDOWN ---")
        
        # Drop any seconds where the heart rate sensor briefly disconnected
        df_clean = df.dropna(subset=['heartrate']).copy()
        
        # Define Threshold Zones 
        # (We will adjust these to your specific metabolic boundaries later)
        bins = [0, 140, 160, 175, 200]
        labels = ['Recovery', 'LT1 (Aerobic)', 'LT2 (Threshold)', 'VO2 Max']
        
        # Categorize Every Second
        df_clean['Zone'] = pd.cut(df_clean['heartrate'], bins=bins, labels=labels)
        
        # Calculate Time in Zone (in minutes)
        time_in_zones = df_clean['Zone'].value_counts(sort=False) / 60
        
        print("Time spent in each zone (Minutes):")
        print(time_in_zones.round(1))
    # --- NEW GRAPHING LOGIC ---
        import matplotlib.pyplot as plt
        
        print("\nGenerating Metabolic Plot... (A new window should pop up)")

        # Create a large, wide canvas
        plt.figure(figsize=(12, 6))
        
        # Plot your actual heart rate line
        # Assuming the index is time in seconds
        plt.plot(df_clean.index, df_clean['heartrate'], color='black', linewidth=1.5, label='Heart Rate')
        
        # Shade the physiological zones in the background
        plt.axhspan(0, 140, color='gray', alpha=0.2, label='Recovery')
        plt.axhspan(140, 160, color='green', alpha=0.2, label='LT1 (Aerobic)')
        plt.axhspan(160, 175, color='orange', alpha=0.2, label='LT2 (Threshold)')
        plt.axhspan(175, 210, color='red', alpha=0.2, label='VO2 Max')
        
        # Add labels and formatting
        plt.title(f"Metabolic Output: {target_activity.name}", fontsize=14, fontweight='bold')
        plt.xlabel("Time (Seconds)", fontsize=12)
        plt.ylabel("Heart Rate (BPM)", fontsize=12)
        
        # Move the legend outside the graph so it doesn't cover your data
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        
        plt.tight_layout() # Keeps the layout clean
        
        # Show the plot to the user
        plt.show()
    else:
        print("\nFailed to pull the streams, even though HR was detected.")

except Exception as e:
    print(f"\n--- FAILURE ---")
    print(f"Error: {e}")