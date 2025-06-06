type EventCallback = (...args: any[]) => void;

class EventBus {
  private events: { [key: string]: EventCallback[] } = {};
  private panelWidth: number = 400; // Shared default width for panels

  // Register an event listener
  on(event: string, callback: EventCallback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  }

  // Remove an event listener
  off(event: string, callback: EventCallback) {
    if (!this.events[event]) return;
    this.events[event] = this.events[event].filter((cb) => cb !== callback);
  }

  // Emit an event
  emit(event: string, ...args: any[]) {
    if (!this.events[event]) return;
    this.events[event].forEach((callback) => callback(...args));
  }

  // Manage shared panel width
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
