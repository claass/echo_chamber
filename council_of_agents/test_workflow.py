#!/usr/bin/env python3
"""Basic tests for the Council of Agents workflow."""

import asyncio
import pytest
import os
from unittest.mock import Mock, AsyncMock
from config_manager import CouncilConfig, AgentConfig
from workflow import CouncilWorkflow
from agents import DraftAgent, CouncilMember, EditorAgent


class TestAgents:
    """Test individual agent functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        # Set a dummy API key for testing
        os.environ["OPENAI_API_KEY"] = "test-key-12345"
    
    def test_draft_agent_initialization(self):
        """Test that DraftAgent initializes correctly."""
        agent = DraftAgent("gpt-4o-mini")
        assert agent.agent_id == "draft_agent"
        assert agent.agent_type == "DraftAgent"
        assert agent.llm.model_name == "gpt-4o-mini"
    
    def test_council_member_initialization(self):
        """Test that CouncilMember initializes correctly."""
        agent = CouncilMember(1, "gpt-4o-mini", perspective="Critical Reviewer")
        assert agent.agent_id == "council_member_1"
        assert agent.agent_type == "CouncilMember"
        assert agent.perspective == "Critical Reviewer"
    
    def test_editor_agent_initialization(self):
        """Test that EditorAgent initializes correctly."""
        agent = EditorAgent("gpt-4o-mini")
        assert agent.agent_id == "editor_agent"
        assert agent.agent_type == "EditorAgent"
        assert agent.llm.temperature == 0.3  # Editor should have lower temperature


class TestCouncilWorkflow:
    """Test the council workflow."""
    
    def setup_method(self):
        """Setup test environment."""
        os.environ["OPENAI_API_KEY"] = "test-key-12345"
        
        # Create test configuration
        self.config = CouncilConfig(
            openai_api_key="test-key-12345",
            draft_agent=AgentConfig(model="gpt-4o-mini"),
            council_members=[
                AgentConfig(model="gpt-4o-mini"),
                AgentConfig(model="gpt-4o-mini")
            ],
            editor_agent=AgentConfig(model="gpt-4o-mini"),
            debate_rounds=2
        )
        
        self.workflow = CouncilWorkflow(self.config)
    
    def test_workflow_initialization(self):
        """Test that workflow initializes with correct agents."""
        assert self.workflow.draft_agent is not None
        assert len(self.workflow.council_members) == 2
        assert self.workflow.editor_agent is not None
        assert self.workflow.config.debate_rounds == 2
    
    def test_should_continue_debate(self):
        """Test the debate continuation logic."""
        state = {
            "current_round": 1,
            "max_rounds": 2
        }
        result = self.workflow.should_continue_debate(state)
        assert result == "continue"
        
        state["current_round"] = 2
        result = self.workflow.should_continue_debate(state)
        assert result == "end"
    
    def test_workflow_build(self):
        """Test that workflow builds correctly."""
        # The workflow should be compiled successfully
        assert self.workflow.workflow is not None


class TestSimpleWorkflow:
    """Test a simplified version of the workflow with mocked LLM calls."""
    
    def setup_method(self):
        """Setup test environment with mocks."""
        os.environ["OPENAI_API_KEY"] = "test-key-12345"
        
        self.config = CouncilConfig(
            openai_api_key="test-key-12345",
            draft_agent=AgentConfig(model="gpt-4o-mini"),
            council_members=[AgentConfig(model="gpt-4o-mini")],
            editor_agent=AgentConfig(model="gpt-4o-mini"),
            debate_rounds=1
        )
    
    async def test_mock_workflow_states(self):
        """Test workflow state transitions with mocked responses."""
        workflow = CouncilWorkflow(self.config)
        
        # Mock the agents to return predictable responses
        mock_draft_response = Mock()
        mock_draft_response.content = "This is a test draft response."
        mock_draft_response.agent_id = "draft_agent"
        mock_draft_response.agent_type = "DraftAgent"
        
        mock_feedback_response = Mock()
        mock_feedback_response.content = "This draft looks good but could use more detail."
        mock_feedback_response.agent_id = "council_member_0"
        mock_feedback_response.agent_type = "CouncilMember"
        
        mock_final_response = Mock()
        mock_final_response.content = "This is the final polished response."
        mock_final_response.agent_id = "editor_agent"
        mock_final_response.agent_type = "EditorAgent"
        
        # Test initial state
        initial_state = {
            "user_query": "What is AI?",
            "current_draft": "",
            "drafts": [],
            "feedback_history": [],
            "current_round": 0,
            "max_rounds": 1,
            "final_response": "",
            "ui_callback": None
        }
        
        # Test state structure
        assert "user_query" in initial_state
        assert "current_round" in initial_state
        assert "max_rounds" in initial_state
        
        # Test should_continue_debate logic
        assert workflow.should_continue_debate(initial_state) == "continue"
        
        # Test after max rounds
        initial_state["current_round"] = 1
        assert workflow.should_continue_debate(initial_state) == "end"


def run_basic_tests():
    """Run basic synchronous tests."""
    print("🧪 Running basic tests...")
    
    # Test agent initialization
    try:
        os.environ["OPENAI_API_KEY"] = "test-key-12345"
        
        # Test DraftAgent
        draft_agent = DraftAgent("gpt-4o-mini")
        assert draft_agent.agent_id == "draft_agent"
        print("✅ DraftAgent initialization test passed")
        
        # Test CouncilMember
        council_member = CouncilMember(1, "gpt-4o-mini")
        assert council_member.agent_id == "council_member_1"
        print("✅ CouncilMember initialization test passed")
        
        # Test EditorAgent
        editor_agent = EditorAgent("gpt-4o-mini")
        assert editor_agent.agent_id == "editor_agent"
        print("✅ EditorAgent initialization test passed")
        
        # Test workflow initialization
        config = CouncilConfig(
            openai_api_key="test-key-12345",
            draft_agent=AgentConfig(model="gpt-4o-mini"),
            council_members=[AgentConfig(model="gpt-4o-mini")],
            editor_agent=AgentConfig(model="gpt-4o-mini"),
            debate_rounds=1
        )
        
        workflow = CouncilWorkflow(config)
        assert workflow.draft_agent is not None
        assert len(workflow.council_members) == 1
        assert workflow.editor_agent is not None
        print("✅ Workflow initialization test passed")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def run_async_tests():
    """Run async tests."""
    print("\n🧪 Running async tests...")
    
    try:
        test_workflow = TestSimpleWorkflow()
        test_workflow.setup_method()
        await test_workflow.test_mock_workflow_states()
        print("✅ Async workflow state tests passed")
        
        print("\n🎉 All async tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting Council of Agents Tests\n")
    
    # Run basic tests
    basic_success = run_basic_tests()
    
    # Run async tests
    async_success = await run_async_tests()
    
    if basic_success and async_success:
        print("\n✅ All tests passed successfully!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)