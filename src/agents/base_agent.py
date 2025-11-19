"""Base agent class for all agents in the application."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, name: str = "base_agent"):
        """
        Initialize the base agent.
        
        Args:
            name: Name of the agent
        """
        self.name = name
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and return output.
        
        Args:
            input_data: Input data for processing
            
        Returns:
            Processed output
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"