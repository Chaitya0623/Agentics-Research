import json
from pathlib import Path
from typing import Dict, List, Optional
import PyPDF2
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

from agentics import LLM, Program, user_message, system_message

load_dotenv()

# ==================== PYDANTIC SCHEMAS ====================

class PartyRole(str, Enum):
    """Common party roles across all contracts"""
    BUYER = "buyer"
    SELLER = "seller"
    LANDLORD = "landlord"
    TENANT = "tenant"
    EMPLOYER = "employer"
    EMPLOYEE = "employee"
    LENDER = "lender"
    BORROWER = "borrower"
    SERVICE_PROVIDER = "service_provider"
    CLIENT = "client"
    INVESTOR = "investor"
    COMPANY = "company"
    OTHER = "other"

class ContractType(str, Enum):
    """All supported contract types"""
    RENTAL = "rental_agreement"
    EMPLOYMENT = "employment_contract"
    SALES = "sales_agreement"
    SERVICE = "service_agreement"
    LOAN = "loan_agreement"
    NDA = "non_disclosure_agreement"
    PARTNERSHIP = "partnership_agreement"
    INVESTMENT = "investment_agreement"
    LEASE = "lease_agreement"
    PURCHASE = "purchase_agreement"
    OTHER = "other"

class ContractParty(BaseModel):
    name: str
    role: str  
    address: Optional[str] = None 
    email: Optional[str] = None
    entity_type: Optional[str] = None

class FinancialTerm(BaseModel):
    """Universal financial term"""
    amount: float
    currency: str = "ETH"
    purpose: str 
    frequency: Optional[str] = None 
    due_date: Optional[str] = None

class ContractDate(BaseModel):
    date_type: str 
    value: Optional[str] = None
    day_of_month: Optional[int] = None
    frequency: Optional[str] = None

class ContractObligation(BaseModel):
    party: str  # Who has this obligation
    description: str
    deadline: Optional[str] = None
    penalty_for_breach: Optional[str] = None

class ContractAsset(BaseModel):
    type: str
    description: str
    location: Optional[str] = None
    quantity: Optional[int] = None
    value: Optional[float] = None

class UniversalContractSchema(BaseModel):
    contract_type: str
    title: Optional[str] = None
    parties: List[ContractParty]
    financial_terms: List[FinancialTerm] = []
    dates: List[ContractDate] = []
    assets: List[ContractAsset] = []
    obligations: List[ContractObligation] = []
    special_terms: List[str] = []
    conditions: Dict[str, Any] = {}
    termination_conditions: List[str] = []

class UniversalContractParserProgram(Program):
    def forward(self, contract_text: str, lm: LLM) -> UniversalContractSchema:
        """Parse any contract type"""
        
        messages = [
            system_message(
                """You are an expert contract analyst who extracts EXACT, SPECIFIC information from contracts.
                
                CRITICAL INSTRUCTIONS:
                1. Extract the EXACT function names mentioned in the contract (e.g., "initializeLease", "payRent", "confirmDelivery")
                2. Extract the EXACT variable names mentioned (e.g., "monthlyRent", "securityDeposit", "deliveryDate")
                3. Extract the EXACT state names mentioned (e.g., "Pending", "Active", "Completed", "Terminated")
                4. Extract the EXACT party roles as described in the contract
                5. DO NOT use generic placeholders - use the specific terminology from the contract
                6. Capture ALL conditions, transitions, and logic flows mentioned
                
                Your goal: Create a structured representation that preserves ALL specific details from the contract text."""
            ),
            user_message(
                f"""Analyze this contract and extract ALL SPECIFIC information exactly as mentioned.

CONTRACT TEXT:
{contract_text}

PAY CLOSE ATTENTION TO:
1. **Specific Function Names**: If the contract says "The main functions include [initializeLease(), payRent(), terminateLease()]", extract EXACTLY those names
2. **Specific Variable Names**: If it mentions "monthlyRent", "securityDeposit", "leaseStartDate", extract those EXACT names
3. **Specific States**: If it mentions states like "Initializing", "Active", "Processing", "Terminated", extract those EXACT state names
4. **State Transitions**: Capture the EXACT transition logic (e.g., "Initializing → Active when lease starts")
5. **Specific Conditions**: Extract the EXACT conditions mentioned (e.g., "rent must be paid by day 5 of each month")
6. **Specific Events**: If events are mentioned like "LeaseInitialized", "RentPaid", extract those EXACT names

Return ONLY valid JSON with this structure:
{{
    "contract_type": "rental|employment|sales|service|loan|nda|partnership|investment|other",
    "title": "specific contract title from text",
    "parties": [
        {{
            "name": "EXACT party name from contract",
            "role": "EXACT role as described (not generic)",
            "address": "blockchain address if mentioned",
            "email": "if mentioned",
            "entity_type": "individual|company|organization"
        }}
    ],
    "financial_terms": [
        {{
            "amount": number,
            "currency": "ETH|USD|etc",
            "purpose": "EXACT purpose from contract (not 'payment' but 'monthly rent' or 'security deposit')",
            "frequency": "EXACT frequency from contract",
            "due_date": "EXACT due date or day of month"
        }}
    ],
    "dates": [
        {{
            "date_type": "EXACT date type from contract (leaseStartDate, deliveryDeadline, etc)",
            "value": "date string if provided",
            "day_of_month": number or null,
            "frequency": "if recurring"
        }}
    ],
    "assets": [
        {{
            "type": "SPECIFIC asset type from contract",
            "description": "EXACT description from contract",
            "location": "if mentioned",
            "quantity": number or null,
            "value": number or null
        }}
    ],
    "obligations": [
        {{
            "party": "EXACT party name",
            "description": "EXACT obligation as written",
            "deadline": "EXACT deadline if mentioned",
            "penalty_for_breach": "EXACT penalty if mentioned"
        }}
    ],
    "special_terms": ["EXACT special conditions word-for-word"],
    "conditions": {{
        "function_names": ["EXACT function names from contract: initializeLease, payRent, etc"],
        "variable_names": ["EXACT variable names: monthlyRent, securityDeposit, tenantAddress, etc"],
        "state_names": ["EXACT state names: Pending, Active, Completed, Terminated, etc"],
        "state_transitions": ["EXACT transitions: Pending->Active when X, Active->Completed when Y"],
        "events": ["EXACT event names: LeaseInitialized, RentPaid, LeaseTerminated, etc"],
        "logic_conditions": ["EXACT conditions: rent due on day 5, penalty if late > 7 days, etc"]
    }},
    "termination_conditions": ["EXACT termination conditions from contract"]
}}

EXTRACT EVERYTHING SPECIFIC - DO NOT USE GENERIC NAMES OR PLACEHOLDERS."""
            )
        ]
        
        response = lm.chat(messages=messages)
        response_text = str(response).strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        
        parsed = json.loads(response_text)
        
        # ===== VALIDATION & CLEANUP =====
        # Ensure financial_terms have required fields
        if "financial_terms" in parsed and parsed["financial_terms"]:
            cleaned_terms = []
            for term in parsed["financial_terms"]:
                # Skip terms with None amount or currency
                if term.get("amount") is None or term.get("currency") is None:
                    continue
                # Ensure amount is a number
                try:
                    term["amount"] = float(term["amount"])
                except (ValueError, TypeError):
                    continue
                # Ensure currency is a string
                if not isinstance(term.get("currency"), str):
                    term["currency"] = "ETH"
                # Ensure purpose exists
                if not term.get("purpose"):
                    term["purpose"] = "Contract payment"
                cleaned_terms.append(term)
            parsed["financial_terms"] = cleaned_terms
        
        # Ensure parties have required fields
        if "parties" in parsed and parsed["parties"]:
            cleaned_parties = []
            for party in parsed["parties"]:
                if party.get("name"):  # Only keep parties with names
                    if not party.get("role"):
                        party["role"] = "other"
                    cleaned_parties.append(party)
            parsed["parties"] = cleaned_parties
        
        # Ensure at least one party
        if not parsed.get("parties"):
            parsed["parties"] = [{"name": "Unknown Party", "role": "other"}]
        
        # Ensure contract_type is set
        if not parsed.get("contract_type"):
            parsed["contract_type"] = "other"
        
        return UniversalContractSchema(**parsed)


