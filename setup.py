from setuptools import setup, find_packages

setup(
    name="nanocoder",
    version="1.0.0",
    description="The Minimal-Token Autonomous Coding Agent",
    author="Global AI Hackathon Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "google-genai>=3.1.0",
        "rich>=15.0.0",
        "streamlit>=1.40.0",
        "pytest>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "nanocoder=cli:main",
        ],
    },
)
