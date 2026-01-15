# IBM Agentics Contract Translator - Research & Evaluation Guide

## 📋 Overview

> **Research Focus**: This application demonstrates a 6-phase semantic translation pipeline for converting natural language contract descriptions into Solidity smart contracts. The focus is on evaluating the quality and accuracy of AI-generated smart contracts using a research dataset.

The system integrates:

1. **Dataset-Driven Translation** - Process contracts from `requirement_fsm_code.jsonl` (21,976 contracts)
2. **6-Phase Contract Translation** - Automated AI-powered contract to Solidity conversion
3. **Security Analysis** - Automated security audit of generated code
4. **Code Quality Assessment** - Output files for analysis and evaluation
5. **MCP Server Generation** - FastMCP server templates for potential deployment

**Note**: Automatic deployment features have been removed to focus on contract generation quality research. Generated contracts can be manually deployed for testing if needed.

## 🗂️ Dataset Structure

The dataset (`requirement_fsm_code.jsonl`) contains:
- **Format**: JSONL (one contract per line)
- **Total Contracts**: 21,976
- **Fields per contract**:
  - `user_requirement`: Natural language contract description
  - `FSM`: Finite state machine representation (JSON)
  - `version`: Solidity version
  - `code`: Reference Solidity implementation

### Sample Contract Entry
```json
{
  "user_requirement": "This smart contract is a [rental agreement] for property leasing...",
  "FSM": "{\"contractName\": \"RentalContract\", ...}",
  "version": "0.8.0",
  "code": "pragma solidity ^0.8.0; contract RentalAgreement { ... }"
}
```

## 🎯 How It Works (Complete Workflow)

### Phase 0: Contract Input
- **Input Method**: Paste natural language contract description from dataset
- **Alternative**: Use `sampler.html` to load random contracts from the dataset
- **Contract Types**: Automatically detected from description (sales, rental, NDA, etc.)
- **Research Focus**: Process and evaluate contracts from the standardized dataset

### Phases 1-6: Automated Translation

#### Phase 1: Document Processing 📄
- **Input**: Natural language contract description
- **Process**: Validates and prepares text for analysis
- **Output**: Processed contract text with character count
- **Research Value**: Evaluate text processing and validation

#### Phase 2: Contract Analysis 🔍
- **Input**: Contract description text
- **Process**: IBM Agentics parses parties, financial terms, conditions
- **Output**: Structured contract schema (parties, amount, dates, etc.)
- **Research Value**: Assess semantic understanding and schema extraction accuracy against FSM ground truth

#### Phase 3: Code Generation ⚙️
- **Input**: Contract schema from Phase 2
- **Process**: LLM (gpt-4o-mini) generates Solidity smart contract
- **Output**: Complete, compilable Solidity code (~100-200 lines)
- **Features**: Functions, events, modifiers, state variables
- **Research Value**: Compare generated code against reference implementation in dataset

#### Phase 4: Security Audit 🔐
- **Input**: Generated Solidity contract
- **Process**: Analyzes for vulnerabilities (reentrancy, state issues, etc.)
- **Output**: Security report with severity level (Low/Medium/High)
- **Research Value**: Measure security awareness in generated vs. reference code

#### Phase 5: ABI Generation 📋
- **Input**: Solidity contract code
- **Process**: Extracts Application Binary Interface (ABI)
- **Output**: JSON ABI file with function signatures and types
- **Research Value**: Verify function interface consistency

#### Phase 6: MCP Server Generation 🤖
- **Input**: ABI and contract schema
- **Process**: Generates FastMCP Python server template with tools for each function
- **Output**: Standalone Python MCP server script
- **Features**: 
  - Template for loading configuration
  - @mcp.tool() decorated functions for each contract function
  - Handles payable, non-payable, and view functions
  - Error handling and transaction patterns
- **Research Value**: Evaluate API generation quality

### Output Files for Research

After the 6-phase pipeline completes, the following files are generated:

1. **[ContractName].sol** - Solidity source code
   - Use for: Code quality analysis, security review, compilation testing

2. **[ContractName].abi.json** - Contract ABI
   - Use for: Interface analysis, deployment testing

3. **security_audit.json** - Security analysis report
   - Use for: Security pattern evaluation, vulnerability assessment

4. **contract_schema.json** - Parsed contract data
   - Use for: Semantic accuracy evaluation

5. **[ContractName]_mcp_server.py** - MCP server template
   - Use for: API design evaluation (optional deployment for testing)

## 🔬 Research Workflow: Using the Dataset

### Option 1: Using the Dataset Browser (sampler.html)

1. **Open the Dataset Browser**
   ```bash
   # Navigate to the contract-translator directory
   cd applications/contract-translator
   
   # Open sampler.html in your browser
   # Double-click the file or open with: chrome sampler.html
   ```

