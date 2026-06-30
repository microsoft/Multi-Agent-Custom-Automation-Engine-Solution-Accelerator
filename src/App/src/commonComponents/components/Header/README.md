# Header Components

The Header components form the top navigation bar of your Coral application, providing branding, navigation tools, and panel toggles.

## Components Overview

- `Header`: Main container component for the top bar
- `HeaderTools`: Container for right-aligned actions and tools
- `PanelRightToggles`: Container for toggle buttons that control right panel visibility

## Phase 1: UI Customization

### Header Component

The Header component accepts these customization props:

```jsx
<Header
  title="Your Company"        // Main title text
  subtitle="Your App Name"    // Secondary title/app name
  logo={<YourLogoComponent/>} // Custom logo component or image
>
  {/* Children will be rendered inside the header */}
</Header>
```

### HeaderTools Component

The `HeaderTools` component is a container for right-aligned elements:

```jsx
<HeaderTools>
  <Avatar />                  // User avatar
  <ToolbarDivider />          // Visual separator
  {/* Other right-aligned tools */}
</HeaderTools>
```

### PanelRightToggles Component

This component contains toggle buttons for showing/hiding right panels:

```jsx
<PanelRightToggles>
  <ToggleButton 
    appearance="subtle" 
    icon={<History />}        // Replace with your icon
  />
  {/* Add more toggle buttons as needed */}
</PanelRightToggles>
```

### Styling

You can customize the appearance using:

1. **Props**: Use the `appearance` prop on buttons (values: "subtle", "primary", etc.)
2. **Icons**: Replace default icons with your own from Fluent UI or custom SVGs
3. **Custom CSS**: Apply CSS classes or inline styles

```jsx
// Example with custom styling
<HeaderTools>
  <Avatar 
    size={32} 
    className="custom-avatar" 
  />
  <ToolbarDivider />
  <Button 
    appearance="primary"
    style={{ marginLeft: '8px' }} 
    icon={<CustomIcon />}
  />
</HeaderTools>
```

## Phase 2: Data Population (Mock Data)

The Header components can be populated with dynamic data:

### Dynamic User Information

```jsx
// Example with dynamic user data
const user = {
  name: "Jane Doe",
  avatarUrl: "https://example.com/avatar.jpg",
  role: "Admin"
};

<HeaderTools>
  <Avatar 
    name={user.name}
    image={{ src: user.avatarUrl }}
  />
  <Text>{user.name}</Text>
  <Badge appearance="filled">{user.role}</Badge>
</HeaderTools>
```

## Phase 3: Service Integration & Event Handling

### Panel Toggle State Management

Connect toggle buttons to control panel visibility:

```jsx
import { useState } from 'react';
import eventBus from '../eventbus';

function MyHeader() {
  const [isHistoryPanelOpen, setHistoryPanelOpen] = useState(false);
  
  const toggleHistoryPanel = () => {
    const newState = !isHistoryPanelOpen;
    setHistoryPanelOpen(newState);
    // Emit event to inform other components
    eventBus.emit('historyPanelToggled', newState);
  };
  
  return (
    <Header title="Microsoft" subtitle="Coral">
      <HeaderTools>
        <Avatar />
        <ToolbarDivider />
        <PanelRightToggles>
          <ToggleButton 
            appearance="subtle" 
            icon={<History />}
            checked={isHistoryPanelOpen}
            onClick={toggleHistoryPanel}
          />
          {/* Other toggles */}
        </PanelRightToggles>
      </HeaderTools>
    </Header>
  );
}
```

### User Authentication Integration

```jsx
// Example with user service integration
import { userService } from '../../services/userService';

function UserProfile() {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    // Fetch user profile on component mount
    userService.getCurrentUser()
      .then(userData => setUser(userData))
      .catch(err => console.error('Failed to load user:', err));
  }, []);
  
  return (
    <HeaderTools>
      {user ? (
        <>
          <Avatar name={user.name} image={{ src: user.avatarUrl }} />
          <Text>{user.name}</Text>
        </>
      ) : (
        <Button appearance="primary">Sign In</Button>
      )}
    </HeaderTools>
  );
}
```

## Props API

### Header Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| title | string | "" | Primary title/brand name |
| subtitle | string | "" | Secondary title/app name |
| logo | ReactNode | null | Component to render as the logo |
| children | ReactNode | null | Content to render in the header |

### HeaderTools Props

This component primarily acts as a container and doesn't accept special props beyond standard React props.

### PanelRightToggles Props

This component primarily acts as a container and doesn't accept special props beyond standard React props.

## Best Practices

1. Keep the header clean and minimal for better user experience.
2. Group related actions together.
3. Use consistent icons and button styles.
4. Consider responsive behavior for smaller screens.
5. Ensure toggle buttons clearly indicate their state (active/inactive). 