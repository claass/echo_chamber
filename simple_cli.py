#!/usr/bin/env python3
"""Simple CLI interface for Echo Chamber."""

import asyncio
import os
import sys
from typing import Optional
import getpass
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.table import Table

from config_manager import CouncilConfig, AgentConfig
from secure_config import SecureConfigManager, CouncilConfigSecure, migrate_old_config
from workflow import CouncilWorkflow


def split_summary(text: str) -> (str, str):
    """Return main text and summary from a response."""
    if "Summary:" in text:
        main, summary = text.rsplit("Summary:", 1)
        return main.strip(), summary.strip()
    return text.strip(), ""


class SimpleCouncilCLI:
    def __init__(self):
        self.console = Console()
        self.config_manager = SecureConfigManager()
        self.workflow: Optional[CouncilWorkflow] = None
        self.config: Optional[CouncilConfig] = None
        self.progress = None
        self.progress_task = None
    
    def print_banner(self):
        """Print the application banner."""
        banner = Panel.fit(
            "🤖 [bold cyan]Echo Chamber[/bold cyan]\n"
            "Multi-agent collaborative AI system",
            style="bold blue"
        )
        self.console.print(banner)
        self.console.print()
    
    async def setup_configuration(self) -> bool:
        """Setup configuration interactively."""
        # First, try to migrate old config if it exists
        migrate_old_config()
        
        # Check if we have a complete setup
        if self.config_manager.has_valid_setup():
            full_config_data = self.config_manager.get_full_config()
            if full_config_data:
                # Set environment variable
                os.environ["OPENAI_API_KEY"] = full_config_data["openai_api_key"]
                # Create CouncilConfig object for compatibility
                self.config = CouncilConfig(**full_config_data)
                self.console.print("✅ [green]Configuration loaded successfully[/green]")
                return True
        
        # Check what's missing
        has_config = self.config_manager.config_exists()
        has_api_key = self.config_manager.get_api_key() is not None
        
        if not has_api_key:
            self.console.print("🔑 [yellow]API key not found in environment[/yellow]")
            self.console.print("💡 You can either:")
            self.console.print("  1. Set OPENAI_API_KEY environment variable")
            self.console.print("  2. Create a .env file with OPENAI_API_KEY=your_key")
            self.console.print("  3. Enter it now (will be stored in .env)")
            self.console.print()
        
        if not has_config:
            self.console.print("⚙️ [yellow]Configuration file not found[/yellow]")
        
        self.console.print("🔧 [yellow]Setup required[/yellow]")
        self.console.print()
        
        # Get API key if we don't have one
        api_key = self.config_manager.get_api_key()
        if not api_key:
            api_key = getpass.getpass("Enter your OpenAI API key: ")
            if not api_key:
                self.console.print("❌ [red]API key is required![/red]")
                return False
            
            # Save to .env file
            from pathlib import Path
            env_path = Path(".env")
            with open(env_path, 'w') as f:
                f.write(f"OPENAI_API_KEY={api_key}\n")
            self.console.print("💾 [green]API key saved to .env file[/green]")
        
        os.environ["OPENAI_API_KEY"] = api_key
        
        # Get available models
        available_models = SecureConfigManager.get_available_models()
        
        # Configure Draft Agent
        self.console.print("\n--- Draft Agent Configuration ---")
        draft_model = Prompt.ask(
            "Select model for Draft Agent",
            choices=available_models["draft_agent"],
            default="gpt-4o"
        )
        
        # Configure Council Members
        self.console.print("\n--- Council Configuration ---")
        num_council = Prompt.ask("Number of council members", choices=["2", "3", "4", "5"], default="3")
        num_council = int(num_council)
        
        council_members = []
        for i in range(num_council):
            member_model = Prompt.ask(
                f"Model for Council Member {i+1}",
                choices=available_models["council_member"],
                default="gpt-4o-mini"
            )
            council_members.append(AgentConfig(model=member_model))
        
        # Configure Editor Agent
        self.console.print("\n--- Editor Agent Configuration ---")
        editor_model = Prompt.ask(
            "Select model for Editor Agent",
            choices=available_models["editor_agent"],
            default="gpt-4o"
        )
        
        # Configure Debate Rounds
        self.console.print("\n--- Debate Configuration ---")
        debate_rounds = Prompt.ask("Number of debate rounds", choices=["1", "2", "3", "4", "5"], default="3")
        debate_rounds = int(debate_rounds)
        
        # Create and save secure configuration (without API key)
        secure_config = CouncilConfigSecure(
            draft_agent=AgentConfig(model=draft_model),
            council_members=council_members,
            editor_agent=AgentConfig(model=editor_model),
            debate_rounds=debate_rounds
        )
        
        self.config_manager.save_config(secure_config)
        
        # Create full config for workflow (with API key)
        self.config = CouncilConfig(
            openai_api_key=api_key,
            draft_agent=AgentConfig(model=draft_model),
            council_members=council_members,
            editor_agent=AgentConfig(model=editor_model),
            debate_rounds=debate_rounds
        )
        
        self.console.print("\n✅ [green]Configuration saved successfully![/green]")
        return True
    
    def show_config_summary(self):
        """Show current configuration."""
        if not self.config:
            return
        
        table = Table(title="Council Configuration")
        table.add_column("Component", style="cyan")
        table.add_column("Model", style="green")
        
        table.add_row("Draft Agent", self.config.draft_agent.model)
        
        for i, member in enumerate(self.config.council_members):
            table.add_row(f"Council Member {i+1}", member.model)
        
        table.add_row("Editor Agent", self.config.editor_agent.model)
        table.add_row("Debate Rounds", str(self.config.debate_rounds))
        
        self.console.print(table)
        self.console.print()
    
    async def process_query(self, query: str):
        """Process a query through the council workflow."""
        if not self.workflow:
            self.workflow = CouncilWorkflow(self.config, ui_callback=self.handle_workflow_event)
        
        self.console.print(f"\n🔍 [cyan]Query:[/cyan] {query}")
        self.console.print()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Processing...", total=None)
            self.progress = progress
            self.progress_task = task
            
            try:
                final_response = await self.workflow.run(query)

                progress.update(task, description="Complete!")
                progress.stop()
                
                # Show final response
                self.console.print("\n" + "="*80)
                self.console.print("🎉 [bold green]Final Response[/bold green]")
                self.console.print("="*80)
                self.console.print()
                self.console.print(Markdown(final_response))
                self.console.print()
                
                # Save response
                with open("council_response.txt", "w") as f:
                    f.write(f"Query: {query}\n\n")
                    f.write(f"Final Response:\n{final_response}\n")
                
                self.console.print("💾 [dim]Response saved to council_response.txt[/dim]")
                
            except Exception as e:
                progress.stop()
                self.console.print(f"\n❌ [red]Error: {str(e)}[/red]")
            finally:
                self.progress = None
                self.progress_task = None
    
    async def handle_workflow_event(self, event_type: str, data):
        """Handle workflow events for progress updates."""
        if event_type == "status":
            if self.progress and self.progress_task is not None:
                self.progress.update(self.progress_task, description=str(data))
        elif event_type == "draft_created":
            summary = data.metadata.get("summary", "")
            if summary:
                self.console.print(f"✅ [green]Draft Created:[/green] {summary}")
            else:
                self.console.print("✅ [green]Initial draft created[/green]")
        elif event_type == "feedback_round":
            self.console.print(f"💬 [blue]Debate round {data['round']} summaries:[/blue]")
            for fb in data['feedback']:
                summary = fb.get('summary', '')
                if summary:
                    self.console.print(f"  • {fb['agent_id']}: {summary}")
        elif event_type == "draft_updated":
            summary = data.metadata.get("summary", "")
            if summary:
                self.console.print(f"✏️ [yellow]Draft Updated:[/yellow] {summary}")
            else:
                self.console.print("✏️ [yellow]Draft updated based on feedback[/yellow]")
        elif event_type == "final_response":
            summary = data.metadata.get("summary", "")
            if summary:
                self.console.print(f"🎯 [green]Final Summary:[/green] {summary}")
            else:
                self.console.print("🎯 [green]Final response ready[/green]")
    
    def show_example_prompts(self):
        """Show example prompts users can try."""
        self.console.print("💡 [yellow]Example prompts to try:[/yellow]")
        examples = [
            "Explain quantum computing in simple terms",
            "Write a short story about a robot discovering emotions",
            "Design a sustainable urban transportation system",
            "Create a lesson plan for teaching the water cycle",
            "Analyze pros and cons of remote work"
        ]
        
        for i, example in enumerate(examples, 1):
            self.console.print(f"  {i}. {example}")
        self.console.print()
    
    async def run(self):
        """Main CLI loop."""
        self.print_banner()
        
        # Setup configuration
        if not await self.setup_configuration():
            return
        
        self.console.print()
        self.show_config_summary()
        self.show_example_prompts()
        
        # Main interaction loop
        while True:
            try:
                self.console.print("─" * 80)
                query = Prompt.ask("\n🤖 [bold cyan]Enter your query[/bold cyan] (or 'quit' to exit)")
                
                if query.lower() in ['quit', 'exit', 'q']:
                    self.console.print("\n👋 [yellow]Goodbye![/yellow]")
                    break
                
                if query.strip():
                    await self.process_query(query.strip())
                    
                    # Ask if they want to continue
                    self.console.print()
                    if not Confirm.ask("Would you like to ask another question?", default=True):
                        self.console.print("\n👋 [yellow]Goodbye![/yellow]")
                        break
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 [yellow]Goodbye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"\n❌ [red]Unexpected error: {str(e)}[/red]")


async def main():
    """Main entry point."""
    cli = SimpleCouncilCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())