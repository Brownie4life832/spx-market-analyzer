from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from datetime import datetime
import anthropic

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
            
            # Fetch market data
            market_data = self.fetch_market_data(OPTIONS_KEY)
            
            # Generate analysis
            analysis = self.generate_analysis(market_data, ANTHROPIC_KEY)
            
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
        """Fetch SPX options data"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        data = {}
        
        # Fetch gamma heatmap
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/heatmap/",
                params={
                    "model": "daily",
                    "ticker": "SPX",
                    "date": current_date,
                    "type": "gamma",
                    "key": api_key
                }
            )
            data['gamma'] = response.json() if response.status_code == 200 else None
        except:
            data['gamma'] = None
        
        # Fetch charm heatmap
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/heatmap/",
                params={
                    "model": "daily",
                    "ticker": "SPX",
                    "date": current_date,
                    "type": "charm",
                    "key": api_key
                }
            )
            data['charm'] = response.json() if response.status_code == 200 else None
        except:
            data['charm'] = None
            
        return data
    
    def generate_analysis(self, market_data, anthropic_key):
        """Generate AI analysis"""
        client = anthropic.Anthropic(api_key=anthropic_key)
        
        prompt = f"""
        Analyze this SPX options market data:
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST
        
        Gamma Data: {json.dumps(market_data.get('gamma', {}))[:1000]}
        Charm Data: {json.dumps(market_data.get('charm', {}))[:1000]}
        
        Provide:
        1. Key gamma levels and what they mean
        2. Market direction bias
        3. Important price levels to watch
        4. What to expect in next 10 minutes
        
        Be specific and actionable.
        """
        
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Analysis unavailable: {str(e)}"
