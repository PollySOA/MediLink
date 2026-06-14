/**
 * Tests for custom hooks
 */
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';

describe('useVoiceRecorder', () => {
  it('should be importable', () => {
    expect(useVoiceRecorder).toBeDefined();
    expect(typeof useVoiceRecorder).toBe('function');
  });
});
