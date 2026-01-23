"""Voice agent personality template generator with business-specific instructions.

This module provides utilities for generating comprehensive personality prompts
for AI voice agents. The personality templates are optimized for:
1. OpenAI RealtimeAgent (automatic interruption detection, context management)
2. Business-specific knowledge injection from dossier data
3. Industry-tailored conversation flows and terminology
4. Professional appointment-setting behaviors

The generated prompts guide the voice agent's behavior including:
- Greeting style and tone
- How to handle common inquiries
- Appointment booking flow
- Objection handling
- Graceful fallbacks for unknown questions
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class VoicePersonalityTone(str, Enum):
    """Voice agent personality tone options."""
    PROFESSIONAL = "professional"      # Formal, business-like
    FRIENDLY = "friendly"              # Warm, approachable
    CASUAL = "casual"                  # Relaxed, conversational
    EMPATHETIC = "empathetic"          # Caring, understanding


class VoiceSpeed(str, Enum):
    """Voice agent speaking speed preferences."""
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"


@dataclass
class VoicePersonalityConfig:
    """Configuration for voice agent personality.

    Attributes:
        business_name: Name of the business.
        industry: Industry category (dentist, hvac, salon, etc.).
        tone: Overall tone of voice interactions.
        speaking_speed: Preferred speaking speed.
        use_caller_name: Whether to use caller's name if known.
        handle_after_hours: Whether to handle after-hours calls.
        enable_appointment_booking: Whether the agent can book appointments.
        enable_call_transfer: Whether the agent can transfer to a human.
        transfer_keywords: Phrases that trigger transfer to human.
        max_booking_days_ahead: How far ahead appointments can be booked.
        custom_greeting: Custom greeting override.
        custom_closing: Custom closing message override.
        services_to_highlight: Key services to mention proactively.
        special_offers: Current promotions or offers to mention.
    """
    business_name: str
    industry: str = "general"
    tone: VoicePersonalityTone = VoicePersonalityTone.FRIENDLY
    speaking_speed: VoiceSpeed = VoiceSpeed.MODERATE
    use_caller_name: bool = True
    handle_after_hours: bool = True
    enable_appointment_booking: bool = True
    enable_call_transfer: bool = True
    transfer_keywords: List[str] = field(default_factory=lambda: [
        "speak to a person",
        "talk to someone",
        "human",
        "real person",
        "manager",
        "owner",
    ])
    max_booking_days_ahead: int = 30
    custom_greeting: Optional[str] = None
    custom_closing: Optional[str] = None
    services_to_highlight: List[str] = field(default_factory=list)
    special_offers: List[str] = field(default_factory=list)


@dataclass
class BusinessContext:
    """Business context for personality generation.

    Attributes:
        name: Business name.
        address: Business address.
        phone: Business phone number.
        website: Business website URL.
        industry: Industry category.
        description: Business description.
        services: List of services offered.
        operating_hours: Operating hours by day.
        team_members: Key team member names.
        pain_points_solved: Pain points the AI receptionist solves.
        unique_selling_points: What makes this business special.
        insurance_accepted: Insurance info (for medical/dental).
        emergency_services: Whether emergency services are offered.
        booking_policy: Appointment booking policies.
    """
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    services: List[str] = field(default_factory=list)
    operating_hours: Optional[Dict[str, str]] = None
    team_members: List[str] = field(default_factory=list)
    pain_points_solved: List[str] = field(default_factory=list)
    unique_selling_points: List[str] = field(default_factory=list)
    insurance_accepted: Optional[str] = None
    emergency_services: bool = False
    booking_policy: Optional[str] = None


@dataclass
class PersonalityTemplate:
    """Complete voice agent personality template.

    Attributes:
        system_prompt: Main system prompt for the voice agent.
        greeting: Opening greeting when answering calls.
        closing: Closing message when ending calls.
        fallback_responses: Responses for unknown questions.
        transfer_message: Message when transferring to human.
        voicemail_message: Message for after-hours voicemail.
        config: Personality configuration used.
        context: Business context used.
    """
    system_prompt: str
    greeting: str
    closing: str
    fallback_responses: List[str]
    transfer_message: str
    voicemail_message: str
    config: VoicePersonalityConfig
    context: BusinessContext


# Industry-specific conversation starters and terminology
INDUSTRY_CONVERSATION_HINTS: Dict[str, Dict[str, Any]] = {
    "dentist": {
        "greeting_variant": "Thank you for calling {business_name}. This is your AI dental assistant.",
        "appointment_term": "dental appointment",
        "common_services": ["cleaning", "exam", "x-rays", "filling", "crown", "whitening", "extraction"],
        "urgency_keywords": ["tooth pain", "toothache", "emergency", "broken tooth", "swelling", "bleeding"],
        "insurance_prompt": "We accept most major dental insurance plans. Would you like me to verify your coverage?",
        "booking_notes": "Please arrive 15 minutes early for new patient paperwork.",
    },
    "hvac": {
        "greeting_variant": "Thank you for calling {business_name}. This is your AI service assistant.",
        "appointment_term": "service appointment",
        "common_services": ["AC repair", "heating repair", "maintenance", "installation", "duct cleaning", "filter replacement"],
        "urgency_keywords": ["no heat", "no cooling", "AC not working", "emergency", "gas smell", "carbon monoxide"],
        "insurance_prompt": None,
        "booking_notes": "A technician will call you 30 minutes before arrival with an estimated time.",
    },
    "salon": {
        "greeting_variant": "Thank you for calling {business_name}. This is your AI booking assistant.",
        "appointment_term": "appointment",
        "common_services": ["haircut", "color", "highlights", "styling", "blowout", "treatment", "manicure", "pedicure"],
        "urgency_keywords": [],  # Salons rarely have emergencies
        "insurance_prompt": None,
        "booking_notes": "Please arrive a few minutes early so we can discuss your style preferences.",
    },
    "auto_repair": {
        "greeting_variant": "Thank you for calling {business_name}. This is your AI service advisor.",
        "appointment_term": "service appointment",
        "common_services": ["oil change", "tire rotation", "brake service", "inspection", "diagnostics", "alignment"],
        "urgency_keywords": ["won't start", "smoke", "overheating", "check engine light", "breakdown"],
        "insurance_prompt": None,
        "booking_notes": "We'll provide a detailed estimate before beginning any work.",
    },
    "medical": {
        "greeting_variant": "Thank you for calling {business_name}. This is your AI patient coordinator.",
        "appointment_term": "appointment",
        "common_services": ["checkup", "physical", "consultation", "follow-up", "vaccination", "lab work"],
        "urgency_keywords": ["emergency", "urgent", "severe pain", "difficulty breathing", "chest pain"],
        "insurance_prompt": "We accept most major insurance plans. Please bring your insurance card to your appointment.",
        "booking_notes": "Please arrive 15 minutes early to complete any necessary paperwork.",
    },
    "legal": {
        "greeting_variant": "Thank you for calling {business_name}. This is your AI scheduling assistant.",
        "appointment_term": "consultation",
        "common_services": ["consultation", "case review", "document preparation", "representation"],
        "urgency_keywords": ["urgent", "emergency", "deadline", "court date"],
        "insurance_prompt": None,
        "booking_notes": "Please have any relevant documents ready for your consultation.",
    },
    "default": {
        "greeting_variant": "Thank you for calling {business_name}. This is your AI assistant.",
        "appointment_term": "appointment",
        "common_services": [],
        "urgency_keywords": ["emergency", "urgent", "asap"],
        "insurance_prompt": None,
        "booking_notes": "",
    },
}


def _get_industry_hints(industry: str) -> Dict[str, Any]:
    """Get industry-specific conversation hints.

    Args:
        industry: Industry category string.

    Returns:
        Dictionary of industry-specific hints and terminology.
    """
    industry_lower = (industry or "").lower().strip()

    # Direct match
    if industry_lower in INDUSTRY_CONVERSATION_HINTS:
        return INDUSTRY_CONVERSATION_HINTS[industry_lower]

    # Partial matches
    if "dent" in industry_lower:
        return INDUSTRY_CONVERSATION_HINTS["dentist"]
    if "hvac" in industry_lower or "heating" in industry_lower or "cooling" in industry_lower:
        return INDUSTRY_CONVERSATION_HINTS["hvac"]
    if "salon" in industry_lower or "hair" in industry_lower or "beauty" in industry_lower:
        return INDUSTRY_CONVERSATION_HINTS["salon"]
    if "auto" in industry_lower or "car" in industry_lower or "mechanic" in industry_lower:
        return INDUSTRY_CONVERSATION_HINTS["auto_repair"]
    if "medic" in industry_lower or "doctor" in industry_lower or "clinic" in industry_lower:
        return INDUSTRY_CONVERSATION_HINTS["medical"]
    if "law" in industry_lower or "legal" in industry_lower or "attorney" in industry_lower:
        return INDUSTRY_CONVERSATION_HINTS["legal"]

    return INDUSTRY_CONVERSATION_HINTS["default"]


def _generate_tone_instructions(tone: VoicePersonalityTone) -> str:
    """Generate tone-specific behavioral instructions.

    Args:
        tone: Desired voice personality tone.

    Returns:
        String with tone instructions for the system prompt.
    """
    tone_instructions = {
        VoicePersonalityTone.PROFESSIONAL: """
