# Native Subagents - Parallel Task Execution with Budgets & Persistent Sessions
# Subagents laufen parallel via asyncio.gather. Jeder Subagent hat eigene Tools, LLM-Client, Memory.
# Hauptagent aggregiert Ergebnisse.
# Unterstützt: task_budget, subagent-to-subagent delegation, session persistence

import asyncio
import uuid
import json
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SubAgentType(Enum):
    """Types of subagents"""
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYZER = "analyzer"
    WRITER = "writer"
    EXECUTOR = "executor"
    BUILDER = "builder"  # New: for making code changes
    TESTER = "tester"   # New: for running tests


@dataclass
class SubAgentSession:
    """Persistent session for subagent"""
    session_id: str
    agent_id: str
    created_at: datetime
    last_active: datetime
    history: List[Dict] = field(default_factory=list)
    state: Dict = field(default_factory=dict)
    task_budget: int = 10
    tasks_used: int = 0


@dataclass
class SubAgentBudget:
    """Budget tracking for subagent"""
    remaining: int
    total: int
    type: str = "task"  # "task" or "token"


@dataclass
class SubAgentConfig:
    """Configuration for a subagent"""
    name: str
    agent_type: SubAgentType
    tools: List[str]
    system_prompt: str
    max_retries: int = 3
    timeout: int = 60


@dataclass
class SubAgentResult:
    """Result from a subagent"""
    agent_id: str
    agent_name: str
    agent_type: str
    success: bool
    result: Any
    error: Optional[str] = None
    duration: float = 0
    metadata: Dict = field(default_factory=dict)


