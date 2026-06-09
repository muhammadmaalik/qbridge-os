from setuptools import setup, find_packages

setup(
    name="qbridge",
    version="1.0.0",
    description="The Universal Quantum Developer Toolkit (Cybersecurity, ML, Robotics, Chemistry)",
    author="Bitcamp Quantum Team",
    packages=find_packages(),
    install_requires=[
        "qiskit",
        "qiskit-aer",
        "qiskit-nature>=0.7.0",
        "qiskit-finance>=0.4.0",
        "qiskit-optimization>=0.6.0",
        "numpy",
        "scipy",
        "pyscf>=2.3.0",
        "rdkit>=2023.9.1",
        "matplotlib",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Physics",
    ],
)
