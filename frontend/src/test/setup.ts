import "@testing-library/jest-dom/vitest";

// Leaflet measures the DOM; jsdom reports every element as 0x0 and react-leaflet
// throws on it. The map is covered by its own unit test of the class-break
// function, not by rendering a tile layer in a fake browser.
if (!globalThis.matchMedia) {
  globalThis.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

// Recharts sizes itself from the container; jsdom has no layout.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
