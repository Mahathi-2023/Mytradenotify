import threading

from flask import Blueprint, jsonify, render_template_string, request

import M1000001
from M1000011 import current_account, login_required


def create_dashboard_blueprint(service_status):
    dashboard_bp = Blueprint('dashboard', __name__)
    trigger_lock = threading.Lock()

    DASHBOARD_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>My Trade Notify</title>
  <style>
    body { margin:0; background:#f4f7fb; color:#172033; font-family:Arial,sans-serif; }
    main { max-width:900px; margin:40px auto; padding:20px; }
    h1 { text-align:center; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px; }
    .card { background:white; border-radius:10px; padding:18px; box-shadow:0 3px 12px rgba(0,0,0,.08); }
    .label { color:#60708a; font-size:13px; text-transform:uppercase; }
    .value { font-size:18px; font-weight:bold; margin-top:8px; }
    .running { color:#16836b; }
    .actions { display:flex; flex-wrap:wrap; gap:12px; justify-content:center; margin:24px 0; }
    button { border:0; border-radius:8px; padding:12px 18px; font-size:15px; font-weight:bold; cursor:pointer; color:white; }
    .daily { background:#2563eb; } .monthly { background:#7c3aed; }
    .alert { background:#dc2626; } .live { background:#ea580c; }
    button:disabled { opacity:.6; cursor:wait; }
    #result { max-width:700px; margin:16px auto; text-align:center; font-weight:bold; }
    .header-bar { display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; }
    .account-name { font-size:18px; font-weight:bold; }
    .header-actions { display:flex; flex-direction:column; align-items:flex-end; gap:8px; }
    .country-row { display:flex; align-items:center; gap:8px; }
    .power-button { width:38px; height:38px; padding:0; border-radius:50%; background:#dc2626; color:white; font-size:20px; line-height:38px; text-align:center; }
    .power-button:hover { background:#b91c1c; }
  </style>
</head>
<body>
  <main>
    <h1>My Trade Notify Production Dashboard</h1>
    <div class="header-bar">
      <div class="account-name">{{ account_name }}</div>
      <div class="header-actions">
        <div class="country-row">
          <label for="country" style="font-weight:bold">Country:</label>
          <select id="country" onchange="setCountry(this.value)" style="padding:8px;border-radius:6px">
            <option value="US">United States</option>
            <option value="IN">India</option>
          </select>
        </div>
        <button type="button" class="power-button" title="Logout" aria-label="Logout" onclick="window.location.href='/logout'">⏻</button>
      </div>
    </div>
    <div style="background:#fff;border-left:4px solid #2563eb;padding:14px;margin-bottom:14px;border-radius:6px">
      <strong>Send Daily Report:</strong> Sends profit/loss and a 30-day unusual-movement check.<br>
      <strong>Send Monthly Report:</strong> Sends the monthly profit/loss report.<br>
      <strong>Check 30-Day Alerts:</strong> Sends only the unusual-movement alert.<br>
      <strong>Check Live Alert:</strong> Checks the latest 5-minute movement once.
    </div>
    <div class="actions">
      {% if account_role == 'admin' %}
      <button class="daily" onclick="triggerAction('daily', this)">Send Daily Report</button>
      <button class="monthly" onclick="triggerAction('monthly', this)">Send Monthly Report</button>
      <button class="alert" onclick="triggerAction('alert', this)">Check 30-Day Alerts</button>
      <button class="live" onclick="triggerAction('live-alert', this)">Check Live Alert</button>
      {% endif %}
    </div>
    <div id="result"></div><div class="grid" id="cards"></div>
  </main>
  <script>
    async function refresh() {
      const status = await (await fetch('/api/status')).json();
      const items = [
        ['Service',status.running?'Running':'Stopped'],['Started At',status.started_at],
        ['Last Daily Report',status.last_daily_report||'Not yet generated'],
        ['Last Monthly Report',status.last_monthly_report||'Not yet generated'],
        ['Last Live Alert Check',status.last_live_alert_check||'Not yet generated'],
        ['Last Unusual Alert',status.last_unusual_alert||'Not yet generated'],
        ['Last Error',status.last_error||'None']
      ];
      document.getElementById('cards').innerHTML=items.map(([l,v])=>
        `<div class="card"><div class="label">${l}</div><div class="value ${l==='Service'?'running':''}">${v}</div></div>`).join('');
      document.getElementById('country').value=status.selected_country;
    }
    async function triggerAction(action,button){
      button.disabled=true; const result=document.getElementById('result');
      result.textContent='Processing action...';
      try {
        const response=await fetch(`/api/trigger/${action}`,{method:'POST',headers:{'Accept':'application/json'},redirect:'follow'});
        if (response.redirected || response.status === 302) {
          window.location.href='/login';
          return;
        }
        const data=await response.json();
        result.textContent=data.message || 'Action request completed.';
        result.style.color=data.success?'#16836b':'#dc2626';
      } catch(error) {
        result.textContent='Unable to trigger the action. Please refresh and log in again.';
        result.style.color='#dc2626';
      }
      finally { button.disabled=false; refresh(); }
    }
    async function setCountry(country){
      const response=await fetch('/api/country',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({country})});
      const data=await response.json(); const result=document.getElementById('result');
      result.textContent=data.success?`Country changed to ${data.country_name}.`:data.message;
      result.style.color=data.success?'#16836b':'#dc2626';
    }
    refresh(); setInterval(refresh,10000);
  </script>
</body>
</html>
'''

    @dashboard_bp.route('/')
    @login_required
    def dashboard():
        account = current_account()
        account_name = f"User: {account.get('first_name','')} {account.get('last_name','')}".strip() if account else ''
        return render_template_string(DASHBOARD_TEMPLATE,
            account_role=account.get('role') if account else 'user',
            account_name=account_name)

    @dashboard_bp.route('/api/status')
    @login_required
    def status():
        return jsonify(service_status)

    @dashboard_bp.route('/api/country', methods=['POST'])
    @login_required
    def set_country():
        data = request.get_json(silent=True) or {}
        country = str(data.get('country','')).upper()
        if country not in {'US','IN'}:
            return jsonify({'success':False,'message':'Choose United States or India.'}),400
        country_name = 'United States' if country == 'US' else 'India'
        service_status['selected_country'] = country
        service_status['selected_country_name'] = country_name
        return jsonify({'success':True,'country':country,'country_name':country_name})

    @dashboard_bp.route('/api/trigger/<action>', methods=['POST'])
    @login_required
    def trigger_action(action):
        account = current_account()
        if account.get('role') != 'admin':
            return jsonify({'success':False,'message':'Only administrators can trigger reports and alerts.'}),403
        if not trigger_lock.acquire(blocking=False):
            return jsonify({'success':False,'message':'Another action is already running.'}),409
        if action not in {'daily','monthly','alert','live-alert'}:
            trigger_lock.release()
            return jsonify({'success':False,'message':'Unknown action.'}),400

        def run_action():
            try:
                country = service_status.get('selected_country', 'US')
                if action == 'daily':
                    M1000001.run_report(report_type='day',stock_symbols=M1000001.get_stock_symbols(country))
                elif action == 'monthly':
                    M1000001.run_report(report_type='month',force_month=True,stock_symbols=M1000001.get_stock_symbols(country))
                elif action == 'alert':
                    M1000001.run_alert(stock_symbols=M1000001.get_stock_symbols(country))
                elif action == 'live-alert':
                    M1000001.run_intraday_alerts(stock_symbols=M1000001.get_stock_symbols(country))
                service_status['last_error'] = None
            except Exception as exc:
                service_status['last_error'] = f'{type(exc).__name__}: {exc}'
            finally:
                trigger_lock.release()
                service_status['background_action'] = None

        service_status['background_action'] = action
        threading.Thread(target=run_action,daemon=True,name=f'dashboard-{action}').start()
        return jsonify({'success':True,'message':f'{action} started in the background. Results will be sent to configured recipients.'})

    return dashboard_bp
