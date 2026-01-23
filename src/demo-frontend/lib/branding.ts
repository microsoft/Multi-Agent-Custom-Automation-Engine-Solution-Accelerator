/**
 * Dynamic branding utilities for personalized demo sites
 *
 * Handles brand color extraction, logo management, and CSS variable injection
 * for per-prospect demo deployments.
 */

/** Branding configuration for a demo site */
export interface BrandingConfig {
  /** Business name displayed in header and page title */
  businessName: string;
  /** Primary brand color (hex) */
  primaryColor: string;
  /** Secondary/accent color (hex) */
  secondaryColor?: string;
  /** Accent color for highlights (hex) */
  accentColor?: string;
  /** URL to business logo (optional) */
  logoUrl?: string;
  /** Business tagline or slogan */
  tagline?: string;
  /** Industry type for default styling */
  industry?: string;
  /** Contact phone number */
  phone?: string;
  /** Business address */
  address?: string;
  /** Business website */
  website?: string;
}

/** CSS variable names for branding */
export const BRANDING_CSS_VARS = {
  primaryColor: '--color-primary',
  primaryDarkColor: '--color-primary-dark',
  secondaryColor: '--color-secondary',
  accentColor: '--color-accent',
} as const;

/** Default branding configuration */
export const DEFAULT_BRANDING: BrandingConfig = {
  businessName: 'Demo Business',
  primaryColor: '#2563eb', // Blue-600
  secondaryColor: '#64748b', // Slate-500
  accentColor: '#10b981', // Emerald-500
  tagline: 'Your AI Appointment Assistant',
  industry: 'general',
};

/** Industry-specific default colors */
export const INDUSTRY_COLORS: Record<string, Partial<BrandingConfig>> = {
  dentist: {
    primaryColor: '#0891b2', // Cyan-600
    secondaryColor: '#0e7490', // Cyan-700
    accentColor: '#06b6d4', // Cyan-500
  },
  hvac: {
    primaryColor: '#ea580c', // Orange-600
    secondaryColor: '#c2410c', // Orange-700
    accentColor: '#f97316', // Orange-500
  },
  salon: {
    primaryColor: '#db2777', // Pink-600
    secondaryColor: '#be185d', // Pink-700
    accentColor: '#ec4899', // Pink-500
  },
  auto: {
    primaryColor: '#dc2626', // Red-600
    secondaryColor: '#b91c1c', // Red-700
    accentColor: '#ef4444', // Red-500
  },
  medical: {
    primaryColor: '#2563eb', // Blue-600
    secondaryColor: '#1d4ed8', // Blue-700
    accentColor: '#3b82f6', // Blue-500
  },
  legal: {
    primaryColor: '#4f46e5', // Indigo-600
    secondaryColor: '#4338ca', // Indigo-700
    accentColor: '#6366f1', // Indigo-500
  },
  restaurant: {
    primaryColor: '#ca8a04', // Yellow-600
    secondaryColor: '#a16207', // Yellow-700
    accentColor: '#eab308', // Yellow-500
  },
  fitness: {
    primaryColor: '#16a34a', // Green-600
    secondaryColor: '#15803d', // Green-700
    accentColor: '#22c55e', // Green-500
  },
  general: {
    primaryColor: '#2563eb',
    secondaryColor: '#64748b',
    accentColor: '#10b981',
  },
};

/**
 * Darken a hex color by a percentage
 */
export function darkenColor(hex: string, percent: number = 15): string {
  // Remove # if present
  const cleanHex = hex.replace('#', '');

  // Parse RGB values
  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);

  // Darken
  const factor = (100 - percent) / 100;
  const newR = Math.round(r * factor);
  const newG = Math.round(g * factor);
  const newB = Math.round(b * factor);

  // Convert back to hex
  const toHex = (n: number) => n.toString(16).padStart(2, '0');
  return `#${toHex(newR)}${toHex(newG)}${toHex(newB)}`;
}

/**
 * Lighten a hex color by a percentage
 */
export function lightenColor(hex: string, percent: number = 15): string {
  const cleanHex = hex.replace('#', '');

  const r = parseInt(cleanHex.substring(0, 2), 16);
  const g = parseInt(cleanHex.substring(2, 4), 16);
  const b = parseInt(cleanHex.substring(4, 6), 16);

  const factor = percent / 100;
  const newR = Math.round(r + (255 - r) * factor);
  const newG = Math.round(g + (255 - g) * factor);
  const newB = Math.round(b + (255 - b) * factor);

  const toHex = (n: number) => n.toString(16).padStart(2, '0');
  return `#${toHex(newR)}${toHex(newG)}${toHex(newB)}`;
}

/**
 * Convert hex color to RGB components
 */
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

/**
 * Calculate relative luminance of a color for contrast calculations
 */
export function getLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0;

  const [r, g, b] = [rgb.r, rgb.g, rgb.b].map((c) => {
    const sRGB = c / 255;
    return sRGB <= 0.03928
      ? sRGB / 12.92
      : Math.pow((sRGB + 0.055) / 1.055, 2.4);
  });

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Determine if text should be light or dark based on background color
 */
export function getContrastTextColor(backgroundColor: string): 'white' | 'black' {
  const luminance = getLuminance(backgroundColor);
  return luminance > 0.179 ? 'black' : 'white';
}

