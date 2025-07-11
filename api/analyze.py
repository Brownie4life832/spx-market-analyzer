from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime, timedelta
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
            
            # Try multiple approaches to get current data
            market_data = self.fetch_current_market_data(OPTIONS_KEY)
            
            # Get AI analysis
            analysis = self.get_ai_analysis(market_data, ANTHROPIC_KEY)
            
            response = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis,
                'debug_info': market_data.get('debug_info', {})
            }
            
        except Exception as e:
            response = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def fetch_current_market_data(self, api_key):
        """Try multiple approaches to get current data"""
        results = {}
        debug_info = {}
        
        # Get current date in different formats
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        
        # Also try yesterday in case today's data isn't available yet
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # If it's weekend, get Friday's date
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            days_since_friday = now.weekday() - 4
            last_friday = (now - timedelta(days=days_since_friday)).strftime("%Y-%m-%d")
            dates_to_try = [last_friday, current_date, yesterday]
        else:
            dates_to_try = [current_date, yesterday]
        
        debug_info['dates_tried'] = dates_to_try
        debug_info['current_datetime'] = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # First, check available intraday slots to see what dates have data
        slots_data = self.check_available_slots(api_key, current_date)
        if slots_data:
            debug_info['available_slots'] = slots_data
        
        # Try each date
        for date_to_try in dates_to_try:
            try:
                # Try heatmap endpoint
                heatmap_url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
                params = {
                    "model": "intraday",  # Changed from "daily" to "intraday"
                    "ticker": "SPX",
                    "date": date_to_try,
                    "type": "gamma",
                    "key": api_key
                }
                
                url = heatmap_url + "?" + urllib.parse.urlencode(params)
                req = urllib.request.Request(url)
                response = urllib.request.urlopen(req, timeout=10)
                data = json.loads(response.read().decode('utf-8'))
                
                if data and not isinstance(data, dict) or (isinstance(data, dict) and 'error' not in data):
                    results['heatmap_gamma'] = data
                    results['data_date'] = date_to_try
                    debug_info['successful_date'] = date_to_try
                    break
                    
            except Exception as e:
                debug_info[f'error_{date_to_try}'] = str(e)
        
        # Also try to get more current data from breakdown endpoint
        try:
            current_datetime = now.strftime("%Y-%m-%dT%H:%M:%S")
            breakdown_url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/"
            
            # Try with current date first
            params = {
                "date": dates_to_try[0],
                "ticker": "SPX",
                "mode": "net",
                "model": "intraday",
                "metric": "DEX",
                "option_type": "C",
                "customer_type": "all",  # Changed from "procust" to "all"
                "expiration_type": "all",  # Changed to "all"
                "date_time": current_datetime,
                "key": api_key
            }
            
            url = breakdown_url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=10)
            breakdown_data = json.loads(response.read().decode('utf-8'))
            
            results['breakdown_data'] = breakdown_data
            debug_info['breakdown_success'] = True
            
        except Exception as e:
            debug_info['breakdown_error'] = str(e)
        
        results['debug_info'] = debug_info
        return results
    
    def check_available_slots(self, api_key, date):
        """Check what time slots are available for the given date"""
        try:
            slots_url = "https://api.optionsdepth.com/options-depth-api/v1/intraday-timeslots/"
            params = {
                "date": date,
                "key": api_key
            }
            
            url = slots_url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=10)
            return json.loads(response.read().decode('utf-8'))
            
        except:
            return None
    
    def get_ai_analysis(self, market_data, api_key):
        """Get analysis from Claude"""
        try:
            # Build debug string
            debug_str = json.dumps(market_data.get('debug_info', {}), indent=2)
            
            prompt = f"""
            IMPORTANT CONTEXT:
            - Today's actual date: {datetime.now().strftime('%Y-%m-%d')}
            - Current SPX level: approximately 6280
            - We're trying to get current market data but may be receiving historical data
            
            Debug Information:
            {debug_str}
            
            Market Data Received:
            {json.dumps(market_data, indent=2)[:2000]}
            
            Please provide:
            1. First, comment on the data freshness - is this current or historical data?
            2. If data appears old, provide general analysis based on typical market conditions at SPX 6280
            3. Key gamma levels and expected effects
            4. Market direction bias
            5. Important levels to watch
            
            Be clear about any data limitations.
            """
            
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
            
            req = urllib.request.Request(url, data=data, headers=headers)
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode('utf-8'))
            
            return result['content'][0]['text']
            
        except Exception as e:
            return f"AI Analysis Error: {str(e)}"
