import { describe, expect, it } from 'vitest';
import { startCountdown, type TickerElement } from './countdown';

function tickerEl(): TickerElement {
  return {
    dataset: {},
    textContent: null,
    setAttribute() {},
    removeAttribute() {},
    style: { strokeDashoffset: '' },
  };
}

describe('startCountdown', () => {
  it('schedules frames on globalThis when the document host has no requestAnimationFrame', () => {
    const dial = tickerEl();
    const progress = tickerEl();
    const scheduled: Array<() => void> = [];
    Object.assign(globalThis, {
      document: {
        getElementById(id: string) {
          if (id === 'status-dial') return dial;
          if (id === 'ticker-progress') return progress;
          return null;
        },
      },
      requestAnimationFrame(cb: () => void) {
        scheduled.push(cb);
        return 1;
      },
      cancelAnimationFrame() {},
      addEventListener() {},
    });
    expect(() => startCountdown()).not.toThrow();
    expect(scheduled).toHaveLength(1);
  });
});
