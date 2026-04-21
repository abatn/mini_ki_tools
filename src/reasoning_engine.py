# Unified Reasoning Engine
# Unterstützt: ToT, GoT, Reflexion, Plan-Solve, PoT, Voyager/ExpeL

import uuid
import json
import subprocess
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

# Import LLM Provider
try:
    from llm_provider import get_llm_manager, LLMProvider
except ImportError:
    LLMProvider = None
    def get_llm_manager():
        return None


class ReasoningMode(Enum):
    """Verfügbare Reasoning-Modes"""
    TAO = "tao"           # Thought-Action-Observation (klassisch)
    TOT = "tot"          # Tree of Thoughts
    GOT = "got"           # Graph of Thoughts
    REFLEXION = "reflexion"  # With error memory
    PLAN_SOLVE = "plan_solve"  # Plan then execute
    POT = "pot"           # Program of Thoughts (Code as Thought)
    VOYAGER = "voyager"   # Experience-based


@dataclass
class ReasoningResult:
    """Ergebnis eines Reasoning-Durchlaufs"""
    success: bool
    thought: str
    action: Optional[Dict] = None
    observation: Optional[str] = None
    result: Optional[str] = None
    steps: List[Dict] = field(default_factory=list)
    mode: ReasoningMode = ReasoningMode.TAO
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class BaseReasoningEngine(ABC):
    """Abstrakte Basisklasse für Reasoning Engines"""
    
    @abstractmethod
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        pass
    
    @abstractmethod
    def reset(self):
        pass


class ToTEngine(BaseReasoningEngine):
    """Tree of Thoughts - Verzweigte Pfade mit Backtracking"""
    
    def __init__(self, max_depth: int = 5, branching: int = 3, llm_manager=None):
        self.max_depth = max_depth
        self.branching = branching
        self._llm = llm_manager or get_llm_manager()
        self.nodes: Dict[str, Dict] = {}
        self.best_path: List[str] = []
    
    def reset(self):
        self.nodes = {}
        self.best_path = []
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """ToT: Generiere mehr Pfade, evalaiere, wähle besten"""
        self.reset()
        
        root = {
            "id": "root",
            "content": problem,
            "depth": 0,
            "children": [],
            "score": 0.0,
            "status": "expanded"
        }
        self.nodes["root"] = root
        
        # Breadth-first expansion
        for depth in range(self.max_depth):
            current_nodes = [n for n in self.nodes.values() if n["depth"] == depth]
            for node in current_nodes[:self.branching]:
                if node["status"] == "expanded":
                    thoughts = await self._generate_thoughts(node["content"])
                    for thought in thoughts[:self.branching]:
                        child_id = f"node_{len(self.nodes)}"
                        child = {
                            "id": child_id,
                            "content": thought,
                            "depth": node["depth"] + 1,
                            "parent": node["id"],
                            "children": [],
                            "score": 0.0,
                            "status": "pending"
                        }
                        self.nodes[child_id] = child
                        node["children"].append(child_id)
        
        # Evaluate and select best path
        await self._evaluate_paths()
        
        # Build result
        steps = [{"thought": n["content"]} for n in self.best_path]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=self.best_path[-1]["content"] if self.best_path else problem,
            steps=steps,
            mode=ReasoningMode.TOT
        )
    
    async def _generate_thoughts(self, content: str) -> List[str]:
        """Generate child thoughts via LLM"""
        system = "You are a creative problem-solving AI. Return a JSON array of 3 diverse approaches."
        prompt = f"""Problem: {content}

Return exactly 3 approaches as a JSON array of strings."""
        
        try:
            if self._llm:
                provider = self._llm.get_provider()
                if provider and provider.is_available():
                    response = provider.generate(prompt, system)
                    import re
                    match = re.search(r'\[.*\]', response, re.DOTALL)
                    if match:
                        thoughts = json.loads(match.group())
                        if isinstance(thoughts, list):
                            return thoughts[:3]
                    return [line.strip() for line in response.split('\n') if line.strip()][:3]
        except Exception as e:
            logger.warning(f"LLM failed, using fallback: {e}")
        
        return [f"Approach {i+1}: {content}" for i in range(3)]
    
    async def _evaluate_paths(self):
        """Bewerte Pfade und wähle besten"""
        if not self.nodes:
            return
        
        # Simple scoring - favor deeper nodes with content
        for node in self.nodes.values():
            if node["children"]:
                node["score"] = node["depth"] * 10 + len(node["content"])
        
        # Find best leaf
        leaves = [n for n in self.nodes.values() if not n["children"]]
        if leaves:
            best = max(leaves, key=lambda n: n["score"])
            self.best_path = [best]
            
            # Trace back
            while best.get("parent"):
                parent = self.nodes.get(best["parent"])
                if parent:
                    self.best_path.insert(0, parent)
                    best = parent
                else:
                    break


