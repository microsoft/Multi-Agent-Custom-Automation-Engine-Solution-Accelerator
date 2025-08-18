"""
Enhanced response callbacks for employee onboarding agent system.
Provides detailed monitoring and response handling for different agent types.
"""

import sys
from semantic_kernel.contents import ChatMessageContent, StreamingChatMessageContent

def enhanced_agent_response_callback(message: ChatMessageContent) -> None:
    """Enhanced callback to monitor agent responses with detailed information."""
    
    # Get basic message information
    message_type = type(message).__name__
    role = getattr(message, 'role', 'unknown')
    metadata = getattr(message, 'metadata', {})
    agent_name = message.name or "Unknown Agent"
    
    # Handle different agent types with specific formatting
    if "Coder" in agent_name:
        _handle_coder_response(message, agent_name, message_type)
    elif "Reasoning" in agent_name:
        _handle_reasoning_response(message, agent_name, message_type, role)
    elif "Research" in agent_name or "Enhanced" in agent_name:
        _handle_research_response(message, agent_name, message_type, role, metadata)
    else:
        _handle_default_response(message, agent_name, message_type, role)

def _handle_coder_response(message, agent_name, message_type):
    """Handle coder agent responses with code execution details."""
    if hasattr(message, 'items') and message.items and len(message.items) > 0:
        for item in message.items:
            if hasattr(item, 'text') and item.text:
                print(item.text, end='', flush=True)
    
    content = message.content or ""
    if content.strip():
        print(content, end='', flush=True)

def _handle_reasoning_response(message, agent_name, message_type, role):
    """Handle reasoning agent responses with logical process details."""
    print(f"\n🧠 **{agent_name}** [{message_type}] (role: {role})")
    print("-" * (len(agent_name) + len(message_type) + 15))
    
    if hasattr(message, 'items') and message.items:
        for item in message.items:
            if hasattr(item, 'function_name') and item.function_name:
                print(f"🔧 Function Call: {item.function_name}")
            if hasattr(item, 'text') and item.text:
                print(item.text, end='', flush=True)
    
    content = message.content or ""
    if content.strip():
        print(f"💭 Reasoning: {content}")
    
    sys.stdout.flush()
    print()

def _handle_research_response(message, agent_name, message_type, role, metadata):
    """Handle research agent responses with search result details."""
    print(f"\n🔍 **{agent_name}** [{message_type}] (role: {role})")
    print("-" * (len(agent_name) + len(message_type) + 15))
    
    if metadata:
        print(f"📋 Metadata: {metadata}")
    
    # Show detailed search results if available
    if hasattr(message, 'items') and message.items and len(message.items) > 0:
        print(f"🔧 Found {len(message.items)} items in message")
        
        for i, item in enumerate(message.items):
            print(f"   Item {i+1}:")
            
            if hasattr(item, 'function_name'):
                print(f"      Function Name: {item.function_name}")
            
            if hasattr(item, 'arguments'):
                print(f"      Arguments: {item.arguments}")
            
            if hasattr(item, 'text') and item.text:
                print(f"      Text: {item.text[:200]}...")
            
            # Extract Bing search results
            if hasattr(item, 'response_metadata'):
                _parse_search_results(item.response_metadata)
    
    content = message.content or ""
    if content.strip():
        print(f"💬 Content: {content}")
    else:
        print("💬 Content: [Empty]")
    
    sys.stdout.flush()
    print()

def _parse_search_results(response_meta):
    """Parse and display Bing search results from metadata."""
    print(f"      Response Metadata: {str(response_meta)[:300]}...")
    
    if isinstance(response_meta, str):
        try:
            import json
            parsed_meta = json.loads(response_meta)
            if 'webPages' in parsed_meta:
                web_pages = parsed_meta.get('webPages', {})
                total_docs = web_pages.get('totalEstimatedMatches', 0)
                available_docs = len(web_pages.get('value', []))
                print(f"      📊 BING SEARCH RESULTS: {available_docs} docs returned, ~{total_docs} total matches")
                
                # Show first few results
                for j, page in enumerate(web_pages.get('value', [])[:3]):
                    title = page.get('name', 'No title')[:50]
                    url = page.get('url', 'No URL')[:80]
                    print(f"         Result {j+1}: {title} - {url}")
        except Exception as parse_error:
            print(f"      ⚠️ Could not parse search results: {parse_error}")

def _handle_default_response(message, agent_name, message_type, role):
    """Handle default agent responses."""
    print(f"\n🤖 **{agent_name}** [{message_type}] (role: {role})")
    print("-" * (len(agent_name) + len(message_type) + 15))
    
    content = message.content or ""
    if content.strip():
        print(f"💬 Content: {content}")
    else:
        print("💬 Content: [Empty]")
    
    sys.stdout.flush()
    print()

async def streaming_agent_response_callback(streaming_message: StreamingChatMessageContent, is_final: bool) -> None:
    """Simple streaming callback to show real-time agent responses."""
    
    # Print streaming content as it arrives
    if hasattr(streaming_message, 'content') and streaming_message.content:
        print(streaming_message.content, end='', flush=True)
    
    # Add a newline when the streaming is complete for this message
    if is_final:
        print()