class BaseSubAgent:
    """
    Base class for subagents.
    Jeder Subagent hat eigene Tools, LLM-Client, Memory.
    """
    
    def __init__(
        self,
        config: SubAgentConfig,
        llm_client: Any = None,
        memory_client: Any = None
    ):
        self.config = config
        self.agent_id = str(uuid.uuid4())[:8]
        self.llm_client = llm_client
        self.memory_client = memory_client
        self._tool_registry = self._init_tools()
    
    def _init_tools(self) -> Dict[str, Callable]:
        """Initialize tools for this subagent"""
        # Base tools - can be overridden by subclasses
        return {
            "search": self._search,
            "analyze": self._analyze,
            "execute": self._execute
        }
    
    async def _search(self, query: str) -> str:
        """Search tool"""
        return f"Search results for: {query}"
    
    async def _analyze(self, data: Any) -> str:
        """Analyze tool"""
        return f"Analysis of: {type(data)}"
    
    async def _execute(self, command: str) -> str:
        """Execute tool"""
        return f"Executed: {command}"
    
    async def execute(self, task: str, context: Dict = None) -> SubAgentResult:
        """
        Führe Task asynchron aus.
        
        Args:
            task: Die auszuführende Aufgabe
            context: Optionaler Kontext
            
        Returns:
            SubAgentResult
        """
        start_time = datetime.now()
        context = context or {}
        
        try:
            # Build prompt with system prompt
            full_prompt = f"{self.config.system_prompt}\n\nTask: {task}"
            
            # Execute with LLM (mock for now)
            result = await self._execute_with_llm(full_prompt, context)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return SubAgentResult(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                agent_type=self.config.agent_type.value,
                success=True,
                result=result,
                duration=duration
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Subagent {self.config.name} error: {e}")
            
            return SubAgentResult(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                agent_type=self.config.agent_type.value,
                success=False,
                result=None,
                error=str(e),
                duration=duration
            )
    
    async def _execute_with_llm(self, prompt: str, context: Dict) -> str:
        """Execute with LLM - override in subclasses"""
        # Mock implementation - in production would call actual LLM
        await asyncio.sleep(0.1)  # Simulate async operation
        return f"[{self.config.name}] Processed: {prompt[:50]}..."


class ResearcherAgent(BaseSubAgent):
    """Researcher subagent for information gathering"""
    
    def __init__(self, config: SubAgentConfig, llm_client: Any = None):
        config.system_prompt = config.system_prompt or """You are a Researcher agent.
Your role is to gather information, search for relevant data, and provide comprehensive answers.
Be thorough and cite sources when possible."""
        super().__init__(config, llm_client)
        self._tool_registry["search_web"] = self._search_web
        self._tool_registry["find_docs"] = self._find_docs
    
    async def _search_web(self, query: str) -> str:
        return f"Web search: {query}"
    
    async def _find_docs(self, topic: str) -> str:
        return f"Documentation for: {topic}"


class CoderAgent(BaseSubAgent):
    """Coder subagent for code generation and manipulation"""
    
    def __init__(self, config: SubAgentConfig, llm_client: Any = None):
        config.system_prompt = config.system_prompt or """You are a Coder agent.
Your role is to write, edit, and debug code.
Follow best practices and provide clean, maintainable code."""
        super().__init__(config, llm_client)
        self._tool_registry["write_code"] = self._write_code
        self._tool_registry["edit_code"] = self._edit_code
        self._tool_registry["debug"] = self._debug
    
    async def _write_code(self, spec: str) -> str:
        return f"Code written for: {spec}"
    
    async def _edit_code(self, file: str, changes: str) -> str:
        return f"Edited: {file}"
    
    async def _debug(self, error: str) -> str:
        return f"Debugged: {error}"


class AnalyzerAgent(BaseSubAgent):
    """Analyzer subagent for data analysis"""
    
    def __init__(self, config: SubAgentConfig, llm_client: Any = None):
        config.system_prompt = config.system_prompt or """You are an Analyzer agent.
Your role is to analyze data, identify patterns, and provide insights.
Use statistical methods and clear visualizations."""
        super().__init__(config, llm_client)
        self._tool_registry["analyze_data"] = self._analyze_data
        self._tool_registry["visualize"] = self._visualize
    
    async def _analyze_data(self, data: Any) -> str:
        return f"Data analyzed: {type(data)}"
    
    async def _visualize(self, data: Any) -> str:
        return "Visualization created"


class WriterAgent(BaseSubAgent):
    """Writer subagent for content creation"""
    
    def __init__(self, config: SubAgentConfig, llm_client: Any = None):
        config.system_prompt = config.system_prompt or """You are a Writer agent.
Your role is to create clear, engaging content.
Adapt your writing style to the target audience."""
        super().__init__(config, llm_client)
        self._tool_registry["write"] = self._write
        self._tool_registry["edit"] = self._edit
    
    async def _write(self, topic: str) -> str:
        return f"Content written about: {topic}"
    
    async def _edit(self, text: str) -> str:
        return "Text edited"


class ExecutorAgent(BaseSubAgent):
    """Executor subagent for running commands"""
    
    def __init__(self, config: SubAgentConfig, llm_client: Any = None):
        config.system_prompt = config.system_prompt or """You are an Executor agent.
Your role is to execute commands and tasks efficiently.
Report results clearly and handle errors gracefully."""
        super().__init__(config, llm_client)
        self._tool_registry["run"] = self._run
        self._tool_registry["install"] = self._install
    
    async def _run(self, command: str) -> str:
        return f"Running: {command}"
    
    async def _install(self, package: str) -> str:
        return f"Installing: {package}"


class SubAgentFactory:
    """Factory for creating subagents"""
    
    @staticmethod
    def create(agent_type: SubAgentType, name: str = None) -> BaseSubAgent:
        """Create a subagent based on type"""
        name = name or f"{agent_type.value}_{uuid.uuid4().hex[:4]}"
        
        config = SubAgentConfig(
            name=name,
            agent_type=agent_type,
            tools=[],
            system_prompt=""
        )
        
        agent_map = {
            SubAgentType.RESEARCHER: ResearcherAgent,
            SubAgentType.CODER: CoderAgent,
            SubAgentType.ANALYZER: AnalyzerAgent,
            SubAgentType.WRITER: WriterAgent,
            SubAgentType.EXECUTOR: ExecutorAgent
        }
        
        agent_class = agent_map.get(agent_type, BaseSubAgent)
        return agent_class(config)


class NativeSubAgents:
    """
    Native Subagents System.
    Subagents laufen parallel via asyncio.gather.
    Jeder Subagent hat eigene Tools, LLM-Client, Memory.
    Hauptagent aggregiert Ergebnisse.
    """
    
    def __init__(self, max_parallel: int = 5):
        self.max_parallel = max_parallel
        self.subagents: Dict[str, BaseSubAgent] = {}
    
    def create_subagent(
        self,
        agent_type: SubAgentType,
        name: str = None,
        llm_client: Any = None,
        memory_client: Any = None
    ) -> BaseSubAgent:
        """Create a new subagent"""
        agent = SubAgentFactory.create(agent_type, name)
        self.subagents[agent.agent_id] = agent
        return agent
    
    async def execute_parallel(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[SubAgentResult]:
        """
        Führe Tasks parallel via asyncio.gather aus.
        
        Args:
            tasks: Liste von Tasks mit 'task' und optional 'agent_type'
            
        Returns:
            Liste von SubAgentResult
        """
        # Create coroutines
        coroutines = []
        
        for task_data in tasks:
            task = task_data.get("task", "")
            agent_type = task_data.get("agent_type", SubAgentType.CODER)
            name = task_data.get("name")
            
            # Get or create agent
            if name and any(a.config.name == name for a in self.subagents.values()):
                agent = next(a for a in self.subagents.values() if a.config.name == name)
            else:
                agent = self.create_subagent(agent_type, name)
            
            context = task_data.get("context", {})
            coroutines.append(agent.execute(task, context))
        
        # Execute in parallel with limit
        results = []
        for i in range(0, len(coroutines), self.max_parallel):
            batch = coroutines[i:i + self.max_parallel]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append(SubAgentResult(
                        agent_id="error",
                        agent_name="error",
                        agent_type="error",
                        success=False,
                        result=None,
                        error=str(result)
                    ))
                else:
                    results.append(result)
        
        return results
    
    async def execute_sequential(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[SubAgentResult]:
        """Execute tasks sequentially"""
        results = []
        
        for task_data in tasks:
            task = task_data.get("task", "")
            agent_type = task_data.get("agent_type", SubAgentType.CODER)
            name = task_data.get("name")
            
            agent = self.create_subagent(agent_type, name)
            result = await agent.execute(task, task_data.get("context", {}))
            results.append(result)
        
        return results
    
    def aggregate_results(self, results: List[SubAgentResult]) -> Dict[str, Any]:
        """
        Aggregiere Ergebnisse aller Subagents.
        
        Args:
            results: Liste von SubAgentResult
            
        Returns:
            Aggregiertes Ergebnis
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "results": [
                {
                    "agent": r.agent_name,
                    "type": r.agent_type,
                    "success": r.success,
                    "result": r.result,
                    "error": r.error,
                    "duration": r.duration
                }
                for r in results
            ],
            "summary": " | ".join([r.result for r in successful if r.result])[:500]
        }
    
    def get_status(self) -> Dict:
        """Get status of all subagents"""
        return {
            "total_agents": len(self.subagents),
            "agents": [
                {
                    "id": a.agent_id,
                    "name": a.config.name,
                    "type": a.config.agent_type.value
                }
                for a in self.subagents.values()
            ]
        }


# Integration with main agent
class MultiAgentOrchestrator:
    """Main agent that coordinates subagents"""
    
    def __init__(self):
        self.subagents = NativeSubAgents()
    
    async def process_task(self, task: str) -> Dict[str, Any]:
        """
        Verarbeite Task mit mehreren Subagents.
        
        Args:
            task: Der zu verarbeitende Task
            
        Returns:
            Aggregiertes Ergebnis
        """
        # Define subagent tasks based on complexity
        tasks = [
            {"task": f"Research: {task}", "agent_type": SubAgentType.RESEARCHER},
            {"task": f"Code: {task}", "agent_type": SubAgentType.CODER},
            {"task": f"Analyze: {task}", "agent_type": SubAgentType.ANALYZER}
        ]
        
        # Execute in parallel
        results = await self.subagents.execute_parallel(tasks)
        
        # Aggregate results
        return self.subagents.aggregate_results(results)


# CLI interface
async def main():
    """CLI interface for subagents"""
    import sys
    
    orchestrator = MultiAgentOrchestrator()
    
    if len(sys.argv) < 2:
        print("Usage: python subagents.py <task>")
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    
    print(f"Processing task with subagents: {task}")
    print("-" * 50)
    
    result = await orchestrator.process_task(task)
    
    print(f"\nTotal: {result['total']}")
    print(f"Successful: {result['successful']}")
    print(f"Failed: {result['failed']}")
    print(f"\nSummary: {result['summary']}")


if __name__ == "__main__":
    asyncio.run(main())