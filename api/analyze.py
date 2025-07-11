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
            
            # Fetch data from ALL 5 endpoints
            market_data = self.fetch_all_optionsdepth_data(OPTIONS_KEY)
            
            # Generate analysis based on options data patterns
            analysis = self.generate_options_analysis(market_data, ANTHROPIC_KEY)
            
            response = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'est_time': market_data.get('actual_fetch_time', 'Unknown'),
                'data_fetched': {
                    'heatmap': market_data.get('heatmap_status', False),
                    'breakdown_strike': market_data.get('strike_status', False),
                    'breakdown_exp': market_data.get('exp_status', False),
                    'depthview': market_data.get('depth_status', False),
                    'timeslots': market_data.get('slots_status', False)
                },
                'errors': market_data.get('errors', []),
                'debug_info': market_data.get('debug_info', {}),
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
        # Get current date - July 11, 2025
        now = datetime.now()
        
        # For options data, if it's weekend, use Friday's date
        if now.weekday() == 5:  # Saturday
            current_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        elif now.weekday() == 6:  # Sunday  
            current_date = (now - timedelta(days=2)).strftime("%Y-%m-%d")
        else:
            current_date = now.strftime("%Y-%m-%d")
        
        current_datetime = now.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Since we're in 2025, let's also try yesterday's date in case the API doesn't have today's data yet
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        all_data = {
            'fetch_date': current_date,
            'fetch_time': current_datetime,
            'actual_fetch_time': now.strftime("%Y-%m-%d %H:%M:%S"),
            'errors': [],
            'debug_info': {
                'requested_date': current_date,
                'yesterday_date': yesterday,
                'current_time': current_datetime,
                'weekday': now.strftime("%A"),
                'year': now.year
            }
        }
        
        # Try to determine which date has data available
        test_date = current_date
        
        # 1. First, try INTRADAY TIMESLOTS to see what dates have data
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/intraday-timeslots/"
            
            # Try today first
            params = {
                "date": current_date,
                "key": api_key
            }
            
            full_url = url + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req, timeout=10)
            timeslots_data = json.loads(response.read().decode('utf-8'))
            
            if timeslots_data and isinstance(timeslots_data, list) and len(timeslots_data) > 0:
                all_data['intraday_timeslots'] = timeslots_data
                all_data['slots_status'] = True
                all_data['latest_timeslot'] = timeslots_data[-1]
                test_date = current_date  # Today has data
            else:
                raise Exception("No timeslots for today")
                
        except:
            # Try yesterday
            try:
                params = {
                    "date": yesterday,
                    "key": api_key
                }
                
                full_url = url + "?" + urllib.parse.urlencode(params)
                req = urllib.request.Request(full_url)
                response = urllib.request.urlopen(req, timeout=10)
                timeslots_data = json.loads(response.read().decode('utf-8'))
                
                if timeslots_data and isinstance(timeslots_data, list) and len(timeslots_data) > 0:
                    all_data['intraday_timeslots'] = timeslots_data
                    all_data['slots_status'] = True
                    all_data['latest_timeslot'] = timeslots_data[-1]
                    test_date = yesterday  # Yesterday has data
                    all_data['debug_info']['using_date'] = yesterday
                    all_data['errors'].append(f"Note: Using yesterday's data ({yesterday}) as today's data not yet available")
            except Exception as e:
                all_data['errors'].append(f"Timeslots: {str(e)}")
        
        # Now use the date that has data for other endpoints
        all_data['fetch_date'] = test_date
        
        # 2. HEATMAP API - Get both Gamma and Charm
        for heatmap_type in ['gamma', 'charm']:
            try:
                url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
                params = {
                    "model": "daily",
                    "ticker": "SPX",
                    "date": test_date,
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
                all_data['errors'].append(f"Heatmap {heatmap_type}: {str(e)}")
        
        # 3. BREAKDOWN BY STRIKE API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/"
            params = {
                "date": test_date,
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
            all_data['breakdown_by_strike'] = json.loads(response.read().decode('utf-8'))
            all_data['strike_status'] = True
        except Exception as e:
            all_data['errors'].append(f"Breakdown Strike: {str(e)}")
        
        # 4. BREAKDOWN BY EXPIRATION API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-expiration/"
            params = {
                "date": test_date,
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
            all_data['breakdown_by_expiration'] = json.loads(response.read().decode('utf-8'))
            all_data['exp_status'] = True
        except Exception as e:
            all_data['errors'].append(f"Breakdown Expiration: {str(e)}")
        
        # 5. DEPTHVIEW API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/depthview/"
            params = {
                "date": test_date,
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
            all_data['depthview'] = json.loads(response.read().decode('utf-8'))
            all_data['depth_status'] = True
        except Exception as e:
            all_data['errors'].append(f"Depthview: {str(e)}")
        
        return all_data
    
    def generate_options_analysis(self, market_data, api_key):
        """Generate analysis based purely on options data patterns"""
        try:
            # Safely handle timeslots data
            timeslots_data = market_data.get('intraday_timeslots', [])
            latest_slot = market_data.get('latest_timeslot', 'No data')
            
            if isinstance(timeslots_data, list) and len(timeslots_data) > 0:
                recent_slots = timeslots_data[-5:] if len(timeslots_data) >= 5 else timeslots_data
            else:
                recent_slots = "No timeslot data available"
            
            # Build comprehensive data summary
            data_summary = f"""
            OPTIONS DATA ANALYSIS REQUEST
            
            Data Collection Date: {market_data.get('fetch_date', 'Unknown')} 
            Data Collection Time: {market_data.get('actual_fetch_time', 'Unknown')}
            Latest Available Timeslot: {latest_slot}
            Successful Endpoints: {sum([market_data.get(f'{x}_status', False) for x in ['heatmap', 'strike', 'exp', 'depth', 'slots']])} out of 5
            
            Available Data:
            - Gamma Heatmap: {'✓' if market_data.get('heatmap_gamma') else '✗'}
            - Charm Heatmap: {'✓' if market_data.get('heatmap_charm') else '✗'}
            - Strike Breakdown: {'✓' if market_data.get('breakdown_by_strike') else '✗'}
            - Expiration Breakdown: {'✓' if market_data.get('breakdown_by_expiration') else '✗'}
            - Market Depth: {'✓' if market_data.get('depthview') else '✗'}
            - Timeslots: {'✓' if market_data.get('intraday_timeslots') else '✗'}
            """
            
            # Add available data to summary
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
            Analyze the available SPX options market data for July 11, 2025. Focus on options positioning and flow patterns.
            
            {data_summary}
            
            Based on the AVAILABLE data, please provide:
            
            1. **GAMMA ANALYSIS** (if gamma heatmap available)
               - Key gamma concentration levels
               - Positive/negative gamma zones
               - Potential pinning or acceleration levels
            
            2. **CHARM ANALYSIS** (if charm heatmap available)
               - Time decay impacts across strikes
               - How positioning may shift through the day
            
            3. **OPTIONS FLOW INSIGHTS**
               - What the available data reveals about positioning
               - Any notable patterns or concentrations
               - Directional bias from the options structure
            
            4. **KEY LEVELS & EXPECTATIONS**
               - Important strikes based on gamma/charm
               - Expected behavior around these levels
               - Near-term outlook based on options positioning
            
            Note: Analyzing data for July 2025. If data appears to be from a previous day, note this but still provide analysis.
            Focus on the heatmap data which appears to be working correctly.
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
            error_summary = f"""
            Analysis Error: {str(e)}
            
            Data Summary: Successfully fetched data from {sum([market_data.get(f'{x}_status', False) for x in ['heatmap', 'strike', 'exp', 'depth', 'slots']])} out of 5 endpoints.
            
            Errors encountered:
            {chr(10).join(market_data.get('errors', [])) if market_data.get('errors') else 'No specific errors logged'}
            """
            return error_summary
