# Autonomous Task Planning - Tree of Thoughts Implementation
# Agent plant kompletten Baum von Aktionen, bewertet Pfade, wählt optimalen

import uuid
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Import LLM Provider (zentrale Abstraktion)
from .llm_provider import get_llm_manager, LLMProvider


class NodeStatus(Enum):
    """Status of a thought node"""
    PENDING = "pending"
    EXPANDED = "expanded"
    EVALUATED = "evaluated"
    SELECTED = "selected"
    REJECTED = "rejected"


@dataclass
class ThoughtNode:
    """Represents a single thought in the tree"""
    id: str
    content: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    score: float = 0.0
    depth: int = 0
    status: NodeStatus = NodeStatus.PENDING
    action: Optional[Dict] = None
    observation: Optional[str] = None
    reasoning: str = ""
    
    def __post_init__(self):
        self.id = self.id or str(uuid.uuid4())[:8]


class TreeOfThoughts:
    """
    Autonomous Task Planning using Tree of Thoughts approach.
    Agent plant kompletten Baum von Aktionen, bewertet Pfade, wählt optimalen.
    """
    
    def __init__(self, max_depth: int = 5, branching_factor: int = 3, max_nodes: int = 100,
                 model: str = "llama3.2", llm_manager: LLMProvider = None):
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.max_nodes = max_nodes
        self.nodes: Dict[str, ThoughtNode] = {}
        self.root_id: Optional[str] = None
        self.best_path: List[str] = []
        self.evaluation_history: List[Dict] = []
        self._llm_manager = llm_manager or get_llm_manager()
        self.model = model
    
    def reset(self):
        """Reset the tree for a new problem"""
        self.nodes = {}
        self.root_id = None
        self.best_path = []
        self.evaluation_history = []
    
    def initialize(self, problem: str) -> str:
        """Initialize tree with root problem node"""
        self.reset()
        
        root = ThoughtNode(
            id="root",
            content=problem,
            depth=0,
            status=NodeStatus.EXPANDED,
            reasoning="Initial problem statement"
        )
        self.nodes["root"] = root
        self.root_id = "root"
        
        logger.info(f"Tree initialized with problem: {problem[:50]}...")
        return "root"
    
    def generate_thoughts(self, parent_id: str, context: Dict = None) -> List[ThoughtNode]:
        """Generate child thoughts from a parent node using LLM"""
        if parent_id not in self.nodes:
            return []
        
        parent = self.nodes[parent_id]
        if parent.depth >= self.max_depth:
            return []
        
        if len(self.nodes) >= self.max_nodes:
            logger.warning("Max nodes reached")
            return []
        
        # Use LLM to generate diverse thoughts
        thoughts_content = self._llm_generate_thoughts(parent, context)
        
        thoughts = []
        for i, thought_content in enumerate(thoughts_content):
            node_id = f"{parent_id}_t{i}_{uuid.uuid4().hex[:4]}"
            
            node = ThoughtNode(
                id=node_id,
                content=thought_content,
                parent_id=parent_id,
                depth=parent.depth + 1,
                status=NodeStatus.PENDING,
                action=self._extract_action(thought_content),
                reasoning=f"Generated from {parent_id}"
            )
            
            self.nodes[node_id] = node
            parent.children.append(node_id)
            thoughts.append(node)
        
        parent.status = NodeStatus.EXPANDED
        logger.info(f"Generated {len(thoughts)} thoughts from {parent_id}")
        return thoughts
    
    def _llm_generate_thoughts(self, parent: ThoughtNode, context: Dict = None) -> List[str]:
        """Use LLM to generate diverse thought branches"""
        provider = self._llm_manager.get_provider()
        if not provider or not provider.is_available():
            # Fallback to template-based generation
            return self._template_generate_thoughts(parent)
        
        system = """You are a creative problem-solving AI. Generate 3 diverse approaches to solve the given problem.
Each approach should be different and explore a unique strategy.
Return exactly 3 lines, each starting with a number 1-3."""
        
        prompt = f"""Problem: {parent.content}

Generate 3 different approaches to solve this problem:"""
        
        response = provider.generate(prompt, system, model=self.model)
        
        thoughts = []
        for line in response.split('\n'):
            line = line.strip()
            if line and len(thoughts) < 3:
                # Remove numbering if present
                if line[0].isdigit() and '. ' in line:
                    line = line.split('. ', 1)[1]
                thoughts.append(line)
        
        # Ensure we have 3 thoughts
        while len(thoughts) < 3:
            thoughts.append(f"Alternative approach {len(thoughts) + 1}: {parent.content[:50]}...")
        
        return thoughts[:3]
    
    def _template_generate_thoughts(self, parent: ThoughtNode) -> List[str]:
        """Fallback template-based thought generation"""
        strategies = [
            f"Technical approach: Analyze and implement {parent.content[:80]}",
            f"Practical approach: Step-by-step solution for {parent.content[:80]}",
            f"Creative approach: Alternative perspective on {parent.content[:80]}"
        ]
        return strategies
    
    def _extract_action(self, thought: str) -> Optional[Dict]:
        """Extract actionable information from thought using LLM or keywords"""
        action_keywords = {
            "analyze": {"type": "analyze", "priority": 0.8},
            "implement": {"type": "implement", "priority": 1.0},
            "test": {"type": "test", "priority": 0.9},
            "optimize": {"type": "optimize", "priority": 0.7},
            "refactor": {"type": "refactor", "priority": 0.6},
            "create": {"type": "create", "priority": 1.0},
            "build": {"type": "build", "priority": 1.0},
            "fix": {"type": "fix", "priority": 0.9},
            "write": {"type": "write", "priority": 0.8}
        }
        
        thought_lower = thought.lower()
        for keyword, action in action_keywords.items():
            if keyword in thought_lower:
                return action
        
        return {"type": "think", "target": "general", "priority": 0.5}
    
    def evaluate_thought(self, node_id: str, llm_client = None) -> float:
        """Evaluate a thought node and return score using LLM"""
        if node_id not in self.nodes:
            return 0.0
        
        node = self.nodes[node_id]
        
        # Base scoring
        score = 0.0
        score += node.depth * 0.1
        
        if node.action:
            score += node.action.get("priority", 0.5) * 0.3
        
        sibling_count = len(self.nodes.get(node.parent_id, ThoughtNode("", "")).children) if node.parent_id else 0
        score += (1.0 / (sibling_count + 1)) * 0.2
        
        if node.status == NodeStatus.EXPANDED:
            score += 0.2
        
        # LLM-based evaluation
        provider = self._llm_manager.get_provider()
        if provider and provider.is_available():
            try:
                llm_score = self._llm_evaluate(node)
                score = score * 0.7 + llm_score * 0.3
            except Exception as e:
                logger.warning(f"LLM evaluation failed: {e}")
        
        node.score = score
        node.status = NodeStatus.EVALUATED
        
        self.evaluation_history.append({
            "node_id": node_id,
            "score": score,
            "timestamp": str(uuid.uuid4())
        })
        
        logger.debug(f"Node {node_id} evaluated: {score:.2f}")
        return score
    
    def _llm_evaluate(self, node: ThoughtNode) -> float:
        """Use LLM to evaluate node quality (returns 0.0-1.0)"""
        system = """You are a quality evaluator. Rate how good a solution approach is on a scale of 0.0 to 1.0.
Consider: feasibility, completeness, innovation, and clarity.
Respond with just a number between 0.0 and 1.0."""
        
        prompt = f"""Evaluate this approach: {node.content[:200]}"""
        
        provider = self._llm_manager.get_provider()
        response = provider.generate(prompt, system, model=self.model) if provider else ""
        
        try:
            # Extract number from response
            import re
            match = re.search(r'0\.\d+', response)
            if match:
                return float(match.group())
        except:
            pass
        
        return 0.5  # Default if parsing fails
    
    def reset(self):
        """Reset the tree for a new problem"""
        self.nodes = {}
        self.root_id = None
        self.best_path = []
        self.evaluation_history = []
    
    def initialize(self, problem: str) -> str:
        """Initialize tree with root problem node"""
        self.reset()
        
        root = ThoughtNode(
            id="root",
            content=problem,
            depth=0,
            status=NodeStatus.EXPANDED,
            reasoning="Initial problem statement"
        )
        self.nodes["root"] = root
        self.root_id = "root"
        
        logger.info(f"Tree initialized with problem: {problem[:50]}...")
        return "root"
    
    def generate_thoughts(self, parent_id: str, context: Dict = None) -> List[ThoughtNode]:
        """Generate child thoughts from a parent node"""
        if parent_id not in self.nodes:
            return []
        
        parent = self.nodes[parent_id]
        if parent.depth >= self.max_depth:
            return []
        
        if len(self.nodes) >= self.max_nodes:
            logger.warning("Max nodes reached")
            return []
        
        thoughts = []
        for i in range(self.branching_factor):
            node_id = f"{parent_id}_t{i}_{uuid.uuid4().hex[:4]}"
            thought_content = self._generate_thought_content(parent, i, context)
            
            node = ThoughtNode(
                id=node_id,
                content=thought_content,
                parent_id=parent_id,
                depth=parent.depth + 1,
                status=NodeStatus.PENDING,
                action=self._extract_action(thought_content),
                reasoning=f"Generated from {parent_id}"
            )
            
            self.nodes[node_id] = node
            parent.children.append(node_id)
            thoughts.append(node)
        
        parent.status = NodeStatus.EXPANDED
        logger.info(f"Generated {len(thoughts)} thoughts from {parent_id}")
        return thoughts
    
    def _generate_thought_content(self, parent: ThoughtNode, index: int, context: Dict = None) -> str:
        """Generate thought content based on parent and index"""
        strategies = [
            f"Analyze the problem from a {['technical', 'practical', 'creative'][index % 3]} perspective",
            f"Consider {['step-by-step', 'recursive', 'parallel'][index % 3]} approach",
            f"Explore {['optimization', 'simplification', 'alternative'][index % 3]} strategies"
        ]
        
        base = parent.content
        strategy = strategies[index]
        
        return f"{strategy}: {base[:100]}... (branch {index + 1})"
    
    def _extract_action(self, thought: str) -> Optional[Dict]:
        """Extract actionable information from thought"""
        action_keywords = ["analyze", "implement", "test", "optimize", "refactor", "create"]
        
        for keyword in action_keywords:
            if keyword in thought.lower():
                return {
                    "type": keyword,
                    "target": "unknown",
                    "priority": 1.0
                }
        
        return {"type": "think", "target": "general", "priority": 0.5}
    
    def evaluate_thought(self, node_id: str, llm_client = None) -> float:
        """Evaluate a thought node and return score"""
        if node_id not in self.nodes:
            return 0.0
        
        node = self.nodes[node_id]
        
        score = 0.0
        score += node.depth * 0.1
        
        if node.action:
            score += node.action.get("priority", 0.5) * 0.3
        
        sibling_count = len(self.nodes.get(node.parent_id, ThoughtNode("", "")).children) if node.parent_id else 0
        score += (1.0 / (sibling_count + 1)) * 0.2
        
        if node.status == NodeStatus.EXPANDED:
            score += 0.2
        
        if llm_client:
            try:
                llm_score = self._llm_evaluate(node, llm_client)
                score = score * 0.7 + llm_score * 0.3
            except Exception as e:
                logger.warning(f"LLM evaluation failed: {e}")
        
        node.score = score
        node.status = NodeStatus.EVALUATED
        
        self.evaluation_history.append({
            "node_id": node_id,
            "score": score,
            "timestamp": str(uuid.uuid4())
        })
        
        logger.debug(f"Node {node_id} evaluated: {score:.2f}")
        return score
    
    def _llm_evaluate(self, node: ThoughtNode, llm_client) -> float:
        """Use LLM to evaluate node quality"""
        return 0.5
    
    def search_best_path(self, start_id: str = "root") -> List[str]:
        """Search for the best path through the tree using DFS with scoring"""
        if start_id not in self.nodes:
            return []
        
        self._evaluate_all_nodes()
        
        best_path = []
        best_score = -1.0
        
        def dfs(node_id: str, current_path: List[str], current_score: float):
            nonlocal best_path, best_score
            
            if node_id not in self.nodes:
                return
            
            node = self.nodes[node_id]
            current_path.append(node_id)
            current_score += node.score
            
            if not node.children or node.depth >= self.max_depth:
                if current_score > best_score:
                    best_score = current_score
                    best_path = current_path.copy()
            else:
                for child_id in node.children:
                    dfs(child_id, current_path.copy(), current_score)
        
        dfs(start_id, [], 0.0)
        
        self.best_path = best_path
        logger.info(f"Best path found with {len(best_path)} nodes, score: {best_score:.2f}")
        return best_path
    
    def _evaluate_all_nodes(self):
        """Evaluate all pending nodes"""
        for node_id, node in self.nodes.items():
            if node.status in [NodeStatus.PENDING, NodeStatus.EXPANDED]:
                self.evaluate_thought(node_id)
    
    def get_best_node(self) -> Optional[ThoughtNode]:
        """Get the best leaf node from the best path"""
        if not self.best_path:
            return None
        
        last_node_id = self.best_path[-1]
        return self.nodes.get(last_node_id)
    
    def expand_tree(self, context: Dict = None) -> int:
        """Expand the entire tree up to max_depth"""
        expanded = 0
        queue = ["root"]
        
        while queue:
            node_id = queue.pop(0)
            if node_id not in self.nodes:
                continue
            
            node = self.nodes[node_id]
            
            if node.depth < self.max_depth and not node.children:
                children = self.generate_thoughts(node_id, context)
                expanded += len(children)
                queue.extend([c.id for c in children])
        
        return expanded
    
    def get_tree_summary(self) -> Dict:
        """Get summary of the tree state"""
        return {
            "total_nodes": len(self.nodes),
            "max_depth": max((n.depth for n in self.nodes.values()), default=0),
            "best_path_length": len(self.best_path),
            "best_path_score": sum(self.nodes[n].score for n in self.best_path) if self.best_path else 0,
            "nodes_by_status": {
                status.value: sum(1 for n in self.nodes.values() if n.status == status)
                for status in NodeStatus
            }
        }
    
    def visualize_tree(self, max_display: int = 20) -> str:
        """Generate a text visualization of the tree"""
        lines = ["Tree of Thoughts Visualization:", "=" * 40]
        
        if self.best_path:
            lines.append("\nBest Path:")
            for i, node_id in enumerate(self.best_path):
                node = self.nodes.get(node_id)
                if node:
                    indent = "  " * node.depth
                    lines.append(f"{indent}→ {node.content[:40]}... (score: {node.score:.2f})")
        
        lines.append(f"\nAll Nodes ({len(self.nodes)}):")
        for i, (node_id, node) in enumerate(list(self.nodes.items())[:max_display]):
            indent = "  " * node.depth
            marker = "✓" if node_id in self.best_path else " "
            lines.append(f"{indent}{marker} {node_id}: {node.content[:30]}... [{node.status.value}]")
        
        if len(self.nodes) > max_display:
            lines.append(f"... and {len(self.nodes) - max_display} more nodes")
        
        return "\n".join(lines)


