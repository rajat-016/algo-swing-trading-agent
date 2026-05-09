from string import Template
from typing import Optional


class PromptTemplate:
    def __init__(self, name: str, template: str, version: str = "1.0.0", description: str = ""):
        self.name = name
        self.template = Template(template)
        self.version = version
        self.description = description

    def render(self, **kwargs) -> str:
        return self.template.safe_substitute(**kwargs)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "template": self.template.template,
            "version": self.version,
            "description": self.description,
        }
