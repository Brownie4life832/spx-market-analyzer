from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime
import urllib.request
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            # Get API keys
            ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY')
            OPTIONS_KEY = os.environ.get('OPTIONSDEPTH_API_KEY')
            
            # First, fetch market data from OptionsDepth
            market_data = self.fetch_market_data(OPTIONS_KEY)
            
            # Then get AI analysis using direct HTTP call
            analysis = self.get_ai_analysis(market_data, ANTHROPIC_KEY)
            
            response = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis
            }
            
        except Exception as e:
            response = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def fetch_market_data(self, api_key):
        """Fetch data from OptionsDepth"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Build URL with parameters
            base_url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
            params = {
                "model": "daily",
                "ticker": "SPX",
                "date": current_date,
                "type": "gamma",
                "key": api_key
            }
            
            url = base_url + "?" + urllib.parse.urlencode(params)
            
            # Make request
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read().decode('utf-8'))
            
            return {
                'gamma_data': data,
                'status': 'success',
                'date': current_date
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def get_ai_analysis(self, market_data, api_key):
        """Get analysis from Claude using direct HTTP"""
        try:
            # Prepare the prompt
            prompt = f"""
            Analyze this SPX options market data:
            
            Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST
            
            Market Data:
            {json.dumps(market_data, indent=2)[:1000]}
            
            Please provide:
            1. Key gamma levels and what they mean
            2. Expected market direction
            3. Important price levels to watch
            4. Next 10-minute outlook
            
            Be specific and concise.
            """
            
            # Prepare API request
            url = "https://api.anthropic.com/v1/messages"
            
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            data = json.dumps({
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            }).encode('utf-8')
            
            # Make request
            req = urllib.request.Request(url, data=data, headers=headers)
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode('utf-8'))
            
            # Extract the response text
            return result['content'][0]['text']
            
        except Exception as e:
            return f"AI Analysis Error: {str(e)}"
