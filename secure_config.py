#!/usr/bin/env python3
"""Secure configuration management that doesn't store API keys in files."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class AgentConfig(BaseModel):
    model: str = Field(description="Model to use for this agent")
    temperature: float = Field(default=0.7, description="Temperature for model responses")


class CouncilConfigSecure(BaseModel):
    """Configuration without API key - keys come from environment."""
    draft_agent: AgentConfig = Field(description="Configuration for the draft agent")
    council_members: List[AgentConfig] = Field(description="Configuration for council members")
    editor_agent: AgentConfig = Field(description="Configuration for the editor agent")
    judge_agent: AgentConfig = Field(description="Configuration for the judge agent")
    debate_rounds: int = Field(default=3, ge=1, description="Number of debate rounds")


class SecureConfigManager:
    """Secure configuration manager that separates API keys from config."""
    
    def __init__(self, config_path: str = "council_config.json"):
        self.config_path = Path(config_path)
        self.config: Optional[CouncilConfigSecure] = None
        # Load environment variables from .env file if it exists
        load_dotenv()
        
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment variables."""
        return os.getenv("OPENAI_API_KEY")
    
    def load_config(self) -> Optional[CouncilConfigSecure]:
        """Load configuration from file (without API key)."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                self.config = CouncilConfigSecure(**data)
                return self.config
            except Exception as e:
                print(f"Error loading config: {e}")
                return None
        return None
    
    def save_config(self, config: CouncilConfigSecure) -> None:
        """Save configuration to file (without API key)."""
        with open(self.config_path, 'w') as f:
            json.dump(config.model_dump(), f, indent=2)
        self.config = config
    
    def config_exists(self) -> bool:
        """Check if configuration file exists."""
        return self.config_path.exists()
    
    def has_valid_setup(self) -> bool:
        """Check if we have both config file and API key."""
        return self.config_exists() and self.get_api_key() is not None
    
    def get_full_config(self) -> Optional[dict]:
        """Get full configuration including API key from environment."""
        config = self.load_config()
        api_key = self.get_api_key()
        
        if not config or not api_key:
            return None
        
        # Combine config with API key
        full_config = config.model_dump()
        full_config["openai_api_key"] = api_key
        return full_config
    
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
            ],
            "judge_agent": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo"
            ]
        }
    
    @staticmethod
    def setup_env_example():
        """Create a .env.example file with instructions."""
        env_example = Path(".env.example")
        if not env_example.exists():
            with open(env_example, 'w') as f:
                f.write("""# Echo Chamber Environment Variables
# Copy this file to .env and fill in your actual API key

# OpenAI API Key - Get this from https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Set custom model preferences
# DEFAULT_DRAFT_MODEL=gpt-4o
# DEFAULT_COUNCIL_MODEL=gpt-4o-mini
# DEFAULT_EDITOR_MODEL=gpt-4o
""")
            print("📝 Created .env.example file - copy to .env and add your API key")


def migrate_old_config():
    """Migrate from old config.json to new secure format."""
    old_config_path = Path("config.json")
    new_config_path = Path("council_config.json")
    env_path = Path(".env")
    
    if old_config_path.exists() and not new_config_path.exists():
        print("🔄 Migrating from old config format...")
        
        try:
            with open(old_config_path, 'r') as f:
                old_data = json.load(f)
            
            # Extract API key
            api_key = old_data.pop("openai_api_key", None)
            
            # Create new config without API key
            secure_config = CouncilConfigSecure(**old_data)
            manager = SecureConfigManager()
            manager.save_config(secure_config)
            
            # Create .env file if it doesn't exist and we have an API key
            if api_key and not env_path.exists():
                with open(env_path, 'w') as f:
                    f.write(f"OPENAI_API_KEY={api_key}\n")
                print("✅ API key moved to .env file")
            
            # Backup old config
            old_config_path.rename("config.json.backup")
            print("✅ Migration complete! Old config backed up to config.json.backup")
            print("⚠️  Make sure to add .env to your .gitignore file")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")


if __name__ == "__main__":
    # Run migration and setup if called directly
    migrate_old_config()
    SecureConfigManager.setup_env_example()
