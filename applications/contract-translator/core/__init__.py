"""
Core components for IBM Agentics Contract Translator

This package contains modular components for contract translation:
- schemas: Pydantic data models
- programs: Legacy Program classes (backward compatibility)
- task_builders: Task description generators for CrewAI
- agents: Agent creation and configuration
- translator: Main translation orchestration
"""

from .schemas import (
    PartyRole,
    ContractType,
    ContractParty,
    FinancialTerm,
    ContractDate,
    ContractObligation,
    ContractAsset,
    UniversalContractSchema,
)

from .programs import (
    UniversalContractParserProgram,
    UniversalSolidityGeneratorProgram,
    SecurityAuditorProgram,
    ABIGeneratorProgram,
    MCPServerGeneratorProgram,
)

from .task_builders import (
    create_parser_task_description,
    create_solidity_generator_task_description,
    create_audit_task_description,
    create_abi_generator_task_description,
    create_quality_evaluation_task_description,
)

from .agents import (
    create_agents,
    should_refine,
    create_refinement_task_description,
    _convert_to_crew_llm,
    DEFAULT_MAX_REFINEMENT_ITERATIONS,
)

from .translator import IBMAgenticContractTranslator

__all__ = [
    # Schemas
    'PartyRole',
    'ContractType',
    'ContractParty',
    'FinancialTerm',
    'ContractDate',
    'ContractObligation',
    'ContractAsset',
    'UniversalContractSchema',
    # Programs
    'UniversalContractParserProgram',
    'UniversalSolidityGeneratorProgram',
    'SecurityAuditorProgram',
    'ABIGeneratorProgram',
    'MCPServerGeneratorProgram',
    # Task Builders
    'create_parser_task_description',
    'create_solidity_generator_task_description',
    'create_audit_task_description',
    'create_abi_generator_task_description',
    'create_quality_evaluation_task_description',
    # Agent utilities
    'create_agents',
    'should_refine',
    'create_refinement_task_description',
    '_convert_to_crew_llm',
    'DEFAULT_MAX_REFINEMENT_ITERATIONS',
    # Main Translator
    'IBMAgenticContractTranslator',
]