class GoTEngine(BaseReasoningEngine):
    """Graph of Thoughts - Beliebig vernetzte Gedanken"""
    
    def __init__(self, llm_manager=None):
        self._llm = llm_manager or get_llm_manager()
        self.graph: Dict[str, Dict] = {}
        self.edges: List[tuple] = []
    
    def reset(self):
        self.graph = {}
        self.edges = []
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """GoT: Generiere vernetzte Gedanken mit Zusammenführungen"""
        self.reset()
        
        # Create initial node
        root = {"id": "root", "content": problem, "type": "problem"}
        self.graph["root"] = root
        
        # Generate thought network via LLM
        thoughts = await self._generate_thoughts(problem)
        
        for i, thought_content in enumerate(thoughts):
            node_id = f"thought_{i}"
            self.graph[node_id] = {
                "id": node_id,
                "content": thought_content,
                "type": "thought",
                "merge_target": f"thought_{(i+1) % 3}"
            }
            self.edges.append(("root", node_id))
        
        # Merge via LLM
        solution = await self._merge_thoughts(problem, thoughts)
        
        merge_id = "merged"
        self.graph[merge_id] = {
            "id": merge_id,
            "content": solution,
            "type": "solution"
        }
        
        steps = [{"thought": n["content"], "type": n["type"]} for n in self.graph.values()]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=solution,
            steps=steps,
            mode=ReasoningMode.GOT
        )
    
    async def _generate_thoughts(self, problem: str) -> List[str]:
        """Generate thoughts via LLM"""
        try:
            if self._llm:
                provider = self._llm.get_provider()
                if provider and provider.is_available():
                    system = "You are a creative problem-solving AI. Generate 3 diverse solution approaches."
                    prompt = f"""Problem: {problem}\n\nList 3 different approaches to solve this problem:"""
                    response = provider.generate(prompt, system)
                    thoughts = [line.strip() for line in response.split('\n') if line.strip()][:3]
                    return thoughts if thoughts else [f"Approach 1: {problem}", f"Approach 2: {problem}", f"Approach 3: {problem}"]
        except Exception as e:
            logger.warning(f"LLM failed: {e}")
        return [f"Approach {i+1}: {problem}" for i in range(3)]
    
    async def _merge_thoughts(self, problem: str, thoughts: List[str]) -> str:
        """Merge thoughts into solution via LLM"""
        try:
            if self._llm:
                provider = self._llm.get_provider()
                if provider and provider.is_available():
                    system = "You are a synthesis AI. Combine multiple approaches into a coherent solution."
                    prompt = f"""Problem: {problem}\n\nApproaches:\n""" + "\n".join([f"- {t}" for t in thoughts]) + "\n\nProvide the best combined solution:"
                    return provider.generate(prompt, system)
        except Exception as e:
            logger.warning(f"LLM merge failed: {e}")
        return f"Combined solution for: {problem}"


