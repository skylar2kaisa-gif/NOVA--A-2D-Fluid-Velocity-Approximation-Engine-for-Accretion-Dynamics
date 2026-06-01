# NOVA-Ω: Dual-Engine Relativistic and Accretion Kinematics Simulator

An optimized, self-contained Python framework for visualizing orbital mechanics, strong-field spacetime deformations, and black hole mass-energy ingestion in a flicker-free ANSI terminal interface.

## 🌌 Core Mechanics & Architecture
The project features a modular architecture that cleanly separates a high-performance cell-buffered renderer (`Screen` class with DEC 2026 synchronized output) from underlying gravitational equations.

### 1. Kinematic Advection Engine (`nova_omega_sim.py`)
Models smooth, steady-state planetary drift across localized fields.
* **Radial Decay Gradient:** $dr/dt = -G_{\text{pull}} / r^2$
* **Application:** Ideal for uniform particle-ring distribution and predictive fluid simulation.

### 2. Dynamical Relativistic Force Engine (`nova_omega_relativity.py`)
A reality-focused simulator integrating Einsteinian orbital corrections and thermodynamic conservation laws.
* **Effective Relativistic Potential:** Includes the crucial Schwarzschild strong-field correction term:
  $$a_{\text{grav}} = -\frac{G}{r^2} - \frac{3GL^2}{r^4}$$
* **Spacetime Energy Dissipation:** Implements continuous gravitational radiation drag scaled dynamically to distance ($1/r^2$).
* **Conservation of Angular Momentum:** Dynamically updates the central singularity's global spin ($\Omega$) upon event horizon ingestion ($r < 2.0$), feeding mass energy directly back into the differential frame-dragging grid:
  $$\Omega_{\text{new}} = \Omega_{\text{old}} + (m_{\text{body}} \times 0.02)$$

Kinematic Advection Engine (`nova_omega_sim.py`):
How to run: python nova_omega_sim.py

Dynamical Relativistic Force Engine (`nova_omega_relativity.py`)
How to run: python nova_omega_relativity.py
