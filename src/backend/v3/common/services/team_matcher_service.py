"""
Team Matcher Service

Uses LLM-based semantic matching to automatically select the most appropriate
agent team based on the user's initial question.
"""

import json
import logging
from typing import List, Optional, Tuple

from common.config.app_config import config
from common.models.messages_kernel import TeamConfiguration
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from v3.config.settings import AzureConfig

logger = logging.getLogger(__name__)


class TeamMatcherService:
    """Service for matching user questions to the most appropriate agent team using LLM."""

    def __init__(self):
        """Initialize the team matcher service."""
        self.azure_config = AzureConfig()
        self.min_confidence_threshold = 0.7
        self.confidence_tie_threshold = 0.1  # If teams are within this, require manual selection

    async def _create_chat_service(self) -> AzureChatCompletion:
        """Create Azure Chat Completion service for LLM matching."""
        return await self.azure_config.create_chat_completion_service(use_reasoning_model=False)

    def _extract_team_context(self, team: TeamConfiguration) -> str:
        """
        Extract comprehensive context from a team configuration for matching.
        
        Args:
            team: TeamConfiguration object
            
        Returns:
            Formatted string containing team metadata for matching
        """
        context_parts = []
        
        # Team name and description
        context_parts.append(f"Team Name: {team.name}")
        if team.description:
            context_parts.append(f"Description: {team.description}")
        
        # Agent information
        agent_info = []
        for agent in team.agents:
            if agent.name.lower() != "proxyagent":  # Skip proxy agents
                agent_desc = f"- {agent.name}"
                if agent.description:
                    agent_desc += f": {agent.description}"
                agent_info.append(agent_desc)
        
        if agent_info:
            context_parts.append(f"Agents: {'; '.join(agent_info)}")
        
        # Starting task examples
        if team.starting_tasks:
            task_examples = []
            for task in team.starting_tasks[:3]:  # Limit to first 3 examples
                if task.prompt:
                    task_examples.append(f"- {task.prompt}")
            
            if task_examples:
                context_parts.append(f"Example Tasks:\n{chr(10).join(task_examples)}")
        
        return "\n".join(context_parts)

    async def find_best_matching_team(
        self,
        user_question: str,
        available_teams: List[TeamConfiguration],
    ) -> Tuple[Optional[str], Optional[str], float]:
        """
        Find the best matching team for a user question using LLM semantic matching.
        
        Args:
            user_question: The user's initial question/task description
            available_teams: List of available team configurations
            
        Returns:
            Tuple of (team_id, team_name, confidence_score)
            Returns (None, None, 0.0) if no good match found or multiple teams tie
        """
        if not available_teams:
            logger.warning("No teams available for matching")
            return (None, None, 0.0)
        
        if len(available_teams) == 1:
            # Only one team available, return it
            team = available_teams[0]
            logger.info(f"Only one team available, selecting: {team.name}")
            return (team.team_id, team.name, 1.0)
        
        try:
            # Build team context for LLM
            team_contexts = []
            for team in available_teams:
                context = self._extract_team_context(team)
                team_contexts.append({
                    "team_id": team.team_id,
                    "team_name": team.name,
                    "context": context
                })
            
            # Create prompt for LLM
            prompt = self._build_matching_prompt(user_question, team_contexts)
            
            # Call LLM for matching
            chat_service = await self._create_chat_service()
            execution_settings = self.azure_config.create_execution_settings()
            execution_settings.max_tokens = 2000
            execution_settings.temperature = 0.1  # Low temperature for consistent matching
            
            # Create chat history with user message
            from semantic_kernel.contents import ChatHistory
            
            chat_history = ChatHistory()
            chat_history.add_user_message(prompt)
            
            # Invoke chat completion
            response = await chat_service.get_chat_message_contents(
                chat_history=chat_history,
                settings=execution_settings
            )
            
            if not response or len(response) == 0:
                logger.error("Empty response from LLM for team matching")
                return (None, None, 0.0)
            
            # Parse LLM response
            response_text = response[0].content if hasattr(response[0], 'content') else str(response[0])
            result = self._parse_llm_response(response_text, team_contexts)
            
            if result:
                team_id, team_name, confidence = result
                
                # Check if confidence meets threshold
                if confidence >= self.min_confidence_threshold:
                    # Check for ties (multiple teams with similar confidence)
                    # This would require a second LLM call or additional logic
                    # For now, if confidence is high enough, return the match
                    logger.info(
                        f"Auto-selected team '{team_name}' (ID: {team_id}) "
                        f"with confidence {confidence:.2f} for question: {user_question[:100]}..."
                    )
                    return (team_id, team_name, confidence)
                else:
                    logger.info(
                        f"Best match confidence {confidence:.2f} below threshold "
                        f"{self.min_confidence_threshold}, requiring manual selection"
                    )
                    return (None, None, confidence)
            else:
                logger.warning("Could not parse LLM response for team matching")
                return (None, None, 0.0)
                
        except Exception as e:
            logger.error(f"Error in team matching: {e}", exc_info=True)
            return (None, None, 0.0)

    def _build_matching_prompt(
        self, user_question: str, team_contexts: List[dict]
    ) -> str:
        """Build the prompt for LLM team matching."""
        teams_section = "\n\n".join([
            f"Team {i+1}: {tc['team_name']}\n{tc['context']}"
            for i, tc in enumerate(team_contexts)
        ])
        
        prompt = f"""You are a team matching assistant. Analyze the user's question and determine which agent team is most appropriate to handle it.

User Question: "{user_question}"

Available Teams:
{teams_section}

Your task:
1. Analyze the user's question to understand the domain, intent, and requirements
2. Compare it against each team's capabilities, agents, and example tasks
3. Select the SINGLE best matching team
4. Provide a confidence score between 0.0 and 1.0

Respond ONLY with a JSON object in this exact format:
{{
    "team_id": "the-team-id",
    "team_name": "the team name",
    "confidence": 0.85,
    "reasoning": "brief explanation of why this team matches"
}}

Rules:
- Only return ONE team (the best match)
- Confidence must be between 0.0 and 1.0
- If no team is a good match (confidence < 0.7), set confidence to 0.0 and return null for team_id
- If multiple teams could work equally well, set confidence to 0.0 and return null for team_id
- Be selective - only return a team if it's clearly the best match

JSON Response:"""
        
        return prompt

    def _parse_llm_response(
        self, response_text: str, team_contexts: List[dict]
    ) -> Optional[Tuple[str, str, float]]:
        """Parse LLM response and extract team match."""
        try:
            # Try to extract JSON from response
            # LLM might wrap JSON in markdown code blocks or add extra text
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            # Try to find JSON object
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")
            
            if start_idx == -1 or end_idx == -1:
                logger.warning("No JSON object found in LLM response")
                return None
            
            json_str = response_text[start_idx:end_idx + 1]
            result = json.loads(json_str)
            
            # Validate response
            if not isinstance(result, dict):
                logger.warning("LLM response is not a dictionary")
                return None
            
            team_id = result.get("team_id")
            team_name = result.get("team_name")
            confidence = result.get("confidence", 0.0)
            
            # Validate team_id exists in available teams
            if team_id:
                valid_team_ids = {tc["team_id"] for tc in team_contexts}
                if team_id not in valid_team_ids:
                    logger.warning(f"LLM returned invalid team_id: {team_id}")
                    return None
            
            # Validate confidence is a number
            try:
                confidence = float(confidence)
                if confidence < 0.0 or confidence > 1.0:
                    logger.warning(f"Confidence out of range: {confidence}")
                    confidence = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                logger.warning(f"Invalid confidence value: {confidence}")
                return None
            
            # If confidence is 0 or team_id is null, return None
            if not team_id or confidence == 0.0:
                return (None, None, 0.0)
            
            return (team_id, team_name, confidence)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}", exc_info=True)
            return None

