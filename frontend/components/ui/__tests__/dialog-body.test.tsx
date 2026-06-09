import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DialogBody } from '@/components/ui/dialog';

describe('DialogBody', () => {
  it('renders children inside a scrollable flex-1 region', () => {
    // DialogBody is the rolling area: it must carry `flex-1` (stretch in the
    // flex-col DialogContent) and `overflow-y-auto` (only the body scrolls).
    render(<DialogBody data-testid="body">conteúdo</DialogBody>);
    const body = screen.getByTestId('body');
    expect(body).toHaveTextContent('conteúdo');
    expect(body.className).toContain('flex-1');
    expect(body.className).toContain('overflow-y-auto');
  });

  it('merges a consumer className without dropping the base classes', () => {
    // cn() keeps flex-1/overflow-y-auto and appends the consumer spacing class.
    render(
      <DialogBody data-testid="body" className="space-y-4 pr-1">
        x
      </DialogBody>
    );
    const body = screen.getByTestId('body');
    expect(body.className).toContain('flex-1');
    expect(body.className).toContain('overflow-y-auto');
    expect(body.className).toContain('space-y-4');
  });

  it('forwards arbitrary div props (role) to the underlying element', () => {
    // It is a plain div primitive — extra HTML attributes pass straight through.
    render(
      <DialogBody role="group" aria-label="corpo">
        x
      </DialogBody>
    );
    expect(screen.getByRole('group', { name: 'corpo' })).toBeInTheDocument();
  });

  it('exposes a stable displayName for devtools/debugging', () => {
    // Mirrors DialogHeader/DialogFooter which set displayName explicitly.
    expect(DialogBody.displayName).toBe('DialogBody');
  });
});
