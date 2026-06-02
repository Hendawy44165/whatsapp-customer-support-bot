import os
import sys
import time
import subprocess
import signal

# List of sub-servers to start
# Each tuple has: (Name, Filepath, Port)
SERVERS = [
    ("Dashboard Server", "dashboard_server/app.py", 8001),
    ("Agent Server", "agent_server/app.py", 8010),
    ("HubSpot CRM MCP Server", "mcp_servers/hubspot_mcp.py", 8011),
    ("Shop Cart Handling MCP Server", "mcp_servers/shop_cart_mcp.py", 8012),
    ("Conversations MCP Server", "mcp_servers/conversations_mcp.py", 8013),
    ("Human Expert MCP Server", "mcp_servers/human_expert_mcp.py", 8014),
]

processes = []

def cleanup(sig=None, frame=None):
    print("\n[start_all.py] Stopping all sub-servers...")
    for name, proc in processes:
        try:
            print(f"[start_all.py] Terminating {name}...")
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    print("[start_all.py] All processes stopped. Exiting.")
    sys.exit(0)

# Register signals for clean exit
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # Check if virtualenv exists
    venv_python = os.path.abspath(os.path.join(backend_dir, "..", ".venv", "bin", "python"))
    if not os.path.exists(venv_python):
        # Fall back to standard sys.executable
        venv_python = sys.executable
        
    print("=================================================================")
    print(f"      NUIT CONCIERGE MULTI-SERVER RUNNER V1                      ")
    print(f"      Python: {venv_python}                                      ")
    print("=================================================================")
    
    for name, script_path, port in SERVERS:
        abs_script = os.path.abspath(script_path)
        print(f"[start_all.py] Launching {name} on port {port}...")
        
        # Start subprocess
        proc = subprocess.Popen(
            [venv_python, abs_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=backend_dir
        )
        processes.append((name, proc))
        
        # Wait a brief moment to ensure port binds
        time.sleep(0.5)

    print("\n=================================================================")
    print("  All sub-servers launched! Press Ctrl+C to stop all of them.")
    print("=================================================================\n")

    # Monitor outputs and print to terminal
    import threading
    
    def log_stream(proc_name, process_obj):
        for line in iter(process_obj.stdout.readline, ''):
            # Print output with server prefix
            print(f"[{proc_name}] {line.strip()}")
            if not is_running(process_obj):
                break

    def is_running(p):
        return p.poll() is None

    threads = []
    for name, proc in processes:
        t = threading.Thread(target=log_stream, args=(name, proc), daemon=True)
        t.start()
        threads.append(t)

    # Keep main thread alive
    while True:
        try:
            # Check if any process has exited unexpectedly
            for name, proc in processes:
                exit_code = proc.poll()
                if exit_code is not None:
                    print(f"\n[start_all.py] WARNING: {name} exited with status code {exit_code}!")
                    cleanup()
            time.sleep(1.0)
        except (KeyboardInterrupt, SystemExit):
            cleanup()

if __name__ == "__main__":
    main()
