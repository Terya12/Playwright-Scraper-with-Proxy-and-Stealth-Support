# Playwright Scraper with Proxy and Stealth Support

## Project Overview

An automated web scraping project using Playwright in Python. Features include:  
- Proxy support to bypass restrictions  
- Browser masking with playwright-stealth  
- Logging of key events via a custom logger module  
- Asynchronous browser control with Playwright  

## Requirements

- Python 3.8+  
- playwright  
- playwright-stealth  

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Terya12/Playwright-Scraper-with-Proxy-and-Stealth-Support.git
cd <project_folder>
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Install Playwright browsers:
```bash
playwright install
```
4. Usage
Run the main script:
```bash
python main.py
```
Proxy Configuration
Proxies can be set in data.txt or via environment variables, depending on your implementation.

Logging
A custom logging module is used for easy debugging and monitoring.
