import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinBot",
  description: "Internal assistant for FinSolve Technologies",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // Keep suppressHydrationWarning: browser extensions can inject html/body attrs pre-hydration.
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