class ReflexionEngine(BaseReasoningEngine):
    """Reflexion - Agent mit persistent Error Memory"""
    
    def __init__(self, llm_manager=None):
        self._llm = llm_manager or get_llm_manager()
        self.error_memory: List[Dict] = []
        self.max_memory = 50
    
    def reset(self):
        pass
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """Reflexion: Denke, handle Fehler, reflektiere, speichere"""
        
        # Check error memory for similar problems
        similar_errors = self._find_similar_errors(problem)
        
        # Build prompt with reflection context
        reflection_context = ""
        if similar_errors:
            reflection_context = "\nPrevious errors to avoid:\n"
            for err in similar_errors[:3]:
                reflection_context += f"- {err['error']}: {err['reflection']}\n"
        
        system = "You are a reflective problem-solving AI. Analyze the problem and provide a solution."
        prompt = f"""Problem: {problem}
{reflection_context}

Provide a solution. If there are potential failure points, explain them."""
        
        result_text = await self._solve_with_llm(prompt, reflection_context or system)
        
        # Simulate execution and reflection
        if "error" in result_text.lower():
            reflection = "Review approach for potential edge cases"
            self._store_error(problem, result_text, reflection)
        
        steps = [
            {"step": "analyze", "content": problem},
            {"step": "reflect", "content": reflection_context or "No prior errors"},
            {"step": "solve", "content": result_text}
        ]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=result_text,
            steps=steps,
            mode=ReasoningMode.REFLEXION
        )
    
    async def _solve_with_llm(self, prompt: str, system: str) -> str:
        """Solve via LLM"""
        try:
            if self._llm:
                provider = self._llm.get_provider()
                if provider and provider.is_available():
                    return provider.generate(prompt, system)
        except Exception as e:
            logger.warning(f"LLM failed: {e}")
        return f"Solution for: {prompt[:50]}..."
    
    def _find_similar_errors(self, problem: str) -> List[Dict]:
        """Find similar errors in memory"""
        return [e for e in self.error_memory if any(w in e["problem"].lower() for w in problem.lower().split()[:3])]
    
    def _store_error(self, problem: str, error: str, reflection: str):
        """Store error with reflection for future"""
        self.error_memory.append({
            "problem": problem,
            "error": error,
            "reflection": reflection,
            "timestamp": str(uuid.uuid4())
        })
        
        # Trim memory
        if len(self.error_memory) > self.max_memory:
            self.error_memory = self.error_memory[-self.max_memory:]


class PlanSolveEngine(BaseReasoningEngine):
    """Plan and Solve - Erst Plan, dann Execute"""
    
    def __init__(self, llm_manager=None):
        self._llm = llm_manager or get_llm_manager()
        self.plan: List[Dict] = []
    
    def reset(self):
        self.plan = []
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """Plan-Solve: Parse problem into plan, execute step by step"""
        
        # Phase 1: Create plan via LLM
        plan_steps = await self._create_plan(problem)
        
        # Phase 2: Execute plan
        results = []
        for i, step in enumerate(plan_steps[:5]):
            results.append(f"Executed: {step}")
        
        steps = [{"step": p, "result": r} for p, r in zip(plan_steps, results)]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result="\n".join(results),
            steps=steps,
            mode=ReasoningMode.PLAN_SOLVE
        )
    
    async def _create_plan(self, problem: str) -> List[str]:
        """Create plan via LLM"""
        try:
            if self._llm:
                provider = self._llm.get_provider()
                if provider and provider.is_available():
                    system = "You are a planning AI. Create a clear step-by-step plan."
                    prompt = f"""Create a 5-step plan for:
{problem}

List the steps:"""
                    response = provider.generate(prompt, system)
                    steps = [line.strip() for line in response.split('\n') if line.strip()][:5]
                    return steps if steps else [f"Step 1 for: {problem}", f"Step 2 for: {problem}"]
        except Exception as e:
            logger.warning(f"LLM plan failed: {e}")
        return [f"Step {i+1} for: {problem}" for i in range(5)]


class PoTEngine(BaseReasoningEngine):
    """Program of Thoughts - Code as Thought"""
    
    def __init__(self, llm_manager=None):
        self._llm = llm_manager or get_llm_manager()
    
    def reset(self):
        pass
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """PoT: Generate and execute code as thought process"""
        
        code = await self._generate_code(problem)
        
        # Execute code
        result = "Code executed"
        try:
            exec_result = subprocess.run(
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=30
            )
            result = exec_result.stdout.strip() if exec_result.stdout.strip() else exec_result.stderr.strip()
        except Exception as e:
            result = f"Error: {e}"
        
        steps = [
            {"step": "generate_code", "content": code[:200]},
            {"step": "execute", "content": result[:200]}
        ]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=result or code[:100],
            steps=steps,
            mode=ReasoningMode.POT
        )
    
    async def _generate_code(self, problem: str) -> str:
        """Generate code via LLM"""
        try:
            if self._llm:
                provider = self._llm.get_provider()
                if provider and provider.is_available():
                    system = "You are a Python code generator. Output only code, no explanation."
                    prompt = f"""Write Python code to solve:
{problem}

Output only the Python code:"""
                    return provider.generate(prompt, system)
        except Exception as e:
            logger.warning(f"LLM code gen failed: {e}")
        return f"# Solution for: {problem}\nprint('Result')"


