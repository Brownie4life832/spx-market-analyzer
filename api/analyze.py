from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime, timezone, timedelta
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
            
            # Get EST time
            est = timezone(timedelta(hours=-5))
            current_time_est = datetime.now(est)
            
            # Fetch comprehensive CURRENT market data
            market_data = self.fetch_current_market_data(OPTIONS_KEY, current_time_est)
            
            # Get AI analysis
            analysis = self.get_ai_analysis(market_data, ANTHROPIC_KEY, current_time_est)
            
            response = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'est_time': current_time_est.strftime('%Y-%m-%d %H:%M:%S EST'),
                'data_timestamp': market_data.get('timestamp', 'Unknown'),
                'spot_price': market_data.get('spot_price', 'Unknown'),
                'analysis': analysis
            }
            
        except Exception as e:
            response = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def fetch_current_market_data(self, api_key, current_time_est):
        """Fetch CURRENT intraday data from OptionsDepth"""
        # Use current date in EST
        current_date = current_time_est.strftime("%Y-%m-%d")
        
        # For intraday data, we need to specify the exact time
        # Round to nearest 5 minutes as OptionsDepth updates every 5-10 minutes
        minutes = (current_time_est.minute // 5) * 5
        rounded_time = current_time_est.replace(minute=minutes, second=0, microsecond=0)
        current_datetime = rounded_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        all_data = {
            'timestamp': current_datetime,
            'fetch_date': current_date,
            'actual_time': current_time_est.strftime("%Y-%m-%d %H:%M:%S EST")
        }
        
        # First, get available timeslots to find the latest data
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
            
            if timeslots and isinstance(timeslots, list) and len(timeslots) > 0:
                # Get the most recent timeslot
                latest_slot = timeslots[-1]
                all_data['latest_available_time'] = latest_slot
                
                # Use the latest available timeslot for data fetching
                if latest_slot:
                    current_datetime = latest_slot
            
            all_data['available_timeslots'] = timeslots[-5:] if len(timeslots) > 5 else timeslots  # Last 5 slots
            
        except Exception as e:
            all_data['timeslot_error'] = str(e)
        
        # Fetch INTRADAY data with the correct timestamp
        # 1. Get current depthview to see spot price and overall positioning
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/depthview/"
            params = {
                "date": current_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "intraday",  # IMPORTANT: Use intraday model
                "option_type": "C",
                "metric": "DEX",
                "customer_type": "procust",
                "expiration_type": "all",  # Get all expirations
                "date_time": current_datetime,
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            depthview_data = json.loads(response.read().decode('utf-8'))
            
            all_data['depthview'] = depthview_data
            
            # Extract spot price if available
            if depthview_data and 'spot_price' in depthview_data:
                all_data['spot_price'] = depthview_data['spot_price']
            elif depthview_data and isinstance(depthview_data, dict):
                # Sometimes spot price is nested
                for key, value in depthview_data.items():
                    if isinstance(value, dict) and 'spot_price' in value:
                        all_data['spot_price'] = value['spot_price']
                        break
                        
        except Exception as e:
            all_data['depthview_error'] = str(e)
        
        # 2. Get breakdown by strike for current positioning
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/"
            
            # Get calls
            params = {
                "date": current_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "intraday",
                "metric": "GEX",  # Try GEX for gamma exposure
                "option_type": "C",
                "customer_type": "procust",
                "expiration_type": "all",
                "date_time": current_datetime,
                "with_markers": "true",
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            call_data = json.loads(response.read().decode('utf-8'))
            all_data['call_strikes'] = call_data
            
            # Get puts
            params['option_type'] = 'P'
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            put_data = json.loads(response.read().decode('utf-8'))
            all_data['put_strikes'] = put_data
            
        except Exception as e:
            all_data['strike_error'] = str(e)
        
        # 3. Try to get current heatmap
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
            params = {
                "model": "intraday",  # Use intraday
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
            all_data['heatmap_error'] = str(e)
        
        return all_data
    
    def get_ai_analysis(self, market_data, api_key, current_time_est):
        """Get CURRENT analysis from Claude"""
        try:
            # Extract spot price for the prompt
            spot_price = market_data.get('spot_price', 'Unknown')
            latest_time = market_data.get('latest_available_time', market_data.get('timestamp'))
            
            # Build prompt with all available data
            prompt = f"""
            REAL-TIME SPX Options Analysis
            
            Current Time: {current_time_est.strftime('%Y-%m-%d %H:%M:%S')} EST
            Latest Data Available: {latest_time}
            SPX Spot Price: {spot_price}
            
            MARKET DATA SUMMARY:
            
            Available Timeslots: {market_data.get('available_timeslots', [])}
            
            1. MARKET DEPTH DATA:
            {json.dumps(market_data.get('depthview', {}), indent=2)[:1000]}
            
            2. CALL STRIKES (Gamma Exposure):
            {json.dumps(market_data.get('call_strikes', {}), indent=2)[:800]}
            
            3. PUT STRIKES (Gamma Exposure):
            {json.dumps(market_data.get('put_strikes', {}), indent=2)[:800]}
            
            4. GAMMA HEATMAP:
            {json.dumps(market_data.get('gamma_heatmap', {}), indent=2)[:600]}
            
            Based on this CURRENT data, provide:
            
            1. **CURRENT SPX LEVEL & CONFIRMATION**
               - Confirm the spot price shown in the data
               - Note if data seems stale or delayed
            
            2. **IMMEDIATE POSITIONING** (As of {current_time_est.strftime('%H:%M')} EST)
               - Net gamma exposure and what it means
               - Key strikes with heavy positioning
               - Put/Call skew indication
            
            3. **NEXT 10-30 MINUTES OUTLOOK**
               - Expected range: [specific low] to [specific high]
               - Directional bias with confidence %
               - Key triggers that could cause movement
            
            4. **KEY LEVELS RIGHT NOW**
               - Immediate support: [exact price]
               - Immediate resistance: [exact price]  
               - Gamma flip/pinning level: [exact price]
               - Max pain for today: [exact price]
            
            5. **UNUSUAL ACTIVITY**
               - Any notable flows or positioning changes
               - Large trades or hedging activity
            
            Be extremely specific with current price levels. If the data appears stale or incorrect, note this clearly.
            Start with: "As of {current_time_est.strftime('%H:%M EST')}..."
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
                "temperature": 0.2,  # Lower temperature for more consistent analysis
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
