"""Unusual stock movement detection and alert summary logic."""

ALERT_MONTHLY_CHANGE_PERCENT = 10.0
ALERT_DAILY_CHANGE_PERCENT = 5.0


def detect_unusual_movement(stock_symbol, df, get_stock_name=None, get_instrument_type=None):
    if df is None or df.empty:
        return None

    start_open = float(df.iloc[0]['Open'])
    end_close = float(df.iloc[-1]['Close'])
    monthly_change = ((end_close - start_open) / start_open * 100) if start_open else 0.0

    closes = [float(value) for value in df['Close'].tolist()]
    daily_changes = []
    for previous_close, close in zip(closes, closes[1:]):
        if previous_close:
            daily_changes.append((close - previous_close) / previous_close * 100)

    session_changes = []
    for _, row in df.iterrows():
        open_price = float(row['Open'])
        close_price = float(row['Close'])
        if open_price:
            session_changes.append((close_price - open_price) / open_price * 100)

    combined_daily_changes = daily_changes + session_changes
    largest_daily_change = max(combined_daily_changes, key=abs) if combined_daily_changes else 0.0

    unusual = abs(monthly_change) >= ALERT_MONTHLY_CHANGE_PERCENT
    unusual = unusual or abs(largest_daily_change) >= ALERT_DAILY_CHANGE_PERCENT
    if not unusual:
        return None

    if monthly_change > 0:
        movement = 'Profit'
    elif monthly_change < 0:
        movement = 'Loss'
    elif largest_daily_change > 0:
        movement = 'Profit'
    else:
        movement = 'Loss'

    symbol = str(stock_symbol).strip().upper()
    stock_name = get_stock_name(symbol) if get_stock_name else symbol
    instrument_type = get_instrument_type(symbol) if get_instrument_type else 'Stock'

    return {
        'Stock': stock_name,
        'Symbol': symbol,
        'Type': instrument_type,
        'Movement': movement,
        'Monthly Change': round(monthly_change, 2),
        'Largest Daily Change': round(largest_daily_change, 2),
        'Start Date': str(df.iloc[0]['Date']),
        'End Date': str(df.iloc[-1]['Date']),
        'Start Price': round(start_open, 2),
        'End Price': round(end_close, 2),
    }


def build_alert_html(alerts, date_range='past 30 days'):
    rows = []
    for alert in alerts:
        direction = 'profit' if alert['Monthly Change'] > 0 else 'loss'
        movement_color = '#166534' if alert['Monthly Change'] > 0 else '#b91c1c'
        rows.append(f"""
          <tr>
            <td>{alert['Stock']}<br><small>{alert['Symbol']}</small></td>
            <td>{alert['Type']}</td>
            <td style="color:{movement_color};font-weight:bold">{alert['Movement']}</td>
            <td>{alert['Start Date']}</td>
            <td>{alert['End Date']}</td>
            <td>{alert['Start Price']:.2f}</td>
            <td>{alert['End Price']:.2f}</td>
            <td>{alert['Monthly Change']:+.2f}% ({direction})</td>
            <td>{alert['Largest Daily Change']:+.2f}%</td>
          </tr>
        """)

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#172033">
        <h2 style="text-align:center;color:#991b1b">ATTENTION: Unusual Stock Movement Alert</h2>
        <p>Movements identified for {date_range}:</p>
        <table border="1" cellspacing="0" cellpadding="8" style="border-collapse:collapse;width:100%;font-size:13px">
          <thead style="background:#4472C4;color:white">
            <tr>
              <th>Stock</th><th>Type</th><th>Movement</th><th>Start Date</th><th>End Date</th>
              <th>Start Price</th><th>End Price</th><th>Period Change</th><th>Largest Daily Change</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        <p>Please review these stocks and market conditions carefully.</p>
      </body>
    </html>
    """


def build_intraday_alert_html(alerts):
    rows = []
    for alert in alerts:
        movement_color = '#166534' if alert['Interval Change'] > 0 else '#b91c1c'
        rows.append(f"""
          <tr>
            <td>{alert['Stock']}<br><small>{alert['Symbol']}</small></td>
            <td style="color:{movement_color};font-weight:bold">{alert['Movement']}</td>
            <td>{alert['Timestamp']}</td>
            <td>{alert['Previous Close']:.2f}</td>
            <td>{alert['Latest Close']:.2f}</td>
            <td>{alert['Interval Change']:+.2f}%</td>
          </tr>
        """)

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#172033">
        <h2 style="text-align:center;color:#991b1b">URGENT: Live Unusual Stock Movement Alert</h2>
        <p>A stock moved unusually within the latest 5-minute interval:</p>
        <table border="1" cellspacing="0" cellpadding="8" style="border-collapse:collapse;width:100%;font-size:13px">
          <thead style="background:#4472C4;color:white">
            <tr><th>Stock</th><th>Movement</th><th>Time</th><th>Previous Close</th><th>Latest Close</th><th>5-Minute Change</th></tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        <p>Please review the live stock movement carefully.</p>
      </body>
    </html>
    """
