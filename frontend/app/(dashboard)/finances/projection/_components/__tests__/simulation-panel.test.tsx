import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SimulationPanel } from '../simulation-panel';

function renderPanel() {
  const onSimulate = vi.fn();
  render(<SimulationPanel onSimulate={onSimulate} isPending={false} />);
  return {
    onSimulate,
    value: screen.getByPlaceholderText('0,00'),
    months: screen.getByPlaceholderText('todos os meses futuros'),
    add: screen.getByRole('button', { name: /Adicionar cenário/i }),
  };
}

describe('SimulationPanel', () => {
  it('adds a scenario with no months window when months is empty', () => {
    const { onSimulate, value, add } = renderPanel();
    fireEvent.change(value, { target: { value: '100' } });
    fireEvent.click(add);
    expect(onSimulate).toHaveBeenCalledTimes(1);
    expect(onSimulate.mock.calls[0]?.[0]).toEqual([{ type: 'add_expense', amount: '100' }]);
  });

  it('accepts a positive integer months window', () => {
    const { onSimulate, value, months, add } = renderPanel();
    fireEvent.change(value, { target: { value: '100' } });
    fireEvent.change(months, { target: { value: '2' } });
    fireEvent.click(add);
    expect(onSimulate.mock.calls[0]?.[0]).toEqual([
      { type: 'add_expense', amount: '100', months: 2 },
    ]);
  });

  it('rejects a decimal months window (avoids a silent backend 400)', () => {
    const { onSimulate, value, months, add } = renderPanel();
    fireEvent.change(value, { target: { value: '100' } });
    fireEvent.change(months, { target: { value: '2.5' } });
    fireEvent.click(add);
    expect(onSimulate).not.toHaveBeenCalled();
  });

  it('rejects a zero months window (would silently apply to no month)', () => {
    const { onSimulate, value, months, add } = renderPanel();
    fireEvent.change(value, { target: { value: '100' } });
    fireEvent.change(months, { target: { value: '0' } });
    fireEvent.click(add);
    expect(onSimulate).not.toHaveBeenCalled();
  });

  it('rejects a zero value (no-op scenario)', () => {
    const { onSimulate, value, add } = renderPanel();
    fireEvent.change(value, { target: { value: '0' } });
    fireEvent.click(add);
    expect(onSimulate).not.toHaveBeenCalled();
  });
});
