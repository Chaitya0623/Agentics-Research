"""
Task description builders for CrewAI agents

These functions create detailed task descriptions for each phase:
- Parser: Extract structured data from contract text
- Generator: Create Solidity smart contract
- Auditor: Security analysis
- ABI Generator: Generate contract ABI
"""

from .schemas import UniversalContractSchema


def create_parser_task_description(contract_text: str) -> str:
    """
    Create task description for the Contract Parser Agent.
    Returns the full task description including the contract text.
    Uses the comprehensive prompt from programs.py for maximum accuracy.
    """
    return f"""Analyze this contract and extract ALL SPECIFIC information exactly as mentioned.

CONTRACT TEXT:
{contract_text}

CRITICAL INSTRUCTIONS:
1. Extract the EXACT function names mentioned in the contract (e.g., "initializeLease", "payRent", "confirmDelivery")
2. Extract the EXACT variable names mentioned (e.g., "monthlyRent", "securityDeposit", "deliveryDate")
3. Extract the EXACT state names mentioned (e.g., "Pending", "Active", "Completed", "Terminated")
4. Extract the EXACT party roles as described in the contract
5. DO NOT use generic placeholders - use the specific terminology from the contract
6. Capture ALL conditions, transitions, and logic flows mentioned

Your goal: Create a structured representation that preserves ALL specific details from the contract text.

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


"""
Create task description for the Solidity Generator Agent.
Final enhanced version with targeted improvements for common failure patterns.
"""

def create_solidity_generation_prompt(schema):
    conditions = schema.conditions if schema.conditions else {}
    function_names = conditions.get('function_names', [])
    variable_names = conditions.get('variable_names', [])
    state_names = conditions.get('state_names', [])
    state_transitions = conditions.get('state_transitions', [])
    events = conditions.get('events', [])
    logic_conditions = conditions.get('logic_conditions', [])
    
    return f"""Generate a COMPLETE, FUNCTIONAL Solidity ^0.8.0 smart contract that FULLY implements this specification.

═══════════════════════════════════════════════════════════════════════════════
PHASE 1 - SEMANTIC ANALYSIS (COMPLETE THIS BEFORE WRITING ANY CODE)
═══════════════════════════════════════════════════════════════════════════════

Before generating any Solidity code, perform this analysis:

1. CORE PURPOSE IDENTIFICATION:
   - What is the PRIMARY purpose of this contract in one sentence?
   - Example: "Manage milestone-based grant payments to initiatives"
   - Example: "Enable token swapping with automated market making"
   - Example: "Facilitate NFT marketplace with royalty distribution"

2. COMPLETE WORKFLOW ANALYSIS:
   - What happens FIRST? (initialization, creation, deposit)
   - What happens NEXT? (assignment, approval, activation)
   - What are the DECISION POINTS? (approval/rejection, success/failure)
   - What triggers PAYMENTS or VALUE TRANSFERS?
   - What is the TERMINAL STATE? (completion, cancellation, expiry)
   - Map out the FULL USER JOURNEY from start to finish
   - CRITICAL: Can multiple users perform different operations SIMULTANEOUSLY?

3. IMPLIED STATE TRANSITIONS:
   - If spec mentions "assigning X" → there must be a transition TO an ASSIGNED state
   - If spec mentions "completing X" → there must be a transition TO a COMPLETED state
   - If spec mentions "milestone payments" → need states for each milestone phase
   - Every mentioned action implies a state change - identify them ALL
   - CRITICAL: Are states PHASES of the workflow or TYPES of operations?

4. ECONOMIC FLOW ANALYSIS:
   - Where do FUNDS ENTER the contract? (constructor, deposit function, payable calls)
   - How are funds STORED? (contract balance, escrow mapping, locked amounts)
   - What TRIGGERS RELEASE? (milestone completion, approval, time passing)
   - Where do funds GO? (recipient address, multiple parties, refunds)
   - Are there FEES or SPLITS? (percentages, fixed amounts, royalties)

5. CONTRACT TYPE DETECTION:
   Identify the contract type to determine required standard behaviors:
   
   □ TOKEN CONTRACT (ERC20/ERC721)
     → MANDATORY: transfer, approve, transferFrom, balanceOf, totalSupply
     → MANDATORY: name, symbol, decimals (ERC20) or tokenURI (ERC721)
     → MANDATORY: Transfer/Approval events
     → MANDATORY: Allowances mapping (ERC20)
     → STATE MACHINE RULE: Do NOT use states to control basic operations
     → CONCURRENT ACCESS: All users must be able to transfer/approve simultaneously
     → If missing ANY of these: YOU HAVE FAILED
   
   □ GOVERNANCE CONTRACT
     → MANDATORY: Delegation must TRANSFER voting power, not just store relationships
     → MANDATORY: Checkpoints must be HISTORICAL (block number + votes)
     → MANDATORY: Votes must UPDATE when tokens transfer
     → INVARIANT: sum(voting power) = sum(balances) at all times
     → If delegation doesn't affect voting power: YOU HAVE FAILED
   
   □ PAYMENT/ESCROW CONTRACT
     → Implement: deposit (payable), release, refund, balance tracking
     → Implement: conditional release logic, dispute resolution if mentioned
   
   □ GRANTS/FUNDING CONTRACT
     → Implement: application/proposal creation, milestone definitions
     → Implement: milestone completion tracking, staged payment release
     → Implement: grant assignment, progress tracking
   
   □ MARKETPLACE CONTRACT
     → Implement: listing creation, purchase, transfer ownership
     → Implement: pricing, fees, royalty distribution
   
   □ STAKING/REWARDS CONTRACT
     → Implement: stake, unstake, reward calculation, claim
     → Implement: time-based accrual, penalty for early withdrawal if mentioned

6. INVARIANT IDENTIFICATION:
   Before implementing, identify the key invariants that MUST hold:
   
   Examples:
   - Token: sum(all balances) = totalSupply (always)
   - Governance: sum(all voting power) = sum(all balances) (always)
   - Escrow: sum(deposits) = sum(withdrawals) + balance (always)
   - NFT: each tokenId has exactly one owner (always)
   - Auction: highestBid >= previousBid (always)
   
   For EACH invariant:
   - Write it down explicitly
   - Identify which functions could violate it
   - Add checks to prevent violation
   
   Test mental model: "If I call functions in ANY order, can I break this invariant?"

═══════════════════════════════════════════════════════════════════════════════
PHASE 2 - CRITICAL GENERATION RULES (STRICT COMPLIANCE REQUIRED)
═══════════════════════════════════════════════════════════════════════════════

1. TRANSLATE EVERY GUARANTEE INTO ENFORCEABLE ON-CHAIN LOGIC
   - For each promise, constraint, or outcome in the natural-language contract,
     implement corresponding state changes, permission checks, and value transfers
   - Violating the described behavior must be IMPOSSIBLE on-chain
   - Never use placeholder functions, event-only logic, or implicit assumptions

