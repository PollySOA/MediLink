import '@testing-library/jest-dom';

// Mock import.meta.env for Vite environment variables
globalThis.import = {
  meta: {
    env: {
      VITE_API_URL: 'http://localhost:8000',
      MODE: 'test',
      DEV: true,
      PROD: false,
    },
  },
} as any;

// Mock HTMLCanvasElement.getContext for jsdom (canvas is not implemented in jsdom)
HTMLCanvasElement.prototype.getContext = jest.fn().mockReturnValue({
  clearRect: jest.fn(),
  fillRect: jest.fn(),
  beginPath: jest.fn(),
  roundRect: jest.fn(),
  fill: jest.fn(),
});
