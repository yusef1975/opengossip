"""
Phase 3: The Infection (State Reconciliation)

WHAT THIS FILE IS:
    This is where the magic happens. We upgrade our nodes to use
    "Anti-Entropy State Reconciliation". Instead of blindly blasting
    data across the network, nodes now swap cryptographic fingerprints.
    
WHAT YOU LEARN:
    - Cryptographic hashing (MD5) to fingerprint data
    - Version Vectors (tracking changes without a central clock)
    - The HASH_CHECK -> REQUEST_DATA -> FULL_SYNC protocol pattern
"""

import socket
import threading
import json
import sys
import time
import hashlib

def generate_hash(city: str, energy: int, timestamp: int, version: int) -> str:
    """
    Creates a unique mathematical fingerprint of the data.
    If even a single byte of the input changes, the resulting hash 
    will be completely different.
    
    This is what allows nodes to quickly check if their databases match
    without having to send the entire database over the network.
    """
    raw_string = f"{city}{energy}{timestamp}{version}"
    return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

class AdvancedGossipNode:
    def __init__(self, name: str, port: int):
        self.name = name
        self.host = '127.0.0.1'
        self.port = port
        
        # The internal database. 
        # Structure: {"Seville": {"energy_surplus_mw": 50, "version": 1, "data_hash": "abc...", ...}}
        self.db = {} 
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))

    def update_own_energy(self, new_energy_mw: int):
        """
        Updates this node's own energy level in the database.
        Crucially, it bumps the VERSION number and calculates a NEW HASH.
        """
        # Get our current version (default to 0 if this is the first time)
        current_data = self.db.get(self.name, {"version": 0})
        new_version = current_data.get("version", 0) + 1
        
        timestamp = int(time.time())
        new_hash = generate_hash(self.name, new_energy_mw, timestamp, new_version)
        
        self.db[self.name] = {
            "city": self.name,
            "energy_surplus_mw": new_energy_mw,
            "timestamp": timestamp,
            "version": new_version,
            "data_hash": new_hash
        }
        
        print(f"\n🔋 Updated internal state: {new_energy_mw}MW | Version {new_version} | Hash: {new_hash[:8]}...")

    def listen(self):
        """Background thread listening for network traffic."""
        while True:
            data, addr = self.sock.recvfrom(2048)
            message = json.loads(data.decode('utf-8'))
            msg_type = message.get("type")
            
            # =================================================================
            # THE 3-STEP ANTI-ENTROPY DANCE
            # =================================================================
            
            # STEP 1: Someone is asking if our hashes match
            if msg_type == "HASH_CHECK":
                remote_city = message["city"]
                remote_version = message["version"]
                remote_hash = message["hash"]
                
                local_record = self.db.get(remote_city)
                
                # If we don't have ANY data for that city, OR our version is older
                if not local_record or local_record["version"] < remote_version:
                    print(f"\n🔍 [SYNC] Hash mismatch for {remote_city}! They have version {remote_version}. Requesting full data...")
                    # Ask them to send the actual data
                    self.send_udp(addr[1], {
                        "type": "REQUEST_DATA", 
                        "city": remote_city
                    })
                else:
                    print(f"\n✅ [SYNC] Hash match for {remote_city}. We are up to date.")
            
            # STEP 2: Someone realized they are out of date and wants our full data
            elif msg_type == "REQUEST_DATA":
                requested_city = message["city"]
                
                if requested_city in self.db:
                    print(f"\n📦 [SYNC] Sending full payload for {requested_city} to port {addr[1]}...")
                    self.send_udp(addr[1], {
                        "type": "FULL_SYNC", 
                        "payload": self.db[requested_city]
                    })
            
            # STEP 3: We received the full missing data. Save it!
            elif msg_type == "FULL_SYNC":
                payload = message["payload"]
                city = payload["city"]
                
                self.db[city] = payload
                print(f"\n💾 [SYNC] Downloaded new data for {city}: {payload['energy_surplus_mw']}MW (v{payload['version']}). Database updated!")

    def send_udp(self, target_port: int, message: dict):
        """Helper function to fire a UDP packet."""
        data = json.dumps(message).encode('utf-8')
        self.sock.sendto(data, (self.host, target_port))

    def trigger_gossip(self, target_port: int, city_to_gossip: str):
        """
        Starts the gossip process by sending JUST the fingerprint (Hash + Version),
        NOT the entire data payload.
        """
        if city_to_gossip in self.db:
            record = self.db[city_to_gossip]
            packet = {
                "type": "HASH_CHECK",
                "city": city_to_gossip,
                "version": record["version"],
                "hash": record["data_hash"]
            }
            print(f"\n📤 Gossiping hash for {city_to_gossip} (v{record['version']}) to port {target_port}...")
            self.send_udp(target_port, packet)
        else:
            print(f"I don't have any data for {city_to_gossip} yet.")

    def start(self):
        print(f"🟢 [{self.name}] Online on port {self.port}")
        threading.Thread(target=self.listen, daemon=True).start()

# ===================================================================
# ENTRY POINT
# ===================================================================
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python advanced_node.py <CityName> <Port>")
        sys.exit(1)

    node = AdvancedGossipNode(sys.argv[1], int(sys.argv[2]))
    node.start()
    
    # Initialize with some default power so we have something to gossip
    node.update_own_energy(10)
    
    time.sleep(0.5)
    print("\n--- COMMANDS ---")
    print("1. Type a number to update your own energy (e.g., '50')")
    print("2. Type 'gossip <port>' to sync your state with someone (e.g., 'gossip 8002')")
    print("3. Type 'db' to view your current internal state")
    
    while True:
        try:
            cmd = input(f"\n[{node.name}] > ").strip().split()
            if not cmd: 
                continue
                
            # Command: Update Energy
            if len(cmd) == 1 and cmd[0].isdigit():
                node.update_own_energy(int(cmd[0]))
                
            # Command: View Database
            elif len(cmd) == 1 and cmd[0] == "db":
                print(json.dumps(node.db, indent=2))
                
            # Command: Trigger Gossip
            elif len(cmd) == 2 and cmd[0] == "gossip" and cmd[1].isdigit():
                # For this learning phase, we manually tell it to gossip.
                # In the real world, a timer would trigger this automatically 
                # to a random peer every few seconds.
                node.trigger_gossip(int(cmd[1]), node.name)
                
            else:
                print("Invalid command.")
                
        except KeyboardInterrupt:
            print(f"\n\n🔴 [{node.name}] Shutting down.")
            break
