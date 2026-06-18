# Quantum Bridge OS — Investor Overview

**Product:** Quantum Bridge OS (QBridge)  
**Category:** Quantum-as-a-Service (QaaS) platform — chemistry simulation, portfolio optimization, and post-quantum security  
**Live demo:** https://qbridge-os.vercel.app  
**API:** https://qbridge-os.onrender.com  
**Source:** https://github.com/muhammadmaalik/qbridge-os  

---

## 1. Executive summary

Quantum Bridge OS is a **web platform that makes quantum computing usable for non-physicists**. Users log in, submit a molecule or a stock portfolio, and receive **ground-state energies**, **3D electron-density visualizations**, or **optimized asset allocations** — computed with real quantum algorithms on classical simulators today, with a path to cloud quantum hardware.

Unlike demo sites that show fixed numbers, our chemistry pipeline runs **ab initio Hartree–Fock integrals** (PyQInt) and then **Variational Quantum Eigensolver (VQE)** optimization. Finance uses **Quantum Approximate Optimization Algorithm (QAOA)** on a quadratic portfolio problem derived from live market data.

The product is built as a **modern SaaS stack**: Next.js frontend, FastAPI backend, email OTP authentication, rate limiting, and a post-quantum cryptographic session layer for API requests.

---

## 2. What problem we solve

| Pain point | Our approach |
|------------|--------------|
| Quantum chemistry tools are CLI-only and fragmented | Browser UI: pick H₂, water, or SMILES → get energy + charts |
| Investors cannot see “real” quantum math | Full pipeline exposed: HF reference, qubit mapping, VQE convergence plot |
| Quantum APIs are insecure for enterprise | PQC-inspired handshake + HMAC-signed compute requests |
| Portfolio optimization is classical-only in most fintech demos | QAOA on a QUBO built from live Yahoo Finance covariance |

---

## 3. What the website does (user-facing modules)

### 3.1 Dashboard (`/`)

- Secure tunnel status (post-quantum handshake with API)
- System telemetry (noise model, backend status)
- Entry point to Chemistry, Finance, and Security labs

### 3.2 Quantum Chemistry (`/chemistry`)

- **Input:** molecule presets (H₂, LiH, H₂O, ethane, caffeine), custom SMILES, or dimer mode (two fragments)
- **Output:**
  - Ground-state energy in **Hartree** (atomic units)
  - VQE energy convergence chart (iteration vs energy)
  - 3D electron probability cloud
  - Telemetry: driver (PyQInt HF), qubit count, mapper, active space, optimizer iterations

### 3.3 Quantum Finance (`/finance`)

- **Input:** stock tickers (e.g. AAPL, MSFT, TSLA), risk factor, history window
- **Output:**
  - Expected returns and covariance from market data
  - QAOA-selected portfolio (binary allocation per asset)
  - Efficient frontier curve (classical mean–variance reference)
  - Optional VADER sentiment adjustment on news headlines

### 3.4 Security lab (`/security`)

- Demonstrates Kyber-style key encapsulation handshake
- Shows how compute requests are signed with a session-derived MAC

### 3.5 Authentication (`/login`)

- Register with email + password
- Two-factor login: password → **6-digit OTP emailed** to user
- JWT session for protected routes

---

## 4. Quantum algorithms we use

### 4.1 Variational Quantum Eigensolver (VQE) — Chemistry

**Goal:** Find the lowest eigenvalue of the molecular electronic Hamiltonian → **ground-state energy**.

**Pipeline:**

1. **Geometry** — RDKit / PubChem / legacy tables → 3D coordinates  
2. **Ab initio integrals** — Restricted **Hartree–Fock (HF)** in STO-3G basis via **PyQInt**  
3. **Active space** — trim orbitals to fit qubit budget (`max_qubits`)  
4. **Fermion → qubit mapping** — **Parity mapping** (or Jordan–Wigner) via Qiskit Nature  
5. **Ansatz** — `RealAmplitudes` circuit (parameterized rotations + entanglement)  
6. **Optimizer** — **SciPy SLSQP** minimizes ⟨ψ(θ)|H|ψ(θ)⟩ on exact **statevector** simulator  
7. **Optional:** noisy ⟨H⟩ pass with Qiskit Aer noise model (post-optimization only)

**Why VQE:** Exact diagonalization of molecular Hamiltonians scales exponentially; VQE is the industry-standard hybrid approach used in drug discovery and materials research prototypes.