Maintain a professional, business-like demeanor at all times:
- Use formal language and avoid slang
- Be concise and efficient in your responses
- Address callers respectfully (Mr., Ms., etc. when name is known)
- Keep conversations focused on the task at hand
- Use industry-appropriate terminology
""",
        VoicePersonalityTone.FRIENDLY: """
Be warm, welcoming, and approachable:
- Use a conversational but professional tone
- Show genuine interest in helping the caller
- Use the caller's first name when appropriate
- Express enthusiasm about the business and services
- Make callers feel comfortable and valued
""",
        VoicePersonalityTone.CASUAL: """
Keep the conversation relaxed and natural:
- Use everyday language that's easy to understand
- Be personable and relatable
- It's okay to use light humor when appropriate
- Keep things simple and straightforward
- Make the caller feel like they're talking to a helpful friend
""",
        VoicePersonalityTone.EMPATHETIC: """
Show understanding and care in every interaction:
- Listen carefully and acknowledge the caller's concerns
- Use supportive and reassuring language
- Express empathy when callers describe problems
- Be patient with frustrated or upset callers
- Prioritize the caller's emotional needs alongside practical solutions
""",
    }
    return tone_instructions.get(tone, tone_instructions[VoicePersonalityTone.FRIENDLY])


def _generate_speed_instructions(speed: VoiceSpeed) -> str:
    """Generate speaking speed instructions.

    Args:
        speed: Desired speaking speed.

    Returns:
        String with speed instructions for the system prompt.
    """
    speed_instructions = {
        VoiceSpeed.SLOW: "Speak slowly and clearly, allowing extra time for the caller to process information.",
        VoiceSpeed.MODERATE: "Speak at a natural, moderate pace that is easy to follow.",
        VoiceSpeed.FAST: "Speak efficiently while remaining clear, respecting the caller's time.",
    }
    return speed_instructions.get(speed, speed_instructions[VoiceSpeed.MODERATE])


def _format_operating_hours(hours: Optional[Dict[str, str]]) -> str:
    """Format operating hours for voice agent context.

    Args:
        hours: Dictionary mapping day names to hours.

    Returns:
        Formatted hours string for the prompt.
    """
    if not hours:
        return "Operating hours are not specified. Offer to have someone call back with this information."

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    lines = []

    for day in days_order:
        if day in hours:
            lines.append(f"- {day}: {hours[day]}")

    # Handle any non-standard keys
    for day, time in hours.items():
        if day not in days_order:
            lines.append(f"- {day}: {time}")

    return "\n".join(lines) if lines else "Operating hours not available."


def _generate_greeting(
    config: VoicePersonalityConfig,
    context: BusinessContext,
    industry_hints: Dict[str, Any]
) -> str:
    """Generate the opening greeting for the voice agent.

    Args:
        config: Personality configuration.
        context: Business context.
        industry_hints: Industry-specific hints.

    Returns:
        Opening greeting string.
    """
    if config.custom_greeting:
        return config.custom_greeting

    greeting_template = industry_hints.get(
        "greeting_variant",
        "Thank you for calling {business_name}. This is your AI assistant."
    )

    greeting = greeting_template.format(business_name=context.name)
    greeting += " How may I help you today?"

    return greeting


def _generate_closing(
    config: VoicePersonalityConfig,
    context: BusinessContext
) -> str:
    """Generate the closing message for the voice agent.

    Args:
        config: Personality configuration.
        context: Business context.

    Returns:
        Closing message string.
    """
    if config.custom_closing:
        return config.custom_closing

    return f"Thank you for calling {context.name}. We look forward to seeing you! Have a great day."


def _generate_fallback_responses(context: BusinessContext) -> List[str]:
    """Generate fallback responses for unknown questions.

    Args:
        context: Business context.

    Returns:
        List of fallback response strings.
    """
    return [
        "I don't have that specific information available, but I'd be happy to have someone from our team call you back with an answer. Would that work for you?",
        f"That's a great question. Let me make a note of it so someone at {context.name} can get back to you with the details. Can I get your callback number?",
        "I want to make sure you get accurate information. Let me arrange for one of our team members to follow up with you directly.",
        f"I'm not able to answer that specific question, but I can help you schedule an appointment or take a message for the team at {context.name}.",
    ]


def _generate_transfer_message(context: BusinessContext) -> str:
    """Generate message when transferring to a human.

    Args:
        context: Business context.

    Returns:
        Transfer message string.
    """
    return f"Of course, I'll connect you with someone from our team at {context.name}. Please hold for just a moment."


def _generate_voicemail_message(
    context: BusinessContext,
    industry_hints: Dict[str, Any]
) -> str:
    """Generate after-hours voicemail message.

    Args:
        context: Business context.
        industry_hints: Industry-specific hints.

    Returns:
        Voicemail message string.
    """
    message = f"Thank you for calling {context.name}. "

    # Add emergency handling for relevant industries
    urgency_keywords = industry_hints.get("urgency_keywords", [])
    if urgency_keywords:
        message += "If this is an emergency, please describe your situation and leave your contact information, and we'll get back to you as soon as possible. "

    message += "Otherwise, please leave your name, phone number, and a brief message, and we'll return your call during our next business day."

    return message


def _build_services_section(context: BusinessContext, industry_hints: Dict[str, Any]) -> str:
    """Build the services section for the system prompt.

    Args:
        context: Business context.
        industry_hints: Industry-specific hints.

    Returns:
        Services section string.
    """
    services = context.services or industry_hints.get("common_services", [])

    if not services:
        return "Services information is not available. Offer to have someone call back with details."

    services_list = "\n".join(f"- {service}" for service in services)
    return f"""Services offered by {context.name}:
{services_list}

