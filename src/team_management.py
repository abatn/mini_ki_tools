# Agent Teams System - Flat Teams with Named Messaging
# Enables multiple agents to work in parallel with inter-agent communication

import uuid
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class TeamRole(Enum):
    """Team member roles"""
    LEAD = "lead"
    MEMBER = "member"
    GUEST = "guest"


@dataclass
class Teammate:
    """A team member"""
    session_id: str
    name: str
    role: TeamRole
    agent_type: str
    model: str
    status: str = "idle"
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    tasks: List[Dict] = field(default_factory=list)


@dataclass
class TeamMessage:
    """Message between team members"""
    id: str
    sender: str
    recipient: str  # "lead" or specific teammate name
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    read: bool = False


@dataclass
class Team:
    """A team of agents"""
    name: str
    lead_session_id: str
    lead_name: str
    members: List[Teammate] = field(default_factory=list)
    messages: List[TeamMessage] = field(default_factory=list)
    tasks: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    config: Dict = field(default_factory=dict)


class TeamManager:
    """Manages teams"""
    
    def __init__(self):
        self.teams: Dict[str, Team] = {}
        self.sessions: Dict[str, str] = {}  # session_id -> team_name
    
    def create_team(
        self,
        name: str,
        lead_session_id: str,
        lead_name: str,
        config: Dict = None
    ) -> Team:
        """Create a new team"""
        team = Team(
            name=name,
            lead_session_id=lead_session_id,
            lead_name=lead_name,
            config=config or {}
        )
        
        self.teams[name] = team
        self.sessions[lead_session_id] = name
        
        logger.info(f"Team created: {name}")
        return team
    
    def get_team(self, name: str) -> Optional[Team]:
        """Get team by name"""
        return self.teams.get(name)
    
    def get_team_by_session(self, session_id: str) -> Optional[Team]:
        """Get team by session ID"""
        team_name = self.sessions.get(session_id)
        return self.teams.get(team_name) if team_name else None
    
    def spawn_member(
        self,
        team_name: str,
        name: str,
        agent_type: str,
        model: str,
        session_id: str = None
    ) -> Optional[Teammate]:
        """Spawn a teammate"""
        team = self.teams.get(team_name)
        if not team:
            return None
        
        session_id = session_id or str(uuid.uuid4())
        
        member = Teammate(
            session_id=session_id,
            name=name,
            role=TeamRole.MEMBER,
            agent_type=agent_type,
            model=model
        )
        
        team.members.append(member)
        self.sessions[session_id] = team_name
        
        logger.info(f"Teammate {name} spawned in team {team_name}")
        return member
    
    def remove_member(self, team_name: str, name: str) -> bool:
        """Remove a teammate"""
        team = self.teams.get(team_name)
        if not team:
            return False
        
        member = next((m for m in team.members if m.name == name), None)
        if member:
            team.members.remove(member)
            del self.sessions[member.session_id]
            logger.info(f"Teammate {name} removed")
            return True
        
        return False
    
    def send_message(
        self,
        team_name: str,
        sender: str,
        recipient: str,
        content: str
    ) -> Optional[TeamMessage]:
        """Send message to team member"""
        team = self.teams.get(team_name)
        if not team:
            return None
        
        message = TeamMessage(
            id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            content=content
        )
        
        team.messages.append(message)
        
        logger.info(f"Message from {sender} to {recipient}")
        return message
    
    def broadcast(
        self,
        team_name: str,
        sender: str,
        content: str
    ) -> List[TeamMessage]:
        """Broadcast message to all members"""
        team = self.teams.get(team_name)
        if not team:
            return []
        
        messages = []
        for member in team.members:
            if member.name != sender:
                msg = self.send_message(team_name, sender, member.name, content)
                if msg:
                    messages.append(msg)
        
        return messages
    
    def get_messages(
        self,
        team_name: str,
        session_id: str
    ) -> List[TeamMessage]:
        """Get messages for a session"""
        team = self.teams.get(team_name)
        if not team:
            return []
        
        # Find teammate
        teammate = next(
            (m for m in team.members if m.session_id == session_id),
            None
        )
        
        if not teammate:
            # Check if lead
            if team.lead_session_id == session_id:
                return team.messages
            return []
        
        # Get messages for this teammate
        messages = [
            msg for msg in team.messages
            if msg.recipient == teammate.name or msg.recipient == "all"
        ]
        
        # Mark as read
        for msg in messages:
            msg.read = True
        
        return messages
    
    def add_task(
        self,
        team_name: str,
        task: Dict
    ) -> bool:
        """Add task to team"""
        team = self.teams.get(team_name)
        if not team:
            return False
        
        task["id"] = str(uuid.uuid4())
        task["created_at"] = datetime.now().isoformat()
        task["status"] = task.get("status", "pending")
        
        team.tasks.append(task)
        return True
    
    def assign_task(
        self,
        team_name: str,
        task_id: str,
        assignee: str
    ) -> bool:
        """Assign task to member"""
        team = self.teams.get(team_name)
        if not team:
            return False
        
        task = next((t for t in team.tasks if t.get("id") == task_id), None)
        if not task:
            return False
        
        task["assignee"] = assignee
        task["status"] = "assigned"
        return True
    
    def complete_task(
        self,
        team_name: str,
        task_id: str
    ) -> bool:
        """Mark task as complete"""
        team = self.teams.get(team_name)
        if not team:
            return False
        
        task = next((t for t in team.tasks if t.get("id") == task_id), None)
        if not task:
            return False
        
        task["status"] = "completed"
        task["completed_at"] = datetime.now().isoformat()
        return True
    
    def list_teams(self) -> List[Dict]:
        """List all teams"""
        return [
            {
                "name": t.name,
                "lead": t.lead_name,
                "members": len(t.members),
                "tasks": len(t.tasks),
                "created_at": t.created_at.isoformat()
            }
            for t in self.teams.values()
        ]
    
    def get_team_status(self, team_name: str) -> Optional[Dict]:
        """Get team status"""
        team = self.teams.get(team_name)
        if not team:
            return None
        
        return {
            "name": team.name,
            "lead": team.lead_name,
            "members": [
                {
                    "name": m.name,
                    "role": m.role.value,
                    "agent_type": m.agent_type,
                    "status": m.status,
                    "tasks": len(m.tasks)
                }
                for m in team.members
            ],
            "tasks": team.tasks,
            "messages": len(team.messages)
        }
    
    def dissolve_team(self, team_name: str) -> bool:
        """Dissolve a team"""
        if team_name in self.teams:
            del self.teams[team_name]
            logger.info(f"Team dissolved: {team_name}")
            return True
        return False


