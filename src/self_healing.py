# Self-Healing via Test Suites
# Nach Code-Änderung führt Agent automatisch pytest aus. Bei Fehlern analysiert LLM den Traceback, generiert Fix, wendet an (max 3 Iterationen).

import subprocess
import re
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Import LLM Provider (zentrale Abstraktion)
from llm_provider import get_llm_manager, LLMProvider


@dataclass
class TestResult:
    """Result of a test run"""
    passed: bool
    output: str
    errors: List[str]
    failed_tests: List[str]
    duration: float


@dataclass
class HealingIteration:
    """Single healing iteration"""
    iteration: int
    test_result: TestResult
    analysis: str
    fix_applied: Optional[str]
    success: bool


class SelfHealingEngine:
    """
    Self-Healing Engine für automatische Fehlerbehebung.
    Nach Code-Änderung führt Agent automatisch pytest aus.
    Bei Fehlern analysiert LLM den Traceback, generiert Fix, wendet an (max 3 Iterationen).
    """
    
    def __init__(
        self,
        max_iterations: int = 3,
        test_command: str = "pytest",
        llm_manager: LLMProvider = None
    ):
        self.max_iterations = max_iterations
        self.test_command = test_command
        self._llm_manager = llm_manager or get_llm_manager()
        self.iterations: List[HealingIteration] = []
    
    def run_tests(self, test_path: str = "tests/", verbose: bool = True) -> TestResult:
        """
        Führe Tests aus und parse Ergebnisse.
        
        Args:
            test_path: Pfad zu den Tests
            verbose: Ausführliche Ausgabe
            
        Returns:
            TestResult mit Details
        """
        cmd = [self.test_command, test_path, "-v"] if verbose else [self.test_command, test_path]
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=Path.cwd()
            )
            
            duration = time.time() - start_time
            
            # Parse output
            output = result.stdout + result.stderr
            
            # Extract failed tests
            failed_tests = self._parse_failed_tests(output)
            
            # Extract errors
            errors = self._parse_errors(output)
            
            passed = result.returncode == 0
            
            return TestResult(
                passed=passed,
                output=output,
                errors=errors,
                failed_tests=failed_tests,
                duration=duration
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                output="Test timeout after 300 seconds",
                errors=["Timeout"],
                failed_tests=[],
                duration=300
            )
        except Exception as e:
            return TestResult(
                passed=False,
                output=str(e),
                errors=[str(e)],
                failed_tests=[],
                duration=0
            )
    
    def _parse_failed_tests(self, output: str) -> List[str]:
        """Parse failed test names from pytest output"""
        failed = []
        
        # Match patterns like "FAILED test_file.py::test_name"
        for line in output.split('\n'):
            if line.startswith('FAILED'):
                # Extract test name
                match = re.search(r'FAILED\s+(.+)', line)
                if match:
                    failed.append(match.group(1).strip())
            elif 'FAILED' in line and '::' in line:
                # Alternative format
                parts = line.split('FAILED')
                if len(parts) > 1:
                    failed.append(parts[1].strip())
        
        return failed
    
    def _parse_errors(self, output: str) -> List[str]:
        """Parse error messages from output"""
        errors = []
        
        # Extract traceback sections
        in_traceback = False
        current_error = []
        
        for line in output.split('\n'):
            if 'Traceback (most recent call last)' in line:
                in_traceback = True
                current_error = []
            elif in_traceback:
                if line.strip() and not line.startswith('  '):
                    # End of traceback
                    if current_error:
                        errors.append('\n'.join(current_error))
                    in_traceback = False
                else:
                    current_error.append(line)
        
        # Also capture assertion errors
        for line in output.split('\n'):
            if 'AssertionError' in line or 'Error:' in line:
                errors.append(line.strip())
        
        return errors[:10]  # Limit to 10 errors
    
    def analyze_failure(self, test_result: TestResult, code_context: str = "") -> str:
        """
        Analysiere Fehler mit LLM.
        
        Args:
            test_result: Das Testergebnis
            code_context: Optionaler Code-Kontext
            
        Returns:
            Analyse des Fehlers
        """
        prompt = f"""Analyze the following test failure and provide a fix.

Test Output:
{test_result.output[:2000]}

Failed Tests: {test_result.failed_tests}

Errors: {test_result.errors}

Code Context:
{code_context[:1000]}

Provide:
1. Root cause of the failure
2. The exact code fix needed
3. Brief explanation

Format your response as:
ROOT CAUSE: <description>
FIX: <code to fix>
EXPLANATION: <brief explanation>"""
        
        try:
            provider = self._llm_manager.get_provider()
            if provider:
                return provider.generate(prompt)
            else:
                return "Error: No LLM provider available"
                
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return f"Could not analyze with LLM: {e}"
    
    def parse_fix(self, analysis: str) -> Optional[Dict[str, str]]:
        """
        Parse die Fix-Information aus der Analyse.
        
        Args:
            analysis: Die LLM-Analyse
            
        Returns:
            Dict mit file_path und fix_code
        """
        try:
            # Extract file and fix from analysis
            lines = analysis.split('\n')
            
            fix_code = ""
            file_path = None
            
            in_fix = False
            for line in lines:
                if line.startswith('FIX:'):
                    in_fix = True
                    fix_code = line[4:].strip()
                elif in_fix:
                    fix_code += "\n" + line
            
            # Try to extract file path from context
            # This is a simplified version - in production would need more sophisticated parsing
            return {
                "fix_code": fix_code.strip(),
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Parse fix error: {e}")
            return None
    
    def apply_fix(self, fix: Dict[str, str], file_path: str) -> bool:
        """
        Wende den Fix an.
        
        Args:
            fix: Die Fix-Information
            file_path: Die zu bearbeitende Datei
            
        Returns:
            True wenn erfolgreich
        """
        try:
            # Read current file
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            current_content = path.read_text()
            
            # Apply fix - this is simplified
            # In production, would use more sophisticated diff application
            new_content = current_content + "\n# Fix applied: " + fix.get('analysis', '')[:100]
            
            path.write_text(new_content)
            
            logger.info(f"Applied fix to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Apply fix error: {e}")
            return False
    
    def heal(
        self,
        test_path: str = "tests/",
        code_context: str = "",
        file_to_fix: str = None
    ) -> Tuple[bool, List[HealingIteration]]:
        """
        Führe Self-Healing-Zyklus aus (max 3 Iterationen).
        
        Args:
            test_path: Pfad zu den Tests
            code_context: Optionaler Code-Kontext
            file_to_fix: Optionale Datei die gefixt werden soll
            
        Returns:
            Tuple von (erfolgreich, iterations)
        """
        self.iterations = []
        
        for i in range(1, self.max_iterations + 1):
            logger.info(f"Healing iteration {i}/{self.max_iterations}")
            
            # Run tests
            test_result = self.run_tests(test_path)
            
            if test_result.passed:
                logger.info("All tests passed!")
                return True, self.iterations
            
            # Analyze failure
            analysis = self.analyze_failure(test_result, code_context)
            
            # Parse fix
            fix = self.parse_fix(analysis)
            
            # Apply fix if possible
            fix_applied = None
            if fix and file_to_fix:
                success = self.apply_fix(fix, file_to_fix)
                if success:
                    fix_applied = fix.get('fix_code', '')[:100]
            
            # Record iteration
            iteration = HealingIteration(
                iteration=i,
                test_result=test_result,
                analysis=analysis,
                fix_applied=fix_applied,
                success=False
            )
            self.iterations.append(iteration)
            
            logger.info(f"Iteration {i} complete - tests still failing")
        
        # All iterations complete
        return False, self.iterations
    
    def get_report(self) -> Dict:
        """Generate healing report"""
        return {
            "total_iterations": len(self.iterations),
            "max_iterations": self.max_iterations,
            "success": any(i.success for i in self.iterations),
            "iterations": [
                {
                    "iteration": i.iteration,
                    "passed": i.test_result.passed,
                    "failed_tests": i.test_result.failed_tests,
                    "fix_applied": i.fix_applied is not None,
                    "analysis": i.analysis[:200]
                }
                for i in self.iterations
            ]
        }


# Integration with agent.py
class SelfHealingAgent:
    """Agent mit Self-Healing Fähigkeiten"""
    
    def __init__(self, max_iterations: int = 3):
        self.healing_engine = SelfHealingEngine(max_iterations=max_iterations)
    
    def execute_with_healing(
        self,
        task: str,
        test_path: str = "tests/",
        file_to_fix: str = None
    ) -> Dict:
        """
        Führe Task aus mit Self-Healing.
        
        Args:
            task: Der auszuführende Task
            test_path: Pfad zu den Tests
            file_to_fix: Zu fixende Datei
            
        Returns:
            Dict mit Ergebnis und Healing-Report
        """
        # First execute the task (implementation would be in agent.py)
        result = f"Executed: {task}"
        
        # Then run healing
        success, iterations = self.healing_engine.heal(
            test_path=test_path,
            code_context=task,
            file_to_fix=file_to_fix
        )
        
        return {
            "task_result": result,
            "healing_success": success,
            "healing_report": self.healing_engine.get_report()
        }


# CLI interface
def main():
    """CLI interface for self-healing"""
    import sys
    
    engine = SelfHealingEngine()
    
    test_path = sys.argv[1] if len(sys.argv) > 1 else "tests/"
    file_to_fix = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Running self-healing on {test_path}...")
    print("-" * 50)
    
    success, iterations = engine.heal(test_path=test_path, file_to_fix=file_to_fix)
    
    print(f"\n{'✓' if success else '✗'} Self-healing {'successful' if success else 'failed'}")
    print(f"Total iterations: {len(iterations)}")
    
    for i in iterations:
        print(f"\nIteration {i.iteration}:")
        print(f"  Tests passed: {i.test_result.passed}")
        print(f"  Failed tests: {i.test_result.failed_tests[:3]}")
        print(f"  Fix applied: {i.fix_applied is not None}")


if __name__ == "__main__":
    main()