2. SYSTEM-WIDE INVARIANTS MUST HOLD ACROSS ALL FUNCTIONS
   - Identify core invariants: conservation of funds, supply limits, state exclusivity,
     delegation correctness, fairness between parties
   - No invariant can be violated by calling functions in ANY order or combination
   - Test mental model: "Can an attacker break this by calling functions in sequence?"

3. DOMAIN TERMS IMPLY FULL DOMAIN SEMANTICS
   - "Token" → Implement full ERC20/ERC721 with transfers, approvals, balances
   - "NFT" → Implement unique ownership, metadata, transfers
   - "Governance" → Implement proposals, voting, quorum, execution
   - "Delegation" → Implement vote power transfer, revocation
   - "Royalties" → Implement percentage calculation, automatic distribution
   - "Milestone" → Implement completion tracking, staged payments
   - DO NOT reduce domain concepts to symbolic or approximate behavior

3.5 DELEGATION SEMANTICS (FOR GOVERNANCE TOKENS)
    When implementing vote delegation:
    
    REQUIRED COMPONENTS:
    1. Delegate mapping: tracks WHO each account delegates to
    2. Voting power mapping: tracks CURRENT voting power of each account
    3. Checkpoint system: tracks HISTORICAL voting power at block numbers
    
    REQUIRED BEHAVIORS:
    a) Self-delegation: Users start with votes delegated to themselves OR must self-delegate
    b) Vote transfer: When A delegates to B, A's voting power goes to B
    c) Cascade on transfer: When tokens transfer, voting power updates accordingly
    d) Historical tracking: Checkpoints record voting power at specific blocks
    
    CRITICAL INVARIANT: 
    Sum of all voting power = Sum of all token balances (always)
    
    ✅ CORRECT delegation implementation:
    ```solidity
    mapping(address => address) public delegates;
    mapping(address => uint256) public votingPower;
    
    function delegate(address delegatee) external {{
        address currentDelegate = delegates[msg.sender];
        uint256 delegatorBalance = balances[msg.sender];
        
        delegates[msg.sender] = delegatee;
        
        // Remove votes from old delegate
        if (currentDelegate != address(0)) {{
            votingPower[currentDelegate] -= delegatorBalance;
        }}
        
        // Add votes to new delegate  
        if (delegatee != address(0)) {{
            votingPower[delegatee] += delegatorBalance;
        }}
        
        emit DelegateChanged(msg.sender, currentDelegate, delegatee);
    }}
    
    function _afterTokenTransfer(address from, address to, uint256 amount) internal {{
        // CRITICAL: Update voting power when tokens move
        address fromDelegate = delegates[from];
        address toDelegate = delegates[to];
        
        if (fromDelegate != address(0)) {{
            votingPower[fromDelegate] -= amount;
        }}
        if (toDelegate != address(0)) {{
            votingPower[toDelegate] += amount;
        }}
    }}
    ```
    
    ❌ WRONG - Delegation that doesn't transfer voting power:
    ```solidity
    function delegate(address delegatee) external {{
        delegates[msg.sender] = delegatee;  // Only stores, doesn't transfer votes!
    }}
    ```

4. SEMANTIC FIDELITY OVER NAME MATCHING
   - UNDERSTAND what the contract DOES before matching function names
   - If spec says "releasing milestone payments", you MUST implement:
     * Storage for milestone definitions (struct or mapping)
     * Logic to track which milestones are completed
     * Actual fund transfer mechanism (transfer, call, send)
     * Access control for who can release payments
   - If a listed function name doesn't fit the analyzed workflow, DON'T force it
   - If the workflow requires unlisted functions, ADD them
   - Names are GUIDANCE; correct behavior is MANDATORY

5. EXPLICIT STATE MACHINE ENFORCEMENT
   - All states must be REACHABLE through actual function calls
   - States must be MUTUALLY EXCLUSIVE and MEANINGFUL
   - Every state must have at least ONE function that transitions INTO it
   - State transitions must reflect REAL operational phases, not artificial sequencing
   - Every state-dependent function MUST use require(currentState == State.X)
   - Never define states that are never set

6. ACCESS CONTROL MUST BE JUSTIFIED AND ENFORCED
   - Use modifiers for ALL access-controlled functions
   - Common patterns:
     * onlyOwner - for admin functions
     * onlyCreator - for resource creator
     * onlyRole - for role-based access
   - Do NOT introduce privileged roles unless justified by specification
   - Use least-privilege principles
   - Every modifier must actually prevent unauthorized access with require()

7. NO SILENT FAILURES OR SYMBOLIC LOGIC
   - NEVER use: if (condition) return;
   - ALWAYS use: require(condition, "Descriptive error message");
   - Do NOT emit events without corresponding state or economic changes
   - Do NOT substitute simplified logic for described behavior
   - Every validation must revert on failure, never silently skip

8. ECONOMIC LOGIC MUST BE COMPLETE AND CONSERVATIVE
   - Implement ALL pricing, fees, transfers, and accounting FULLY
   - Ensure conservation of value across all functions (input = output + fees)
   - Every financial variable must affect LIVE execution paths
   - If fundsAllocated is stored, it must be TRANSFERRED somewhere
   - If price is stored, it must be CHECKED and CHARGED
   - Never store economic values that are never used in transfers

9. TIME-BASED CONDITIONS MUST AFFECT BEHAVIOR
   - Store deadlines using uint256 timestamp variables
   - ENFORCE deadlines using require(block.timestamp <= deadline)
   - Time conditions must CHANGE state, permissions, or outcomes
   - If deadline exists, implement what happens BEFORE and AFTER it
   - Never store time variables that are never compared to block.timestamp

10. EVENT SEMANTICS MUST MATCH COMPLETED ACTIONS
    - Emit events ONLY AFTER successful state or value changes
    - ONE event per distinct action type; no merged or decorative events
    - Event parameters must include all relevant data about the action
    - Never emit events in failed transactions (they will revert anyway)
    - Event name should clearly indicate what happened (past tense)

11. NO UNUSED OR DECORATIVE CODE
    - Every variable must be WRITTEN in at least one function
    - Every variable must be READ in at least one function (or returned by getter)
    - Every function must modify state OR transfer value OR return useful data
    - Every state must be SET in at least one function
    - Every state must be CHECKED in at least one function guard
    - If behavior cannot be implemented faithfully, OMIT it rather than fake it

12. INTERNAL COHERENCE AND ADVERSARIAL SAFETY
    - Contract must remain correct under ARBITRARY call order
    - Functions must not contradict each other
    - Variables must represent a SINGLE, clear concept
    - Reentrancy protection where needed (external calls after state changes)
    - Integer overflow protection (use SafeMath or Solidity ^0.8.0 built-in)
    - Access control must not have bypasses

═══════════════════════════════════════════════════════════════════════════════
PHASE 3 - FORBIDDEN PATTERNS (IMMEDIATE REJECTION IF PRESENT)
═══════════════════════════════════════════════════════════════════════════════

❌ FORBIDDEN - Empty or stub function bodies:
```solidity
function doSomething() external {{
    // TODO: implement
}}
```

❌ FORBIDDEN - Unused state variables:
```solidity
uint256 public deadline;  // Never checked against block.timestamp
```

