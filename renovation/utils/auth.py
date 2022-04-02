import frappe
from frappe.utils import get_url
import asyncer


async def update_user_password(email: str, new_password: str):
    from frappe.utils.password import update_password

    await asyncer.asyncify(update_password)(
        user=email, pwd=new_password, doctype="User", fieldname="password"
    )


async def check_user_password(email: str, pwd: str):
    from frappe.utils.password import check_password

    try:
        await asyncer.asyncify(check_password)(email, pwd)
        return True
    except BaseException:
        return False


def get_oath_client():
    client = frappe.db.get_value("OAuth Client", {})
    if not client:
        # Make one auto
        client = frappe.get_doc(frappe._dict(
            doctype="OAuth Client",
            app_name="default",
            scopes="all openid",
            redirect_urls=get_url(),
            default_redirect_uri=get_url(),
            grant_type="Implicit",
            response_type="Token"
        ))
        client.insert(ignore_permissions=True)
    else:
        client = frappe.get_doc("OAuth Client", client)

    return client


async def get_bearer_token(user, expires_in=3600):
    # TODO: Make this more async
    import hashlib
    import jwt
    import frappe.oauth
    from oauthlib.oauth2.rfc6749.tokens import random_token_generator, OAuth2Token  # noqa

    client = await asyncer.asyncify(get_oath_client)()
    token = frappe._dict({
        'access_token': random_token_generator(None),
        'expires_in': expires_in,
        'token_type': 'Bearer',
        'scopes': client.scopes,
        'refresh_token': random_token_generator(None)
    })
    bearer_token = frappe.new_doc("OAuth Bearer Token")
    bearer_token.client = client.name
    bearer_token.scopes = token['scopes']
    bearer_token.access_token = token['access_token']
    bearer_token.refresh_token = token.get('refresh_token')
    bearer_token.expires_in = token['expires_in'] or 3600
    bearer_token.user = user
    bearer_token.save(ignore_permissions=True)
    frappe.db.commit()

    # ID Token
    id_token_header = {
        "typ": "jwt",
        "alg": "HS256"
    }
    id_token = {
        "aud": "token_client",
        "exp": int(
            (frappe.db.get_value(
                "OAuth Bearer Token",
                token.access_token,
                "expiration_time") -
                frappe.utils.datetime.datetime(
                1970,
                1,
                1)).total_seconds()),
        "sub": frappe.db.get_value(
            "User Social Login",
            {
                "parent": bearer_token.user,
                "provider": "frappe"},
            "userid"),
        "iss": "frappe_server_url",
        "at_hash": frappe.oauth.calculate_at_hash(
            token.access_token,
            hashlib.sha256)}
    id_token_encoded = jwt.encode(
        id_token, "client_secret", algorithm='HS256', headers=id_token_header)
    id_token_encoded = frappe.safe_decode(id_token_encoded)
    token.id_token = id_token_encoded
    frappe.flags.jwt = id_token_encoded
    return token


async def get_bearer_token_against_refresh_token(refresh_token: str):
    from frappe.integrations.oauth2 import get_token
    r = frappe.request
    r.form = frappe._dict(
        grant_type="refresh_token",
        refresh_token=refresh_token
    )
    frappe.form_dict.refresh_token = refresh_token

    # frappe.oauth.authenticate_client
    # requires cookies.user_id to be equal to frappe.session.user
    # to be successful. It is a bug in frappe
    # Let's bypass it temporarily
    r = frappe.request
    r.headers = frappe._dict(r.headers)  # EnvironHeaders are immutable
    r.headers["Cookie"] = "user_id={};".format(frappe.session.user)

    get_token()
    token = frappe._dict(frappe.local.response)

    token.user = frappe.db.get_value(
        "OAuth Bearer Token",
        token.access_token,
        "user"
    )
    frappe.set_user(token.user)

    # Let's delete this refreshToken
    frappe.db.set_value(
        "OAuth Bearer Token", {"refresh_token": refresh_token}, "refresh_token", "void")

    return token
