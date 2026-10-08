/** ClaimShield mark: a flat shield with a three-node link (decorative). */
export function AppLogo() {
  return (
    <svg className="app-logo" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M12 1.5 21 5v6.2c0 5.4-3.7 9.7-9 11.3-5.3-1.6-9-5.9-9-11.3V5Z" fill="var(--color-brand)" />
      <path
        d="M8 9.5 12 14l4-4.5M8 9.5h0M16 9.5h0"
        stroke="var(--color-text-on-brand)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="8" cy="9.5" r="1.6" fill="var(--color-text-on-brand)" />
      <circle cx="16" cy="9.5" r="1.6" fill="var(--color-text-on-brand)" />
      <circle cx="12" cy="14" r="1.6" fill="var(--color-text-on-brand)" />
    </svg>
  );
}
