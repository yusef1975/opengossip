"""
Bonus Phase: The AI Supervisor (The Control Plane)

WHAT THIS FILE IS:
    This script acts as a strategic overseer. It is NOT a node in the grid.
    Instead, it passively listens to the UDP network traffic, builds a 
    global picture of the grid, and feeds that data into Google's Gemini model
    to get strategic recommendations.

WHAT YOU LEARN:
    - Data Plane (the nodes doing the work) vs Control Plane (the AI managing them)
    - Creating a "Digital Twin" of a distributed system
    - Integrating real-time network data into an LLM context

REQUIREMENTS:
    pip install google-genai
    Set GEMINI_API_KEY environment variable.
    
    (If you don't have an API key, the script will run in 'Simulation Mode' 
    and just print the data it would have sent to the AI.)
"""

import socket
import threading
import json
import time
import os
import sys

# Try to import the new standard Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

class AISupervisor:
    def __init__(self, port: int):
        self.host = '127.0.0.1'
        self.port = port
        
        # This is our "Digital Twin" of the entire grid
        self.global_state = {}
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        
        # Setup Gemini Client if API key is present
        self.client = None
        self.api_key = os.environ.get("GEMINI_API_KEY")
        
        if HAS_GEMINI and self.api_key:
            print("🟢 Gemini API Key detected. AI analysis enabled.")
            self.client = genai.Client(api_key=self.api_key)
        else:
            print("🟡 No GEMINI_API_KEY found (or google-genai not installed).")
            print("   Running in SIMULATION MODE. Data will be aggregated but not sent to AI.")
            print("   To enable AI: pip install google-genai && set GEMINI_API_KEY=your_key")

    def listen(self):
        """Passively listens to gossip data to build the Digital Twin."""
        print(f"👂 [Supervisor] Listening for network traffic on port {self.port}...")
        
        while True:
            data, addr = self.sock.recvfrom(2048)
            message = json.loads(data.decode('utf-8'))
            msg_type = message.get("type")
            
            # The supervisor intercepts FULL_SYNC messages to see what's happening
            if msg_type == "FULL_SYNC":
                payload = message["payload"]
                city = payload["city"]
                energy = payload["energy_surplus_mw"]
                version = payload["version"]
                
                # Update our digital twin
                self.global_state[city] = {
                    "energy_surplus_mw": energy,
                    "last_updated_version": version,
                    "status": "ONLINE"
                }
                print(f"📡 [Supervisor] Intercepted data: {city} is at {energy}MW (v{version})")
            
            # We also intercept HASH_CHECKs just to see who is talking to who
            elif msg_type == "HASH_CHECK":
                city = message["city"]
                print(f"📡 [Supervisor] Network activity detected regarding {city}")

    def analyze_with_ai(self):
        """
        Takes the current global state (the Digital Twin) and sends it
        to Gemini for analysis.
        """
        if not self.global_state:
            print("\n🤖 [AI] Waiting for data. The grid is currently empty.")
            return

        print("\n" + "="*50)
        print("🧠 INITIATING AI ANALYSIS OF GRID STATE")
        print("="*50)
        
        state_json = json.dumps(self.global_state, indent=2)
        print(f"Sending this context to Gemini:\n{state_json}\n")

        prompt = f"""
        You are the AI Control Plane for the Iberian Energy Grid.
        You monitor a decentralized, peer-to-peer gossip network of energy nodes.
        
        Here is the current state of the network (Digital Twin):
        {state_json}
        
        Standard energy baseline is 10MW per city.
        
        Task:
        1. Identify any anomalies (e.g., massive spikes in energy, or cities that seem offline).
        2. Make a strategic recommendation on how to route power across the peninsula.
        3. Keep your response brief, professional, and formatted as a Situation Report (SITREP).
        """

        if self.client:
            try:
                print("⏳ Thinking...")
                # We use gemini-2.5-flash as it's fast and perfect for quick analysis tasks
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                print("\n" + "*"*50)
                print("🚨 AI STRATEGIC REPORT 🚨")
                print("*"*50)
                print(response.text)
                print("*"*50 + "\n")
            except Exception as e:
                print(f"❌ AI Error: {e}")
        else:
            print("[SIMULATION] If the AI was active, it would process the above JSON.")
            print("[SIMULATION] End of cycle.\n")

    def start_ai_loop(self):
        """Runs the AI analysis every 15 seconds."""
        while True:
            time.sleep(15)  # Wait 15 seconds
            self.analyze_with_ai()

    def start(self):
        # Start listening for network traffic
        threading.Thread(target=self.listen, daemon=True).start()
        
        # Start the AI analysis loop
        threading.Thread(target=self.start_ai_loop, daemon=True).start()

# ===================================================================
# ENTRY POINT
# ===================================================================
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    
    supervisor = AISupervisor(port)
    supervisor.start()
    
    # Keep the main thread alive so the background threads can run
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🔴 [Supervisor] Shutting down.")
