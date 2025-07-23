import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    model: str = Field(description="Model to use for this agent")
    temperature: float = Field(default=0.7, description="Temperature for model responses")


class CouncilConfig(BaseModel):
    openai_api_key: str = Field(description="OpenAI API key")
    draft_agent: AgentConfig = Field(description="Configuration for the draft agent")
    council_members: List[AgentConfig] = Field(description="Configuration for council members")
    editor_agent: AgentConfig = Field(description="Configuration for the editor agent")
    debate_rounds: int = Field(default=3, ge=1, description="Number of debate rounds")


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config: Optional[CouncilConfig] = None
        
    def load_config(self) -> Optional[CouncilConfig]:
        """Load configuration from file if it exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self.config = CouncilConfig(**data)
                return self.config
            except Exception as e:
                print(f"Error loading config: {e}")
                return None
        return None
    
    def save_config(self, config: CouncilConfig) -> None:
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(config.model_dump(), f, indent=2)
        self.config = config
    
    def config_exists(self) -> bool:
        """Check if configuration file exists."""
        return self.config_path.exists()
    
    @staticmethod
    def get_available_models() -> Dict[str, List[str]]:
        """Return available models for each agent type."""
        return {
            "draft_agent": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo"
            ],
            "council_member": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo"
            ],
            "editor_agent": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo"
            ]
        }