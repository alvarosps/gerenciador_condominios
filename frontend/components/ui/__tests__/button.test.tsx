import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { Button, buttonVariants } from '@/components/ui/button';

describe('Button', () => {
  it('renders touch size with a >=44px touch target (h-11) and px-5', () => {
    renderWithProviders(<Button size="touch">Ação</Button>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('h-11');
    expect(button.className).toContain('px-5');
  });

  it('renders default size with h-10 and not the old h-9', () => {
    renderWithProviders(<Button>Padrão</Button>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('h-10');
    expect(button.className).not.toContain('h-9');
  });

  it('renders explicit default size with h-10', () => {
    renderWithProviders(<Button size="default">Padrão explícito</Button>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('h-10');
  });

  it('keeps the icon size at h-9 w-9', () => {
    renderWithProviders(<Button size="icon">+</Button>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('h-9');
    expect(button.className).toContain('w-9');
  });

  it('exposes touch size through buttonVariants directly', () => {
    expect(buttonVariants({ size: 'touch' })).toContain('h-11');
  });
});
