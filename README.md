Billboard Music Theory & Harmonic Analysis Pipeline
An end-to-end automated data pipeline that scrapes popular music charts, retrieves corresponding guitar tabs, extracts chord progressions using AI, and converts them into numerical musical notation for harmonic analysis.

📊 Project Overview
This toolkit is designed for musicologists, data scientists, and musicians to analyze the structural and harmonic trends of "Hot 100" hits. It automates the transition from a chart ranking to a theoretical data point (like Nashville Numbers), allowing for large-scale study of pop music composition.

The Analysis Pipeline
Fetch: Scrape the current Billboard Hot 100 chart data.

Match: Automate web searches to find and download high-quality guitar chord tabs.

Extract: Utilize Large Language Models (LLM) to parse raw HTML/text and extract clean chord sequences.

Analyze: Convert standard chords (e.g., C, Am, G) into universal numerical notation relative to the song's key.

Visualize: Display findings through an interactive web-based dashboard.

📂 File Structure & Modules
🚀 Getting Started
Prerequisites
Python 3.10+

Chrome/Chromium Browser (Required for the DrissionPage automation)

Installation
Clone the repository:

Install dependencies:

Configuration
Obtain API keys for ZhipuAI and Google Gemini.

Store your keys in a local file (e.g., api.txt) or set them as environment variables.

⚠️ Security Warning: Do not upload your api.txt or any file containing raw API keys to GitHub. Add them to your .gitignore file immediately.

📖 Usage Instructions
Step 1: Fetch Chart Data
Run the fetcher to get the latest 100 songs.

Step 2: Match & Download Tabs
This script will open a browser instance to find the best chord tabs for your list.

Step 3: Extract Chord Sequences
Process the downloaded files through the AI extraction layer.

Step 4: Theoretical Analysis
Convert the raw chords into numerical format based on the song's key.

📉 Visualization
Once the data is processed, open index.html in any modern web browser. The dashboard provides:

Progression Frequency: Distribution of the most common chord patterns.

Key Distribution: Analysis of the most popular keys in the current charts.

Song Browser: Detailed breakdown of individual tracks.

📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
