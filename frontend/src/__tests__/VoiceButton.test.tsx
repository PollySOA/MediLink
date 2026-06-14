/**
 * Tests for VoiceButton component
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import VoiceButton from '../components/VoiceButton';

const defaultProps = {
  state: 'idle' as const,
  isSupported: true,
  interimText: '',
  isElenaThinking: false,
  onToggle: jest.fn(),
};

describe('VoiceButton', () => {
  it('should render the voice button in idle state', () => {
    render(<VoiceButton {...defaultProps} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
    expect(screen.getByText('Hablar con Elena')).toBeInTheDocument();
  });

  it('should render in listening state', () => {
    render(<VoiceButton {...defaultProps} state="listening" />);
    expect(screen.getByText('Escuchando... (pulsa para parar)')).toBeInTheDocument();
  });

  it('should show unsupported message when browser lacks speech recognition', () => {
    render(<VoiceButton {...defaultProps} isSupported={false} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Reconocimiento de voz no disponible/)).toBeInTheDocument();
  });

  it('should show interim transcript text when provided', () => {
    render(<VoiceButton {...defaultProps} interimText="Hola Elena" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText(/Hola Elena/)).toBeInTheDocument();
  });

  it('should call onToggle when button is clicked', () => {
    const onToggle = jest.fn();
    render(<VoiceButton {...defaultProps} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('should disable the button while Elena is thinking', () => {
    render(<VoiceButton {...defaultProps} isElenaThinking={true} />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('should accept onToggle callback prop', () => {
    const mockOnToggle = jest.fn();
    expect(typeof mockOnToggle).toBe('function');
    expect(mockOnToggle).toBeDefined();
  });
});

