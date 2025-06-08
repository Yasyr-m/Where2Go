from unittest.mock import patch


def mock_google_oauth2_token():
    return {
        "access_token": "mock_access_token",
        "expires_in": 3599,
        "refresh_token": "mock_refresh_token",
        "scope": "email profile",
        "token_type": "Bearer",
        "id_token": "mock_id_token",
    }


def mock_google_user_info():
    return {
        "id": "123456789",
        "email": "test@example.com",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/photo.jpg",
        "locale": "en",
    }


def mock_google_oauth2_token_response():
    return patch(
        "requests.post",
        return_value=type(
            "Response",
            (),
            {"json": lambda: mock_google_oauth2_token(), "status_code": 200},
        ),
    )


def mock_google_user_info_response():
    return patch(
        "requests.get",
        return_value=type(
            "Response",
            (),
            {"json": lambda: mock_google_user_info(), "status_code": 200},
        ),
    )
