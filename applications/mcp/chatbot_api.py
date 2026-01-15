"""
Chatbot API Server - Bridges demo.html with chatbot.py functionality

This provides a REST API for the demo.html to communicate with the actual chatbot
and MCP servers, allowing real contract function calls.
"""

import os
import asyncio
import json
from pathlib import Path
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
from fastmcp import Client
import sys
import tempfile
import shutil
import importlib.util
from queue import Queue
import threading
import subprocess
import time

# Add contract-translator directory to path
contract_translator_path = Path(__file__).parent.parent / "contract-translator"
sys.path.insert(0, str(contract_translator_path))

from agentics import LLM, user_message, system_message

# Import ContractTranslator from agentic_implementation
try:
    from agentic_implementation import IBMAgenticContractTranslator
    ContractTranslator = IBMAgenticContractTranslator
except ImportError:
    # Fallback: try direct import
    import importlib.util
    spec = importlib.util.spec_from_file_location("agentic_implementation", contract_translator_path / "agentic_implementation.py")
    agentic_impl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agentic_impl)
    ContractTranslator = agentic_impl.IBMAgenticContractTranslator

# Load environment - try multiple locations
env_paths = [
    Path(__file__).parent / '.env',  # mcp/.env
    Path(__file__).parent.parent / '.env',  # applications/.env
    Path(__file__).parent.parent.parent / '.env',  # Agentics-Research/.env
]

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        env_loaded = True
        print(f"✓ Loaded .env from {env_path}")
        break

if not env_loaded:
    load_dotenv()  # Try default locations

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in .env")
    print("   Searched locations:")
    for p in env_paths:
        print(f"      - {p} {'(exists)' if p.exists() else '(not found)'}")
    raise RuntimeError("OPENAI_API_KEY not found in .env. Please create a .env file with OPENAI_API_KEY=your_key")

llm = LLM(model="gpt-4o-mini")
app = Flask(__name__)
CORS(app)

# Global state
current_mcp_client = None
current_tools = []
current_contract_type = "sales"
current_mcp_process = None  # Track MCP server subprocess

# Store ongoing translation sessions for pause/resume
translation_sessions = {}


# ==================== SOLIDITY ERROR RECOVERY FUNCTIONS ====================

def _fix_empty_statements(solidity_code: str) -> str:
    """Remove incomplete statement fragments that cause syntax errors"""
    lines = solidity_code.split('\n')
    fixed_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip completely empty lines or lines with only whitespace
        if not stripped:
            fixed_lines.append('')
            continue
        
        # Skip lines that are just closing braces
        if stripped == '}':
            fixed_lines.append(line)
            continue
        
        # Skip lines that end with semicolon (complete statements)
        if stripped.endswith(';') or stripped.endswith('{'):
            fixed_lines.append(line)
            continue
        
        # Skip function declarations and control flow
        if any(keyword in stripped for keyword in ['function ', 'if (', 'for (', 'while (', 'else', 'event ', 'mapping', 'struct ', 'contract ']):
            fixed_lines.append(line)
            continue
        
        # Skip lines with common valid patterns
        if any(pattern in stripped for pattern in ['return ', 'require(', 'assert(', 'revert(', 'emit ', '=', 'public', 'private', 'internal', 'external']):
            fixed_lines.append(line)
            continue
        
        # Skip lines that look like valid statements
        if not any(char in stripped for char in ['(', ')', '[', ']']):
            # If it's just a word or simple identifier, likely incomplete
            if len(stripped.split()) <= 2 and not any(op in stripped for op in ['=', '>', '<', '+', '-', '*', '/']):
                continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def _fix_malformed_statements(solidity_code: str) -> str:
    """Fix missing semicolons, mismatched brackets, and malformed function calls"""
    import re
    
    lines = solidity_code.split('\n')
    fixed_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped or stripped.startswith('//'):
            fixed_lines.append(line)
            continue
        
        # Add missing semicolons to assignment and function call statements
        if stripped and not stripped.endswith((';', '{', '}', '(', ')', '/*', '*/')):
            # Check if it looks like a statement that needs a semicolon
            if any(kw in stripped for kw in ['return ', 'require(', 'assert(', 'emit ', 'revert(', '=']):
                # Make sure it's not a function declaration or control structure
                if not any(kw in stripped for kw in ['function ', 'if (', 'for (', 'while (', 'else if', 'contract ', 'event ']):
                    if not stripped.endswith(':'):
                        # Check if statement is complete (not missing closing parens)
                        if stripped.count('(') == stripped.count(')'):
                            line = line.rstrip() + ';'
        
        # Fix: Remove incomplete inline comments
        if ' //' in line:
            # Make sure comment doesn't cut off code
            comment_pos = line.find(' //')
            code_part = line[:comment_pos].strip()
            if code_part and not code_part.endswith((';', '{', '}')):
                if code_part.count('(') == code_part.count(')'):
                    line = line[:comment_pos].rstrip() + '; //' + line[comment_pos+3:]
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def _remove_problematic_modifiers(solidity_code: str) -> str:
    """Remove access modifiers and complex decorators that may cause issues"""
    import re
    
    # Remove problematic inline modifiers that aren't standard Solidity
    # Keep standard ones: public, private, internal, external, pure, view, payable, constant
    
    lines = solidity_code.split('\n')
    fixed_lines = []
    
    standard_modifiers = {'public', 'private', 'internal', 'external', 'pure', 'view', 'payable', 'constant', 'virtual', 'override', 'abstract'}
    
    for line in lines:
        # Skip comments
        if line.strip().startswith('//') or line.strip().startswith('/*'):
            fixed_lines.append(line)
            continue
        
        # For lines with function declarations, clean up modifiers
        if 'function ' in line:
            # Split the line at function keyword
            before_func = line[:line.find('function')]
            func_part = line[line.find('function'):]
            
            # Try to preserve the line but remove non-standard modifiers
            # This is conservative - keep the line mostly as-is
            fixed_lines.append(line)
            continue
        
        # Remove lines that are just dangling modifiers
        stripped = line.strip()
        if stripped in standard_modifiers or (len(stripped.split()) == 1 and stripped not in standard_modifiers):
            if stripped and not any(kw in stripped for kw in ['return', 'require', 'assert', 'emit', 'revert']):
                # Check if this is a complete line (ends with { ; or })
                if not any(c in stripped for c in ['{', ';', '}']):
                    # Skip dangling single words that aren't keywords
                    if not any(kw in stripped for kw in ['contract', 'function', 'if', 'for', 'while']):
                        continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


