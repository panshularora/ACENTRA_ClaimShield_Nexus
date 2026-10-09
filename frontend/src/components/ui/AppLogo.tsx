const LOCKUP = "/brand/claimshield-nexus.jpg";
const MARK = "/brand/claimshield-mark.jpg";

interface AppLogoProps {
  /** Wide lockup with wordmark, or the shield alone. */
  variant?: "lockup" | "mark";
  className?: string;
}

/** Official ClaimShield Nexus art from the brand still. */
export function AppLogo({ variant = "lockup", className }: AppLogoProps) {
  const src = variant === "mark" ? MARK : LOCKUP;
  return (
    <img
      className={`brand-img brand-img-${variant}${className ? ` ${className}` : ""}`}
      src={src}
      alt="ClaimShield Nexus"
      width={variant === "mark" ? 40 : 280}
      height={40}
    />
  );
}