class AutonomousPlanner:
    """High-level planner that uses Tree of Thoughts for autonomous task planning."""
    
    def __init__(self, max_depth: int = 4, branching: int = 3):
        self.tree = TreeOfThoughts(max_depth=max_depth, branching_factor=branching)
        self.current_plan: List[Dict] = []
    
    def plan(self, task: str, context: Dict = None) -> Dict:
        """Create a complete plan for the given task."""
        logger.info(f"Starting autonomous planning for: {task[:50]}...")
        
        self.tree.initialize(task)
        self.tree.expand_tree(context)
        best_path = self.tree.search_best_path()
        
        self.current_plan = []
        for node_id in best_path:
            node = self.tree.nodes.get(node_id)
            if node and node.action:
                self.current_plan.append({
                    "node_id": node_id,
                    "action": node.action,
                    "content": node.content,
                    "score": node.score
                })
        
        result = {
            "task": task,
            "plan": self.current_plan,
            "best_path": best_path,
            "tree_summary": self.tree.get_tree_summary(),
            "visualization": self.tree.visualize_tree()
        }
        
        logger.info(f"Plan created with {len(self.current_plan)} actions")
        return result
    
    def execute_plan(self) -> List[Dict]:
        """Execute the current plan (placeholder)"""
        results = []
        for step in self.current_plan:
            results.append({
                "step": step,
                "status": "pending",
                "result": None
            })
        return results
    
    def get_next_action(self) -> Optional[Dict]:
        """Get the next action to execute from the plan"""
        if not self.current_plan:
            return None
        return self.current_plan[0]