# ==================== STREAMING TRANSLATION ====================

async def decide_tool_call(user_input: str, tools: list, contract_type: str) -> dict:
    """Use LLM to decide which tool to call based on user input."""
    import asyncio
    
    tool_descriptions = []
    for t in tools:
        if hasattr(t, 'name'):
            name = t.name
            desc = t.description if hasattr(t, 'description') else 'No description'
            input_schema = t.inputSchema if hasattr(t, 'inputSchema') else {}
        else:
            name = t.get('name', 'unknown')
            desc = t.get('description', 'No description')
            input_schema = t.get('inputSchema', {})
        
        tool_descriptions.append(f"- {name}: {desc}")
    
    tool_descriptions_str = "\n".join(tool_descriptions)
    
    messages = [
        system_message(
            f"""You are an AI assistant managing a {contract_type} smart contract.
            
Your job is to understand what the user wants and decide which contract tool to call.

Available tools:
{tool_descriptions_str}

When the user makes a request, respond with ONLY valid JSON (no explanations or markdown).
Format: {{"tool": "function_name", "args": {{"param1": value1, "param2": value2}}}}

Common requests:
- "What's the status?" → call a status/view function
- "Pay rent" → call payment functions
- "Check balance" → call balance checking functions
- "Get details" → call getter functions

Always use actual function names from the available tools.
If the user's request doesn't match any tool, respond with {{"tool": "none", "explanation": "I don't see a matching function for that request"}}"""
        ),
        user_message(
            f"""User request: "{user_input}"

Respond with ONLY the JSON, no extra text or markdown."""
        )
    ]
    
    try:
        # Wrap LLM call with timeout to prevent hanging
        def call_llm():
            return llm.chat(messages=messages)
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, call_llm),
            timeout=10.0  # 10 second timeout for LLM response
        )
        response_text = str(response).strip()
        
        # Remove markdown fences if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(response_text)
            return result
        except Exception as e:
            print(f"⚠ LLM response parsing error: {response_text}")
            return {"error": f"Invalid response format: {response_text}", "exception": str(e)}
    
    except asyncio.TimeoutError:
        print("❌ LLM call timed out after 10 seconds")
        return {"error": "LLM request timed out", "tool": "none", "explanation": "The AI is taking too long to respond. Please try again."}
    except Exception as e:
        print(f"❌ Error in decide_tool_call: {str(e)}")
        return {"error": f"Failed to determine tool: {str(e)}", "tool": "none"}


def wait_for_approval(session_id: str, timeout: int = 600):
    """Wait for user approval before continuing translation"""
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if session_id in translation_sessions:
            session = translation_sessions[session_id]
            if 'user_approval' in session:
                approval = session['user_approval']
                del session['user_approval']  # Clear the approval flag
                return approval
        time.sleep(0.5)
    
    return False  # Timeout