When asked about services:
- Confirm the service is offered
- Offer to schedule an appointment for that service
- If the service isn't listed, say you'll check with the team and call back"""


def _build_booking_section(
    config: VoicePersonalityConfig,
    context: BusinessContext,
    industry_hints: Dict[str, Any]
) -> str:
    """Build the appointment booking section.

    Args:
        config: Personality configuration.
        context: Business context.
        industry_hints: Industry-specific hints.

    Returns:
        Booking section string.
    """
    if not config.enable_appointment_booking:
        return "Appointment booking is not available through this AI assistant. Take a message and offer a callback."

    appointment_term = industry_hints.get("appointment_term", "appointment")
    booking_notes = industry_hints.get("booking_notes", "")
    policy = context.booking_policy or booking_notes

    section = f"""Appointment Booking:
You CAN schedule {appointment_term}s up to {config.max_booking_days_ahead} days in advance.

When booking an {appointment_term}:
1. Ask what service or reason for the visit
2. Ask for preferred date and time (offer alternatives if needed)
3. Collect caller's name and phone number
4. Confirm the {appointment_term} details back to them
5. Thank them and remind them of any preparation needed"""

    if policy:
        section += f"\n\nBooking policy: {policy}"

    return section


def _build_urgency_handling(
    context: BusinessContext,
    industry_hints: Dict[str, Any]
) -> str:
    """Build urgency/emergency handling instructions.

    Args:
        context: Business context.
        industry_hints: Industry-specific hints.

    Returns:
        Urgency handling section string.
    """
    urgency_keywords = industry_hints.get("urgency_keywords", [])

    if not urgency_keywords:
        return ""

    keywords_list = ", ".join(f'"{kw}"' for kw in urgency_keywords)

    section = f"""Emergency/Urgent Situations:
