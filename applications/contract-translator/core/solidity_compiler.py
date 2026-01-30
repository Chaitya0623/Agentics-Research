"""
Solidity Compilation Checker

This module provides utilities to check if generated Solidity contracts
can be compiled successfully using solc (Solidity compiler).
"""

import tempfile
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
import os


class SolidityCompilationChecker:
    """Check if Solidity code compiles successfully"""
    
    def __init__(self):
        """Initialize compiler checker"""
        self.compiler_cmd, self.solc_available = self._check_solc_available()
    
    def _strip_version_pragma(self, solidity_code: str) -> str:
        """Remove version pragma to allow compilation with any compiler version"""
        lines = solidity_code.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip pragma solidity lines
            if stripped.startswith('pragma solidity'):
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _check_solc_available(self) -> tuple[Optional[list], bool]:
        """Check if solc or solcjs is available in the system"""
        # Try solc first (native binary)
        try:
            result = subprocess.run(
                ['solc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return ['solc'], True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try solcjs (npm package)
        try:
            result = subprocess.run(
                ['npx', 'solcjs', '--version'],
                capture_output=True,
                text=True,
                timeout=5,
                shell=True  # Need shell on Windows for npx
            )
            if result.returncode == 0:
                return ['npx', 'solcjs'], True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return None, False
    
    def check_compilation(self, solidity_code: str) -> Dict[str, Any]:
        """
        Check if Solidity code compiles successfully
        
        Args:
            solidity_code: The Solidity source code to compile
            
        Returns:
            Dict with:
            - compiles: bool (True if compilation succeeded)
            - error_message: str (error details if compilation failed)
            - warnings: list (any compiler warnings)
            - compiler_version: str (solc version used)
        """
        
        if not self.solc_available:
            return {
                'compiles': None,
                'error_message': 'solc compiler not available. Install with: npm install -g solc',
                'warnings': [],
                'compiler_version': None
            }
        
        # Strip version pragma to avoid version mismatch issues
        # This allows compilation even if ground truth uses different Solidity version
        modified_code = self._strip_version_pragma(solidity_code)
        
        # Create output directory for compilation artifacts
        output_dir = Path('compilation_output')
        output_dir.mkdir(exist_ok=True)
        
        # Create temporary file for the Solidity code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(modified_code)
            tmp_path = tmp_file.name
        
        try:
            # Build compilation command based on available compiler
            if self.compiler_cmd[0] == 'npx':
                # solcjs has different syntax: solcjs --bin --abi --output-dir <dir> file.sol
                compile_cmd = self.compiler_cmd + ['--bin', '--abi', '--output-dir', str(output_dir), tmp_path]
                version_cmd = self.compiler_cmd + ['--version']
            else:
                # Native solc: solc --bin --abi -o <dir> file.sol
                compile_cmd = self.compiler_cmd + ['--bin', '--abi', '-o', str(output_dir), tmp_path]
                version_cmd = self.compiler_cmd + ['--version']
            
            # Try to compile the contract
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=(self.compiler_cmd[0] == 'npx')  # Use shell for npx on Windows
            )
            
            # Get compiler version
            version_result = subprocess.run(
                version_cmd,
                capture_output=True,
                text=True,
                timeout=5,
                shell=(self.compiler_cmd[0] == 'npx')
            )
            compiler_version = version_result.stdout.strip() if version_result.returncode == 0 else 'unknown'
            
            # Parse output
            if result.returncode == 0:
                # Compilation succeeded
                warnings = []
                if 'Warning:' in result.stderr:
                    # Extract warnings
                    for line in result.stderr.split('\n'):
                        if 'Warning:' in line:
                            warnings.append(line.strip())
                
                return {
                    'compiles': True,
                    'error_message': None,
                    'warnings': warnings,
                    'compiler_version': compiler_version
                }
            else:
                # Compilation failed
                return {
                    'compiles': False,
                    'error_message': result.stderr.strip(),
                    'warnings': [],
                    'compiler_version': compiler_version
                }
        
        except subprocess.TimeoutExpired:
            return {
                'compiles': False,
                'error_message': 'Compilation timed out after 30 seconds',
                'warnings': [],
                'compiler_version': None
            }
        
        except Exception as e:
            return {
                'compiles': False,
                'error_message': f'Unexpected error during compilation: {str(e)}',
                'warnings': [],
                'compiler_version': None
            }
        
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def get_compilation_summary(self, solidity_code: str) -> str:
        """
        Get a human-readable summary of compilation status
        
        Args:
            solidity_code: The Solidity source code
            
        Returns:
            str: Formatted summary
        """
        result = self.check_compilation(solidity_code)
        
        if result['compiles'] is None:
            return "⚠️  Compiler not available - cannot check compilation"
        elif result['compiles']:
            warnings_text = f" ({len(result['warnings'])} warnings)" if result['warnings'] else ""
            return f"✅ Compiles successfully{warnings_text}"
        else:
            error = result['error_message'][:100] + "..." if len(result['error_message']) > 100 else result['error_message']
            return f"❌ Compilation failed: {error}"


# Convenience function for quick checks
def check_solidity_compiles(solidity_code: str) -> Dict[str, Any]:
    """
    Quick check if Solidity code compiles
    
    Args:
        solidity_code: The Solidity source code
        
    Returns:
        Dict with compilation results
    """
    checker = SolidityCompilationChecker()
    return checker.check_compilation(solidity_code)
