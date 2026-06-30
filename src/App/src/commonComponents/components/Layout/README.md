# Layout Components

The Layout components provide the fundamental structure for your Coral application, defining how different sections are arranged on the page.

## Components Overview

- `CoralShellColumn`: Vertical layout container that typically wraps the entire application
- `CoralShellRow`: Horizontal layout container that typically wraps the main content area and panels

## Phase 1: UI Customization

### CoralShellColumn Component

The `CoralShellColumn` component creates a vertical column layout:

```jsx
<CoralShellColumn>
  <Header />
  <CoralShellRow>
    {/* Main content and panels */}
  </CoralShellRow>
</CoralShellColumn>
```

You can customize it with:

- Standard CSS properties via inline styles
- CSS classes
- Wrapping it with custom containers

Example with styling:

```jsx
<CoralShellColumn 
  style={{ 
    maxWidth: '1400px', 
    margin: '0 auto',
    minHeight: '100vh'
  }}
  className="custom-shell"
>
  {/* Content */}
</CoralShellColumn>
```

### CoralShellRow Component

The `CoralShellRow` component creates a horizontal row layout, typically used to arrange panels and main content:

```jsx
<CoralShellRow>
  <PanelLeft />
  <Content />
  <PanelRight />
</CoralShellRow>
```

Customization options:

```jsx
<CoralShellRow 
  style={{ 
    flex: 1,
    gap: '16px', 
    padding: '8px' 
  }}
  className="main-content-row"
>
  {/* Content */}
</CoralShellRow>
```

## Layout Structure

The typical arrangement of components:

```jsx
<CoralShellColumn>
  {/* Top Section */}
  <Header>
    <HeaderTools>
      <PanelRightToggles />
    </HeaderTools>
  </Header>
  
  {/* Main Section */}
  <CoralShellRow>
    {/* Left Navigation */}
    <PanelLeft>
      <PanelLeftToolbar />
      {/* Panel content */}
    </PanelLeft>
    
    {/* Center Content */}
    <Content>
      <ContentToolbar />
      {/* Main application content */}
    </Content>
    
    {/* Right Panels */}
    <PanelRightFirst />
    <PanelRightSecond />
    {/* Additional panels */}
  </CoralShellRow>
</CoralShellColumn>
```

## Responsive Behavior

The layout components are designed to be responsive. Here are some tips for ensuring your layout works across different screen sizes:

1. Use percentage or viewport-based widths for panels
2. Consider hiding less important panels on smaller screens
3. Apply media queries for specific breakpoints

Example of responsive customization:

```jsx
// In your CSS file
@media (max-width: 768px) {
  .panel-left {
    display: none;
  }
  
  .content-area {
    padding: 8px;
  }
}

// In your component
<PanelLeft className="panel-left" />
<Content className="content-area" />
```

## Props API

### CoralShellColumn Props

This component primarily acts as a container and accepts standard React props like:
- `children`: React nodes to render inside the column
- `className`: CSS class to apply to the column
- `style`: Inline styles to apply to the column

### CoralShellRow Props

This component primarily acts as a container and accepts standard React props like:
- `children`: React nodes to render inside the row
- `className`: CSS class to apply to the row
- `style`: Inline styles to apply to the row

## Best Practices

1. **Maintain Hierarchy**: Follow the standard nesting pattern (Column > Row > Components)
2. **Flex Properties**: Use flex properties for fine-tuning the layout
3. **Accessibility**: Ensure your layout is accessible by maintaining proper landmark regions
4. **Consistent Spacing**: Use consistent spacing between layout elements
5. **Responsive Design**: Test your layout on various screen sizes 