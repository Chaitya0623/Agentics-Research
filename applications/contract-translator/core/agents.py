"""
Agent creation and configuration for CrewAI

Defines specialized agents for each translation phase:
- Parser Agent: Extract structured contract data
- Generator Agent: Create Solidity code
- Auditor Agent: Security analysis
- Refiner Agent: Fix security vulnerabilities (reinforcement loop)
- ABI Agent: Generate contract ABI
- MCP Agent: Generate MCP server code

The reinforcement logic is integrated directly into agent creation and the pipeline,
enabling automatic code refinement when security audits identify issues.
"""

import os
from typing import Dict, Any, Optional
from crewai import Agent, LLM as CrewLLM


# Default maximum refinement iterations for the reinforcement loop
DEFAULT_MAX_REFINEMENT_ITERATIONS = 2


def _convert_to_crew_llm(agentics_llm) -> CrewLLM:
    """
    Convert Agentics LLM to CrewAI LLM format.
    Both use similar underlying structure, so we extract the model name and create a CrewAI LLM.
    """
    # Get the model name from the Agentics LLM
    model_name = getattr(agentics_llm, 'model', 'gpt-4o-mini')
    
    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Create CrewAI LLM with same configuration
    return CrewLLM(
        model=model_name,
        api_key=api_key,
        temperature=0.7
    )


def create_agents(crew_llm: CrewLLM, enable_reinforcement: bool = True) -> dict:
    """
    Create all specialized agents for the translation pipeline.
    
    Args:
        crew_llm: CrewAI LLM instance
        enable_reinforcement: If True, includes a Refiner Agent for the reinforcement loop
        
    Returns:
        Dictionary with agent instances for each phase, including refiner_agent if enabled
    """
    
    # Phase 2: Contract Parser Agent
    parser_agent = Agent(
        role="Contract Analysis Expert",
        goal="Extract precise, specific information from legal contracts",
        backstory=(
            "You are an expert contract analyst specializing in extracting exact terminology, "
            "function names, variable names, states, and conditions from legal documents. "
            "You never use generic placeholders - only specific terms from the contract."
        ),
        llm=crew_llm,
        verbose=False,
        allow_delegation=False
    )
    
    # Phase 3: Solidity Generator Agent
    generator_agent = Agent(
        role="Solidity Smart Contract Developer",
        goal="Generate complete, production-ready Solidity smart contracts",
        backstory=(
            "You are a Solidity expert who generates COMPLETE, FUNCTIONAL smart contracts. "
            "You implement every function with full logic, use require() for validation, "
            "implement proper access control, and ensure all variables are actively used. "
            "You never write placeholder code or empty functions."
        ),
        llm=crew_llm,
        verbose=False,
        allow_delegation=False
    )
    
    # Phase 4: Security Auditor Agent
    auditor_agent = Agent(
        role="Blockchain Security Auditor",
        goal="Identify security vulnerabilities in smart contracts",
        backstory=(
            "You are a blockchain security expert who audits smart contracts for vulnerabilities. "
            "You check for reentrancy, access control issues, integer overflow, and other common exploits. "
            "You provide severity ratings (none/low/medium/high/critical) based on exploitability and impact. "
            "You give specific line references and concrete remediation steps, not generic advice."
        ),
        llm=crew_llm,
        verbose=False,
        allow_delegation=False
    )
    
    # Phase 5: ABI Generator Agent
    abi_agent = Agent(
        role="Ethereum ABI Specialist",
        goal="Generate accurate ABI specifications from Solidity contracts",
        backstory=(
            "You are an Ethereum ABI expert who generates complete, accurate ABI JSON "
            "from Solidity contracts, including all functions, events, and constructor details."
        ),
        llm=crew_llm,
        verbose=False,
        allow_delegation=False
    )
    
    # Phase 6: MCP Server Generator Agent
    mcp_agent = Agent(
        role="MCP Server Developer",
        goal="Generate production-ready MCP server code for blockchain interaction",
        backstory=(
            "You are an expert Python developer specializing in Web3.py and MCP server generation. "
            "You create complete, self-contained MCP servers with proper error handling and "
            "transaction management for smart contract interaction."
        ),
        llm=crew_llm,
        verbose=False,
        allow_delegation=False
    )
    
    agents = {
        'parser_agent': parser_agent,
        'generator_agent': generator_agent,
        'auditor_agent': auditor_agent,
        'abi_agent': abi_agent,
        'mcp_agent': mcp_agent,
    }
    
    # Add Refiner Agent for reinforcement loop if enabled
    if enable_reinforcement:
        refiner_agent = Agent(
            role="Smart Contract Security Refiner",
            goal="Fix all identified security vulnerabilities in Solidity smart contracts",
            backstory=(
                "You are a Solidity security specialist who fixes smart contract vulnerabilities. "
                "Given a contract and a list of security issues from an audit, you rewrite the code "
                "to address every vulnerability while maintaining the original functionality. "
                "You follow the Checks-Effects-Interactions pattern, add reentrancy guards where needed, "
                "implement proper access control, validate all inputs with require(), "
                "and ensure no silent failures. You return ONLY the fixed Solidity code."
            ),
            llm=crew_llm,
            verbose=False,
            allow_delegation=False
        )
        agents['refiner_agent'] = refiner_agent
    
    return agents