# Team tools for MCP
class TeamTools:
    """MCP tools for team operations"""
    
    def __init__(self, manager: TeamManager):
        self.manager = manager
    
    async def team_create(
        self,
        name: str,
        lead_session_id: str,
        lead_name: str,
        config: Dict = None
    ) -> Dict:
        """Create a team"""
        team = self.manager.create_team(name, lead_session_id, lead_name, config)
        return {
            "success": True,
            "team": {"name": team.name, "lead": team.lead_name}
        }
    
    async def team_spawn(
        self,
        team_name: str,
        name: str,
        agent_type: str,
        model: str
    ) -> Dict:
        """Spawn a teammate"""
        member = self.manager.spawn_member(team_name, name, agent_type, model)
        if member:
            return {
                "success": True,
                "member": {
                    "name": member.name,
                    "agent_type": member.agent_type,
                    "model": member.model
                }
            }
        return {"success": False, "error": "Team not found"}
    
    async def team_message(
        self,
        team_name: str,
        sender: str,
        recipient: str,
        content: str
    ) -> Dict:
        """Send message to member"""
        msg = self.manager.send_message(team_name, sender, recipient, content)
        if msg:
            return {"success": True, "message_id": msg.id}
        return {"success": False, "error": "Team not found"}
    
    async def team_broadcast(
        self,
        team_name: str,
        sender: str,
        content: str
    ) -> Dict:
        """Broadcast to all members"""
        messages = self.manager.broadcast(team_name, sender, content)
        return {
            "success": True,
            "message_count": len(messages)
        }
    
    async def team_tasks(
        self,
        team_name: str,
        action: str = "list",
        task: Dict = None
    ) -> Dict:
        """Manage team tasks"""
        team = self.manager.teams.get(team_name)
        if not team:
            return {"success": False, "error": "Team not found"}
        
        if action == "list":
            return {"success": True, "tasks": team.tasks}
        elif action == "add" and task:
            self.manager.add_task(team_name, task)
            return {"success": True}
        
        return {"success": False, "error": "Invalid action"}
    
    async def team_approve_plan(
        self,
        team_name: str,
        plan_id: str,
        approved: bool
    ) -> Dict:
        """Approve/reject plan"""
        return {
            "success": True,
            "approved": approved,
            "plan_id": plan_id
        }


# Global team manager
_team_manager: Optional[TeamManager] = None


def get_team_manager() -> TeamManager:
    """Get global team manager"""
    global _team_manager
    if _team_manager is None:
        _team_manager = TeamManager()
    return _team_manager


def get_team_tools() -> TeamTools:
    """Get team tools"""
    return TeamTools(get_team_manager())


# Persistence
def save_teams(path: str):
    """Save teams to disk"""
    manager = get_team_manager()
    data = {
        name: {
            "lead_session_id": t.lead_session_id,
            "lead_name": t.lead_name,
            "members": [
                {
                    "session_id": m.session_id,
                    "name": m.name,
                    "role": m.role.value,
                    "agent_type": m.agent_type,
                    "model": m.model
                }
                for m in t.members
            ],
            "tasks": t.tasks,
            "config": t.config
        }
        for name, t in manager.teams.items()
    }
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_teams(path: str):
    """Load teams from disk"""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        
        manager = get_team_manager()
        
        for name, team_data in data.items():
            manager.create_team(
                name=name,
                lead_session_id=team_data["lead_session_id"],
                lead_name=team_data["lead_name"],
                config=team_data.get("config", {})
            )
            
            for member in team_data.get("members", []):
                manager.spawn_member(
                    team_name=name,
                    name=member["name"],
                    agent_type=member["agent_type"],
                    model=member["model"],
                    session_id=member["session_id"]
                )
            
            for task in team_data.get("tasks", []):
                manager.add_task(name, task)
        
        logger.info(f"Teams loaded from {path}")
    except Exception as e:
        logger.error(f"Failed to load teams: {e}")