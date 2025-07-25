from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field


def split_summary(text: str) -> (str, str):
    """Return main text and summary from a response."""
    if "Summary:" in text:
        main, summary = text.rsplit("Summary:", 1)
        return main.strip(), summary.strip()
    return text.strip(), ""


class AgentResponse(BaseModel):
    content: str
    agent_id: str
    agent_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent:
    def __init__(self, agent_id: str, model_name: str, temperature: float = 0.7):
        self.agent_id = agent_id
        self.agent_type = self.__class__.__name__
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature
        )
    
    async def generate_response(self, messages: List[BaseMessage]) -> AgentResponse:
        """Generate a response from the agent."""
        response = await self.llm.ainvoke(messages)
        text, summary = split_summary(response.content)
        
        # Extract token usage information
        metadata = {}
        if summary:
            metadata["summary"] = summary
        
        # Add token usage information
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            metadata["token_usage"] = {
                "input_tokens": response.usage_metadata.get('input_tokens', 0),
                "output_tokens": response.usage_metadata.get('output_tokens', 0),
                "total_tokens": response.usage_metadata.get('total_tokens', 0)
            }
        
        return AgentResponse(
            content=text,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            metadata=metadata
        )


class DraftAgent(BaseAgent):
    """Agent responsible for creating initial drafts and incorporating feedback."""
    
    def __init__(self, model_name: str, temperature: float = 0.7):
        super().__init__("draft_agent", model_name, temperature)
    
    async def create_initial_draft(self, user_query: str) -> AgentResponse:
        """Create the initial draft response to the user query."""
        messages = [
            SystemMessage(content="""You are a draft agent responsible for creating comprehensive,
            well-structured responses to user queries. Focus on clarity, accuracy, and completeness.
            Finish your reply with a single sentence summary prefixed with 'Summary:'."""),
            HumanMessage(content=user_query)
        ]
        return await self.generate_response(messages)
    
    async def update_draft(self, current_draft: str, feedback: List[str]) -> AgentResponse:
        """Update the draft based on council feedback."""
        feedback_text = "\n\n".join([f"Feedback {i+1}: {fb}" for i, fb in enumerate(feedback)])
        
        messages = [
            SystemMessage(content="""You are a draft agent. Your task is to improve your draft
            based on the feedback provided by the council members. Incorporate valid suggestions
            while maintaining the overall coherence of your response.
            Finish with a single sentence summary prefixed with 'Summary:'."""),
            HumanMessage(content=f"""Current Draft:
{current_draft}

Council Feedback:
{feedback_text}

Please provide an updated draft that addresses the feedback while maintaining quality and coherence.""")
        ]
        
        response = await self.generate_response(messages)
        response.metadata["revision"] = True
        return response


class CouncilMember(BaseAgent):
    """Council member agent that provides feedback on drafts."""
    
    def __init__(self, member_id: int, model_name: str, temperature: float = 0.7, 
                 perspective: Optional[str] = None):
        super().__init__(f"council_member_{member_id}", model_name, temperature)
        self.member_id = member_id
        self.perspective = perspective or f"Critical Reviewer {member_id}"
    
    async def provide_feedback(self, user_query: str, current_draft: str, 
                              round_number: int) -> AgentResponse:
        """Provide feedback on the current draft."""
        messages = [
            SystemMessage(content=f"""You are {self.perspective}. Your role is to critically evaluate
            the draft response and provide constructive feedback. Focus on:
            - Accuracy and factual correctness
            - Completeness and coverage of the topic
            - Clarity and organization
            - Potential improvements or missing elements

            This is round {round_number} of the review process.
            End with a one sentence summary prefixed with 'Summary:'."""),
            HumanMessage(content=f"""User Query: {user_query}

Current Draft:
{current_draft}

Please provide specific, actionable feedback to improve this response.
Finish with a one sentence summary prefixed with 'Summary:'.""")
        ]
        
        response = await self.generate_response(messages)
        response.metadata["round"] = round_number
        return response


class EditorAgent(BaseAgent):
    """Editor agent responsible for final polish and coherence."""
    
    def __init__(self, model_name: str, temperature: float = 0.3):
        super().__init__("editor_agent", model_name, temperature)
    
    async def edit_final_response(self, user_query: str, final_draft: str, 
                                 debate_history: List[Dict[str, Any]]) -> AgentResponse:
        """Create the final, polished response."""
        messages = [
            SystemMessage(content="""You are an expert editor. Your task is to take the final draft
            and ensure it is polished, coherent, and well-formatted. Make minor adjustments for:
            - Grammar and style consistency
            - Logical flow and transitions
            - Formatting and presentation
            - Overall coherence

            Do not make major content changes unless absolutely necessary for accuracy.
            Provide a one sentence summary of your edits prefixed with 'Summary:'."""),
            HumanMessage(content=f"""User Query: {user_query}

Final Draft:
{final_draft}

Please provide the polished, final version of this response.""")
        ]
        
        response = await self.generate_response(messages)
        response.metadata["final"] = True
        return response


class JudgeAgent(BaseAgent):
    """Judge agent that compares initial and final drafts."""

    def __init__(self, model_name: str, temperature: float = 0.3):
        super().__init__("judge_agent", model_name, temperature)

    async def compare_drafts(self, user_query: str, initial_draft: str,
                             final_draft: str) -> AgentResponse:
        """Provide commentary on how the drafts compare."""
        messages = [
            SystemMessage(content="""You are an impartial judge evaluating two drafts of a response. Compare the initial draft with the final draft and discuss how the final draft improved or changed. Highlight differences in clarity, accuracy and completeness. Conclude with one sentence starting with 'Summary:' summarizing your judgement."""),
            HumanMessage(content=f"""User Query: {user_query}

Initial Draft:
{initial_draft}

Final Draft:
{final_draft}

Provide your comparison and commentary.""")
        ]

        response = await self.generate_response(messages)
        response.metadata["judgement"] = True
        return response
