# Orchestrator Mode - Multi-Agent Task Management
# Komplexe Tasks werden in Subtasks zerlegt (Architect → Code → Debug → Test)

import uuid
import json
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Roles for multi-agent system"""
    ARCHITECT = "architect"
    CODER = "coder"
    DEBUGGER = "debugger"
    TESTER = "tester"
    REVIEWER = "reviewer"


@dataclass
class SubTask:
    """Individual subtask in the orchestrator"""
    id: str
    role: AgentRole
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    prompt_template: str = ""
    dependencies: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.id = self.id or str(uuid.uuid4())[:8]


@dataclass
class TaskResult:
    """Result of orchestrator task execution"""
    task_id: str
    status: str
    subtasks: List[SubTask]
    final_result: str
    duration: float
    errors: List[str] = field(default_factory=list)


class SubAgent:
    """Specialized sub-agent for specific role"""
    
    def __init__(self, role: AgentRole):
        self.role = role
        self.tools = self._get_tools_for_role(role)
        self.prompt_template = self._get_prompt_template(role)
    
    def _get_tools_for_role(self, role: AgentRole) -> List[str]:
        """Get tools available for each role"""
        tools_map = {
            AgentRole.ARCHITECT: [
                "analyze", "plan", "design", "review_architecture"
            ],
            AgentRole.CODER: [
                "write_code", "edit_file", "create_file", "read_file"
            ],
            AgentRole.DEBUGGER: [
                "debug", "analyze_error", "fix_bug", "inspect_code"
            ],
            AgentRole.TESTER: [
                "write_test", "run_test", "validate", "check_coverage"
            ],
            AgentRole.REVIEWER: [
                "review_code", "check_quality", "suggest_improvements"
            ]
        }
        return tools_map.get(role, [])
    
    def _get_prompt_template(self, role: AgentRole) -> str:
        """Get prompt template for each role"""
        templates = {
            AgentRole.ARCHITECT: """You are an Architect agent. Your role is to:
- Analyze the problem and break it down into components
- Design the overall solution architecture
- Identify dependencies and constraints
- Create a detailed plan for implementation

Task: {task}
Context: {context}

Provide:
1. Problem analysis
2. Component breakdown
3. Architecture design
4. Implementation plan""",
            
            AgentRole.CODER: """You are a Coder agent. Your role is to:
- Write clean, efficient code
- Follow best practices and patterns
- Implement according to specifications
- Handle edge cases

Task: {task}
Architecture: {architecture}
Context: {context}

Provide:
1. Implementation code
2. Explanation of approach
3. Any assumptions made""",
            
            AgentRole.DEBUGGER: """You are a Debugger agent. Your role is to:
- Identify bugs and issues in code
- Analyze error messages and stack traces
- Find root causes of problems
- Suggest and implement fixes

Task: {task}
Code: {code}
Error: {error}

Provide:
1. Problem identification
2. Root cause analysis
3. Fix implementation
4. Verification steps""",
            
            AgentRole.TESTER: """You are a Tester agent. Your role is to:
- Write comprehensive tests
- Validate functionality
- Check edge cases
- Ensure code quality

Task: {task}
Code: {code}
Architecture: {architecture}

Provide:
1. Test cases
2. Test implementation
3. Validation results
4. Coverage analysis""",
            
            AgentRole.REVIEWER: """You are a Reviewer agent. Your role is to:
- Review code for quality and best practices
- Check for security issues
- Suggest improvements
- Ensure maintainability

Task: {task}
Code: {code}
Tests: {tests}

