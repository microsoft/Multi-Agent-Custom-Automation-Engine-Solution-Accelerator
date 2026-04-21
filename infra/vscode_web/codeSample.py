from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str="<%= connectionString %>")

agent = project_client.agents.get_agent("<%= agentId %>")

thread = project_client.agents.create_thread()
print(f"Created thread, ID: {thread.id}")

message = project_client.agents.create_message(
    thread_id=thread.id,
    role="user",
    content="<%= userMessage %>"
)

run = project_client.agents.create_and_process_run(
    thread_id=thread.id,
    agent_id=agent.id)
messages = project_client.agents.list_messages(thread_id=thread.id)

for text_message in messages.text_messages:
    print(text_message.as_dict())