### 4.2 Quantum Approximate Optimization Algorithm (QAOA) — Finance

**Goal:** Select a subset of assets (budget constraint) that optimizes risk–return.

**Pipeline:**

1. Pull historical prices (**yfinance**)  
2. Estimate **expected returns μ** and **covariance matrix Σ** (annualized)  
3. Build **quadratic program** via Qiskit Finance `PortfolioOptimization`  
4. Convert to **QUBO** (`QuadraticProgramToQubo`)  
5. Run **QAOA** (COBYLA classical optimizer, StatevectorSampler)  
6. Decode bitstring → selected tickers  

**Why QAOA:** Discrete portfolio selection is NP-hard; QAOA is a leading candidate for combinatorial finance problems on near-term quantum hardware.

### 4.3 Classical reference — Efficient frontier

Mean–variance optimization with SciPy SLSQP provides a **classical baseline** to compare against QAOA allocations.

### 4.4 Post-quantum session layer (security)

- Mock **CRYSTALS-Kyber-512**-style encapsulation for session keys  
- **HMAC-SHA256** signatures on canonical compute request payloads  
- Aligns with NIST PQC direction (Kyber / ML-KEM family) for “harvest now, decrypt later” threat model  

*Note: Production PQC would use certified libraries (e.g. liboqs); our layer demonstrates the architecture.*

---

## 5. Mathematics (investor-friendly)

### 5.1 Born–Oppenheimer electronic Hamiltonian

We solve for the electronic ground state with fixed nuclei:

\[
H = E_{\text{nuc}} + \sum_{pq} h_{pq} a_p^\dagger a_q + \frac{1}{2} \sum_{pqrs} g_{pqrs} a_p^\dagger a_q^\dagger a_r a_s
\]

- \(E_{\text{nuc}}\) — nuclear repulsion  
- \(h_{pq}\) — one-electron integrals (kinetic + nuclear attraction)  
- \(g_{pqrs}\) — two-electron repulsion integrals  
- Computed at HF level in STO-3G, then mapped to qubits  

**Units:** Energy reported in **Hartree** (1 Ha ≈ 27.21 eV). Example: H₂ ≈ −1.137 Ha.

### 5.2 Qubit mapping

Fermionic operators are mapped to Pauli strings:

- **Jordan–Wigner** or **Parity** transformation (Qiskit Nature)  
- Qubit count ≈ 2 × active spatial orbitals  

### 5.3 VQE objective

Minimize:

\[
E(\theta) = \langle \psi(\theta) | H_{\text{qubit}} | \psi(\theta) \rangle
\]

where \(\psi(\theta)\) is prepared by a parameterized quantum circuit.

### 5.4 Portfolio optimization

Classical Markowitz-style objective inside the QP:

\[
\max_w \; \mu^\top w - \lambda \, w^\top \Sigma \, w
\]

subject to \(\sum_i w_i = 1\), \(w_i \in \{0,1\}\), \(\sum_i w_i = \text{budget}\).

Converted to QUBO for QAOA.

### 5.5 Sentiment (finance adjunct)

**VADER** lexicon scores news text; scores nudge return estimates — bridging “market narrative” with quantitative optimization.

---

## 6. Technology stack

| Layer | Technology | Role |
|-------|------------|------|
| Frontend | **Next.js 16**, React 19, Tailwind CSS 4 | Dashboard, chemistry/finance UIs, 3D viewer (Three.js) |
| API | **FastAPI**, Uvicorn, async Python | REST + WebSocket gateway |
| Quantum | **Qiskit**, Qiskit Nature, Aer, Finance, Optimization | Circuits, VQE, QAOA |
| Chemistry integrals | **PyQInt** (HF, STO-3G) | Ab initio on Windows & Linux |
| Cheminformatics | **RDKit**, PubChemPy | SMILES → 3D geometry |
| Classical math | **SciPy**, NumPy, pandas | SLSQP, covariance, frontier |
| Market data | **yfinance** | Live stock history |
| NLP | **vaderSentiment** | News sentiment |
| Auth | **bcrypt**, **python-jose** (JWT), SMTP OTP | Accounts + 2FA |
| Database | PostgreSQL (prod) / in-memory (dev) | Users, jobs, API keys |
| Hosting | **Vercel** (frontend), **Render** (API) | Auto-deploy from GitHub |

