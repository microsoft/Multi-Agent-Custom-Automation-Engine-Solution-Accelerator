# Panel Components

Panel components provide specialized containers for navigation, filters, tools, and information displays that typically appear on the sides of your Coral application.

## Components Overview

- `PanelLeft`: Main left-side panel with resize capabilities
- `PanelLeftToolbar`: Header area for the left panel with title and controls
- `PanelRightFirst`, `PanelRightSecond`, etc.: Right-side panels for various purposes

## Phase 1: UI Customization

### PanelLeft Component

The `PanelLeft` component creates a resizable left panel:

```jsx
<PanelLeft
  panelWidth={280}          // Initial width in pixels
  panelResize={true}        // Allow user resizing
>
  <PanelLeftToolbar 
    panelTitle="Navigation" 
    panelIcon={<YourIcon />} 
  />
  {/* Panel content */}
</PanelLeft>
```

Customization options:

```jsx
<PanelLeft
  panelWidth={320}
  panelResize={true}
  style={{ 
    backgroundColor: '#f5f5f5',
    borderRight: '1px solid #e0e0e0'
  }}
  className="custom-left-panel"
>
  {/* Content */}
</PanelLeft>
```

### PanelLeftToolbar Component

The `PanelLeftToolbar` component provides a header for the left panel:

```jsx
<PanelLeftToolbar 
  panelTitle="Your Panel Title"
  panelIcon={<CustomIcon />}
>
  {/* Optional toolbar actions */}
  <Button appearance="subtle" icon={<RefreshIcon />} />
</PanelLeftToolbar>
```

### Right Panel Components

Right panels follow a similar pattern:

```jsx
<PanelRightFirst>
  {/* Content for the first right panel */}
</PanelRightFirst>

<PanelRightSecond>
  {/* Content for the second right panel */}
</PanelRightSecond>
```

## Phase 2: Data Population (Mock Data)

The panels can be populated with dynamic data to display lists, trees, or other structured information.

### Navigation List Example

```jsx
import { useState } from 'react';
import { 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText 
} from '@fluentui/react-components';

function NavigationPanel() {
  // Mock navigation data
  const navItems = [
    { id: 'home', label: 'Home', icon: <HomeIcon /> },
    { id: 'documents', label: 'Documents', icon: <DocumentIcon /> },
    { id: 'settings', label: 'Settings', icon: <SettingsIcon /> },
  ];
  
  const [selectedItem, setSelectedItem] = useState('home');
  
  return (
    <PanelLeft panelWidth={280} panelResize={true}>
      <PanelLeftToolbar panelTitle="Navigation" />
      
      <List>
        {navItems.map(item => (
          <ListItem 
            key={item.id}
            selected={selectedItem === item.id}
            onClick={() => setSelectedItem(item.id)}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText>{item.label}</ListItemText>
          </ListItem>
        ))}
      </List>
    </PanelLeft>
  );
}
```

### Filtered List Example

```jsx
import { useState, useEffect } from 'react';
import { 
  Input, 
  List, 
  ListItem,
  ListItemText 
} from '@fluentui/react-components';
import { Search } from '@fluentui/react-icons';

function FilterPanel() {
  // Mock data
  const allItems = [
    { id: '1', name: 'Item One', category: 'A' },
    { id: '2', name: 'Item Two', category: 'B' },
    { id: '3', name: 'Another Item', category: 'A' },
    { id: '4', name: 'Last Item', category: 'C' },
  ];
  
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredItems, setFilteredItems] = useState(allItems);
  
  // Filter items based on search
  useEffect(() => {
    const filtered = allItems.filter(item => 
      item.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredItems(filtered);
  }, [searchTerm]);
  
  return (
    <PanelLeft panelWidth={300} panelResize={true}>
      <PanelLeftToolbar panelTitle="Items" />
      
      <div style={{ padding: '8px' }}>
        <Input 
          placeholder="Search items..." 
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          contentBefore={<Search />}
        />
      </div>
      
      <List>
        {filteredItems.map(item => (
          <ListItem key={item.id}>
            <ListItemText>{item.name}</ListItemText>
          </ListItem>
        ))}
      </List>
    </PanelLeft>
  );
}
```

