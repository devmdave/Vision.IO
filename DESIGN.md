---
name: Vision Industrial Intelligence
colors:
  surface: '#131314'
  surface-dim: '#131314'
  surface-bright: '#3a393a'
  surface-container-lowest: '#0e0e0f'
  surface-container-low: '#1c1b1c'
  surface-container: '#201f20'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353435'
  on-surface: '#e5e2e2'
  on-surface-variant: '#c6c6cb'
  inverse-surface: '#e5e2e2'
  inverse-on-surface: '#313031'
  outline: '#909095'
  outline-variant: '#45474b'
  surface-tint: '#c3c6d1'
  primary: '#c3c6d1'
  on-primary: '#2c3039'
  primary-container: '#1e222a'
  on-primary-container: '#868993'
  inverse-primary: '#5b5e68'
  secondary: '#c3c6ce'
  on-secondary: '#2d3137'
  secondary-container: '#43474e'
  on-secondary-container: '#b2b5bd'
  tertiary: '#c2c6d5'
  on-tertiary: '#2b303c'
  tertiary-container: '#1d222d'
  on-tertiary-container: '#848997'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dfe2ed'
  primary-fixed-dim: '#c3c6d1'
  on-primary-fixed: '#181c23'
  on-primary-fixed-variant: '#434750'
  secondary-fixed: '#dfe2eb'
  secondary-fixed-dim: '#c3c6ce'
  on-secondary-fixed: '#181c22'
  on-secondary-fixed-variant: '#43474e'
  tertiary-fixed: '#dee2f1'
  tertiary-fixed-dim: '#c2c6d5'
  on-tertiary-fixed: '#161c26'
  on-tertiary-fixed-variant: '#424753'
  background: '#131314'
  on-background: '#e5e2e2'
  surface-variant: '#353435'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
  telemetry-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  telemetry-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
spacing:
  unit: 4px
  gutter: 12px
  margin-page: 16px
  component-padding-x: 12px
  component-padding-y: 8px
---

## Brand & Style

This design system is built for high-stakes enterprise surveillance and industrial monitoring. The aesthetic is strictly **Minimalist** and **Corporate/Modern**, prioritizing cognitive clarity over visual flair. It avoids all decorative trends like glassmorphism or glows in favor of a "Dashboard-as-a-Tool" philosophy. 

The target audience consists of security operators and system administrators who require sustained focus over long shifts. The UI should evoke a sense of reliability, precision, and calm authority. Every visual element serves a functional purpose, utilizing a high-density layout to maximize information awareness without inducing fatigue.

## Colors

The palette is a focused industrial grayscale designed for low-light environments. The background utilizes a soft neutral dark gray to reduce eye strain. Components are distinguished by a slightly lighter slate gray, defined by crisp 1px borders rather than shadows. 

Functional status accents are matte and desaturated, ensuring they stand out against the monochrome base without appearing luminous or distracting. Use Olive Green for "Secure/Active" states, Dull Amber for "Attention Required," and Matte Crimson for "Critical Alerts." Text should remain off-white (#E2E8F0) to maintain high contrast without the "vibration" of pure white on dark backgrounds.

## Typography

Typography is bifurcated by function. **Inter** is the primary interface typeface, chosen for its exceptional legibility in dense UI environments. It handles all navigational elements, headers, and standard body copy. 

**JetBrains Mono** is reserved strictly for telemetry data, timestamps, coordinates, and system logs. The monospaced nature ensures that rapidly changing numerical data remains stable on the screen, preventing "jumping" layouts during real-time updates. Use `label-caps` for table headers and persistent sidebar categories to provide clear structural hierarchy.

## Layout & Spacing

The design system employs a **Fixed Grid** model optimized for 16:9 and 21:9 monitor setups standard in surveillance hubs. The layout uses a 4px base unit to achieve high density. 

Margins and gutters are kept tight (12px to 16px) to maximize the "screen real estate" dedicated to video feeds and data visualizations. On desktop, use a 12-column grid; on mobile/tablet, transition to a single-column scrollable feed where telemetry is nested below video containers. Content should be organized into "tiles" that maintain a rigid horizontal and vertical alignment to reinforce the sense of order.

## Elevation & Depth

This system rejects shadows. Depth is communicated exclusively through **Tonal Layers** and **Bold Borders**. 

1.  **Level 0 (Background):** #1E222A - The base canvas.
2.  **Level 1 (Containers):** #21252B - Cards, sidebars, and header bars.
3.  **Level 2 (Interactives):** #2C313A - Hover states and active input fields.

Every container must have a 1px solid border (#3A3F4B). This creates a "blueprint" effect where the structure of the application is clearly mapped out. Active or focused states should replace the neutral border with a subtle 1px primary accent color.

## Shapes

The shape language is strictly **Sharp (0)**. There are no rounded corners in this design system. All containers, buttons, input fields, and video feeds must use 90-degree angles. This reinforces the industrial, utilitarian nature of the product and allows for more efficient tiling of components without "dead space" created by corner radii.

## Components

-   **Buttons:** Rectangular, no rounding. Primary buttons use a solid #3A3F4B background with white text. Ghost buttons use the 1px border. 
-   **Input Fields:** Background #1E222A with a 1px border. Labels should use `label-caps` typography positioned directly above the field.
-   **Status Chips:** Small, rectangular badges. No background fill; only a 1px border in the status color (Green/Amber/Red) with matching text color.
-   **Data Tables:** High-density, no row stripping. Use 1px horizontal dividers. Telemetry data columns should use JetBrains Mono.
-   **Video Containers:** No padding around the video stream. The 1px border should wrap the frame. Overlays (camera name, timestamp) should use a semi-opaque black bar at the top or bottom with white JetBrains Mono text.
-   **Checkboxes/Radios:** Square, sharp-edged. Checked states use the status_success color.