2. **Browse Contracts**
   - Click "Load Random Contract" to load a sample from the dataset
   - View contract description and metadata (FSM, version, code preview)
   - Click "Copy to Clipboard" to copy the contract description
   - Click "Open in Demo" to automatically load it into the translator

3. **Process the Contract**
   - The contract description is automatically loaded into the demo page
   - Contract type is auto-detected from the description
   - Click "Translate Contract" to start the 6-phase pipeline

### Option 2: Direct Text Input (demo.html)

1. **Open the Demo Page**
   ```bash
   python launch_demo.py
   # Opens demo at http://localhost:5001
   ```

2. **Paste Contract Description**
   - Manually copy any contract from `requirement_fsm_code.jsonl`
   - Paste into the large text area on the demo page
   - Select contract type (or let it auto-detect)
   - Click "Translate Contract"

### Option 3: Batch Processing (Python Script)

For evaluating 100 contracts at once, use the dataset loader:

```python
from dataset_loader import ContractDatasetLoader

# Load a sample of 100 contracts
loader = ContractDatasetLoader('requirement_fsm_code.jsonl')
sample = loader.get_sample(n=100, seed=42)  # seed for reproducibility

# Process each contract
for idx, contract in enumerate(sample):
    contract_text = loader.extract_contract_text(contract)
    metadata = loader.get_contract_metadata(contract)
    
    print(f"Processing contract {idx+1}/100")
    print(f"Version: {metadata['version']}")
    
    # Call translation API
    # Compare generated code vs. metadata['reference_code']
    # Collect metrics (security scores, compilation success, etc.)
```

### Research Evaluation Metrics

When evaluating generated contracts, consider:

1. **Compilation Success Rate** - Does the generated code compile?
2. **Security Score** - What severity level from the audit?
3. **Semantic Accuracy** - Does the generated contract match the FSM structure?
4. **Code Quality** - Follows Solidity best practices?
5. **Completeness** - All parties, terms, and conditions represented?

Compare against reference implementations in the dataset:
- **FSM Matching**: Does the contract structure align with the ground truth FSM?
- **Function Parity**: Are all expected functions present?
- **Variable Coverage**: Are all key contract terms captured as state variables?

### Optional: Manual Testing & Deployment

If you wish to test the generated contracts on a blockchain:

