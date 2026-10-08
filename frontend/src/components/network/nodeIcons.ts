// Node glyphs from lucide-static (ISC). Imported one file at a time so only these icons ship.
import building2 from "lucide-static/icons/building-2.svg?raw";
import landmark from "lucide-static/icons/landmark.svg?raw";
import mapPin from "lucide-static/icons/map-pin.svg?raw";
import stethoscope from "lucide-static/icons/stethoscope.svg?raw";
import userRound from "lucide-static/icons/user-round.svg?raw";

const ICONS: Record<string, string> = {
  provider: stethoscope,
  owner: userRound,
  facility: building2,
  address: mapPin,
  bank: landmark,
};

/** Data-URI for a node type's glyph in the given colour, or undefined when the type has none. */
export function nodeIcon(type: string, color: string): string | undefined {
  const svg = ICONS[type];
  if (!svg) return undefined;
  const coloured = svg.replace(/<!--[\s\S]*?-->/, "").replaceAll("currentColor", color);
  return `data:image/svg+xml;utf8,${encodeURIComponent(coloured)}`;
}
