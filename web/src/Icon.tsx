import type { CSSProperties } from 'react';

const paths = {
  arrow: 'M5 12h14M13 6l6 6-6 6',
  arrowUp: 'M6 18 18 6M6 6h12v12',
  search: 'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  ticket: 'M3 7h18v4a2 2 0 0 0 0 4v3H3v-3a2 2 0 0 0 0-4V7ZM15 7v2m0 3v2m0 3v1',
  compass: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM16 8l-3 5-5 3 3-5 5-3Z',
  grid: 'M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z',
  list: 'M9 6h12M9 12h12M9 18h12M3 6h1m-1 6h1m-1 6h1',
  sun: 'M12 3V1m0 22v-2M3 12H1m22 0h-2M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0',
  moon: 'M21 14.5A9 9 0 0 1 9.5 3 9 9 0 1 0 21 14.5Z',
  close: 'M6 6l12 12M6 18 18 6',
  menu: 'M3 6h18M3 12h18M3 18h18',
  pin: 'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  calendar: 'M4 5h16v16H4V5ZM4 10h16M8 2v5m8-5v5M8 14h2m4 0h2m-8 4h2',
  check: 'M5 12l4 4L19 6',
  heart: 'M20.5 4.6a5.5 5.5 0 0 0-8.5.7 5.5 5.5 0 0 0-8.5-.7C-1 9.1 5 15 12 21c7-6 13-11.9 8.5-16.4Z',
  sparkle: 'm12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z',
  shield: 'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6l-9-4ZM8 12l3 3 5-6',
  clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM12 6v6l4 2',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  chart: 'M4 3v18h17M8 16v-4m5 4V7m5 9v-6',
  scan: 'M3 8V3h5m8 0h5v5M3 16v5h5m8 0h5v-5M5 12h14',
  music: 'M9 18V5l12-2v13M9 5v4l12-2M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm12-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  chevron: 'm9 5 7 7-7 7',
} as const;
export type IconName = keyof typeof paths;
export function Icon({ name, size = 20, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg className="icon" aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={style}><path d={paths[name]} /></svg>;
}
