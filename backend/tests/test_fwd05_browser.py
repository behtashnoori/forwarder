"""Actual production bundle and native PG backend; synthetic private pipe only."""
import json
from pathlib import Path
import subprocess
import threading
import queue
import secrets
import time
import pytest
from flask import request, send_from_directory
from werkzeug.serving import make_server, WSGIRequestHandler
from backend.extensions import db
from backend.tests.test_fwd05_runtime import journey


class QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        pass


@pytest.mark.parametrize('timezone', ['UTC', 'America/New_York'])
def test_real_customer_browser_fragment_responses_receipts_and_leakage(journey, timezone, tmp_path):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('Browser qualification explicitly requires native PostgreSQL')
    dist = Path(__file__).resolve().parents[2] / 'dist'
    assert (dist / 'quote-response.html').is_file()
    app = journey.app
    @app.get('/quote-response.html')
    def shell():
        return send_from_directory(dist, 'quote-response.html')
    @app.get('/quote-capture.js')
    def capture_script():
        return send_from_directory(dist, 'quote-capture.js')
    @app.get('/assets/<path:name>')
    def asset(name):
        return send_from_directory(dist / 'assets', name)
    def shell_headers(response):
        if request.path == '/quote-response.html' or request.path == '/quote-capture.js' or request.path.startswith('/assets/'):
            response.headers['Content-Security-Policy'] = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
            response.headers['Cache-Control'] = 'no-store'
            response.headers['Referrer-Policy'] = 'no-referrer'
        return response
    app.after_request_funcs[None].insert(0, shell_headers)
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    origin = f'http://127.0.0.1:{server.server_port}'
    app.config['QUOTE_CAPABILITY_ALLOWED_ORIGINS'] = [origin]
    db.session.rollback()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        private = json.dumps({'link': origin + '/quote-response.html#' + journey.token,
            'timezone': timezone, 'screenshot': str(tmp_path / ('customer-' + timezone.replace('/', '-') + '.png'))})
        result = subprocess.run(['node', 'scripts/uat/fwd05_customer_browser_runner.mjs'],
            input=private, text=True, capture_output=True, timeout=90)
        # Never include subprocess arguments/private input/Playwright stacks.
        assert result.returncode == 0, 'Actual Chromium customer qualification failed; private diagnostics suppressed'
        summary = json.loads(result.stdout.strip())
        assert summary['status'] == 'PASS' and summary['timezone'] == timezone
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()


