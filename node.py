"""
Phase 1: The Foundation — A Single Gossip Node

WHAT THIS FILE IS:
    A single, independent process that:
    1. Binds to a UDP port (claims a "radio channel")
    2. Listens for incoming messages in the background
    3. Can fire messages to any other port on the network
    4. Maintains its own internal state (a local "database")

WHAT YOU LEARN:
    - Raw UDP networking (no HTTP, no REST, no frameworks)
    - Threading (doing two things at once)
    - The idea that each node is a self-contained unit
"""

import socket       # The standard library for low-level networking
import threading    # Lets us run the listener in the background
import json         # Converts Python dicts <-> network-safe strings
import sys          # Reads command-line arguments (node name, port)
import time         # Small delays for cleaner terminal output


class GossipNode:
    """
    A single node in our gossip network.
    
    Think of this as ONE city on the Iberian Peninsula.
    It has:
        - A name (e.g., "Seville")
        - A port (e.g., 8001) — its unique address on the network
        - A state dict — its local "database" of what it knows
        - A UDP socket — its walkie-talkie for sending/receiving
    """

    def __init__(self, name: str, port: int):
        self.name = name
        self.host = '127.0.0.1'  # localhost — everything runs on your machine
        self.port = port
        self.state = {}          # The node's internal "database" — starts empty

        # -----------------------------------------------------------
        # CREATE THE SOCKET
        # -----------------------------------------------------------
        # socket.AF_INET    = We're using IPv4 addresses (like 127.0.0.1)
        # socket.SOCK_DGRAM = We want UDP (datagram), not TCP (stream)
        #
        # If we used SOCK_STREAM, we'd get TCP — reliable but slow.
        # SOCK_DGRAM gives us UDP — fast, fire-and-forget.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # -----------------------------------------------------------
        # BIND TO THE PORT
        # -----------------------------------------------------------
        # This is like claiming apartment 8001 in the building.
        # No other process can use this port while we're running.
        # If you try to run two nodes on the same port, you'll get
        # an "Address already in use" error.
        self.sock.bind((self.host, self.port))

    def listen(self):
        """
        Endless loop that listens for incoming UDP packets.
        
        This runs in a BACKGROUND THREAD. It sits at the "mailbox" 
        and waits for postcards. When one arrives, it:
            1. Decodes the raw bytes back into a Python dict
            2. Merges the received data into our local state
            3. Prints what happened
        
        WHY AN INFINITE LOOP?
        Because a gossip node never stops listening. In a real system,
        messages can arrive at any microsecond. The listener must 
        always be ready.
        """
        print(f"🟢 [{self.name}] Online and listening on port {self.port}...")
        
        while True:
            # .recvfrom(1024) = "Wait here until a packet arrives"
            # 1024 = max bytes we'll accept in one packet
            # Returns: (raw_bytes, (sender_ip, sender_port))
            data, addr = self.sock.recvfrom(1024)

            # The raw data is bytes. We decode it to a string,
            # then parse the JSON string back into a Python dict.
            message = json.loads(data.decode('utf-8'))

            print(f"\n⚡ [{self.name}] Received data from port {addr[1]}: {message}")

            # Merge the received data into our local state.
            # dict.update() adds new keys and overwrites existing ones.
            # This is NAIVE — in Phase 3 we'll replace this with 
            # version-aware merging so we don't blindly overwrite newer data.
            self.state.update(message)

            print(f"💾 [{self.name}] Updated state: {self.state}")

    def send_message(self, target_port: int, payload: dict):
        """
        Fires a UDP packet to another port.
        
        This is the "throw a postcard into someone else's mailbox" action.
        
        Args:
            target_port: The port number of the node we're sending to
            payload:     A Python dict with the data to send
            
        NOTE: We don't get confirmation that the other side received it.
        That's the nature of UDP. If the target node is dead, the packet
        just vanishes into the void. No error, no retry.
        """
        # Convert the dict -> JSON string -> bytes
        message = json.dumps(payload).encode('utf-8')

        # Fire the packet. sendto() takes (bytes, (host, port))
        self.sock.sendto(message, (self.host, target_port))
        print(f"📤 [{self.name}] Sent payload to port {target_port}")

    def start(self):
        """
        Boots the node by starting the listener in a background thread.
        
        daemon=True means: "If the main program exits, kill this thread too."
        Without daemon=True, the program would hang forever even after 
        you press Ctrl+C because the listener thread would keep running.
        """
        listener = threading.Thread(target=self.listen, daemon=True)
        listener.start()


# ===================================================================
# ENTRY POINT — What runs when you type: python node.py Seville 8001
# ===================================================================
if __name__ == "__main__":
    # sys.argv is a list of command-line arguments:
    # sys.argv[0] = "node.py" (the script name)
    # sys.argv[1] = "Seville"  (the node name)
    # sys.argv[2] = "8001"     (the port)
    if len(sys.argv) < 3:
        print("Usage: python node.py <NodeName> <Port>")
        print("Example: python node.py Seville 8001")
        sys.exit(1)

    node_name = sys.argv[1]
    node_port = int(sys.argv[2])

    # Create and boot the node
    node = GossipNode(node_name, node_port)
    node.start()

    # Small delay so the "Online" message prints before the prompt
    time.sleep(0.5)

    # -----------------------------------------------------------
    # INTERACTIVE COMMAND LOOP
    # -----------------------------------------------------------
    # This is a simple REPL (Read-Eval-Print Loop) that lets you
    # manually send messages to other nodes for testing.
    #
    # In Phase 2, we'll replace this with automatic peer discovery.
    # In Phase 3, we'll replace the payload with hash-based sync.
    print("\n--- COMMANDS ---")
    print("Type a port number to send a test message (e.g., '8002')")
    print("Press Ctrl+C to quit\n")

    while True:
        try:
            target = input(f"[{node.name}] Enter target port > ").strip()

            if target.isdigit():
                # For Phase 1, we send a simple hardcoded payload.
                # The interesting part isn't WHAT we send — it's that 
                # two independent processes can communicate via UDP.
                fake_payload = {
                    "origin": node.name,
                    "energy_surplus_mw": 50,
                    "message": f"Hello from {node.name}!"
                }
                node.send_message(int(target), fake_payload)
            else:
                print("Please enter a valid port number.")

        except KeyboardInterrupt:
            print(f"\n\n🔴 [{node.name}] Shutting down.")
            break
