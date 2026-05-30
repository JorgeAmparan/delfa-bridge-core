import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DOCYAN LDE — by XCID",
  description: "Live Document Environment by XCID",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es-MX">
      <body>{children}</body>
    </html>
  );
}