/**
 * Get branding config from environment variables
 * Environment variables are injected during Vercel deployment
 */
export function getBrandingFromEnv(): BrandingConfig {
  // Check for environment variables (NEXT_PUBLIC_ prefix for client-side access)
  const env = {
    businessName: process.env.NEXT_PUBLIC_BUSINESS_NAME,
    primaryColor: process.env.NEXT_PUBLIC_PRIMARY_COLOR,
    secondaryColor: process.env.NEXT_PUBLIC_SECONDARY_COLOR,
    accentColor: process.env.NEXT_PUBLIC_ACCENT_COLOR,
    logoUrl: process.env.NEXT_PUBLIC_LOGO_URL,
    tagline: process.env.NEXT_PUBLIC_TAGLINE,
    industry: process.env.NEXT_PUBLIC_INDUSTRY,
    phone: process.env.NEXT_PUBLIC_PHONE,
    address: process.env.NEXT_PUBLIC_ADDRESS,
    website: process.env.NEXT_PUBLIC_WEBSITE,
  };

  // Get industry-specific defaults if industry is specified
  const industry = env.industry || 'general';
  const industryDefaults = INDUSTRY_COLORS[industry] || INDUSTRY_COLORS.general;

  return {
    businessName: env.businessName || DEFAULT_BRANDING.businessName,
    primaryColor: env.primaryColor || industryDefaults.primaryColor || DEFAULT_BRANDING.primaryColor,
    secondaryColor: env.secondaryColor || industryDefaults.secondaryColor || DEFAULT_BRANDING.secondaryColor,
    accentColor: env.accentColor || industryDefaults.accentColor || DEFAULT_BRANDING.accentColor,
    logoUrl: env.logoUrl,
    tagline: env.tagline || DEFAULT_BRANDING.tagline,
    industry,
    phone: env.phone,
    address: env.address,
    website: env.website,
  };
}

/**
 * Generate CSS variables string for branding injection
 */
export function generateBrandingCSSVars(config: BrandingConfig): string {
  const primaryDark = darkenColor(config.primaryColor, 15);

  return `
    ${BRANDING_CSS_VARS.primaryColor}: ${config.primaryColor};
    ${BRANDING_CSS_VARS.primaryDarkColor}: ${primaryDark};
    ${BRANDING_CSS_VARS.secondaryColor}: ${config.secondaryColor || DEFAULT_BRANDING.secondaryColor};
    ${BRANDING_CSS_VARS.accentColor}: ${config.accentColor || DEFAULT_BRANDING.accentColor};
  `.trim();
}

/**
 * Generate inline style object for branding CSS variables
 */
export function getBrandingStyleVars(config: BrandingConfig): Record<string, string> {
  const primaryDark = darkenColor(config.primaryColor, 15);

  return {
    [BRANDING_CSS_VARS.primaryColor]: config.primaryColor,
    [BRANDING_CSS_VARS.primaryDarkColor]: primaryDark,
    [BRANDING_CSS_VARS.secondaryColor]: config.secondaryColor || DEFAULT_BRANDING.secondaryColor!,
    [BRANDING_CSS_VARS.accentColor]: config.accentColor || DEFAULT_BRANDING.accentColor!,
  };
}

/**
 * Validate branding configuration
 */
export function validateBrandingConfig(config: Partial<BrandingConfig>): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Validate required fields
  if (!config.businessName || config.businessName.trim() === '') {
    errors.push('Business name is required');
  }

  // Validate color formats
  const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;

  if (config.primaryColor && !hexColorRegex.test(config.primaryColor)) {
    errors.push('Primary color must be a valid hex color (e.g., #2563eb)');
  }

  if (config.secondaryColor && !hexColorRegex.test(config.secondaryColor)) {
    errors.push('Secondary color must be a valid hex color (e.g., #64748b)');
  }

  if (config.accentColor && !hexColorRegex.test(config.accentColor)) {
    errors.push('Accent color must be a valid hex color (e.g., #10b981)');
  }

  // Validate URL format for logo
  if (config.logoUrl) {
    try {
      new URL(config.logoUrl);
    } catch {
      errors.push('Logo URL must be a valid URL');
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Merge partial branding config with defaults
 */
export function mergeBrandingConfig(partial: Partial<BrandingConfig>): BrandingConfig {
  const industry = partial.industry || 'general';
  const industryDefaults = INDUSTRY_COLORS[industry] || INDUSTRY_COLORS.general;

  return {
    ...DEFAULT_BRANDING,
    ...industryDefaults,
    ...partial,
    businessName: partial.businessName || DEFAULT_BRANDING.businessName,
    primaryColor: partial.primaryColor || industryDefaults.primaryColor || DEFAULT_BRANDING.primaryColor,
  };
}

/**
 * Extract dominant color from an image URL (placeholder - would need server-side processing)
 * For now, returns a fallback color based on industry
 */
export function extractDominantColor(imageUrl: string, industry?: string): string {
  // In a real implementation, this would use a color extraction library
  // For now, return industry-specific default or primary blue
  if (industry && INDUSTRY_COLORS[industry]) {
    return INDUSTRY_COLORS[industry].primaryColor || DEFAULT_BRANDING.primaryColor;
  }
  return DEFAULT_BRANDING.primaryColor;
}
