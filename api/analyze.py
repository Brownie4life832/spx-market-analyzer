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
                'est_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data_fetched': {
                    'heatmap': market_data.get('heatmap_status', False),
                    'breakdown_strike': market_data.get('strike_status', False),
                    'breakdown_exp': market_data.get('exp_status', False),
                    'depthview': market_data.get('depth_status', False),
                    'timeslots': market_data.get('slots_status', False)
                },
                'data_timestamps': market_data.get('data_timestamps', {}),
                'errors': market_data.get('errors', []),
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
        request_date = datetime.now().strftime("%Y-%m-%d")
        request_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        all_data = {
            'errors': [],
            'data_timestamps': {}  # Track when each piece of data is from
        }
        
        # 1. First get timeslots to find the latest available data time
        latest_timeslot = None
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
            
            if isinstance(timeslots_data, list) and len(timeslots_data) > 0:
                latest_timeslot = timeslots_data[-1]
                all_data['latest_timeslot'] = latest_timeslot
                all_data['data_timestamps']['timeslots'] = f"Latest: {latest_timeslot}"
                
        except Exception as e:
            all_data['errors'].append(f"Timeslots: {str(e)}")
        
        # 2. HEATMAP API - Try BOTH daily and intraday models
        for heatmap_type in ['gamma', 'charm']:
            success = False
            
            # First try intraday model with latest timeslot
            if latest_timeslot:
                try:
                    url = "https://api.optionsdepth.com/options-depth-api/v1/heatmap/"
                    params = {
                        "model": "intraday",
                        "ticker": "SPX",
                        "date": request_date,
                        "type": heatmap_type,
                        "date_time": latest_timeslot,  # Use latest timeslot
                        "key": api_key
                    }
                    
                    full_url = url + "?" + urllib.parse.urlencode(params)
                    req = urllib.request.Request(full_url)
                    response = urllib.request.urlopen(req, timeout=15)
                    data = json.loads(response.read().decode('utf-8'))
                    
                    all_data[f'heatmap_{heatmap_type}'] = data
                    all_data['heatmap_status'] = True
                    all_data['data_timestamps'][f'heatmap_{heatmap_type}'] = f"Intraday: {latest_timeslot}"
                    success = True
                    
                except:
                    pass
            
            # If intraday didn't work, try daily model
            if not success:
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
                    all_data['data_timestamps'][f'heatmap_{heatmap_type}'] = f"Daily: {request_date}"
                    
                except Exception as e:
                    all_data['errors'].append(f"Heatmap {heatmap_type}: {str(e)}")
        
        # 3. BREAKDOWN BY STRIKE API - Try intraday first
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/"
            
            # Try intraday with latest timeslot
            if latest_timeslot:
                params = {
                    "date": request_date,
                    "ticker": "SPX",
                    "mode": "net",
                    "model": "intraday",
                    "metric": "DEX", 
                    "option_type": "C",
                    "customer_type": "procust",
                    "expiration_type": "all",
                    "date_time": latest_timeslot,
                    "with_markers": "true",
                    "key": api_key
                }
            else:
                # Fallback to daily
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
            all_data['data_timestamps']['strikes'] = f"Model: {'intraday' if latest_timeslot else 'daily'}"
            
        except Exception as e:
            all_data['errors'].append(f"Breakdown Strike: {str(e)}")
        
        # 4. BREAKDOWN BY EXPIRATION API
        try:
            url = "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-expiration/"
            
            if latest_timeslot:
                params = {
                    "date": request_date,
                    "ticker": "SPX",
                    "mode": "net",
                    "model": "intraday",
                    "option_type": "C",
                    "metric": "DEX",
                    "customer_type": "procust",
                    "expiration_type": "all",
                    "date_time": latest_timeslot,
                    "key": api_key
                }
            else:
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
            all_data['data_timestamps']['expirations'] = f"Model: {'intraday' if latest_timeslot else 'daily'}"
            
        except Exception as e:
            all_data['errors'].append(f"Breakdown Expiration: {str(e)}")
        
        # 5. DEPTHVIEW API
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
        
        return all_data
    
    def generate_options_analysis(self, market_data, api_key):
        """Generate analysis based on whatever data is available"""
        try:
            # Get info about data freshness
            latest_slot = market_data.get('latest_timeslot', 'Unknown')
            data_timestamps = market_data.get('data_timestamps', {})
            
            # Build data summary
            data_summary = f"""
            OPTIONS DATA ANALYSIS - MIXED DATA SOURCES
            
            Latest Available Timeslot: {latest_slot}
            
            Data Freshness by Source:
            - Heatmap Gamma: {data_timestamps.get('heatmap_gamma', 'Unknown')}
            - Heatmap Charm: {data_timestamps.get('heatmap_charm', 'Unknown')}
            - Strike Breakdown: {data_timestamps.get('strikes', 'Unknown')}
            - Expiration Breakdown: {data_timestamps.get('expirations', 'Unknown')}
            
            Available Data:
            - Gamma Heatmap: {'✓' if market_data.get('heatmap_gamma') else '✗'}
            - Charm Heatmap: {'✓' if market_data.get('heatmap_charm') else '✗'}
            - Strike Breakdown: {'✓ CURRENT' if market_data.get('breakdown_by_strike') else '✗'}
            - Expiration Breakdown: {'✓ CURRENT' if market_data.get('breakdown_by_expiration') else '✗'}
            - Market Depth: {'✓' if market_data.get('depthview') else '✗'}
            """
            
            # Add current data first (strikes and expirations)
            if market_data.get('breakdown_by_strike'):
                data_summary += f"\n\n1. CURRENT STRIKE BREAKDOWN (MOST RECENT DATA):\n{json.dumps(market_data.get('breakdown_by_strike'), indent=2)[:1200]}"
            
            if market_data.get('breakdown_by_expiration'):
                data_summary += f"\n\n2. CURRENT EXPIRATION BREAKDOWN (MOST RECENT DATA):\n{json.dumps(market_data.get('breakdown_by_expiration'), indent=2)[:1200]}"
            
            # Add potentially older heatmap data
            if market_data.get('heatmap_gamma'):
                data_summary += f"\n\n3. GAMMA HEATMAP (MAY BE OLDER):\n{json.dumps(market_data.get('heatmap_gamma'), indent=2)[:800]}"
            
            if market_data.get('heatmap_charm'):
                data_summary += f"\n\n4. CHARM HEATMAP (MAY BE OLDER):\n{json.dumps(market_data.get('heatmap_charm'), indent=2)[:800]}"
            
            prompt = f"""
            Analyze the SPX options market data. IMPORTANT: The strike and expiration breakdowns show CURRENT data, 
            while the heatmaps might be showing older data. Focus primarily on the current data.
            
            {data_summary}
            
            Please provide:
            
            1. **CURRENT OPTIONS POSITIONING** (from strike/expiration breakdowns - THIS IS CURRENT)
               - Key strikes with heavy positioning RIGHT NOW
               - Put/call imbalances in current data
               - Most active expirations and what they indicate
               - Current dealer positioning implications
            
            2. **GAMMA/CHARM CONTEXT** (from heatmaps - note if this appears to be older data)
               - If heatmap data seems stale, mention this caveat
               - General gamma levels for context only
               - Don't base primary analysis on potentially old heatmap data
            
            3. **KEY TRADING LEVELS** (based on CURRENT strike/expiration data)
               - Important strikes showing heavy interest NOW
               - Support/resistance from current options positioning
               - Potential pinning levels from current data
            
            4. **NEAR-TERM OUTLOOK**
               - Based primarily on the current strike/expiration data
               - Expected behavior around key strikes
               - Directional bias from current positioning
            
            PRIORITIZE the strike and expiration breakdown data as this appears to be current.
            If heatmap data seems inconsistent with current strikes, note this discrepancy.
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