#### Step 1: Manual Deployment via Remix IDE
1. Copy the generated `.sol` file
2. Open [Remix IDE](https://remix.ethereum.org)
3. Create new file, paste Solidity code
4. Compile using the version from the contract (e.g., 0.8.0)
5. Deploy to a local testnet (Ganache) or test network (Sepolia)
6. Record the deployed contract address

#### Step 2: Manual Testing with MCP Server (Optional)
1. Update the generated `_mcp_server.py` with your contract address
2. Set up `.env` file with RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS
3. Run the MCP server to interact with deployed contract
4. Use Claude Desktop or other MCP clients to test contract functions

**Note**: Deployment is optional for research purposes. The focus is on evaluating generated code quality, security, and semantic accuracy rather than on-chain execution.


## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install ibm-agentics PyPDF2 pydantic fastmcp

# Ensure you have the dataset
# File: applications/requirement_fsm_code.jsonl (21,976 contracts)
```

### Running the Application

1. **Start the Translation API**
   ```bash
   cd applications/contract-translator
   python launch_demo.py
   ```
   This launches:
   - Flask API on http://localhost:5000
   - Demo UI on http://localhost:5001

2. **Option A: Browse Dataset with Sampler**
   ```bash
   # Open sampler.html in your browser
   # Click "Load Random Contract" to explore the dataset
   # Click "Open in Demo" to translate a contract
   ```

3. **Option B: Direct Text Input**
   - Open http://localhost:5001
   - Paste a contract description from the dataset
   - Click "Translate Contract"

4. **Download Results**
   - After 6-phase pipeline completes
   - Download `.sol`, `.abi.json`, `_mcp_server.py` files
   - Use for research analysis and evaluation

## 📁 Files Generated/Used

### Research Output Structure

```
output/
├── ContractName_TIMESTAMP/
│   ├── ContractName.sol                 # Generated Solidity source code
│   ├── ContractName.abi.json            # Function signatures (JSON)
│   ├── security_audit.json              # Security findings (Low/Medium/High)
│   ├── contract_schema.json             # Parsed contract structure
│   ├── ContractName_mcp_server.py       # FastMCP server template (optional)
│   └── README.md                        # Contract documentation
```

### Key Files for Research Evaluation:

**ContractName.sol**
- Generated Solidity smart contract (compare with dataset reference)
- Compilation test: Does it compile without errors?
- Quality metrics: Lines of code, function count, modifier usage
- Completeness: All parties, terms, conditions represented?

**security_audit.json**
- Security analysis results from Phase 4
- Severity level: Low/Medium/High
- Vulnerability types: Reentrancy, integer overflow, access control, etc.
- Compare security patterns vs. reference implementation

**contract_schema.json**
- Structured data extracted in Phase 2
- Parties, financial terms, dates, conditions
- Evaluate semantic accuracy: Does it match the FSM ground truth?

**ContractName.abi.json**
- Function interfaces (signatures, parameters, return types)
- Function parity check: Are all expected functions present?
- Compare against FSM-defined functions

**ContractName_mcp_server.py**
- FastMCP server template for potential deployment testing
- Optional: Deploy and test contract execution
- Not required for static analysis and research evaluation

## 🔬 Research Evaluation Example

### Scenario: Evaluating 100 Rental Agreements

1. **Load Sample from Dataset**
   ```python
   from dataset_loader import ContractDatasetLoader
   
   loader = ContractDatasetLoader('requirement_fsm_code.jsonl')
   sample = loader.get_sample(n=100, seed=42)
   ```

2. **Process Each Contract**
   - Extract contract description with `loader.extract_contract_text()`
   - Send to translation API
   - Collect generated `.sol`, `security_audit.json`, `contract_schema.json`

3. **Evaluate Metrics**
   - **Compilation Success**: Use `solc` to attempt compilation
   - **Security Scores**: Parse `security_audit.json` for severity counts
   - **FSM Matching**: Compare `contract_schema.json` against ground truth FSM
   - **Code Quality**: Static analysis (function count, state variables, events)

4. **Compare with Reference**
   ```python
   metadata = loader.get_contract_metadata(sample[0])
   reference_code = metadata['reference_code']  # Ground truth from dataset
   reference_fsm = metadata['fsm']              # Expected structure
   
   # Compare generated vs. reference
   # - Function coverage
   # - Variable completeness
   # - Security patterns
   ```

5. **Generate Research Report**
   - Aggregate metrics across 100 contracts
   - Identify common failure patterns
   - Measure translation quality improvements


            │ Downloads files
            ↓
┌─────────────────────────────────────────────────┐
│    User's Filesystem (Local Directory)          │
│  • contract.sol (to Remix)                      │
│  • contract.abi.json                            │
│  • mcp_server.py (Python)                       │
│  • .env (user configures)                       │
└───────────┬─────────────────────────────────────┘
            │
            │ User deploys via Remix
            ↓
┌─────────────────────────────────────────────────┐
│      Remix IDE (remix.ethereum.org)             │
│  • Compile .sol                                 │
│  • Deploy to Ganache                            │
│  • Get contract address                         │
└───────────┬─────────────────────────────────────┘
            │
            │ User updates .env with address
            ↓
┌─────────────────────────────────────────────────┐
│   MCP Server (mcp_server.py - Python)           │
│  • Loads local .env                             │
│  • Loads .abi.json                              │
│  • Creates Web3.py contract instance            │
│  • Exposes functions as MCP tools               │
└───────────┬─────────────────────────────────────┘
            │ stdio

## 🛠️ Architecture

### Technology Stack (Research Focus)

```
┌─────────────────────────────────────────────────┐
│         Browser (demo.html - React)             │
│  • Text input for contract descriptions         │
│  • 6-phase visualization                        │
│  • File download buttons                        │
└───────────┬─────────────────────────────────────┘
            │ HTTP POST (FormData with contract_text)
            ↓
┌─────────────────────────────────────────────────┐
│    Flask API (chatbot_api.py)                   │
│  • /api/translate-stream endpoint               │
│  • Accepts text or PDF input                    │
│  • Saves to temp .txt or .pdf file              │
└───────────┬─────────────────────────────────────┘
            │ file_path
            ↓
┌─────────────────────────────────────────────────┐
│  Translation Engine (agentic_implementation.py) │
│  • ContractTranslator.translate_contract()      │
│  • 6-phase pipeline orchestration               │
└───────────┬─────────────────────────────────────┘
            │ yields phase updates
            ↓
┌─────────────────────────────────────────────────┐
│       IBM Agentics Framework                    │
│  • UniversalContractParserProgram (Phase 2)     │
│  • SolidityGeneratorProgram (Phase 3)           │
│  • SecurityAuditorProgram (Phase 4)             │
│  • ABIGeneratorProgram (Phase 5)                │
│  • MCPGeneratorProgram (Phase 6)                │
└───────────┬─────────────────────────────────────┘
            │ generated files
            ↓
┌─────────────────────────────────────────────────┐
│          Output Files (output/)                 │
│  • .sol (Solidity source code)                  │
│  • .abi.json (Contract interface)               │
│  • security_audit.json (Security report)        │
│  • contract_schema.json (Parsed structure)      │
│  • _mcp_server.py (MCP template)                │
└─────────────────────────────────────────────────┘
```

### Dataset Integration

```
requirement_fsm_code.jsonl (21,976 contracts)
         ↓
dataset_loader.py (Python module)
    ├── load_contracts(max_contracts)
    ├── get_sample(n=100, seed=42)
    ├── extract_contract_text(contract)
    └── get_contract_metadata(contract)
         ↓
sampler.html (Browser UI)
    ├── loadRandomContract()
    ├── copyToClipboard()
    └── openInDemo() → localStorage
         ↓
demo.html (React UI)
    ├── useEffect loads from localStorage
    └── Submits contract_text to API
```

## 📊 What You Can Learn

This demo teaches:

1. **Contract Translation**: How natural language becomes smart contracts using LLMs
2. **Security Analysis**: Identifying blockchain vulnerabilities (reentrancy, overflow, etc.)
3. **ABI Generation**: Understanding function signatures and interfaces
4. **MCP Integration**: Exposing smart contracts as AI-accessible tools
5. **AI Orchestration**: Multi-phase LLM pipelines with IBM Agentics
6. **Research Evaluation**: Systematic quality assessment of AI-generated code
7. **Dataset Processing**: Working with JSONL datasets and ground truth comparisons

## 🔧 Key Files

- [demo.html](demo.html) - React UI for translation demo
- [sampler.html](sampler.html) - Dataset browser for contract selection
- [chatbot_api.py](chatbot_api.py) - Flask API for translation pipeline
- [agentic_implementation.py](agentic_implementation.py) - 6-phase translation engine
- [dataset_loader.py](dataset_loader.py) - Dataset loading and sampling utilities
- [launch_demo.py](launch_demo.py) - Auto-launcher for API and demo
- [requirement_fsm_code.jsonl](../requirement_fsm_code.jsonl) - 21,976 contract dataset



```javascript
const templates = {
    sales: `// Your Solidity code here`,
    custom: `// New contract type`,
};
```

## ⚠️ Important Notes

### For Local Development Only
- Ganache runs on local machine
- Private keys are fake test accounts
- No real funds or assets involved
- Perfect for learning and testing

### Production Considerations

## ⚠️ Important Notes

### Research vs. Production
- This system is designed for research and quality evaluation
- Generated contracts should be thoroughly reviewed before production use
- Security audits are automated but not comprehensive
- Always conduct manual security review for production deployment

### Dataset Considerations
- Dataset contains 21,976 contracts with varying quality
- Reference implementations (`code` field) provide ground truth for comparison
- FSM structures (`FSM` field) define expected contract architecture
- Use sampling (n=100) for initial experiments before scaling up

### Known Limitations
- Generated contracts may not compile if input is ambiguous or incomplete
- Security audit is pattern-based, not exhaustive
- Contract type detection is heuristic-based
- MCP server generation is optional for research purposes

## 📚 Next Steps

1. **Explore Dataset**: Open `sampler.html` to browse the 21,976 contracts
2. **Generate First Contract**: Load a sample and run through the 6-phase pipeline
3. **Collect Outputs**: Download `.sol`, `.abi.json`, `security_audit.json` files
4. **Evaluate Quality**: Compare generated code against reference implementation
5. **Process Batch**: Use `dataset_loader.py` to evaluate 100 contracts
6. **Analyze Results**: Aggregate metrics (compilation rate, security scores, FSM matching)
7. **Iterate**: Refine prompts and pipeline based on findings
8. **Optional Testing**: Deploy selected contracts to Remix/Ganache for functional testing

## 🆘 Troubleshooting

### Translation fails or produces invalid Solidity
**Cause**: Ambiguous or incomplete contract description  
**Solution**: Use dataset contracts with clear party definitions and terms

### Phase 2 (Contract Analysis) returns empty schema
**Cause**: Input text doesn't contain standard contract elements  
**Solution**: Ensure description includes parties, amounts, dates, conditions

### Security audit shows all High severity
**Cause**: Generated code lacks basic security patterns  
**Solution**: Review Phase 3 Solidity generator prompts, add security guidelines

### Downloaded files are empty or corrupted
**Cause**: Browser security restrictions or API errors  
**Solution**: Check browser console for errors, verify API response

### Can't load contracts from dataset
**Cause**: `requirement_fsm_code.jsonl` not found or malformed  
**Solution**: Verify file exists at `applications/requirement_fsm_code.jsonl` (183MB)

---

**Demo Version**: 2.0 (Research Edition)  
**Last Updated**: January 2025  
**Focus**: Contract generation quality evaluation with dataset-driven input

**Compatibility**: All modern browsers, Python 3.8+, Ganache CLI or Desktop
