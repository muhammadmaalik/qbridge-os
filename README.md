<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 0;
            background-color: #050505;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #050505;
            color: #e0e0e0;
            margin: 0;
            padding: 40px;
            line-height: 1.6;
        }
        .header {
            text-align: center;
            padding: 60px 20px;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            border-bottom: 2px solid #4f46e5;
            position: relative;
            overflow: hidden;
        }
        .header h1 {
            font-size: 32pt;
            margin: 0;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 2px;
        }
        .header p {
            font-size: 14pt;
            color: #94a3b8;
            margin-top: 10px;
        }
        .section {
            margin-top: 40px;
            padding: 20px;
            background: rgba(30, 30, 50, 0.5);
            border-radius: 12px;
            border: 1px solid #334155;
        }
        h2 {
            color: #818cf8;
            border-left: 4px solid #818cf8;
            padding-left: 15px;
            font-size: 18pt;
        }
        .grid {
            display: table;
            width: 100%;
            border-spacing: 20px;
        }
        .card {
            display: table-cell;
            width: 33%;
            padding: 20px;
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            vertical-align: top;
        }
        .card h3 {
            color: #f472b6;
            margin-top: 0;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            background: #4f46e5;
            color: white;
            font-size: 9pt;
            margin-bottom: 10px;
        }
        code {
            background: #1e293b;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            color: #38bdf8;
        }
        .footer {
            text-align: center;
            margin-top: 60px;
            color: #64748b;
            font-size: 10pt;
        }
        /* Simulation of what the "Interactive" parts would look like in the browser */
        .animation-box {
            height: 150px;
            width: 100%;
            background: #000;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px dashed #4f46e5;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #4f46e5;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>QUANTUM BRIDGE OS</h1>
        <p>Advanced Computational Intelligence & Post-Quantum Secure Infrastructure</p>
    </div>

    <div class="section">
        <h2>🚀 Overview</h2>
        <p>
            Quantum Bridge OS is a next-generation distributed platform combining <strong>Quantum Chemical Simulation</strong>, 
            <strong>Algorithmic Finance</strong>, and <strong>Post-Quantum Cryptography (PQC)</strong>. Built for a future where 
            classical and quantum systems coexist, it provides real-time insights into molecular dynamics and market optimization.
        </p>
    </div>

    <div class="grid">
        <div class="card">
            <div class="badge">CHEMISTRY</div>
            <h3>Molecular Eigensolver</h3>
            <p>Simulating complex organic molecules like <strong>Caffeine</strong> and <strong>Ethane</strong> using VQE algorithms.</p>
            <div class="animation-box">[3D Orbital Rendering Active]</div>
        </div>
        <div class="card">
            <div class="badge">FINANCE</div>
            <h3>QAOA Optimizer</h3>
            <p>Dynamic portfolio rebalancing using Quantum Approximate Optimization with VADER news sentiment integration.</p>
            <div class="animation-box">[Live Market Matrix]</div>
        </div>
        <div class="card">
            <div class="badge">SECURITY</div>
            <h3>PQC Handshake</h3>
            <p>Hybrid encryption layers resilient against future quantum decryption threats (Shor's Algorithm protection).</p>
            <div class="animation-box">[Quantum Key Exchange]</div>
        </div>
    </div>

    <div class="section">
        <h2>🛠️ Technology Stack</h2>
        <ul>
            <li><strong>Frontend:</strong> Next.js 15, TailwindCSS, Framer Motion (for animations), Three.js (for 3D models).</li>
            <li><strong>Backend:</strong> FastAPI, Python 3.14, Qiskit (Quantum SDK), RDKit (Cheminformatics).</li>
            <li><strong>Data:</strong> Yahoo Finance API + VADER Sentiment Analysis.</li>
            <li><strong>Deployment:</strong> Vercel (Frontend) & Render (Distributed Backend).</li>
        </ul>
    </div>

    <div class="section">
        <h2>🔧 Quick Start</h2>
        <p>1. <strong>Clone:</strong> <code>git clone https://github.com/muhammadmaalik/qbridge-os.git</code></p>
        <p>2. <strong>Setup:</strong> Create <code>.env</code> with your Render Backend URL.</p>
        <p>3. <strong>Run:</strong> <code>npm run dev</code> for the dashboard.</p>
    </div>

    <div class="footer">
        © 2024 Quantum Bridge OS Project. Engineered for the Post-Quantum Era.
    </div>
</body>
</html>