Listen for urgency indicators such as: {keywords_list}

When you detect urgency:
1. Express empathy and concern
2. Gather essential details about the situation
3. Collect callback number immediately
4. Assure them someone will contact them right away
5. Mark the call as urgent/priority"""

    if context.emergency_services:
        section += f"\n\n{context.name} DOES offer emergency services. Emphasize this and prioritize scheduling."

    return section


def generate_personality(
    business_data: Dict[str, Any],
    config: Optional[VoicePersonalityConfig] = None
) -> PersonalityTemplate:
    """Generate a complete voice agent personality template.

    Creates a comprehensive personality configuration for an AI voice agent
    that is customized for a specific business. The template includes:
    - System prompt with business knowledge and behavioral instructions
    - Greeting and closing messages
    - Fallback responses for unknown questions
    - Industry-specific conversation handling

    Args:
        business_data: Dictionary containing business information. Expected keys:
            - name (str): Business name (required)
            - address (str): Business address
            - phone (str): Phone number
            - website (str): Website URL
            - industry (str): Industry category
            - description (str): Business description
            - services (list): Services offered
            - operating_hours (dict): Day -> hours mapping
            - team (list): Team member names
        config: Optional personality configuration overrides.

    Returns:
        PersonalityTemplate with complete voice agent configuration.

    Example:
        >>> data = {"name": "Acme Dental", "industry": "dentist"}
        >>> template = generate_personality(data)
        >>> print(template.greeting)
    """
    # Build context from business data
    context = BusinessContext(
        name=business_data.get("name", "our business"),
        address=business_data.get("address"),
        phone=business_data.get("phone"),
        website=business_data.get("website"),
        industry=business_data.get("industry"),
        description=business_data.get("description"),
        services=business_data.get("services", []),
        operating_hours=business_data.get("operating_hours"),
        team_members=[
            m.get("name") if isinstance(m, dict) else m
            for m in business_data.get("team", [])
        ],
        unique_selling_points=business_data.get("unique_selling_points", []),
        insurance_accepted=business_data.get("insurance_accepted"),
        emergency_services=business_data.get("emergency_services", False),
        booking_policy=business_data.get("booking_policy"),
    )

    # Use provided config or create default
    if config is None:
        config = VoicePersonalityConfig(
            business_name=context.name,
            industry=context.industry or "general",
        )

    # Get industry-specific hints
    industry_hints = _get_industry_hints(config.industry)

    # Build the system prompt
    system_prompt = _build_system_prompt(config, context, industry_hints)

    # Generate other template components
    greeting = _generate_greeting(config, context, industry_hints)
    closing = _generate_closing(config, context)
    fallback_responses = _generate_fallback_responses(context)
    transfer_message = _generate_transfer_message(context)
    voicemail_message = _generate_voicemail_message(context, industry_hints)

    return PersonalityTemplate(
        system_prompt=system_prompt,
        greeting=greeting,
        closing=closing,
        fallback_responses=fallback_responses,
        transfer_message=transfer_message,
        voicemail_message=voicemail_message,
        config=config,
        context=context,
    )


def _build_system_prompt(
    config: VoicePersonalityConfig,
    context: BusinessContext,
    industry_hints: Dict[str, Any]
) -> str:
    """Build the complete system prompt for the voice agent.

    Args:
        config: Personality configuration.
        context: Business context.
        industry_hints: Industry-specific hints.

    Returns:
        Complete system prompt string.
    """
    # Build sections
    sections = []

    # Identity section
    sections.append(f"""# Voice Agent Identity