@app.route('/api/translate-stream', methods=['POST'])
def translate_stream():
    """Stream real-time updates during 6-phase translation pipeline using Server-Sent Events"""
    import uuid
    
    try:
        # Check if text contract or PDF file provided
        contract_text = request.form.get('contract_text')
        contract_type = request.form.get('contract_type', 'other')
        
        if contract_text:
            # TEXT CONTRACT MODE (NEW)
            print(f"📝 Processing text contract ({len(contract_text)} chars, type: {contract_type})")
            
            # Create a session ID for this translation
            session_id = str(uuid.uuid4())
            translation_sessions[session_id] = {'temp_path': None, 'is_text': True}
            print(f"📋 Created session: {session_id}")
            
            # Save text to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(contract_text)
                temp_text_path = tmp_file.name
                translation_sessions[session_id]['temp_path'] = temp_text_path
                print(f"✓ Saved to temp: {temp_text_path}")
        
        elif 'file' in request.files:
            # PDF MODE (LEGACY - KEPT FOR COMPATIBILITY)
            file = request.files['file']
            if file.filename == '':
                print("❌ Empty filename")
                return Response(f"data: {json.dumps({'error': 'No file selected', 'phase': 0})}\n\n", mimetype='text/event-stream'), 400
            
            if not file.filename.lower().endswith('.pdf'):
                print(f"❌ Invalid file type: {file.filename}")
                return Response(f"data: {json.dumps({'error': 'Only PDF files are supported', 'phase': 0})}\n\n", mimetype='text/event-stream'), 400
            
            print(f"📄 Processing file: {file.filename}")
            
            # Create a session ID for this translation
            session_id = str(uuid.uuid4())
            translation_sessions[session_id] = {'temp_path': None, 'is_text': False}
            print(f"📋 Created session: {session_id}")
            
            # Save to temporary location
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                file.save(tmp_file.name)
                temp_pdf_path = tmp_file.name
                translation_sessions[session_id]['temp_path'] = temp_pdf_path
                print(f"✓ Saved to temp: {temp_pdf_path}")
        else:
            print("❌ No contract text or file provided")
            return Response(f"data: {json.dumps({'error': 'No contract text or file provided', 'phase': 0})}\n\n", mimetype='text/event-stream'), 400
        
        def generate():
            """Generator for Server-Sent Events"""
            try:
                # Initialize the real translator
                print("🚀 Initializing ContractTranslator...")
                translator = ContractTranslator()
                print("✓ Translator initialized")
                
                # Run the streaming 6-phase pipeline
                print("📋 Starting 6-phase translation pipeline...")
                
                # Set output directory to contract-translator/output
                output_directory = str(contract_translator_path / "output")
                
                # Get the input path (either text file or PDF)
                input_path = translation_sessions[session_id]['temp_path']
                
                for phase_update in translator.translate_contract_streaming(
                    input_path=input_path,
                    output_dir=output_directory,
                    require_audit_approval=False,
                    generate_mcp_server=True
                ):
                    # Send each phase update as an SSE event
                    print(f"📡 Streaming phase {phase_update['phase']}...")
                    
                    # For Phase 4 (security audit), pause and wait for approval
                    if phase_update['phase'] == 4 and phase_update['status'] == 'needs_approval':
                        print(f"⏸️  Waiting for user approval on Phase 4...")
                        # Include session_id in the event so frontend knows which session to approve
                        phase_update['session_id'] = session_id
                        yield f"data: {json.dumps(phase_update)}\n\n"
                        
                        # Wait for user approval
                        approval = wait_for_approval(session_id, timeout=600)
                        print(f"✓ User approval received: {approval}")
                        
                        if not approval:
                            print("❌ User rejected the audit or approval timed out")
                            error_event = {"error": "Security audit rejected or approval timed out", "phase": 0}
                            yield f"data: {json.dumps(error_event)}\n\n"
                            return
                        else:
                            # Continue to next phase
                            continue
                    
                    yield f"data: {json.dumps(phase_update)}\n\n"
                
                print("✓ Translation streaming completed")
                
            except Exception as e:
                print(f"❌ Translation error: {str(e)}")
                import traceback
                traceback.print_exc()
                error_event = {"error": str(e), "phase": 0}
                yield f"data: {json.dumps(error_event)}\n\n"
            
            finally:
                # Clean up temp file
                if session_id in translation_sessions and translation_sessions[session_id]['temp_path']:
                    temp_path = translation_sessions[session_id]['temp_path']
                    if Path(temp_path).exists():
                        try:
                            os.unlink(temp_path)
                            print(f"✓ Cleaned up temp file")
                        except:
                            pass
                # Clean up session
                if session_id in translation_sessions:
                    del translation_sessions[session_id]
        
        return Response(generate(), mimetype='text/event-stream', headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        })
    
    except Exception as e:
        print(f"❌ API error: {str(e)}")
        import traceback
        traceback.print_exc()
        error_event = {"error": str(e), "phase": 0}
        return Response(f"data: {json.dumps(error_event)}\n\n", mimetype='text/event-stream'), 500


