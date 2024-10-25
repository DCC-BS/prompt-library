import yaml
from dataclasses import dataclass
from typing import List

@dataclass
class LLMEndpoint:
    name: str
    url: str
    description: str
    model: str

class ConfigHandler:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.endpoints = self.load_config()
    
    def load_config(self) -> List[LLMEndpoint]:
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                return [
                    LLMEndpoint(
                        name=endpoint['name'],
                        url=endpoint['url'],
                        description=endpoint['description'],
                        model=endpoint["model"]
                    )
                    for endpoint in config['llm_endpoints']
                ]
        except Exception as e:
            print(f"Error loading config: {e}")
            return []