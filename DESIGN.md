---
name: NeuroVision Clinical Intelligence
colors:
  surface: '#16121b'
  surface-dim: '#16121b'
  surface-bright: '#3c3741'
  surface-container-lowest: '#100d15'
  surface-container-low: '#1e1a23'
  surface-container: '#221e27'
  surface-container-high: '#2d2832'
  surface-container-highest: '#38333d'
  on-surface: '#e8dfed'
  on-surface-variant: '#cbc3d7'
  inverse-surface: '#e8dfed'
  inverse-on-surface: '#332e38'
  outline: '#958ea0'
  outline-variant: '#494454'
  surface-tint: '#d0bcff'
  primary: '#d0bcff'
  on-primary: '#3c0091'
  primary-container: '#a078ff'
  on-primary-container: '#340080'
  inverse-primary: '#6d3bd7'
  secondary: '#44e2cd'
  on-secondary: '#003731'
  secondary-container: '#03c6b2'
  on-secondary-container: '#004d44'
  tertiary: '#ffafd3'
  on-tertiary: '#620040'
  tertiary-container: '#e364a7'
  on-tertiary-container: '#560038'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e9ddff'
  primary-fixed-dim: '#d0bcff'
  on-primary-fixed: '#23005c'
  on-primary-fixed-variant: '#5516be'
  secondary-fixed: '#62fae3'
  secondary-fixed-dim: '#3cddc7'
  on-secondary-fixed: '#00201c'
  on-secondary-fixed-variant: '#005047'
  tertiary-fixed: '#ffd8e7'
  tertiary-fixed-dim: '#ffafd3'
  on-tertiary-fixed: '#3d0026'
  on-tertiary-fixed-variant: '#85145a'
  background: '#16121b'
  on-background: '#e8dfed'
  surface-variant: '#38333d'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1440px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

This design system is engineered for high-stakes neurological analysis, merging clinical rigor with cutting-edge computational intelligence. The aesthetic is a fusion of **Corporate Modern** and **Minimalism**, utilizing a deep-space canvas to reduce eye fatigue during longitudinal data reviews. 

The brand personality is authoritative, precise, and visionary. It avoids the sterile coldness of traditional medical software by introducing a "Graphite Plum" foundation—a warm, dark neutral that feels sophisticated rather than industrial. The emotional response is one of "calm mastery": providing clinicians with a sense of clarity and control over complex neural datasets. Visual priority is always given to the data (EEG maps, risk gauges, and metrics), with the UI acting as a silent, high-performance conduit for insight.

## Colors

The palette is optimized for a high-contrast dark mode environment. 

- **The Base (Graphite Plum):** Used for the primary canvas. It provides a warm, deep substrate that prevents the "harshness" of pure black.
- **Surface Tiers:** Use #25202B for primary cards and #2D2736 for sidebars or nested panels to create a clear structural hierarchy without relying on heavy borders.
- **Neural Violet (Primary Interaction):** Reserved for primary actions, focus states, and active neural pathways. It signifies "Human Interaction."
- **Clinical Teal (Intelligence/Data):** Used for AI-generated insights, data points, and successful system computations. It signifies "Machine Intelligence."
- **Semantic Colors:** Use a "muted-vibrant" approach for status indicators to ensure they stand out against the dark plum background without blooming.

## Typography

This design system utilizes a dual-font strategy to distinguish between qualitative interfaces and quantitative data.

- **Inter (Primary UI):** Used for all structural elements, navigation, and headers. Its neutral, systematic nature ensures maximum legibility and a professional tone.
- **JetBrains Mono (Data & Metadata):** Used for all numerical values, timestamps, EEG coordinates, and system logs. The monospaced nature allows for vertical alignment in data grids and emphasizes the "technical intelligence" of the platform.

**Scale Philosophy:** High contrast between display headers and body text. Use `label-sm` in all-caps for section headers and technical categories to evoke a laboratory instrument feel.

## Layout & Spacing

The layout follows a **Fixed Grid** philosophy for dashboard views to maintain the integrity of complex data visualizations, while adopting a **Fluid Grid** for document-heavy analytical reports.

- **Grid:** A 12-column system with a 24px gutter. On desktop, sidebars are fixed at 280px, while the main stage expands.
- **Spacing Rhythm:** Based on an 8px base unit. Use generous `stack-lg` (32px) padding within primary hero cards to create a "premium" feel.
- **Mobile Adaption:** For tablets and mobile, 12 columns collapse to 4. Data grids should implement horizontal scrolling with "pinned" first columns (e.g., Patient ID) to maintain clinical context.

## Elevation & Depth

Depth is achieved through **Tonal Layering** rather than traditional drop shadows. This preserves the "clinical" flatness while providing necessary visual hierarchy.

- **Level 0 (Base):** #1A161F (Canvas).
- **Level 1 (Cards):** #25202B. Used for the main content containers.
- **Level 2 (Nested/Interaction):** #2D2736. Used for flyout menus, tooltips, and inner card sections.
- **Accents:** Use a subtle 1px inner border (opacity 10% white) on Level 1 cards to define edges against the dark background. 
- **Active State:** A 2px solid stroke of "Neural Violet" (#8B5CF6) is used to indicate the current focused element or active data stream.

## Shapes

The shape language is **Soft (0.25rem)**. This provides a professional, precise edge that feels engineered rather than "bubbly."

- **Standard Elements:** Buttons, inputs, and small widgets use a 4px (0.25rem) radius.
- **Containers:** Large hero cards and main dashboard panels use an 8px (0.5rem) radius.
- **Data Points:** Circular elements (like nodes in a head map) should be perfect circles to contrast against the rectangular grid of the UI.

## Components

### Buttons & Inputs
- **Primary Action:** Solid "Neural Violet" with white text. 4px radius.
- **Secondary/Ghost:** "Clinical Teal" outline with 10% teal fill on hover.
- **Inputs:** Background set to `Nested Graphite Plum`, with `JetBrains Mono` text for data entry. Focus state uses a Clinical Teal 1px border.

### Data Visualizations
- **Risk Gauges:** Semicircular stroke with a thickness of 12px. The stroke color transitions through the status colors (Green to Red) based on value. Use a needle or a large centered `JetBrains Mono` percentage.
- **EEG Head Maps:** A stylized 10-20 system silhouette in `Elevated Graphite Plum`. Nodes should glow with `Clinical Teal` or `Neural Violet` based on activity intensity.
- **Contribution Charts:** Horizontal bar stacks with 2px gaps between segments to maintain the "digital/technical" aesthetic.

### Cards & Lists
- **Hero Cards:** Large containers with `stack-lg` padding. Titles in `Inter` Bold, metadata in `JetBrains Mono` at the bottom right.
- **Data Grids:** Monospaced rows with zebra-striping (using #2D2736 for alternate rows). No vertical borders; use subtle horizontal dividers.

### Chips
- Used for "Tags" or "Active Filters." Rectangular with a 2px radius. Use low-saturation versions of status colors with high-saturation text to ensure legibility.