@app.route('/api/audit-approval', methods=['POST'])
def audit_approval():
    """Handle user approval/rejection of security audit"""
    data = request.json
    session_id = data.get('session_id')
    approved = data.get('approved', False)
    
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    
    if session_id not in translation_sessions:
        return jsonify({"error": "Session not found"}), 404
    
    # Store the approval and resume the stream
    translation_sessions[session_id]['user_approval'] = approved
    print(f"📝 User approval: {approved} (Session: {session_id})")
    
    return jsonify({"success": True, "message": f"Audit {'approved' if approved else 'rejected'}"})


def _generate_mcp_server_code(contract_name: str, abi: list) -> str:
    """Generate MCP server code from contract ABI with proper error handling"""
    
    # Filter functions from ABI
    functions = [item for item in abi if item.get('type') == 'function']
    
    # Build tool functions
    tool_functions = []
    
    for func in functions:
        func_name = func.get('name', 'unknown')
        inputs = func.get('inputs', [])
        state_mutability = func.get('stateMutability', 'view')
        
        # Build parameter list
        params = ', '.join([f'{inp.get("name", "param")}' for inp in inputs])
        
        # Build parameter documentation
        param_docs = '\n        '.join([
            f'Args:',
            *[f'  {inp.get("name", "param")}: {inp.get("type", "unknown")}' 
              for inp in inputs]
        ]) if inputs else 'Returns: Contract data'
        
        # Determine if function writes to blockchain
        is_write = state_mutability in ['nonpayable', 'payable']
        
        if is_write:
            # Write function
            tool_code = f'''@mcp.tool()
async def {func_name}({params}):
    """Call {func_name} on the contract.
    
    {param_docs}
    """
    try:
        sys.stderr.write(f"[MCP] Calling {func_name}\\n")
        sys.stderr.flush()
        
        # Get nonce with timeout
        try:
            nonce = web3.eth.get_transaction_count(account_address, timeout=5)
        except Exception as e:
            return {{"error": f"Failed to get nonce: {{str(e)}}"}}
        
        # Build transaction with timeout
        try:
            txn = contract.functions.{func_name}({params}).build_transaction({{
                'from': account_address,
                'nonce': nonce,
                'gas': 2000000,
                'gasPrice': web3.eth.gas_price
            }})
        except Exception as e:
            return {{"error": f"Failed to build transaction: {{str(e)}}"}}
        
        # Send transaction
        try:
            tx_hash = web3.eth.send_transaction(txn)
            sys.stderr.write(f"[MCP] Transaction sent: {{tx_hash.hex()}}\\n")
            sys.stderr.flush()
            return {{"tx_hash": tx_hash.hex()}}
        except Exception as e:
            return {{"error": f"Transaction failed: {{str(e)}}"}}
            
    except Exception as e:
        sys.stderr.write(f"[MCP] ERROR: {{str(e)}}\\n")
        sys.stderr.flush()
        return {{"error": str(e)}}
'''
        else:
            # Read function - make it async
            tool_code = f'''@mcp.tool()
async def {func_name}({params}):
    """Get {func_name} from the contract.
    
    {param_docs}
    """
    try:
        sys.stderr.write(f"[MCP] Calling view function {func_name}\\n")
        sys.stderr.flush()
        
        # CRITICAL FIX: Add explicit timeout and error handling
        try:
            # Create a call with explicit timeout
            result = contract.functions.{func_name}({params}).call(block_identifier='latest')
            
            sys.stderr.write(f"[MCP] Result: {{result}}\\n")
            sys.stderr.flush()
            
            # Handle different return types
            if isinstance(result, bytes):
                result = result.hex()
            elif isinstance(result, tuple):
                result = list(result)
            
            return {{"result": result}}
            
        except Exception as call_error:
            error_msg = str(call_error)
            sys.stderr.write(f"[MCP] Contract call failed: {{error_msg}}\\n")
            sys.stderr.flush()
            
            # Try to diagnose the issue
            if "execution reverted" in error_msg.lower():
                return {{"error": "Contract execution reverted. The function may require different parameters or the contract state doesn't allow this call."}}
            elif "invalid opcode" in error_msg.lower():
                return {{"error": "Invalid contract bytecode. The contract may not be deployed correctly."}}
            elif "timeout" in error_msg.lower():
                return {{"error": "RPC timeout. Check your blockchain connection."}}
            else:
                return {{"error": f"Contract call failed: {{error_msg}}"}}
        
    except Exception as e:
        error_msg = str(e)
        sys.stderr.write(f"[MCP] EXCEPTION: {{error_msg}}\\n")
        sys.stderr.flush()
        return {{"error": error_msg}}
'''
        
        tool_functions.append(tool_code)
    
    # Build complete server code with connection validation
    server_code = f'''#!/usr/bin/env python3
import os
import json
import sys
from pathlib import Path

sys.stderr.write("[MCP] Starting server initialization...\\n")
sys.stderr.flush()

try:
    from web3 import Web3
    from dotenv import load_dotenv
    from fastmcp import FastMCP
    sys.stderr.write("[MCP] Imports successful\\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"[MCP] Import error: {{e}}\\n")
    sys.stderr.flush()
    sys.exit(1)

# Load .env from the same directory as this script
env_path = Path(__file__).parent / '.env'
sys.stderr.write(f"[MCP] Loading env from: {{env_path}}\\n")
sys.stderr.flush()
load_dotenv(dotenv_path=env_path)

# Load ABI
abi_path = Path(__file__).parent / '{contract_name}.abi.json'
sys.stderr.write(f"[MCP] Loading ABI from: {{abi_path}}\\n")
sys.stderr.flush()
try:
    with open(abi_path, 'r') as f:
        contract_abi = json.load(f)
    sys.stderr.write(f"[MCP] ABI loaded ({{len(contract_abi)}} items)\\n")
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write(f"[MCP] ABI load error: {{e}}\\n")
    sys.stderr.flush()
    sys.exit(1)

# Get environment variables
RPC_URL = os.getenv('RPC_URL')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
ACCOUNT_ADDRESS = os.getenv('ACCOUNT_ADDRESS')

sys.stderr.write(f"[MCP] RPC_URL: {{RPC_URL}}\\n")
sys.stderr.flush()
sys.stderr.write(f"[MCP] CONTRACT_ADDRESS: {{CONTRACT_ADDRESS}}\\n")
sys.stderr.flush()
sys.stderr.write(f"[MCP] ACCOUNT_ADDRESS: {{ACCOUNT_ADDRESS}}\\n")
sys.stderr.flush()

# Initialize Web3 with timeout
try:
    web3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={{'timeout': 10}}))
    
    # Test connection immediately
    if not web3.is_connected():
        sys.stderr.write(f"[MCP] ERROR: Cannot connect to RPC at {{RPC_URL}}\\n")
        sys.stderr.flush()
        sys.exit(1)
    
    sys.stderr.write(f"[MCP] Web3 connected successfully\\n")
    sys.stderr.flush()
    
    # Test if we can get latest block (verifies RPC is working)
    try:
        latest_block = web3.eth.block_number
        sys.stderr.write(f"[MCP] Latest block: {{latest_block}}\\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"[MCP] WARNING: Cannot get latest block: {{e}}\\n")
        sys.stderr.flush()
    
except Exception as e:
    sys.stderr.write(f"[MCP] Web3 connection error: {{e}}\\n")
    sys.stderr.flush()
    sys.exit(1)

# Set up account and contract
try:
    account_address = Web3.to_checksum_address(ACCOUNT_ADDRESS)
    contract_address_checksum = Web3.to_checksum_address(CONTRACT_ADDRESS)
    
    # Verify contract exists
    try:
        code = web3.eth.get_code(contract_address_checksum)
        if code == b'' or code == '0x':
            sys.stderr.write(f"[MCP] ERROR: No contract code at address {{contract_address_checksum}}\\n")
            sys.stderr.flush()
            sys.exit(1)
        sys.stderr.write(f"[MCP] Contract code verified ({{len(code)}} bytes)\\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"[MCP] ERROR checking contract code: {{e}}\\n")
        sys.stderr.flush()
        sys.exit(1)
    
    contract = web3.eth.contract(address=contract_address_checksum, abi=contract_abi)
    sys.stderr.write(f"[MCP] Contract initialized successfully\\n")
    sys.stderr.flush()
    
except Exception as e:
    sys.stderr.write(f"[MCP] Contract setup error: {{e}}\\n")
    sys.stderr.flush()
    sys.exit(1)

# Create FastMCP instance
mcp = FastMCP("{contract_name}")
sys.stderr.write("[MCP] FastMCP instance created\\n")
sys.stderr.flush()

# Log registered tools
sys.stderr.write("[MCP] Attempting to list registered tools...\\n")
sys.stderr.flush()
try:
    import inspect
    tool_count = 0
    for name, obj in inspect.getmembers(mcp):
        if name.startswith('_'):
            continue
        if callable(obj):
            tool_count += 1
    sys.stderr.write(f"[MCP] MCP has {{tool_count}} callable members\\n")
    sys.stderr.flush()
    
    # Try to get registered tools from FastMCP's internal registry
    if hasattr(mcp, '_tools'):
        sys.stderr.write(f"[MCP] Internal _tools attribute: {{mcp._tools}}\\n")
        sys.stderr.flush()
    
    if hasattr(mcp, 'tools'):
        sys.stderr.write(f"[MCP] Tools property: {{mcp.tools}}\\n")
        sys.stderr.flush()
        
except Exception as e:
    sys.stderr.write(f"[MCP] Could not inspect tools: {{e}}\\n")
    sys.stderr.flush()

''' + '\n'.join(tool_functions) + '''

if __name__ == "__main__":
    sys.stderr.write("[MCP] Starting mcp.run()...\\n")
    sys.stderr.flush()
    
    try:
        mcp.run()
    except Exception as e:
        sys.stderr.write(f"[MCP] Runtime error: {{e}}\\n")
        sys.stderr.flush()
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
'''
    
    return server_code





