#!/usr/bin/env python3
"""
Auto-launcher for contract translation demo
Starts the Flask API server and opens demo.html in browser
"""

import os
import sys
import subprocess
import time
import webbrowser
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Get the workspace root (parent of where this script is)
workspace_root = Path(__file__).parent.absolute()

print("\n" + "="*70)
print("🚀 IBM Agentics - Smart Contract Translator (Research Edition)")
print("   Dataset-Driven Quality Evaluation")
print("="*70 + "\n")

# Ensure required packages are installed
print("📦 Checking dependencies...")
required_packages = {
    'flask': 'flask',
    'flask_cors': 'flask-cors',
    'fastmcp': 'fastmcp',
    'agentics': 'agentics',
    'PyPDF2': 'PyPDF2',
    'pydantic': 'pydantic'
}

for import_name, pip_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"   ✓ {pip_name}")
    except ImportError:
        print(f"   ⚠️  Installing {pip_name}...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pip_name, '-q'])
        print(f"   ✓ {pip_name} installed")

print("\n✓ All dependencies ready!\n")

# Add paths - make sure they're absolute
mcp_dir = workspace_root / "mcp"
contract_translator_dir = workspace_root / "contract-translator"
demo_file = contract_translator_dir / "demo.html"

print("📍 Workspace Paths:")
print(f"   Root: {workspace_root}")
print(f"   Demo: {demo_file}")

# Check if demo.html and sampler.html exist
sampler_file = contract_translator_dir / "sampler.html"

if not demo_file.exists():
    print(f"\n❌ Error: demo.html not found at {demo_file}")
    sys.exit(1)

if not sampler_file.exists():
    print(f"\n⚠️ Warning: sampler.html not found at {sampler_file}")
    print("   Dataset browser will not be available.\n")
else:
    print(f"   ✓ Demo files found (demo.html + sampler.html)\n")

# Start HTTP server for demo.html in background thread
print("🌐 Starting servers...\n")

class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress the default HTTP server logging
        pass

def start_http_server():
    os.chdir(str(contract_translator_dir))
    server = HTTPServer(('localhost', 8000), QuietHTTPRequestHandler)
    server.serve_forever()

http_thread = threading.Thread(daemon=True, target=start_http_server)
http_thread.start()

print("   [1/3] HTTP server starting on http://localhost:8000")

# Start the translation API in background
print("   [2/3] Translation API starting on http://localhost:5000\n")
try:
    # Use Popen to start in FOREGROUND so we can see logs
    chatbot_process = subprocess.Popen(
        [sys.executable, str(mcp_dir / "chatbot_api.py")],
        cwd=str(workspace_root)
    )
    
    # Open demo in browser after giving server a moment
    print("⏳ Waiting 3 seconds for servers to initialize...\n")
    time.sleep(3)
    
    print("   [3/3] Opening demo pages in browser\n")
    demo_url = "http://localhost:8000/demo.html"
    sampler_url = "http://localhost:8000/sampler.html"
    
    try:
        webbrowser.open(demo_url)
        print(f"   ✓ Demo opened: {demo_url}")
        time.sleep(1)  # Small delay between opens
        webbrowser.open(sampler_url)
        print(f"   ✓ Sampler opened: {sampler_url}\n")
    except Exception as e:
        print(f"   ⚠️  Could not open browser automatically")
        print(f"   → Please open manually:")
        print(f"      Demo: {demo_url}")
        print(f"      Sampler: {sampler_url}\n")
    
    print("="*70)
    print("✅ DEMO IS READY!")
    print("="*70)
    print("\n📊 What's running:")
    print("   • Translation Demo: http://localhost:8000/demo.html")
    print("   • Dataset Browser: http://localhost:8000/sampler.html")
    print("   • Translation API: http://localhost:5000")
    print("\n🔬 Research Workflow:")
    print("   1. Browse dataset: http://localhost:8000/sampler.html")
    print("   2. Click 'Open in Demo' to load a contract")
    print("   3. Or paste text directly at: http://localhost:8000/demo.html")
    print("   4. Translate & evaluate generated Solidity contracts")
    print("\n📊 Dataset: requirement_fsm_code.jsonl (21,976 contracts)")
    print("\n📝 Logs below (Ctrl+C to stop):\n")
    
    # Keep the process alive
    chatbot_process.wait()

except KeyboardInterrupt:
    print("\n\nShutting down...")
    chatbot_process.terminate()
    try:
        chatbot_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        chatbot_process.kill()
    print("✓ Server stopped")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed to start translation API: {e}")
    sys.exit(1)
