from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime
import subprocess
import sys

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            # Install anthropic at runtime
            subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic==0.18.1"])
            
            # Now import it
            import anthropic
            
            # Get API key
            ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY')
            
            if not ANTHROPIC_KEY:
                raise Exception("No Anthropic API key found")
            
            # Create client - simple initialization
            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            
            # Test message
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": "Say 'API is working!' in 5 words"}]
            )
            
            result = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'analysis': response.content[0].text
            }
            
        except Exception as e:
            result = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(result).encode())
