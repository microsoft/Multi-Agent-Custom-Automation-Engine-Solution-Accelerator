type EventCallback = (...args: any[]) => void;

class EventBus {
  private events: { [key: string]: EventCallback[] } = {};
  private panelWidth: number = 400;
  private activePanel: "first" | "second" | "third" | "fourth" | null = null;

  on(event: string, callback: EventCallback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  }

  off(event: string, callback: EventCallback) {
    if (!this.events[event]) return;
    this.events[event] = this.events[event].filter(cb => cb !== callback);
  }

  emit(event: string, ...args: any[]) {
    if (!this.events[event]) return;
    this.events[event].forEach(callback => callback(...args));
  }

  // Panel control
  setActivePanel(panel: "first" | "second" | "third" | "fourth" | null) {
    this.activePanel = panel;
    this.emit("setActivePanel", panel);
  }

  getActivePanel(): "first" | "second" | "third" | "fourth" | null {
    return this.activePanel;
  }

  // Shared panel width
  setPanelWidth(width: number) {
    this.panelWidth = width;
    this.emit("panelWidthChanged", width);
  }

  getPanelWidth(): number {
    return this.panelWidth;
  }
}

const eventBus = new EventBus();
export default eventBus;