You are the AI receptionist for {context.name}.
{f'Industry: {context.industry}' if context.industry else ''}
{f'{context.description}' if context.description else ''}

Your primary goals:
1. Answer incoming calls professionally and helpfully
2. Provide accurate information about the business
3. Schedule appointments when requested
4. Take messages when you cannot directly help
5. Ensure every caller has a positive experience""")

    # Business information section
    business_info = [f"\n# Business Information\n"]
    business_info.append(f"**Business Name:** {context.name}")
    if context.address:
        business_info.append(f"**Address:** {context.address}")
    if context.phone:
        business_info.append(f"**Phone:** {context.phone}")
    if context.website:
        business_info.append(f"**Website:** {context.website}")

    if context.operating_hours:
        business_info.append(f"\n**Operating Hours:**\n{_format_operating_hours(context.operating_hours)}")

    if context.team_members:
        team_list = ", ".join(context.team_members[:5])  # Limit to first 5
        business_info.append(f"\n**Key Team Members:** {team_list}")

    sections.append("\n".join(business_info))

    # Services section
    sections.append(f"\n# Services\n\n{_build_services_section(context, industry_hints)}")

    # Tone and style section
    sections.append(f"\n# Conversation Style\n{_generate_tone_instructions(config.tone)}")
    sections.append(f"\n{_generate_speed_instructions(config.speaking_speed)}")

    # Booking section
    sections.append(f"\n# {_build_booking_section(config, context, industry_hints)}")

    # Urgency handling (if applicable)
    urgency_section = _build_urgency_handling(context, industry_hints)
    if urgency_section:
        sections.append(f"\n# {urgency_section}")

    # Insurance section (if applicable)
    insurance_prompt = industry_hints.get("insurance_prompt")
    if insurance_prompt or context.insurance_accepted:
        insurance_info = context.insurance_accepted or insurance_prompt
        sections.append(f"\n# Insurance\n{insurance_info}")

    # Transfer handling
    if config.enable_call_transfer:
        transfer_keywords = ", ".join(f'"{kw}"' for kw in config.transfer_keywords)
        sections.append(f"""
