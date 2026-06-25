---
name: NeuroVision Intelligence
colors:
  surface: '#15121b'
  surface-dim: '#15121b'
  surface-bright: '#3b3742'
  surface-container-lowest: '#0f0d15'
  surface-container-low: '#1d1a23'
  surface-container: '#211e27'
  surface-container-high: '#2c2832'
  surface-container-highest: '#37333d'
  on-surface: '#e7e0ed'
  on-surface-variant: '#cbc3d7'
  inverse-surface: '#e7e0ed'
  inverse-on-surface: '#322f39'
  outline: '#958ea0'
  outline-variant: '#494454'
  surface-tint: '#d0bcff'
  primary: '#d0bcff'
  on-primary: '#3c0091'
  primary-container: '#a078ff'
  on-primary-container: '#340080'
  inverse-primary: '#6d3bd7'
  secondary: '#4fdbc8'
  on-secondary: '#003731'
  secondary-container: '#04b4a2'
  on-secondary-container: '#003f38'
  tertiary: '#ffb869'
  on-tertiary: '#482900'
  tertiary-container: '#ca801e'
  on-tertiary-container: '#3f2300'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e9ddff'
  primary-fixed-dim: '#d0bcff'
  on-primary-fixed: '#23005c'
  on-primary-fixed-variant: '#5516be'
  secondary-fixed: '#71f8e4'
  secondary-fixed-dim: '#4fdbc8'
  on-secondary-fixed: '#00201c'
  on-secondary-fixed-variant: '#005048'
  tertiary-fixed: '#ffdcbb'
  tertiary-fixed-dim: '#ffb869'
  on-tertiary-fixed: '#2c1700'
  on-tertiary-fixed-variant: '#673d00'
  background: '#15121b'
  on-background: '#e7e0ed'
  surface-variant: '#37333d'
typography:
  display-xl:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: 0em
  sub-header:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.15em
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
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-page: 24px
  split-left: 45%
  split-right: 55%
---

## Brand & Style

The design system is engineered for high-stakes neurological analysis, blending the precision of aerospace interfaces with the clean, sophisticated aesthetic of cutting-edge AI research labs. The brand personality is authoritative yet calm, designed to instill confidence in clinicians and researchers handling complex data.

The style is **Modern Enterprise with a High-Density Data Focus**, utilizing a "Glassmorphism-lite" approach. It prioritizes clarity through layered depth and subtle tonal shifts rather than decorative elements. Every pixel must feel intentional, secure, and computationally powerful. The emotional response is one of "focused intelligence"—minimizing cognitive load while maximizing information density.

## Colors

This design system utilizes a sophisticated dark-mode palette rooted in "Deep Graphite Plum." This base provides a restful, high-contrast environment for long-duration clinical analysis.

- **Primary Accent (Neural Violet):** Reserved exclusively for interactive elements like primary buttons, active navigation states, and focus indicators.
- **Data Accent (Clinical Teal):** Used strictly for data visualization, EEG waveforms, and neural mapping. It must never be used for buttons to ensure clear semantic separation between "system action" and "biological data."
- **Tonal Hierarchy:** Depth is created by lightening the Graphite Plum base as elements move "closer" to the user. Surfaces should never use pure black; the subtle plum undertone reduces eye strain and adds a premium, modern feel.

## Typography

The typography system relies on **Geist** for its technical precision and readability, and **JetBrains Mono** for data-specific labels and telemetry.

- **Sub-headers:** Use the `sub-header` style (all caps, wide tracking) for section labels and metadata groups to create a "Mission Control" aesthetic.
- **Data Labels:** Use the monospaced font for all numerical values, timestamps, and coordinates to ensure tabular alignment and a research-grade feel.
- **Scale:** Maintain high density by favoring `body-sm` for secondary metadata and auxiliary controls.

## Layout & Spacing

The layout is a **Fixed 45/55 Split** on desktop, designed to eliminate scrolling. The left pane (45%) is reserved for global controls, patient overview, and input parameters. The right pane (55%) is the "Command Center" for primary data visualizations and AI-generated insights.

- **High Density:** Use a strict 4px grid. Padding inside cards should be condensed (12px or 16px) to maximize the "at-a-glance" information density.
- **No Scrolling:** Content must be compartmentalized into scrollable inner regions (e.g., a specific list inside a card) while the global layout remains locked.
- **Breakpoints:** On tablets, the 45/55 split shifts to a vertical stack. On mobile, the interface provides a simplified "Alert & Monitor" view, as full analysis is intended for desktop/workstation environments.

## Elevation & Depth

Hierarchy is achieved through **Tonal Layers** and **Precise Outlines** rather than heavy shadows.

- **Base Layer:** Deep Graphite Plum (`#0F0C13`).
- **Primary Cards:** Elevated Plum (`#1A1621`) with a 1px solid border (`#2D2838`) to define edges without adding visual weight.
- **Active Overlays:** Modals or tooltips use a subtle backdrop blur (8px) with a semi-transparent fill to maintain context of the underlying data.
- **Glow Effects:** Use a very soft, low-spread outer glow (Neural Violet) only for critical active states or "AI-processing" indicators to simulate a backlit console.

## Shapes

The shape language is **Soft-Geometric**. A low corner radius (4px to 8px) is used to maintain a professional, rigid scientific feel while appearing more modern than sharp 90-degree corners.

- **Buttons & Inputs:** 4px radius (`rounded`).
- **Data Cards:** 8px radius (`rounded-lg`).
- **Status Indicators:** 2px or fully circular for small status pips.

## Components

- **Buttons:** Primary buttons use a solid Neural Violet fill with white text. Secondary buttons use a ghost style (violet outline, transparent fill). No gradients.
- **Precise Input Fields:** Dark background (`#0F0C13`) with a subtle 1px border. On focus, the border glows Neural Violet. Include a dedicated area for real-time validation micro-copy in `label-mono`.
- **Sophisticated Cards:** Use "Sub-header" typography for card titles. Include a top-right "Action Area" for card-specific tools (e.g., Export, Refresh).
- **Sleek Tab Switchers:** Segmented controls that sit flush within the surface. The active tab is indicated by a Neural Violet underline or a subtle tonal shift.
- **Live Status Indicators:** Use "Blinking" pips for active data streams. Success (Green), Warning (Amber), and Error (Red) status pips should be accompanied by monospaced labels for accessibility.
- **Signal Visualizers:** EEG/Waveform containers must have a subtle grid-line background (10% opacity Clinical Teal) to aid in visual measurement.