class UniversalSolidityGeneratorProgram(Program):
    """Generates Solidity for ANY contract type"""
    
    def forward(self, schema: UniversalContractSchema, lm: LLM) -> str:
        """Generate contract-type-specific Solidity"""
 
        # Extract specific function names, variables, states from the parsed schema
        conditions = schema.conditions if schema.conditions else {}
        function_names = conditions.get('function_names', [])
        variable_names = conditions.get('variable_names', [])
        state_names = conditions.get('state_names', [])
        state_transitions = conditions.get('state_transitions', [])
        events = conditions.get('events', [])
        logic_conditions = conditions.get('logic_conditions', [])
        
        messages = [
            system_message(
                f"""You are a Solidity expert who generates COMPLETE, FUNCTIONAL smart contracts.
                
                CRITICAL GENERATION RULES - STRICT COMPLIANCE REQUIRED:
                
                1. SEMANTIC FIDELITY OVER NAME MATCHING
                   - Never generate functions without FULL implementation
                   - No placeholder logic, no "// logic goes here" comments
                   - Every function mentioned must have complete, executable behavior
                
                2. EXPLICIT STATE MACHINE ENFORCEMENT
                   - All states must be reachable and mutually exclusive
                   - State transitions use require() with clear error messages
                   - Never allow invalid state transitions
                   - Every state-dependent function must enforce valid state with require()
                
                3. ACCESS CONTROL MUST BE ENFORCED
                   - All administrative functions use modifiers (onlyOwner, onlyRole, etc)
                   - No state-changing function callable by arbitrary addresses unless specified
                   - Define and use access roles consistently
                
                4. NO SILENT FAILURES - PROHIBITED PATTERN
                   - NEVER use: if (condition) return;
                   - ALWAYS use: require(condition, "Error message");
                   - All invalid conditions MUST revert with descriptive messages
                
                5. ECONOMIC LOGIC MUST BE COMPLETE
                   - If pricing/fees/swaps/payments mentioned: implement ALL calculations
                   - Funds MUST be transferred or accounted for
                   - Variables like price, feeRate, amountRaised MUST be read and written in live logic
                   - No passive declarations - every financial variable must affect behavior
                
                6. TIME-BASED CONDITIONS MUST BE ENFORCED
                   - If deadlines/start times/durations mentioned: store AND check using block.timestamp
                   - Time variables MUST affect contract behavior
                   - Implement automatic state transitions based on time
                
                7. EVENT SEMANTICS MUST MATCH ACTIONS
                   - Events represent real, completed actions only
                   - Each state change or economic transfer emits separate, specific event
                   - Never merge unrelated actions into single event (e.g., no "TransferAndApproval")
                   - Event names must be clear: Transfer, Approval, Swap, Paused, etc
                
                8. NO UNUSED OR DECORATIVE CODE
                   - Every variable, state, function, event MUST be actively used
                   - If something cannot be implemented: either infer reasonable behavior or omit it
                   - No "filler" code
                
                9. STANDARD SOLIDITY SAFETY - MANDATORY
                   - Use require() for all validation
                   - Validate zero addresses
                   - Ensure invariants (e.g., total supply consistency)
                   - Use SafeMath patterns where needed
                
                10. INTERNAL COHERENCE REQUIRED
                    - Names must reflect actual behavior
                    - States correspond to real operational modes
                    - Functions must not contradict each other
                    - Variables must not represent multiple concepts
                
                FORBIDDEN PATTERNS:
                - Empty function bodies
                - Unused state variables
                - Silent failures (if/return pattern)
                - Placeholder comments
                - Decorative events that don't represent real actions
                - State variables that are never read
                - Time variables that are never checked
                - Access-controlled functions without modifiers
                
                YOUR GOAL: Generate production-ready, complete, semantically accurate Solidity code."""
            ),
            user_message(
                f"""Generate a COMPLETE, FUNCTIONAL Solidity ^0.8.0 smart contract that FULLY implements this specification.

CONTRACT ANALYSIS:
{schema.model_dump_json(indent=2)}

SPECIFIC REQUIREMENTS TO IMPLEMENT:

**EXACT Function Names to Implement (WITH FULL LOGIC):**
{chr(10).join(f"- {fn} (must be fully functional, not a stub)" for fn in function_names) if function_names else "- Extract function names from the obligations and implement them completely"}

**EXACT Variable Names to Use (MUST BE ACTIVELY USED IN LOGIC):**
{chr(10).join(f"- {vn} (must be read/written in functions, not decorative)" for vn in variable_names) if variable_names else "- Extract variable names from financial terms and dates"}

**EXACT State Names (MUST ALL BE REACHABLE WITH TRANSITIONS):**
{chr(10).join(f"- {sn} (implement transition logic TO and FROM this state)" for sn in state_names) if state_names else "- Determine if contract needs states based on transitions"}

**EXACT State Transitions (IMPLEMENT WITH require() CHECKS):**
{chr(10).join(f"- {st} (use require() to enforce this transition)" for st in state_transitions) if state_transitions else "- Implement any state changes mentioned in obligations"}

**EXACT Event Names (EMIT ON REAL ACTIONS ONLY):**
{chr(10).join(f"- {ev} (emit when the actual action completes)" for ev in events) if events else "- Create events based on function names (e.g., FunctionNameExecuted)"}

**EXACT Logic Conditions (IMPLEMENT WITH require() AND CALCULATIONS):**
{chr(10).join(f"- {lc} (enforce this condition in code)" for lc in logic_conditions) if logic_conditions else "- Implement conditions from obligations and special_terms"}

PARTIES TO HANDLE:
{chr(10).join(f"- {p.name} ({p.role}) - store as state variable with proper type" for p in schema.parties)}

FINANCIAL TERMS TO IMPLEMENT COMPLETELY:
{chr(10).join(f"- {t.purpose}: {t.amount} {t.currency} ({t.frequency if t.frequency else 'one-time'}) - implement full payment/transfer logic" for t in schema.financial_terms)}

OBLIGATIONS TO IMPLEMENT AS COMPLETE FUNCTIONS:
{chr(10).join(f"- {o.party} must: {o.description} (deadline: {o.deadline if o.deadline else 'none'}) - implement full logic with checks" for o in schema.obligations)}

MANDATORY IMPLEMENTATION CHECKLIST:
□ All functions have COMPLETE implementation (no "// TODO" or empty bodies)
□ All financial variables (price, fee, amount) are USED in calculations
□ All time variables (deadline, startTime) are CHECKED with block.timestamp
□ All state transitions use require() to prevent invalid changes
□ All administrative functions have access control modifiers
□ All economic transfers actually move funds (msg.value, transfer calls)
□ All events are emitted when their corresponding action completes
□ No silent failures - all invalid conditions revert with require()
□ All declared variables are read or written in at least one function
□ State machine is complete - all states are reachable and have transitions

STRUCTURE YOUR CONTRACT:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract [ContractName] {{
    // === STATE ENUM (if states mentioned) ===
    enum State {{ {', '.join(state_names) if state_names else 'Active, Completed, Terminated'} }}
    State public currentState;
    
    // === ACCESS CONTROL ===
    address public owner;
    // Add role-based addresses for each party
    
    modifier onlyOwner() {{
        require(msg.sender == owner, "Not authorized");
        _;
    }}
    
    modifier inState(State _state) {{
        require(currentState == _state, "Invalid state for this action");
        _;
    }}
    
    // === STATE VARIABLES (using EXACT names) ===
    // Declare all variables mentioned in contract
    // CRITICAL: Every variable MUST be used in at least one function
    
    // === EVENTS (using EXACT names, separate events for different actions) ===
    // One event per action type, never merge unrelated actions
    
    // === CONSTRUCTOR ===
    constructor(...) {{
        owner = msg.sender;
        // Initialize all state variables
        // Set initial state
        currentState = State.[InitialState];
    }}
    
    // === MAIN FUNCTIONS (using EXACT names with FULL implementation) ===
    // Implement complete logic for each function:
    // - Access control (modifiers)
    // - State checks (require currentState)
    // - Validation (require conditions)
    // - State updates
    // - Fund transfers (if applicable)
    // - Event emissions
    // - State transitions (if applicable)
    
    // === VIEW FUNCTIONS (getters for all state variables) ===
    // Provide read access to all state
    
    // === INTERNAL HELPER FUNCTIONS (if needed) ===
    // Extract complex logic into private functions
}}
```

EXAMPLE OF COMPLETE vs INCOMPLETE:

❌ INCOMPLETE (forbidden):
```solidity
function swapTokensForEth(uint256 amount) external {{
    require(swappingEnabled, "Swap disabled");
    // Logic goes here
}}
```

✅ COMPLETE (required):
```solidity
function swapTokensForEth(uint256 amount) external {{
    require(swappingEnabled, "Swap disabled");
    require(balances[msg.sender] >= amount, "Insufficient balance");
    require(address(this).balance >= amount * ethPrice, "Insufficient ETH");
    
    balances[msg.sender] -= amount;
    totalSupply -= amount;
    
    uint256 ethAmount = amount * ethPrice;
    (bool success, ) = msg.sender.call{{value: ethAmount}}("");
    require(success, "ETH transfer failed");
    
    emit TokensSwapped(msg.sender, amount, ethAmount);
}}
```

Return ONLY complete, production-ready Solidity code with ALL logic fully implemented."""
            )
        ]
        
        response = lm.chat(messages=messages)
        solidity_code = str(response).strip()
        
        # Remove markdown code fences if present
        if "```solidity" in solidity_code:
            solidity_code = solidity_code.split("```solidity")[1].split("```")[0].strip()
        elif "```" in solidity_code:
            solidity_code = solidity_code.split("```")[1].split("```")[0].strip()
        
        # Validate code quality
        quality_issues = self._validate_code_quality(solidity_code, schema)
        if quality_issues:
            print(f"\n⚠️  CODE QUALITY ISSUES DETECTED:")
            for issue in quality_issues:
                print(f"   - {issue}")
            print(f"\n   These issues should be addressed in future iterations.")
        
        return solidity_code
    
    def _validate_code_quality(self, solidity_code: str, schema: UniversalContractSchema) -> List[str]:
        """Validate generated code for common quality issues"""
        issues = []
        
        # Check for placeholder comments
        if "// logic goes here" in solidity_code.lower() or "// todo" in solidity_code.lower():
            issues.append("Contains placeholder comments - logic not fully implemented")
        
        # Check for silent failure pattern
        if "if (" in solidity_code and "return;" in solidity_code:
            lines = solidity_code.split('\n')
            for i, line in enumerate(lines):
                if "if (" in line and i + 1 < len(lines) and "return;" in lines[i + 1]:
                    issues.append(f"Silent failure detected (if/return pattern) - should use require()")
        
        # Check if declared variables are used
        conditions = schema.conditions if schema.conditions else {}
        variable_names = conditions.get('variable_names', [])
        for var_name in variable_names[:5]:  # Check first 5 variables
            if var_name and var_name not in solidity_code:
                issues.append(f"Variable '{var_name}' from contract not found in generated code")
        
        # Check if function names are used
        function_names = conditions.get('function_names', [])
        for func_name in function_names[:5]:  # Check first 5 functions
            if func_name and f"function {func_name}" not in solidity_code:
                issues.append(f"Function '{func_name}' from contract not implemented")
        
        # Check for empty function bodies
        if "function " in solidity_code and "{ }" in solidity_code:
            issues.append("Contains empty function bodies")
        
        # Check for access control
        if "onlyOwner" not in solidity_code and "owner" in solidity_code.lower():
            issues.append("Owner declared but no access control modifier used")
        
        # Check for time-based variables that aren't checked
        if "deadline" in solidity_code.lower() and "block.timestamp" not in solidity_code:
            issues.append("Time variable declared but never checked against block.timestamp")
        
        return issues
    
    def regenerate_with_error_feedback(self, schema: UniversalContractSchema, error_message: str, lm: LLM) -> str:
        """Regenerate contract with compilation error feedback"""
        
        print(f"\n🔧 REGENERATING CONTRACT WITH ERROR FEEDBACK")
        print(f"   Error reported: {error_message[:100]}...")
        
        # Extract specific names from schema
        conditions = schema.conditions if schema.conditions else {}
        function_names = conditions.get('function_names', [])
        variable_names = conditions.get('variable_names', [])
        state_names = conditions.get('state_names', [])
        events = conditions.get('events', [])
        
        messages = [
            system_message(
                f"""You are a Solidity expert debugging and regenerating smart contracts.

CRITICAL INSTRUCTIONS:
1. FIX the compilation error: {error_message[:150]}
2. KEEP the EXACT function names: {', '.join(function_names) if function_names else 'from schema'}
3. KEEP the EXACT variable names: {', '.join(variable_names) if variable_names else 'from schema'}
4. KEEP the EXACT state names: {', '.join(state_names) if state_names else 'from schema'}
5. KEEP the EXACT event names: {', '.join(events) if events else 'from schema'}
6. DO NOT change to generic names - preserve all specific terminology

MUST GENERATE:
- Valid Solidity ^0.8.0 syntax
- Every statement ends with semicolon
- All function bodies complete
- All parentheses/brackets matched
- Exact names from the contract preserved"""
            ),
            user_message(
                f"""REGENERATE the contract fixing this error: {error_message[:200]}

CONTRACT SCHEMA:
{schema.model_dump_json(indent=2)}

PRESERVE THESE EXACT NAMES:
- Functions: {', '.join(function_names) if function_names else 'extract from obligations'}
- Variables: {', '.join(variable_names) if variable_names else 'extract from terms'}
- States: {', '.join(state_names) if state_names else 'extract from transitions'}
- Events: {', '.join(events) if events else 'create from function names'}

REQUIREMENTS:
1. Fix the syntax error completely
2. Use EXACT names from above (not generic replacements)
3. Every statement must end with semicolon
4. Complete all function bodies
5. Handle all parties: {[p.name + ' (' + p.role + ')' for p in schema.parties]}
6. Implement all financial terms: {[f"{t.purpose}: {t.amount} {t.currency}" for t in schema.financial_terms]}
7. Implement all obligations as functions

Return ONLY valid, compilable Solidity code with EXACT names preserved."""
            )
        ]
        
        print(f"   Requesting LLM to regenerate with error feedback...")
        response = lm.chat(messages=messages)
        solidity_code = str(response).strip()
        
        # Remove markdown code fences if present
        if "```solidity" in solidity_code:
            solidity_code = solidity_code.split("```solidity")[1].split("```")[0].strip()
        elif "```" in solidity_code:
            solidity_code = solidity_code.split("```")[1].split("```")[0].strip()
        
        print(f"   ✓ Regenerated contract ({len(solidity_code.splitlines())} lines)")
        return solidity_code
    
    def _get_requirements_for_type(self, contract_type: str) -> str:
        """Get contract-type-specific requirements"""
        
        requirements_map = {
            'non_disclosure_agreement': """
REQUIRED FUNCTIONS FOR NDA:
VIEW FUNCTIONS (getters - must handle missing data gracefully):
- getPartyA() returns address
- getPartyB() returns address  
- getConfidentialityPeriodDays() returns uint
- getBreachPenaltyAmount() returns uint
- isConfidentialityActive() returns bool
- getBreachCount() returns uint

ACTION FUNCTIONS (only if relevant):
- confirmConfidentiality(bool agreeToTerms)
- reportBreach(string memory description)
- calculatePenalty(uint breachCount) returns uint256
- checkTerminationDate() returns (bool isExpired, uint daysRemaining)

STATE VARIABLES TO STORE:
- partyA, partyB (addresses, use address(0) if missing)
- confidentialityStartDate, confidentialityPeriodDays (0 if not specified)
- breachPenalty (0 if not specified)
- breachReportedCount (tracks breaches)
- isActive (bool)

IMPORTANT: All functions must be defensive - return safely even if data missing.""",
            
            'rental_agreement': """
REQUIRED FUNCTIONS FOR RENTAL:
VIEW FUNCTIONS:
- getLandlord() returns address
- getTenant() returns address
- getMonthlyRent() returns uint
- getSecurityDeposit() returns uint
- getLeaseStartDate() returns uint
- getLeaseEndDate() returns uint
- isLeaseActive() returns bool
- getTotalRentPaid() returns uint
- getDaysUntilLeaseEnd() returns uint

ACTION FUNCTIONS:
- payRent(uint amountInWei) payable
- inspectProperty(string memory notes)
- terminateLease(string memory reason)
- refundSecurityDeposit()

STATE VARIABLES TO STORE:
- landlord, tenant (addresses)
- monthlyRent, securityDeposit (amounts)
- leaseStartDate, leaseEndDate (dates)
- totalRentPaid (tracking)
- isActive (bool)

IMPORTANT: All getters return safely with defaults (0, address(0)) if data missing.""",
            
            'employment_contract': """
REQUIRED FUNCTIONS FOR EMPLOYMENT:
VIEW FUNCTIONS:
- getEmployee() returns address
- getEmployer() returns address
- getBaseSalary() returns uint
- getPerformanceBonus() returns uint
- getEmploymentStartDate() returns uint
- getEmploymentEndDate() returns uint
- isEmploymentActive() returns bool
- getTotalSalaryEarned() returns uint
- getOutstandingSalary() returns uint

ACTION FUNCTIONS:
- payEmployeeSalary() payable
- payBonus(uint bonusAmount) payable
- terminateEmployment(string memory reason)
- claimSeverancePayment()

STATE VARIABLES TO STORE:
- employee, employer (addresses)
- baseSalary, performanceBonus (amounts, 0 if not specified)
- employmentStartDate, employmentEndDate (dates, 0 if missing)
- totalSalaryPaid, isEmployed (tracking)

IMPORTANT: Handle missing salary/bonus gracefully - return 0, don't fail.""",
            
            'sales_agreement': """
REQUIRED FUNCTIONS FOR SALES:
VIEW FUNCTIONS:
- getSeller() returns address
- getBuyer() returns address
- getGoodsDescription() returns string
- getPurchasePrice() returns uint
- getPaymentTerms() returns string
- isDeliveryComplete() returns bool
- hasInspectionPassed() returns bool
- getOutstandingPayment() returns uint

ACTION FUNCTIONS:
- confirmOrderDetails(string memory terms)
- makePayment() payable
- shipGoods(string memory trackingNumber)
- confirmDelivery()
- inspectGoods(bool passed, string memory notes)
- releaseFunds()

STATE VARIABLES TO STORE:
- seller, buyer (addresses)
- goodsDescription (string)
- purchasePrice, totalPaidAmount (amounts, 0 if missing)
- deliveryConfirmed, inspectionPassed (bools)

IMPORTANT: Handle missing descriptions and prices gracefully.""",
            
            'service_agreement': """
REQUIRED FUNCTIONS FOR SERVICE:
VIEW FUNCTIONS:
- getServiceProvider() returns address
- getClient() returns address
- getServiceDescription() returns string
- getMilestoneAmount() returns uint
- getTotalMilestones() returns uint
- getCompletedMilestones() returns uint
- getMonthlyServiceFee() returns uint
- getTotalAmountPaid() returns uint
- isServiceActive() returns bool

ACTION FUNCTIONS:
- confirmServiceStart()
- payMonthlyServiceFee() payable
- payMilestonePayment(uint milestoneNumber) payable
- reportMilestoneCompletion(string memory evidence)
- approveMilestoneCompletion(uint milestoneNumber)
- reportServiceIssue(string memory issue)
- terminateService(string memory reason)

STATE VARIABLES TO STORE:
- serviceProvider, client (addresses)
- milestoneAmount, monthlyServiceFee (amounts, 0 if missing)
- completedMilestones, totalAmountPaid (tracking)
- isActive (bool)

IMPORTANT: All functions safe with missing milestone/fee data.""",
            
            'loan_agreement': """
REQUIRED FUNCTIONS FOR LOAN:
VIEW FUNCTIONS:
- getLender() returns address
- getBorrower() returns address
- getPrincipalAmount() returns uint
- getInterestRate() returns uint
- getMonthlyPayment() returns uint
- getLoanTermMonths() returns uint
- getTotalAmountRepaid() returns uint
- getRemainingBalance() returns uint
- isLoanActive() returns bool
- isLoanInDefault() returns bool

ACTION FUNCTIONS:
- disburseLoan() payable
- makeMonthlyPayment() payable
- makePrepayment(uint amount) payable
- calculateInterestAccrued() returns uint
- reportPaymentDefault()
- cureDefaultPayment() payable
- terminateLoanEarly() payable

STATE VARIABLES TO STORE:
- lender, borrower (addresses)
- principalAmount, interestRate, monthlyPayment (amounts, 0 if missing)
- totalAmountRepaid, isActive, inDefault (tracking)

IMPORTANT: Interest calculations return 0 if rate not specified.""",
            
            'investment_agreement': """
REQUIRED FUNCTIONS FOR INVESTMENT:
VIEW FUNCTIONS:
- getInvestor() returns address
- getCompany() returns address
- getInvestmentAmount() returns uint
- getEquityPercentage() returns uint
- getSharesPurchased() returns uint
- getInvestmentDate() returns uint
- getDividendRate() returns uint
- getTotalDividendsPaid() returns uint
- canRedeemShares() returns bool

ACTION FUNCTIONS:
- fundInvestment() payable
- claimBoardSeat()
- requestFinancialStatements()
- receiveDividendPayment() payable
- claimDividends()
- reportDownRound(uint newValuation)
- requestRedemption()
- settleRedemption() payable

STATE VARIABLES TO STORE:
- investor, company (addresses)
- investmentAmount, equityPercentage, sharesPurchased (amounts, 0 if missing)
- investmentDate, dividendRate (0 if missing)
- totalDividendsPaid, boardSeatGranted (tracking)

IMPORTANT: All functions safe with missing valuation/dividend data.""",
        }
        
        return requirements_map.get(contract_type, """
REQUIRED FOR ALL CONTRACTS:
VIEW FUNCTIONS:
- Create getters for all mentioned parties, amounts, and dates
- All getters must return safely with sensible defaults
- Return 0 for uint, address(0) for address, false for bool, "" for string

ACTION FUNCTIONS:
- Create functions for all contract obligations mentioned
- Use if/else for optional conditions, NOT require()
- Never fail just because optional data is missing

STATE VARIABLES:
- Store all parties (use address(0) if missing)
- Store all amounts (use 0 if missing)
- Store all dates (use 0 if missing)
- Store tracking variables initialized to 0 or false

DEFENSIVE PROGRAMMING RULES:
- EVERY function must handle missing data gracefully
- Return sensible defaults, never revert on missing fields
- Check if amounts > 0 before operations
- Never require() to fail due to missing optional terms""")