---

## 7. Security architecture

| Control | Implementation |
|---------|----------------|
| Password storage | bcrypt hashing |
| Session | JWT access tokens (24h configurable) |
| 2FA | Email OTP, 10-minute expiry, 5 attempt cap |
| API abuse | Per-IP rate limits (auth: 15/min, compute: 30/min) |
| Transport | HTTPS (HSTS on API) |
| Headers | X-Frame-Options DENY, nosniff, Referrer-Policy |
| Compute integrity | PQC handshake + HMAC request signatures |
| CORS | Explicit allowlist (Vercel + localhost) |
| WebSocket | Connection cap (50) |

**DDoS note:** Application rate limits help against abuse; **edge protection** (e.g. Cloudflare in front of Vercel/Render) is recommended for large-scale attacks.

---

## 8. Architecture diagram

```
┌─────────────────┐     HTTPS      ┌──────────────────┐
│  Next.js (Vercel)│ ◄────────────► │ FastAPI (Render) │
│  Dashboard UI    │   PQC + JWT    │  Quantum Router  │
└─────────────────┘                └────────┬─────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              PyQInt HF + VQE            QAOA Portfolio            SMTP OTP
              Qiskit Nature              yfinance + VADER          PostgreSQL
```

---

## 9. What is “real” vs simulated

| Component | Status |
|-----------|--------|
| Hartree–Fock integrals (PyQInt) | **Real** ab initio |
| VQE energy minimization (SLSQP) | **Real** optimization on statevector |
| QAOA portfolio solver | **Real** Qiskit algorithm on simulator |
| Market data | **Real** Yahoo Finance feeds |
| IBM Quantum hardware | Optional path; default is **local simulator** |
| PQC Kyber | **Educational mock** (architecture correct, not NIST-certified binary) |
| Hardware noise telemetry on dashboard | **Representative** parameters for UX |

---

## 10. Example results (validation)

| Molecule | Method | Typical energy (Ha) |
|----------|--------|---------------------|
| H₂ | PyQInt HF + VQE | ≈ −1.137 |
| LiH | PyQInt HF + VQE | ≈ −7.6 |
| H₂O | PyQInt HF + VQE | ≈ −75 |

Energies depend on basis set (STO-3G) and active space; convergence visible in UI chart.

---

## 11. Business model angles (for discussion)

1. **SaaS API** — per-seat or per-compute-minute pricing for chemistry/finance endpoints  
2. **Enterprise** — private deploy + hardware connector (IBM Quantum, AWS Braket)  
3. **Education** — university labs teaching VQE/QAOA with auditable pipelines  
4. **Pharma R&D** — early-stage conformer / reaction screening via API  

---

## 12. Roadmap (technical)

- [ ] Certified PQC (ML-KEM) via liboqs / BoringSSL  
- [ ] IBM Quantum Runtime backend toggle (production)  
- [ ] Persistent PostgreSQL on Render (multi-user accounts)  
- [ ] Cloudflare WAF for DDoS  
- [ ] ADAPT-VQE / UCCSD ansätze for higher accuracy  
- [ ] GPU / tensor-network accelerators for larger molecules  

---

## 13. Repository & deployment status

- **GitHub:** all source on `main` branch, auto-deploy to Vercel  
- **Render API:** must be **manually redeployed** after major backend changes — see `docs/DEPLOY_RENDER.md`  
- **Verify live API:** `GET /api/v1/system/version` should return `"auth_routes": true`  

---

## 14. Demo script for investors (10 minutes)

1. **Login** — register, receive OTP email, enter code  
2. **Chemistry** — run H₂, show energy ≈ −1.137 Ha, VQE convergence, ab initio telemetry  
3. **Finance** — AAPL + MSFT + TSLA, run QAOA optimize, show selected allocation  
4. **Security** — show PQC handshake completing  
5. **Architecture** — walk through this document, section 4–6  

**Offline backup:** run `.\start-local.ps1` if cloud API is cold-starting.

---

## 15. Contact & links

| Resource | URL |
|----------|-----|
| Website | https://qbridge-os.vercel.app |
| API docs (when deployed) | https://qbridge-os.onrender.com/docs |
| GitHub | https://github.com/muhammadmaalik/qbridge-os |

---

*Document version: June 2026 — aligned with commit on `main` (Quantum Bridge OS).*
