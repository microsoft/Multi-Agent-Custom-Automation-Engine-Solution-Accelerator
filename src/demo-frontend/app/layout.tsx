import type { Metadata, Viewport } from 'next';
import {
  getBrandingFromEnv,
  getBrandingStyleVars,
  getContrastTextColor,
} from '@/lib/branding';
import './globals.css';

/**
 * Get branding configuration at build time
 * This runs on the server during static generation
 */
function getBranding() {
  return getBrandingFromEnv();
}

/**
 * Generate dynamic metadata based on branding
 */
export async function generateMetadata(): Promise<Metadata> {
  const branding = getBranding();

  return {
    title: {
      default: `${branding.businessName} - AI Appointment Assistant`,
      template: `%s | ${branding.businessName}`,
    },
    description:
      branding.tagline ||
      `${branding.businessName}'s intelligent appointment scheduling powered by AI`,
    keywords: [
      branding.businessName,
      'appointment scheduling',
      'AI assistant',
      branding.industry || 'business',
      'booking',
      'receptionist',
    ],
    authors: [{ name: branding.businessName }],
    creator: branding.businessName,
    publisher: branding.businessName,
    robots: {
      index: true,
      follow: true,
    },
    openGraph: {
      type: 'website',
      locale: 'en_US',
      siteName: branding.businessName,
      title: `${branding.businessName} - AI Appointment Assistant`,
      description:
        branding.tagline ||
        `${branding.businessName}'s intelligent appointment scheduling powered by AI`,
    },
    twitter: {
      card: 'summary_large_image',
      title: `${branding.businessName} - AI Appointment Assistant`,
      description:
        branding.tagline ||
        `${branding.businessName}'s intelligent appointment scheduling powered by AI`,
    },
  };
}

/**
 * Viewport configuration
 */
export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#2563eb', // Will be overridden by branding if needed
};

/**
 * Root layout component with dynamic branding injection
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const branding = getBranding();
  const brandingStyles = getBrandingStyleVars(branding);
  const textColor = getContrastTextColor(branding.primaryColor);

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preconnect to external resources */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />

        {/* Inter font for clean typography */}
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />

        {/* Favicon - can be customized per prospect */}
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />

        {/* Dynamic theme color based on branding */}
        <meta name="theme-color" content={branding.primaryColor} />
      </head>

      <body
        className="min-h-screen bg-background text-foreground antialiased"
        style={brandingStyles as React.CSSProperties}
      >
        {/* Skip to content link for accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-brand focus:text-white"
        >
          Skip to main content
        </a>

        {/* Header with dynamic branding */}
        <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container mx-auto flex h-16 items-center justify-between px-4">
            {/* Logo and business name */}
            <div className="flex items-center gap-3">
              {branding.logoUrl ? (
                <img
                  src={branding.logoUrl}
                  alt={`${branding.businessName} logo`}
                  className="h-8 w-auto object-contain"
                  loading="eager"
                />
              ) : (
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-lg font-bold text-lg"
                  style={{
                    backgroundColor: branding.primaryColor,
                    color: textColor,
                  }}
                >
                  {branding.businessName.charAt(0).toUpperCase()}
                </div>
              )}
              <div className="flex flex-col">
                <span className="font-semibold text-lg leading-tight">
                  {branding.businessName}
                </span>
                {branding.tagline && (
                  <span className="text-xs text-muted-foreground hidden sm:block">
                    {branding.tagline}
                  </span>
                )}
              </div>
            </div>

            {/* Contact info (optional) */}
            {branding.phone && (
              <a
                href={`tel:${branding.phone}`}
                className="hidden md:flex items-center gap-2 text-sm text-muted-foreground hover:text-brand transition-colors"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                </svg>
                <span>{branding.phone}</span>
              </a>
            )}
          </div>
        </header>

        {/* Main content area */}
        <main id="main-content" className="flex-1">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-border bg-muted/50">
          <div className="container mx-auto px-4 py-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              {/* Business info */}
              <div className="flex flex-col items-center md:items-start gap-1 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">
                  {branding.businessName}
                </span>
                {branding.address && <span>{branding.address}</span>}
                {branding.phone && (
                  <a
                    href={`tel:${branding.phone}`}
                    className="hover:text-brand transition-colors"
                  >
                    {branding.phone}
                  </a>
                )}
                {branding.website && (
                  <a
                    href={branding.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-brand transition-colors"
                  >
                    Visit Website
                  </a>
                )}
              </div>

              {/* AI Assistant badge */}
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 8V4H8" />
                  <rect width="16" height="12" x="4" y="8" rx="2" />
                  <path d="M2 14h2" />
                  <path d="M20 14h2" />
                  <path d="M15 13v2" />
                  <path d="M9 13v2" />
                </svg>
                <span>Powered by AI Appointment Assistant</span>
              </div>
            </div>

            {/* Copyright */}
            <div className="mt-6 pt-6 border-t border-border text-center text-xs text-muted-foreground">
              <p>
                &copy; {new Date().getFullYear()} {branding.businessName}. All
                rights reserved.
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
