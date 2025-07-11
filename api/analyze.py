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
            
            # Fetch data from ALL 5 endpoints
            market_data = self.fetch_all_optionsdepth_data(OPTIONS_KEY)
            
            # Generate analysis based on options data patterns
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
        """Fetch data from ALL 5 OptionDepth endpoints"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        all_data = {
            'fetch_date': current_date,
            'fetch_time': current_datetime
        }
        
        # 1. HEATMAP API - Get both Gamma and Charm
        print("Fetching heatmap data...")
        for heatmap_type in ['gamma', 'charm']:
            try:
                url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
                params = {
                    "model": "daily",
                    "ticker": "SPX",
                    "date": current_date,
                    "type": heatmap_type,
                    "key": api_key
                }
                
                full_url = url + "?" + urllib.parse.urlencode(params)
                req = urllib.request.Request(full_url)
                response = urllib.request.urlopen(req, timeout=15)
                data = json.loads(response.read().decode('utf-8'))
                all_data[f'heatmap_{heatmap_type}'] = data
                all_data['heatmap_status'] = True
            except Exception as e:
                all_data[f'heatmap_{heatmap_type}_error'] = str(e)
        
        # 2. BREAKDOWN BY STRIKE API
        print("Fetching breakdown by strike...")
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/"
            params = {
                "date": current_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "intraday",
                "metric": "DEX",
                "option_type": "C",
                "customer_type": "procust",
                "expiration_type": "range",
                "expiration_range_start": current_date,
                "expiration_range_end": current_date,
                "date_time": current_datetime,
                "with_markers": "true",
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            all_data['breakdown_by_strike'] = json.loads(response.read().decode('utf-8'))
            all_data['strike_status'] = True
        except Exception as e:
            all_data['breakdown_strike_error'] = str(e)
        
        # 3. BREAKDOWN BY EXPIRATION API
        print("Fetching breakdown by expiration...")
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-expiration/"
            params = {
                "date": current_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "intraday",
                "option_type": "C",
                "metric": "DEX",
                "customer_type": "procust_posn",
                "expiration_type": "specific",
                "expiration_dates": f"{current_date}:SPXW",
                "expiration_range_start": current_date,
                "expiration_range_end": current_date,
                "lower_strike_price": "200",
                "upper_strike_price": "12000",
                "date_time": current_datetime,
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            all_data['breakdown_by_expiration'] = json.loads(response.read().decode('utf-8'))
            all_data['exp_status'] = True
        except Exception as e:
            all_data['breakdown_exp_error'] = str(e)
        
        # 4. DEPTHVIEW API
        print("Fetching depthview...")
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/depthview/"
            params = {
                "date": current_date,
                "ticker": "SPX",
                "mode": "net",
                "model": "intraday",
                "option_type": "C",
                "metric": "DEX",
                "customer_type": "procust",
                "expiration_type": "range",
                "expiration_range_start": current_date,
                "expiration_range_end": current_date,
                "date_time": current_datetime,
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            all_data['depthview'] = json.loads(response.read().decode('utf-8'))
            all_data['depth_status'] = True
        except Exception as e:
            all_data['depthview_error'] = str(e)
        
        # 5. INTRADAY TIMESLOTS API
        print("Fetching intraday timeslots...")
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/intraday-timeslots/"
            params = {
                "date": current_date,
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=15)
            all_data['intraday_timeslots'] = json.loads(response.read().decode('utf-8'))
            all_data['slots_status'] = True
        except Exception as e:
            all_data['timeslots_error'] = str(e)
        
        return all_data
    
    def generate_options_analysis(self, market_data, api_key):
        """Generate analysis based purely on options data patterns"""
        try:
            # Build comprehensive data summary
            data_summary = f"""
            OPTIONS DATA ANALYSIS REQUEST
            
            Data Collection Time: {market_data.get('fetch_time', 'Unknown')}
            
            Available Data Sources:
            - Gamma Heatmap: {'✓' if market_data.get('heatmap_gamma') else '✗'}
            - Charm Heatmap: {'✓' if market_data.get('heatmap_charm') else '✗'}
            - Strike Breakdown: {'✓' if market_data.get('breakdown_by_strike') else '✗'}
            - Expiration Breakdown: {'✓' if market_data.get('breakdown_by_expiration') else '✗'}
            - Market Depth: {'✓' if market_data.get('depthview') else '✗'}
            - Timeslots: {'✓' if market_data.get('intraday_timeslots') else '✗'}
            
            1. GAMMA HEATMAP DATA:
            {json.dumps(market_data.get('heatmap_gamma', {}), indent=2)[:1000]}
            
            2. CHARM HEATMAP DATA:
            {json.dumps(market_data.get('heatmap_charm', {}), indent=2)[:1000]}
            
            3. STRIKE BREAKDOWN:
            {json.dumps(market_data.get('breakdown_by_strike', {}), indent=2)[:1000]}
            
            4. EXPIRATION BREAKDOWN:
            {json.dumps(market_data.get('breakdown_by_expiration', {}), indent=2)[:1000]}
            
            5. MARKET DEPTH VIEW:
            {json.dumps(market_data.get('depthview', {}), indent=2)[:1000]}
            
            6. AVAILABLE TIMESLOTS:
            {json.dumps(market_data.get('intraday_timeslots', [])[-5:], indent=2)}
            """
            
            prompt = f"""
            Analyze this SPX options market data. DO NOT reference current SPX price. 
            Focus ONLY on what the options data reveals about market positioning and flows.
            
            {data_summary}
            
            Please provide analysis of:
            
            1. **GAMMA POSITIONING**
               - Net gamma exposure levels and concentrations
               - Key gamma strikes that may act as magnets/barriers
               - Positive vs negative gamma zones
            
            2. **CHARM FLOW ANALYSIS**
               - Time decay impacts across strikes
               - Charm flip points and their significance
               - How positioning changes with time decay
            
            3. **STRIKE & EXPIRATION INSIGHTS**
               - Most heavily traded strikes and what they indicate
               - Put/Call positioning imbalances
               - Expiration concentrations and roll effects
            
            4. **MARKET MAKER POSITIONING**
               - Net dealer exposure and hedging needs
               - Levels where dealers are long/short gamma
               - Potential pinning or acceleration zones
            
            5. **FLOW PATTERNS & SIGNALS**
               - Unusual activity or positioning changes
               - Directional bias from options flows
               - Support/resistance implied by options
            
            6. **NEXT 10-30 MIN EXPECTATIONS**
               - Based purely on options positioning
               - Key levels that may attract price
               - Potential for squeeze or pinning
            
            Focus on actionable insights from the options data patterns. 
            Be specific about strike levels and their importance.
            DO NOT mention or guess at current SPX price.
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
            return f"Analysis Error: {str(e)}\n\nData Summary: Successfully fetched data from {sum([market_data.get(f'{x}_status', False) for x in ['heatmap', 'strike', 'exp', 'depth', 'slots']])} out of 5 endpoints."
