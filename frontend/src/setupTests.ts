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