❌ FORBIDDEN - Silent failures:
```solidity
function transfer(address to, uint256 amount) external {{
    if (balances[msg.sender] < amount) return;  // Silent failure!
    balances[to] += amount;
}}
```

❌ FORBIDDEN - Decorative events without state changes:
```solidity
function doNothing() external {{
    emit ActionPerformed(msg.sender);  // No actual action!
}}
```

❌ FORBIDDEN - Unused states:
```solidity
enum State {{ ACTIVE, ASSIGNED, COMPLETED }}  // ASSIGNED never set in any function
State public currentState;
```

❌ FORBIDDEN - Stored funds never transferred:
```solidity
uint256 public fundsAllocated;  // Stored but never used in transfer
```

❌ FORBIDDEN - Non-functional reentrancy guard:
```solidity
modifier nonReentrant() {{
    require(msg.sender != address(0));  // Always true, useless!
    _;
}}

// Also wrong:
modifier nonReentrant() {{
    require(msg.sender == tx.origin);  // Blocks all smart contracts!
    _;
}}
```

❌ FORBIDDEN - State jumps that skip intermediate states:
```solidity
// If states are ACTIVE → ASSIGNED → COMPLETED
function complete() external {{
    currentState = State.COMPLETED;  // Jumps from ACTIVE, skips ASSIGNED!
}}
```

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: STATE MACHINE ANTI-PATTERNS
═══════════════════════════════════════════════════════════════════════════════

⚠️ WARNING: State machines are for WORKFLOW PHASES, not OPERATION TYPES

❌ WRONG - States that represent operation types:
```solidity
enum State {{ TokenCreation, Transfer, Approval, Delegation }}
// This makes ONLY ONE operation possible at a time for ALL users!

function transfer(address to, uint256 amount) external inState(State.Transfer) {{
    // Can only transfer when owner sets state to Transfer
    // Breaks ALL concurrent operations!
}}
```

✅ CORRECT - States that represent workflow phases:
```solidity
enum State {{ Fundraising, Active, Closed }}
// Multiple operation types are possible within each phase

function transfer(address to, uint256 amount) external {{
    require(currentState == State.Active, "Transfers only in Active phase");
    // All users can transfer simultaneously during Active phase
}}
```

RULE: If your states are named after FUNCTIONS (Transfer, Approval, Mint),
you are doing it WRONG. States should represent PHASES of the contract lifecycle.

EXAMPLES OF CORRECT STATE USAGE:
- Crowdfunding: Fundraising → Active → Refunding/Success
- Auction: Open → Ended → Claimed
- Vesting: Locked → Vesting → FullyVested
- Grant: Proposed → Approved → InProgress → Completed
- Sale: PreSale → PublicSale → Ended

EXAMPLES OF INCORRECT STATE USAGE (DO NOT DO THIS):
- Token: Minting, Transfer, Approval ❌ (operations, not phases)
- Payment: Deposit, Withdraw, Refund ❌ (operations, not phases)
- Governance: Propose, Vote, Execute ❌ (operations, not phases)

FOR TOKEN CONTRACTS:
- DO NOT use states to control transfer/approve/delegate
- These operations should be available SIMULTANEOUSLY to all users
- Only use states for phases like: Paused/Active, or PreSale/PublicSale/Ended

═══════════════════════════════════════════════════════════════════════════════
PHASE 4 - CORRECT IMPLEMENTATION PATTERNS (FOLLOW THESE EXAMPLES)
═══════════════════════════════════════════════════════════════════════════════

✅ CORRECT - Complete function with full logic:
```solidity
function releaseMilestonePayment(uint256 grantId, uint256 milestoneId) 
    external 
    validGrant(grantId)
    onlyGrantCreator(grantId)
    inState(grantId, State.ASSIGNED)
{{
    require(!milestones[grantId][milestoneId].paid, "Already paid");
    require(milestones[grantId][milestoneId].completed, "Milestone not completed");
    require(address(this).balance >= milestones[grantId][milestoneId].amount, "Insufficient funds");
    
    milestones[grantId][milestoneId].paid = true;
    grants[grantId].totalPaid += milestones[grantId][milestoneId].amount;
    
    (bool success, ) = grants[grantId].recipient.call{{value: milestones[grantId][milestoneId].amount}}("");
    require(success, "Transfer failed");
    
    emit MilestonePaymentReleased(grantId, milestoneId, milestones[grantId][milestoneId].amount);
    
    // Check if all milestones paid, transition to COMPLETED
    if (grants[grantId].totalPaid == grants[grantId].fundsAllocated) {{
        grants[grantId].state = State.COMPLETED;
        emit GrantCompleted(grantId);
    }}
}}
```

✅ CORRECT - All states are reachable:
```solidity
enum State {{ ACTIVE, ASSIGNED, COMPLETED, CANCELLED }}

function createGrant(...) external {{
    grants[id].state = State.ACTIVE;  // Entry point to ACTIVE
}}

function assignInitiative(uint256 grantId, ...) external inState(grantId, State.ACTIVE) {{
    // ... assignment logic ...
    grants[grantId].state = State.ASSIGNED;  // Transition to ASSIGNED
}}

function completeGrant(uint256 grantId) external inState(grantId, State.ASSIGNED) {{
    // ... completion logic ...
    grants[grantId].state = State.COMPLETED;  // Transition to COMPLETED
}}

function cancelGrant(uint256 grantId) external {{
    require(grants[grantId].state == State.ACTIVE || grants[grantId].state == State.ASSIGNED);
    grants[grantId].state = State.CANCELLED;  // Transition to CANCELLED
}}
```

✅ CORRECT - Economic variables are actually used:
```solidity
uint256 public pricePerToken;

function buyTokens(uint256 amount) external payable {{
    uint256 cost = amount * pricePerToken;  // Price is USED
    require(msg.value >= cost, "Insufficient payment");
    
    balances[msg.sender] += amount;
    
    if (msg.value > cost) {{
        (bool success, ) = msg.sender.call{{value: msg.value - cost}}("");
        require(success, "Refund failed");
    }}
}}
```

✅ CORRECT - Time variables are checked:
```solidity
uint256 public deadline;

function submitProposal(...) external {{
    require(block.timestamp <= deadline, "Deadline passed");  // Time CHECKED
    // ... proposal logic ...
}}

function finalizeAfterDeadline() external {{
    require(block.timestamp > deadline, "Deadline not reached");  // Time CHECKED
    // ... finalization logic ...
}}
```

✅ CORRECT - Historical checkpoint system:
```solidity
struct Checkpoint {{
    uint256 fromBlock;
    uint256 votes;
}}

mapping(address => Checkpoint[]) private checkpoints;

// Write checkpoint when votes change
function _writeCheckpoint(address account, uint256 newVotes) internal {{
    uint256 blockNumber = block.number;
    uint256 length = checkpoints[account].length;
    
    // Update current block checkpoint or create new one
    if (length > 0 && checkpoints[account][length - 1].fromBlock == blockNumber) {{
        checkpoints[account][length - 1].votes = newVotes;
    }} else {{
        checkpoints[account].push(Checkpoint(blockNumber, newVotes));
    }}
}}

// Read historical votes
function getPriorVotes(address account, uint256 blockNumber) external view returns (uint256) {{
    require(blockNumber < block.number, "Not yet determined");
    
    uint256 length = checkpoints[account].length;
    if (length == 0) return 0;
    
    // Binary search for the checkpoint at or before blockNumber
    // ... binary search implementation ...
}}
```

