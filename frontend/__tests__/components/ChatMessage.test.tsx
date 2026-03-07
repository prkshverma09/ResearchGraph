import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ChatMessage from '@/app/components/ChatMessage';
import { Source } from '@/lib/api';

describe('ChatMessage', () => {
  describe('user message', () => {
    it('should render user message', () => {
      render(<ChatMessage role="user" content="Hello, how are you?" />);

      expect(screen.getByText('Hello, how are you?')).toBeInTheDocument();
      expect(screen.getByText('U')).toBeInTheDocument();
      expect(screen.queryByText('AI')).not.toBeInTheDocument();
    });

    it('should not show sources for user messages', () => {
      const sources: Source[] = [
        { title: 'Test Paper', paper_id: 'paper1' },
      ];

      render(
        <ChatMessage role="user" content="Hello" sources={sources} />
      );

      expect(screen.queryByText('Sources:')).not.toBeInTheDocument();
    });
  });

  describe('assistant message', () => {
    it('should render assistant message', () => {
      render(
        <ChatMessage role="assistant" content="I am doing well, thank you!" />
      );

      expect(screen.getByText('I am doing well, thank you!')).toBeInTheDocument();
      expect(screen.getByText('AI')).toBeInTheDocument();
      expect(screen.queryByText('U')).not.toBeInTheDocument();
    });

    it('should render assistant message with sources', () => {
      const sources: Source[] = [
        { title: 'Paper 1', paper_id: 'paper1' },
        { title: 'Paper 2', paper_id: 'paper2' },
      ];

      render(
        <ChatMessage
          role="assistant"
          content="Here is the answer"
          sources={sources}
        />
      );

      expect(screen.getByText('Here is the answer')).toBeInTheDocument();
      expect(screen.getByText('Sources:')).toBeInTheDocument();
      expect(screen.getByText('Paper 1')).toBeInTheDocument();
      expect(screen.getByText('Paper 2')).toBeInTheDocument();
    });

    it('should display paper_id when title is missing', () => {
      const sources: Source[] = [{ paper_id: 'paper123' }];

      render(
        <ChatMessage
          role="assistant"
          content="Answer"
          sources={sources}
        />
      );

      expect(screen.getByText('paper123')).toBeInTheDocument();
    });

    it('should display streaming indicator when isStreaming is true', () => {
      render(
        <ChatMessage
          role="assistant"
          content="Streaming answer"
          isStreaming={true}
        />
      );

      const streamingIndicator = screen.getByText('Streaming answer').parentElement;
      expect(streamingIndicator).toBeInTheDocument();
    });

    it('should not display streaming indicator when isStreaming is false', () => {
      render(
        <ChatMessage
          role="assistant"
          content="Complete answer"
          isStreaming={false}
        />
      );

      expect(screen.getByText('Complete answer')).toBeInTheDocument();
    });
  });
});