class AgentWithToT:
    """Agent that uses Tree of Thoughts for autonomous planning"""
    
    def __init__(self):
        self.planner = AutonomousPlanner(max_depth=4, branching_factor=3)
        self.current_task = None
    
    def process_message(self, message: str) -> str:
        """Process message with autonomous planning"""
        if len(message.split()) > 5:
            plan_result = self.planner.plan(message)
            response = self._generate_response_from_plan(plan_result)
            return response
        else:
            return f"Thought: {message}, Action: processing, Observation: completed"
    
    def _generate_response_from_plan(self, plan_result: Dict) -> str:
        """Generate response from plan result"""
        summary = plan_result["tree_summary"]
        actions = plan_result["plan"]
        
        response = f"Autonomous Plan Created:\n"
        response += f"- Total nodes: {summary['total_nodes']}\n"
        response += f"- Best path: {summary['best_path_length']} steps\n"
        response += f"- Plan:\n"
        
        for i, action in enumerate(actions, 1):
            response += f"  {i}. {action['action']['type']} (score: {action['score']:.2f})\n"
        
        return response


if __name__ == "__main__":
    planner = AutonomousPlanner(max_depth=3, branching_factor=2)
    task = "Implement a user authentication system with JWT tokens"
    result = planner.plan(task)
    print(result["visualization"])
    print("\nPlan:")
    for step in result["plan"]:
        print(f"  - {step['action']}")