class SecurityAuditorProgram(Program):
    """IBM Agentics Program for security auditing"""
    
    def forward(self, solidity_code: str, lm: LLM) -> Dict:
        """Perform security audit"""
        
        messages = [
            system_message(
                "You are a blockchain security expert. "
                "Audit smart contracts for vulnerabilities and provide detailed reports."
            ),
            user_message(
                f"""Audit this contract for security issues:

{solidity_code}

Return ONLY valid JSON:
{{
    "severity_level": "none|low|medium|high",
    "approved": boolean,
    "issues": ["list of issues"],
    "recommendations": ["improvements"],
    "vulnerability_count": number,
    "security_score": "A|B|C|D|F"
}}"""
            )
        ]
        
        response = lm.chat(messages=messages)
        audit_text = str(response).strip()
        
        if "```json" in audit_text:
            audit_text = audit_text.split("```json")[1].split("```")[0].strip()
        elif "```" in audit_text:
            audit_text = audit_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(audit_text)


class ABIGeneratorProgram(Program):
    
    def forward(self, solidity_code: str, lm: LLM) -> List[Dict]:
        """Generate ABI"""
        
        messages = [
            system_message(
                "You are an Ethereum ABI expert. "
                "Generate accurate ABI specifications from Solidity contracts."
            ),
            user_message(
                f"""Generate complete ABI for:

{solidity_code}

Include constructor, all functions, and events with correct types.
Return ONLY the JSON array."""
            )
        ]
        
        response = lm.chat(messages=messages)
        abi_text = str(response).strip()
        
        if "```json" in abi_text:
            abi_text = abi_text.split("```json")[1].split("```")[0].strip()
        elif "```" in abi_text:
            abi_text = abi_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(abi_text)

