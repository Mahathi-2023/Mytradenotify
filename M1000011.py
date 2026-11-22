from flask import Blueprint, redirect, render_template_string, request, session, url_for

from M1000010 import authenticate, load_accounts, register_user

login_bp = Blueprint('login', __name__)

LOGIN_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    body { margin:0; min-height:100vh; display:grid; place-items:center; background:linear-gradient(135deg,#edf4ff,#f8fafc); font-family:Arial,sans-serif; color:#172033; }
    .card { width:min(420px,calc(100% - 32px)); background:white; border-radius:14px; padding:28px; box-shadow:0 10px 30px rgba(15,23,42,.12); }
    h1 { text-align:center; margin-top:0; }
    label { display:block; font-weight:bold; margin-top:14px; }
    input { width:100%; box-sizing:border-box; padding:12px; margin-top:6px; border:1px solid #cbd5e1; border-radius:8px; }
    button { width:100%; padding:12px; margin-top:18px; border:0; border-radius:8px; background:#2563eb; color:white; font-weight:bold; cursor:pointer; }
    .message { margin-top:12px; color:#b91c1c; text-align:center; }
    .links { text-align:center; margin-top:16px; }
  </style>
</head>
<body>
  <form class="card" method="post" action="{{ action }}">
    <h1>{{ title }}</h1>
    {% if register %}
      <label>First Name *</label><input name="first_name" required>
      <label>Last Name</label><input name="last_name">
    {% endif %}
    <label>Gmail Address *</label><input name="email" type="email" required placeholder="name@gmail.com">
    <label>Password *</label><input name="password" type="password" required minlength="8">
    {% if register %}<label>Confirm Password *</label><input name="confirm_password" type="password" required minlength="8">{% endif %}
    <button type="submit">{{ submit_text }}</button>
    {% if message %}<div class="message">{{ message }}</div>{% endif %}
    <div class="links">
      {% if register %}<a href="/login">Back to Login</a>{% else %}<a href="/register">Create User Account</a>{% endif %}
    </div>
  </form>
</body>
</html>
'''


def current_account():
    email = session.get('account_email')
    return load_accounts().get(email) if email else None


def login_required(view):
    from functools import wraps

    @wraps(view)
    def protected(*args, **kwargs):
        account = current_account()
        if account is None or not account.get('active'):
            session.clear()
            return redirect(url_for('login.login'))
        return view(*args, **kwargs)

    return protected


@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        account = authenticate(request.form.get('email'), request.form.get('password'))
        if account:
            session['account_email'] = account['email']
            return redirect(url_for('dashboard.dashboard'))
        message = 'Invalid Gmail address or password.'

    return render_template_string(LOGIN_TEMPLATE, action='/login', title='My Trade Notify Login', submit_text='Sign In', register=False, message=message)


@login_bp.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        if password != confirm_password:
            message = 'Passwords do not match.'
        else:
            account, error = register_user(
                request.form.get('first_name'),
                request.form.get('last_name'),
                request.form.get('email'),
                password,
            )
            if account:
                session['account_email'] = account['email']
                return redirect(url_for('dashboard.dashboard'))
            message = error

    return render_template_string(LOGIN_TEMPLATE, action='/register', title='Create User Account', submit_text='Create Account', register=True, message=message)


@login_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login.login'))
