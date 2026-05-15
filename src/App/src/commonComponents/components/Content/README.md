# Content Components

The Content components create the main workspace of your Coral application, providing the primary display area for your application's features and interfaces.

## Components Overview

- `Content`: Main container for application content
- `ContentToolbar`: Header area for the content section with title and controls
- `Chat`: Component for displaying and interacting with chat interfaces

## Phase 1: UI Customization

### Content Component

The `Content` component creates the main workspace area:

```jsx
<Content>
  <ContentToolbar panelTitle="Your Title" panelIcon={<YourIcon />} />
  {/* Main content goes here */}
</Content>
```

Customization options:

```jsx
<Content
  style={{
    backgroundColor: '#ffffff',
    padding: '16px',
    overflow: 'auto'
  }}
  className="main-content-area"
>
  {/* Content */}
</Content>
```

### ContentToolbar Component

The `ContentToolbar` component provides a header for the content area:

```jsx
<ContentToolbar 
  panelTitle="Content Title"
  panelIcon={<DocumentIcon />}
>
  {/* Optional toolbar actions */}
  <Button appearance="subtle" icon={<SearchIcon />} />
  <ToolbarDivider />
  <Button appearance="subtle" icon={<MoreHorizontalRegular />} />
</ContentToolbar>
```

### Chat Component

The `Chat` component provides a conversation interface:

```jsx
<Chat
  userId="user123"
  onSendMessage={handleSendMessage}
  onLoadHistory={handleLoadHistory}
  onClearHistory={handleClearHistory}
>
  {/* Optional chat actions */}
  <Button appearance="subtle" icon={<AttachIcon />} />
  <Button appearance="subtle" icon={<EmojiIcon />} />
</Chat>
```

## Phase 2: Data Population (Mock Data)

The Content components can be populated with dynamic data to display various types of content.

### Chat with Mock Messages

```jsx
import { useState } from 'react';

function MockChat() {
  // Mock chat history
  const initialHistory = [
    { role: 'assistant', content: 'Hello! How can I help you today?' },
    { role: 'user', content: 'I need information about your services.' },
    { role: 'assistant', content: 'We offer a variety of services including...' },
  ];
  
  const [messages, setMessages] = useState(initialHistory);
  
  // Mock send message handler
  const handleSendMessage = async (input, history) => {
    // In a real app, this would call a service
    const response = `Thanks for your message: "${input}". This is a mock response.`;
    setMessages([...history, { role: 'user', content: input }, { role: 'assistant', content: response }]);
    return response;
  };
  
  // Mock load history handler
  const handleLoadHistory = (userId) => {
    // In a real app, this would fetch from a service
    console.log(`Loading history for user ${userId}`);
    return Promise.resolve(initialHistory);
  };
  
  // Mock clear history handler
  const handleClearHistory = (userId) => {
    // In a real app, this would call a service
    console.log(`Clearing history for user ${userId}`);
    setMessages([]);
    return Promise.resolve();
  };
  
  return (
    <Content>
      <ContentToolbar panelTitle="Mock Chat" panelIcon={<ChatIcon />}>
        <Button appearance="subtle" icon={<ClearIcon />} onClick={() => handleClearHistory('user123')} />
      </ContentToolbar>
      
      <Chat
        userId="user123"
        onSendMessage={handleSendMessage}
        onLoadHistory={handleLoadHistory}
        onClearHistory={handleClearHistory}
      >
        <Button appearance="subtle" icon={<AttachIcon />} />
      </Chat>
    </Content>
  );
}
```

### Content with Custom Interface

```jsx
import { useState } from 'react';
import { 
  Card, 
  CardHeader, 
  CardPreview,
  CardFooter,
  Button, 
  Text
} from '@fluentui/react-components';

function CustomContent() {
  // Mock data
  const items = [
    { id: '1', title: 'Item One', description: 'Description for item one', image: 'item1.jpg' },
    { id: '2', title: 'Item Two', description: 'Description for item two', image: 'item2.jpg' },
    { id: '3', title: 'Item Three', description: 'Description for item three', image: 'item3.jpg' },
  ];
  
  return (
    <Content>
      <ContentToolbar panelTitle="Custom Interface" panelIcon={<GridIcon />} />
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px', padding: '16px' }}>
        {items.map(item => (
          <Card key={item.id}>
            <CardHeader header={<Text weight="semibold">{item.title}</Text>} />
            <CardPreview>
              <img src={item.image} alt={item.title} style={{ width: '100%', height: 'auto' }} />
            </CardPreview>
            <Text>{item.description}</Text>
            <CardFooter>
              <Button>View Details</Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </Content>
  );
}
```

