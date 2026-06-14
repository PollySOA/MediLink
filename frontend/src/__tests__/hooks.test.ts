/**
 * Tests for custom hooks
 */

describe('useVoiceRecorder', () => {
  it('should be importable', () => {
    const { useVoiceRecorder } = require('../hooks/useVoiceRecorder');
    expect(useVoiceRecorder).toBeDefined();
    expect(typeof useVoiceRecorder).toBe('function');
  });
});
