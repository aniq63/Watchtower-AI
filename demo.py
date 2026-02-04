from watchtower_sdk.watchtower.monitor import WatchtowerInputMonitor
import pandas as pd
import time

def run_drift_demo():
    print("Initializing Watchtower Input Monitor...")
    
    # 1. Initialize the Watchtower Input Monitor
    # Replace with your actual project details and API key
    monitor = WatchtowerInputMonitor(
        api_key="0f1385e341463f66604195d11a45851b16c0e11fb95003b7a6581a168f366b30",
        project_name="Cat Classification",
        endpoint="http://localhost:8000"
    )

    print("Loading test data...")
    # Load test data
    try:
        df = pd.read_csv(r'test_datasets_for_ingestion\weather.csv')
        # Ensure we have enough data
        if len(df) < 1800:
            print(f"Warning: Dataset has only {len(df)} rows. Baseline creation (1000 rows) might fail.")
        
        # Batch 1: 1200 rows (Sufficient for default baseline of 1000)
        batch_1 = df[:1200]
        
        # Batch 2: 600 rows (Sufficient for default monitor window of 500)
        batch_2 = df[1200:1800] 
    except FileNotFoundError:
        print("Error: 'weather.csv' not found. Please ensure the file exists.")
        return

    print(f"Logging Batch 1 ({len(batch_1)} rows)...")
    try:
        # Log Batch 1
        response_1 = monitor.log(
            features=batch_1.to_dict(orient='records'),
            metadata={"environment": "production", "batch": "1"}
        )
        print("Batch 1 Response:", response_1)
    except Exception as e:
        print("Failed to log Batch 1:", e)

    print("\nWaiting 5 seconds...")
    time.sleep(5)

    print(f"Logging Batch 2 ({len(batch_2)} rows) - This might trigger drift detection...")
    try:
        # Log Batch 2
        response_2 = monitor.log(
            features=batch_2.to_dict(orient='records'),
            metadata={"environment": "production", "batch": "2"}
        )
        print("Batch 2 Response:", response_2)
    except Exception as e:
        print("Failed to log Batch 2:", e)

if __name__ == "__main__":
    print("--- Watchtower Input Monitor Demo ---")
    run_drift_demo()