@app.route('/api/translate', methods=['POST'])
def translate_contract_endpoint():
    """Legacy endpoint - redirects to stream"""
    return translate_stream()


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "mcp_connected": current_mcp_client is not None})


@app.route('/api/random-contract', methods=['GET'])
def random_contract():
    """Get a random contract from the dataset (requirement_fsm_code.jsonl)"""
    import random
    
    try:
        # Path to dataset
        dataset_path = Path(__file__).parent.parent / 'requirement_fsm_code.jsonl'
        
        if not dataset_path.exists():
            return jsonify({
                "error": "Dataset not found",
                "path": str(dataset_path)
            }), 404
        
        # Read all contracts
        contracts = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        contract = json.loads(line)
                        contracts.append(contract)
                    except json.JSONDecodeError:
                        continue
        
        if not contracts:
            return jsonify({"error": "No contracts found in dataset"}), 404
        
        # Select random contract
        random_contract = random.choice(contracts)
        
        # Extract relevant fields
        return jsonify({
            "user_requirement": random_contract.get('user_requirement', ''),
            "version": random_contract.get('version', '0.8.0'),
            "fsm": random_contract.get('FSM', ''),
            "reference_code": random_contract.get('code', ''),
            "total_contracts": len(contracts)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "Failed to load contract from dataset"
        }), 500