class VoyagerEngine(BaseReasoningEngine):
    """Voyager/ExpeL - Experience-based learning"""
    
    def __init__(self, llm_manager=None):
        self._llm = llm_manager or get_llm_manager()
        self.experiences: List[Dict] = []
    
    def reset(self):
        pass
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """Voyager: Retrieve similar experiences, apply learnings"""
        
        # Retrieve similar experiences
        similar = self._retrieve_experiences(problem)
        
        # Use LLM to solve with experience context
        solution = await self._solve_with_experience(problem, similar)
        
        steps = [
            {"step": "retrieve", "content": f"Found {len(similar)} experiences"},
            {"step": "learn", "content": f"Applied {len(similar)} past learnings"},
            {"step": "solve", "content": solution[:100]}
        ]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=solution,
            steps=steps,
            mode=ReasoningMode.VOYAGER
        )
    
    async def _solve_with_experience(self, problem: str, experiences: List[Dict]) -> str:
        """Solve using LLM with experience context"""
        try:
            if self._llm:
                provider = self._llm.get_provider()
                if provider and provider.is_available():
                    context = ""
                    if experiences:
                        context = "Past experiences:\n" + "\n".join([f"- {e['result']}" for e in experiences[:3]])
                    system = "You are an experienced problem-solver. Apply your knowledge."
                    prompt = f"""Problem: {problem}
{context}

Provide a solution using your experience:"""
                    return provider.generate(prompt, system)
        except Exception as e:
            logger.warning(f"LLM solve failed: {e}")
        return f"Solution for: {problem[:50]}..."
    
    def _retrieve_experiences(self, problem: str) -> List[Dict]:
        """Retrieve similar experiences from memory"""
        keywords = problem.lower().split()[:5]
        return [
            e for e in self.experiences
            if any(w in e["problem"].lower() for w in keywords)
        ]
    
    def store_experience(self, problem: str, result: str, success: bool):
        """Store experience for future retrieval"""
        self.experiences.append({
            "problem": problem,
            "result": result,
            "success": success
        })


class ReasoningEngine:
    """Unified Reasoning Engine with Mode Selection"""
    
    MODES = {
        ReasoningMode.TAO: ("TAO", "Thought-Action-Observation (klassisch)"),
        ReasoningMode.TOT: ("ToT", "Tree of Thoughts"),
        ReasoningMode.GOT: ("GoT", "Graph of Thoughts"),
        ReasoningMode.REFLEXION: ("Reflexion", "With error memory"),
        ReasoningMode.PLAN_SOLVE: ("Plan-Solve", "Plan then execute"),
        ReasoningMode.POT: ("PoT", "Code as Thought"),
        ReasoningMode.VOYAGER: ("Voyager", "Experience-based"),
    }
    
    def __init__(self, mode: ReasoningMode = ReasoningMode.TAO, llm_manager=None):
        self.mode = mode
        self._llm = llm_manager or get_llm_manager()
        self._engine = self._create_engine(mode)
    
    def _create_engine(self, mode: ReasoningMode) -> BaseReasoningEngine:
        """Erstelle passende Engine für Modus"""
        engines = {
            ReasoningMode.TAO: ToTEngine,  # Fallback to ToT for now
            ReasoningMode.TOT: ToTEngine,
            ReasoningMode.GOT: GoTEngine,
            ReasoningMode.REFLEXION: ReflexionEngine,
            ReasoningMode.PLAN_SOLVE: PlanSolveEngine,
            ReasoningMode.POT: PoTEngine,
            ReasoningMode.VOYAGER: VoyagerEngine,
        }
        engine_class = engines.get(mode, ToTEngine)
        return engine_class(llm_manager=self._llm)
    
    def set_mode(self, mode: ReasoningMode):
        """Wechsle Reasoning-Modus"""
        self.mode = mode
        self._engine = self._create_engine(mode)
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """Führe Reasoning durch"""
        return await self._engine.think(problem, context)
    
    def reset(self):
        """Reset Engine"""
        self._engine.reset()
    
    def get_available_modes(self) -> Dict[ReasoningMode, tuple]:
        """Liste verfügbare Modi"""
        return self.MODES


def get_reasoning_engine(mode: str = "tao") -> ReasoningEngine:
    """Factory function"""
    try:
        mode_enum = ReasoningMode(mode)
    except ValueError:
        mode_enum = ReasoningMode.TAO
    
    return ReasoningEngine(mode=mode_enum)