## Phase 3: Service Integration & Event Handling

Connect your panels to services and event handling to make them fully interactive.

### Data Service Integration

```jsx
import { useState, useEffect } from 'react';
import { 
  List, 
  ListItem,
  ListItemText,
  Spinner 
} from '@fluentui/react-components';
// Example service
import { itemService } from '../../services/itemService';

function ServiceConnectedPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // Fetch data from service
    setLoading(true);
    itemService.getItems()
      .then(data => {
        setItems(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load items:', err);
        setError('Failed to load items');
        setLoading(false);
      });
  }, []);
  
  return (
    <PanelLeft panelWidth={280} panelResize={true}>
      <PanelLeftToolbar panelTitle="Items" />
      
      {loading && <Spinner />}
      {error && <div className="error-message">{error}</div>}
      
      <List>
        {items.map(item => (
          <ListItem key={item.id}>
            <ListItemText>{item.name}</ListItemText>
          </ListItem>
        ))}
      </List>
    </PanelLeft>
  );
}
```

### EventBus Integration

```jsx
import { useState, useEffect } from 'react';
import eventBus from '../eventbus';

function EventAwarePanel() {
  const [isPanelVisible, setPanelVisible] = useState(true);
  
  useEffect(() => {
    // Subscribe to events
    const handleToggle = (visible) => {
      setPanelVisible(visible);
    };
    
    eventBus.on('toggleLeftPanel', handleToggle);
    
    // Cleanup
    return () => {
      eventBus.off('toggleLeftPanel', handleToggle);
    };
  }, []);
  
  if (!isPanelVisible) return null;
  
  return (
    <PanelLeft panelWidth={280} panelResize={true}>
      <PanelLeftToolbar 
        panelTitle="Event-Aware Panel"
        panelIcon={<InfoIcon />}
      />
      {/* Panel content */}
    </PanelLeft>
  );
}
```

### Selection Event Emitting

```jsx
import eventBus from '../eventbus';

function SelectionPanel() {
  const items = [/*...your items...*/];
  
  const handleItemClick = (item) => {
    // Emit event when item is selected
    eventBus.emit('itemSelected', item);
  };
  
  return (
    <PanelLeft panelWidth={280} panelResize={true}>
      <PanelLeftToolbar panelTitle="Select Item" />
      
      <List>
        {items.map(item => (
          <ListItem 
            key={item.id}
            onClick={() => handleItemClick(item)}
          >
            <ListItemText>{item.name}</ListItemText>
          </ListItem>
        ))}
      </List>
    </PanelLeft>
  );
}
```

## Props API

### PanelLeft Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| panelWidth | number | 280 | Initial width of the panel in pixels |
| panelResize | boolean | false | Whether the panel can be resized by the user |
| children | ReactNode | null | Content to render inside the panel |
| className | string | "" | Additional CSS class names |
| style | CSSProperties | {} | Additional inline styles |

### PanelLeftToolbar Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| panelTitle | string | "" | Title text to display in the toolbar |
| panelIcon | ReactNode | null | Icon to display next to the title |
| children | ReactNode | null | Additional content for the toolbar (buttons, etc.) |

### Right Panel Props

Right panels typically accept standard React props like `children`, `className`, and `style`.

## Best Practices

1. **Content Organization**: Keep panel content organized and minimal.
2. **Visual Hierarchy**: Use proper sizing and spacing for list items.
3. **Loading States**: Always show loading indicators when fetching data.
4. **Error Handling**: Display user-friendly error messages.
5. **Responsive Design**: Consider how panels will behave on smaller screens. 