❌ WRONG - Checkpoint mapping never written to:
```solidity
mapping(address => uint256) public checkpoints;  // Not historical!

function getPriorVotes(address account, uint256 checkpointId) external view returns (uint256) {{
    return checkpoints[account];  // Always returns same value, not historical!
}}
```

CHECKPOINT REQUIREMENTS:
- Must store BLOCK NUMBER with each checkpoint
- Must be an ARRAY or linked list, not a single value
- Must be WRITTEN TO when voting power changes
- Must support HISTORICAL QUERIES (past block numbers)

═══════════════════════════════════════════════════════════════════════════════
PHASE 5 - SPECIFICATION ANALYSIS
═══════════════════════════════════════════════════════════════════════════════

CONTRACT SPECIFICATION:
{schema.model_dump_json(indent=2)}

PARTIES TO IMPLEMENT:
{chr(10).join(f"- {p.name} ({p.role}) - store as address state variable, implement role-based access control" for p in schema.parties) if schema.parties else "- No parties specified"}

FINANCIAL TERMS TO IMPLEMENT COMPLETELY:
{chr(10).join(f"- {t.purpose}: {t.amount} {t.currency} ({t.frequency if t.frequency else 'one-time'})" for t in schema.financial_terms) if schema.financial_terms else "- No financial terms specified"}

Analysis required:
- How do funds enter? (constructor deposit, payable function, multiple deposits?)
- How are funds released? (automatic, manual approval, milestone-based?)
- Who receives funds? (single party, multiple parties, split percentages?)
- Implement COMPLETE transfer logic with require() checks and actual value movement

OBLIGATIONS TO IMPLEMENT AS COMPLETE FUNCTIONS:
{chr(10).join(f"- {o.party} must: {o.description} (deadline: {o.deadline if o.deadline else 'none'})" for o in schema.obligations) if schema.obligations else "- No obligations specified"}

Analysis required for each obligation:
- What function implements this obligation?
- What state changes when this is fulfilled?
- Who can call this function? (implement access control)
- What happens if deadline is missed? (implement time checks)

REQUIRED CAPABILITIES (implement with appropriate functions):

**Function Capabilities to Implement:**
{chr(10).join(f"- {fn} - analyze what this capability MEANS and implement the FULL behavior" for fn in function_names) if function_names else "- Extract required capabilities from obligations and financial terms"}

GUIDANCE: These names indicate WHAT should be possible. Implement the BEHAVIOR, not just the name.
- Add helper functions if needed for the workflow
- Combine functions if they represent a single atomic operation
- Split functions if one name implies multiple distinct actions

**State Variables to Use Meaningfully:**
{chr(10).join(f"- {vn} - must be both WRITTEN and READ in function logic" for vn in variable_names) if variable_names else "- Extract variable names from financial terms, parties, and dates"}

CRITICAL: Every listed variable must appear in:
1. At least one function that WRITES to it
2. At least one function that READS from it (or a getter function)

**States to Implement with Transitions:**
{chr(10).join(f"- {sn} - implement transition logic TO and FROM this state" for sn in state_names) if state_names else "- Determine if contract needs states based on workflow analysis"}

CRITICAL: For each state listed:
1. At least one function must SET the contract to this state
2. At least one function must CHECK for this state (in modifier or require)
3. States must form a coherent workflow (no orphaned states)
4. States must represent PHASES, not OPERATION TYPES

**State Transitions to Enforce:**
{chr(10).join(f"- {st} - use require(currentState == ...) to enforce this transition" for st in state_transitions) if state_transitions else "- Implement transitions implied by obligations (e.g., create → assign → complete)"}

**Events to Emit on Real Actions:**
{chr(10).join(f"- {ev} - emit when the corresponding action COMPLETES successfully" for ev in events) if events else "- Create events based on function names (e.g., FunctionNameExecuted)"}

CRITICAL: Events must be emitted AFTER state/value changes, never before or without changes.

**Logic Conditions to Enforce:**
{chr(10).join(f"- {lc} - implement with require() checks and calculations" for lc in logic_conditions) if logic_conditions else "- Extract conditions from obligations, special terms, and domain logic"}

═══════════════════════════════════════════════════════════════════════════════
PHASE 6 - MANDATORY IMPLEMENTATION CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Before finalizing your contract, verify ALL of these:

WORKFLOW COHERENCE:
□ I can explain the complete user journey from start to finish
□ Every state serves a purpose in the workflow  
□ All state transitions are reachable through actual function calls
□ Functions form a logical sequence of operations
□ Users would understand what to call and when
□ Multiple users can perform different operations simultaneously (unless intentionally prevented)

STATE MACHINE:
□ Every defined state is SET in at least one function
□ Every defined state is CHECKED in at least one require() or modifier
□ State transitions follow a logical progression (no impossible jumps)
□ Terminal states (COMPLETED, CANCELLED) are reachable
□ States represent WORKFLOW PHASES, not operation types
□ If states are named after functions (Transfer, Approve), REDESIGN

ECONOMIC LOGIC:
□ If ANY payment/fund term exists, there is payable/transfer logic
□ All stored fund amounts are actually transferred somewhere
□ Conservation of value: deposits = withdrawals + remaining balance
□ All price/fee variables are used in calculations
□ Sufficient balance checks before all transfers

TIME LOGIC:
□ All deadline variables are compared to block.timestamp
□ Functions behave differently before vs after deadlines
□ Time-based state transitions are implemented if mentioned

ACCESS CONTROL:
□ All administrative functions have modifiers
□ All modifiers contain actual require() checks
□ Role-based access matches specification parties
□ No unauthorized access bypasses exist

ACCESS CONTROL VALIDATION:
□ Identified which functions should be restricted (admin, owner, creator)
□ Created appropriate modifiers (onlyOwner, onlyRole, etc.)
□ Applied modifiers to ALL restricted functions
□ Modifiers contain actual require() checks that revert
□ CRITICAL: Functions that mint, burn, pause, or change critical parameters MUST have access control
□ Test: "Can any random address call this function and break the contract?"

FUNCTIONS THAT ALMOST ALWAYS NEED ACCESS CONTROL:
- mint() / burn() - unless public minting is explicitly intended
- pause() / unpause() - only admin
- setPrice() / setFee() - only admin or governance
- transferOwnership() - only current owner
- withdraw() - only owner or authorized party
- deprecate() / upgrade() - only owner
- addToBlacklist() / removeFromBlacklist() - only admin

FUNCTION IMPLEMENTATION:
□ Zero functions with empty bodies or TODOs
□ All functions have: validation + logic + state change + event
□ No silent failures (no if/return pattern)
□ All require() statements have descriptive error messages