@pytest.mark.parametrize('timezone', ['UTC', 'America/New_York'])
def test_real_staff_admin_publication_private_customer_reissue_journey(journey, timezone, tmp_path):
    if db.engine.dialect.name != 'postgresql':
        pytest.skip('Browser qualification explicitly requires native PostgreSQL')
    import bcrypt
    from backend.models import ExpertUser, ShipmentRequest
    from backend.operational_models import OperationalMembership, OperationalAudit
    from backend.quote_response_models import QuoteResponseFact, QuoteResponseReceipt
    from backend.services.notification_action_service import consume_one, _dispatch
    from backend.notification_models import NotificationAction, NotificationAttempt
    from datetime import date, timedelta
    root = db.session.get(ShipmentRequest, journey.root_id)
    root.tracking_code='SR-FWD05-SYNTHETIC'
    root_public_id, organization_id = root.public_id, root.operational_organization_id
    password = secrets.token_urlsafe(24)
    expert = db.session.get(ExpertUser, journey.expert_id)
    expert.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    admin = ExpertUser(username='synthetic-fwd05-browser-admin',password_hash=expert.password_hash,
        full_name='مدیر آزمون',authority='ORGANIZATION_ADMIN',role='admin',is_active=True)
    db.session.add(admin); db.session.flush()
    db.session.add(OperationalMembership(organization_id=organization_id,user_id=admin.id,is_active=True,permissions=['request.read']))
    expert_username, admin_username = expert.username, admin.username
    db.session.commit()
    app, dist = journey.app, Path(__file__).resolve().parents[2] / 'dist'
    @app.get('/admin')
    @app.get('/expert')
    @app.get('/expert/requests/<reference>')
    @app.get('/customer/track/<reference>')
    def staff_shell(reference=None):
        return send_from_directory(dist, 'index.html')
    # The backend owns a pre-existing '/' health page. This synthetic gateway
    # fixture serves the built frontend there; duplicate routes would leave the
    # health endpoint first and never exercise the actual application bundle.
    root_endpoint,_ = app.url_map.bind('127.0.0.1').match('/',method='GET')
    app.view_functions[root_endpoint] = staff_shell
    @app.get('/quote-response.html')
    def customer_shell():
        return send_from_directory(dist, 'quote-response.html')
    @app.get('/quote-capture.js')
    def customer_capture_script():
        return send_from_directory(dist, 'quote-capture.js')
    @app.get('/assets/<path:name>')
    def bundle_asset(name):
        return send_from_directory(dist / 'assets', name)
    def customer_headers(response):
        if request.path in {'/quote-response.html','/quote-capture.js'}:
            response.headers['Content-Security-Policy']="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
            response.headers['Cache-Control']='no-store'
            response.headers['Referrer-Policy']='no-referrer'
        return response
    app.after_request_funcs[None].insert(0,customer_headers)
    server=make_server('127.0.0.1',0,app,threaded=True,request_handler=QuietHandler)
    origin=f'http://127.0.0.1:{server.server_port}'
    app.config.update(QUOTE_CAPABILITY_ALLOWED_ORIGINS=[origin],QUOTE_CAPABILITY_CUSTOMER_ORIGIN=origin)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    process=None
    try:
        process=subprocess.Popen(['node','scripts/uat/fwd05_staff_browser_runner.mjs'],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
        events=queue.Queue()
        def read_events():
            for line in process.stdout:
                events.put(line)
            events.put(None)
        reader=threading.Thread(target=read_events,daemon=True);reader.start()
        process.stdin.write(json.dumps({'origin':origin,'root':root_public_id,'tracking':'SR-FWD05-SYNTHETIC','timezone':timezone,
            'validUntil':(date.today()+timedelta(days=3)).isoformat(),'screenshot':str(tmp_path/'staff-home.png'),
            'admin':{'username':admin_username,'password':password},
            'expert':{'username':expert_username,'password':password}})+'\n');process.stdin.flush()
        summary=None
        deadline=time.monotonic()+150
        while time.monotonic()<deadline:
            event=events.get(timeout=max(1,deadline-time.monotonic()))
            assert event is not None,'Browser exited before qualification summary; private diagnostics suppressed'
            parsed=json.loads(event)
            if parsed.get('command')=='DISPATCH_PRIVATE':
                db.session.rollback()
                action_id=consume_one()
                assert action_id is not None and _dispatch(action_id),'Synthetic private delivery failed'
                action=db.session.get(NotificationAction,action_id)
                attempt=db.session.get(NotificationAttempt,action.active_attempt_id)
                _,link=journey.capture.consume_for_fixture(attempt.provider_reference)
                db.session.rollback()
                process.stdin.write(json.dumps({'link':link})+'\n');process.stdin.flush()
            elif parsed.get('command')=='INVALIDATE_SYNTHETIC_RECIPIENT':
                # Explicit synthetic fixture mutation, not production onboarding.
                from backend.models import Customer
                db.session.rollback()
                customer=db.session.get(Customer,journey.customer_id)
                customer.email='synthetic-invalidated@example.test'
                db.session.commit()
                process.stdin.write(json.dumps({'status':'ACK'})+'\n');process.stdin.flush()
            else:
                summary=parsed;break
        if summary:
            (tmp_path/'staff-browser-result.json').write_text(json.dumps(summary),encoding='utf-8')
        assert summary and summary['status']=='PASS','Staff/admin browser failed; safe stage: '+str((summary or {}).get('stage'))+'; checks: '+','.join((summary or {}).get('checks',[]))
        assert process.wait(timeout=10)==0
        db.session.remove()
        assert db.session.query(QuoteResponseFact).count()==db.session.query(QuoteResponseReceipt).count()==2
        assert db.session.query(OperationalAudit).filter_by(action='organization.quotation-timezone.changed').count()==1
        assert db.session.query(OperationalAudit).filter_by(action='authorization.quote-capability.reissue').count()==1
        (tmp_path/'staff-browser-result.json').write_text(json.dumps(summary),encoding='utf-8')
    finally:
        if process and process.poll() is None:
            process.terminate();process.wait(timeout=10)
        server.shutdown();thread.join(timeout=5);server.server_close()
