import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { RentPaymentToggle } from '../rent-payment-toggle';

describe('RentPaymentToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders a checked switch when isPaid is true', () => {
    render(
      <RentPaymentToggle isPaid canToggle isPending={false} onToggle={vi.fn()} />,
    );
    expect(screen.getByRole('switch')).toBeChecked();
  });

  it('renders an unchecked switch when isPaid is false', () => {
    render(
      <RentPaymentToggle isPaid={false} canToggle isPending={false} onToggle={vi.fn()} />,
    );
    expect(screen.getByRole('switch')).not.toBeChecked();
  });

  it('disables the switch when canToggle is false', () => {
    render(
      <RentPaymentToggle isPaid canToggle={false} isPending={false} onToggle={vi.fn()} />,
    );
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('disables the switch when isPending is true', () => {
    render(
      <RentPaymentToggle isPaid={false} canToggle isPending onToggle={vi.fn()} />,
    );
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('calls onToggle when clicked while enabled', () => {
    const onToggle = vi.fn();
    render(
      <RentPaymentToggle isPaid={false} canToggle isPending={false} onToggle={onToggle} />,
    );
    fireEvent.click(screen.getByRole('switch'));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('does not call onToggle when clicked while disabled', () => {
    const onToggle = vi.fn();
    render(
      <RentPaymentToggle isPaid canToggle={false} isPending={false} onToggle={onToggle} />,
    );
    fireEvent.click(screen.getByRole('switch'));
    expect(onToggle).not.toHaveBeenCalled();
  });

  it('exposes the disabled reason via aria-label when blocked by paid + day passed', () => {
    const reason = 'Pagamento confirmado — o dia já passou, não é possível desmarcar';
    render(
      <TooltipProvider>
        <RentPaymentToggle
          isPaid
          canToggle={false}
          isPending={false}
          onToggle={vi.fn()}
          disabledReason={reason}
        />
      </TooltipProvider>,
    );
    expect(screen.getByRole('switch')).toHaveAttribute('aria-label', reason);
  });
});
