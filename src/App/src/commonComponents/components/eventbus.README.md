# Event Bus

The `eventbus.tsx` component provides a simple pub/sub (publish-subscribe) mechanism for decoupled communication between components across your Coral application.

## Overview

The Event Bus enables communication between components that:
- Don't have a direct parent-child relationship
- Are in different parts of the component tree
- Need to communicate without prop drilling

It follows the Observer pattern, allowing components to subscribe to events (topics) and react when those events are triggered by other components.

## Basic Usage

### Importing the Event Bus

```jsx
import eventBus from './eventbus';
```

### Subscribing to Events

To listen for a specific event:

```jsx
// Event handler function
const handleMyEvent = (data) => {
  console.log('Event received with data:', data);
  // Handle the event...
};

// Subscribe to an event
eventBus.on('myEventName', handleMyEvent);
```

### Publishing Events

To trigger an event:

```jsx
// Emit an event with optional data
eventBus.emit('myEventName', { id: 123, value: 'example data' });
```

### Unsubscribing from Events

Always unsubscribe when a component unmounts to prevent memory leaks:

```jsx
// Unsubscribe from an event
eventBus.off('myEventName', handleMyEvent);
```

## Example in React Components

### Component A (Event Publisher)

```jsx
import React from 'react';
import eventBus from '../eventbus';
import { Button } from '@fluentui/react-components';

function ComponentA() {
  const handleButtonClick = () => {
    // Publish an event when button is clicked
    eventBus.emit('itemSelected', { 
      id: '123', 
      name: 'Example Item', 
      details: 'This is an example item'
    });
  };
  
  return (
    <div>
      <Button onClick={handleButtonClick}>Select Item</Button>
    </div>
  );
}

export default ComponentA;
```

### Component B (Event Subscriber)

```jsx
import React, { useState, useEffect } from 'react';
import eventBus from '../eventbus';

function ComponentB() {
  const [selectedItem, setSelectedItem] = useState(null);
  
  useEffect(() => {
    // Handler function
    const handleItemSelected = (item) => {
      setSelectedItem(item);
      console.log('Item selected:', item);
    };
    
    // Subscribe when component mounts
    eventBus.on('itemSelected', handleItemSelected);
    
    // Unsubscribe when component unmounts
    return () => {
      eventBus.off('itemSelected', handleItemSelected);
    };
  }, []); // Empty dependency array ensures this runs only once on mount
  
  return (
    <div>
      <h2>Selected Item:</h2>
      {selectedItem ? (
        <div>
          <p>ID: {selectedItem.id}</p>
          <p>Name: {selectedItem.name}</p>
          <p>Details: {selectedItem.details}</p>
        </div>
      ) : (
        <p>No item selected</p>
      )}
    </div>
  );
}

export default ComponentB;
```

## Common Use Cases

1. **Panel Visibility Toggling**: Toggle right/left panels from header buttons
   ```jsx
   // In header component
   eventBus.emit('togglePanel', { panelId: 'rightPanel', isVisible: true });
   
   // In panel component
   eventBus.on('togglePanel', ({ panelId, isVisible }) => {
     if (panelId === 'rightPanel') {
       setVisible(isVisible);
     }
   });
   ```

2. **Selection Synchronization**: Update multiple components when an item is selected
   ```jsx
   // In list component
   eventBus.emit('itemSelected', selectedItem);
   
   // In details component
   eventBus.on('itemSelected', setCurrentItem);
   ```

3. **Global Notifications**: Show notifications across the application
   ```jsx
   // Trigger notification from anywhere
   eventBus.emit('showNotification', { 
     message: 'Operation completed successfully', 
     type: 'success' 
   });
   
   // In notification component
   eventBus.on('showNotification', showNotification);
   ```

## Best Practices

1. **Consistent Event Names**: Use a clear naming convention for events, such as:
   - `verb:noun` (e.g., `select:item`, `toggle:panel`)
   - `entityName:action` (e.g., `item:selected`, `panel:toggled`)

2. **Typed Events**: For TypeScript applications, define interfaces for your event data:
   ```typescript
   interface ItemSelectedEvent {
     id: string;
     name: string;
     category?: string;
   }
   
   // Emit with type
   eventBus.emit('itemSelected', { id: '123', name: 'Example' } as ItemSelectedEvent);
   
   // Handle with type
   const handleItemSelected = (data: ItemSelectedEvent) => {
     // Typed data
   };
   ```

3. **Cleanup Subscriptions**: Always unsubscribe in the `useEffect` cleanup function or `componentWillUnmount` lifecycle method.

4. **Documentation**: Document the events emitted and required payload for each component.

5. **When to Use**: Only use the Event Bus when props or React Context are not suitable:
   - Props: For direct parent-child communication
   - Context: For state shared across a subtree of components
   - Event Bus: For communication between unrelated components

## Implementation Details

The Event Bus is implemented using a simple JavaScript object that maintains a map of event names to arrays of handler functions:

```typescript
// Simplified implementation
const eventBus = {
  events: {},
  
  on(event: string, callback: Function) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  },
  
  off(event: string, callback: Function) {
    if (this.events[event]) {
      this.events[event] = this.events[event].filter(cb => cb !== callback);
    }
  },
  
  emit(event: string, data?: any) {
    if (this.events[event]) {
      this.events[event].forEach(callback => callback(data));
    }
  }
};

export default eventBus;
``` 