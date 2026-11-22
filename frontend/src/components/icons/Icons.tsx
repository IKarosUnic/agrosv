import React from "react";

type IconProps = { size?: number; className?: string };

const base = (size = 16): React.SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
});

export const IconHome = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" /></svg>
);

export const IconMap = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z" /><path d="M9 3v15M15 6v15" /></svg>
);

export const IconTerrain = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M3 20h18L14 7l-4 6-3-4z" /></svg>
);

export const IconLeaf = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10z" /><path d="M2 21c0-3 1.8-5.3 5-6" /></svg>
);

export const IconCalendar = ({ size }: IconProps) => (
  <svg {...base(size)}><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>
);

export const IconSatellite = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M13 7 9 3 5 7l4 4" /><path d="m17 11 4 4-4 4-4-4" /><path d="m8 12 4 4 6-6-4-4z" /><path d="M4 20a5 5 0 0 1 5-5" /></svg>
);

export const IconAlert = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></svg>
);

export const IconCoins = ({ size }: IconProps) => (
  <svg {...base(size)}><circle cx="9" cy="12" r="6" /><path d="M15 6a6 6 0 0 1 0 12" /><path d="M9 9v6M7.5 10.5h3a1 1 0 0 1 0 3h-3" /></svg>
);

export const IconFlask = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3" /></svg>
);

export const IconSearch = ({ size }: IconProps) => (
  <svg {...base(size)}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
);

export const IconCheck = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M20 6 9 17l-5-5" /></svg>
);

export const IconInfo = ({ size }: IconProps) => (
  <svg {...base(size)}><circle cx="12" cy="12" r="9" /><path d="M12 16v-4M12 8h.01" /></svg>
);

export const IconBan = ({ size }: IconProps) => (
  <svg {...base(size)}><circle cx="12" cy="12" r="9" /><path d="m5.6 5.6 12.8 12.8" /></svg>
);

export const IconWifiOff = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M2 2l20 20" /><path d="M8.5 16.5a5 5 0 0 1 7 0M5 12.6a10 10 0 0 1 5.2-2.6M15.8 10.4a10 10 0 0 1 3.2 2.2M12 20h.01" /></svg>
);

export const IconMenu = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M4 6h16M4 12h16M4 18h16" /></svg>
);

export const IconSun = ({ size }: IconProps) => (
  <svg {...base(size)}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
);

export const IconMoon = ({ size }: IconProps) => (
  <svg {...base(size)}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
);

export const IconHelp = ({ size }: IconProps) => (
  <svg {...base(size)}><circle cx="12" cy="12" r="9" /><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01" /></svg>
);