class MCPServerGeneratorProgram(Program):
    """
    IBM Agentics Program for generating custom MCP servers from ABI files
    """
    
    def forward(self, abi: List[Dict], schema: UniversalContractSchema, contract_name: str, lm: LLM) -> str:
        """
        Generate custom MCP server code from ABI
        
        Args:
            abi: The contract ABI
            schema: The contract schema (for context)
            contract_name: Name of the contract file
            lm: Language model
            
        Returns:
            str: Complete Python code for MCP server
        """
        
        # Extract function information from ABI
        functions = [item for item in abi if item.get('type') == 'function']
        payable_functions = [f for f in functions if f.get('stateMutability') == 'payable']
        nonpayable_functions = [f for f in functions if f.get('stateMutability') == 'nonpayable']
        view_functions = [f for f in functions if f.get('stateMutability') in ['view', 'pure']]
        
        # Get constructor for understanding contract initialization
        constructor = next((item for item in abi if item.get('type') == 'constructor'), None)
        
        # Create detailed function descriptions
        function_details = self._create_function_descriptions(functions, schema)
        
        messages = [
            system_message(
                """You are an expert Python developer specializing in blockchain integration and MCP servers.
                
                You understand:
                - Web3.py for Ethereum interaction
                - FastMCP (v0.7+) for creating MCP tool servers using FastMCP class
                - Smart contract function calling patterns
                - Transaction signing and gas management
                - Error handling for blockchain operations
                
                CRITICAL: Use FastMCP (not the old MCP class). The correct import is:
                  from fastmcp import FastMCP
                  mcp = FastMCP("ContractName")
                  @mcp.tool()
                  def function_name():
                      ...
                
                The main block must end with:
                  if __name__ == "__main__":
                      mcp.run()
                
                You write clean, well-documented, production-ready code."""
            ),
            user_message(
                f"""Generate a complete MCP server for this {schema.contract_type} smart contract.

CONTRACT NAME: {contract_name}
CONTRACT TYPE: {schema.contract_type}
PARTIES: {[f"{p.name} ({p.role})" for p in schema.parties]}

ABI SUMMARY:
- Payable functions: {len(payable_functions)}
- Non-payable functions: {len(nonpayable_functions)}
- View functions: {len(view_functions)}

COMPLETE ABI:
{json.dumps(abi, indent=2)}

FUNCTION DETAILS:
{function_details}

Generate a Python MCP server file with CORRECT FastMCP API:

1. **Imports (MUST use FastMCP, not old MCP)**:
   ```python
   import os
   import json
   from pathlib import Path
   from web3 import Web3
   from dotenv import load_dotenv
   from fastmcp import FastMCP
   ```

2. **Setup (Load .env from SAME DIRECTORY as script, Load ABI from .abi.json file)**:
   ```python
   import os
   import json
   from pathlib import Path
   from dotenv import load_dotenv
   
   # Load .env from the same directory as this script
   env_path = Path(__file__).parent / '.env'
   load_dotenv(dotenv_path=env_path)
   
   # Load ABI from the same directory as this script
   abi_path = Path(__file__).parent / '{contract_name}.abi.json'
   with open(abi_path, 'r') as f:
       contract_abi = json.load(f)
   
   RPC_URL = os.getenv('RPC_URL')
   PRIVATE_KEY = os.getenv('PRIVATE_KEY')
   CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
   
   web3 = Web3(Web3.HTTPProvider(RPC_URL))
   account = web3.eth.account.from_key(PRIVATE_KEY)
   contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)
   ```

3. **Create FastMCP instance**:
   ```python
   mcp = FastMCP("{contract_name}")
   ```

4. **Create @mcp.tool() decorated functions for EACH ABI function**:
   
   For PAYABLE functions:
   - Build transaction with correct value
   - Sign and send transaction
   - Return {{"tx_hash": hash}}
   
   For NON-PAYABLE functions:
   - Build transaction (no value)
   - Sign and send transaction
   - Return {{"tx_hash": hash}}
   
   For VIEW functions:
   - Call function (read-only)
   - Return result directly
   
5. **Documentation**:
   - Each @mcp.tool() function must have docstring
   - Explain what it does, who can call it, parameters, return value
   - Handle errors gracefully

6. **Error Handling**:
   - Wrap each tool in try/except
   - Return {{"error": str(e)}} on failure

7. **Main Block (CRITICAL)**:
   ```python
   if __name__ == "__main__":
       mcp.run()
   ```

CRITICAL CODE EXAMPLES:

Setup must use local .env file:
```python
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)
```

Transaction building for non-payable:
```python
txn = contract.functions.function_name(param1).buildTransaction({{
    'from': account.address,
    'nonce': web3.eth.get_transaction_count(account.address),
    'gas': 2000000,
    'gasPrice': web3.to_wei('20', 'gwei')
}})
signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
return {{"tx_hash": tx_hash.hex()}}
```

Transaction building for payable:
```python
txn = contract.functions.makePayment().buildTransaction({{
    'from': account.address,
    'nonce': web3.eth.get_transaction_count(account.address),
    'gas': 2000000,
    'gasPrice': web3.to_wei('20', 'gwei'),
    'value': web3.to_wei(5, 'ether')
}})
signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
return {{"tx_hash": tx_hash.hex()}}
```

View function:
```python
result = contract.functions.getBalance().call()
return {{"result": result}}
```

IMPORTANT RULES:
- Function names must match ABI exactly
- Include ALL functions from ABI
- Use @mcp.tool() decorator (not @tool())
- Load ABI from {contract_name}.abi.json file in same directory (do NOT hardcode ABI)
- Load .env from same directory as script
- ALWAYS initialize: account = web3.eth.account.from_key(PRIVATE_KEY)
- Use 'from': account.address in all transactions
- Use web3.eth.get_transaction_count(), NOT web3.eth.getTransactionCount()
- Use web3.to_wei(), NOT web3.toWei()
- Use web3.eth.send_raw_transaction(), NOT web3.eth.sendRawTransaction()
- Use Web3.to_checksum_address(), NOT Web3.toChecksumAddress()
- For payable functions, include 'value': web3.to_wei(amount, 'ether')
- File must be self-contained and runnable

Return ONLY the complete Python code, no explanations."""
            )
        ]
        
        response = lm.chat(messages=messages)
        server_code = str(response).strip()
        
        # Clean markdown
        if "```python" in server_code:
            server_code = server_code.split("```python")[1].split("```")[0].strip()
        elif "```" in server_code:
            server_code = server_code.split("```")[1].split("```")[0].strip()
        
        return server_code
    
    def _create_function_descriptions(self, functions: List[Dict], schema: UniversalContractSchema) -> str:
        """Create human-readable descriptions of functions based on contract context"""
        
        descriptions = []
        
        for func in functions:
            name = func.get('name', 'unknown')
            inputs = func.get('inputs', [])
            outputs = func.get('outputs', [])
            stateMutability = func.get('stateMutability', 'nonpayable')
            
            # Create parameter description
            params = ', '.join([f"{inp.get('name', 'param')}:{inp.get('type', 'unknown')}" for inp in inputs])
            returns = ', '.join([f"{out.get('name', 'result')}:{out.get('type', 'unknown')}" for out in outputs]) if outputs else 'void'
            
            descriptions.append(
                f"  - {name}({params}) → {returns} [{stateMutability}]"
            )
        
        return '\n'.join(descriptions)
    
