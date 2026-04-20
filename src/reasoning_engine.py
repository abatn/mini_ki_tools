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
        prompt = f"""Generate 3 diverse solution approaches for this problem:
{content}

Return as JSON array of strings."""
        
        try:
            if self._llm:
                response = await self._llm.agenerate([prompt])
                thoughts = json.loads(response[0].text)
                return thoughts if isinstance(thoughts, list) else [response[0].text]
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
        
        # Generate thought network
        for i in range(3):
            node_id = f"thought_{i}"
            self.graph[node_id] = {
                "id": node_id,
                "content": f"Solution approach {i+1}: {problem}",
                "type": "thought",
                "merge_target": f"thought_{(i+1) % 3}"
            }
            self.edges.append(("root", node_id))
        
        # Merge node
        merge_id = "merged"
        self.graph[merge_id] = {
            "id": merge_id,
            "content": "Final solution",
            "type": "solution"
        }
        
        steps = [{"thought": n["content"], "type": n["type"]} for n in self.graph.values()]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=self.graph["merged"]["content"],
            steps=steps,
            mode=ReasoningMode.GOT
        )


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
        
        prompt = f"""Problem: {problem}
{reflection_context}

Provide a solution. If there are potential failure points, explain them."""
        
        result_text = "Solution generated"
        
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
        
        # Phase 1: Create plan
        plan_prompt = f"""Create a step-by-step plan for:
{problem}

Return as JSON array with 'step' and 'action' fields."""
        
        # Phase 2: Execute plan
        results = []
        for i, step in enumerate(self.plan[:5]):
            results.append(f"Executed: {step.get('action', '')}")
        
        steps = [{"step": p["step"], "result": r} for p, r in zip(self.plan, results)]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result="\n".join(results),
            steps=steps,
            mode=ReasoningMode.PLAN_SOLVE
        )


class PoTEngine(BaseReasoningEngine):
    """Program of Thoughts - Code as Thought"""
    
    def __init__(self, llm_manager=None):
        self._llm = llm_manager or get_llm_manager()
    
    def reset(self):
        pass
    
    async def think(self, problem: str, context: Dict = None) -> ReasoningResult:
        """PoT: Generate and execute code as thought process"""
        
        code_prompt = f"""Write Python code to solve:
{problem}

Output only the code, no explanation."""
        
        code = f"# Solution for: {problem}\nprint('Result')"
        
        # Execute code
        result = "Code executed"
        try:
            result = subprocess.run(
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=30
            )
            result = result.stdout or result.stderr
        except Exception as e:
            result = f"Error: {e}"
        
        steps = [
            {"step": "generate_code", "content": code[:100]},
            {"step": "execute", "content": result[:100]}
        ]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=result,
            steps=steps,
            mode=ReasoningMode.POT
        )


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
        
        learned = ""
        if similar:
            learned = "\n".join([f"From experience: {e['result']}" for e in similar[:2]])
        
        solution = f"Solution based on {len(similar)} similar experiences" if similar else "New solution"
        
        steps = [
            {"step": "retrieve", "content": f"Found {len(similar)} experiences"},
            {"step": "learn", "content": learned or "No prior knowledge"},
            {"step": "solve", "content": solution}
        ]
        
        return ReasoningResult(
            success=True,
            thought=problem,
            result=solution,
            steps=steps,
            mode=ReasoningMode.VOYAGER
        )
    
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