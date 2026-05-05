import sys
import os

try:
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
except ImportError:
    print("Qiskit not installed! Please run: pip install qiskit qiskit-aer")
    sys.exit(1)

def print_header(title):
    print("\n" + "="*50)
    print(f" {title} ".center(50, "="))
    print("="*50)

def draw_histogram(counts):
    print("\n--- Measurement Distribution ---")
    total = sum(counts.values())
    for state, count in counts.items():
        prob = count / total
        bar = "█" * int(prob * 30)
        print(f"|{state}⟩: {bar} ({prob*100:.1f}%)")
    print("--------------------------------\n")

def run_level(level_name, description, num_qubits, target_evaluator):
    print_header(f"Level: {level_name}")
    print(description)
    print("\nAvailable Gates: ")
    print("  X <qubit>       (Bit Flip - NOT gate)")
    print("  H <qubit>       (Hadamard - Superposition)")
    print("  CX <ctrl> <tgt> (CNOT - Entanglement)")
    print("  RUN             (Measure & Evaluate Circuit)")
    print("  RESET           (Start Over)")
    print("  EXIT            (Return to Menu)")
    
    qc = QuantumCircuit(num_qubits)
    
    while True:
        print("\nCurrent Circuit:")
        print(qc.draw(output='text'))
        
        cmd = input("\nEnter Command > ").strip().upper().split()
        if not cmd:
            continue
            
        action = cmd[0]
        
        try:
            if action == 'EXIT':
                return False
            elif action == 'RESET':
                qc = QuantumCircuit(num_qubits)
                print("Circuit reset!")
            elif action == 'X':
                q = int(cmd[1])
                qc.x(q)
            elif action == 'H':
                q = int(cmd[1])
                qc.h(q)
            elif action == 'CX':
                ctrl = int(cmd[1])
                tgt = int(cmd[2])
                qc.cx(ctrl, tgt)
            elif action == 'RUN':
                print("\nMeasuring Qubits...")
                qc_meas = qc.copy()
                qc_meas.measure_all()
                
                sim = AerSimulator()
                job = sim.run(qc_meas, shots=1024)
                counts = job.result().get_counts()
                
                draw_histogram(counts)
                
                if target_evaluator(counts):
                    print("🎉 SUCCESS! You achieved the target quantum state!")
                    return True
                else:
                    print("❌ INCORRECT STATE. Try again or RESET.")
            else:
                print(f"Unknown command: {action}")
        except Exception as e:
            print(f"Error parsing command: {e}")

# Level Evaluators
def eval_superposition(counts):
    # Expecting ~50% |0> and ~50% |1> on 1 qubit
    c0 = counts.get('0', 0)
    c1 = counts.get('1', 0)
    total = c0 + c1
    if total == 0: return False
    return 0.4 < (c0/total) < 0.6 and 0.4 < (c1/total) < 0.6

def eval_bell_state(counts):
    # Expecting ~50% |00> and ~50% |11> on 2 qubits
    c00 = counts.get('00', 0)
    c11 = counts.get('11', 0)
    total = sum(counts.values())
    if total == 0: return False
    prob00 = c00 / total
    prob11 = c11 / total
    return 0.4 < prob00 < 0.6 and 0.4 < prob11 < 0.6

def play():
    print_header("Welcome to QBridge Educator")
    print("This interactive sandbox allows you to compile real Quantum Circuits")
    print("using Qiskit's Aer Simulator natively on your machine.\n")
    
    # LEVEL 1
    passed = run_level(
        "1. The Quantum Coin Flip",
        "Your goal is to put a single Qubit into perfect Superposition.\nTarget: 50% chance of |0>, 50% chance of |1>.",
        1,
        eval_superposition
    )
    if not passed: return
    
    # LEVEL 2
    passed = run_level(
        "2. Spooky Action at a Distance",
        "Your goal is to Entangle two Qubits into a Bell State.\nTarget: 50% chance of |00>, 50% chance of |11>. No other states allowed!",
        2,
        eval_bell_state
    )
    if not passed: return
    
    print_header("CONGRATULATIONS")
    print("You have mastered the foundational building blocks of Quantum Mathematics!")
    print("You can now build advanced Entropy Pools and Molecular simulations using QBridge.\n")

if __name__ == '__main__':
    play()
