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
            
            # Fetch ALL market data from 5 endpoints
            market_data = self.fetch_all_market_data(OPTIONS_KEY)
            
            # Generate analysis
            analysis = self.generate_analysis(market_data, ANTHROPIC_KEY)
            
            response = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis,
                'data_sources': {
                    'heatmap_gamma': market_data.get('heatmap_gamma') is not None,
                    'heatmap_charm': market_data.get('heatmap_charm') is not None,
                    'breakdown_strike': market_data.get('breakdown_strike') is not None,
                    'breakdown_expiration': market_data.get('breakdown_expiration') is not None,
                    'depthview': market_data.get('depthview') is not None
                }
            }
            
        except Exception as e:
            response = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def fetch_all_market_data(self, api_key):
        """Fetch data from all 5 OptionDepth API endpoints"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        data = {}
        
        # 1. HEATMAP - GAMMA
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/heatmap/",
                params={
                    "model": "daily",
                    "ticker": "SPX",
                    "date": current_date,
                    "type": "gamma",
                    "key": api_key
                },
                timeout=10
            )
            data['heatmap_gamma'] = response.json() if response.status_code == 200 else None
        except:
            data['heatmap_gamma'] = None
        
        # 2. HEATMAP - CHARM
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/heatmap/",
                params={
                    "model": "daily",
                    "ticker": "SPX",
                    "date": current_date,
                    "type": "charm",
                    "key": api_key
                },
                timeout=10
            )
            data['heatmap_charm'] = response.json() if response.status_code == 200 else None
        except:
            data['heatmap_charm'] = None
        
        # 3. BREAKDOWN BY STRIKE
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-strike/",
                params={
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
                },
                timeout=10
            )
            data['breakdown_strike'] = response.json() if response.status_code == 200 else None
        except:
            data['breakdown_strike'] = None
        
        # 4. BREAKDOWN BY EXPIRATION
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/breakdown-by-expiration/",
                params={
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
                },
                timeout=10
            )
            data['breakdown_expiration'] = response.json() if response.status_code == 200 else None
        except:
            data['breakdown_expiration'] = None
        
        # 5. DEPTHVIEW
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/depthview/",
                params={
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
                },
                timeout=10
            )
            data['depthview'] = response.json() if response.status_code == 200 else None
        except:
            data['depthview'] = None
        
        # Get intraday slots for timing
        try:
            response = requests.get(
                "https://api.optionsdepth.com/options-depth-api/v1/intraday-timeslots/",
                params={
                    "date": current_date,
                    "key": api_key
                },
                timeout=10
            )
            data['timeslots'] = response.json() if response.status_code == 200 else None
        except:
            data['timeslots'] = None
            
        return data
    
    def generate_analysis(self, market_data, anthropic_key):
        """Generate comprehensive AI analysis from all data sources"""
        client = anthropic.Anthropic(api_key=anthropic_key)
        
        # Build comprehensive data summary
        data_summary = "COMPREHENSIVE SPX MARKET DATA:\n\n"
        
        if market_data.get('heatmap_gamma'):
            data_summary += f"1. GAMMA HEATMAP:\n{json.dumps(market_data['heatmap_gamma'], indent=2)[:800]}\n\n"
        
        if market_data.get('heatmap_charm'):
            data_summary += f"2. CHARM HEATMAP:\n{json.dumps(market_data['heatmap_charm'], indent=2)[:800]}\n\n"
        
        if market_data.get('breakdown_strike'):
            data_summary += f"3. STRIKE BREAKDOWN:\n{json.dumps(market_data['breakdown_strike'], indent=2)[:800]}\n\n"
        
        if market_data.get('breakdown_expiration'):
            data_summary += f"4. EXPIRATION BREAKDOWN:\n{json.dumps(market_data['breakdown_expiration'], indent=2)[:800]}\n\n"
        
        if market_data.get('depthview'):
            data_summary += f"5. MARKET DEPTH:\n{json.dumps(market_data['depthview'], indent=2)[:800]}\n\n"
        
        prompt = f"""
        You are an expert SPX options trader. Analyze this comprehensive options market data:
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST
        
        {data_summary}
        
        Provide a detailed analysis including:
        
        1. **GAMMA ANALYSIS**
           - Key gamma levels (support/resistance)
           - Net gamma exposure implications
           - Expected hedging flows
        
        2. **CHARM FLOW ANALYSIS**
           - Time decay impact
           - Charm flip points
           - Overnight vs intraday positioning
        
        3. **STRIKE/EXPIRATION ANALYSIS**
           - Most active strikes and what they indicate
           - Put/Call skew signals
           - Expiration concentration insights
        
        4. **MARKET DEPTH & POSITIONING**
           - Current dealer positioning
           - Key levels where dealers need to hedge
           - Potential squeeze levels
        
        5. **DIRECTIONAL OUTLOOK (Next 10 Minutes)**
           - Expected price movement and range
           - Key triggers to watch
           - Confidence level (High/Medium/Low)
        
        6. **RISK FACTORS**
           - What could invalidate this view
           - Key levels to monitor
        
        Be specific with price levels and percentages. Focus on actionable insights.
        """
        
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Analysis unavailable: {str(e)}"
