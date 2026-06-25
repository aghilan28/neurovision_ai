---
name: NeuroVision Intelligence
colors:
  surface: '#141218'
  surface-dim: '#141218'
  surface-bright: '#3b383e'
  surface-container-lowest: '#0f0d13'
  surface-container-low: '#1d1b20'
  surface-container: '#211f24'
  surface-container-high: '#2b292f'
  surface-container-highest: '#36343a'
  on-surface: '#e6e0e9'
  on-surface-variant: '#cbc4d2'
  inverse-surface: '#e6e0e9'
  inverse-on-surface: '#322f35'
  outline: '#948e9c'
  outline-variant: '#494551'
  surface-tint: '#cfbcff'
  primary: '#cfbcff'
  on-primary: '#381e72'
  primary-container: '#6750a4'
  on-primary-container: '#e0d2ff'
  inverse-primary: '#6750a4'
  secondary: '#cdc0e9'
  on-secondary: '#342b4b'
  secondary-container: '#4d4465'
  on-secondary-container: '#bfb2da'
  tertiary: '#e7c365'
  on-tertiary: '#3e2e00'
  tertiary-container: '#c9a74d'
  on-tertiary-container: '#503d00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e9ddff'
  primary-fixed-dim: '#cfbcff'
  on-primary-fixed: '#22005d'
  on-primary-fixed-variant: '#4f378a'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#cdc0e9'
  on-secondary-fixed: '#1f1635'
  on-secondary-fixed-variant: '#4b4263'
  tertiary-fixed: '#ffdf93'
  tertiary-fixed-dim: '#e7c365'
  on-tertiary-fixed: '#241a00'
  on-tertiary-fixed-variant: '#594400'
  background: '#141218'
  on-background: '#e6e0e9'
  surface-variant: '#36343a'
typography:
  display-lg:
    fontFamily: Playfair Display
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Playfair Display
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-sm:
    fontFamily: Playfair Display
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  body-lg:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  data-label:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-metric:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  section-gap: 48px
---

## Brand & Style

The design system is engineered for a premium neurological intelligence platform, merging the sterile precision of a clinical research facility with the sophisticated fluidity of high-end artificial intelligence. The aesthetic is "Clinical Noir"—a dark, focused environment that minimizes cognitive load while signaling authority and high-value data processing.

The style is a hybrid of **Modern Minimalism** and **Refined Glassmorphism**. It utilizes deep, warm-toned dark surfaces to reduce eye strain during long-form research sessions. The interface feels "expensive" through the use of expansive whitespace (despite the dark theme), razor-thin borders, and subtle, purposeful motion. Every pixel serves a diagnostic purpose; decorative elements are stripped away in favor of functional elegance and data-driven clarity.

## Colors

The palette is rooted in **Deep Graphite Plum**, providing a warmer, more sophisticated alternative to pure black or neutral grey. This choice reduces the "harshness" of the UI while maintaining a serious, scientific atmosphere.

- **Foundational Neutrals:** Backgrounds utilize the deepest plum tones to create a sense of infinite depth. Surfaces are layered using slightly lighter values to denote hierarchy and modularity.
- **Neural Violet (Brand Accent):** Reserved exclusively for human interaction. It denotes where the user can click, select, or modify parameters. It should be used sparingly to maintain its impact.
- **Clinical Teal (Data Accent):** Reserved strictly for machine intelligence outputs, EEG wave patterns, and neural signal data. This separation ensures the user instinctively distinguishes between "system controls" and "biological data."
- **Functional States:** Success, Warning, and Critical colors follow standard clinical conventions but are desaturated slightly to harmonize with the deep plum background.

## Typography

The typographic hierarchy utilizes three distinct families to categorize information types:

1.  **Editorial Serif (Playfair Display):** Used for primary headlines and section titles. It evokes the prestige of scientific journals and academic excellence.
2.  **Modern Sans-Serif (Geist):** The workhorse of the interface. Selected for its technical, geometric precision and high legibility at small sizes. Used for all UI controls, labels, and descriptive text.
3.  **Monospaced (JetBrains Mono):** Used for all quantitative data, coordinates, timestamps, and raw neural telemetry. This ensures that columns of numbers remain aligned for easy scanning and clinical comparison.

On mobile devices, `display-lg` should scale down to 32px to ensure readability without excessive wrapping.

## Layout & Spacing

The design system employs a **12-column fluid grid** for desktop, transitioning to a **4-column grid** for mobile devices. The spacing philosophy is rooted in a 4px baseline grid to ensure mathematical precision in element alignment.

- **Margins:** Desktop views should maintain a minimum outer margin of 32px to provide "breathing room" for complex data visualizations.
- **Modularity:** Information is grouped into cards. Large-scale data visualizations (Brain Maps, EEG Streams) should occupy at least 8 columns to prioritize clinical detail.
- **Density:** While the overall atmosphere is spacious, data tables and technical panels use a "Compact" density model to maximize information density for expert users.

## Elevation & Depth

Depth in this design system is achieved through **Tonal Layering** and **Glassmorphism**, rather than traditional drop shadows.

- **Surfaces:** Each elevation level is represented by a specific hex value (Base > Surface > Nested). 
- **Glass Effects:** Overlays, modals, and dropdown menus utilize a subtle backdrop blur (12px to 20px) with a semi-transparent border (0.5px white at 10% opacity) to simulate high-end glass hardware.
- **Borders:** Instead of shadows, use 1px solid borders using the `Nested Surface` color or a low-opacity white to define edges.
- **Hover States:** Elements do not "lift" (move up); instead, they emit a soft **Neural Violet** inner glow or a subtle outer bloom to indicate interactivity.

## Shapes

The shape language is disciplined and professional. 

- **Primary Radius:** A consistent 4px (Soft) radius is used for buttons, input fields, and small UI components. This provides a modern feel without appearing "playful."
- **Container Radius:** Larger panels and cards use an 8px (rounded-lg) radius to distinguish structural containers from interactive elements.
- **Interactive Elements:** Checkboxes and radio buttons maintain sharp/slightly softened corners (2px) to reflect the precision of clinical instrumentation.

## Components

- **Buttons:** 
  - *Primary:* Solid Neural Violet with white text. 
  - *Secondary:* Ghost style with a 1px Violet border. 
  - *Hover:* Add a subtle 10px violet outer glow (bloom).
- **Cards:** Use `Primary Surface` background with a 1px border of `Nested Surface`. No shadows. High-data cards use `Nested Surface` for headers to create internal hierarchy.
- **Inputs:** Darker than the surface they sit on. Active state indicated by a Clinical Teal or Neural Violet bottom border (2px).
- **Chips/Badges:** Monospaced text. For data status (e.g., "Active Signal"), use a Clinical Teal background at 15% opacity with solid Teal text.
- **EEG/Data Streams:** Rendered in Clinical Teal. Lines should be thin (1px to 1.5px) with no smoothing to maintain "raw signal" integrity.
- **Lists:** Clean rows separated by 1px `Nested Surface` dividers. Hovering a row changes the background to a slightly lighter plum.