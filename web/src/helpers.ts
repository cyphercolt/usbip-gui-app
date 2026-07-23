import { useEffect, useState } from "react";

export function osBadge(os: string): string {
  if (os.includes("win")) return "🪟";
  if (os.includes("linux")) return "🐧";
  if (os.includes("darwin") || os.includes("mac")) return "🍎";
  return "💻";
}

export function useFullscreen(): [boolean, () => void] {
  const [fs, setFs] = useState(!!document.fullscreenElement);
  useEffect(() => {
    const onChange = () => setFs(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);
  const toggle = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void document.documentElement.requestFullscreen().catch(() => {});
  };
  return [fs, toggle];
}