VARIABLE USAGE:
□ All declared variables are written by at least one function
□ All declared variables are read by at least one function
□ No decorative variables that don't affect behavior

EVENT EMISSIONS:
□ Events are emitted only after successful operations
□ One event type per action type (no merged events)
□ Events include all relevant parameters
□ Event names clearly indicate what happened

ERC20 TOKEN COMPLETENESS (if contract type is TOKEN):
□ name, symbol, decimals variables declared
□ totalSupply tracked and accurate
□ balances mapping for all accounts
□ allowances mapping for approvals
□ transfer(address to, uint256 amount) implemented
□ approve(address spender, uint256 amount) implemented
□ transferFrom(address from, address to, uint256 amount) implemented
□ balanceOf(address account) view function implemented
□ allowance(address owner, address spender) view function implemented
□ Transfer(address from, address to, uint256 value) event emitted
□ Approval(address owner, address spender, uint256 value) event emitted
□ All token operations work CONCURRENTLY (no state machine blocking them)

If ANY of these are missing, the contract is NOT ERC20 compliant.

GOVERNANCE/DELEGATION COMPLETENESS (if contract has delegation):
□ Delegate mapping exists (who delegates to whom)
□ Voting power mapping exists (current vote power)
□ Delegation TRANSFERS voting power, not just stores relationship
□ Votes UPDATE when tokens transfer
□ Checkpoints are HISTORICAL (block number + votes)
□ Checkpoints are WRITTEN when voting power changes
□ getPriorVotes() can query historical voting power
□ Invariant holds: sum(voting power) = sum(balances)

COMMON FAILURE CHECKS:
□ If contract has "Token" in name: verified full ERC20 implementation
□ If contract has "Governance" or "Delegation": votes update on transfer
□ If contract has "Checkpoint": they are written to AND historical
□ If contract has states: verified they represent PHASES not OPERATIONS
□ If contract has mint(): verified it has access control
□ If contract stores funds: verified they are actually transferred out
□ If contract has deadline: verified it's compared to block.timestamp

═══════════════════════════════════════════════════════════════════════════════
PHASE 7 - CONTRACT STRUCTURE TEMPLATE
═══════════════════════════════════════════════════════════════════════════════

