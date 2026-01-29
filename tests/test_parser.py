from gogo_bot.parser import extract_ticket_number, extract_user_id, parse_csrf_token


def test_parse_csrf_token():
    html = '<html><head><meta name="csrf-token" content="abc123"></head></html>'
    assert parse_csrf_token(html) == "abc123"


def test_extract_user_id():
    html = '<button class="one-ticket-modal-continue-btn" user-id="42"></button>'
    assert extract_user_id(html) == "42"


def test_extract_ticket_number():
    html = """
    <div>
        <h1>Ticket Number</h1>
        <p>Your ticket number is <strong>1234</strong>.</p>
    </div>
    """
    assert extract_ticket_number(html) == "1234"
