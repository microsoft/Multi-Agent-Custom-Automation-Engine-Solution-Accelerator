# Sprint 4 Frontend Testing Guide

## 🚀 Quick Start

### Option 1: Using the Helper Script (Recommended)

Simply double-click or run:
```bash
run_frontend.bat
```

This will:
1. Navigate to `src/frontend`
2. Install any missing dependencies
3. Start the Vite development server
4. Open on `http://localhost:5173`

### Option 2: Manual Start

```bash
cd src/frontend
npm install
npm run dev
```

---

## 🌐 Testing the Components

### 1. Analytics Dashboard

**URL:** `http://localhost:5173/analytics`

**What to Test:**
- [ ] 4 KPI cards display correctly
- [ ] Trend indicators show (green up arrow or red down arrow)
- [ ] KPI cards are clickable and navigate
- [ ] Forecast chart renders with data
- [ ] Quick action buttons work
- [ ] Responsive design (resize browser window)

**Expected Behavior:**
- **Revenue Forecast:** $1.2M with +8.5% (green arrow)
- **Customer Retention:** 92.3% with +2.1% (green arrow)  
- **Avg Order Value:** $142 with -3.2% (red arrow)
- **Forecast Accuracy:** 94.8% with +1.5% (green arrow)
- Chart shows Jan-Jun with forecast starting at Mar

### 2. Forecast Chart Component

**Location:** Integrated in Analytics Dashboard

**What to Test:**
- [ ] Chart displays historical data (blue line, solid)
- [ ] Chart displays forecast data (green line, dashed)
- [ ] Confidence interval shows as shaded green area
- [ ] Toggle "Actual" button hides/shows historical data
- [ ] Toggle "Forecast" button hides/shows forecast data
- [ ] Hover tooltip shows values
- [ ] Reference line at "Forecast Start"
- [ ] Summary stats at bottom show forecast range

**Interactive Features:**
- Click "Actual" toggle - blue line disappears/reappears
- Click "Forecast" toggle - green line and shading disappears/reappears
- Hover over points - see tooltips with exact values

### 3. Enhanced Dataset Panel

**URL:** Via Plan page or integrated view

**What to Test:**
- [ ] Multi-file upload works (select multiple CSVs)
- [ ] Drag and drop works (drag files onto drop zone)
- [ ] Search box filters datasets
- [ ] Filter dropdown (All Types / CSV Only / XLSX Only)
- [ ] Dataset cards show file size, column count
- [ ] File type badges (CSV = green, XLSX = blue)
- [ ] Quick action buttons (visualize, stats, download, delete)
- [ ] Preview table shows first 3 rows, first 5 columns
- [ ] Delete confirmation dialog appears

**Test Data:** Use files from `data/datasets/` folder

### 4. Model Comparison Panel

**URL:** Integrated component (can be viewed in Storybook or standalone page)

**Mock Test:**
Currently shown with mock data. When integrated with backend:
- [ ] Metrics table displays all models
- [ ] Best model has "Best" badge
- [ ] MAPE sorting (lowest to highest)
- [ ] "Select" button changes to "Selected" when clicked
- [ ] Chart updates when different model selected
- [ ] All metrics (MAE, RMSE, MAPE) display correctly

---

## 🎨 Visual Verification Checklist

