import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TooltipProvider } from '@/components/ui/tooltip';
import { BillPaymentToggle } from '../bill-payment-toggle';

function renderToggle(props: Partial<React.ComponentProps<typeof BillPaymentToggle>> = {}) {
  const onPay = vi.fn();
  const result = render(
    <TooltipProvider>
      <BillPaymentToggle
        paymentStatus="open"
        isOverdue={false}
        lifecycleState="active"
        canPay
        isPending={false}
        onPay={onPay}
        {...props}
      />
    </TooltipProvider>,
  );
  return { onPay, unmount: result.unmount };
}

describe('BillPaymentToggle', () => {
  it('shows the switch checked when paid and unchecked when open/partial', () => {
    const { unmount } = render(
      <TooltipProvider>
        <BillPaymentToggle
          paymentStatus="paid"
          isOverdue={false}
          lifecycleState="active"
          canPay={false}
          isPending={false}
          onPay={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.getByRole('switch')).toBeChecked();
    unmount();

    renderToggle({ paymentStatus: 'partial' });
    expect(screen.getByRole('switch')).not.toBeChecked();
  });

  it('disables the switch when canPay is false, isPending is true, or already paid', () => {
    const { unmount } = renderToggle({ canPay: false });
    expect(screen.getByRole('switch')).toBeDisabled();
    unmount();

    renderToggle({ isPending: true });
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('calls onPay when toggled while enabled', async () => {
    const { onPay } = renderToggle();
    await userEvent.click(screen.getByRole('switch'));
    expect(onPay).toHaveBeenCalledTimes(1);
  });

  it('does not call onPay when disabled', async () => {
    const { onPay } = renderToggle({ canPay: false });
    await userEvent.click(screen.getByRole('switch'));
    expect(onPay).not.toHaveBeenCalled();
  });

  it('exposes the Portuguese disabledReason as the switch aria-label when disabled by lifecycle', () => {
    renderToggle({
      canPay: false,
      lifecycleState: 'suspended',
      disabledReason: 'Conta suspensa — reative para pagar',
    });
    expect(
      screen.getByRole('switch', { name: 'Conta suspensa — reative para pagar' }),
    ).toBeInTheDocument();
  });

  it('renders the status with a label (not color only)', () => {
    const { unmount } = renderToggle({ paymentStatus: 'paid' });
    expect(screen.getByText('Pago')).toBeInTheDocument();
    unmount();

    const partial = renderToggle({ paymentStatus: 'partial' });
    expect(screen.getByText('Parcial')).toBeInTheDocument();
    partial.unmount();

    const overdue = render(
      <TooltipProvider>
        <BillPaymentToggle
          paymentStatus="open"
          isOverdue
          lifecycleState="active"
          canPay
          isPending={false}
          onPay={vi.fn()}
        />
      </TooltipProvider>,
    );
    expect(screen.getByText('Em atraso')).toBeInTheDocument();
    overdue.unmount();

    renderToggle({ paymentStatus: 'open' });
    expect(screen.getByText('Em aberto')).toBeInTheDocument();
  });
});
