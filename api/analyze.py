from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime, timezone
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
            
            # Fetch comprehensive CURRENT market data
            market_data = self.fetch_current_market_data(OPTIONS_KEY)
            
            # Get AI analysis
            analysis = self.get_ai_analysis(market_data, ANTHROPIC_KEY)
            
            response = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'data_timestamp': market_data.get('timestamp', 'Unknown'),
                'analysis': analysis
            }
            
        except Exception as e:
            response = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def fetch_current_market_data(self, api_key):
        """Fetch CURRENT intraday data from OptionsDepth"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        all_data = {
            'fetch_time': current_datetime,
            'date': current_date
        }
        
        # 1. Fetch INTRADAY breakdown by strike (most current data)
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/"
            params = {
                "date": current_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "intraday",  # IMPORTANT: Intraday for current data
                "metric": "DEX",
                "option_type": "C",
                "customer_type": "procust",
                "expiration_type": "range",
                "expiration_range_start": current_date,
                "expiration_range_end": current_date,
                "date_time": current_datetime,  # Current time
                "with_markers": "true",
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=10)
            all_data['call_strikes'] = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            all_data['call_strikes'] = {'error': str(e)}
        
        # 2. Also get PUT data for complete picture
        try:
            params['option_type'] = 'P'
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=10)
            all_data['put_strikes'] = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            all_data['put_strikes'] = {'error': str(e)}
        
        # 3. Get current gamma heatmap
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
            params = {
                "model": "intraday",  # Changed to intraday
                "ticker": "SPX",
                "date": current_date,
                "type": "gamma",
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=10)
            all_data['gamma_heatmap'] = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            all_data['gamma_heatmap'] = {'error': str(e)}
        
        # 4. Get intraday time slots to see latest update time
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/intraday-timeslots/"
            params = {
                "date": current_date,
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=10)
            timeslots = json.loads(response.read().decode('utf-8'))
            
            # Get the latest available timeslot
            if timeslots and isinstance(timeslots, list):
                all_data['latest_timeslot'] = timeslots[-1] if timeslots else "No timeslots"
                all_data['all_timeslots'] = timeslots
        except Exception as e:
            all_data['timeslot_error'] = str(e)
        
        return all_data
    
    def get_ai_analysis(self, market_data, api_key):
        """Get CURRENT analysis from Claude"""
        try:
            # Get current time in EST
            from datetime import timezone, timedelta
            est_offset = timedelta(hours=-5)  # EST is UTC-5
            est_time = datetime.now(timezone.utc) + est_offset
            
            # Build comprehensive prompt with current data
            prompt = f"""
            REAL-TIME SPX Options Analysis Request
            
            Current Time: {est_time.strftime('%Y-%m-%d %H:%M:%S')} EST
            Data Fetch Time: {market_data.get('fetch_time', 'Unknown')}
            Latest Market Update: {market_data.get('latest_timeslot', 'Unknown')}
            
            CURRENT MARKET DATA:
            
            1. CALL OPTIONS (Current):
            {json.dumps(market_data.get('call_strikes', {}), indent=2)[:800]}
            
            2. PUT OPTIONS (Current):
            {json.dumps(market_data.get('put_strikes', {}), indent=2)[:800]}
            
            3. GAMMA HEATMAP:
            {json.dumps(market_data.get('gamma_heatmap', {}), indent=2)[:600]}
            
            Please provide CURRENT REAL-TIME analysis:
            
            1. **IMMEDIATE MARKET POSITIONING** (Right Now)
               - Current gamma levels and their impact
               - Net positioning (bullish/bearish/neutral)
               - Key strike concentrations
            
            2. **NEXT 10 MINUTES OUTLOOK** (from {est_time.strftime('%H:%M')} to {(est_time + timedelta(minutes=10)).strftime('%H:%M')} EST)
               - Expected price movement
               - Key levels to watch
               - Probability of move
            
            3. **INTRADAY LEVELS**
               - Immediate support: [specific price]
               - Immediate resistance: [specific price]
               - Gamma flip point: [specific price]
            
            4. **REAL-TIME SIGNALS**
               - Any unusual activity RIGHT NOW
               - Hedging flows detected
               - Market maker positioning
            
            Be extremely specific with CURRENT data and times. This is for immediate trading decisions.
            Start with: "As of [exact time] EST..."
            """
            
            # Make API request
            url = "https://api.anthropic.com/v1/messages"
            
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            data = json.dumps({
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1500,
                "temperature": 0.3,
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
            return f"AI Analysis Error: {str(e)}\n\nMarket Data Summary: {json.dumps(market_data, indent=2)[:500]}"