## Phase 3: Service Integration & Event Handling

Connect your content components to services and event handling to make them fully interactive.

### Chat with Real Service

```jsx
import { useState, useEffect } from 'react';
import { chatService } from '../../services/chatService';

function ServiceConnectedChat() {
  const [userId] = useState('user123');
  const [messages, setMessages] = useState([]);
  
  // Load initial history
  useEffect(() => {
    chatService.getUserHistory(userId)
      .then(history => setMessages(history))
      .catch(err => console.error('Failed to load chat history:', err));
  }, [userId]);
  
  // Send message handler
  const handleSendMessage = async (input, history) => {
    try {
      // Get last conversation ID if available
      const lastAssistantMessage = history.filter(msg => msg.role === 'assistant').pop();
      const conversationId = lastAssistantMessage ? (lastAssistantMessage).conversation_id : undefined;
      
      // Call the service
      const response = await chatService.sendMessage(userId, input, conversationId);
      return response.assistant_response;
    } catch (error) {
      console.error('Error sending message:', error);
      return "Sorry, there was an error processing your request.";
    }
  };
  
  // Load history handler
  const handleLoadHistory = async (id) => {
    try {
      return await chatService.getUserHistory(id);
    } catch (error) {
      console.error('Error loading history:', error);
      return [];
    }
  };
  
  // Clear history handler
  const handleClearHistory = async (id) => {
    try {
      await chatService.clearChatHistory(id);
      setMessages([]);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  };
  
  return (
    <Content>
      <ContentToolbar panelTitle="Chat" panelIcon={<ChatIcon />} />
      
      <Chat
        userId={userId}
        onSendMessage={handleSendMessage}
        onLoadHistory={handleLoadHistory}
        onClearHistory={handleClearHistory}
      >
        <Button appearance="subtle" icon={<AttachIcon />} />
        <Button appearance="subtle" icon={<EmojiIcon />} />
      </Chat>
    </Content>
  );
}
```

### EventBus Integration

```jsx
import { useState, useEffect } from 'react';
import eventBus from '../eventbus';

function EventAwareContent() {
  const [selectedItem, setSelectedItem] = useState(null);
  
  useEffect(() => {
    // Subscribe to item selection events
    const handleItemSelected = (item) => {
      setSelectedItem(item);
    };
    
    eventBus.on('itemSelected', handleItemSelected);
    
    // Cleanup
    return () => {
      eventBus.off('itemSelected', handleItemSelected);
    };
  }, []);
  
  return (
    <Content>
      <ContentToolbar panelTitle="Item Details" panelIcon={<DetailsIcon />} />
      
      {selectedItem ? (
        <div className="item-details">
          <h2>{selectedItem.name}</h2>
          <p>ID: {selectedItem.id}</p>
          <p>Category: {selectedItem.category}</p>
          {/* More item details */}
        </div>
      ) : (
        <div className="no-selection">
          <p>Select an item from the left panel to view details</p>
        </div>
      )}
    </Content>
  );
}
```

## Props API

### Content Props

This component primarily acts as a container and accepts standard React props like:
- `children`: React nodes to render inside the content area
- `className`: CSS class to apply to the content area
- `style`: Inline styles to apply to the content area

### ContentToolbar Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| panelTitle | string | "" | Title text to display in the toolbar |
| panelIcon | ReactNode | null | Icon to display next to the title |
| children | ReactNode | null | Additional content for the toolbar (buttons, etc.) |

### Chat Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| userId | string | required | Identifier for the current user |
| onSendMessage | function | required | Function to call when sending a message: (input, history) => Promise<string> |
| onLoadHistory | function | required | Function to call when loading chat history: (userId) => Promise<ChatMessage[]> |
| onClearHistory | function | required | Function to call when clearing chat history: (userId) => Promise<void> |
| children | ReactNode | null | Additional content for chat actions (buttons, etc.) |

## Best Practices

1. **Maintain Focus**: Keep the main content area focused on the primary task.
2. **Responsive Design**: Ensure content adapts to different screen sizes.
3. **Loading States**: Show loading indicators when fetching data.
4. **Error Handling**: Implement user-friendly error messages.
5. **Accessibility**: Maintain proper heading hierarchy and ensure all interactive elements are accessible.
6. **Performance**: For content with large data sets, implement pagination or virtualization. 