### Colors
- [ ] Primary blue (#0078d4) for buttons and links
- [ ] Success green (#107c10) for positive trends and forecasts
- [ ] Danger red (#d83b01) for negative trends
- [ ] Brand purple (#5c2d91) for special indicators
- [ ] Neutral grays for backgrounds and borders

### Typography
- [ ] Headers are bold and prominent
- [ ] Body text is readable (14px)
- [ ] Captions are smaller (12px)
- [ ] Consistent font family (Segoe UI)

### Spacing
- [ ] Cards have consistent padding (1.5rem)
- [ ] Grid gaps are uniform (1.5rem)
- [ ] Elements don't overlap
- [ ] White space is balanced

### Responsiveness
- [ ] Desktop view (1400px+) - all cards in grid
- [ ] Tablet view (768-1024px) - 2-column grid
- [ ] Mobile view (<768px) - single column
- [ ] Charts scale properly
- [ ] Text doesn't overflow

---

## 🐛 Common Issues & Solutions

### Issue: "npm is not recognized"
**Solution:** Install Node.js from https://nodejs.org/ (v18 or later recommended)

### Issue: "Permission denied" errors
**Solution:** Run PowerShell as Administrator or use the batch file

### Issue: "Port 5173 already in use"
**Solution:** 
```bash
# Kill the existing process
npx kill-port 5173

# Or use a different port
npm run dev -- --port 3000
```

### Issue: Charts not rendering
**Solution:** Ensure recharts is installed
```bash
cd src/frontend
npm install recharts @types/recharts
```

### Issue: TypeScript errors
**Solution:** 
```bash
cd src/frontend
npm run build
```
This will show any TypeScript compilation errors

### Issue: Blank page
**Solution:** Check browser console (F12) for errors. Likely causes:
1. Import path issues
2. Missing component exports
3. Router configuration problems

---

## 📸 Screenshots to Capture

For documentation purposes, capture:

1. **Analytics Dashboard - Full View**
   - All 4 KPI cards
   - Forecast chart
   - Quick actions panel

2. **Forecast Chart - Detailed View**
   - Chart with confidence intervals visible
   - Tooltip showing on hover
   - Toggle buttons in different states

3. **Enhanced Dataset Panel**
   - Multiple datasets loaded
   - Search in action
   - Filter dropdown open
   - Preview table expanded

4. **Responsive Views**
   - Desktop layout
   - Tablet layout
   - Mobile layout

---

## 🧪 Browser Compatibility

Test in:
- [ ] Chrome/Edge (Chromium-based) - Primary target
- [ ] Firefox
- [ ] Safari (if on Mac)

**Minimum supported versions:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## 📊 Performance Checks

### Load Times
- [ ] Initial page load < 2 seconds
- [ ] Chart render < 500ms
- [ ] Dataset list load < 1 second
- [ ] No visible lag when toggling chart elements

### Memory Usage
- [ ] No memory leaks after navigating between pages
- [ ] Stable memory usage (~50-100MB)
- [ ] Charts clean up properly when unmounted

### Console
- [ ] No console errors
- [ ] No console warnings (except deprecated npm packages)
- [ ] API calls complete successfully

---

## ✅ Acceptance Criteria

Sprint 4 is considered complete when:

- [ ] All 4 components render without errors
- [ ] Analytics Dashboard is accessible at `/analytics`
- [ ] Interactive features work (toggles, buttons, navigation)
- [ ] Charts display data correctly
- [ ] Responsive design works on desktop, tablet, mobile
- [ ] No TypeScript compilation errors
- [ ] No console errors in browser
- [ ] Components follow Fluent UI design system
- [ ] Code passes linting (no errors)

---

## 🎯 Next Steps After Testing

1. **Document Issues** - Create list of bugs found
2. **Performance Optimization** - If needed
3. **Accessibility Audit** - Screen reader testing
4. **User Feedback** - Show to stakeholders
5. **Sprint 5 Planning** - Use cases and documentation

---

## 📝 Test Results Template

```markdown
## Sprint 4 Test Results

**Date:** ___________
**Tester:** ___________
**Browser:** ___________

### Component Status
- [ ] ForecastChart: ✅ Pass / ❌ Fail
- [ ] ModelComparisonPanel: ✅ Pass / ❌ Fail
- [ ] AnalyticsDashboard: ✅ Pass / ❌ Fail
- [ ] EnhancedForecastDatasetPanel: ✅ Pass / ❌ Fail

### Issues Found
1. [Issue description]
2. [Issue description]

### Notes
[Any additional observations]
```

---

**Happy Testing! 🎉**

For questions or issues, refer to:
- Implementation details: `docs/Frontend_Sprint4_Implementation_Guide.md`
- Component code: `src/frontend/src/components/content/`
- Progress summary: `SPRINT_PROGRESS_SUMMARY.md`

