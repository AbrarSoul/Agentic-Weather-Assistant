# Weather Chatbot Comparison Tool

This tool allows you to compare the performance of two weather chatbot frameworks (GADK and MS) side by side.

## Features

- **Side-by-side comparison**: View responses from both frameworks simultaneously
- **Real-time performance metrics**: See response times for each framework
- **Unified interface**: Single input box that triggers both chatbots
- **Modern UI**: Clean, responsive design with gradient styling

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   Create a `.env` file in the root directory with:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   OPENWEATHER_API_KEY=your_openweather_api_key_here
   ```

3. **Run the comparison app**:
   ```bash
   python comparison_app.py
   ```

4. **Access the interface**:
   Open your browser and navigate to `http://localhost:5001`

## Usage

1. Type your weather-related question in the input box (e.g., "What's the weather in Helsinki?")
2. Click "Send" or press Enter
3. Both frameworks will process your query simultaneously
4. View the responses side by side in their respective columns
5. Check the response times displayed in the time badges

## Project Structure

- `comparison_app.py` - Main Flask application that integrates both projects
- `templates/comparison.html` - HTML template with two-column layout
- `requirements.txt` - Python dependencies
- `GADK/` - GADK framework project
- `MS/` - MS framework project

## Notes

- The app runs on port 5001 (to avoid conflicts with individual project apps on port 5000)
- Both frameworks run in parallel using threading for fair comparison
- Response times are measured independently for each framework
- The app handles errors gracefully and displays them in the respective columns