Provide:
1. Code quality assessment
2. Security review
3. Improvement suggestions
4. Final approval"""
        }
        return templates.get(role, "")
    
    def execute(self, task: str, context: Dict = None) -> str:
        """Execute task with role-specific prompt"""
        context = context or {}
        
        # Build prompt with template
        prompt = self.prompt_template.format(
            task=task,
            context=context.get('context', ''),
            architecture=context.get('architecture', ''),
            code=context.get('code', ''),
            error=context.get('error', ''),
            tests=context.get('tests', '')
        )
        
        # In production, this would call the LLM
        # For now, return a mock response
        return f"[{self.role.value}] Executed: {task[:50]}..."


class Orchestrator:
    """
    Orchestrator für Multi-Agent Task Management.
    Komplexe Tasks werden in Subtasks zerlegt (Architect → Code → Debug → Test).
    Jeder Sub-Agent hat spezialisierte Tools und Prompt-Template.
    """
    
    def __init__(self, enable_parallel: bool = True):
        self.sub_agents: Dict[AgentRole, SubAgent] = {
            role: SubAgent(role) for role in AgentRole
        }
        self.enable_parallel = enable_parallel
        self.current_task: Optional[str] = None
        self.subtasks: List[SubTask] = []
    
    def decompose_task(self, task: str) -> List[SubTask]:
        """
        Zerlege komplexen Task in Subtasks.
        
        Args:
            task: Der zu zerlegende Task
            
        Returns:
            Liste von SubTasks
        """
        subtasks = []
        
        # Create subtask chain based on task complexity
        # Default: Architect → Coder → Debugger → Tester → Reviewer
        
        # 1. Architect - Analyze and plan
        architect_task = SubTask(
            id=f"task_{uuid.uuid4().hex[:6]}",
            role=AgentRole.ARCHITECT,
            description=f"Analyze and plan: {task}",
            tools=self.sub_agents[AgentRole.ARCHITECT].tools,
            prompt_template=self.sub_agents[AgentRole.ARCHITECT].prompt_template
        )
        subtasks.append(architect_task)
        
        # 2. Coder - Implement
        coder_task = SubTask(
            id=f"task_{uuid.uuid4().hex[:6]}",
            role=AgentRole.CODER,
            description=f"Implement: {task}",
            tools=self.sub_agents[AgentRole.CODER].tools,
            prompt_template=self.sub_agents[AgentRole.CODER].prompt_template,
            dependencies=[architect_task.id]
        )
        subtasks.append(coder_task)
        
        # 3. Debugger - Fix issues (conditional)
        debugger_task = SubTask(
            id=f"task_{uuid.uuid4().hex[:6]}",
            role=AgentRole.DEBUGGER,
            description=f"Debug implementation of: {task}",
            tools=self.sub_agents[AgentRole.DEBUGGER].tools,
            prompt_template=self.sub_agents[AgentRole.DEBUGGER].prompt_template,
            dependencies=[coder_task.id]
        )
        subtasks.append(debugger_task)
        
        # 4. Tester - Test
        tester_task = SubTask(
            id=f"task_{uuid.uuid4().hex[:6]}",
            role=AgentRole.TESTER,
            description=f"Test implementation of: {task}",
            tools=self.sub_agents[AgentRole.TESTER].tools,
            prompt_template=self.sub_agents[AgentRole.TESTER].prompt_template,
            dependencies=[coder_task.id]
        )
        subtasks.append(tester_task)
        
        # 5. Reviewer - Review
        reviewer_task = SubTask(
            id=f"task_{uuid.uuid4().hex[:6]}",
            role=AgentRole.REVIEWER,
            description=f"Review final implementation of: {task}",
            tools=self.sub_agents[AgentRole.REVIEWER].tools,
            prompt_template=self.sub_agents[AgentRole.REVIEWER].prompt_template,
            dependencies=[tester_task.id, debugger_task.id]
        )
        subtasks.append(reviewer_task)
        
        self.subtasks = subtasks
        return subtasks
    
    def _can_execute(self, task: SubTask) -> bool:
        """Check if task dependencies are satisfied"""
        if not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            dep_task = next((t for t in self.subtasks if t.id == dep_id), None)
            if not dep_task or dep_task.status != "completed":
                return False
        
        return True
    
    def execute_task(self, task: str, context: Dict = None) -> TaskResult:
        """
        Führe Task mit Multi-Agent Orchestration aus.
        
        Args:
            task: Der auszuführende Task
            context: Zusätzlicher Kontext
            
        Returns:
            TaskResult mit allen Subtask-Ergebnissen
        """
        start_time = datetime.now()
        self.current_task = task
        context = context or {}
        
        # Decompose task
        subtasks = self.decompose_task(task)
        
        results = []
        errors = []
        
        # Execute subtasks in order (respecting dependencies)
        for subtask in subtasks:
            # Wait for dependencies
            while not self._can_execute(subtask):
                # In production, would use proper async handling
                break
            
            subtask.status = "in_progress"
            
            # Get context from previous subtasks
            task_context = self._build_context(subtask, context)
            
            # Execute with appropriate agent
            try:
                agent = self.sub_agents[subtask.role]
                result = agent.execute(subtask.description, task_context)
                
                subtask.status = "completed"
                subtask.result = result
                results.append(result)
                
            except Exception as e:
                subtask.status = "failed"
                errors.append(f"{subtask.role.value}: {str(e)}")
                logger.error(f"Subtask {subtask.id} failed: {e}")
        
        # Build final result
        duration = (datetime.now() - start_time).total_seconds()
        
        final_result = self._build_final_result(results)
        
        return TaskResult(
            task_id=str(uuid.uuid4())[:8],
            status="completed" if not errors else "partial",
            subtasks=subtasks,
            final_result=final_result,
            duration=duration,
            errors=errors
        )
    
    def _build_context(self, task: SubTask, global_context: Dict) -> Dict:
        """Build context for subtask from previous results"""
        context = global_context.copy()
        
        # Get results from dependencies
        for dep_id in task.dependencies:
            dep_task = next((t for t in self.subtasks if t.id == dep_id), None)
            if dep_task and dep_task.result:
                if task.role == AgentRole.CODER:
                    context['architecture'] = dep_task.result
                elif task.role == AgentRole.DEBUGGER:
                    context['code'] = dep_task.result
                elif task.role == AgentRole.TESTER:
                    context['code'] = dep_task.result
                elif task.role == AgentRole.REVIEWER:
                    context['tests'] = dep_task.result
        
        return context
    
    def _build_final_result(self, results: List[str]) -> str:
        """Build final result from all subtask results"""
        if not results:
            return "No results"
        
        summary = "=== Orchestrator Task Execution ===\n\n"
        
        for i, result in enumerate(results, 1):
            summary += f"Step {i}: {result[:200]}...\n\n"
        
        return summary
    
    def get_status(self) -> Dict:
        """Get current orchestrator status"""
        return {
            "current_task": self.current_task,
            "subtasks": [
                {
                    "id": t.id,
                    "role": t.role.value,
                    "status": t.status,
                    "dependencies": t.dependencies
                }
                for t in self.subtasks
            ]
        }


# Integration with agent.py
class OrchestratorAgent:
    """Agent mit Orchestrator-Mode für komplexe Tasks"""
    
    def __init__(self, use_orchestrator: bool = False):
        self.use_orchestrator = use_orchestrator
        self.orchestrator = Orchestrator() if use_orchestrator else None
    
    def process_message(self, message: str) -> str:
        """Process message with optional orchestrator"""
        if self.use_orchestrator and self.orchestrator:
            # Use orchestrator for complex tasks
            result = self.orchestrator.execute_task(message)
            return result.final_result
        else:
            # Use standard processing
            return f"Standard processing: {message}"


# CLI interface
def main():
    """CLI interface for orchestrator"""
    import sys
    
    orchestrator = Orchestrator()
    
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <task>")
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    
    print(f"Executing task: {task}")
    print("-" * 50)
    
    result = orchestrator.execute_task(task)
    
    print(f"\nStatus: {result.status}")
    print(f"Duration: {result.duration:.2f}s")
    print(f"\nFinal Result:\n{result.final_result}")
    
    if result.errors:
        print(f"\nErrors: {result.errors}")


if __name__ == "__main__":
    main()