class IBMAgenticContractTranslator:
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize translator
        
        Args:
            model: LLM model to use (default: gpt-4o-mini for OpenAI)
        
        Note: IBM Agentics requires OPENAI_API_KEY in environment
        """

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY required in .env file. "
                "IBM Agentics uses OpenAI models by default."
            )
        
        self.llm = LLM(model=model)
        print(f"✓ IBM Agentics LLM initialized with {model}")
        print("🤖 Initializing IBM Agentics Programs...")
        self.parser = UniversalContractParserProgram()
        self.generator = UniversalSolidityGeneratorProgram()
        self.auditor = SecurityAuditorProgram()
        self.abi_generator = ABIGeneratorProgram()
        self.mcp_generator = MCPServerGeneratorProgram()  # NEW!
        print("✓ All Programs initialized (including MCP Generator)\n")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        print(f"📄 Reading PDF: {pdf_path}")
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    
    def translate_contract_streaming(
        self, 
        input_path: str, 
        output_dir: str = "./output",
        require_audit_approval: bool = True,
        generate_mcp_server: bool = True
    ):
        """
        Streaming version that yields phase updates as they complete.
        Yields dict with {phase: int, status: str, data: dict}
        """
        
        print("\n" + "="*70)
        print("IBM AGENTICS CONTRACT TRANSLATOR (STREAMING)")
        print("="*70)
        
        results = {}
        
        # Phase 1: Document Processing
        print("\n[Phase 1/6] Document Processing")
        if input_path.endswith('.pdf'):
            contract_text = self.extract_text_from_pdf(input_path)
            source = "PDF"
        else:
            with open(input_path, 'r', encoding='utf-8') as f:
                contract_text = f.read()
            source = "text file"
        print(f"✓ Extracted {len(contract_text)} characters from {source}")
        
        yield {
            'phase': 1,
            'status': 'complete',
            'data': {
                'title': 'Document Processing',
                'message': f'Extracted {len(contract_text)} characters from {source}'
            }
        }
        
        # Phase 2: Contract Analysis
        print("\n[Phase 2/6] Contract Analysis (Parser Program)")
        schema = self.parser.forward(contract_text, self.llm)
        results['schema'] = schema
        print(f"✓ Parsed: {len(schema.parties)} parties, {len(schema.financial_terms)} financial terms")
        
        # Convert schema to dict for JSON serialization to frontend
        try:
            if hasattr(schema, 'model_dump'):
                schema_dict = schema.model_dump()
            elif hasattr(schema, '__dict__'):
                schema_dict = schema.__dict__
            else:
                schema_dict = {}
        except Exception as e:
            print(f"   ⚠️  Error converting schema to dict: {e}")
            schema_dict = {
                'contract_type': str(schema.contract_type),
                'parties': [{'name': p.name, 'role': p.role} for p in schema.parties] if schema.parties else [],
                'financial_terms': [{'amount': t.amount, 'currency': t.currency, 'purpose': t.purpose} for t in schema.financial_terms] if schema.financial_terms else []
            }
        
        yield {
            'phase': 2,
            'status': 'complete',
            'data': {
                'title': 'Contract Analysis',
                'message': f'Parsed: {len(schema.parties)} parties, {len(schema.financial_terms)} financial terms',
                'contract_type': schema.contract_type,
                'parties': schema_dict.get('parties', []) if isinstance(schema_dict, dict) else [],
                'financial_terms': schema_dict.get('financial_terms', []) if isinstance(schema_dict, dict) else [],
                'schema': schema_dict
            }
        }
        
        # Phase 3: Solidity Generation
        print("\n[Phase 3/6] Code Generation (Generator Program)")
        solidity_code = self.generator.forward(schema, self.llm)
        results['solidity'] = solidity_code
        print(f"✓ Generated {len(solidity_code.splitlines())} lines")
        
        yield {
            'phase': 3,
            'status': 'complete',
            'data': {
                'title': 'Code Generation',
                'message': f'Generated {len(solidity_code.splitlines())} lines of Solidity',
                'solidity': solidity_code
            }
        }
        
        # Phase 4: Security Audit
        print("\n[Phase 4/6] Security Analysis (Auditor Program)")
        audit_report = self.auditor.forward(solidity_code, self.llm)
        results['audit'] = audit_report
        severity = audit_report.get('severity_level', 'unknown')
        score = audit_report.get('security_score', 'N/A')
        issues = audit_report.get('issues', [])
        print(f"✓ Audit Complete: Severity={severity}, Score={score}")
        
        # Log audit issues for regeneration tracking
        if issues:
            print(f"   ⚠️  Found {len(issues)} issue(s) during security audit:")
            for idx, issue in enumerate(issues[:5], 1):  # Show first 5
                issue_text = issue[:100] + "..." if len(str(issue)) > 100 else issue
                print(f"      {idx}. {issue_text}")
            print(f"   🔄 Contract may be regenerated with audit feedback if compilation fails")
        else:
            print(f"   ✓ No security issues detected")
        
        # Send audit details to frontend for user approval
        yield {
            'phase': 4,
            'status': 'needs_approval',
            'data': {
                'title': 'Security Audit',
                'message': f'Severity: {severity.upper()}, Score: {score}',
                'severity_level': severity,
                'security_score': score,
                'issues': issues,
                'vulnerability_count': audit_report.get('vulnerability_count', 0),
                'recommendations': audit_report.get('recommendations', [])
            }
        }
        
        # Phase 5: ABI Generation
        print("\n[Phase 5/6] Interface Generation (ABI Program)")
        abi = self.abi_generator.forward(solidity_code, self.llm)
        results['abi'] = abi
        print(f"✓ Generated {len(abi)} ABI elements")
        
        yield {
            'phase': 5,
            'status': 'complete',
            'data': {
                'title': 'ABI Generation',
                'message': f'Generated {len(abi)} ABI elements',
                'abi': abi
            }
        }
        
        # Phase 6: MCP Server Generation
        if generate_mcp_server:
            print("\n[Phase 6/6] MCP Server Generation (MCP Generator Program)")
            
            # Extract contract name from schema
            contract_name = "_".join([p.name.replace(' ', '_')[:10] for p in schema.parties[:2]]) if schema.parties else "Contract"
            contract_name = contract_name[:40]
            
            mcp_server_code = self.mcp_generator.forward(abi, schema, contract_name, self.llm)
            results['mcp_server'] = mcp_server_code
            print(f"✓ Generated MCP server ({len(mcp_server_code.splitlines())} lines)")
        else:
            print("\n[Phase 6/6] MCP Server Generation - SKIPPED")
        
        # Save all outputs
        self._save_outputs(results, output_dir, schema)
        
        print("\n" + "="*70)
        print("✅ TRANSLATION COMPLETE")
        print("="*70)
        
        yield {
            'phase': 6,
            'status': 'complete',
            'data': {
                'title': 'MCP Server Generation',
                'message': f'Generated MCP server',
                'mcp_server': results.get('mcp_server', '')
            }
        }
    
    def translate_contract(
        self, 
        input_path: str, 
        output_dir: str = "./output",
        require_audit_approval: bool = True,
        generate_mcp_server: bool = True  # NEW parameter
    ) -> Dict:
        """
        Complete translation workflow using IBM Agentics Programs
        """
        
        print("\n" + "="*70)
        print("IBM AGENTICS CONTRACT TRANSLATOR")
        print("="*70)
        
        results = {}
        
        # Phase 1: Document Processing
        print("\n[Phase 1/6] Document Processing")
        if input_path.endswith('.pdf'):
            contract_text = self.extract_text_from_pdf(input_path)
        else:
            with open(input_path, 'r', encoding='utf-8') as f:
                contract_text = f.read()
        print(f"✓ Extracted {len(contract_text)} characters")
        
        # Phase 2: Contract Analysis
        print("\n[Phase 2/6] Contract Analysis (Parser Program)")
        schema = self.parser.forward(contract_text, self.llm)
        results['schema'] = schema
        print(f"✓ Parsed: {len(schema.parties)} parties, {len(schema.financial_terms)} financial terms")
        
        # Phase 3: Solidity Generation
        print("\n[Phase 3/6] Code Generation (Generator Program)")
        solidity_code = self.generator.forward(schema, self.llm)
        results['solidity'] = solidity_code
        print(f"✓ Generated {len(solidity_code.splitlines())} lines")
        
        # Phase 4: Security Audit
        print("\n[Phase 4/6] Security Analysis (Auditor Program)")
        audit_report = self.auditor.forward(solidity_code, self.llm)
        results['audit'] = audit_report
        severity = audit_report.get('severity_level', 'unknown')
        score = audit_report.get('security_score', 'N/A')
        print(f"✓ Audit: Severity={severity}, Score={score}")
        
        # Check audit approval
        if require_audit_approval and not audit_report.get('approved', False):
            print("\n⚠️  Security issues detected!")
            for i, issue in enumerate(audit_report.get('issues', [])[:3], 1):
                print(f"   {i}. {issue}")
            
            response = input("\n   Continue? (yes/no): ").lower()
            if response != 'yes':
                raise Exception("Halted due to security concerns")
        
        # Phase 5: ABI Generation
        print("\n[Phase 5/6] Interface Generation (ABI Program)")
        abi = self.abi_generator.forward(solidity_code, self.llm)
        results['abi'] = abi
        print(f"✓ Generated {len(abi)} ABI elements")
        
        # Phase 6: MCP Server Generation (NEW!)
        if generate_mcp_server:
            print("\n[Phase 6/6] MCP Server Generation (MCP Generator Program)")
            
            # Extract contract name from schema
            contract_name = "_".join([p.name.replace(' ', '_')[:10] for p in schema.parties[:2]]) if schema.parties else "Contract"
            contract_name = contract_name[:40]
            
            mcp_server_code = self.mcp_generator.forward(abi, schema, contract_name, self.llm)
            results['mcp_server'] = mcp_server_code
            print(f"✓ Generated MCP server ({len(mcp_server_code.splitlines())} lines)")
        else:
            print("\n[Phase 6/6] MCP Server Generation - SKIPPED")
        
        # Save all outputs
        self._save_outputs(results, output_dir, schema)
        
        print("\n" + "="*70)
        print("✅ TRANSLATION COMPLETE")
        print("="*70)
        
        return results
    
    def _save_outputs(self, results: Dict, output_dir: str, schema):
        """Save all outputs including MCP server"""
        
        print("\n💾 Saving outputs...")
        
        # Create directories (existing code)
        base_output_path = Path(output_dir)
        base_output_path.mkdir(exist_ok=True, parents=True)
        
        contract_type = schema.contract_type.replace('_', ' ').title()
        subdirectory_name = contract_type.replace(' ', '_')
        
        run_number = 1
        subdir_path = base_output_path / f"{subdirectory_name}_{run_number}"
        while subdir_path.exists():
            run_number += 1
            subdir_path = base_output_path / f"{subdirectory_name}_{run_number}"
        
        subdir_path.mkdir(exist_ok=True, parents=True)
        
        # Generate contract filename
        contract_name = "_".join([p.name.replace(' ', '_')[:10] for p in schema.parties[:2]]) if schema.parties else "Contract"
        contract_name = contract_name[:40]
        
        # Save Solidity
        with open(subdir_path / f"{contract_name}.sol", 'w', encoding='utf-8') as f:
            f.write(results['solidity'])
        print(f"   ✓ {contract_name}.sol")

        # Save ABI
        abi_filename = f"{contract_name}.abi.json"
        with open(subdir_path / abi_filename, 'w', encoding='utf-8') as f:
            json.dump(results['abi'], f, indent=2)
        print(f"   ✓ {abi_filename}")

        # Save schema
        with open(subdir_path / "contract_schema.json", 'w', encoding='utf-8') as f:
            json.dump(results['schema'].model_dump(), f, indent=2)
        print(f"   ✓ contract_schema.json")
 
        # Save audit
        with open(subdir_path / "security_audit.json", 'w', encoding='utf-8') as f:
            json.dump(results['audit'], f, indent=2)
        print(f"   ✓ security_audit.json")
        
        # Save MCP Server (NEW!)
        if 'mcp_server' in results:
            mcp_filename = f"{contract_name}_mcp_server.py"
            with open(subdir_path / mcp_filename, 'w', encoding='utf-8') as f:
                f.write(results['mcp_server'])
            print(f"   ✓ {mcp_filename}")
            
            # Create .env file for this contract (user will fill in values)
            env_content = f"""# MCP Server Configuration for {contract_name}
