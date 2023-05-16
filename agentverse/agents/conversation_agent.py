import logging
from string import Template
from typing import List, NamedTuple, Optional, Union

from agentverse.llms import BaseChatModel, BaseCompletionModel, BaseLLM
from agentverse.memory import BaseMemory
from agentverse.message import Message
from agentverse.parser import OutputParseError, OutputParser
from .base import BaseAgent


class ConversationAgent(BaseAgent):
    def step(self, env_description: str = "") -> Message:
        prompt = self._fill_prompt_template(env_description)

        parsed_response = None
        for i in range(self.max_retry):
            try:
                response = self.llm.generate_response(prompt)
                parsed_response = self.output_parser.parse(response)
                break
            except Exception as e:
                logging.error(e)
                logging.warning("Retrying...")
                continue

        if parsed_response is None:
            logging.error(f"{self.name} failed to generate valid response.")

        message = Message(
            content=""
            if parsed_response is None
            else parsed_response.return_values["output"],
            sender=self.name,
            receiver=self.get_receiver(),
        )
        return message

    async def astep(self, env_description: str = "") -> Message:
        """Asynchronous version of step"""
        prompt = self._fill_prompt_template(env_description)

        parsed_response = None
        for i in range(self.max_retry):
            try:
                response = await self.llm.agenerate_response(prompt)
                parsed_response = self.output_parser.parse(response)
                break
            except Exception as e:
                logging.error(e)
                logging.warning("Retrying...")
                continue

        if parsed_response is None:
            logging.error(f"{self.name} failed to generate valid response.")

        message = Message(
            content=""
            if parsed_response is None
            else parsed_response.return_values["output"],
            sender=self.name,
            receiver=self.get_receiver(),
        )
        return message

    def _fill_prompt_template(self, env_description: str = "") -> str:
        """Fill the placeholders in the prompt template

        In the conversation agent, three placeholders are supported:
        - ${agent_name}: the name of the agent
        - ${env_description}: the description of the environment
        - ${role_description}: the description of the role of the agent
        """
        input_arguments = {
            "agent_name": self.name,
            "env_description": env_description,
            "role_description": self.role_description,
        }
        chat_history = self.memory.to_string(add_sender_prefix=True)
        input_arguments["chat_history"] = chat_history
        return Template(self.prompt_template).safe_substitute(input_arguments)

    def add_message_to_memory(self, message: Message) -> None:
        self.memory.add_message(message)

    def reset(self) -> None:
        """Reset the agent"""
        self.memory.reset()
        # TODO: reset receiver