Use this structure for your implementation:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract [ContractName] {{
    // ═══════════════════════════════════════════════════════════════
    // STATE ENUMS (if states are needed based on workflow)
    // ═══════════════════════════════════════════════════════════════
    enum State {{ {', '.join(state_names) if state_names else 'Active, Completed, Terminated'} }}
    
    // ═══════════════════════════════════════════════════════════════
    // STATE VARIABLES (using EXACT names, all must be used)
    // ═══════════════════════════════════════════════════════════════
    
    // Access control
    address public owner;
    // Add role-based addresses for each party from specification
    
    // State tracking (if needed)
    // State public currentState;  // Or mapping(uint256 => State) if per-resource
    
    // Economic variables (all must be used in transfers)
    // uint256 public price;
    // uint256 public totalFunds;
    // mapping(address => uint256) public balances;
    
    // Time variables (all must be checked against block.timestamp)
    // uint256 public deadline;
    // uint256 public startTime;
    
    // Domain-specific variables
    // Declare based on contract type and obligations
    
    // Counters for resource IDs
    // uint256 public resourceCount;
    
    // ═══════════════════════════════════════════════════════════════
    // STRUCTS (for complex resources)
    // ═══════════════════════════════════════════════════════════════
    // struct Resource {{
    //     uint256 id;
    //     State state;
    //     address owner;
    //     uint256 amount;
    //     // ... other fields
    // }}
    
    // ═══════════════════════════════════════════════════════════════
    // MAPPINGS (for resource storage)
    // ═══════════════════════════════════════════════════════════════
    // mapping(uint256 => Resource) public resources;
    
    // ═══════════════════════════════════════════════════════════════
    // EVENTS (one per action type, separate distinct actions)
    // ═══════════════════════════════════════════════════════════════
    // event ResourceCreated(uint256 indexed id, address indexed creator);
    // event StateChanged(uint256 indexed id, State newState);
    // event PaymentReleased(uint256 indexed id, address indexed recipient, uint256 amount);
    
    // ═══════════════════════════════════════════════════════════════
    // MODIFIERS (access control and state validation)
    // ═══════════════════════════════════════════════════════════════
    modifier onlyOwner() {{
        require(msg.sender == owner, "Not authorized");
        _;
    }}
    
    modifier onlyResourceOwner(uint256 resourceId) {{
        require(resources[resourceId].owner == msg.sender, "Not resource owner");
        _;
    }}
    
    modifier inState(uint256 resourceId, State _state) {{
        require(resources[resourceId].state == _state, "Invalid state for this action");
        _;
    }}
    
    modifier validResourceId(uint256 resourceId) {{
        require(resourceId < resourceCount, "Invalid resource ID");
        _;
    }}
    
    modifier beforeDeadline() {{
        require(block.timestamp <= deadline, "Deadline passed");
        _;
    }}
    
    modifier afterDeadline() {{
        require(block.timestamp > deadline, "Deadline not reached");
        _;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════
    constructor(...) {{
        owner = msg.sender;
        // Initialize all state variables
        // Set initial state if using state machine
        // currentState = State.Active;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // MAIN FUNCTIONS (implement complete logic)
    // ═══════════════════════════════════════════════════════════════
    
    // Each function must include:
    // 1. Access control (modifiers)
    // 2. State validation (require currentState or inState modifier)
    // 3. Input validation (require checks on parameters)
    // 4. State updates (modify storage variables)
    // 5. Fund transfers (if applicable, with success checks)
    // 6. Event emissions (after all changes succeed)
    // 7. State transitions (if applicable)
    
    // function createResource(...) external payable {{
    //     // 1. Access control: only authorized parties
    //     // 2. State validation: check contract or resource state
    //     // 3. Input validation: require(amount > 0, ...)
    //     // 4. State updates: resources[id] = Resource(...)
    //     // 5. Fund handling: if payable, store or transfer
    //     // 6. Event emission: emit ResourceCreated(id, msg.sender)
    //     // 7. State transition: currentState = State.NextState
    // }}
    
    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS (getters for all important state)
    // ═══════════════════════════════════════════════════════════════
    
    // function getResource(uint256 resourceId) external view validResourceId(resourceId) returns (Resource memory) {{
    //     return resources[resourceId];
    // }}
    
    // ═══════════════════════════════════════════════════════════════
    // INTERNAL HELPER FUNCTIONS (if needed for complex logic)
    // ═══════════════════════════════════════════════════════════════
    
    // function _calculateAmount(...) internal pure returns (uint256) {{
    //     // Complex calculations
    // }}
    
    // function _transferFunds(address recipient, uint256 amount) internal {{
    //     require(address(this).balance >= amount, "Insufficient balance");
    //     (bool success, ) = recipient.call{{value: amount}}("");
    //     require(success, "Transfer failed");
    // }}
}}
```

═══════════════════════════════════════════════════════════════════════════════
PHASE 8 - FINAL VALIDATION QUESTIONS
═══════════════════════════════════════════════════════════════════════════════

Before submitting your contract, answer these questions:

1. Can multiple users perform different operations simultaneously?
   (If no, your state machine is probably wrong)

2. If this is a token, can I use it in Uniswap/DEX?
   (If no, you're missing ERC20 functions or blocking them with states)

3. If delegation exists, does voting power actually move between accounts?
   (If no, your delegation is decorative)

4. If checkpoints exist, can I query voting power at block N?
   (If no, your checkpoints aren't historical)

5. Can a random attacker mint unlimited tokens?
   (If yes, you forgot access control)

6. Do all stored fund amounts eventually get transferred?
   (If no, you have unused economic variables)

7. Can I break any invariant by calling functions in creative orders?
   (If yes, your contract has a critical bug)

8. If there are states, do they represent phases or operation types?
   (If operation types, REDESIGN - states should be phases)

If you answered wrong to ANY of these, GO BACK and fix it.

═══════════════════════════════════════════════════════════════════════════════
FINAL INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

1. Complete PHASE 1 analysis before writing any code
2. Identify contract type and required standard behaviors
3. Map out complete workflow and state transitions
4. Implement ALL economic logic with actual fund transfers
5. Ensure ALL states are reachable and checked
6. Use ALL listed variables in meaningful ways
7. Verify ALL checklist items before finalizing
8. Return ONLY complete, production-ready Solidity code
9. NO placeholders, NO TODOs, NO stub functions
10. Every line of code must serve the specification's intent

Your goal: Generate a contract that FULLY implements the specification such that
violating any stated guarantee or workflow is IMPOSSIBLE on-chain.

BEGIN GENERATION:
"""


def create_mcp_task_description(abi, schema, contract_name: str) -> str:
    """
    Create task description for the MCP Server Generator Agent.
    Uses the comprehensive prompt from programs.py.
    """
    # Extract function information from ABI
    functions = [item for item in abi if item.get('type') == 'function']
    payable_functions = [f for f in functions if f.get('stateMutability') == 'payable']
    nonpayable_functions = [f for f in functions if f.get('stateMutability') == 'nonpayable']
    view_functions = [f for f in functions if f.get('stateMutability') in ['view', 'pure']]
    
    import json
    
    return f"""Generate a complete MCP server for this {schema.contract_type} smart contract.

CONTRACT NAME: {contract_name}
CONTRACT TYPE: {schema.contract_type}
PARTIES: {[f"{p.name} ({p.role})" for p in schema.parties]}

ABI SUMMARY:
- Payable functions: {len(payable_functions)}
- Non-payable functions: {len(nonpayable_functions)}
- View functions: {len(view_functions)}

COMPLETE ABI:
{json.dumps(abi, indent=2)}

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


# Alias for backward compatibility
def create_solidity_generator_task_description(schema):
    """
    Alias for create_solidity_generation_prompt for backward compatibility.
    """
    return create_solidity_generation_prompt(schema)


def create_audit_task_description(solidity_code: str) -> str:
    """
    Create task description for the Security Auditor Agent.
    """
    return f"""Perform a comprehensive security audit on this Solidity smart contract:

{solidity_code}

SYSTEMATIC AUDIT CHECKLIST - Check each category:

1. **REENTRANCY ATTACKS**: 
   - Look for external calls (call, transfer, send, delegatecall) followed by state changes
   - Check if state is updated BEFORE external calls (Checks-Effects-Interactions pattern)
   - Verify reentrancy guards (nonReentrant modifier) on sensitive functions

2. **ACCESS CONTROL**:
   - Verify onlyOwner or role-based modifiers on critical functions (withdraw, changeOwner, etc.)
   - Check if constructor properly initializes owner
   - Look for functions that should be internal/private but are public/external

3. **ARITHMETIC SAFETY**:
   - Check for unchecked arithmetic that could overflow/underflow
   - Verify SafeMath usage or Solidity ^0.8.0 built-in checks
   - Look for division by zero possibilities

4. **ETHER HANDLING**:
   - Check payable functions have proper access control
   - Verify withdraw/transfer functions validate amounts and recipients
   - Look for locked ether (payable functions with no withdrawal mechanism)

5. **DOS VULNERABILITIES**:
   - Look for unbounded loops that could hit gas limits
   - Check for external calls in loops
   - Verify functions can't be blocked by reverting recipients

6. **INPUT VALIDATION**:
   - Check require() statements validate all critical parameters
   - Verify address parameters check for address(0)
   - Ensure amount checks prevent zero or negative values

7. **TIMESTAMP DEPENDENCE**:
   - Check if block.timestamp is used for critical logic
   - Verify it's not used for randomness or precise timing

8. **EXTERNAL CALL SAFETY**:
   - Verify return values of external calls are checked
   - Check low-level calls (call, delegatecall) have proper error handling

Return ONLY valid JSON with specific findings:
{{
    "severity_level": "none|low|medium|high|critical",
    "approved": boolean (true if severity is none/low, false for medium/high/critical),
    "issues": [
        "SPECIFIC issue with line reference and exploit scenario",
        "Example: HIGH: Reentrancy in withdraw() - external call before balance update allows recursive calls"
    ],
    "recommendations": [
        "SPECIFIC remediation step, not generic advice",
        "Example: Move 'balances[msg.sender] = 0' BEFORE 'msg.sender.call{{value: amount}}()'"
    ],
    "vulnerability_count": number (total count of issues found),
    "security_score": "A|B|C|D|F" (A = no issues, B = only low, C = medium, D = high, F = critical)
}}

Be specific about WHERE issues are and HOW to fix them. Reference actual function names and variables from the code."""


def create_abi_generator_task_description(solidity_code: str) -> str:
    """
    Create task description for the ABI Generator Agent.
    """
    return f"""Generate the complete, accurate ABI (Application Binary Interface) for this Solidity contract:

{solidity_code}

REQUIREMENTS - Extract ALL of these:

1. **CONSTRUCTOR**: 
   - Include ALL constructor parameters with exact types (address, uint256, string, etc.)
   - stateMutability should be "nonpayable" unless constructor is payable
   - type: "constructor"

2. **ALL PUBLIC/EXTERNAL FUNCTIONS**:
   - Extract function name exactly as written
   - Include ALL parameters with correct types and names
   - Include ALL outputs with correct types
   - Set stateMutability: "pure" (no state read/write), "view" (reads state), "payable" (accepts ETH), or "nonpayable" (default)
   - type: "function"

3. **ALL EVENTS**:
   - Extract event name exactly as written
   - Include ALL parameters with correct types and names
   - Mark indexed parameters with "indexed": true
   - type: "event"

4. **TYPE ACCURACY**:
   - Use exact Solidity types: uint256 (not uint), address, bool, string, bytes, bytes32, etc.
   - For arrays: uint256[], address[], etc.
   - For mappings in public vars: treat as getter function
   - For enums: use uint8
   - For structs: expand to individual fields if returned

5. **PARAMETER NAMES**:
   - Preserve parameter names from code (critical for debugging)
   - Use empty string "" only if parameter has no name in code

VALIDATION:
- Every public/external function must be included
- Every event must be included
- Constructor must be included if it exists
- Types must match Solidity declarations EXACTLY
- Output must be valid JSON array

Return ONLY the JSON array (no markdown, no explanation):
[
  {{
    "type": "constructor",
    "stateMutability": "nonpayable",
    "inputs": [...]
  }},
  {{
    "type": "function",
    "name": "functionName",
    "stateMutability": "view|pure|payable|nonpayable",
    "inputs": [...],
    "outputs": [...]
  }},
  {{
    "type": "event",
    "name": "EventName",
    "inputs": [
      {{"name": "param", "type": "uint256", "indexed": true}}
    ]
  }}
]"""


def create_quality_evaluation_task_description(solidity_code: str, schema, contract_name: str) -> str:
    """
    Create task description for the Quality Evaluator Agent.
    Performs comprehensive multi-metric evaluation of generated contract quality.
    """
    conditions = schema.conditions if schema.conditions else {}
    function_names = conditions.get('function_names', [])
    variable_names = conditions.get('variable_names', [])
    state_names = conditions.get('state_names', [])
    state_transitions = conditions.get('state_transitions', [])
    events = conditions.get('events', [])
    logic_conditions = conditions.get('logic_conditions', [])
    
    import json
    schema_dict = schema.model_dump() if hasattr(schema, 'model_dump') else schema.dict()
    
    return f"""Perform a comprehensive quality evaluation of this generated Solidity smart contract against the original natural language specification.

═══════════════════════════════════════════════════════════════════════════════
GENERATED SOLIDITY CONTRACT
═══════════════════════════════════════════════════════════════════════════════

{solidity_code}

═══════════════════════════════════════════════════════════════════════════════
ORIGINAL CONTRACT SPECIFICATION
═══════════════════════════════════════════════════════════════════════════════

{json.dumps(schema_dict, indent=2)}

EXTRACTED KEY ELEMENTS:
- Expected Functions: {function_names if function_names else 'Not specified'}
- Expected Variables: {variable_names if variable_names else 'Not specified'}
- Expected States: {state_names if state_names else 'Not specified'}
- State Transitions: {state_transitions if state_transitions else 'Not specified'}
- Expected Events: {events if events else 'Not specified'}
- Logic Conditions: {logic_conditions if logic_conditions else 'Not specified'}

═══════════════════════════════════════════════════════════════════════════════
EVALUATION INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

Evaluate the contract across FIVE dimensions. For each, provide:
1. A numerical score (0-100)
2. Detailed breakdown showing what earned/lost points
3. Specific evidence from the code with line references

═══════════════════════════════════════════════════════════════════════════════
METRIC 1: FUNCTIONAL COMPLETENESS (0-100 points)
═══════════════════════════════════════════════════════════════════════════════

**Scoring Rules:**

A. Function Name Matching (Max 50 points):
   - For each expected function in specification:
     * Exact match found in code: +10 points
     * Semantic match (similar name/purpose): +7 points
     * Missing completely: -10 points
   - List each expected function and whether it was found

B. Function Implementation Quality (Max 50 points):
   - For each implemented function, check:
     * Has complete logic (not placeholder/TODO): +5 points
     * Has proper access control (modifiers/require): +3 points
     * Emits appropriate events: +2 points
     * Has input validation with require(): +2 points
   - Provide specific examples of good/bad implementations

**Output Format:**
```json
{{
  "function_matching": {{
    "expected_functions": ["list from spec"],
    "found_exact": ["functions with exact matches"],
    "found_semantic": ["functions with semantic matches"],
    "missing": ["functions not found"],
    "unexpected": ["functions not in spec"],
    "points": 0-50
  }},
  "implementation_quality": {{
    "complete_logic": ["functions with full implementation"],
    "incomplete_logic": ["functions with placeholders"],
    "proper_access_control": ["functions with modifiers/checks"],
    "missing_access_control": ["functions needing protection"],
    "event_emissions": ["functions emitting events"],
    "missing_events": ["functions not emitting events"],
    "input_validation": ["functions with require checks"],
    "missing_validation": ["functions needing validation"],
    "points": 0-50
  }},
  "total_score": 0-100,
  "evidence": ["specific code examples with line numbers"]
}}
```

═══════════════════════════════════════════════════════════════════════════════
METRIC 2: VARIABLE/PARAMETER FIDELITY (0-100 points)
═══════════════════════════════════════════════════════════════════════════════

**Scoring Rules:**

A. State Variable Completeness (Max 60 points):
   - For each expected variable in specification:
     * Variable declared: +10 points
     * Correct type (uint256 for amounts, address for parties, etc.): +5 points
     * Actually used in logic (written AND read): +5 points
     * Missing or decorative only: -10 points

B. Function Parameter Quality (Max 40 points):
   - Check representative functions:
     * Correct parameter count: +10 points
     * Correct parameter types: +10 points
     * Descriptive parameter names: +10 points
     * Parameters actually used in function: +10 points

**Output Format:**
```json
{{
  "state_variables": {{
    "expected_variables": ["list from spec"],
    "declared": ["variables found in contract"],
    "correct_types": ["variables with correct types"],
    "actively_used": ["variables used in logic"],
    "decorative_only": ["declared but never used"],
    "missing": ["expected but not found"],
    "points": 0-60
  }},
  "function_parameters": {{
    "functions_checked": ["sample of functions analyzed"],
    "correct_count": ["functions with right param count"],
    "correct_types": ["functions with right param types"],
    "descriptive_names": ["functions with good naming"],
    "parameters_used": ["functions using all params"],
    "points": 0-40
  }},
  "total_score": 0-100,
  "evidence": ["specific examples from code"]
}}
```

═══════════════════════════════════════════════════════════════════════════════
METRIC 3: STATE MACHINE CORRECTNESS (0-100 points)
═══════════════════════════════════════════════════════════════════════════════

**Scoring Rules:**

A. State Definition (Max 25 points):
   - All expected states present in enum: +15 points
   - States used in state variable declaration: +10 points
   - Extra unnecessary states: -5 points each

B. State Transitions (Max 50 points):
   - For each expected transition:
     * Transition implemented in code: +10 points
     * Has proper require() check: +10 points
     * Matches specification logic: +10 points
   - Missing transitions: -10 points each
   - Invalid transitions possible: -10 points each

C. State Guards (Max 25 points):
   - Functions use state-based modifiers: +10 points
   - Functions use state require() checks: +10 points
   - No state bypass vulnerabilities: +5 points

**Output Format:**
```json
{{
  "state_definition": {{
    "expected_states": ["list from spec"],
    "defined_states": ["states in enum"],
    "state_variable_exists": true/false,
    "extra_states": ["unnecessary states"],
    "points": 0-25
  }},
  "state_transitions": {{
    "expected_transitions": ["list from spec"],
    "implemented_correctly": ["transitions with proper logic"],
    "missing_transitions": ["expected but not found"],
    "invalid_transitions_possible": ["security issues"],
    "points": 0-50
  }},
  "state_guards": {{
    "functions_with_modifiers": ["functions using state modifiers"],
    "functions_with_checks": ["functions using state requires"],
    "bypass_vulnerabilities": ["issues found"],
    "points": 0-25
  }},
  "total_score": 0-100,
  "evidence": ["specific code examples"]
}}
```

═══════════════════════════════════════════════════════════════════════════════
METRIC 4: BUSINESS LOGIC FIDELITY (0-100 points) - MOST IMPORTANT
═══════════════════════════════════════════════════════════════════════════════

**Scoring Rules:**

A. Obligation Implementation (Max 30 points):
   - For each obligation in specification:
     * Obligation mapped to function: +10 points
     * Logic correctly implements obligation: +10 points
     * Proper enforcement (access control, checks): +10 points

B. Financial Logic (Max 30 points):
   - For each financial term:
     * Payment handling implemented: +10 points
     * Correct amounts/calculations: +10 points
     * Proper fund tracking: +10 points

C. Temporal Logic (Max 20 points):
   - For each date/deadline:
     * Deadline enforcement with block.timestamp: +10 points
     * Time-based behavior changes implemented: +10 points

D. Conditional Logic (Max 20 points):
   - For each logic condition:
     * Condition implemented in code: +10 points
     * Correct logic/calculations: +10 points

**Output Format:**
```json
{{
  "obligation_implementation": {{
    "total_obligations": 0,
    "obligations_with_functions": ["obligation → function mapping"],
    "correct_logic": ["obligations correctly implemented"],
    "missing_obligations": ["obligations not implemented"],
    "improper_enforcement": ["weak or missing checks"],
    "points": 0-30
  }},
  "financial_logic": {{
    "total_financial_terms": 0,
    "payment_handling": ["terms with payment functions"],
    "correct_calculations": ["terms with right amounts"],
    "fund_tracking": ["terms with proper accounting"],
    "missing_financial_logic": ["terms not implemented"],
    "points": 0-30
  }},
  "temporal_logic": {{
    "total_dates": 0,
    "deadline_enforcement": ["dates checked with block.timestamp"],
    "time_based_behavior": ["time-dependent logic implemented"],
    "missing_temporal_logic": ["dates not enforced"],
    "points": 0-20
  }},
  "conditional_logic": {{
    "total_conditions": 0,
    "implemented_conditions": ["conditions in code"],
    "correct_logic": ["conditions with right calculations"],
    "missing_conditions": ["conditions not implemented"],
    "points": 0-20
  }},
  "total_score": 0-100,
  "evidence": ["specific examples from code and spec"]
}}
```

═══════════════════════════════════════════════════════════════════════════════
METRIC 5: CODE QUALITY (0-100 points)
═══════════════════════════════════════════════════════════════════════════════

**Scoring Rules:**

A. Placeholder Detection (Max 30 points - DEDUCTIONS):
   - Start at 30 points
   - Search for: "// TODO", "// implement", "// logic", empty function bodies
   - Deduct 10 points for each placeholder found (max -30)

B. Error Message Quality (Max 25 points):
   - Count require() statements
   - Score = (requires with messages / total requires) * 25
   - Examples of good vs missing messages

C. Event Quality (Max 20 points):
   - Events match actions (not decorative): +10 points
   - Proper indexing of parameters: +5 points
   - All major actions have events: +5 points

D. Code Structure (Max 15 points):
   - Proper logical grouping: +5 points
   - No redundant code: +5 points
   - Clear naming conventions: +5 points

E. Documentation (Max 10 points):
   - NatSpec comments on functions: +5 points
   - Clear variable names: +5 points

**Output Format:**
```json
{{
  "placeholder_detection": {{
    "placeholders_found": ["list with line numbers"],
    "placeholder_count": 0,
    "points": 0-30
  }},
  "error_messages": {{
    "total_requires": 0,
    "requires_with_messages": 0,
    "requires_missing_messages": ["line numbers"],
    "percentage": 0-100,
    "points": 0-25
  }},
  "event_quality": {{
    "total_events": 0,
    "events_match_actions": ["good events"],
    "decorative_events": ["events without actions"],
    "proper_indexing": ["events with indexed params"],
    "missing_events": ["actions without events"],
    "points": 0-20
  }},
  "code_structure": {{
    "logical_grouping": true/false,
    "redundant_code_found": ["examples"],
    "naming_conventions": "good|fair|poor",
    "points": 0-15
  }},
  "documentation": {{
    "natspec_coverage": 0-100,
    "clear_variable_names": true/false,
    "points": 0-10
  }},
  "total_score": 0-100,
  "evidence": ["specific examples"]
}}
```

═══════════════════════════════════════════════════════════════════════════════
FINAL OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

Return ONLY valid JSON (no markdown, no explanation):

{{
  "contract_name": "{contract_name}",
  "evaluation_timestamp": "ISO timestamp",
  
  "metric_1_functional_completeness": {{
    "score": 0-100,
    "function_matching": {{}},
    "implementation_quality": {{}},
    "evidence": []
  }},
  
  "metric_2_variable_fidelity": {{
    "score": 0-100,
    "state_variables": {{}},
    "function_parameters": {{}},
    "evidence": []
  }},
  
  "metric_3_state_machine": {{
    "score": 0-100,
    "state_definition": {{}},
    "state_transitions": {{}},
    "state_guards": {{}},
    "evidence": []
  }},
  
  "metric_4_business_logic": {{
    "score": 0-100,
    "obligation_implementation": {{}},
    "financial_logic": {{}},
    "temporal_logic": {{}},
    "conditional_logic": {{}},
    "evidence": []
  }},
  
  "metric_5_code_quality": {{
    "score": 0-100,
    "placeholder_detection": {{}},
    "error_messages": {{}},
    "event_quality": {{}},
    "code_structure": {{}},
    "documentation": {{}},
    "evidence": []
  }},
  
  "composite_score": {{
    "functional_completeness_weighted": 0-25,
    "variable_fidelity_weighted": 0-15,
    "state_machine_weighted": 0-15,
    "business_logic_weighted": 0-35,
    "code_quality_weighted": 0-10,
    "final_score": 0-100,
    "grade": "A|B|C|D|F"
  }},
  
  "summary": {{
    "strengths": ["top 3-5 things done well"],
    "weaknesses": ["top 3-5 issues found"],
    "critical_gaps": ["must-fix issues"],
    "recommendation": "ACCEPT|REVISE|REJECT with rationale"
  }}
}}

CRITICAL INSTRUCTIONS:
1. Be thorough but objective - cite specific evidence
2. Use line numbers when referencing code
3. Compare implementation to specification systematically
4. Calculate final_score = (M1 * 0.25) + (M2 * 0.15) + (M3 * 0.15) + (M4 * 0.35) + (M5 * 0.10)
5. Grade: A(90-100), B(80-89), C(70-79), D(60-69), F(<60)
6. Be specific about what is missing vs what is implemented incorrectly
7. Return ONLY the JSON, no additional text"""