# Fill in your values below, then run the MCP server

# Blockchain RPC endpoint (e.g., http://127.0.0.1:8545 for Ganache)
RPC_URL=http://127.0.0.1:8545

# Private key for signing transactions (get from Ganache, without 0x prefix)
PRIVATE_KEY=your_private_key_here

# Deployed contract address (get after deploying Solidity contract)
CONTRACT_ADDRESS=0x...
"""
            with open(subdir_path / ".env", 'w', encoding='utf-8') as f:
                f.write(env_content)
            print(f"   ✓ .env")
            
            # Also create a .env.example as reference
            env_example = f"""# MCP Server Configuration for {contract_name}
# This is an example. Copy to .env and fill in your values

# Blockchain RPC endpoint (Infura, Alchemy, or local Ganache)
RPC_URL=http://127.0.0.1:8545

# Private key for signing transactions (without 0x prefix)
PRIVATE_KEY=your_private_key_here

# Deployed contract address (will be filled after deployment)
CONTRACT_ADDRESS=0x...
"""
            with open(subdir_path / ".env.example", 'w', encoding='utf-8') as f:
                f.write(env_example)
            print(f"   ✓ .env.example")
        
        # Update README
        schema = results['schema']
        audit = results['audit']
        
        readme = f"""# IBM Agentics Contract Translation

