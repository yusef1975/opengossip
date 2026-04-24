"""
Phase 2: Discovery — The Seed Node Pattern

WHAT THIS FILE IS:
    An upgrade to Phase 1. Instead of typing in ports manually, nodes now:
    1. Have a hardcoded list of "Seed" addresses (e.g., Madrid on 8002)
    2. When booting, they ask the seed: "Who is online?"
    3. The seed replies with a list of known active ports
    4. The node saves those ports to its internal "peer list"

WHAT YOU LEARN:
    - Network Bootstrapping
    - Eliminating the "Single Point of Failure" (SPOF)
    - Distinguishing between different types of messages (Hello vs. PeerList)
"""

import socket
import threading
import json
import sys
import time

# We hardcode the seed nodes. In a real system, these would be IP addresses
# like 192.168.1.5. Here, we just use localhost ports.
SEED_NODES = [8002]  # Let's say Madrid runs on 8002 and acts as our Seed

class DiscoveryNode:
    def __init__(self, name: str, port: int):
        self.name = name
        self.host = '127.0.0.1'
        self.port = port
        
        # New in Phase 2: A list of known active peers
        self.known_peers = set()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))

    def listen(self):
        print(f"🟢 [{self.name}] Online on port {self.port}...")
        
        while True:
            data, addr = self.sock.recvfrom(2048)
            message = json.loads(data.decode('utf-8'))
            sender_port = addr[1]
            
            msg_type = message.get("type")
            
            # SCENARIO A: Someone is saying Hello
            if msg_type == "HELLO":
                print(f"\n👋 [{self.name}] Received HELLO from {message['name']} (Port {sender_port})")
                
                # We learn about the new node and add them to our peer list
                self.known_peers.add(sender_port)
                
                # Send them back our list of peers so they aren't lonely
                reply = {
                    "type": "PEER_LIST",
                    "peers": list(self.known_peers)
                }
                self.send_udp(sender_port, reply)
                
            # SCENARIO B: We asked a seed who was online, and they replied
            elif msg_type == "PEER_LIST":
                new_peers = message["peers"]
                print(f"\n🗺️ [{self.name}] Received peer list: {new_peers}")
                
                # Merge the received peers into our own set
                for p in new_peers:
                    # Don't add ourselves to our own peer list
                    if p != self.port:
                        self.known_peers.add(p)
                        
                print(f"✅ [{self.name}] My active peer list is now: {self.known_peers}")

            # SCENARIO C: Regular data message (like Phase 1)
            elif msg_type == "DATA":
                print(f"\n⚡ [{self.name}] Received DATA from port {sender_port}: {message['payload']}")

    def send_udp(self, target_port: int, message: dict):
        data = json.dumps(message).encode('utf-8')
        self.sock.sendto(data, (self.host, target_port))

    def bootstrap(self):
        """
        The very first thing a node does when it wakes up.
        It knocks on the door of the Seed Nodes to ask who is inside.
        """
        print(f"🔍 [{self.name}] Bootstrapping... looking for peers.")
        
        for seed in SEED_NODES:
            if seed != self.port:  # Don't bootstrap off yourself if you ARE the seed
                hello_msg = {
                    "type": "HELLO",
                    "name": self.name
                }
                self.send_udp(seed, hello_msg)

    def start(self):
        # 1. Start the listener thread
        listener = threading.Thread(target=self.listen, daemon=True)
        listener.start()
        
        # 2. Short delay to ensure the listener is ready
        time.sleep(0.5)
        
        # 3. Reach out to the seed nodes to get the map of the network
        self.bootstrap()

# ===================================================================
# ENTRY POINT
# ===================================================================
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python seed_node.py <NodeName> <Port>")
        print("Example (Seed): python seed_node.py Madrid 8002")
        print("Example (Node): python seed_node.py Seville 8001")
        sys.exit(1)

    node = DiscoveryNode(sys.argv[1], int(sys.argv[2]))
    node.start()

    time.sleep(1) # Let the bootstrap finish before showing the prompt
    
    print("\n--- COMMANDS ---")
    print("Type a port number to send a test DATA message.")
    print("Type 'peers' to see who you know.")
    print("Press Ctrl+C to quit\n")

    while True:
        try:
            cmd = input(f"[{node.name}] > ").strip()

            if cmd == "peers":
                print(f"Current known peers: {node.known_peers}")
            elif cmd.isdigit():
                target = int(cmd)
                if target in node.known_peers:
                    payload = {"type": "DATA", "payload": f"Hello from {node.name}!"}
                    node.send_udp(target, payload)
                else:
                    print(f"Port {target} is not in your peer list! Type 'peers' to check.")
            elif cmd:
                print("Invalid command.")

        except KeyboardInterrupt:
            print(f"\n\n🔴 [{node.name}] Shutting down.")
            break