@app.route('/api/test', methods=['GET'])
def test():
    """Test endpoint to verify API is working"""
    return jsonify({
        "status": "ok",
        "message": "API is working correctly",
        "openai_key": "✓ Set" if OPENAI_API_KEY else "❌ Not set",
        "translator_importable": True
    })


@app.route('/api/connect', methods=['POST'])
def connect_mcp():
    """Connect to MCP server"""
    global current_mcp_client, current_tools, current_contract_type
    
    data = request.json
    mcp_path = data.get('mcp_path')
    contract_type = data.get('contract_type', 'sales')
    
    # If already connected, return current connection
    if current_mcp_client:
        tool_names = []
        for t in current_tools:
            if hasattr(t, 'name'):
                tool_names.append(t.name)
            else:
                tool_names.append(t.get('name', 'unknown'))
        
        return jsonify({
            "status": "already_connected",
            "tools": tool_names,
            "count": len(current_tools)
        })
    
    if not mcp_path:
        return jsonify({"error": "No mcp_path provided"}), 400
    
    try:
        # Convert env file path to MCP server script path if needed
        mcp_file = Path(mcp_path)
        if mcp_file.name == ".env":
            # Look for MCP server in the same directory
            parent_dir = mcp_file.parent
            mcp_scripts = list(parent_dir.glob("*_mcp_server.py"))
            if mcp_scripts:
                mcp_file = mcp_scripts[0]
            else:
                # MCP server not found
                current_contract_type = contract_type
                return jsonify({
                    "status": "not_found",
                    "tools": [],
                    "count": 0,
                    "message": "MCP server script not found for this contract type."
                })
        
        if not mcp_file.exists():
            return jsonify({"error": f"MCP server not found: {mcp_file}"}), 404
        
        print(f"📡 Launching MCP server: {mcp_file}")
        
        global current_mcp_process
        
        # Kill any existing process
        if current_mcp_process:
            try:
                current_mcp_process.terminate()
                current_mcp_process.wait(timeout=2)
            except:
                current_mcp_process.kill()
        
        # Launch MCP server as subprocess
        try:
            # Use python to run the MCP server script
            python_exe = sys.executable
            current_mcp_process = subprocess.Popen(
                [python_exe, str(mcp_file)],
                cwd=str(mcp_file.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            print(f"   Process started (PID: {current_mcp_process.pid})")
            
            # Start a thread to capture MCP server output
            def capture_mcp_output():
                try:
                    print(f"   📺 MCP Server Output Stream:")
                    print(f"   " + "="*60)
                    if current_mcp_process.stdout:
                        for line in iter(current_mcp_process.stdout.readline, ''):
                            if line:
                                print(f"   [MCP] {line.rstrip()}")
                except Exception as e:
                    print(f"   ⚠️  Error reading MCP output: {str(e)}")
            
            import threading
            mcp_output_thread = threading.Thread(target=capture_mcp_output, daemon=True)
            mcp_output_thread.start()
            
            # Wait for server to start
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Failed to launch MCP server: {str(e)}")
            return jsonify({"error": f"Failed to launch MCP server: {str(e)}"}), 500
        
        # Now try to connect
        try:
            print(f"📡 Connecting to MCP server...")
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def connect():
                # Give server more time to initialize with retries
                for attempt in range(5):
                    try:
                        print(f"   Connection attempt {attempt + 1}/5...")
                        print(f"   Creating Client with: {str(mcp_file)}")
                        client = Client(str(mcp_file))
                        print(f"   Client created, entering context...")
                        await client.__aenter__()
                        print(f"   Context entered, listing tools...")
                        tools = await client.list_tools()
                        print(f"   Tools listed successfully: {len(tools)} tools")
                        return client, tools
                    except Exception as e:
                        print(f"   Attempt {attempt + 1} failed: {type(e).__name__}: {str(e)}")
                        if attempt < 4:
                            print(f"   Waiting 1 second before retry...")
                            await asyncio.sleep(1)
                        else:
                            raise
            
            current_mcp_client, current_tools = loop.run_until_complete(connect())
            current_contract_type = contract_type
            
            tool_names = []
            for t in current_tools:
                if hasattr(t, 'name'):
                    tool_names.append(t.name)
                else:
                    tool_names.append(t.get('name', 'unknown'))
            
            print(f"✅ Connected! Found {len(tool_names)} tools: {tool_names}")
            
            return jsonify({
                "status": "connected",
                "tools": tool_names,
                "count": len(current_tools)
            })
            
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Kill the process if connection failed
            if current_mcp_process:
                try:
                    current_mcp_process.terminate()
                except:
                    pass
            return jsonify({"error": f"Connection failed: {str(e)}"}), 500
    
    except Exception as e:
        print(f"❌ Outer error in connect: {str(e)}")
        import traceback
        traceback.print_exc()
        # Kill the process if anything failed
        if current_mcp_process:
            try:
                current_mcp_process.terminate()
            except:
                pass
        return jsonify({"error": f"Connection setup failed: {str(e)}"}), 500


def _sync_decide_tool_call(user_input: str, tools: list, contract_type: str) -> dict:
    """Synchronous version of tool selection using LLM"""
    import json
    
    tool_descriptions = []
    for t in tools:
        if hasattr(t, 'name'):
            name = t.name
            desc = t.description if hasattr(t, 'description') else 'No description'
        else:
            name = t.get('name', 'unknown')
            desc = t.get('description', 'No description')
        
        tool_descriptions.append(f"- {name}: {desc}")
    
    tool_descriptions_str = "\n".join(tool_descriptions)
    
    messages = [
        system_message(
            f"""You are an AI assistant managing a {contract_type} smart contract.

Your job is to understand what the user wants and decide which contract tool to call.

Available tools:
{tool_descriptions_str}

When the user makes a request, respond with ONLY valid JSON (no explanations or markdown).
Format: {{"tool": "function_name", "args": {{"param1": value1, "param2": value2}}}}

If the user's request doesn't match any tool, respond with {{"tool": "none", "explanation": "I don't see a matching function for that request"}}"""
        ),
        user_message(
            f"""User request: "{user_input}"

Respond with ONLY the JSON, no extra text."""
        )
    ]
    
    try:
        print("   Calling LLM to decide tool...")
        response = llm.chat(messages=messages, timeout=10)  # 10 second timeout
        response_text = str(response).strip()
        print(f"   LLM response: {response_text[:100]}...")
        
        # Remove markdown fences if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(response_text)
            return result
        except Exception as e:
            print(f"   ⚠️  Failed to parse LLM response as JSON: {response_text}")
            return {"tool": "none", "explanation": f"Could not parse response: {response_text}"}
    
    except Exception as e:
        print(f"   ❌ LLM error: {str(e)}")
        return {"error": f"LLM failed: {str(e)}", "tool": "none"}


def _sync_call_mcp_tool(tool_name: str, args: dict) -> str:
    """Call an MCP tool synchronously with enhanced debugging"""
    global current_mcp_client, current_mcp_process
    
    if not current_mcp_client:
        raise Exception("MCP client not connected")
    
    print(f"   📞 Calling tool: {tool_name}")
    print(f"   Arguments: {args}")
    if current_mcp_process:
        print(f"   MCP Process ID: {current_mcp_process.pid}")
        print(f"   Process Status: {'Running' if current_mcp_process.poll() is None else 'Terminated'}")
    
    # Call tool with extended timeout
    import time
    start = time.time()
    
    try:
        # Create a coroutine for the tool call
        coro = current_mcp_client.call_tool(tool_name, args)
        
        # Run it in a new event loop (since we're in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print(f"   ⏳ Waiting for MCP server response (timeout: 30s)...")
            # Increase timeout to 30 seconds for MCP tool execution
            result = loop.run_until_complete(asyncio.wait_for(coro, timeout=30.0))
            elapsed = time.time() - start
            print(f"   ✅ Tool returned successfully in {elapsed:.2f}s")
            
            # Format the result for display
            if isinstance(result, dict):
                result_str = json.dumps(result, indent=2)
            elif isinstance(result, str):
                result_str = result
            else:
                result_str = str(result)
            
            print(f"   Result preview: {result_str[:200]}...")
            return result_str
        finally:
            loop.close()
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"   ⏱️  Tool execution timed out after {elapsed:.2f}s")
        
        # Check if MCP process is still alive
        if current_mcp_process:
            poll_result = current_mcp_process.poll()
            if poll_result is not None:
                print(f"   ⚠️  MCP process has terminated with code: {poll_result}")
            else:
                print(f"   ⚠️  MCP process still running but tool is not responding")
        
        error_msg = f"Tool execution timed out after {elapsed:.2f}s. The MCP server may be unresponsive, the smart contract interaction may be failing silently, or there may be an issue with the generated MCP server code."
        print(f"   ❌ {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"Tool execution failed after {elapsed:.2f}s: {type(e).__name__}: {str(e)}"
        print(f"   ❌ {error_msg}")
        print(f"   \n   DEBUG INFO:")
        print(f"      - Tool: {tool_name}")
        print(f"      - Args: {args}")
        if current_mcp_process:
            print(f"      - MCP Process running: {current_mcp_process.poll() is None}")
        import traceback
        print(f"      - Traceback: {traceback.format_exc()}")
        raise


@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat message and call MCP tools"""
    global current_mcp_client, current_tools, current_contract_type
    
    print("\n" + "="*70)
    print("📨 /api/chat POST request received")
    print("="*70)
    
    data = request.json
    print(f"Request data: {data}")
    
    if not data:
        print("❌ No JSON data in request")
        return jsonify({"error": "No data provided"}), 400
    
    user_input = data.get('message', '').strip()
    print(f"User message: '{user_input}'")
    
    if not user_input:
        print("❌ Empty message received")
        return jsonify({"error": "Empty message"}), 400
    
    # If MCP client not connected, provide helpful response
    if not current_mcp_client:
        print("⚠️  MCP client not connected")
        return jsonify({
            "user_input": user_input,
            "response": "⚠️ MCP server not connected. Please connect to an MCP server first using the connect endpoint.",
            "success": False,
            "tool_called": None,
            "mcp_status": "disconnected"
        }), 200
    
    try:
        print("📡 Deciding which tool to call...")
        
        # Use synchronous version of tool selection
        decision = _sync_decide_tool_call(user_input, current_tools, current_contract_type)
        print(f"Decision: {decision}")
        
        if "error" in decision or decision.get("tool") == "none":
            response_text = decision.get("explanation", decision.get("error", "Could not process request"))
            print(f"✓ No matching tool found: {response_text}")
            return jsonify({
                "user_input": user_input,
                "response": response_text,
                "success": False,
                "tool_called": None
            }), 200
        
        tool_name = decision.get("tool")
        args = decision.get("args", {})
        print(f"📞 Calling tool: {tool_name} with args: {args}")
        
        # Call the tool synchronously
        try:
            result = _sync_call_mcp_tool(tool_name, args)
            print(f"✓ Tool result: {result}")
            return jsonify({
                "user_input": user_input,
                "tool_called": tool_name,
                "arguments": args,
                "response": str(result),
                "success": True
            }), 200
        except Exception as e:
            error_msg = f"Error calling tool {tool_name}: {str(e)}"
            print(f"❌ {error_msg}")
            return jsonify({
                "user_input": user_input,
                "tool_called": tool_name,
                "arguments": args,
                "response": error_msg,
                "success": False
            }), 200
    
    except Exception as e:
        error_msg = f"Chat processing error: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": error_msg,
            "user_input": user_input
        }), 500


@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get list of available tools"""
    if not current_mcp_client:
        return jsonify({"tools": [], "error": "Not connected"}), 400
    
    tool_info = []
    for t in current_tools:
        if hasattr(t, 'name'):
            name = t.name
            desc = t.description if hasattr(t, 'description') else ''
        else:
            name = t.get('name', 'unknown')
            desc = t.get('description', '')
        
        tool_info.append({"name": name, "description": desc})
    
    return jsonify({"tools": tool_info})


if __name__ == '__main__':
    import threading
    import time
    from werkzeug.serving import run_simple
    
    print("Starting Chatbot API Server...")
    print("Available endpoints:")
    print("  GET  /api/health          - Health check")
    print("  GET  /api/random-contract - Get random contract from dataset")
    print("  GET  /api/test            - Test endpoint")
    print("  POST /api/translate-stream - Translate contract (streaming)")
    print("  POST /api/translate       - Translate contract PDF")
    print("  POST /api/connect         - Connect to MCP server")
    print("  POST /api/chat            - Send chat message")
    print("  GET  /api/tools           - List available tools")
    print("\nServer running on http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    # Set Flask to log output
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    
    # Run server with logging enabled (blocking, so logs show)
    try:
        app.run(debug=False, port=5000, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        exit(0)