# Transferring to a Human

When callers request to speak with a person (using phrases like {transfer_keywords}):
1. Acknowledge their request politely
2. Let them know you'll connect them
3. Transfer the call

ALWAYS offer to transfer if:
- The caller seems frustrated
- You cannot answer their question after two attempts
- They have complex billing or insurance questions
- They specifically request a human""")

    # Special offers (if any)
    if config.special_offers:
        offers_list = "\n".join(f"- {offer}" for offer in config.special_offers)
        sections.append(f"""
# Current Promotions

When relevant, you may mention these current offers:
{offers_list}

Only mention promotions when they naturally fit the conversation.""")

    # Behavioral guidelines
    sections.append("""
# Behavioral Guidelines

DO:
- Listen carefully and let callers finish speaking
- Confirm understanding by summarizing what you heard
- Be patient with callers who are confused or upset
- Offer alternatives when you can't fulfill a request
- End every call on a positive note

DON'T:
- Interrupt callers mid-sentence
- Make promises you can't keep
- Provide medical, legal, or financial advice
- Share other customers' information
- Argue with callers

When you don't know something:
- Admit it honestly
- Offer to find out and call back
- Or transfer to someone who can help""")

    # Handling special situations
    sections.append("""
# Handling Difficult Situations

Angry or Frustrated Callers:
- Stay calm and professional
- Acknowledge their frustration
- Focus on finding a solution
- Offer to escalate if needed

Confused Callers:
- Speak slowly and clearly
- Ask clarifying questions
- Repeat important information
- Be patient

Prank Calls:
- Remain professional
- Politely end the call if it continues""")

    return "\n".join(sections)


def generate_personality_prompt(
    business_data: Dict[str, Any],
    include_full_context: bool = True
) -> str:
    """Generate just the system prompt string for a voice agent.

    Convenience function that returns only the system prompt string,
    useful when you just need the prompt without the full template.

    Args:
        business_data: Dictionary containing business information.
        include_full_context: Whether to include all context sections.

    Returns:
        System prompt string.

    Example:
        >>> data = {"name": "Acme Dental", "industry": "dentist"}
        >>> prompt = generate_personality_prompt(data)
        >>> print(prompt[:100])
    """
    template = generate_personality(business_data)
    return template.system_prompt


def generate_personality_from_dossier(
    dossier_content: str,
    business_name: str,
    industry: str,
    config: Optional[VoicePersonalityConfig] = None
) -> PersonalityTemplate:
    """Generate personality template with dossier content injection.

    Creates a personality template that incorporates the full research
    dossier, enabling the voice agent to answer detailed business-specific
    questions accurately.

    Args:
        dossier_content: Markdown content from the research dossier.
        business_name: Name of the business.
        industry: Industry category.
        config: Optional personality configuration.

    Returns:
        PersonalityTemplate with dossier-enhanced system prompt.
    """
    # Create basic business data
    business_data = {
        "name": business_name,
        "industry": industry,
    }

    # Generate base template
    template = generate_personality(business_data, config)

    # Inject dossier content into system prompt
    dossier_section = f"""
# Detailed Business Knowledge

The following is detailed research about {business_name}. Use this information
to answer caller questions accurately. If a question is about something not
covered here, acknowledge that you'll need to check and offer to call back.

---
{dossier_content}
---

When using this knowledge:
- Reference specific details when answering questions
- Be confident about information you have
- Admit when something isn't covered
- Never make up information not in the dossier
"""

    # Append dossier to system prompt
    enhanced_prompt = template.system_prompt + dossier_section

    # Create new template with enhanced prompt
    return PersonalityTemplate(
        system_prompt=enhanced_prompt,
        greeting=template.greeting,
        closing=template.closing,
        fallback_responses=template.fallback_responses,
        transfer_message=template.transfer_message,
        voicemail_message=template.voicemail_message,
        config=template.config,
        context=template.context,
    )


def get_available_tones() -> List[str]:
    """Get list of available personality tones.

    Returns:
        List of tone option strings.
    """
    return [tone.value for tone in VoicePersonalityTone]


def get_available_speeds() -> List[str]:
    """Get list of available speaking speeds.

    Returns:
        List of speed option strings.
    """
    return [speed.value for speed in VoiceSpeed]


def get_supported_industries() -> List[str]:
    """Get list of industries with specialized conversation hints.

    Returns:
        List of supported industry strings.
    """
    return list(INDUSTRY_CONVERSATION_HINTS.keys())