## Contract Summary
- **Type**: {schema.contract_type}
- **Parties**: {', '.join(p.name for p in schema.parties)}
- **Financial Terms**: {len(schema.financial_terms)} term(s)

## Security Audit
- **Status**: {'✅ APPROVED' if audit.get('approved') else '⚠️ REVIEW NEEDED'}
- **Severity**: {audit['severity_level'].upper()}
- **Score**: {audit.get('security_score', 'N/A')}

## Generated Files

### Smart Contract Files
1. **{contract_name}.sol** - Solidity smart contract ({len(results['solidity'].splitlines())} lines)
2. **{contract_name}.abi.json** - Contract ABI ({len(results['abi'])} elements)

### Configuration & Documentation
3. **contract_schema.json** - Structured contract data
4. **security_audit.json** - Security audit report

### MCP Server
5. **{contract_name}_mcp_server.py** - Custom MCP server ({len(results.get('mcp_server', '').splitlines())} lines)
6. **.env.example** - Environment configuration template

## Using the MCP Server

### 1. Setup Environment
```bash
# Copy and configure environment file
cp .env.example .env

# Edit .env with your values:
# - RPC_URL: Your blockchain endpoint
# - PRIVATE_KEY: Your wallet private key
# - CONTRACT_ADDRESS: Deployed contract address
```

