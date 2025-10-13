# 🎯 Team Selector Guide

**Status:** ✅ Team Selector is ALREADY in the UI!

---

## Where to Find the Team Selector

The `TeamSelector` component is already integrated into your frontend and should be visible on the **HomePage** (main page).

### **Location:**
- **Page:** HomePage (route: `/`)
- **Position:** In the left sidebar panel, right under the toolbar
- **File:** `src/frontend/src/components/content/PlanPanelLeft.tsx` (lines 180-186)

---

## How to Use the Team Selector

### **Step 1: Look for the Team Selector Button**

On the HomePage, in the left panel, you should see a button or dropdown near the top that shows the currently selected team.

### **Step 2: Click to Open Team List**

Click on the team selector to open a dialog/dropdown showing all available teams.

### **Step 3: Select a Team**

You should see all 8 teams:
1. ✅ Human Resources Team (default)
2. ✅ Retail Customer Success Team
3. ✅ Financial Forecasting Team
4. ✅ Retail Operations Team
5. ✅ Customer Intelligence Team
6. ✅ Revenue Optimization Team
7. ✅ Marketing Intelligence Team
8. ✅ Product Marketing Team

Click on any team to switch to it.

### **Step 4: Confirm Selection**

After selecting a team:
- The backend will initialize the selected team
- The UI will update to show the new team's name
- You'll see a success toast notification
- The team's agents will be loaded

---

## If You Don't See the Team Selector

### **Troubleshooting:**

1. **Verify you're on the HomePage** (URL: `http://localhost:3001/`)
   - The team selector only shows on the HomePage
   - It won't appear on the Plan page or other pages

2. **Check the browser console** (F12)
   - Look for any errors related to `TeamSelector`
   - Check if teams are being loaded

3. **Verify teams are being fetched:**
   Open browser console and run:
   ```javascript
   fetch('http://localhost:8000/api/v3/team_configs')
     .then(r => r.json())
     .then(teams => console.log('Teams:', teams))
   ```

4. **Hard refresh the page:**
   - Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
   - This clears the cache and reloads all components

---

## How the Team Selector Works

### **Component Flow:**

```
HomePage
  ↓
PlanPanelLeft
  ↓
TeamSelector (if isHomePage === true)
  ↓
Opens Dialog → Shows Team List → User Selects → Calls handleTeamSelect
  ↓
Backend initializes selected team → UI updates → Success!
```

### **Code Location:**

```typescript
// HomePage.tsx
<PlanPanelLeft
    reloadTasks={reloadLeftList}
    onNewTaskButton={handleNewTaskButton}
    onTeamSelect={handleTeamSelect}      // ← Handles team selection
    onTeamUpload={handleTeamUpload}       // ← Handles team upload
    isHomePage={true}                     // ← Enables TeamSelector
    selectedTeam={selectedTeam}
/>

// PlanPanelLeft.tsx
{isHomePage && (
  <TeamSelector
    onTeamSelect={handleTeamSelect}
    onTeamUpload={onTeamUpload}
    selectedTeam={selectedTeam}
    isHomePage={isHomePage}
  />
)}
```

---

## What Happens When You Select a Team

1. **User clicks on a team** in the TeamSelector dialog
2. **TeamSelector calls `onTeamSelect(team)`**
3. **HomePage's `handleTeamSelect` is triggered:**
   - Sets the selected team in state
   - Calls `TeamService.initializeTeam(true)` with `team_switched=true`
   - Backend initializes the selected team (creates agents, etc.)
   - Fetches updated team details from backend
   - Stores team in localStorage
   - Shows success toast
4. **UI updates** to reflect the new team
5. **Left panel reloads** with the new team's tasks

---

## Testing the Team Selector

### **Quick Test:**

1. Open `http://localhost:3001/` in your browser
2. Look at the left sidebar panel
3. Find the team selector (should show "Human Resources Team" by default)
4. Click on it to open the team list
5. Select "Financial Forecasting Team"
6. Wait for initialization (~5-10 seconds)
7. Verify the UI updates with the new team name

### **What You Should See:**

**Before Selection:**
```
Currently selected: Human Resources Team
Agents: 3 (HRHelperAgent, TechnicalSupportAgent, ProxyAgent)
```

**After Selecting Financial Forecasting:**
```
Currently selected: Financial Forecasting Team
Agents: 3 (FinancialStrategistAgent, DataPreparationAgent, ProxyAgent)
```

---

## Visual Reference

The TeamSelector component includes:
- 📋 **Teams Tab** - View and select from all available teams
- ⬆️ **Upload Tab** - Upload new custom team configurations
- 🔍 **Search** - Filter teams by name
- ✅ **Continue Button** - Confirm team selection

---

## API Calls Made by Team Selector

When you open the TeamSelector:
```
GET /api/v3/team_configs  // Fetches all available teams
```

When you select a team:
```
GET /api/v3/init_team?team_switched=true  // Initializes selected team
POST /api/v3/team_selection  // Stores selection (if endpoint exists)
```

---

## Common Issues

### **Issue: "Team initialization failed"**

**Cause:** Backend can't initialize the selected team

**Solution:**
1. Check backend terminal for errors
2. Verify the team has valid `deployment_name` for all agents
3. Ensure all required models are deployed

### **Issue: "No teams showing in selector"**

**Cause:** Teams not being fetched from backend

**Solution:**
1. Verify backend is running: `http://localhost:8000/docs`
2. Check console for API errors
3. Manually test: `curl http://localhost:8000/api/v3/team_configs`

### **Issue: "Selector not visible"**

**Cause:** Not on HomePage or conditional rendering issue

**Solution:**
1. Ensure you're on `http://localhost:3001/` (not `/plan` or other routes)
2. Check `isHomePage` prop is `true`
3. Look for the component in browser DevTools (React tab)

---

## Summary

✅ **Team Selector is already integrated and should be visible on your HomePage**  
✅ **All 8 teams are uploaded and available for selection**  
✅ **Team switching works via the `handleTeamSelect` callback**  
✅ **You can select any team from the UI**

**Just look for the team selector button in the left sidebar on the HomePage!** 🎯

