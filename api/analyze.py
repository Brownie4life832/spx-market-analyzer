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
            
            # Fetch whatever data is available from the APIs
            market_data = self.fetch_all_optionsdepth_data(OPTIONS_KEY)
            
            # Generate analysis based on whatever data we got
            analysis = self.generate_options_analysis(market_data, ANTHROPIC_KEY)
            
            response = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'data_fetched': {
                    'heatmap': market_data.get('heatmap_status', False),
                    'breakdown_strike': market_data.get('strike_status', False),
                    'breakdown_exp': market_data.get('exp_status', False),
                    'depthview': market_data.get('depth_status', False),
                    'timeslots': market_data.get('slots_status', False)
                },
                'errors': market_data.get('errors', []),
                'api_info': market_data.get('api_info', {}),
                'analysis': analysis
            }
            
        except Exception as e:
            response = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def fetch_all_optionsdepth_data(self, api_key):
        """Fetch whatever data is available from OptionDepth endpoints"""
        # We'll use today's date for the request, but we don't care what date the data is actually from
        request_date = datetime.now().strftime("%Y-%m-%d")
        request_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        all_data = {
            'errors': [],
            'api_info': {
                'request_made_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data_dates': {}  # Will store what dates the API actually returns
            }
        }
        
        # 1. HEATMAP API - Get both Gamma and Charm
        for heatmap_type in ['gamma', 'charm']:
            try:
                url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
                params = {
                    "model": "daily",
                    "ticker": "SPX",
                    "date": request_date,
                    "type": heatmap_type,
                    "key": api_key
                }
                
                full_url = url + "?" + urllib.parse.urlencode(params)
                req = urllib.request.Request(full_url)
                response = urllib.request.urlopen(req, timeout=15)
                data = json.loads(response.read().decode('utf-8'))
                
                all_data[f'heatmap_{heatmap_type}'] = data
                all_data['heatmap_status'] = True
                
                # Try to extract what date this data is actually for
                if data and isinstance(data, dict):
                    # Look for date info in the response
                    for key in ['date', 'data_date', 'as_of_date', 'timestamp']:
                        if key in data:
                            all_data['api_info']['data_dates'][f'heatmap_{heatmap_type}'] = data[key]
                            break
                            
            except Exception as e:
                all_data['errors'].append(f"Heatmap {heatmap_type}: {str(e)}")
        
        # 2. BREAKDOWN BY STRIKE API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/"
            params = {
                "date": request_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "daily",
                "metric": "DEX", 
                "option_type": "C",
                "customer_type": "procust",
                "expiration_type": "all",
                "with_markers": "true",
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            data = json.loads(response.read().decode('utf-8'))
            
            all_data['breakdown_by_strike'] = data
            all_data['strike_status'] = True
            
        except Exception as e:
            all_data['errors'].append(f"Breakdown Strike: {str(e)}")
        
        # 3. BREAKDOWN BY EXPIRATION API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-expiration/"
            params = {
                "date": request_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "daily",
                "option_type": "C",
                "metric": "DEX",
                "customer_type": "procust",
                "expiration_type": "all",
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            data = json.loads(response.read().decode('utf-8'))
            
            all_data['breakdown_by_expiration'] = data
            all_data['exp_status'] = True
            
        except Exception as e:
            all_data['errors'].append(f"Breakdown Expiration: {str(e)}")
        
        # 4. DEPTHVIEW API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/depthview/"
            params = {
                "date": request_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "daily",
                "option_type": "C",
                "metric": "DEX",
                "customer_type": "procust",
                "expiration_type": "all",
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            data = json.loads(response.read().decode('utf-8'))
            
            all_data['depthview'] = data
            all_data['depth_status'] = True
            
        except Exception as e:
            all_data['errors'].append(f"Depthview: {str(e)}")
        
        # 5. INTRADAY TIMESLOTS API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/intraday-timeslots/"
            params = {
                "date": request_date,
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            timeslots_data = json.loads(response.read().decode('utf-8'))
            
            all_data['intraday_timeslots'] = timeslots_data
            all_data['slots_status'] = True
            
            # Get the latest timeslot
            if isinstance(timeslots_data, list) and len(timeslots_data) > 0:
                all_data['latest_timeslot'] = timeslots_data[-1]
                all_data['api_info']['latest_data_point'] = timeslots_data[-1]
                
        except Exception as e:
            all_data['errors'].append(f"Timeslots: {str(e)}")
        
        return all_data
    
    def generate_options_analysis(self, market_data, api_key):
        """Generate analysis based on whatever data is available"""
        try:
            # Get info about what data we have
            latest_slot = market_data.get('latest_timeslot', 'Unknown')
            api_info = market_data.get('api_info', {})
            
            # Build data summary
            data_summary = f"""
            OPTIONS DATA ANALYSIS - LATEST AVAILABLE DATA
            
            API Request Made At: {api_info.get('request_made_at', 'Unknown')}
            Latest Data Point: {latest_slot}
            Successful Endpoints: {sum([market_data.get(f'{x}_status', False) for x in ['heatmap', 'strike', 'exp', 'depth', 'slots']])} out of 5
            
            Available Data:
            - Gamma Heatmap: {'✓' if market_data.get('heatmap_gamma') else '✗'}
            - Charm Heatmap: {'✓' if market_data.get('heatmap_charm') else '✗'}
            - Strike Breakdown: {'✓' if market_data.get('breakdown_by_strike') else '✗'}
            - Expiration Breakdown: {'✓' if market_data.get('breakdown_by_expiration') else '✗'}
            - Market Depth: {'✓' if market_data.get('depthview') else '✗'}
            - Timeslots: {len(market_data.get('intraday_timeslots', [])) if market_data.get('intraday_timeslots') else 0} slots available
            """
            
            # Add available data
            if market_data.get('heatmap_gamma'):
                data_summary += f"\n\n1. GAMMA HEATMAP DATA:\n{json.dumps(market_data.get('heatmap_gamma'), indent=2)[:1000]}"
            
            if market_data.get('heatmap_charm'):
                data_summary += f"\n\n2. CHARM HEATMAP DATA:\n{json.dumps(market_data.get('heatmap_charm'), indent=2)[:1000]}"
            
            if market_data.get('breakdown_by_strike'):
                data_summary += f"\n\n3. STRIKE BREAKDOWN:\n{json.dumps(market_data.get('breakdown_by_strike'), indent=2)[:1000]}"
            
            if market_data.get('breakdown_by_expiration'):
                data_summary += f"\n\n4. EXPIRATION BREAKDOWN:\n{json.dumps(market_data.get('breakdown_by_expiration'), indent=2)[:1000]}"
            
            if market_data.get('depthview'):
                data_summary += f"\n\n5. MARKET DEPTH:\n{json.dumps(market_data.get('depthview'), indent=2)[:1000]}"
            
            prompt = f"""
            Analyze the LATEST AVAILABLE SPX options market data. Don't worry about what date this data is from - just analyze what patterns and insights it shows.
            
            {data_summary}
            
            Based on whatever data is available, provide analysis of:
            
            1. **GAMMA POSITIONING** (if gamma data available)
               - Key gamma concentration levels visible in the data
               - Positive/negative gamma zones
               - Potential support/resistance from gamma
            
            2. **CHARM FLOW** (if charm data available)
               - Time decay patterns across strikes
               - Key charm flip points
            
            3. **OPTIONS STRUCTURE INSIGHTS**
               - What the available data reveals about market positioning
               - Put/call imbalances
               - Key strikes with heavy interest
            
            4. **TRADING IMPLICATIONS**
               - What levels appear important based on the options data
               - Potential pinning or acceleration zones
               - Directional bias from the options structure
            
            Focus on the patterns and levels shown in the data. Don't reference specific dates unless they're clearly shown in the data.
            Work with whatever endpoints provided data successfully.
            """
            
            # Call Anthropic API
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
            response = urllib.request.urlopen(req, timeout=20)
            result = json.loads(response.read().decode('utf-8'))
            
            return result['content'][0]['text']
            
        except Exception as e:
            return f"Analysis Error: {str(e)}"