def should_refine(audit_report: Dict[str, Any], refinement_count: int, max_iterations: int = DEFAULT_MAX_REFINEMENT_ITERATIONS) -> bool:
    """
    Determine if the contract should go through refinement based on audit results.
    
    This is the decision function for the reinforcement loop. It checks:
    1. Whether there are remaining refinement iterations
    2. Whether the audit found issues requiring fixes
    
    Args:
        audit_report: The security audit report dictionary
        refinement_count: Current number of refinement iterations completed
        max_iterations: Maximum allowed refinement iterations
        
    Returns:
        True if refinement should be performed, False otherwise
    """
    if refinement_count >= max_iterations:
        return False
    
    severity = audit_report.get('severity_level', 'unknown').lower()
    approved = audit_report.get('approved', False)
    
    # Refine if not approved and severity is medium or higher
    if not approved and severity in ['medium', 'high', 'critical']:
        return True
    
    return False


def create_refinement_task_description(solidity_code: str, audit_report: Dict[str, Any]) -> str:
    """
    Create task description for the Refiner Agent based on audit findings.
    
    Args:
        solidity_code: The current Solidity code that needs fixing
        audit_report: The security audit report with issues to fix
        
    Returns:
        Task description string for the refiner agent
    """
    issues = audit_report.get('issues', [])
    recommendations = audit_report.get('recommendations', [])
    severity = audit_report.get('severity_level', 'unknown')
    
    issues_text = "\n".join(f"  - {issue}" for issue in issues) if issues else "  - No specific issues listed"
    recommendations_text = "\n".join(f"  - {rec}" for rec in recommendations) if recommendations else "  - No specific recommendations"
    
    return f"""Fix ALL security vulnerabilities in this Solidity smart contract.

CURRENT CONTRACT CODE:
```solidity
{solidity_code}
```

SECURITY AUDIT FINDINGS (Severity: {severity.upper()}):
{issues_text}

REQUIRED FIXES:
{recommendations_text}

CRITICAL REQUIREMENTS:
1. Fix EVERY issue listed above - do not skip any vulnerability
2. Follow the Checks-Effects-Interactions pattern for all external calls
3. Add reentrancy guards (nonReentrant modifier) where needed
4. Ensure ALL state changes happen BEFORE external calls
5. Add proper access control (onlyOwner, role-based) on sensitive functions
6. Validate ALL inputs with require() statements - no silent failures
7. Check for zero addresses on address parameters
8. Ensure arithmetic operations are safe (Solidity ^0.8.0 has built-in overflow protection)
9. Preserve the original contract functionality while fixing security issues

Return ONLY the complete, fixed Solidity code with ALL vulnerabilities addressed.
Do not include explanations - just the corrected code."""


__all__ = [
    'create_agents',
    'should_refine',
    'create_refinement_task_description',
    '_convert_to_crew_llm',
    'DEFAULT_MAX_REFINEMENT_ITERATIONS'
]
