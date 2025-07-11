from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Simple test without Anthropic
        response = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'analysis': 'Testing: Basic API is working! OptionsDepth Key is: ' + str(os.environ.get('OPTIONSDEPTH_API_KEY', 'Not found')[:10]) + '...',
            'environment': {
                'has_anthropic_key': bool(os.environ.get('ANTHROPIC_API_KEY')),
                'has_options_key': bool(os.environ.get('OPTIONSDEPTH_API_KEY'))
            }
        }
        
        self.wfile.write(json.dumps(response).encode())
