"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

  const linkClass = (href: string) => {
    const isActive =
      href === "/" ? pathname === "/" : pathname.startsWith(href);
    return `text-sm transition-colors ${
      isActive ? "text-white font-medium" : "text-gray-400 hover:text-white"
    }`;
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between border-b border-gray-800 bg-gray-900/80 px-6 py-3 backdrop-blur-md">
      <Link href="/" className="text-lg font-bold text-white">
        gestorIA
      </Link>

      <div className="flex items-center gap-6">
        <Link href="/" className={linkClass("/")}>
          Nueva consulta
        </Link>
        <Link href="/historial" className={linkClass("/historial")}>
          Historial
        </Link>
      </div>
    </nav>
  );
}