### 2. Install Dependencies
```bash
pip install web3 python-dotenv fastmcp
```

### 3. Deploy Contract
First deploy the Solidity contract to get CONTRACT_ADDRESS:
```bash
# Using Remix, Hardhat, or web3.py
# Update CONTRACT_ADDRESS in .env after deployment
```

### 4. Run MCP Server
```bash
python {contract_name}_mcp_server.py
```

### 5. Available Tools
The MCP server exposes these tools based on the contract ABI:
{self._generate_tool_list(results.get('abi', []))}

## Next Steps
1. ✅ Review security audit
2. ✅ Deploy Solidity contract to testnet
3. ✅ Update .env with CONTRACT_ADDRESS
4. ✅ Run MCP server
5. ✅ Connect AI agents to MCP server
6. ✅ Test contract interactions

---
*Generated by IBM Agentics Framework*
*MCP Server auto-generated from ABI*
"""
        
        with open(subdir_path / "README.md", 'w', encoding='utf-8') as f:
            f.write(readme)
        print(f"   ✓ README.md")
        
        try:
            display_path = subdir_path.relative_to(Path.cwd())
        except ValueError:
            display_path = subdir_path.resolve()
        print(f"\n📁 Outputs saved to: {display_path}")
    
    def _generate_tool_list(self, abi: List[Dict]) -> str:
        """Generate markdown list of available MCP tools"""
        
        tools = []
        for item in abi:
            if item.get('type') == 'function':
                name = item.get('name')
                stateMutability = item.get('stateMutability', 'nonpayable')
                
                if stateMutability == 'payable':
                    tools.append(f"- `{name}()` - Payable transaction")
                elif stateMutability in ['view', 'pure']:
                    tools.append(f"- `{name}()` - Read-only query")
                else:
                    tools.append(f"- `{name}()` - State-changing transaction")
        
        return '\n'.join(tools) if tools else "- No tools available"
    

def main():
    """CLI entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python agentic_implementation.py <contract.pdf> [output_dir] [--no-mcp]")
        print("\nOptions:")
        print("  --no-mcp    Skip MCP server generation")
        print("\nRequirements:")
        print("  - OPENAI_API_KEY in .env")
        print("  - PDF contract file")
        print("\nExample:")
        print("  python agentic_implementation.py 'contracts/rental.pdf'")
        print("  python agentic_implementation.py 'contracts/rental.pdf' ./output --no-mcp")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = "./output"
    generate_mcp = True
    
    # Parse arguments
    for arg in sys.argv[2:]:
        if arg == '--no-mcp':
            generate_mcp = False
        elif not arg.startswith('--'):
            output_dir = arg
    
    try:
        translator = IBMAgenticContractTranslator()
        results = translator.translate_contract(
            input_file, 
            output_dir,
            generate_mcp_server=generate_mcp
        )
        
        print("\n📊 Summary:")
        print(f"   Contract Type: {results['schema'].contract_type}")
        print(f"   Parties: {len(results['schema'].parties)}")
        print(f"   Solidity: {len(results['solidity'].splitlines())} lines")
        print(f"   Security: {results['audit']['severity_level']}")
        print(f"   ABI: {len(results['abi'])} elements")
        if 'mcp_server' in results:
            print(f"   MCP Server: {len(results['mcp_server'].splitlines())} lines")
        print(f"\n📁 Output: {output_dir}/")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()