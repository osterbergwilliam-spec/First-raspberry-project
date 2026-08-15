import json
import time
import os


# ==========================================
# CONFIGURATION
# ==========================================
# MUST match the path in your C# code
FILE_PATH = r"C:\Users\William\Desktop\vscode\Nya test\input.json"

def update_json(proximity, value):
    """Writes the current simulation state to the JSON file."""
    data = {
        "Proximity": proximity,
        "Value": value
    }
    try:
        with open(FILE_PATH, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error writing to file: {e}")

def simulate_approach(target_id):
    """Simulates a person walking from far away to the lock."""
    print(f"\n--- Simulating Approach: Person with ID {target_id} ---")
    
    # Increase proximity from 0.0 to 1.0
    for p in [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
        print(f"Proximity: {p:.1f}")
        update_json(p, target_id)
        time.sleep(3) # Wait 3 seconds between steps to see C# react
    
    print("Person is now standing in front of the lock.")
    time.sleep(5) # Hold the position for 3 seconds

def simulate_departure():
    """Simulates the person walking away."""
    print("\n--- Simulating Departure ---")
    for p in [0.7, 0.4, 0.1, 0.0]:
        print(f"Proximity: {p:.1f}")
        update_json(p, -1) # ID becomes irrelevant once they leave
        time.sleep(1)
    print("Area clear.")

# ==========================================
# MAIN LOOP
# ==========================================
if __name__ == "__main__":
    print("Vision Simulator Started.")
    print("This script will feed data into the JSON file for the C# Brain.")
    
    try:
        while True:
            print("\nChoose a scenario:")
            print("1. Authorized Person (ID 10)")
            print("2. Unauthorized Person (ID 73)")
            print("3. Exit")
            
            choice = input("Selection: ")
            
            if choice == '1':
                simulate_approach(10)
                simulate_departure()
            elif choice == '2':
                simulate_approach(73)
                simulate_departure()
            elif choice == '3':
                break
            else:
                print("Invalid choice.")
                
    except KeyboardInterrupt:
        print("\nSimulator stopped.")