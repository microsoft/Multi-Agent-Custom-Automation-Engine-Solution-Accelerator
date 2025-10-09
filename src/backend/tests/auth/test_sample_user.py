from src.backend.auth.sample_user import sample_user  # Adjust path as necessary


def test_sample_user_keys():
    """Verify that all expected keys are present in the sample_user dictionary."""
    expected_keys = [
        "Accept",
        "Accept-Encoding",
        "Accept-Language",
        "Client-Ip",
        "Content-Length",
        "Content-Type",
        "Cookie",
        "Disguised-Host",
        "Host",
        "Max-Forwards",
        "Origin",
        "Referer",
        "Sec-Ch-Ua",
        "Sec-Ch-Ua-Mobile",
        "Sec-Ch-Ua-Platform",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "Traceparent",
        "User-Agent",
        "Was-Default-Hostname",
        "X-Appservice-Proto",
        "X-Arr-Log-Id",
        "X-Arr-Ssl",
        "X-Client-Ip",
        "X-Client-Port",
        "X-Forwarded-For",
        "X-Forwarded-Proto",
        "X-Forwarded-Tlsversion",
        "X-Ms-Client-Principal",
        "X-Ms-Client-Principal-Id",
        "X-Ms-Client-Principal-Idp",
        "X-Ms-Client-Principal-Name",
        "X-Ms-Token-Aad-Id-Token",
        "X-Original-Url",
        "X-Site-Deployment-Id",
        "X-Waws-Unencoded-Url",
    ]
    assert set(expected_keys) == set(sample_user.keys())


def test_sample_user_values():
    # Proceed with assertions
    assert sample_user["Accept"].strip() == "*/*"  # Ensure no hidden characters
    assert sample_user["Content-Type"] == "application/json"
    assert sample_user["Disguised-Host"] == "your_app_service.azurewebsites.net"
    assert (
        sample_user["X-Ms-Client-Principal-Id"]
        == "00000000-0000-0000-0000-000000000000"
    )
    assert sample_user["X-Ms-Client-Principal-Name"] == "testusername@constoso.com"
    assert sample_user["X-Forwarded-Proto"] == "https"


def test_sample_user_cookie():
    """Check if the Cookie key is present and contains an expected substring."""
    assert "AppServiceAuthSession" in sample_user["Cookie"]


def test_sample_user_protocol():
    """Verify protocol-related keys."""
    assert sample_user["X-Appservice-Proto"] == "https"
    assert sample_user["X-Forwarded-Proto"] == "https"
    assert sample_user["Sec-Fetch-Mode"] == "cors"


def test_sample_user_client_ip():
    """Verify the Client-Ip key."""
    assert sample_user["Client-Ip"] == "22.222.222.2222:64379"
    assert sample_user["X-Client-Ip"] == "22.222.222.222"


def test_sample_user_user_agent():
    """Verify the User-Agent key."""
    user_agent = sample_user["User-Agent"]
    assert "Mozilla/5.0" in user_agent
    assert "Windows NT 10.0" in user_agent
    assert "Edg/" in user_agent  # Matches Edge's identifier more accurately
