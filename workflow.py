from typing import Dict, List, Any, TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from agents import DraftAgent, CouncilMember, EditorAgent, AgentResponse
from config_manager import CouncilConfig
import asyncio
import operator


class CouncilState(TypedDict):
    user_query: str
    current_draft: str
    drafts: Annotated[List[str], operator.add]
    feedback_history: Annotated[List[List[Dict[str, str]]], operator.add]
    current_round: int
    max_rounds: int
    final_response: str
    ui_callback: Any


class CouncilWorkflow:
    def __init__(self, config: CouncilConfig, ui_callback=None):
        self.config = config
        self.ui_callback = ui_callback
        
        # Initialize agents
        self.draft_agent = DraftAgent(
            model_name=config.draft_agent.model,
            temperature=config.draft_agent.temperature
        )
        
        self.council_members = [
            CouncilMember(
                member_id=i,
                model_name=agent_config.model,
                temperature=agent_config.temperature,
                perspective=f"Council Member {i+1}"
            )
            for i, agent_config in enumerate(config.council_members)
        ]
        
        self.editor_agent = EditorAgent(
            model_name=config.editor_agent.model,
            temperature=config.editor_agent.temperature
        )
        
        # Build the workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(CouncilState)
        
        # Add nodes
        workflow.add_node("create_draft", self.create_initial_draft)
        workflow.add_node("council_debate", self.council_debate)
        workflow.add_node("update_draft", self.update_draft)
        workflow.add_node("final_edit", self.final_edit)
        
        # Add edges
        workflow.add_edge(START, "create_draft")
        workflow.add_edge("create_draft", "council_debate")
        
        # Conditional edge for debate rounds
        workflow.add_conditional_edges(
            "council_debate",
            self.should_continue_debate,
            {
                "continue": "update_draft",
                "end": "final_edit"
            }
        )
        
        workflow.add_edge("update_draft", "council_debate")
        workflow.add_edge("final_edit", END)
        
        return workflow.compile()
    
    async def create_initial_draft(self, state: CouncilState) -> Dict[str, Any]:
        """Create the initial draft."""
        if self.ui_callback:
            await self.ui_callback("status", "Creating initial draft...")
        
        response = await self.draft_agent.create_initial_draft(state["user_query"])
        
        if self.ui_callback:
            await self.ui_callback("draft_created", response)
        
        return {
            "current_draft": response.content,
            "drafts": [response.content],
            "current_round": 0
        }
    
    async def council_debate(self, state: CouncilState) -> Dict[str, Any]:
        """Council members provide feedback on the current draft."""
        current_round = state["current_round"] + 1
        
        if self.ui_callback:
            await self.ui_callback("status", f"Council debate round {current_round}...")
        
        # Gather feedback from all council members concurrently
        feedback_tasks = [
            member.provide_feedback(
                user_query=state["user_query"],
                current_draft=state["current_draft"],
                round_number=current_round
            )
            for member in self.council_members
        ]
        
        feedback_responses = await asyncio.gather(*feedback_tasks)
        
        # Store feedback
        round_feedback = [
            {
                "agent_id": response.agent_id,
                "feedback": response.content
            }
            for response in feedback_responses
        ]
        
        if self.ui_callback:
            await self.ui_callback("feedback_round", {
                "round": current_round,
                "feedback": round_feedback
            })
        
        return {
            "current_round": current_round,
            "feedback_history": [round_feedback]
        }
    
    async def update_draft(self, state: CouncilState) -> Dict[str, Any]:
        """Update the draft based on council feedback."""
        if self.ui_callback:
            await self.ui_callback("status", "Updating draft based on feedback...")
        
        # Get the latest round of feedback
        latest_feedback = state["feedback_history"][-1]
        feedback_texts = [fb["feedback"] for fb in latest_feedback]
        
        response = await self.draft_agent.update_draft(
            current_draft=state["current_draft"],
            feedback=feedback_texts
        )
        
        if self.ui_callback:
            await self.ui_callback("draft_updated", response)
        
        return {
            "current_draft": response.content,
            "drafts": [response.content]
        }
    
    async def final_edit(self, state: CouncilState) -> Dict[str, Any]:
        """Final editing pass by the editor agent."""
        if self.ui_callback:
            await self.ui_callback("status", "Performing final edit...")
        
        response = await self.editor_agent.edit_final_response(
            user_query=state["user_query"],
            final_draft=state["current_draft"],
            debate_history=state.get("feedback_history", [])
        )
        
        if self.ui_callback:
            await self.ui_callback("final_response", response)
        
        return {"final_response": response.content}
    
    def should_continue_debate(self, state: CouncilState) -> Literal["continue", "end"]:
        """Determine whether to continue the debate or proceed to final edit."""
        if state["current_round"] >= state["max_rounds"]:
            return "end"
        return "continue"
    
    async def run(self, user_query: str) -> str:
        """Run the council workflow and return the final response."""
        initial_state = {
            "user_query": user_query,
            "current_draft": "",
            "drafts": [],
            "feedback_history": [],
            "current_round": 0,
            "max_rounds": self.config.debate_rounds,
            "final_response": "",
            "ui_callback": self.ui_callback
        }
        
        final_state = await self.workflow.ainvoke(initial_state)
        return final_state["final_response"]